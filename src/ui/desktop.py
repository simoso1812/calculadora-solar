"""
Interfaz para escritorio (Desktop).
"""
import streamlit as st
import datetime
import os
import math
import folium
from streamlit_folium import st_folium
import googlemaps
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.config import HSP_MENSUAL_POR_CIUDAD, PROMEDIOS_COSTO, ESTRUCTURA_CARPETAS, HSP_POR_CIUDAD
from src.services.pvgis_service import get_pvgis_hsp_alternative
from src.services.location_service import get_static_map_image
from src.services.calculator_service import (
    calcular_costo_por_kwp,
    cotizacion, 
    redondear_a_par,
    calcular_lista_materiales,
    generar_csv_flujo_caja_detallado,
    calcular_analisis_sensibilidad
)
from src.services.drive_service import (
    gestionar_creacion_drive, 
    obtener_siguiente_consecutivo,
    subir_csv_a_drive
)
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

def render_desktop_interface():
    """Interfaz optimizada para desktop"""
    # Debug visual - confirmar que estamos en modo desktop
    st.markdown("""
    <div style="background: #4ecdc4; color: white; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; border: 3px solid #45b7d1;">
        <h1 style="margin: 0; color: white;">🖥️ MODO DESKTOP ACTIVADO 🖥️</h1>
        <p style="margin: 10px 0; font-size: 18px;">Interfaz completa con sidebar</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header desktop con indicador claro
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.markdown("🖥️")
    with col2:
        st.title("☀️ Calculadora y Cotizador Solar Profesional")
    with col3:
        st.markdown("🖥️")
    
    st.success("✅ Interfaz desktop cargada correctamente")

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
        
        st.subheader("Datos del Cliente y Propuesta")
        nombre_cliente = st.text_input("Nombre del Cliente", "Andres Pinzón")
        documento_cliente = st.text_input("Documento del Cliente (CC o NIT)", "123.456.789-0")
        direccion_proyecto = st.text_input("Dirección del Proyecto", "Villa Roca 1 Int. 9B, Copacabana")
        fecha_propuesta = st.date_input("Fecha de la Propuesta", datetime.date.today()) 
        
        st.subheader("Información del Proyecto (Interna)")
        ubicacion = st.text_input("Ubicación (Etiqueta para carpeta)", "Villa Roca 1")
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

        address = st.text_input("Buscar dirección o lugar:", placeholder="Ej: Cl. 77 Sur #40-168, Sabaneta", key="address_search")
        address = address.strip()
        if st.button("Buscar Dirección"):
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
                st.success("✅ Datos de HSP obtenidos de PVGIS.")
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
        
        opcion = st.radio("Método para dimensionar:", ["Por Consumo Mensual (kWh)", "Por Cantidad de Paneles"], horizontal=True, key="metodo_dimensionamiento")

        if opcion == "Por Consumo Mensual (kWh)":
            Load = st.number_input("Consumo mensual (kWh)", min_value=50, value=700, step=50)
            module = st.number_input("Potencia del panel (W)", min_value=300, value=615, step=10)
            HSP_aprox = 4.5; n_aprox = 0.85; Ratio = 1.2
            size = round(Load * Ratio / (HSP_aprox * 30 * n_aprox), 2)
            quantity = redondear_a_par(size * 1000 / module)
            size = round(quantity * module / 1000, 2)
            st.info(f"Sistema estimado: **{size:.2f} kWp** ({int(quantity)} paneles)")
        else:
            module = st.number_input("Potencia del panel (W)", min_value=300, value=615, step=10)
            quantity_input = st.number_input("Cantidad de paneles", min_value=1, value=12, step=2)
            quantity = redondear_a_par(quantity_input)
            Load = st.number_input("Consumo mensual (kWh)", min_value=50, value=700, step=50)
            size = round((quantity * module) / 1000, 2)
            st.info(f"Sistema dimensionado: **{size:.2f} kWp**")

        st.subheader("Datos Generales")
        cubierta = st.selectbox("Tipo de cubierta", ["LÁMINA", "TEJA"])
        clima = st.selectbox("Clima predominante", ["SOL", "NUBE"])

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
        
        # Debug: Mostrar el valor del toggle
        st.write(f"🔧 Debug - Toggle activado: {incluir_analisis_sensibilidad}")
        
        if incluir_analisis_sensibilidad:
            st.info("📈 **Análisis de Sensibilidad**: Se calculará TIR a 10 y 20 años con y sin financiación para mostrar la robustez del proyecto")
        
        costkWh = st.number_input("Costo por kWh (COP)", min_value=200, value=850, step=10)
        index_input = st.slider("Indexación de energía (%)", 0.0, 20.0, 5.0, 0.5)
        dRate_input = st.slider("Tasa de descuento (%)", 0.0, 25.0, 10.0, 0.5)
        
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
                        key="download_financial_pdf"
                    )

                except Exception as e:
                    st.error(f"Error generando PDF financiero: {e}")

        st.markdown("---")
        st.subheader("🔌 Cotizador de Cargadores")
        ev_nombre = st.text_input("Cliente y Lugar (Cargadores)", "")
        ev_dist = st.number_input("Distancia parqueadero a subestación (m)", min_value=1.0, value=10.0, step=1.0)
        if st.button("Generar PDF Cargadores", use_container_width=True, key="ev_gen_desktop"):
            try:
                ev_pdf, ev_desglose = generar_pdf_cargadores(ev_nombre or "Cliente", ev_dist)
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
    # LÓGICA DE CÁLCULO Y VISUALIZACIÓN (AL PRESIONAR EL BOTÓN)
    # ==============================================================================
    if st.button("   Calcular y Generar Reporte", use_container_width=True):
        # Validar datos de entrada
        errores_validacion = validar_datos_entrada(Load, size, quantity, cubierta, clima, costkWh, module)
        
        if errores_validacion:
            st.error("❌ Errores de validación encontrados:")
            for error in errores_validacion:
                st.error(f"• {error}")
            return
        
        with st.spinner('Realizando cálculos y creando archivos... ⏳'):
            nombre_proyecto = f"FV{str(datetime.datetime.now().year)[-2:]}{numero_proyecto_del_año:03d} - {nombre_cliente}" + (f" - {ubicacion}" if ubicacion else "")
            st.success(f"Proyecto Generado: {nombre_proyecto}")


            valor_proyecto_total, size_calc, monto_a_financiar, cuota_mensual_credito, \
            desembolso_inicial_cliente, fcl, trees, monthly_generation, valor_presente, \
            tasa_interna, cantidad_calc, life, recomendacion_inversor, lcoe, n_final, hsp_mensual_final, \
            potencia_ac_inversor, ahorro_año1, area_requerida, capacidad_nominal_bateria, carbon_data = \
                cotizacion(Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100, costkWh, module,
                             ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                             perc_financiamiento=perc_financiamiento, tasa_interes_credito=tasa_interes_input / 100,
                             plazo_credito_años=plazo_credito_años, tasa_degradacion=0.001, precio_excedentes=300.0,
                             incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                             profundidad_descarga=profundidad_descarga / 100,
                             eficiencia_bateria=eficiencia_bateria / 100, dias_autonomia=dias_autonomia,
                             horizonte_tiempo=horizonte_tiempo, incluir_carbon=incluir_carbon,
                             incluir_beneficios_tributarios=incluir_beneficios_tributarios,
                             incluir_deduccion_renta=incluir_deduccion_renta,
                             incluir_depreciacion_acelerada=incluir_depreciacion_acelerada,
                             demora_6_meses=demora_6_meses)
            
            # Aplicar precio manual si está activado
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
                                ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * 300.0)  # precio_excedentes = 300
                            else:
                                ahorro_mes = gen_mes * costkWh
                            ahorro_anual_total += ahorro_mes

                    # Aplicar indexación
                    ahorro_anual_indexado = ahorro_anual_total * ((1 + index_input / 100) ** i)
                    if i == 0:
                        ahorro_año1 = ahorro_anual_total

                    # Mantenimiento anual
                    mantenimiento_anual = 0.05 * ahorro_anual_indexado

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

                st.success(f"✅ **Precio Manual Aplicado**: ${val_total:,.0f} COP")
                st.info("🔄 **Flujo de caja recalculado** con el precio manual para métricas correctas")
            
            generacion_promedio_mensual = sum(monthly_generation) / len(monthly_generation) if monthly_generation else 0
            payback_simple = next((i for i, x in enumerate(np.cumsum(fcl)) if x >= 0), None)
            payback_exacto = None
            if payback_simple is not None:
                if payback_simple > 0 and (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1]) != 0:
                    payback_exacto = (payback_simple - 1) + abs(np.cumsum(fcl)[payback_simple-1]) / (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1])
                else:
                    payback_exacto = float(payback_simple)
            
            # Store calculation results for project management
            calculation_results = {
                'valor_proyecto_total': valor_proyecto_total,
                'size_calc': size_calc,
                'monto_a_financiar': monto_a_financiar,
                'cuota_mensual_credito': cuota_mensual_credito,
                'desembolso_inicial_cliente': desembolso_inicial_cliente,
                'fcl': fcl,
                'trees': trees,
                'monthly_generation': monthly_generation,
                'valor_presente': valor_presente,
                'tasa_interna': tasa_interna,
                'cantidad_calc': cantidad_calc,
                'life': life,
                'recomendacion_inversor': recomendacion_inversor,
                'lcoe': lcoe,
                'n_final': n_final,
                'hsp_mensual_final': hsp_mensual_final,
                'potencia_ac_inversor': potencia_ac_inversor,
                'ahorro_año1': ahorro_año1,
                'area_requerida': area_requerida,
                'capacidad_nominal_bateria': capacidad_nominal_bateria,
                'carbon_data': carbon_data,
                'payback_exacto': payback_exacto,
                'generacion_promedio_mensual': generacion_promedio_mensual
            }


            # DEBUG: Mostrar información del cálculo principal
            print(f"\n=== DEBUG CÁLCULO PRINCIPAL ===")
            print(f"Horizonte: {horizonte_tiempo}")
            print(f"Desembolso inicial: {desembolso_inicial_cliente:,.0f}")
            print(f"Primeros 10 flujos: {[f'{x:,.0f}' for x in fcl[:10]]}")
            print(f"Payback calculado: {payback_exacto}")
            print(f"Suma acumulada primeros 6 años: {[f'{x:,.0f}' for x in np.cumsum(fcl)[:6]]}")
            print("=" * 50)

            st.header("Resultados de la Propuesta")
            
            # Indicador del horizonte de tiempo
            st.info(f"📅 **Análisis financiero a {horizonte_tiempo} años** - TIR, VPN y Payback calculados para este período")
            
            col1, col2, col3, col4 = st.columns(4)
            # Usar val_total si precio manual está activado, de lo contrario usar valor_proyecto_total
            valor_mostrar = val_total if (precio_manual and precio_manual_valor) else valor_proyecto_total
            col1.metric("Valor del Proyecto", f"${valor_mostrar:,.0f}")
            col2.metric("TIR", f"{tasa_interna:.1%}")
            col3.metric("Payback (años)", f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A")
            if incluir_baterias:
                col4.metric("Batería Recomendada", f"{capacidad_nominal_bateria:.1f} kWh")
            else:
                col4.metric("Ahorro Año 1", f"${ahorro_año1:,.0f}")

            # Display carbon metrics if available
            if incluir_carbon and carbon_data and 'annual_co2_avoided_tons' in carbon_data:
                st.markdown("---")
                st.header("🌱 Impacto Ambiental y Sostenibilidad")

                # Carbon metrics in columns
                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                col_c1.metric(
                    "CO2 Evitado Anual",
                    f"{carbon_data['annual_co2_avoided_tons']:.1f} ton",
                    help="Toneladas de CO2 evitadas por año"
                )
                col_c2.metric(
                    "Árboles Salvados",
                    f"{carbon_data['trees_saved_per_year']:.0f}",
                    help="Árboles equivalentes salvados por año"
                )
                col_c3.metric(
                    "Valor Carbono",
                    f"${carbon_data['annual_certification_value_cop']:,.0f}",
                    help="Valor potencial de certificación de carbono"
                )
                col_c4.metric(
                    "Autos Equivalentes",
                    f"{carbon_data['cars_off_road_per_year']:.1f}",
                    help="Autos que dejarían de circular por año"
                )

                # Additional equivalencies
                with st.expander("📊 Ver más equivalencias ambientales"):
                    st.markdown("**Impacto Ambiental Detallado:**")
                    st.write(f"• **Vuelos evitados**: {carbon_data['flights_avoided_per_year']:.0f} vuelos de ida y vuelta")
                    st.write(f"• **Botellas de plástico**: {carbon_data['plastic_bottles_avoided_per_year']:,.0f} botellas recicladas")
                    st.write(f"• **Cargas de celular**: {carbon_data['smartphone_charges_avoided_per_year']:,.0f} cargas de batería")

                    if 'lifetime_co2_avoided_tons' in carbon_data:
                        st.markdown("**Impacto a Largo Plazo:**")
                        st.write(f"• **CO2 total evitado**: {carbon_data['lifetime_co2_avoided_tons']:.1f} toneladas en {life} años")
                        st.write(f"• **Valor total carbono**: ${carbon_data['lifetime_certification_value_cop']:,.0f} COP")

            # Análisis de Sensibilidad
            st.write(f"🔧 Debug - Verificando toggle: {incluir_analisis_sensibilidad}")
            if incluir_analisis_sensibilidad:
                st.header("📊 Análisis de Sensibilidad")
                st.info("🔍 **Análisis comparativo** de TIR a 10 y 20 años con y sin financiación para evaluar la robustez del proyecto")
                
                with st.spinner("Calculando análisis de sensibilidad..."):
                    # Calcular análisis de sensibilidad
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
                        incluir_depreciacion_acelerada=incluir_depreciacion_acelerada
                    )
                
                # Crear tabla comparativa
                st.subheader("📈 Comparativa de Escenarios")
                
                # Preparar datos para la tabla
                datos_tabla = []
                for escenario, datos in analisis_sensibilidad.items():
                    datos_tabla.append({
                        "Escenario": escenario,
                        "TIR": f"{datos['tir']:.1%}" if datos['tir'] is not None else "N/A",
                        "VPN (COP)": f"${datos['vpn']:,.0f}" if datos['vpn'] is not None else "N/A",
                        "Payback (años)": f"{datos['payback']:.2f}" if datos['payback'] is not None else "N/A",
                        "Desembolso Inicial": f"${datos['desembolso_inicial']:,.0f}",
                        "Cuota Mensual": f"${datos['cuota_mensual']:,.0f}" if datos['cuota_mensual'] > 0 else "N/A"
                    })
                
                # Mostrar tabla
                df_sensibilidad = pd.DataFrame(datos_tabla)
                st.dataframe(df_sensibilidad, use_container_width=True)
                
                # Análisis de conclusiones
                st.subheader("💡 Conclusiones del Análisis")
                
                # Encontrar mejores escenarios
                mejor_tir_10 = max([(k, v['tir']) for k, v in analisis_sensibilidad.items() if '10 años' in k and v['tir'] is not None], key=lambda x: x[1], default=(None, 0))
                mejor_tir_20 = max([(k, v['tir']) for k, v in analisis_sensibilidad.items() if '20 años' in k and v['tir'] is not None], key=lambda x: x[1], default=(None, 0))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Mejor TIR a 10 años", f"{mejor_tir_10[1]:.1%}" if mejor_tir_10[0] else "N/A", 
                             help=f"Escenario: {mejor_tir_10[0]}" if mejor_tir_10[0] else "")
                
                with col2:
                    st.metric("Mejor TIR a 20 años", f"{mejor_tir_20[1]:.1%}" if mejor_tir_20[0] else "N/A",
                             help=f"Escenario: {mejor_tir_20[0]}" if mejor_tir_20[0] else "")
                
                # Recomendaciones
                st.info("""
                **📋 Recomendaciones:**
                - **TIR más alta**: Indica mayor rentabilidad del proyecto
                - **Payback más bajo**: Indica recuperación más rápida de la inversión
                - **Con financiación**: Reduce desembolso inicial pero puede afectar TIR
                - **Sin financiación**: Mayor desembolso inicial pero potencialmente mejor TIR
                """)

            with st.expander("📊 Ver Análisis Financiero Interno (Presupuesto Guía)"):
                st.subheader("Desglose Basado en Promedios Históricos")
                # Usar precio manual si está activado para el presupuesto también
                valor_base_presupuesto = precio_manual_valor if precio_manual and precio_manual_valor else valor_proyecto_total
                presupuesto_equipos = valor_base_presupuesto * (PROMEDIOS_COSTO['Equipos'] / 100)
                presupuesto_materiales = valor_base_presupuesto * (PROMEDIOS_COSTO['Materiales'] / 100)
                ganancia_estimada_guia = valor_base_presupuesto * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
                provision_iva_guia = (presupuesto_materiales + ganancia_estimada_guia) * 0.19
                st.info(f"""Basado en el **Valor Total del Proyecto de ${valor_base_presupuesto:,.0f} COP**, el presupuesto guía según tu historial es:""")
                col_guia1, col_guia2, col_guia3, col_guia4 = st.columns(4)
                col_guia1.metric(f"Equipos ({PROMEDIOS_COSTO['Equipos']:.2f}%)", f"${math.ceil(presupuesto_equipos):,.0f}")
                col_guia2.metric(f"Materiales ({PROMEDIOS_COSTO['Materiales']:.2f}%)", f"${math.ceil(presupuesto_materiales):,.0f}")
                col_guia3.metric(f"Provisión IVA (19% de Materiales+Ganancia)", f"${math.ceil(provision_iva_guia):,.0f}")
                col_guia4.metric(f"Ganancia Estimada ({PROMEDIOS_COSTO['Margen (Ganancia)']:.2f}%)", f"${math.ceil(ganancia_estimada_guia):,.0f}")
                st.warning("Nota: Esta sección es una guía interna y no se incluirá en el reporte PDF del cliente.")

            with st.expander("📋 Ver Lista de Materiales (Referencia Interna)"):
                st.subheader("Materiales de Montaje Estimados")
                lista_materiales = calcular_lista_materiales(cantidad_calc, cubierta, module, recomendacion_inversor)
                if lista_materiales:
                    df_materiales = pd.DataFrame(lista_materiales.items(), columns=['Material', 'Cantidad Estimada'])
                    df_materiales.index = df_materiales.index + 1
                    st.table(df_materiales)
                else:
                    st.write("No se calcularon materiales (cantidad de paneles es cero).")
                st.warning("Nota: Esta es una lista de referencia y no incluye todos los componentes.")
        
            st.header("Análisis Gráfico")
            
            lat, lon = None, None
            if st.session_state.map_state["marker"]:
                lat, lon = st.session_state.map_state["marker"]
                api_key = os.environ.get("Maps_API_KEY") 
                if api_key and gmaps:
                    with st.spinner("Generando imagen del mapa..."):
                        get_static_map_image(lat, lon, api_key)

            # --- CÓDIGO DEL GRÁFICO 1 (GENERACIÓN VS CONSUMO) ---
            fig1, ax1 = plt.subplots(figsize=(10, 5))
            meses_grafico = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

            if incluir_baterias:
                # --- LÓGICA PARA GRÁFICA OFF-GRID (CON BATERÍAS) ---
                st.subheader("Flujo de Energía Mensual (Off-Grid)")
                generacion_autoconsumida = []
                energia_a_bateria = []
                
                for gen_mes in monthly_generation:
                    # Lo que se consume directamente es el mínimo entre lo que se genera y lo que se necesita
                    autoconsumo_mes = min(gen_mes, Load)
                    # Lo que va a la batería es todo el excedente
                    bateria_mes = max(0, gen_mes - autoconsumo_mes)
                    
                    generacion_autoconsumida.append(autoconsumo_mes)
                    energia_a_bateria.append(bateria_mes)

                ax1.bar(meses_grafico, generacion_autoconsumida, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
                ax1.bar(meses_grafico, energia_a_bateria, bottom=generacion_autoconsumida, color='green', edgecolor='black', label='Energía Almacenada en Batería', width=0.7)
                ax1.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
                ax1.set_ylabel("Energía (kWh)", fontweight="bold")
                ax1.set_title("Flujo de Energía Mensual Estimado (Off-Grid)", fontweight="bold")
                ax1.legend()

            else:
                # --- LÓGICA PARA GRÁFICA ON-GRID (SIN BATERÍAS) ---
                st.subheader("Generación Vs. Consumo Mensual (On-Grid)")
                generacion_autoconsumida_on, excedentes_vendidos, importado_de_la_red = [], [], []
                for gen_mes in monthly_generation:
                    if gen_mes >= Load:
                        generacion_autoconsumida_on.append(Load); excedentes_vendidos.append(gen_mes - Load); importado_de_la_red.append(0)
                    else:
                        generacion_autoconsumida_on.append(gen_mes); excedentes_vendidos.append(0); importado_de_la_red.append(Load - gen_mes)
                
                ax1.bar(meses_grafico, generacion_autoconsumida_on, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
                ax1.bar(meses_grafico, excedentes_vendidos, bottom=generacion_autoconsumida_on, color='red', edgecolor='black', label='Excedentes Vendidos', width=0.7)
                ax1.bar(meses_grafico, importado_de_la_red, bottom=generacion_autoconsumida_on, color='#2ECC71', edgecolor='black', label='Importado de la Red', width=0.7)
                ax1.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
                ax1.set_ylabel("Energía (kWh)", fontweight="bold")
                ax1.set_title("Generación Vs. Consumo Mensual (On-Grid)", fontweight="bold")
                ax1.legend()

            st.pyplot(fig1)

            fig2, ax2 = plt.subplots(figsize=(10, 5))
            fcl_acumulado = np.cumsum(fcl)
            años = np.arange(0, life + 1)
            ax2.plot(años, fcl_acumulado, marker='o', linestyle='-', color='green', label='Flujo de Caja Acumulado')
            ax2.plot(0, fcl_acumulado[0], marker='X', markersize=10, color='red', label='Desembolso Inicial (Año 0)')
            if payback_exacto is not None: ax2.axvline(x=payback_exacto, color='red', linestyle='--', label=f'Payback Simple: {payback_exacto:.2f} años')
            ax2.axhline(0, color='grey', linestyle='--', linewidth=0.8)
            ax2.set_ylabel("Flujo de Caja Acumulado (COP)", fontweight="bold"); ax2.set_xlabel("Año", fontweight="bold")
            ax2.set_title("Flujo de Caja Acumulado y Período de Retorno", fontweight="bold"); ax2.legend()
            st.pyplot(fig2)
            
            fig1.savefig('grafica_generacion.png', bbox_inches='tight')
            fig2.savefig('grafica_flujo_caja.png', bbox_inches='tight')

            presupuesto_equipos = valor_proyecto_total * (PROMEDIOS_COSTO['Equipos'] / 100)
            presupuesto_materiales = valor_proyecto_total * (PROMEDIOS_COSTO['Materiales'] / 100)
            provision_iva_guia = valor_proyecto_total * (PROMEDIOS_COSTO['IVA (Impuestos)'] / 100)
            ganancia_estimada_guia = valor_proyecto_total * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
            valor_total_redondeado = math.ceil(valor_proyecto_total / 100) * 100
            valor_iva_redondeado = math.ceil(provision_iva_guia / 100) * 100
            valor_sistema_sin_iva_redondeado = valor_total_redondeado - valor_iva_redondeado

            # Usar precio manual si está activado para el PDF principal también
            valor_pdf = precio_manual_valor if precio_manual and precio_manual_valor else valor_proyecto_total
            valor_pdf_redondeado = math.ceil(valor_pdf / 100) * 100
            presupuesto_materiales_pdf = valor_pdf_redondeado * (PROMEDIOS_COSTO['Materiales'] / 100)
            ganancia_estimada_pdf = valor_pdf_redondeado * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
            valor_iva_pdf = math.ceil(((presupuesto_materiales_pdf + ganancia_estimada_pdf) * 0.19)/100)*100
            valor_sistema_sin_iva_pdf = valor_pdf_redondeado - valor_iva_pdf

            # Calcular datos de carbono si están disponibles
            arboles_equivalentes_desktop = 0
            co2_evitado_tons_desktop = 0.0
            if incluir_carbon and carbon_data:
                arboles_equivalentes_desktop = carbon_data.get('trees_saved_per_year', 0)
                co2_evitado_tons_desktop = carbon_data.get('annual_co2_avoided_tons', 0.0)
            
            datos_para_pdf = {
                "Nombre del Proyecto": nombre_proyecto, "Cliente": nombre_cliente,
                "Valor Total del Proyecto (COP)": f"${valor_pdf_redondeado:,.0f}",
                "Valor Sistema FV (sin IVA)": f"${valor_sistema_sin_iva_pdf:,.0f}",
                "Valor IVA": f"${valor_iva_pdf:,.0f}",
                "Tamano del Sistema (kWp)": f"{size:.1f}",
                "Cantidad de Paneles": f"{int(quantity)} de {int(module)}W","Área Requerida Aprox. (m²)": f"{area_requerida}",
                "Inversor Recomendado": f"{recomendacion_inversor}",
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
            
            # Calcular O&M (2% del CAPEX)
            om_anual = valor_pdf_redondeado * 0.02  # 2% del valor total del proyecto
            datos_para_pdf["O&M (Operation & Maintenance)"] = f"${om_anual:,.0f}"
            if usa_financiamiento:
                # Recalcular financiamiento con el precio manual si está activado
                if precio_manual and precio_manual_valor:
                    monto_a_financiar_pdf = valor_pdf_redondeado * (perc_financiamiento / 100)
                    monto_a_financiar_pdf = math.ceil(monto_a_financiar_pdf)
                    desembolso_inicial_pdf = valor_pdf_redondeado - monto_a_financiar_pdf

                    # Recalcular cuota mensual con precio manual
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
            
            datos_para_contrato = datos_para_pdf.copy() # Copiamos los datos
            datos_para_contrato['Fecha de la Propuesta'] = fecha_propuesta

            pdf = PropuestaPDF(
                client_name=nombre_cliente, 
                project_name=nombre_proyecto,
                documento=documento_cliente,
                direccion=direccion_proyecto,
                fecha=fecha_propuesta 
            )

            pdf_bytes = pdf.generar(datos_para_pdf, usa_financiamiento, lat, lon)
            nombre_pdf_final = f"{nombre_proyecto}.pdf"
            
            nombre_contrato_final = f"Contrato - {nombre_proyecto}.docx"
            contrato_bytes = generar_contrato_docx(datos_para_contrato)

            if drive_service:
                link_carpeta = gestionar_creacion_drive(
                    drive_service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf_final,contrato_bytes, nombre_contrato_final
                )
                if link_carpeta:
                    st.info(f"➡️ [Abrir carpeta del proyecto en Google Drive]({link_carpeta})")
            
            st.download_button(
                label="📥 Descargar Reporte en PDF (Copia Local)",
                data=pdf_bytes, file_name=nombre_pdf_final,
                mime="application/pdf", use_container_width=True
            )
            if contrato_bytes:
                st.download_button(
                    label="   Descargar Contrato en Word (.docx)",
                    data=contrato_bytes,
                    file_name=nombre_contrato_final,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            # Generar y descargar CSV detallado del flujo de caja
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
                nombre_csv = f"Flujo_Caja_Detallado_{nombre_proyecto}.csv"
                
                # Botón de descarga
                st.download_button(
                    label="📊 Descargar Flujo de Caja en CSV (Detallado)",
                    data=csv_content,
                    file_name=nombre_csv,
                    mime="text/csv",
                    use_container_width=True,
                    help="Descarga un archivo CSV con el flujo de caja anual detallado, incluyendo generación, consumo, costos, TIR/VPN parciales y más métricas"
                )
                
                # Guardar automáticamente en Google Drive (carpeta Administrativo y Financiero)
                try:
                    if 'drive_service' in locals() and drive_service:
                        # Buscar la carpeta del proyecto por nombre
                        query_proyecto = f"name='{nombre_proyecto}' and mimeType='application/vnd.google-apps.folder'"
                        results_proyecto = drive_service.files().list(
                            q=query_proyecto, 
                            fields="files(id)", 
                            supportsAllDrives=True, 
                            includeItemsFromAllDrives=True
                        ).execute()
                        
                        if results_proyecto.get('files'):
                            id_carpeta_principal = results_proyecto['files'][0]['id']
                            
                            # Buscar carpeta "08_Administrativo_y_Financiero"
                            query_administrativo = f"'{id_carpeta_principal}' in parents and name='08_Administrativo_y_Financiero'"
                            results_administrativo = drive_service.files().list(
                                q=query_administrativo, 
                                fields="files(id)", 
                                supportsAllDrives=True, 
                                includeItemsFromAllDrives=True
                            ).execute()
                            
                            if results_administrativo.get('files'):
                                id_carpeta_administrativo = results_administrativo['files'][0]['id']
                                csv_link = subir_csv_a_drive(drive_service, id_carpeta_administrativo, nombre_csv, csv_content)
                                if csv_link:
                                    st.success("✅ CSV del flujo de caja guardado automáticamente en Google Drive")
                            else:
                                st.warning("⚠️ No se encontró la carpeta '08_Administrativo_y_Financiero'")
                        else:
                            st.info("ℹ️ Proyecto no encontrado en Google Drive")
                    else:
                        st.info("ℹ️ CSV generado localmente (Google Drive no configurado)")
                except Exception as drive_error:
                    st.warning(f"⚠️ No se pudo guardar el CSV en Google Drive: {drive_error}")
                    
            except Exception as csv_error:
                st.warning(f"No se pudo generar el CSV: {csv_error}")
            st.success('¡Proceso completado!')

            # Notion CRM - agregar a "En conversaciones" (flujo desktop)
            agregado, msg = agregar_cliente_a_notion_crm(
                nombre=nombre_cliente,
                documento=documento_cliente,
                direccion=direccion_proyecto,
                proyecto=nombre_proyecto,
                fecha=fecha_propuesta,
                estado="En conversaciones"
            )
            if agregado:
                st.info("🗂️ Cliente agregado a Notion: En conversaciones")
            else:
                st.caption(f"Notion: {msg}")
