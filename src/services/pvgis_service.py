"""
Servicio para obtener y procesar datos de radiación solar (PVGIS y estimaciones).
"""
import requests
import time
import math
import os
import streamlit as st

# Track data source for UI display
DATA_SOURCE_PVGIS = "pvgis"
DATA_SOURCE_ESTIMATED = "estimated"

def get_pvgis_hsp_local(lat, lon, show_progress=True):
    """
    Versión optimizada para desarrollo local con PVGIS.
    Returns tuple: (hsp_data, data_source, error_message)
    """
    try:
        api_url = 'https://re.jrc.ec.europa.eu/api/MRcalc'
        params = {
            'lat': lat,
            'lon': lon,
            'horirrad': 1,
            'outputformat': 'json',
            'components': 1,
        }
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SolarCalculator/1.0)',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        max_retries = 3
        timeout = 20
        
        for attempt in range(max_retries):
            try:
                if show_progress and attempt > 0:
                    st.info(f"🔄 Reintentando conexión PVGIS... (intento {attempt + 1}/{max_retries})")
                
                response = session.get(api_url, params=params, timeout=timeout)
                response.raise_for_status()
                
                if response.status_code == 200 and response.content:
                    data = response.json()
                    hsp_data = process_pvgis_data(data, lat, lon, show_messages=False)
                    if hsp_data:
                        # Store source in session state
                        st.session_state.hsp_data_source = DATA_SOURCE_PVGIS
                        return hsp_data
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                    
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
        
        # All retries failed - use estimation
        st.warning("⚠️ No se pudo conectar con PVGIS (base de datos satelital). Usando datos estimados por región geográfica.")
        st.session_state.hsp_data_source = DATA_SOURCE_ESTIMATED
        return get_hsp_estimado_mejorado(lat, lon, show_messages=False)
        
    except Exception as e:
        st.warning(f"⚠️ Error consultando datos solares: {str(e)[:100]}. Usando estimación regional.")
        st.session_state.hsp_data_source = DATA_SOURCE_ESTIMATED
        return get_hsp_estimado_mejorado(lat, lon, show_messages=False)

def get_hsp_estimado_mejorado(lat, lon, show_messages=True):
    """
    Genera estimaciones mejoradas de HSP basadas en datos climáticos globales.
    """
    dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    hsp_mensual = []
    
    # Datos climáticos mejorados por región
    region_data = get_climate_data_by_region(lat, lon)
    
    for month_index in range(12):
        # Factor estacional más preciso
        seasonal_factor = get_seasonal_factor(lat, month_index)
        
        # HSP base por región
        base_hsp = region_data['base_hsp']
        variation = region_data['variation']
        
        # Cálculo mejorado
        hsp_diario = base_hsp + variation * seasonal_factor
        
        # Ajuste por altitud (si tenemos datos)
        altitude_factor = get_altitude_factor(lat, lon)
        hsp_diario *= altitude_factor
        
        # Limitar valores razonables
        hsp_diario = max(1.5, min(7.5, hsp_diario))
        
        hsp_mensual.append(round(hsp_diario, 2))
    
    # Store source in session state
    st.session_state.hsp_data_source = DATA_SOURCE_ESTIMATED
    
    if show_messages:
        st.info(f"📊 Datos HSP estimados para zona {region_data['region']} (lat: {lat:.4f}, lon: {lon:.4f})")
    
    return hsp_mensual

def get_climate_data_by_region(lat, lon):
    """
    Obtiene datos climáticos específicos por región geográfica.
    """
    # Zona ecuatorial (0-10°)
    if abs(lat) < 10:
        return {
            'base_hsp': 5.2,
            'variation': 0.8,
            'region': 'ecuatorial'
        }
    
    # Zona tropical (10-30°)
    elif abs(lat) < 30:
        return {
            'base_hsp': 4.8,
            'variation': 1.2,
            'region': 'tropical'
        }
    
    # Zona subtropical (30-40°)
    elif abs(lat) < 40:
        return {
            'base_hsp': 4.2,
            'variation': 1.8,
            'region': 'subtropical'
        }
    
    # Zona templada (40-60°)
    elif abs(lat) < 60:
        return {
            'base_hsp': 3.5,
            'variation': 2.2,
            'region': 'templada'
        }
    
    # Zona polar (>60°)
    else:
        return {
            'base_hsp': 2.8,
            'variation': 2.5,
            'region': 'polar'
        }

def get_seasonal_factor(lat, month_index):
    """
    Calcula el factor estacional basado en la latitud y el mes.
    """
    # Meses del año (0-11)
    month_angle = 2 * math.pi * month_index / 12
    
    # Para el hemisferio norte
    if lat >= 0:
        seasonal_factor = math.sin(month_angle - math.pi/2)  # Máximo en junio
    else:
        seasonal_factor = math.sin(month_angle + math.pi/2)  # Máximo en diciembre
    
    return seasonal_factor

