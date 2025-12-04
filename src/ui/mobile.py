"""
Interfaz para dispositivos móviles.
"""
import streamlit as st
import datetime
import os
import math
import folium
from streamlit_folium import st_folium
import googlemaps
import pandas as pd
import matplotlib.pyplot as plt

from src.config import HSP_MENSUAL_POR_CIUDAD, PROMEDIOS_COSTO, ESTRUCTURA_CARPETAS, HSP_POR_CIUDAD
from src.services.pvgis_service import get_pvgis_hsp_alternative
from src.services.calculator_service import (
    calcular_costo_por_kwp,
    cotizacion, 
    redondear_a_par,
    calcular_lista_materiales
)
from src.services.drive_service import gestionar_creacion_drive, obtener_siguiente_consecutivo
from src.services.notion_service import agregar_cliente_a_notion_crm
from src.utils.pdf_generator import PropuestaPDF
from src.utils.contract_generator import generar_contrato_docx
from src.utils.chargers import generar_pdf_cargadores, cotizacion_cargadores_costos, calcular_materiales_cargador
from src.utils.helpers import validar_datos_entrada, formatear_moneda

try:
    from carbon_calculator import CarbonEmissionsCalculator
    carbon_calculator = CarbonEmissionsCalculator()
except ImportError:
    carbon_calculator = None

