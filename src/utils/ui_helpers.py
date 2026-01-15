"""
Utilidades para la interfaz de usuario.
"""
import streamlit as st

def detect_mobile_device():
    """Función simple para detectar modo móvil"""
    return st.session_state.get('force_mobile', False)

def apply_responsive_css():
    """Aplica CSS responsive para móviles y personalización del sidebar"""
    st.markdown("""
    <style>
    /* === SIDEBAR MÁS ANCHO === */
    [data-testid="stSidebar"] {
        min-width: 400px !important;
        max-width: 450px !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        min-width: 400px !important;
        max-width: 450px !important;
    }
    
    /* Ajustar contenido del sidebar */
    [data-testid="stSidebar"] .block-container {
        padding: 1rem 1.5rem !important;
    }
    
    /* === RESPONSIVE MÓVIL === */
    @media (max-width: 768px) {
        .stButton > button {
            width: 100% !important;
            margin: 5px 0 !important;
        }
        .stSelectbox > div > div {
            width: 100% !important;
        }
        .stTextInput > div > div {
            width: 100% !important;
        }
        .stNumberInput > div > div {
            width: 100% !important;
        }
        .stDateInput > div > div {
            width: 100% !important;
        }
        .stRadio > div > div {
            width: 100% !important;
        }
        .stTabs > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
        .stTabs > div > div > div > div > div > div > div > ptr > div > div > div > div > div > div > div > div > div > div > div > div > div {
            width: 100% !important;
        }
    }
    
    /* Estilos generales para móviles */
    .mobile-optimized {
        padding: 10px !important;
        margin: 5px 0 !important;
    }
    
    .mobile-button {
        width: 100% !important;
        height: 50px !important;
        font-size: 16px !important;
        margin: 10px 0 !important;
    }
    
    .mobile-input {
        width: 100% !important;
        margin: 5px 0 !important;
    }
    
    .mobile-tab {
        width: 100% !important;
        padding: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

def detect_device_type():
    """Detecta el tipo de dispositivo de forma simple y estable"""
    # Inyectar JavaScript simple para detectar
    st.markdown("""
    <script>
    // Función simple para detectar dispositivo
    function detectDevice() {
        const isMobile = window.innerWidth < 768;
        const deviceType = isMobile ? 'Móvil' : 'Desktop';
        
        // Crear elemento visual para mostrar la detección
        const detectionDiv = document.createElement('div');
        detectionDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            padding: 15px;
            border-radius: 10px;
            font-weight: bold;
            z-index: 9999;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        `;
        detectionDiv.innerHTML = `📱 Dispositivo detectado: ${deviceType}<br><small>Usa el sidebar para cambiar</small>`;
        
        // Agregar al DOM
        document.body.appendChild(detectionDiv);
        
        // Remover después de 5 segundos
        setTimeout(() => {
            if (detectionDiv.parentNode) {
                detectionDiv.parentNode.removeChild(detectionDiv);
            }
        }, 5000);
    }
    
    // Ejecutar detección
    detectDevice();
    </script>
    """, unsafe_allow_html=True)

