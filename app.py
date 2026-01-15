import streamlit as st
import datetime
import os

# Importaciones de módulos refactorizados
from src.config import HSP_MENSUAL_POR_CIUDAD, PROMEDIOS_COSTO, ESTRUCTURA_CARPETAS, HSP_POR_CIUDAD
from src.utils.helpers import validar_datos_entrada, formatear_moneda
from src.utils.chargers import cotizacion_cargadores_costos, calcular_materiales_cargador, generar_pdf_cargadores
from src.services.notion_service import agregar_cliente_a_notion_crm
from src.services.pvgis_service import get_pvgis_hsp_local, get_pvgis_hsp_alternative, get_hsp_estimado_mejorado, get_hsp_estimado
from src.services.location_service import get_coords_from_address, get_static_map_image
from src.services.calculator_service import (
    calcular_costo_por_kwp, 
    generar_csv_flujo_caja_detallado, 
    calcular_analisis_sensibilidad,
    redondear_a_par,
    recomendar_inversor,
    cotizacion,
    calcular_lista_materiales
)
from src.services.drive_service import (
    obtener_siguiente_consecutivo,
    crear_subcarpetas,
    subir_pdf_a_drive,
    subir_csv_a_drive,
    subir_docx_a_drive,
    gestionar_creacion_drive
)
from src.utils.pdf_generator import PropuestaPDF
from src.utils.contract_generator import generar_contrato_docx
from src.utils.ui_helpers import detect_mobile_device, apply_responsive_css, detect_device_type
from src.ui.mobile import render_mobile_interface
from src.ui.desktop import render_desktop_interface

# Import carbon calculator module
try:
    from carbon_calculator import CarbonEmissionsCalculator
    carbon_calculator = CarbonEmissionsCalculator()
except ImportError:
    # st.warning("⚠️ Módulo de cálculo de carbono no encontrado.")
    carbon_calculator = None

# Project management features removed - not needed
project_manager = None
financial_summary_generator = None

def main():
    # Configuración básica
    st.set_page_config(
        page_title="Calculadora Solar", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )
    
    # Inicializar first_load
    if 'first_load' not in st.session_state:
        st.session_state.first_load = True
    
    # Inicializar session_state si no existe
    if 'force_mobile' not in st.session_state:
        st.session_state.force_mobile = False
    
    # Inicializar otras variables de session_state que podrían ser necesarias
    if 'first_load' not in st.session_state:
        st.session_state.first_load = False
    
    if 'sistema_data' not in st.session_state:
        st.session_state.sistema_data = {}
    
    if 'cliente_data' not in st.session_state:
        st.session_state.cliente_data = {}
    
    if 'ubicacion_data' not in st.session_state:
        st.session_state.ubicacion_data = {}
    
    # Sidebar simple para control de modo
    with st.sidebar:
        st.header("⚙️ Configuración de Visualización")
        
        # Mostrar estado actual y botones de cambio
        if st.session_state.force_mobile:
            st.success("📱 **MODO MÓVIL ACTIVADO**")
            if st.button("🖥️ Cambiar a Desktop", use_container_width=True):
                st.session_state.force_mobile = False
                st.rerun()
        else:
            st.info("🖥️ **MODO DESKTOP ACTIVADO**")
            if st.button("📱 Cambiar a Móvil", use_container_width=True):
                st.session_state.force_mobile = True
                st.rerun()
        
        st.markdown("---")
        st.markdown("**💡 Cómo funciona:**")
        st.markdown("- **Móvil**: Interfaz con tabs optimizada")
        st.markdown("- **Desktop**: Interfaz completa con sidebar")
        st.markdown("- Cambia instantáneamente con los botones")
    
    # Aplicar CSS responsive
    apply_responsive_css()
    
    # Renderizar interfaz según el modo seleccionado
    if st.session_state.force_mobile:
        render_mobile_interface()
    else:
        render_desktop_interface()

if __name__ == '__main__':
    main()
