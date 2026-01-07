"""
Configuración y constantes globales para la aplicación Calculadora Solar.
"""

HSP_MENSUAL_POR_CIUDAD = {
    # Datos de HSP promedio mensual (kWh/m²/día)
    # Fuente: PVGIS y promedios históricos de radiación solar.
    "MEDELLIN":    [4.39, 4.49, 4.51, 4.31, 4.20, 4.35, 4.80, 4.71, 4.40, 4.15, 4.05, 4.19],
    "BOGOTA":      [4.35, 4.48, 4.21, 3.89, 3.70, 3.81, 4.25, 4.30, 4.10, 3.95, 3.88, 4.15],
    "CALI":        [4.80, 4.95, 4.85, 4.60, 4.50, 4.75, 5.10, 5.05, 4.80, 4.65, 4.55, 4.68],
    "BARRANQUILLA":[5.10, 5.35, 5.80, 5.90, 5.75, 5.85, 5.95, 5.80, 5.45, 5.15, 4.90, 4.95],
    "BUCARAMANGA": [4.60, 4.75, 4.50, 4.30, 4.15, 4.25, 4.70, 4.80, 4.65, 4.40, 4.30, 4.45],
    "CARTAGENA":   [5.30, 5.60, 6.10, 6.20, 6.00, 6.15, 6.25, 6.10, 5.70, 5.40, 5.10, 5.15],
    "PEREIRA":     [4.55, 4.68, 4.60, 4.40, 4.30, 4.45, 4.90, 4.85, 4.55, 4.35, 4.25, 4.40]
}

PROMEDIOS_COSTO = {
    'Equipos': 24.33,
    'Materiales': 16.67,
    'IVA (Impuestos)': 6.28,
    'Margen (Ganancia)': 16.38
}

ESTRUCTURA_CARPETAS = {
    "00_Contacto_y_Venta": {},
    "01_Propuesta_y_Contratacion": {},
    "02_Ingenieria_y_Diseno": {
        "Fichas_Tecnicas": {
            "Paneles": {}, "Inversores": {}, "Estructura_Soporte": {},
            "Tableros_y_Protecciones": {}, "Cableado": {}
        },
        "Memorias_de_Calculo": {},
        "Planos_y_Diagramas": {}
    },
    "03_Adquisiciones_y_Logistica": {},
    "04_Permisos_y_Legal": {},
    "05_Instalacion_y_Construccion": {
        "Reportes_Fotograficos": {}, "Informes_Diarios_Avance": {}
    },
    "06_Puesta_en_Marcha_y_Entrega": {},
    "07_Operacion_y_Mantenimiento_OM": {},
    "08_Administrativo_y_Financiero": {},
    "09_Material_Grafico_y_Marketing": {}
}

HSP_POR_CIUDAD = {
    "MEDELLIN": 4.5, "BOGOTA": 4.0, "CALI": 4.8, "BARRANQUILLA": 5.2,
    "BUCARAMANGA": 4.3, "CARTAGENA": 5.3, "PEREIRA": 4.6
}

