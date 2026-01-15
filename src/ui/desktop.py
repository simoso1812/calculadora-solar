import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import datetime
import os
import math
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import folium
from streamlit_folium import st_folium
import googlemaps
from src.config import HSP_MENSUAL_POR_CIUDAD, PROMEDIOS_COSTO, HSP_POR_CIUDAD
from src.config_parametros import DEFAULT_PARAMS, PARAM_DESCRIPTIONS, PARAM_LIMITS, get_param
from src.services.calculator_service import (
    cotizacion, calcular_costo_por_kwp, generar_csv_flujo_caja_detallado,
    calcular_analisis_sensibilidad, calcular_lista_materiales, redondear_a_par
)
from src.services.drive_service import obtener_siguiente_consecutivo, gestionar_creacion_drive
from src.services.location_service import get_static_map_image
from src.services.pvgis_service import get_pvgis_hsp_alternative, get_data_source_label, DATA_SOURCE_PVGIS
from src.services.notion_service import agregar_cliente_a_notion_crm
from src.utils.pdf_generator import PropuestaPDF
from src.utils.contract_generator import generar_contrato_docx
from src.utils.chargers import generar_pdf_cargadores
from src.utils.helpers import validar_datos_entrada, formatear_moneda
from src.utils.plotting import generar_grafica_generacion
from src.utils.excel_generator import generar_excel_financiero