def get_altitude_factor(lat, lon):
    """
    Factor de corrección por altitud (estimado).
    """
    # Estimación simple basada en coordenadas
    # En Colombia, altitudes típicas por región
    if 4 <= lat <= 12 and -80 <= lon <= -70:  # Colombia
        if lat < 6:  # Costa Caribe
            return 1.0
        elif lat < 8:  # Región Andina baja
            return 0.95
        else:  # Región Andina alta
            return 0.90
    else:
        return 1.0

def process_pvgis_data(data, lat, lon, show_messages=True):
    """
    Procesa los datos de PVGIS cuando están disponibles.
    """
    try:
        outputs = data.get('outputs', {})
        monthly_data = outputs.get('monthly', [])

        if not monthly_data:
            return get_hsp_estimado_mejorado(lat, lon, show_messages=show_messages)
        
        dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        hsp_mensual = []
        
        for month in monthly_data:
            hsp_diario = None
            
            # Intentar diferentes claves de datos
            if 'H(h)_m' in month and month['H(h)_m'] is not None:
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    hsp_diario = month['H(h)_m'] / dias_por_mes[month_index]
            
            elif 'H_d' in month and 'H_b' in month:
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    hsp_diario = (month['H_d'] + month['H_b']) / dias_por_mes[month_index]
            
            elif 'G(i)' in month:
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    hsp_diario = month['G(i)'] / dias_por_mes[month_index]
            
            # Fallback a estimación si no hay datos válidos
            if hsp_diario is None or hsp_diario <= 0:
                month_index = month.get('month', 1) - 1
                region_data = get_climate_data_by_region(lat, lon)
                seasonal_factor = get_seasonal_factor(lat, month_index)
                altitude_factor = get_altitude_factor(lat, lon)
                hsp_diario = (region_data['base_hsp'] + region_data['variation'] * seasonal_factor) * altitude_factor
            
            hsp_mensual.append(round(hsp_diario, 2))
        
        # Completar meses faltantes
        while len(hsp_mensual) < 12:
            month_index = len(hsp_mensual)
            region_data = get_climate_data_by_region(lat, lon)
            seasonal_factor = get_seasonal_factor(lat, month_index)
            altitude_factor = get_altitude_factor(lat, lon)
            hsp_diario = (region_data['base_hsp'] + region_data['variation'] * seasonal_factor) * altitude_factor
            hsp_mensual.append(round(hsp_diario, 2))
        
        # Validar valores
        for i, hsp in enumerate(hsp_mensual):
            if hsp < 1.0 or hsp > 8.0:
                month_index = i
                region_data = get_climate_data_by_region(lat, lon)
                seasonal_factor = get_seasonal_factor(lat, month_index)
                altitude_factor = get_altitude_factor(lat, lon)
                hsp_mensual[i] = round((region_data['base_hsp'] + region_data['variation'] * seasonal_factor) * altitude_factor, 2)
        
        # Store source in session state
        st.session_state.hsp_data_source = DATA_SOURCE_PVGIS
        
        if show_messages:
            st.success(f"✅ Datos HSP obtenidos de PVGIS (satélite) para lat: {lat:.4f}, lon: {lon:.4f}")
        return hsp_mensual
        
    except Exception as e:
        if show_messages:
            st.warning(f"⚠️ Error procesando datos PVGIS: {str(e)[:50]}. Usando estimación regional.")
        return get_hsp_estimado_mejorado(lat, lon, show_messages=show_messages)
    
def get_pvgis_hsp_alternative(lat, lon):
    """
    Función alternativa para obtener datos HSP usando múltiples fuentes.
    Optimizada para producción con fallbacks robustos.
    """
    try:
        # Validar coordenadas
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            st.error("❌ Coordenadas inválidas. Por favor selecciona una ubicación válida en el mapa.")
            return None
        
        # Detectar entorno de producción
        is_production = os.getenv('RENDER') or os.getenv('HEROKU') or os.getenv('PORT')
        
        if is_production:
            # In production, use estimated data (more reliable)
            st.session_state.hsp_data_source = DATA_SOURCE_ESTIMATED
            return get_hsp_estimado_mejorado(lat, lon, show_messages=True)
        
        # En desarrollo local, intentar PVGIS con configuración más agresiva
        return get_pvgis_hsp_local(lat, lon, show_progress=True)
        
    except Exception as e:
        st.warning(f"⚠️ Error obteniendo datos solares: {str(e)[:100]}. Usando estimación regional.")
        st.session_state.hsp_data_source = DATA_SOURCE_ESTIMATED
        return get_hsp_estimado_mejorado(lat, lon, show_messages=False)

def get_hsp_estimado(lat, lon):
    """
    Genera estimaciones de HSP basadas en la latitud cuando PVGIS falla.
    Ahora usa la función mejorada.
    """
    return get_hsp_estimado_mejorado(lat, lon, show_messages=True)

def get_data_source_label():
    """
    Returns a user-friendly label for the current HSP data source.
    """
    source = st.session_state.get('hsp_data_source', DATA_SOURCE_ESTIMATED)
    if source == DATA_SOURCE_PVGIS:
        return "🛰️ PVGIS (Datos Satelitales)"
    else:
        return "📊 Estimación Regional"