def render_mobile_interface():
    """Interfaz optimizada para móviles"""
    # Debug visual - confirmar que estamos en modo móvil
    st.markdown("""
    <div style="background: #ff6b6b; color: white; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; border: 3px solid #ff4757;">
        <h1 style="margin: 0; color: white;">📱 MODO MÓVIL ACTIVADO 📱</h1>
        <p style="margin: 10px 0; font-size: 18px;">Interfaz optimizada para dispositivos móviles</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header móvil con indicador claro
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.markdown("📱")
    with col2:
        st.title("☀️ Calculadora Solar")
    with col3:
        st.markdown("📱")
    
    st.success("✅ Interfaz móvil cargada correctamente")

    # Inicializar estado de resultados si no existe
    if 'mobile_results' not in st.session_state:
        st.session_state.mobile_results = None
    
    # Información del modo móvil
    with st.expander("ℹ️ Información del Modo Móvil", expanded=False):
        st.markdown("""
        **Características del modo móvil:**
        - 📱 Interfaz optimizada para pantallas pequeñas
        - 🗂️ Navegación por tabs para mejor organización
        - 📍 Mapa interactivo para ubicación
        - ⚡ Cálculos automáticos del sistema
        - 📊 Generación completa de documentos
        - ☁️ Integración con Google Drive
        """)
    
    # Tabs principales con Ubicación
    tab1, tabUbic, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👤 Cliente", "📍 Ubicación", "⚡ Sistema", "💰 Finanzas", "📊 Resultados", "📁 Archivos", "🔌 Cargadores"
    ])
    
    with tab1:
        render_tab_cliente_mobile()
    with tabUbic:
        render_tab_ubicacion_mobile()
    with tab2:
        render_tab_sistema_mobile()
    with tab3:
        render_tab_finanzas_mobile()
    with tab4:
        render_tab_resultados_mobile()
    with tab5:
        render_tab_archivos_mobile()
    with tab6:
        render_tab_cargadores_mobile()

def render_tab_cliente_mobile():
    """Tab de cliente para interfaz móvil"""
    st.header("👤 Datos del Cliente")
        
    # Datos del cliente
    nombre_cliente = st.text_input("Nombre del Cliente", key="nombre_mobile")
    documento_cliente = st.text_input("Documento del Cliente (CC o NIT)", key="doc_mobile")
    direccion_proyecto = st.text_input("Dirección del Proyecto", key="dir_mobile")
    fecha_propuesta = st.date_input("Fecha de la Propuesta", datetime.date.today(), key="fecha_mobile")
    
    if st.button("💾 Guardar Datos del Cliente", use_container_width=True):
        st.session_state.cliente_data = {
            'nombre': nombre_cliente,
            'documento': documento_cliente,
            'direccion': direccion_proyecto,
            'fecha': fecha_propuesta
        }
        st.success("✅ Datos del cliente guardados")

def render_tab_ubicacion_mobile():
    """Tab de ubicación con mapa y PVGIS para móviles"""
    st.header("📍 Ubicación del Proyecto")
    
    # Búsqueda opcional si hay API key
    gmaps = None
    maps_api_key = os.environ.get("Maps_API_KEY")
    if maps_api_key:
        try:
            gmaps = googlemaps.Client(key=maps_api_key)
        except Exception as e:
            st.warning(f"No se pudo inicializar el cliente de Google Maps: {e}")
    else:
        st.info("Configura la variable Maps_API_KEY para habilitar la búsqueda de direcciones.")
    
    address = st.text_input("Buscar dirección o lugar:", placeholder="Ej: Cl. 77 Sur #40-168, Sabaneta", key="address_search_mobile")
    address = address.strip()
    if st.button("🔎 Buscar Dirección", key="buscar_dir_mobile"):
        if not address:
            st.warning("Ingresa una dirección antes de buscar.")
        elif not gmaps:
            st.warning("La búsqueda no está disponible. Revisa la configuración de la API de Google Maps.")
        else:
            try:
                with st.spinner("Buscando dirección..."):
                    res = gmaps.geocode(address, region='CO')
                if res:
                    loc = res[0]['geometry']['location']
                    coords = [loc['lat'], loc['lng']]
                    st.session_state.map_state = st.session_state.get('map_state', {"center":[4.5709,-74.2973],"zoom":6,"marker":None})
                    st.session_state.map_state["marker"] = coords
                    st.session_state.map_state["center"] = coords
                    st.session_state.map_state["zoom"] = 16
                    st.rerun()
                else:
                    st.warning("Dirección no encontrada.")
            except googlemaps.exceptions.ApiError as api_error:
                st.error(f"Google Maps rechazó la solicitud ({api_error}). Verifica la dirección y los permisos del API Key.")
            except Exception as e:
                st.error(f"Error inesperado consultando Google Maps: {e}")
    
    # Estado de mapa
    if "map_state" not in st.session_state:
        st.session_state.map_state = {"center":[4.5709,-74.2973],"zoom":6,"marker":None}
    
    m = folium.Map(location=st.session_state.map_state["center"], zoom_start=st.session_state.map_state["zoom"])
    if st.session_state.map_state["marker"]:
        folium.Marker(location=st.session_state.map_state["marker"], popup="Ubicación", icon=folium.Icon(color="red")).add_to(m)
    
    map_data = st_folium(m, width=700, height=400, key="folium_map_mobile")
    if map_data and map_data.get("last_clicked"):
        st.session_state.map_state["marker"] = [map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]]
        st.session_state.map_state["center"] = st.session_state.map_state["marker"]
        st.session_state.map_state["zoom"] = 16
        st.rerun()
    
    # PVGIS
    hsp_mensual_calculado = None
    latitud = longitud = None
    if st.session_state.map_state["marker"]:
        latitud, longitud = st.session_state.map_state["marker"]
        st.write(f"Coordenadas: `{latitud:.6f}`, `{longitud:.6f}`")
        if 'pvgis_data' not in st.session_state or st.session_state.get('last_coords') != (latitud, longitud):
            with st.spinner("Consultando PVGIS..."):
                st.session_state.pvgis_data = get_pvgis_hsp_alternative(latitud, longitud)
                st.session_state.last_coords = (latitud, longitud)
        hsp_mensual_calculado = st.session_state.pvgis_data
        if hsp_mensual_calculado:
            prom = sum(hsp_mensual_calculado)/len(hsp_mensual_calculado)
            st.metric("Promedio Diario Anual (HSP)", f"{prom:.2f} kWh/m²")
            with st.expander("📊 HSP mensual"):
                meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
                for mes, hsp in zip(meses, hsp_mensual_calculado):
                    st.write(f"{mes}: {hsp:.2f}")
    else:
        st.info("Toca el mapa para fijar la ubicación.")

def render_tab_sistema_mobile():
    """Tab de sistema para interfaz móvil"""
    st.header("⚡ Configuración del Sistema")
    
    # Parámetros del sistema
    consumo = st.number_input("Consumo mensual promedio (kWh)", min_value=100, max_value=10000, value=700, step=50, key="consumo_mobile")
    potencia_panel = st.selectbox("Potencia del panel (W)", [400, 450, 500, 550, 600, 615, 650, 700, 750], index=5, key="pot_panel_mobile")
    cubierta = st.selectbox("Tipo de cubierta", ["LÁMINA", "TEJA", "CONCRETO"], key="cubierta_mobile")
    clima = st.selectbox("Clima predominante", ["SOL", "NUBLADO", "LLUVIA"], key="clima_mobile")
    
    # Factor de seguridad configurable
    factor_seguridad_pct = st.slider("Factor de Seguridad / Sobredimensionamiento (%)", 0, 50, 10, 5, help="Porcentaje adicional al consumo para asegurar cobertura", key="safety_factor_mobile")
    factor_seguridad = 1 + (factor_seguridad_pct / 100)
    
    # Obtener HSP real de la ubicación o usar promedio ciudad
    hsp_data = st.session_state.get('pvgis_data')
    if hsp_data:
        hsp_promedio = sum(hsp_data) / len(hsp_data)
        st.caption(f"📍 Usando HSP real de ubicación: {hsp_promedio:.2f} kWh/m²")
    else:
        # Fallback a un valor razonable si no hay datos (ej. promedio Colombia)
        hsp_promedio = 4.8 
        st.caption(f"⚠️ Usando HSP estimado: {hsp_promedio:.2f} kWh/m² (Selecciona ubicación para mayor precisión)")

    # Cálculo automático de cantidad y tamaño
    # Fórmula: Consumo * FactorSeguridad / (HSP * 30 * Eficiencia)
    eficiencia_sistema = 0.85
    potencia_panel_kw = int(potencia_panel) / 1000
    
    size_teorico = (consumo * factor_seguridad) / (hsp_promedio * 30 * eficiencia_sistema)
    cantidad_calc = max(1, math.ceil(size_teorico / potencia_panel_kw))
    cantidad = redondear_a_par(cantidad_calc)
    size = round(cantidad * potencia_panel / 1000, 2)
    
    st.info(f"📊 Sistema calculado: {cantidad} paneles de {potencia_panel}W = {size} kWp")
    
    if st.button("💾 Guardar Configuración del Sistema", use_container_width=True):
        # Inicializar sistema_data si no existe
        if 'sistema_data' not in st.session_state:
            st.session_state.sistema_data = {}
            
        st.session_state.sistema_data.update({
            'consumo': consumo,
            'potencia_panel': potencia_panel,
            'cubierta': cubierta,
            'clima': clima,
            'quantity': cantidad,
            'size': size
        })
        st.success("✅ Configuración del sistema guardada")

def render_tab_finanzas_mobile():
    """Tab de finanzas para interfaz móvil"""
    st.header("💰 Parámetros Financieros")
    
    # Opción de precio manual para emergencias y descuentos
    precio_manual = st.toggle("💰 Precio Manual (Emergencias/Descuentos)", help="Activa esta opción para ingresar un precio personalizado del proyecto", key="precio_manual_mobile")
    
    if precio_manual:
        precio_manual_valor = st.number_input("Precio Manual del Proyecto (COP)", min_value=1000000, value=50000000, step=100000, help="Ingresa el precio total del proyecto en COP", key="precio_manual_valor_mobile")
        st.warning("⚠️ **Modo Precio Manual Activado** - Se usará este valor en lugar del cálculo automático")
    else:
        precio_manual_valor = None
    
    # Horizonte de tiempo para análisis financiero
    horizonte_tiempo = st.selectbox(
        "📅 Horizonte de Análisis (años)", 
        [15, 20, 25, 30, 35, 40], 
        index=2,  # 25 años por defecto
        help="Selecciona el período de análisis para calcular TIR, VPN y Payback",
        key="horizonte_mobile"
    )
    
    # Análisis de sensibilidad
    incluir_analisis_sensibilidad = st.toggle(
        "🔍 Análisis de Sensibilidad", 
        help="Genera un análisis comparativo de TIR a 10 y 20 años con y sin financiación",
        key="sensibilidad_mobile"
    )
    
    if incluir_analisis_sensibilidad:
        st.info("📈 **Análisis de Sensibilidad**: Se calculará TIR a 10 y 20 años con y sin financiación")
    
    # Parámetros financieros
    costo_kwh = st.number_input("Costo del kWh (COP)", min_value=100, max_value=2000, value=850, step=50, key="costo_mobile")
    indexacion = st.slider("Inflación anual (%)", 0.0, 20.0, 5.0, 0.5, key="index_mobile")
    tasa_descuento = st.slider("Tasa de descuento (%)", 5.0, 25.0, 10.0, 0.5, key="tasa_mobile")
    
    # Financiamiento
    usa_financiamiento = st.checkbox("¿Incluir financiamiento?", key="fin_check_mobile")
    
    if usa_financiamiento:
        porcentaje = st.slider("Porcentaje financiado (%)", 0, 100, 70, 5, key="porc_mobile")
        tasa_interes = st.slider("Tasa de interés anual (%)", 0.0, 30.0, 15.0, 0.5, key="tasa_int_mobile")
        plazo = st.slider("Plazo del crédito (años)", 1, 20, 10, 1, key="plazo_mobile")
    else:
        porcentaje = 0
        tasa_interes = 0.0
        plazo = 0
    
    # Baterías
    incluir_baterias = st.checkbox("¿Incluir baterías?", key="bat_check_mobile")
    
    if incluir_baterias:
        dias_autonomia = st.slider("Días de autonomía", 1, 7, 2, 1, key="dias_mobile")
        costo_bateria = st.number_input("Costo por kWh de batería (COP)", min_value=500000, max_value=2000000, value=1000000, step=50000, key="costo_bat_mobile")
    else:
        dias_autonomia = 2
        costo_bateria = 0
    
    st.subheader("📊 Consideraciones Adicionales del Flujo de Caja")

    # Beneficios tributarios
    incluir_beneficios_tributarios_mobile = st.toggle(
        "💰 Incluir beneficios tributarios",
        help="Agrega beneficios fiscales al flujo de caja",
        key="beneficios_tributarios_mobile"
    )

    tipo_beneficio_tributario_mobile = "deduccion_renta"
    if incluir_beneficios_tributarios_mobile:
        tipo_beneficio_tributario_mobile = st.radio(
            "Tipo de beneficio:",
            ["deduccion_renta", "depreciacion_acelerada"],
            format_func=lambda x: "Deducción Renta" if x == "deduccion_renta" else "Depreciación Acelerada",
            key="tipo_beneficio_mobile"
        )

    # Demora de 6 meses
    demora_6_meses_mobile = st.toggle(
        "⏰ 6 meses de demora",
        help="Reduce beneficios año 1 a la mitad",
        key="demora_6_meses_mobile"
    )

    st.subheader("🌱 Cálculo de Emisiones de Carbono")
    incluir_carbon = st.toggle(
        "🌱 Incluir análisis de sostenibilidad",
        help="Calcula las emisiones de CO2 evitadas y equivalencias ambientales",
        key="incluir_carbon_mobile"
    )

    st.subheader("💼 Resumen Financiero para Financieros")
    mostrar_resumen_financiero_mobile = st.toggle(
        "💼 Mostrar resumen financiero",
        help="Muestra métricas clave para análisis financiero",
        key="resumen_financiero_mobile"
    )

    if st.button("💾 Guardar Parámetros Financieros", use_container_width=True):
        st.session_state.finanzas_data = {
            'costo_kwh': costo_kwh,
            'indexacion': indexacion,
            'tasa_descuento': tasa_descuento,
            'precio_manual': precio_manual,
            'precio_manual_valor': precio_manual_valor,
            'horizonte_tiempo': horizonte_tiempo,
            'incluir_analisis_sensibilidad': incluir_analisis_sensibilidad,
            'usa_financiamiento': usa_financiamiento,
            'porcentaje': porcentaje,
            'tasa_interes': tasa_interes,
            'plazo': plazo,
            'incluir_baterias': incluir_baterias,
            'dias_autonomia': dias_autonomia,
            'costo_bateria': costo_bateria,
            'incluir_carbon': incluir_carbon,
            'mostrar_resumen_financiero_mobile': mostrar_resumen_financiero_mobile,
            'incluir_beneficios_tributarios': incluir_beneficios_tributarios_mobile,
            'tipo_beneficio_tributario': tipo_beneficio_tributario_mobile,
            'demora_6_meses': demora_6_meses_mobile
        }
        st.success("✅ Parámetros financieros guardados")

def render_tab_resultados_mobile():
    """Tab de resultados para interfaz móvil"""
    st.header("📊 Resultados del Cálculo")

    if not all(k in st.session_state for k in ['cliente_data', 'sistema_data', 'finanzas_data']):
        st.warning("Completa Cliente, Sistema y Finanzas antes de ver resultados.")
        return

    # Mostrar resumen de datos ingresados
    with st.expander("📋 Resumen de Datos"):
        st.write("**Cliente:**", st.session_state.cliente_data.get('nombre', 'N/A'))
        st.write("**Sistema:**", f"{st.session_state.sistema_data.get('size', 'N/A')} kWp")
        st.write("**Consumo:**", f"{st.session_state.sistema_data.get('consumo', 'N/A')} kWh/mes")

    # Check if carbon analysis is enabled
    fin = st.session_state.finanzas_data
    incluir_carbon = bool(fin.get('incluir_carbon', False))
    mostrar_resumen_financiero = bool(fin.get('mostrar_resumen_financiero_mobile', False))

    if mostrar_resumen_financiero:
        st.header("💼 Resumen Financiero para Análisis")

        # Calcular métricas financieras clave
        sistema = st.session_state.sistema_data
        consumo = float(sistema.get('consumo', 700))
        pot_panel = float(sistema.get('potencia_panel', 615))
        cantidad = int(sistema.get('quantity') or max(1, round((consumo * 1.2) / (4.5 * 30 * 0.85) * 1000 // int(pot_panel))))
        size_calc = float(sistema.get('size') or round(cantidad * pot_panel / 1000, 2))
        cubierta = sistema.get('cubierta', 'LÁMINA')

        # Calcular costo del proyecto
        costo_por_kwp = calcular_costo_por_kwp(size_calc)
        valor_proyecto_fv = costo_por_kwp * size_calc
        if cubierta.strip().upper() == "TEJA":
            valor_proyecto_fv *= 1.03

        # Costo de baterías si aplica
        costo_bateria = 0
        if fin.get('incluir_baterias', False):
            consumo_diario = consumo / 30
            dias_auto = int(fin.get('dias_autonomia', 2))
            capacidad_util_bateria = consumo_diario * dias_auto
            capacidad_nominal_bateria = capacidad_util_bateria / 0.9  # 90% DoD
            costo_kwh_bat = int(fin.get('costo_bateria', 0))
            costo_bateria = capacidad_nominal_bateria * costo_kwh_bat

        valor_proyecto_total = math.ceil(valor_proyecto_fv + costo_bateria)

        # Calcular generación anual aproximada
        hsp_data = st.session_state.get('pvgis_data') or HSP_MENSUAL_POR_CIUDAD.get(st.session_state.get('ciudad_mobile', 'MEDELLIN'), HSP_MENSUAL_POR_CIUDAD["MEDELLIN"])
        hsp_promedio = sum(hsp_data) / len(hsp_data) if hsp_data else 4.5

        # Generación anual inicial
        potencia_efectiva = min(size_calc, size_calc / 1.2)  # Aproximación
        generacion_anual_inicial = potencia_efectiva * hsp_promedio * 365 * 0.8  # 80% eficiencia

        # O&M anual (2% del CAPEX)
        om_anual = valor_proyecto_total * 0.02  # 2% del valor total del proyecto

        # Degradación anual
        tasa_degradacion_anual = 0.1  # 0.1% por año

        # Mostrar métricas (mobile optimized)
        st.metric("💰 Precio del Proyecto", f"${valor_proyecto_total:,.0f} COP")
        st.metric("🔧 O&M Anual", f"${om_anual:,.0f} COP")
        st.metric("⚡ Generación Anual Inicial", f"{generacion_anual_inicial:,.0f} kWh")
        st.metric("📉 Degradación Anual", f"{tasa_degradacion_anual:.1f}%")

        with st.expander("📋 Detalles Técnicos"):
            st.write(f"**Sistema**: {size_calc:.1f} kWp con {cantidad} paneles")
            st.write(f"**HSP Promedio**: {hsp_promedio:.2f} kWh/m²/día")
            st.write(f"**Tipo de Cubierta**: {cubierta}")

    if incluir_carbon:
        st.header("🌱 Impacto Ambiental y Sostenibilidad")
        st.info("📊 **Análisis de Sostenibilidad Activado**: Se calcularán las emisiones de carbono evitadas, equivalencias ambientales y valor de certificación.")

        # Carbon metrics in columns (mobile optimized)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.metric(
                "CO2 Evitado Anual",
                "Calculado al generar",
                help="Toneladas de CO2 evitadas por año"
            )
            st.metric(
                "Árboles Salvados",
                "Calculado al generar",
                help="Árboles equivalentes salvados por año"
            )
        with col_c2:
            st.metric(
                "Valor Carbono",
                "Calculado al generar",
                help="Valor potencial de certificación de carbono"
            )
            st.metric(
                "Autos Equivalentes",
                "Calculado al generar",
                help="Autos que dejarían de circular por año"
            )

        st.info("Los resultados detallados de sostenibilidad se mostrarán al generar la propuesta en el tab '📁 Archivos'.")

    st.info("Los resultados detallados se mostrarán al generar la propuesta en el tab '📁 Archivos'.")

def render_tab_archivos_mobile():
    """Generación real de propuesta, contrato, gráficos y subida a Drive"""
    st.header("📁 Archivos y Acciones")
    
    if not all(k in st.session_state for k in ['cliente_data','sistema_data','finanzas_data']):
        st.warning("Completa Cliente, Ubicación, Sistema y Finanzas antes de generar.")
        return
    
    cliente = st.session_state.cliente_data
    sistema = st.session_state.sistema_data
    fin = st.session_state.finanzas_data
    ciudad_input = st.selectbox("Ciudad (respaldo HSP si no hay PVGIS)", list(HSP_MENSUAL_POR_CIUDAD.keys()), key="ciudad_mobile")
    
    if st.button("📄 Generar Documentos y Guardar", use_container_width=True, key="generar_mobile"):
        # Obtener datos
        try:
            with st.spinner("Generando documentos y procesando..."):
                # Preparar datos para cotización
                hsp_data = st.session_state.get('pvgis_data') or HSP_MENSUAL_POR_CIUDAD.get(ciudad_input, HSP_MENSUAL_POR_CIUDAD["MEDELLIN"])
                
                # Extract financial parameters
                incluir_beneficios_tributarios = fin.get('incluir_beneficios_tributarios', False)
                tipo_beneficio = fin.get('tipo_beneficio_tributario', 'deduccion_renta')
                incluir_deduccion_renta = incluir_beneficios_tributarios and tipo_beneficio == 'deduccion_renta'
                incluir_depreciacion_acelerada = incluir_beneficios_tributarios and tipo_beneficio == 'depreciacion_acelerada'
                demora_6_meses = fin.get('demora_6_meses', False)
                
                valor_total, size, monto_fin, cuota_mensual, desembolso_ini, flujo_caja, arboles, gen_mensual, vpn, tir, cantidad, vida_util, rec_inv, lcoe, pr, hsp_mensual, pot_ac, ahorro_a1, area_req, cap_bat, carbon_data = cotizacion(
                    Load=float(sistema.get('consumo')),
                    size=float(sistema.get('size')),
                    quantity=int(sistema.get('quantity')),
                    cubierta=sistema.get('cubierta'),
                    clima=sistema.get('clima'),
                    index=float(fin.get('indexacion'))/100,
                    dRate=float(fin.get('tasa_descuento'))/100,
                    costkWh=float(fin.get('costo_kwh')),
                    module=float(sistema.get('potencia_panel')),
                    ciudad=ciudad_input,
                    hsp_lista=hsp_data,
                    perc_financiamiento=float(fin.get('porcentaje')),
                    tasa_interes_credito=float(fin.get('tasa_interes'))/100,
                    plazo_credito_años=int(fin.get('plazo')),
                    incluir_baterias=fin.get('incluir_baterias', False),
                    costo_kwh_bateria=float(fin.get('costo_bateria', 0)),
                    dias_autonomia=int(fin.get('dias_autonomia', 2)),
                    horizonte_tiempo=int(fin.get('horizonte_tiempo', 25)),
                    incluir_carbon=fin.get('incluir_carbon', False),
                    incluir_beneficios_tributarios=incluir_beneficios_tributarios,
                    incluir_deduccion_renta=incluir_deduccion_renta,
                    incluir_depreciacion_acelerada=incluir_depreciacion_acelerada,
                    demora_6_meses=demora_6_meses
                )
                
                # 1. Generar gráficas (guardar datos para recrearlas)
                # No guardamos las figuras directamente en session_state porque pueden causar problemas de pickling o memoria
                # Guardamos los datos necesarios para recrearlas
                
                # 2. Generar PDF
                lat, lon = st.session_state.map_state["marker"] if st.session_state.get("map_state") else (0,0)
                pot_panel = float(sistema.get('potencia_panel'))
                
                # Calcular desglose de precios
                valor_total_red = round(valor_total)
                valor_sin_iva = valor_total_red / 1.19
                valor_iva = valor_total_red - valor_sin_iva
                prom_gen = sum(gen_mensual)/12
                
                usa_fin = fin.get('usa_financiamiento', False)
                plazo = int(fin.get('plazo', 0))
                
                # Get carbon data
                incluir_carbon = fin.get('incluir_carbon', False)
                arboles_equivalentes = 0
                co2_evitado_tons = 0
                
                if incluir_carbon and carbon_data:
                    arboles_equivalentes = carbon_data.get('trees_saved_per_year', 0)
                    co2_evitado_tons = carbon_data.get('annual_co2_avoided_tons', 0.0)
                
                datos_pdf = {
                    "Nombre del Proyecto": f"{cliente.get('nombre','Cliente')} - {cliente.get('ubicacion','Proyecto')}",
                    "Cliente": cliente.get('nombre','Cliente'),
                    "Valor Total del Proyecto (COP)": f"${valor_total_red:,.0f}",
                    "Valor Sistema FV (sin IVA)": f"${valor_sin_iva:,.0f}",
                    "Valor IVA": f"${valor_iva:,.0f}",
                    "Tamano del Sistema (kWp)": f"{size}",
                    "Cantidad de Paneles": f"{int(cantidad)} de {int(pot_panel)}W",
                    "Área Requerida Aprox. (m²)": f"{area_req}",
                    "Inversor Recomendado": f"{rec_inv}",
                    "Generacion Promedio Mensual (kWh)": f"{prom_gen:,.1f}",
                    "Ahorro Estimado Primer Ano (COP)": f"{ahorro_a1:,.2f}",
                    "TIR (Tasa Interna de Retorno)": f"{tir:.1%}",
                    "VPN (Valor Presente Neto) (COP)": f"{vpn:,.2f}",
                    "Periodo de Retorno (anos)": "N/A",
                    "Tipo de Cubierta": sistema.get('cubierta'),
                    "Potencia de Paneles": f"{int(pot_panel)}",
                    "Potencia AC Inversor": f"{pot_ac}",
                    "Desembolso Inicial (COP)": f"${desembolso_ini:,.0f}",
                    "Cuota Mensual del Credito (COP)": f"${cuota_mensual:,.0f}",
                    "Plazo del Crédito": str(plazo * 12) if usa_fin else "0",
                    "Árboles Equivalentes Ahorrados": str(int(round(arboles_equivalentes))),
                    "CO2 Evitado Anual (Toneladas)": f"{co2_evitado_tons:.2f}",
                }
                
                # Determinar si hay financiamiento
                usa_financiamiento = fin.get('usa_financiamiento', False)
                
                pdf = PropuestaPDF(client_name=cliente.get('nombre','Cliente'), project_name=datos_pdf["Nombre del Proyecto"], documento=cliente.get('documento',''), direccion=cliente.get('direccion',''), fecha=cliente.get('fecha', datetime.date.today()))
                pdf_bytes = pdf.generar(datos_pdf, usa_financiamiento, lat, lon)
                nombre_proyecto = datos_pdf["Nombre del Proyecto"]
                nombre_pdf_final = f"{nombre_proyecto}.pdf"
                datos_contrato = datos_pdf.copy(); datos_contrato['Fecha de la Propuesta'] = cliente.get('fecha', datetime.date.today())
                contrato_bytes = generar_contrato_docx(datos_contrato)
                
                # Subida a Drive (si hay credenciales)
                link_carpeta = None
                try:
                    parent_folder_id = os.environ.get("PARENT_FOLDER_ID")
                    if parent_folder_id:
                        # Ensure drive service is available
                        if 'drive_service' not in st.session_state:
                             from google.oauth2.credentials import Credentials
                             from googleapiclient.discovery import build
                             creds = Credentials(
                                None, refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
                                token_uri='https://oauth2.googleapis.com/token',
                                client_id=os.environ.get("GOOGLE_CLIENT_ID"), 
                                client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
                                scopes=['https://www.googleapis.com/auth/drive']
                            )
                             st.session_state.drive_service = build('drive', 'v3', credentials=creds)

                        link_carpeta = gestionar_creacion_drive(
                            st.session_state.drive_service,
                            parent_folder_id,
                            nombre_proyecto,
                            pdf_bytes,
                            nombre_pdf_final,
                            contrato_bytes,
                            f"Contrato_{nombre_proyecto}.docx"
                        )
                except Exception as e:
                    st.warning(f"No se pudo conectar con Drive: {e}")
                
                # Notion CRM
                crm_ok, crm_msg = agregar_cliente_a_notion_crm(
                    cliente.get('nombre'),
                    cliente.get('documento'),
                    cliente.get('direccion'),
                    nombre_proyecto,
                    cliente.get('fecha'),
                    estado="Propuesta Generada"
                )

                # Guardar resultados en session state
                st.session_state.mobile_results = {
                    'gen_mensual': gen_mensual,
                    'flujo_caja': flujo_caja,
                    'pdf_bytes': pdf_bytes,
                    'nombre_pdf_final': nombre_pdf_final,
                    'contrato_bytes': contrato_bytes,
                    'nombre_contrato_final': f"Contrato_{nombre_proyecto}.docx",
                    'link_carpeta': link_carpeta,
                    'crm_ok': crm_ok,
                    'crm_msg': crm_msg,
                    'consumo': float(sistema.get('consumo')),
                    'incluir_baterias': fin.get('incluir_baterias', False)
                }
                st.rerun()
                
        except Exception as e:
            st.error(f"Error generando documentos: {e}")
            import traceback
            st.error(traceback.format_exc())

    # Renderizar resultados persistentes
    if st.session_state.mobile_results:
        res = st.session_state.mobile_results
        
        st.success("✅ Documentos generados exitosamente!")
        
        # Recrear gráficas
        fig1, ax1 = plt.subplots(figsize=(10,5))
        meses_graf = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
        
        if res['incluir_baterias']:
            gen_autoconsumo = [min(g, res['consumo']) for g in res['gen_mensual']]
            gen_bateria = [max(0, g - c) for g, c in zip(res['gen_mensual'], [res['consumo']]*12)]
            ax1.bar(meses_graf, gen_autoconsumo, color='orange', label='Autoconsumo')
            ax1.bar(meses_graf, gen_bateria, bottom=gen_autoconsumo, color='green', label='Batería')
        else:
            ax1.bar(meses_graf, res['gen_mensual'], color='#f5a623', alpha=0.7, label='Generación')
            ax1.plot(meses_graf, [res['consumo']]*12, color='red', linestyle='--', label='Consumo')
        
        ax1.legend()
        st.pyplot(fig1)
        
        fig2, ax2 = plt.subplots(figsize=(10,5))
        ax2.bar(range(len(res['flujo_caja'])), res['flujo_caja'], color='green')
        ax2.set_title("Flujo de Caja Acumulado")
        st.pyplot(fig2)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("⬇️ Descargar Propuesta PDF", res['pdf_bytes'], file_name=res['nombre_pdf_final'], mime="application/pdf", use_container_width=True)
        with col2:
            st.download_button("⬇️ Descargar Contrato Word", res['contrato_bytes'], file_name=res['nombre_contrato_final'], mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        
        if res['link_carpeta']:
            st.markdown(f"[📂 Abrir Carpeta en Google Drive]({res['link_carpeta']})")
        
        if res['crm_ok']:
            st.info(f"🗂️ {res['crm_msg']}")
        else:
            st.warning(f"⚠️ Notion: {res['crm_msg']}")

def render_tab_cargadores_mobile():
    """Tab de cargadores para interfaz móvil"""
    st.header("🔌 Cotizador de Cargadores")
    
    nombre_lugar = st.text_input("Nombre del Cliente/Lugar (Cargadores)", key="nombre_cargador_mobile")
    distancia = st.number_input("Distancia (metros)", min_value=1.0, value=10.0, step=1.0, key="dist_cargador_mobile")
    
    # Opción de precio manual para cargadores
    precio_manual_cargador = st.checkbox("Precio Manual (Cargadores)", key="precio_manual_cargador_mobile")
    precio_valor_cargador = None
    if precio_manual_cargador:
        precio_valor_cargador = st.number_input("Precio Manual del Cargador (COP)", min_value=100000, value=2500000, step=50000, key="precio_valor_cargador_mobile")
    
    if st.button("Calcular Cargador", use_container_width=True):
        pdf_bytes, desglose = generar_pdf_cargadores(nombre_lugar, distancia, precio_valor_cargador)
        if pdf_bytes:
            st.subheader("Desglose de Costos")
            st.write(desglose)
            st.download_button("⬇️ Descargar Cotización Cargador", pdf_bytes, file_name="Cotizacion_Cargador.pdf", mime="application/pdf", use_container_width=True)
            
            # Lista materiales
            mat = calcular_materiales_cargador(distancia)
            st.subheader("Lista de Materiales")
            st.dataframe(pd.DataFrame(mat, columns=["Item", "Cantidad", "Unidad"]))