def init_form_defaults():
    """Initialize session state with default form values to persist across reruns"""
    defaults = {
        'form_nombre_cliente': '',
        'form_documento_cliente': '',
        'form_direccion_proyecto': '',
        'form_ubicacion': '',
        'form_consumo': 700,
        'form_potencia_panel': 615,
        'form_cubierta': 'LÁMINA',
        'form_clima': 'SOL',
        'form_costo_kwh': 850,
        'form_indexacion': 5.0,
        'form_tasa_descuento': 10.0,
        'form_horizonte': 25,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def render_desktop_interface():
    """Interfaz optimizada para desktop"""
    st.title("☀️ Calculadora y Cotizador Solar Profesional")

    # === PROCESAR DUPLICACIÓN ANTES DE INIT ===
    # Si hay datos pendientes para duplicar, cargarlos antes de crear widgets
    if 'duplicar_datos' in st.session_state and st.session_state.duplicar_datos:
        datos = st.session_state.duplicar_datos
        st.session_state.form_nombre_cliente = datos.get('nombre_cliente', '')
        st.session_state.form_documento_cliente = datos.get('documento_cliente', '')
        st.session_state.form_direccion_proyecto = datos.get('direccion_proyecto', '')
        st.session_state.form_consumo = datos.get('Load', 700)
        st.session_state.form_costo_kwh = datos.get('costkWh', 850)
        st.session_state.form_indexacion = datos.get('index_input', 5.0)
        st.session_state.form_tasa_descuento = datos.get('dRate_input', 10.0)
        st.session_state.form_horizonte = datos.get('horizonte_tiempo', 25)
        if datos.get('lat') and datos.get('lon'):
            st.session_state.map_state = {
                "center": [datos['lat'], datos['lon']],
                "zoom": 16,
                "marker": [datos['lat'], datos['lon']]
            }
        # Limpiar flag
        st.session_state.duplicar_datos = None
        st.toast("✅ Cotización duplicada. Modifica los parámetros y genera una nueva.")

    # Initialize form defaults for persistence
    init_form_defaults()

    # Inicializar estado de resultados si no existe
    if 'desktop_results' not in st.session_state:
        st.session_state.desktop_results = None
    
    # Inicializar historial de cotizaciones (máximo 10)
    if 'historial_cotizaciones' not in st.session_state:
        st.session_state.historial_cotizaciones = []

    # --- INICIALIZACIÓN DE SERVICIOS Y DATOS ---
    drive_service = None
    numero_proyecto_del_año = 1
    parent_folder_id = None
    try:
        creds = Credentials(
            None, refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get("GOOGLE_CLIENT_ID"), 
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=creds)
        # Store drive service in session state for reuse
        st.session_state.drive_service = drive_service
        
        parent_folder_id = os.environ.get("PARENT_FOLDER_ID")
        if parent_folder_id:
            numero_proyecto_del_año = obtener_siguiente_consecutivo(drive_service, parent_folder_id)
        else:
            st.warning("ID de la carpeta padre no encontrado. El consecutivo iniciará en 1.")
    except Exception as e:
        st.warning(f"Secretos de Google Drive no configurados o inválidos. La creación de carpetas está desactivada.")

    # ==============================================================================
    # INTERFAZ EN LA BARRA LATERAL (SIDEBAR)
    # ==============================================================================
    with st.sidebar:
        st.header("Parámetros de Entrada")
        
        # === HISTORIAL DE COTIZACIONES ===
        if st.session_state.historial_cotizaciones:
            with st.expander(f"📜 Historial de Cotizaciones ({len(st.session_state.historial_cotizaciones)})", expanded=False):
                st.caption("Últimas cotizaciones generadas. Haz clic en 'Duplicar' para cargar los parámetros.")
                
                for i, cot in enumerate(st.session_state.historial_cotizaciones):
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{cot['nombre_cliente']}**")
                            st.caption(f"📅 {cot['fecha']} | ⚡ {cot['size']:.1f} kWp | 💰 ${cot['val_total']:,.0f}")
                        with col2:
                            if st.button("🔄", key=f"duplicar_{cot['id']}", help="Duplicar esta cotización"):
                                # Guardar datos para duplicar en el próximo ciclo
                                st.session_state.duplicar_datos = {
                                    'nombre_cliente': cot['nombre_cliente'] + " (copia)",
                                    'documento_cliente': cot.get('documento_cliente', ''),
                                    'direccion_proyecto': cot.get('direccion_proyecto', ''),
                                    'Load': cot['Load'],
                                    'costkWh': cot['costkWh'],
                                    'index_input': cot['index_input'],
                                    'dRate_input': cot['dRate_input'],
                                    'horizonte_tiempo': cot['horizonte_tiempo'],
                                    'lat': cot.get('lat'),
                                    'lon': cot.get('lon'),
                                }
                                st.session_state.desktop_results = None
                                st.rerun()
                        st.divider()
                
                # Botón para limpiar historial
                if st.button("🗑️ Limpiar historial", use_container_width=True):
                    st.session_state.historial_cotizaciones = []
                    st.rerun()
        
        st.subheader("Datos del Cliente y Propuesta")
        nombre_cliente = st.text_input("Nombre del Cliente", key="form_nombre_cliente")
        documento_cliente = st.text_input("Documento del Cliente (CC o NIT)", key="form_documento_cliente")
        direccion_proyecto = st.text_input("Dirección del Proyecto", key="form_direccion_proyecto")
        fecha_propuesta = st.date_input("Fecha de la Propuesta", datetime.date.today()) 
        
        st.subheader("Información del Proyecto (Interna)")
        ubicacion = st.text_input("Ubicación (Etiqueta para carpeta)", key="form_ubicacion")
        st.text_input("Número de Proyecto del Año (Automático)", value=numero_proyecto_del_año, disabled=True)
        
        st.subheader("Ubicación Geográfica")
        gmaps = None
        maps_api_key = os.environ.get("Maps_API_KEY")
        if maps_api_key:
            try:
                gmaps = googlemaps.Client(key=maps_api_key)
            except Exception as e:
                st.warning(f"No se pudo inicializar el cliente de Google Maps: {e}")
        else:
            st.warning("Variable de entorno Maps_API_KEY no configurada. La búsqueda está desactivada.")

        # === BOTÓN USAR MI UBICACIÓN ===
        col_geo1, col_geo2 = st.columns([1, 1])
        with col_geo1:
            if st.button("📍 Usar mi ubicación", key="use_my_location_desktop", use_container_width=True):
                st.session_state.requesting_location = True
        
        # JavaScript para obtener geolocalización
        if st.session_state.get('requesting_location', False):
            import streamlit.components.v1 as components
            geolocation_js = """
            <script>
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        localStorage.setItem('user_lat', lat);
                        localStorage.setItem('user_lng', lng);
                        alert('Ubicación obtenida: ' + lat.toFixed(6) + ', ' + lng.toFixed(6) + '\\n\\nSi el mapa no se actualiza automáticamente, ingresa estas coordenadas manualmente.');
                    },
                    function(error) {
                        alert('Error obteniendo ubicación: ' + error.message + '\\n\\nAsegúrate de permitir el acceso a la ubicación.');
                    },
                    {enableHighAccuracy: true, timeout: 10000}
                );
            } else {
                alert('Tu navegador no soporta geolocalización');
            }
            </script>
            <p style="color: #888; font-size: 12px;">🔄 Solicitando ubicación... Permite el acceso cuando el navegador lo pida.</p>
            """
            components.html(geolocation_js, height=50)
            st.session_state.requesting_location = False
        
        # Input manual de coordenadas como alternativa
        with col_geo2:
            with st.popover("📝 Ingresar coordenadas"):
                st.caption("Ingresa las coordenadas manualmente:")
                manual_lat = st.number_input("Latitud", value=6.2, min_value=-90.0, max_value=90.0, format="%.6f", key="manual_lat_desktop")
                manual_lng = st.number_input("Longitud", value=-75.5, min_value=-180.0, max_value=180.0, format="%.6f", key="manual_lng_desktop")
                if st.button("✅ Aplicar", key="apply_manual_coords_desktop"):
                    if "map_state" not in st.session_state:
                        st.session_state.map_state = {}
                    st.session_state.map_state["marker"] = [manual_lat, manual_lng]
                    st.session_state.map_state["center"] = [manual_lat, manual_lng]
                    st.session_state.map_state["zoom"] = 16
                    st.rerun()

        address = st.text_input("Buscar dirección o lugar:", placeholder="Ej: Cl. 77 Sur #40-168, Sabaneta", key="address_search")
        address = address.strip()
        if st.button("🔎 Buscar Dirección"):
            if not address:
                st.warning("Por favor, ingresa una dirección para buscar.")
            elif not gmaps:
                st.warning("La búsqueda está desactivada porque no se pudo inicializar Google Maps.")
            else:
                try:
                    with st.spinner("Buscando dirección..."):
                        geocode_result = gmaps.geocode(address, region='CO')
                    if geocode_result:
                        location = geocode_result[0]['geometry']['location']
                        coords = [location['lat'], location['lng']]
                        if "map_state" not in st.session_state:
                             st.session_state.map_state = {}
                        st.session_state.map_state["marker"] = coords
                        st.session_state.map_state["center"] = coords
                        st.session_state.map_state["zoom"] = 16
                        st.rerun()
                    else:
                        st.error("Dirección no encontrada.")
                except googlemaps.exceptions.ApiError as api_error:
                    st.error(f"Google Maps rechazó la solicitud ({api_error}). Revisa que la dirección esté completa y que la API Key tenga acceso al servicio de Geocoding.")
                except Exception as e:
                    st.error(f"Error inesperado consultando Google Maps: {e}")

        if "map_state" not in st.session_state:
            st.session_state.map_state = {"center": [4.5709, -74.2973], "zoom": 6, "marker": None}

        # === TOGGLE VISTA SATÉLITE ===
        vista_satelite = st.toggle("🛰️ Vista Satélite", key="satellite_view_desktop")
        
        # Crear mapa con tiles según selección
        if vista_satelite:
            m = folium.Map(
                location=st.session_state.map_state["center"], 
                zoom_start=st.session_state.map_state["zoom"],
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri World Imagery'
            )
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
                attr='Esri Labels',
                overlay=True,
                name='Etiquetas'
            ).add_to(m)
        else:
            m = folium.Map(location=st.session_state.map_state["center"], zoom_start=st.session_state.map_state["zoom"])
        
        if st.session_state.map_state["marker"]:
            folium.Marker(location=st.session_state.map_state["marker"], popup="Ubicación del Proyecto", icon=folium.Icon(color="red")).add_to(m)
        map_data = st_folium(m, width=700, height=400, key="folium_map_main")
        if map_data and map_data["last_clicked"]:
            st.session_state.map_state["marker"] = [map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]]
            st.rerun()

        hsp_mensual_calculado = None
        latitud, longitud = None, None
        if st.session_state.map_state["marker"]:
            latitud, longitud = st.session_state.map_state["marker"]
            st.write(f"**Coordenadas Seleccionadas:** Lat: `{latitud:.6f}` | Long: `{longitud:.6f}`")
            if 'pvgis_data' not in st.session_state or st.session_state.get('last_coords') != (latitud, longitud):
                with st.spinner("Consultando base de datos satelital (PVGIS)..."):
                    st.session_state.pvgis_data = get_pvgis_hsp_alternative(latitud, longitud)
                    st.session_state.last_coords = (latitud, longitud)
            hsp_mensual_calculado = st.session_state.pvgis_data
            if hsp_mensual_calculado:
                promedio_hsp_anual = sum(hsp_mensual_calculado) / len(hsp_mensual_calculado)
                
                # Show data source clearly
                data_source = get_data_source_label()
                if st.session_state.get('hsp_data_source') == DATA_SOURCE_PVGIS:
                    st.success(f"✅ {data_source}")
                else:
                    st.info(f"📊 {data_source}")
                
                st.metric(label="Promedio Diario Anual (HSP)", value=f"{promedio_hsp_anual:.2f} kWh/m²")
                
                # Mostrar detalles mensuales
                with st.expander("📊 Ver datos mensuales detallados"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**HSP Mensual (kWh/m²/día):**")
                        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
                        for i, (mes, hsp) in enumerate(zip(meses, hsp_mensual_calculado)):
                            st.write(f"{mes}: {hsp:.2f}")
                    
                    with col2:
                        st.write("**Análisis:**")
                        max_hsp = max(hsp_mensual_calculado)
                        min_hsp = min(hsp_mensual_calculado)
                        variacion = ((max_hsp - min_hsp) / promedio_hsp_anual) * 100
                        st.write(f"• Máximo: {max_hsp:.2f} kWh/m²")
                        st.write(f"• Mínimo: {min_hsp:.2f} kWh/m²")
                        st.write(f"• Variación: {variacion:.1f}%")
                
                # Mostrar calidad de los datos
                if any(hsp < 1.0 or hsp > 8.0 for hsp in hsp_mensual_calculado):
                    st.warning("⚠️ Algunos valores HSP están fuera del rango típico. Se han ajustado automáticamente.")
        else:
            st.info("👈 Escribe una dirección, busca, o haz clic directamente en el mapa.")

        ciudad_input = st.selectbox("Ciudad (usada como respaldo)", list(HSP_MENSUAL_POR_CIUDAD.keys()))
        
        if hsp_mensual_calculado:
            hsp_a_usar = hsp_mensual_calculado
            ciudad_para_calculo = f"Coord. ({latitud:.2f}, {longitud:.2f})"
        else:
            hsp_a_usar = HSP_MENSUAL_POR_CIUDAD[ciudad_input]
            ciudad_para_calculo = ciudad_input
        
        # === PARAMETER PRESETS ===
        st.subheader("⚡ Configuración Rápida")
        
        PRESETS = {
            "Personalizado": {"consumo": 700, "paneles": 12, "cubierta": "LÁMINA", "clima": "SOL", "descripcion": "Configura manualmente todos los parámetros"},
            "🏠 Residencial Pequeño": {"consumo": 350, "paneles": 6, "cubierta": "TEJA", "clima": "SOL", "descripcion": "Casa pequeña, 1-2 personas (~3 kWp)"},
            "🏡 Residencial Mediano": {"consumo": 700, "paneles": 12, "cubierta": "LÁMINA", "clima": "SOL", "descripcion": "Casa mediana, 3-4 personas (~6 kWp)"},
            "🏘️ Residencial Grande": {"consumo": 1200, "paneles": 20, "cubierta": "LÁMINA", "clima": "SOL", "descripcion": "Casa grande, 5+ personas (~10 kWp)"},
            "🏪 Comercial Pequeño": {"consumo": 2500, "paneles": 40, "cubierta": "LÁMINA", "clima": "SOL", "descripcion": "Local comercial, oficina (~20 kWp)"},
            "🏢 Comercial Grande": {"consumo": 6000, "paneles": 100, "cubierta": "LÁMINA", "clima": "SOL", "descripcion": "Bodega, supermercado (~50 kWp)"},
            "🏭 Industrial": {"consumo": 12000, "paneles": 200, "cubierta": "LÁMINA", "clima": "SOL", "descripcion": "Fábrica, planta industrial (~100 kWp)"},
        }
        
        preset_seleccionado = st.selectbox(
            "Tipo de proyecto",
            list(PRESETS.keys()),
            format_func=lambda x: f"{x} - {PRESETS[x]['descripcion']}" if x != "Personalizado" else "Personalizado",
            key="preset_proyecto_desktop"
        )
        
        preset_actual = PRESETS[preset_seleccionado]
        
        if preset_seleccionado != "Personalizado":
            st.caption(f"💡 {preset_actual['descripcion']}")
        
        st.divider()
        
        opcion = st.radio("Método para dimensionar:", ["Por Consumo Mensual (kWh)", "Por Cantidad de Paneles"], horizontal=True, key="metodo_dimensionamiento")

        if opcion == "Por Consumo Mensual (kWh)":
            Load = st.number_input("Consumo mensual (kWh)", min_value=50, value=preset_actual['consumo'], step=50)
            module = st.number_input("Potencia del panel (W)", min_value=300, value=615, step=10)
            
            # Factor de seguridad configurable
            factor_seguridad_pct = st.slider("Factor de Seguridad / Sobredimensionamiento (%)", 0, 50, 10, 5, help="Porcentaje adicional al consumo para asegurar cobertura")
            factor_seguridad = 1 + (factor_seguridad_pct / 100)
            
            # Usar HSP real si está disponible
            if hsp_mensual_calculado:
                HSP_promedio = sum(hsp_mensual_calculado) / len(hsp_mensual_calculado)
                st.caption(f"📍 Usando HSP real de ubicación: {HSP_promedio:.2f} kWh/m²")
            else:
                HSP_promedio = HSP_POR_CIUDAD.get(ciudad_input, 4.8)
                st.caption(f"⚠️ Usando HSP estimado de {ciudad_input}: {HSP_promedio:.2f} kWh/m²")

            n_aprox = 0.85
            
            # Fórmula actualizada: Consumo * FactorSeguridad / (HSP * 30 * Eficiencia)
            size_teorico = (Load * factor_seguridad) / (HSP_promedio * 30 * n_aprox)
            quantity_calc = math.ceil(size_teorico * 1000 / module)
            quantity = redondear_a_par(quantity_calc)
            
            size = round(quantity * module / 1000, 2)
            st.info(f"Sistema estimado: **{size:.2f} kWp** ({int(quantity)} paneles)")
        else:
            module = st.number_input("Potencia del panel (W)", min_value=300, value=615, step=10)
            quantity_input = st.number_input("Cantidad de paneles", min_value=1, value=preset_actual['paneles'], step=2)
            quantity = redondear_a_par(quantity_input)
            Load = st.number_input("Consumo mensual (kWh)", min_value=50, value=preset_actual['consumo'], step=50)
            size = round((quantity * module) / 1000, 2)
            st.info(f"Sistema dimensionado: **{size:.2f} kWp**")

        st.subheader("Datos Generales")
        cubierta_options = ["LÁMINA", "TEJA"]
        cubierta_default = cubierta_options.index(preset_actual['cubierta']) if preset_actual['cubierta'] in cubierta_options else 0
        cubierta = st.selectbox("Tipo de cubierta", cubierta_options, index=cubierta_default)
        
        clima_options = ["SOL", "NUBE"]
        clima_default = clima_options.index(preset_actual['clima']) if preset_actual['clima'] in clima_options else 0
        clima = st.selectbox("Clima predominante", clima_options, index=clima_default)
        
        # Inverter brand selection
        st.subheader("🔌 Marca de Inversor")
        usar_marca_inversor = st.toggle(
            "Especificar marca de inversor",
            help="Selecciona una marca específica de inversor para la propuesta",
            key="usar_marca_inversor_desktop"
        )
        
        marca_inversor = "Automático"
        modelo_inversor = None
        if usar_marca_inversor:
            marcas_inversores = {
                "Huawei": {
                    "descripcion": "🇨🇳 Premium - Alta eficiencia, monitoreo avanzado",
                    "modelos": ["SUN2000-3KTL", "SUN2000-5KTL", "SUN2000-6KTL", "SUN2000-8KTL", "SUN2000-10KTL", 
                               "SUN2000-20KTL", "SUN2000-30KTL", "SUN2000-40KTL", "SUN2000-50KTL", "SUN2000-100KTL"],
                },
                "Deye": {
                    "descripcion": "🇨🇳 Híbrido - Compatible con baterías, backup",
                    "modelos": ["SUN-3K-SG04LP1", "SUN-5K-SG04LP1", "SUN-6K-SG04LP1", "SUN-8K-SG04LP1", 
                               "SUN-10K-SG04LP1", "SUN-12K-SG04LP3", "SUN-15K-SG04LP3", "SUN-20K-SG04LP3",
                               "SUN-25K-SG04LP3", "SUN-30K-SG04LP3", "SUN-50K-SG01HP3"],
                },
                "Growatt": {
                    "descripcion": "🇨🇳 Económico - Buena relación precio/calidad",
                    "modelos": ["MIN 3000TL-X", "MIN 5000TL-X", "MIN 6000TL-X", "MOD 8000TL3-X", "MOD 10000TL3-X",
                               "MOD 20000TL3-X", "MOD 30000TL3-X", "MAX 50KTL3", "MAX 100KTL3"],
                },
                "Solis": {
                    "descripcion": "🇨🇳 Económico - Opción accesible",
                    "modelos": ["S5-GR1P3K", "S5-GR1P5K", "S5-GR1P6K", "S5-GR3P8K", "S5-GR3P10K",
                               "S5-GC20K", "S5-GC30K", "S5-GC50K", "S5-GC100K"],
                },
                "Hoymiles": {
                    "descripcion": "🇨🇳 Microinversor - Ideal para sistemas ≤4kW",
                    "modelos": ["HMS-2000-4T"],
                },
            }
            
            marca_inversor = st.selectbox(
                "Marca del inversor",
                list(marcas_inversores.keys()),
                format_func=lambda x: f"{x} - {marcas_inversores[x]['descripcion']}",
                key="marca_inversor_desktop"
            )
            
            modelos_disponibles = marcas_inversores[marca_inversor]["modelos"]
            modelo_inversor = st.selectbox(
                "Modelo específico (opcional)",
                ["Automático según potencia"] + modelos_disponibles,
                key="modelo_inversor_desktop"
            )
            
            if modelo_inversor == "Automático según potencia":
                modelo_inversor = None
            
            st.info(f"📋 Se incluirá **{marca_inversor}** en la propuesta")

        # Smart Meter option
        st.subheader("📊 Opciones de Propuesta")
        incluir_smartmeter = st.toggle(
            "🔌 Incluir Smart Meter",
            help="Agrega una página de Smart Meter (medidor inteligente) a la propuesta",
            key="incluir_smartmeter_desktop"
        )
        if incluir_smartmeter:
            st.info("📊 Se incluirá la página de **Smart Meter** en la propuesta PDF")

        st.subheader("Parámetros Financieros")
        
        # Opción de precio manual para emergencias y descuentos
        precio_manual = st.toggle("💰 Precio Manual (Emergencias/Descuentos)", help="Activa esta opción para ingresar un precio personalizado del proyecto", key="precio_manual_desktop")
        
        if precio_manual:
            precio_manual_valor = st.number_input("Precio Manual del Proyecto (COP)", min_value=1000000, value=50000000, step=100000, help="Ingresa el precio total del proyecto en COP")
            st.warning("⚠️ **Modo Precio Manual Activado** - Se usará este valor en lugar del cálculo automático")
        else:
            precio_manual_valor = None
        
        # Horizonte de tiempo para análisis financiero
        horizonte_tiempo = st.selectbox(
            "📅 Horizonte de Análisis (años)", 
            [15, 20, 25, 30, 35, 40], 
            index=2,  # 25 años por defecto
            help="Selecciona el período de análisis para calcular TIR, VPN y Payback"
        )
        
        # Análisis de sensibilidad
        st.subheader("📊 Análisis de Sensibilidad")
        incluir_analisis_sensibilidad = st.toggle(
            "🔍 Incluir Análisis de Sensibilidad",
            help="Genera un análisis comparativo de TIR a 10 y 20 años con y sin financiación",
            key="analisis_sensibilidad_desktop"
        )
        
        if incluir_analisis_sensibilidad:
            st.info("📈 **Análisis de Sensibilidad**: Se calculará TIR a 10 y 20 años con y sin financiación para mostrar la robustez del proyecto")
        
        # Multi-project comparison
        st.subheader("🔄 Comparación de Tamaños")
        incluir_comparacion_tamanos = st.toggle(
            "🔄 Comparar diferentes tamaños de sistema",
            help="Compara 3 tamaños de sistema: 80%, 100% y 120% del tamaño calculado",
            key="comparacion_tamanos_desktop"
        )
        
        if incluir_comparacion_tamanos:
            st.info("📊 **Comparación de tamaños**: Se calcularán 3 escenarios para ayudar al cliente a elegir el tamaño óptimo")
        
        costkWh = st.number_input("Costo por kWh (COP)", min_value=200, value=850, step=10)
        index_input = st.slider("Indexación de energía (%)", 0.0, 20.0, 5.0, 0.5)
        dRate_input = st.slider("Tasa de descuento (%)", 0.0, 25.0, 10.0, 0.5)
        
        # Modo de conexión a red
        st.subheader("⚡ Modo de Conexión")
        modo_conexion = st.radio(
            "Selecciona el modo de compensación:",
            ["Net Metering (Intercambio 1:1)", "Net Billing (Excedentes a precio reducido)", "Autoconsumo (Sin venta de excedentes)"],
            index=1,
            help="Define cómo se compensan los excedentes de energía",
            key="modo_conexion_desktop"
        )
        
        # Precio de excedentes según modo
        if modo_conexion == "Net Metering (Intercambio 1:1)":
            precio_excedentes_input = costkWh  # Same as purchase price
            st.success(f"✅ Excedentes valorados al mismo precio de compra: ${costkWh:,} COP/kWh")
        elif modo_conexion == "Net Billing (Excedentes a precio reducido)":
            precio_excedentes_input = st.number_input(
                "Precio de venta de excedentes (COP/kWh)", 
                min_value=0, 
                max_value=costkWh, 
                value=min(350, costkWh),
                step=10,
                help="Precio al que la comercializadora compra los excedentes"
            )
            porcentaje_precio = (precio_excedentes_input / costkWh * 100) if costkWh > 0 else 0
            st.info(f"📊 Precio de excedentes: {porcentaje_precio:.0f}% del precio de compra")
        else:  # Autoconsumo
            precio_excedentes_input = 0
            st.warning("⚠️ Modo Autoconsumo: Los excedentes no generan ingresos. Considera dimensionar para cubrir exactamente el consumo.")
        
        st.subheader("Financiamiento")
        usa_financiamiento = st.toggle("Incluir financiamiento", key="financiamiento_desktop")
        perc_financiamiento, tasa_interes_input, plazo_credito_años = 0, 0, 0
        if usa_financiamiento:
            perc_financiamiento = st.slider("Porcentaje a financiar (%)", 0, 100, 70)
            tasa_interes_input = st.slider("Tasa de interés anual (%)", 0.0, 30.0, 15.0, 0.5)
            plazo_credito_años = st.number_input("Plazo del crédito (años)", 1, 20, 5)
        
        st.subheader("Almacenamiento (Baterías) - Modo Off-Grid")
        incluir_baterias = st.toggle("Añadir baterías (asumir sistema aislado)", key="baterias_desktop")
        dias_autonomia = 2
        if incluir_baterias:
            dias_autonomia = st.number_input("Días de autonomía deseados", 1, 7, 2, help="Días que el sistema debe soportar el consumo sin sol.")
            costo_kwh_bateria = st.number_input("Costo por kWh de batería (COP)", 100000, 5000000, 2500000, 100000)
            profundidad_descarga = st.slider("Profundidad de Descarga (DoD) (%)", 50.0, 100.0, 90.0, 0.5)
            eficiencia_bateria = st.slider("Eficiencia Carga/Descarga (%)", 80.0, 100.0, 95.0, 0.5)
        else:
            costo_kwh_bateria, profundidad_descarga, eficiencia_bateria = 0, 0, 0
        
        st.markdown("---")
        st.subheader("📊 Consideraciones Adicionales del Flujo de Caja")

        # Beneficios tributarios - permitir selección múltiple
        incluir_beneficios_tributarios = st.toggle(
            "💰 Incluir beneficios tributarios",
            help="Agrega beneficios fiscales al flujo de caja (puedes seleccionar ambos)",
            key="beneficios_tributarios_desktop"
        )

        incluir_deduccion_renta = False
        incluir_depreciacion_acelerada = False
        if incluir_beneficios_tributarios:
            st.info("💡 **Puedes seleccionar ambos beneficios tributarios simultáneamente**")
            incluir_deduccion_renta = st.checkbox(
                "Deducción de Renta (17.5% del CAPEX en año 2)",
                help="Aplica deducción de renta del 17.5% del valor del proyecto en el año 2",
                key="deduccion_renta_desktop"
            )
            incluir_depreciacion_acelerada = st.checkbox(
                "Depreciación Acelerada (33% del CAPEX años 1-3)",
                help="Aplica depreciación acelerada del 33% del valor del proyecto en los años 1, 2 y 3",
                key="depreciacion_acelerada_desktop"
            )

        # Demora de 6 meses
        demora_6_meses = st.toggle(
            "⏰ Proyecto con 6 meses de demora en conexión",
            help="Reduce los beneficios del año 1 a la mitad (6 meses de operación)",
            key="demora_6_meses_desktop"
        )

        st.markdown("---")
        st.subheader("🌱 Cálculo de Emisiones de Carbono")
        incluir_carbon = st.toggle(
            "🌱 Incluir análisis de sostenibilidad",
            help="Calcula las emisiones de CO2 evitadas y equivalencias ambientales",
            key="carbon_desktop"
        )
        if incluir_carbon:
            st.info("📊 **Análisis de Sostenibilidad Activado**: Se calcularán las emisiones de carbono evitadas, equivalencias ambientales y valor de certificación.")

        st.markdown("---")
        st.subheader("⚙️ Parámetros Avanzados")
        usar_params_personalizados = st.toggle(
            "⚙️ Personalizar parámetros de cálculo",
            help="Permite ajustar parámetros como precio de excedentes, tasa de degradación y mantenimiento",
            key="params_avanzados_desktop"
        )

        # Inicializar custom_params - siempre incluir precio de excedentes del modo de conexión
        custom_params = {"precio_excedentes": precio_excedentes_input}
        
        if usar_params_personalizados:
            st.info("💡 **Parámetros Avanzados**: Ajusta los valores según las condiciones específicas del proyecto")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                # Use net metering price as base, allow override
                custom_params["precio_excedentes"] = st.number_input(
                    "Precio venta excedentes (COP/kWh)",
                    min_value=0,
                    max_value=2000,
                    value=int(precio_excedentes_input),  # Use value from net metering selection
                    step=10,
                    help=f"Valor base del modo de conexión: ${precio_excedentes_input}. " + PARAM_DESCRIPTIONS["precio_excedentes"],
                    key="precio_excedentes_desktop"
                )

                tasa_deg_pct = st.number_input(
                    "Tasa degradación anual (%)",
                    min_value=0.01,
                    max_value=1.0,
                    value=DEFAULT_PARAMS["tasa_degradacion_anual"] * 100,
                    step=0.01,
                    format="%.2f",
                    help=PARAM_DESCRIPTIONS["tasa_degradacion_anual"],
                    key="tasa_degradacion_desktop"
                )
                custom_params["tasa_degradacion_anual"] = tasa_deg_pct / 100

            with col_p2:
                mant_pct = st.number_input(
                    "Mantenimiento (% del ahorro)",
                    min_value=0.0,
                    max_value=15.0,
                    value=DEFAULT_PARAMS["porcentaje_mantenimiento"] * 100,
                    step=0.5,
                    format="%.1f",
                    help=PARAM_DESCRIPTIONS["porcentaje_mantenimiento"],
                    key="mantenimiento_desktop"
                )
                custom_params["porcentaje_mantenimiento"] = mant_pct / 100

                pr_base = st.number_input(
                    "Performance Ratio base (%)",
                    min_value=50.0,
                    max_value=95.0,
                    value=DEFAULT_PARAMS["performance_ratio_base"] * 100,
                    step=1.0,
                    format="%.1f",
                    help=PARAM_DESCRIPTIONS["performance_ratio_base"],
                    key="pr_base_desktop"
                )
                custom_params["performance_ratio_base"] = pr_base / 100

            with st.expander("📋 Valores actuales vs defaults"):
                st.markdown(f"""
                | Parámetro | Valor actual | Default |
                |-----------|--------------|---------|
                | Precio excedentes | {custom_params['precio_excedentes']} COP/kWh | {DEFAULT_PARAMS['precio_excedentes']} COP/kWh |
                | Tasa degradación | {custom_params['tasa_degradacion_anual']*100:.2f}% | {DEFAULT_PARAMS['tasa_degradacion_anual']*100:.2f}% |
                | Mantenimiento | {custom_params['porcentaje_mantenimiento']*100:.1f}% | {DEFAULT_PARAMS['porcentaje_mantenimiento']*100:.1f}% |
                | Performance Ratio | {custom_params['performance_ratio_base']*100:.1f}% | {DEFAULT_PARAMS['performance_ratio_base']*100:.1f}% |
                """)

        st.markdown("---")
        st.subheader("💼 Resumen Financiero para Financieros")
        mostrar_resumen_financiero = st.toggle(
            "💼 Mostrar resumen financiero",
            help="Muestra métricas clave para análisis financiero: precio del proyecto, O&M anual, generación anual y degradación",
            key="resumen_financiero_desktop"
        )

        if mostrar_resumen_financiero:
            st.markdown("### 📊 Resumen Financiero para Análisis")

            # Calcular métricas financieras clave
            if opcion == "Por Consumo Mensual (kWh)":
                # Calcular tamaño del sistema
                HSP_aprox = 4.5
                n_aprox = 0.85
                Ratio = 1.2
                size_calc = round(Load * Ratio / (HSP_aprox * 30 * n_aprox), 2)
                quantity_calc = redondear_a_par(size_calc * 1000 / module)
                size_calc = round(quantity_calc * module / 1000, 2)
            else:
                size_calc = size
                quantity_calc = quantity

            # Calcular costo del proyecto
            costo_por_kwp = calcular_costo_por_kwp(size_calc)
            valor_proyecto_fv = costo_por_kwp * size_calc
            if cubierta.strip().upper() == "TEJA":
                valor_proyecto_fv *= 1.03

            # Costo de baterías si aplica
            costo_bateria = 0
            if incluir_baterias:
                consumo_diario = Load / 30
                capacidad_util_bateria = consumo_diario * dias_autonomia
                if profundidad_descarga > 0:
                    capacidad_nominal_bateria = capacidad_util_bateria / (profundidad_descarga / 100)
                costo_bateria = capacidad_nominal_bateria * costo_kwh_bateria

            valor_proyecto_total = math.ceil(valor_proyecto_fv + costo_bateria)

            # Calcular generación anual aproximada
            if hsp_mensual_calculado:
                hsp_promedio = sum(hsp_mensual_calculado) / len(hsp_mensual_calculado)
            else:
                hsp_promedio = HSP_POR_CIUDAD.get(ciudad_input, 4.5)

            # Generación anual inicial
            potencia_efectiva = min(size_calc, size_calc / 1.2)  # Aproximación
            # Use default efficiency if n_aprox is not available
            n_aprox = 0.85  # Default efficiency value
            generacion_anual_inicial = potencia_efectiva * hsp_promedio * 365 * n_aprox

            # O&M anual (2% del CAPEX)
            om_anual = valor_proyecto_total * 0.02  # 2% del valor total del proyecto

            # Degradación anual
            tasa_degradacion_anual = 0.1  # 0.1% por año

            # Mostrar métricas
            col1, col2 = st.columns(2)
            with col1:
                st.metric("💰 Precio del Proyecto", f"${valor_proyecto_total:,.0f} COP")
                st.metric("🔧 O&M Anual", f"${om_anual:,.0f} COP", help="2% del CAPEX (valor total del proyecto)")
                st.metric("⚡ Generación Anual Inicial", f"{generacion_anual_inicial:,.0f} kWh")

            with col2:
                st.metric("📉 Degradación Anual", f"{tasa_degradacion_anual:.1f}%", help="Pérdida de eficiencia por año")
                st.metric("🏗️ Tamaño del Sistema", f"{size_calc:.1f} kWp")
                st.metric("🔌 Potencia del Panel", f"{module} Wp")

            # Información adicional
            with st.expander("📋 Información Técnica para Financieros"):
                st.markdown(f"""
                **📊 Parámetros Técnicos:**
                - **Sistema**: {size_calc:.1f} kWp con {int(quantity_calc)} paneles
                - **HSP Promedio**: {hsp_promedio:.2f} kWh/m²/día
                - **Eficiencia del Sistema**: {n_aprox:.1%}
                - **Tipo de Cubierta**: {cubierta}
                - **Ubicación**: {ciudad_input}

                **💡 Notas para Análisis Financiero:**
                - El O&M incluye mantenimiento preventivo y correctivo
                - La degradación se aplica anualmente a la generación
                - Los cálculos son aproximados y pueden variar según condiciones reales
                """)

            # Opción para exportar como PDF simple
            if st.button("📄 Generar Resumen Financiero (PDF)", key="export_financial_pdf"):
                try:
                    from fpdf import FPDF
                    import datetime as dt

                    class FinancialSummaryPDF(FPDF):
                        def header(self):
                            self.set_font('Arial', 'B', 16)
                            self.cell(0, 10, 'Resumen Financiero para Análisis', 0, 1, 'C')
                            self.ln(10)

                        def footer(self):
                            self.set_y(-15)
                            self.set_font('Arial', 'I', 8)
                            self.cell(0, 10, f'Generado el {dt.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

                    pdf = FinancialSummaryPDF()
                    pdf.add_page()
                    pdf.set_font('Arial', '', 12)

                    # Contenido del PDF
                    pdf.cell(0, 10, f'Cliente: {nombre_cliente}', 0, 1)
                    pdf.cell(0, 10, f'Proyecto: {ubicacion or "Sin especificar"}', 0, 1)
                    pdf.cell(0, 10, f'Fecha: {fecha_propuesta.strftime("%d/%m/%Y")}', 0, 1)
                    pdf.ln(10)

                    pdf.set_font('Arial', 'B', 14)
                    pdf.cell(0, 10, 'Métricas Financieras Clave', 0, 1)
                    pdf.ln(5)

                    pdf.set_font('Arial', '', 12)
                    # Usar precio manual si está activado para el PDF también
                    precio_pdf = precio_manual_valor if precio_manual and precio_manual_valor else valor_proyecto_total
                    pdf.cell(0, 8, f'Precio del Proyecto: ${precio_pdf:,.0f} COP', 0, 1)
                    pdf.cell(0, 8, f'O&M Anual: ${om_anual:,.0f} COP', 0, 1)
                    pdf.cell(0, 8, f'Generación Anual Inicial: {generacion_anual_inicial:,.0f} kWh', 0, 1)
                    pdf.cell(0, 8, f'Degradación Anual: {tasa_degradacion_anual:.1f}%', 0, 1)
                    pdf.ln(10)

                    pdf.set_font('Arial', 'B', 14)
                    pdf.cell(0, 10, 'Parámetros Técnicos', 0, 1)
                    pdf.ln(5)

                    pdf.set_font('Arial', '', 12)
                    pdf.cell(0, 8, f'Tamaño del Sistema: {size_calc:.1f} kWp', 0, 1)
                    pdf.cell(0, 8, f'Cantidad de Paneles: {int(quantity_calc)}', 0, 1)
                    pdf.cell(0, 8, f'Potencia por Panel: {module} Wp', 0, 1)
                    pdf.cell(0, 8, f'HSP Promedio: {hsp_promedio:.2f} kWh/m²/día', 0, 1)
                    pdf.cell(0, 8, f'Tipo de Cubierta: {cubierta}', 0, 1)
                    pdf.cell(0, 8, f'Ubicación: {ciudad_input}', 0, 1)

                    pdf_bytes = bytes(pdf.output(dest='S'))

                    st.download_button(
                        label="📥 Descargar Resumen Financiero (PDF)",
                        data=pdf_bytes,
                        file_name=f"Resumen_Financiero_{nombre_cliente}_{dt.datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Error generando PDF financiero: {e}")

        st.markdown("---")
        st.subheader("🔌 Cotizador de Cargadores")
        ev_nombre = st.text_input("Cliente y Lugar (Cargadores)", "")
        ev_dist = st.number_input("Distancia parqueadero a subestación (m)", min_value=1.0, value=10.0, step=1.0)
        
        # Opción de precio manual para cargadores
        ev_precio_manual = st.checkbox("Precio Manual (Cargadores)", key="ev_precio_manual_desktop")
        ev_precio_valor = None
        if ev_precio_manual:
            ev_precio_valor = st.number_input("Precio Manual del Cargador (COP)", min_value=100000, value=2500000, step=50000, key="ev_precio_valor_desktop")

        if st.button("Generar PDF Cargadores", use_container_width=True, key="ev_gen_desktop"):
            try:
                ev_pdf, ev_desglose = generar_pdf_cargadores(ev_nombre or "Cliente", ev_dist, ev_precio_valor)
                st.success("✅ Cotización de Cargadores generada")
                col_ev1, col_ev2 = st.columns(2)
                with col_ev1:
                    st.metric("Costo Base", formatear_moneda(ev_desglose.get("Costo Base", 0)))
                    st.metric("IVA (19%)", formatear_moneda(ev_desglose.get("IVA", 0)))
                with col_ev2:
                    st.metric("Diseño (35%)", formatear_moneda(ev_desglose.get("Diseño", 0)))
                    st.metric("Materiales (65%)", formatear_moneda(ev_desglose.get("Materiales", 0)))
                st.metric("Costo Total", formatear_moneda(ev_desglose.get("Costo Total", 0)))
                st.download_button("📥 Descargar PDF de Cargadores", data=ev_pdf, file_name=f"Propuesta Mirac {ev_nombre or 'Cliente'}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as ev_ex:
                st.error(f"❌ Error generando la cotización de cargadores: {ev_ex}")


    # ==============================================================================
    # LÓGICA DE CÁLCULO Y VISUALIZACIÓN
    # ==============================================================================
    if st.button("   Calcular y Generar Reporte", use_container_width=True):
        # Validar datos de entrada
        errores_validacion = validar_datos_entrada(Load, size, quantity, cubierta, clima, costkWh, module)
        
        if errores_validacion:
            st.error("❌ Errores de validación encontrados:")
            for error in errores_validacion:
                st.error(f"• {error}")
        else:
            with st.status("Generando propuesta...", expanded=True) as status:
                status.update(label="📊 Calculando dimensionamiento y análisis financiero...", state="running")
                nombre_proyecto = f"FV{str(datetime.datetime.now().year)[-2:]}{numero_proyecto_del_año:03d} - {nombre_cliente}" + (f" - {ubicacion}" if ubicacion else "")
                
                valor_proyecto_total, size_calc, monto_a_financiar, cuota_mensual_credito, \
                desembolso_inicial_cliente, fcl, trees, monthly_generation, valor_presente, \
                tasa_interna, cantidad_calc, life, recomendacion_inversor, lcoe, n_final, hsp_mensual_final, \
                potencia_ac_inversor, ahorro_año1, area_requerida, capacidad_nominal_bateria, carbon_data = \
                    cotizacion(Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100, costkWh, module,
                                 ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                                 perc_financiamiento=perc_financiamiento, tasa_interes_credito=tasa_interes_input / 100,
                                 plazo_credito_años=plazo_credito_años,
                                 incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                                 profundidad_descarga=profundidad_descarga / 100,
                                 eficiencia_bateria=eficiencia_bateria / 100, dias_autonomia=dias_autonomia,
                                 horizonte_tiempo=horizonte_tiempo, incluir_carbon=incluir_carbon,
                                 incluir_beneficios_tributarios=incluir_beneficios_tributarios,
                                 incluir_deduccion_renta=incluir_deduccion_renta,
                                 incluir_depreciacion_acelerada=incluir_depreciacion_acelerada,
                                 demora_6_meses=demora_6_meses,
                                 custom_params=custom_params)
                
                # Aplicar precio manual si está activado
                val_total = valor_proyecto_total
                if precio_manual and precio_manual_valor:
                    val_total = precio_manual_valor
                    # Recalcular financiamiento con el precio manual
                    monto_a_financiar = val_total * (perc_financiamiento / 100)
                    monto_a_financiar = math.ceil(monto_a_financiar)

                    cuota_mensual_credito = 0
                    if monto_a_financiar > 0 and plazo_credito_años > 0 and tasa_interes_input > 0:
                        tasa_mensual_credito = (tasa_interes_input / 100) / 12
                        num_pagos_credito = plazo_credito_años * 12
                        cuota_mensual_credito = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_a_financiar))
                        cuota_mensual_credito = math.ceil(cuota_mensual_credito)

                    desembolso_inicial_cliente = val_total - monto_a_financiar

                    # RECALCULAR FLUJO DE CAJA COMPLETO con el precio manual
                    # Obtener parámetros configurables
                    precio_excedentes_calc = get_param("precio_excedentes", custom_params)
                    porcentaje_mant_calc = get_param("porcentaje_mantenimiento", custom_params)

                    fcl = []  # Reiniciar flujo de caja
                    for i in range(life):
                        # Calcular ahorro anual para cada año
                        ahorro_anual_total = 0
                        if incluir_baterias:
                            ahorro_anual_total = (Load * 12) * costkWh
                        else:  # Lógica On-Grid
                            for gen_mes in monthly_generation:
                                consumo_mes = Load
                                if gen_mes >= consumo_mes:
                                    ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * precio_excedentes_calc)
                                else:
                                    ahorro_mes = gen_mes * costkWh
                                ahorro_anual_total += ahorro_mes

                        # Aplicar indexación
                        ahorro_anual_indexado = ahorro_anual_total * ((1 + index_input / 100) ** i)
                        if i == 0:
                            ahorro_año1 = ahorro_anual_total

                        # Mantenimiento anual
                        mantenimiento_anual = porcentaje_mant_calc * ahorro_anual_indexado

                        # Cuotas anuales del crédito
                        cuotas_anuales_credito = 0
                        if i < plazo_credito_años:
                            cuotas_anuales_credito = cuota_mensual_credito * 12

                        # Flujo anual
                        flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
                        fcl.append(flujo_anual)

                    # Insertar desembolso inicial al inicio
                    fcl.insert(0, -desembolso_inicial_cliente)

                    # Recalcular métricas financieras
                    valor_presente = npf.npv(dRate_input / 100, fcl)
                    tasa_interna = npf.irr(fcl)
                
                generacion_promedio_mensual = sum(monthly_generation) / len(monthly_generation) if monthly_generation else 0
                payback_simple = next((i for i, x in enumerate(np.cumsum(fcl)) if x >= 0), None)
                payback_exacto = None
                if payback_simple is not None:
                    if payback_simple > 0 and (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1]) != 0:
                        payback_exacto = (payback_simple - 1) + abs(np.cumsum(fcl)[payback_simple-1]) / (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1])
                    else:
                        payback_exacto = float(payback_simple)

                # Análisis de Sensibilidad
                analisis_sensibilidad = None
                if incluir_analisis_sensibilidad:
                    analisis_sensibilidad = calcular_analisis_sensibilidad(
                        Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100,
                        costkWh, module, ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                        incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                        profundidad_descarga=profundidad_descarga / 100, eficiencia_bateria=eficiencia_bateria / 100,
                        dias_autonomia=dias_autonomia, perc_financiamiento=perc_financiamiento,
                        tasa_interes_credito=tasa_interes_input / 100, plazo_credito_años=plazo_credito_años,
                        precio_manual=precio_manual_valor, horizonte_base=horizonte_tiempo,
                        incluir_beneficios_tributarios=incluir_beneficios_tributarios,
                        incluir_deduccion_renta=incluir_deduccion_renta,
                        incluir_depreciacion_acelerada=incluir_depreciacion_acelerada,
                        custom_params=custom_params
                    )

                # Comparación de tamaños de sistema
                comparacion_tamanos = None
                if incluir_comparacion_tamanos:
                    comparacion_tamanos = {}
                    escalas = [('Económico (80%)', 0.8), ('Recomendado (100%)', 1.0), ('Premium (120%)', 1.2)]
                    
                    for nombre_escala, factor in escalas:
                        size_escala = round(size * factor, 2)
                        quantity_escala = redondear_a_par(size_escala * 1000 / module)
                        size_escala = round(quantity_escala * module / 1000, 2)
                        
                        try:
                            val_proy, size_c, _, _, desemb, fcl_c, _, monthly_gen, vpn_c, tir_c, \
                            qty_c, _, inv_rec, _, _, _, pot_ac, ahorro_c, area_c, _, _ = \
                                cotizacion(Load, size_escala, quantity_escala, cubierta, clima, 
                                          index_input / 100, dRate_input / 100, costkWh, module,
                                          ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                                          perc_financiamiento=0, horizonte_tiempo=horizonte_tiempo,
                                          incluir_carbon=False, custom_params=custom_params)
                            
                            # Calculate payback
                            cumsum_fcl = np.cumsum(fcl_c)
                            pb = next((i for i, x in enumerate(cumsum_fcl) if x >= 0), None)
                            
                            gen_anual = sum(monthly_gen) if monthly_gen else 0
                            cobertura = (gen_anual / (Load * 12) * 100) if Load > 0 else 0
                            
                            comparacion_tamanos[nombre_escala] = {
                                'size_kwp': size_escala,
                                'paneles': quantity_escala,
                                'valor': val_proy,
                                'tir': tir_c,
                                'payback': pb,
                                'ahorro_ano1': ahorro_c,
                                'generacion_anual': gen_anual,
                                'cobertura': min(cobertura, 100),
                                'inversor': inv_rec
                            }
                        except Exception as e:
                            comparacion_tamanos[nombre_escala] = {'error': str(e)}

                # Lista de Materiales
                lista_materiales = calcular_lista_materiales(cantidad_calc, cubierta, module, recomendacion_inversor)

                status.update(label="📈 Generando gráficas...", state="running")
                # --- GENERAR GRÁFICA PARA PDF ---
                generar_grafica_generacion(monthly_generation, Load, incluir_baterias)

                # Generación de Documentos
                lat, lon = None, None
                if st.session_state.map_state.get("marker"):
                    lat, lon = st.session_state.map_state["marker"]
                    api_key = os.environ.get("Maps_API_KEY") 
                    if api_key and gmaps:
                        get_static_map_image(lat, lon, api_key)

                presupuesto_equipos = valor_proyecto_total * (PROMEDIOS_COSTO['Equipos'] / 100)
                presupuesto_materiales = valor_proyecto_total * (PROMEDIOS_COSTO['Materiales'] / 100)
                provision_iva_guia = valor_proyecto_total * (PROMEDIOS_COSTO['IVA (Impuestos)'] / 100)
                ganancia_estimada_guia = valor_proyecto_total * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
                valor_total_redondeado = math.ceil(valor_proyecto_total / 100) * 100
                valor_iva_redondeado = math.ceil(provision_iva_guia / 100) * 100
                valor_sistema_sin_iva_redondeado = valor_total_redondeado - valor_iva_redondeado

                valor_pdf = precio_manual_valor if precio_manual and precio_manual_valor else valor_proyecto_total
                valor_pdf_redondeado = math.ceil(valor_pdf / 100) * 100
                presupuesto_materiales_pdf = valor_pdf_redondeado * (PROMEDIOS_COSTO['Materiales'] / 100)
                ganancia_estimada_pdf = valor_pdf_redondeado * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
                valor_iva_pdf = math.ceil(((presupuesto_materiales_pdf + ganancia_estimada_pdf) * 0.19)/100)*100
                valor_sistema_sin_iva_pdf = valor_pdf_redondeado - valor_iva_pdf

                arboles_equivalentes_desktop = 0
                co2_evitado_tons_desktop = 0.0
                if incluir_carbon and carbon_data:
                    arboles_equivalentes_desktop = carbon_data.get('trees_saved_per_year', 0)
                    co2_evitado_tons_desktop = carbon_data.get('annual_co2_avoided_tons', 0.0)
                
                # Construir referencia del inversor (con marca/modelo si está especificado)
                referencia_inversor_pdf = recomendacion_inversor
                if marca_inversor and marca_inversor != "Automático":
                    if modelo_inversor:
                        referencia_inversor_pdf = f"{marca_inversor} {modelo_inversor}"
                    else:
                        referencia_inversor_pdf = f"{marca_inversor} ({recomendacion_inversor})"
                
                datos_para_pdf = {
                    "Nombre del Proyecto": nombre_proyecto, "Cliente": nombre_cliente,
                    "Valor Total del Proyecto (COP)": f"${valor_pdf_redondeado:,.0f}",
                    "Valor Sistema FV (sin IVA)": f"${valor_sistema_sin_iva_pdf:,.0f}",
                    "Valor IVA": f"${valor_iva_pdf:,.0f}",
                    "Tamano del Sistema (kWp)": f"{size:.1f}",
                    "Cantidad de Paneles": f"{int(quantity)} de {int(module)}W","Área Requerida Aprox. (m²)": f"{area_requerida}",
                    "Inversor Recomendado": f"{recomendacion_inversor}",
                    "Referencia Inversor": referencia_inversor_pdf,
                    "Generacion Promedio Mensual (kWh)": f"{generacion_promedio_mensual:,.1f}",
                    "Ahorro Estimado Primer Ano (COP)": f"{ahorro_año1:,.2f}",
                    "TIR (Tasa Interna de Retorno)": f"{tasa_interna:.1%}",
                    "VPN (Valor Presente Neto) (COP)": f"{valor_presente:,.2f}",
                    "Periodo de Retorno (anos)": f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A",
                    "Tipo de Cubierta": cubierta,
                    "Potencia de Paneles": f"{int(module)}",
                    "Potencia AC Inversor": f"{potencia_ac_inversor}",
                    "Árboles Equivalentes Ahorrados": str(int(round(arboles_equivalentes_desktop))),
                    "CO2 Evitado Anual (Toneladas)": f"{co2_evitado_tons_desktop:.2f}",
                }
                
                om_anual = valor_pdf_redondeado * 0.02
                datos_para_pdf["O&M (Operation & Maintenance)"] = f"${om_anual:,.0f}"
                
                monto_a_financiar_pdf = 0
                desembolso_inicial_pdf = 0
                cuota_mensual_pdf = 0

                if usa_financiamiento:
                    if precio_manual and precio_manual_valor:
                        monto_a_financiar_pdf = valor_pdf_redondeado * (perc_financiamiento / 100)
                        monto_a_financiar_pdf = math.ceil(monto_a_financiar_pdf)
                        desembolso_inicial_pdf = valor_pdf_redondeado - monto_a_financiar_pdf

                        if monto_a_financiar_pdf > 0 and plazo_credito_años > 0 and tasa_interes_input > 0:
                            tasa_mensual_pdf = (tasa_interes_input / 100) / 12
                            num_pagos_pdf = plazo_credito_años * 12
                            cuota_mensual_pdf = abs(npf.pmt(tasa_mensual_pdf, num_pagos_pdf, -monto_a_financiar_pdf))
                            cuota_mensual_pdf = math.ceil(cuota_mensual_pdf)
                        else:
                            cuota_mensual_pdf = 0
                    else:
                        monto_a_financiar_pdf = math.ceil(monto_a_financiar)
                        desembolso_inicial_pdf = math.ceil(desembolso_inicial_cliente)
                        cuota_mensual_pdf = cuota_mensual_credito

                    datos_para_pdf["--- Detalles de Financiamiento ---"] = ""
                    datos_para_pdf["Monto a Financiar (COP)"] = f"{monto_a_financiar_pdf:,.0f}"
                    datos_para_pdf["Cuota Mensual del Credito (COP)"] = f"{cuota_mensual_pdf:,.0f}"
                    datos_para_pdf["Desembolso Inicial (COP)"] = f"{desembolso_inicial_pdf:,.0f}"
                    datos_para_pdf["Plazo del Crédito"] = str(plazo_credito_años * 12)
                
                datos_para_contrato = datos_para_pdf.copy()
                datos_para_contrato['Fecha de la Propuesta'] = fecha_propuesta

                status.update(label="📄 Generando PDF de propuesta...", state="running")
                pdf = PropuestaPDF(
                    client_name=nombre_cliente, 
                    project_name=nombre_proyecto,
                    documento=documento_cliente,
                    direccion=direccion_proyecto,
                    fecha=fecha_propuesta 
                )

                pdf_bytes = pdf.generar(datos_para_pdf, usa_financiamiento, lat, lon, incluir_smartmeter=incluir_smartmeter)
                nombre_pdf_final = f"{nombre_proyecto}.pdf"
                
                status.update(label="📝 Generando contrato...", state="running")
                nombre_contrato_final = f"Contrato - {nombre_proyecto}.docx"
                contrato_bytes = generar_contrato_docx(datos_para_contrato)

                link_carpeta = None
                if drive_service:
                    status.update(label="☁️ Subiendo archivos a Google Drive...", state="running")
                    link_carpeta = gestionar_creacion_drive(
                        drive_service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf_final,contrato_bytes, nombre_contrato_final
                    )

                # CSV
                status.update(label="📊 Generando archivo de flujo de caja...", state="running")
                csv_content = None
                nombre_csv = f"Flujo_Caja_Detallado_{nombre_proyecto}.csv"
                try:
                    csv_content = generar_csv_flujo_caja_detallado(
                        Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100, costkWh, module,
                        ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                        perc_financiamiento=perc_financiamiento, tasa_interes_credito=tasa_interes_input / 100,
                        plazo_credito_años=plazo_credito_años, incluir_baterias=incluir_baterias,
                        costo_kwh_bateria=costo_kwh_bateria, profundidad_descarga=profundidad_descarga / 100,
                        eficiencia_bateria=eficiencia_bateria / 100, dias_autonomia=dias_autonomia,
                        horizonte_tiempo=horizonte_tiempo, precio_manual=precio_manual_valor,
                        fcl=fcl, monthly_generation=monthly_generation,
                        incluir_beneficios_tributarios=incluir_beneficios_tributarios,
                        incluir_deduccion_renta=incluir_deduccion_renta,
                        incluir_depreciacion_acelerada=incluir_depreciacion_acelerada
                    )
                    
                    if drive_service:
                        # Lógica simplificada para guardar en Drive si es necesario
                        pass 

                except Exception as csv_error:
                    st.warning(f"No se pudo generar el CSV: {csv_error}")

                # Notion
                status.update(label="📋 Registrando en Notion CRM...", state="running")
                agregado_notion, msg_notion = agregar_cliente_a_notion_crm(
                    nombre=nombre_cliente,
                    documento=documento_cliente,
                    direccion=direccion_proyecto,
                    proyecto=nombre_proyecto,
                    fecha=fecha_propuesta,
                    estado="En conversaciones"
                )

                # Guardar TODO en session_state
                st.session_state.desktop_results = {
                    'nombre_proyecto': nombre_proyecto,
                    'valor_proyecto_total': valor_proyecto_total,
                    'val_total': val_total,
                    'tasa_interna': tasa_interna,
                    'payback_exacto': payback_exacto,
                    'capacidad_nominal_bateria': capacidad_nominal_bateria,
                    'ahorro_año1': ahorro_año1,
                    'carbon_data': carbon_data,
                    'analisis_sensibilidad': analisis_sensibilidad,
                    'comparacion_tamanos': comparacion_tamanos,
                    'lista_materiales': lista_materiales,
                    'pdf_bytes': pdf_bytes,
                    'nombre_pdf_final': nombre_pdf_final,
                    'contrato_bytes': contrato_bytes,
                    'nombre_contrato_final': nombre_contrato_final,
                    'link_carpeta': link_carpeta,
                    'csv_content': csv_content,
                    'nombre_csv': nombre_csv,
                    'agregado_notion': agregado_notion,
                    'msg_notion': msg_notion,
                    'fcl': fcl,
                    'life': life,
                    'monthly_generation': monthly_generation,
                    'incluir_baterias': incluir_baterias,
                    'Load': Load,
                    'horizonte_tiempo': horizonte_tiempo,
                    'valor_presente': valor_presente,
                    'recomendacion_inversor': recomendacion_inversor,
                    'lcoe': lcoe,
                    'n_final': n_final,
                    'hsp_mensual_final': hsp_mensual_final,
                    'potencia_ac_inversor': potencia_ac_inversor,
                    'area_requerida': area_requerida,
                    'generacion_promedio_mensual': generacion_promedio_mensual,
                    'precio_manual': precio_manual,
                    'precio_manual_valor': precio_manual_valor,
                    'PROMEDIOS_COSTO': PROMEDIOS_COSTO,
                    'size': size,
                    'quantity': quantity,
                    'module': module,
                    'cubierta': cubierta,
                    'lat': lat,
                    'lon': lon,
                    'marca_inversor': marca_inversor,
                    'modelo_inversor': modelo_inversor,
                    'incluir_smartmeter': incluir_smartmeter,
                    # Datos adicionales para historial/duplicar
                    'nombre_cliente': nombre_cliente,
                    'documento_cliente': documento_cliente,
                    'direccion_proyecto': direccion_proyecto,
                    'fecha_propuesta': fecha_propuesta,
                    'clima': clima,
                    'costkWh': costkWh,
                    'index_input': index_input,
                    'dRate_input': dRate_input,
                }
                
                # === GUARDAR EN HISTORIAL ===
                cotizacion_historial = {
                    'id': datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                    'fecha': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
                    'nombre_proyecto': nombre_proyecto,
                    'nombre_cliente': nombre_cliente,
                    'size': size,
                    'quantity': int(quantity),
                    'module': module,
                    'val_total': val_total,
                    'tir': tasa_interna,
                    'payback': payback_exacto,
                    'Load': Load,
                    'cubierta': cubierta,
                    'clima': clima,
                    'costkWh': costkWh,
                    'index_input': index_input,
                    'dRate_input': dRate_input,
                    'horizonte_tiempo': horizonte_tiempo,
                    'documento_cliente': documento_cliente,
                    'direccion_proyecto': direccion_proyecto,
                    'lat': lat,
                    'lon': lon,
                    'marca_inversor': marca_inversor,
                    'modelo_inversor': modelo_inversor,
                    'incluir_smartmeter': incluir_smartmeter,
                }
                
                # Agregar al inicio del historial y mantener máximo 10
                st.session_state.historial_cotizaciones.insert(0, cotizacion_historial)
                if len(st.session_state.historial_cotizaciones) > 10:
                    st.session_state.historial_cotizaciones = st.session_state.historial_cotizaciones[:10]
                
                status.update(label="✅ ¡Propuesta generada exitosamente!", state="complete", expanded=False)
                st.rerun()

    # --- RENDERIZADO DE RESULTADOS ---
    if st.session_state.desktop_results:
        res = st.session_state.desktop_results
        
        st.success(f"Proyecto Generado: {res['nombre_proyecto']}")
        
        # === BOTONES DE ACCIÓN RÁPIDA ===
        col_action1, col_action2, col_action3 = st.columns([1, 1, 2])
        with col_action1:
            if st.button("➕ Nueva Cotización", use_container_width=True, type="primary"):
                # Limpiar resultados para empezar de nuevo
                st.session_state.desktop_results = None
                st.rerun()
        with col_action2:
            if st.button("🔄 Duplicar y Ajustar", use_container_width=True):
                # Guardar datos para duplicar en el próximo ciclo
                st.session_state.duplicar_datos = {
                    'nombre_cliente': res.get('nombre_cliente', '') + " (copia)",
                    'documento_cliente': res.get('documento_cliente', ''),
                    'direccion_proyecto': res.get('direccion_proyecto', ''),
                    'Load': res.get('Load', 700),
                    'costkWh': res.get('costkWh', 850),
                    'index_input': res.get('index_input', 5.0),
                    'dRate_input': res.get('dRate_input', 10.0),
                    'horizonte_tiempo': res.get('horizonte_tiempo', 25),
                    'lat': res.get('lat'),
                    'lon': res.get('lon'),
                }
                st.session_state.desktop_results = None
                st.rerun()
        
        if res['precio_manual'] and res['precio_manual_valor']:
             st.success(f"✅ **Precio Manual Aplicado**: ${res['val_total']:,.0f} COP")
             st.info("🔄 **Flujo de caja recalculado** con el precio manual para métricas correctas")

        st.header("Resultados de la Propuesta")
        st.info(f"📅 **Análisis financiero a {res['horizonte_tiempo']} años** - TIR, VPN y Payback calculados para este período")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valor del Proyecto", f"${res['val_total']:,.0f}")
        col2.metric("TIR", f"{res['tasa_interna']:.1%}")
        col3.metric("Payback (años)", f"{res['payback_exacto']:.2f}" if res['payback_exacto'] is not None else "N/A")
        if res['incluir_baterias']:
            col4.metric("Batería Recomendada", f"{res['capacidad_nominal_bateria']:.1f} kWh")
        else:
            col4.metric("Ahorro Año 1", f"${res['ahorro_año1']:,.0f}")

        # Inverter brand info
        if res.get('marca_inversor') and res['marca_inversor'] != "Automático":
            inversor_display = f"{res['marca_inversor']}"
            if res.get('modelo_inversor'):
                inversor_display += f" - {res['modelo_inversor']}"
            st.info(f"🔌 **Marca de Inversor**: {inversor_display} | **Configuración recomendada**: {res['recomendacion_inversor']}")
        else:
            st.info(f"🔌 **Inversor recomendado**: {res['recomendacion_inversor']}")

        # Carbono
        if incluir_carbon and res['carbon_data'] and 'annual_co2_avoided_tons' in res['carbon_data']:
            cd = res['carbon_data']
            st.markdown("---")
            st.header("🌱 Impacto Ambiental y Sostenibilidad")
            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            col_c1.metric("CO2 Evitado Anual", f"{cd['annual_co2_avoided_tons']:.1f} ton")
            col_c2.metric("Árboles Salvados", f"{cd['trees_saved_per_year']:.0f}")
            col_c3.metric("Valor Carbono", f"${cd['annual_certification_value_cop']:,.0f}")
            col_c4.metric("Autos Equivalentes", f"{cd['cars_off_road_per_year']:.1f}")
            
            with st.expander("📊 Ver más equivalencias ambientales"):
                st.write(f"• **Vuelos evitados**: {cd['flights_avoided_per_year']:.0f}")
                st.write(f"• **Botellas de plástico**: {cd['plastic_bottles_avoided_per_year']:,.0f}")
                st.write(f"• **Cargas de celular**: {cd['smartphone_charges_avoided_per_year']:,.0f}")

        # Análisis de Sensibilidad
        if incluir_analisis_sensibilidad and res['analisis_sensibilidad']:
            st.header("📊 Análisis de Sensibilidad")
            st.info("🔍 **Análisis comparativo** de TIR a 10 y 20 años")
            
            datos_tabla = []
            for escenario, datos in res['analisis_sensibilidad'].items():
                datos_tabla.append({
                    "Escenario": escenario,
                    "TIR": f"{datos['tir']:.1%}" if datos['tir'] is not None else "N/A",
                    "VPN (COP)": f"${datos['vpn']:,.0f}" if datos['vpn'] is not None else "N/A",
                    "Payback (años)": f"{datos['payback']:.2f}" if datos['payback'] is not None else "N/A",
                    "Desembolso Inicial": f"${datos['desembolso_inicial']:,.0f}",
                    "Cuota Mensual": f"${datos['cuota_mensual']:,.0f}" if datos['cuota_mensual'] > 0 else "N/A"
                })
            st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)

        # Comparación de Tamaños de Sistema
        if res.get('comparacion_tamanos'):
            st.header("🔄 Comparación de Tamaños de Sistema")
            st.info("📊 **Compara diferentes opciones** para encontrar el tamaño ideal para tu cliente")
            
            # Crear tabla de comparación
            comp_data = []
            for nombre, datos in res['comparacion_tamanos'].items():
                if 'error' not in datos:
                    comp_data.append({
                        "Opción": nombre,
                        "Tamaño (kWp)": f"{datos['size_kwp']:.1f}",
                        "Paneles": int(datos['paneles']),
                        "Inversión (COP)": f"${datos['valor']:,.0f}",
                        "TIR": f"{datos['tir']:.1%}" if datos['tir'] else "N/A",
                        "Payback (años)": f"{datos['payback']}" if datos['payback'] else "N/A",
                        "Ahorro Año 1": f"${datos['ahorro_ano1']:,.0f}",
                        "Cobertura": f"{datos['cobertura']:.0f}%",
                    })
            
            if comp_data:
                df_comp = pd.DataFrame(comp_data)
                
                # Highlight the recommended option with brand color
                def highlight_recommended(row):
                    if 'Recomendado' in row['Opción']:
                        return ['background-color: #FA323F; color: white; font-weight: bold'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(
                    df_comp.style.apply(highlight_recommended, axis=1),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Visual comparison with metrics
                st.subheader("📈 Resumen Visual")
                cols = st.columns(len(comp_data))
                for i, (col, datos) in enumerate(zip(cols, res['comparacion_tamanos'].values())):
                    if 'error' not in datos:
                        with col:
                            nombre = list(res['comparacion_tamanos'].keys())[i]
                            if 'Recomendado' in nombre:
                                st.success(f"**{nombre}**")
                            else:
                                st.info(f"**{nombre}**")
                            st.metric("Inversión", f"${datos['valor']:,.0f}")
                            st.metric("TIR", f"{datos['tir']:.1%}" if datos['tir'] else "N/A")
                            st.metric("Cobertura", f"{datos['cobertura']:.0f}%")

        # Presupuesto Guía
        with st.expander("📊 Ver Análisis Financiero Interno (Presupuesto Guía)"):
            st.subheader("Desglose Basado en Promedios Históricos")
            prom = res['PROMEDIOS_COSTO']
            val_base = res['val_total']
            p_equipos = val_base * (prom['Equipos'] / 100)
            p_materiales = val_base * (prom['Materiales'] / 100)
            ganancia = val_base * (prom['Margen (Ganancia)'] / 100)
            iva = (p_materiales + ganancia) * 0.19
            
            col_guia1, col_guia2, col_guia3, col_guia4 = st.columns(4)
            col_guia1.metric(f"Equipos ({prom['Equipos']:.2f}%)", f"${math.ceil(p_equipos):,.0f}")
            col_guia2.metric(f"Materiales ({prom['Materiales']:.2f}%)", f"${math.ceil(p_materiales):,.0f}")
            col_guia3.metric(f"Provisión IVA", f"${math.ceil(iva):,.0f}")
            col_guia4.metric(f"Ganancia ({prom['Margen (Ganancia)']:.2f}%)", f"${math.ceil(ganancia):,.0f}")

        # Lista Materiales
        with st.expander("📋 Ver Lista de Materiales (Referencia Interna)"):
            if res['lista_materiales']:
                df_mat = pd.DataFrame(res['lista_materiales'].items(), columns=['Material', 'Cantidad Estimada'])
                df_mat.index = df_mat.index + 1
                st.table(df_mat)
            else:
                st.write("No se calcularon materiales.")

        # Gráficos
        st.header("Análisis Gráfico")
        if res['lat'] and res['lon']:
             # Mostrar mapa estático si existe (se generó en el cálculo)
             if os.path.exists("static_map.png"):
                 st.image("static_map.png", caption="Ubicación del Proyecto")

        if os.path.exists("grafica_generacion.png"):
            st.image("grafica_generacion.png", caption="Generación Mensual Estimada", use_container_width=True)
        else:
            st.warning("No se encontró la gráfica de generación.")

        fig2, ax2 = plt.subplots(figsize=(10, 5))
        fcl_acumulado = np.cumsum(res['fcl'])
        años = np.arange(0, res['life'] + 1)
        ax2.plot(años, fcl_acumulado, marker='o', linestyle='-', color='green', label='Flujo de Caja Acumulado')
        ax2.plot(0, fcl_acumulado[0], marker='X', markersize=10, color='red', label='Desembolso Inicial (Año 0)')
        if res['payback_exacto'] is not None: ax2.axvline(x=res['payback_exacto'], color='red', linestyle='--', label=f'Payback Simple: {res["payback_exacto"]:.2f} años')
        ax2.axhline(0, color='grey', linestyle='--', linewidth=0.8)
        ax2.set_title("Flujo de Caja Acumulado y Período de Retorno", fontweight="bold"); ax2.legend()
        st.pyplot(fig2)

        # Vista Previa del PDF
        st.subheader("👁️ Vista Previa de la Propuesta")
        with st.expander("Ver PDF de la propuesta", expanded=False):
            try:
                from streamlit_pdf_viewer import pdf_viewer
                pdf_viewer(res['pdf_bytes'], width=700, height=800)
            except ImportError:
                # Fallback si no está instalado streamlit-pdf-viewer
                pdf_base64 = base64.b64encode(res['pdf_bytes']).decode('utf-8')
                pdf_display = f'''
                <embed 
                    src="data:application/pdf;base64,{pdf_base64}" 
                    width="100%" 
                    height="600px" 
                    type="application/pdf"
                    style="border: 1px solid #333; border-radius: 5px;">
                </embed>
                '''
                st.markdown(pdf_display, unsafe_allow_html=True)
                st.caption("💡 Instala `streamlit-pdf-viewer` para mejor visualización: `pip install streamlit-pdf-viewer`")
        
        # Descargas y Links
        st.subheader("📁 Descargas y Enlaces")
        if res['link_carpeta']:
            st.info(f"➡️ [Abrir carpeta del proyecto en Google Drive]({res['link_carpeta']})")
        
        st.download_button("📥 Descargar Reporte en PDF (Copia Local)", data=res['pdf_bytes'], file_name=res['nombre_pdf_final'], mime="application/pdf", use_container_width=True)
        
        if res['contrato_bytes']:
            st.download_button("   Descargar Contrato en Word (.docx)", data=res['contrato_bytes'], file_name=res['nombre_contrato_final'], mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

        if res['csv_content']:
            st.download_button("📊 Descargar Flujo de Caja en CSV (Detallado)", data=res['csv_content'], file_name=res['nombre_csv'], mime="text/csv", use_container_width=True)

        # Excel Export
        try:
            hsp_promedio = sum(res['hsp_mensual_final']) / len(res['hsp_mensual_final']) if res['hsp_mensual_final'] else 0
            datos_excel = {
                'cliente': res.get('nombre_proyecto', '').split(' - ')[1] if ' - ' in res.get('nombre_proyecto', '') else '',
                'proyecto': res.get('nombre_proyecto', ''),
                'fecha': datetime.date.today().strftime('%Y-%m-%d'),
                'tamano_kwp': res.get('size', 0),
                'cantidad_paneles': res.get('quantity', 0),
                'inversor': res.get('recomendacion_inversor', ''),
                'valor_proyecto': res.get('val_total', 0),
                'tir': res.get('tasa_interna', 0),
                'vpn': res.get('valor_presente', 0),
                'payback': res.get('payback_exacto', 'N/A'),
                'ahorro_ano1': res.get('ahorro_año1', 0),
                'generacion_anual': sum(res.get('monthly_generation', [])) if res.get('monthly_generation') else 0,
                'consumo_mensual': res.get('Load', 0),
                'costo_kwh': st.session_state.get('form_costo_kwh', 850),
                'indexacion': st.session_state.get('form_indexacion', 5.0),
                'tasa_descuento': st.session_state.get('form_tasa_descuento', 10.0),
                'cubierta': res.get('cubierta', ''),
                'clima': 'N/A',
                'hsp_promedio': hsp_promedio,
            }
            
            excel_bytes = generar_excel_financiero(
                datos_proyecto=datos_excel,
                flujo_caja=res.get('fcl', []),
                monthly_generation=res.get('monthly_generation', []),
                horizonte=res.get('horizonte_tiempo', 25),
                analisis_sensibilidad=res.get('analisis_sensibilidad')
            )
            
            nombre_excel = f"Análisis_Financiero_{res.get('nombre_proyecto', 'Proyecto')}.xlsx"
            st.download_button(
                "📈 Descargar Análisis en Excel (con gráficos)", 
                data=excel_bytes, 
                file_name=nombre_excel, 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
        except Exception as excel_error:
            st.warning(f"No se pudo generar el Excel: {excel_error}")

        if res['agregado_notion']:
            st.info("🗂️ Cliente agregado a Notion: En conversaciones")
        else:
            st.caption(f"Notion: {res['msg_notion']}")
