"""
Configuración de parámetros ajustables para la Calculadora Solar.

Este módulo centraliza todos los parámetros que pueden ser configurados
por el usuario o que varían según el mercado/cliente.

Para modificar los valores por defecto, cambia los valores en DEFAULT_PARAMS.
"""

# =============================================================================
# PARÁMETROS CONFIGURABLES POR DEFECTO
# =============================================================================

DEFAULT_PARAMS = {
    # --- Parámetros de Venta de Excedentes ---
    "precio_excedentes": 300.0,  # COP/kWh - Precio de venta de energía excedente a la red

    # --- Parámetros de Degradación ---
    "tasa_degradacion_anual": 0.001,  # 0.1% por año - Pérdida de eficiencia de paneles

    # --- Parámetros de Mantenimiento ---
    "porcentaje_mantenimiento": 0.05,  # 5% del ahorro anual

    # --- Parámetros de Eficiencia ---
    "performance_ratio_base": 0.75,  # 75% - Eficiencia base del sistema
    "eficiencia_sistema_estimacion": 0.85,  # 85% - Para estimación inicial de tamaño

    # --- Parámetros de Costo ---
    # Coeficientes para sistemas pequeños (<20 kW): costo = a * size^b
    "costo_pequeño_coef_a": 11917544,
    "costo_pequeño_coef_b": -0.484721,

    # Coeficientes para sistemas grandes (>=20 kW): costo = ax³ + bx² + cx + d
    "costo_grande_coef_a": -0.265979,
    "costo_grande_coef_b": 103.58,
    "costo_grande_coef_c": -14285.52,
    "costo_grande_coef_d": 3286846.42,

    # Ajuste por tipo de cubierta
    "ajuste_cubierta_teja": 1.03,  # +3% para teja

    # --- Parámetros de Baterías ---
    "profundidad_descarga_default": 0.9,  # 90% DoD
    "eficiencia_bateria_default": 0.95,  # 95% eficiencia

    # --- Parámetros de Carbon ---
    "precio_certificado_carbono_cop": 95000,  # COP por tonelada CO2
    "precio_certificado_carbono_usd": 25.50,  # USD por tonelada CO2

    # --- Parámetros de O&M ---
    "porcentaje_om_anual": 0.02,  # 2% del CAPEX
}

# =============================================================================
# LÍMITES Y VALIDACIONES
# =============================================================================

PARAM_LIMITS = {
    "precio_excedentes": {"min": 0, "max": 2000, "step": 10},
    "tasa_degradacion_anual": {"min": 0.0001, "max": 0.01, "step": 0.0001},
    "porcentaje_mantenimiento": {"min": 0, "max": 0.15, "step": 0.01},
    "performance_ratio_base": {"min": 0.5, "max": 0.95, "step": 0.01},
}

# =============================================================================
# DESCRIPCIONES PARA UI
# =============================================================================

PARAM_DESCRIPTIONS = {
    "precio_excedentes": "Precio de venta de energía excedente a la red (COP/kWh). En Colombia típicamente entre 200-400 COP/kWh.",
    "tasa_degradacion_anual": "Pérdida de eficiencia anual de los paneles. Típicamente 0.1%-0.5% por año según fabricante.",
    "porcentaje_mantenimiento": "Porcentaje del ahorro anual destinado a mantenimiento. Típicamente 3-7%.",
    "performance_ratio_base": "Eficiencia base del sistema considerando pérdidas. Típicamente 70-80%.",
}

# =============================================================================
# FUNCIONES DE ACCESO
# =============================================================================

def get_param(name: str, custom_params: dict = None) -> float:
    """
    Obtiene el valor de un parámetro, priorizando valores personalizados.

    Args:
        name: Nombre del parámetro
        custom_params: Diccionario opcional con valores personalizados

    Returns:
        Valor del parámetro (personalizado si existe, default si no)
    """
    if custom_params and name in custom_params:
        return custom_params[name]
    return DEFAULT_PARAMS.get(name, 0)


def get_all_params(custom_params: dict = None) -> dict:
    """
    Obtiene todos los parámetros, combinando defaults con personalizados.

    Args:
        custom_params: Diccionario opcional con valores personalizados

    Returns:
        Diccionario con todos los parámetros
    """
    params = DEFAULT_PARAMS.copy()
    if custom_params:
        params.update(custom_params)
    return params


def validate_param(name: str, value: float) -> tuple:
    """
    Valida un parámetro contra sus límites.

    Args:
        name: Nombre del parámetro
        value: Valor a validar

    Returns:
        Tuple (is_valid, error_message)
    """
    if name not in PARAM_LIMITS:
        return True, ""

    limits = PARAM_LIMITS[name]
    if value < limits["min"]:
        return False, f"{name} debe ser >= {limits['min']}"
    if value > limits["max"]:
        return False, f"{name} debe ser <= {limits['max']}"

    return True, ""
