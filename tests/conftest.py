"""
Pytest configuration and shared fixtures for Calculadora Solar tests.
"""
import pytest
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def default_hsp_medellin():
    """HSP mensual típico para Medellín"""
    return [4.39, 4.39, 4.39, 4.08, 4.08, 4.14, 4.50, 4.72, 4.53, 4.08, 4.08, 4.80]


@pytest.fixture
def default_hsp_bogota():
    """HSP mensual típico para Bogotá"""
    return [3.70, 3.89, 3.83, 3.72, 3.58, 3.72, 4.00, 4.17, 4.03, 3.72, 3.61, 4.48]


@pytest.fixture
def small_system_params():
    """Parámetros típicos para un sistema residencial pequeño (5 kWp)"""
    return {
        'Load': 500,  # kWh/mes
        'size': 5.0,  # kWp
        'quantity': 10,  # paneles
        'cubierta': 'LÁMINA',
        'clima': 'SOL',
        'index': 0.05,  # 5% inflación
        'dRate': 0.08,  # 8% tasa de descuento
        'costkWh': 850,  # COP/kWh
        'module': 500,  # W por panel
    }


@pytest.fixture
def medium_system_params():
    """Parámetros típicos para un sistema comercial mediano (25 kWp)"""
    return {
        'Load': 3000,  # kWh/mes
        'size': 25.0,  # kWp
        'quantity': 50,  # paneles
        'cubierta': 'METAL',
        'clima': 'SOL',
        'index': 0.05,
        'dRate': 0.10,
        'costkWh': 750,
        'module': 500,
    }


@pytest.fixture
def large_system_params():
    """Parámetros típicos para un sistema industrial grande (100 kWp)"""
    return {
        'Load': 12000,  # kWh/mes
        'size': 100.0,  # kWp
        'quantity': 200,  # paneles
        'cubierta': 'CONCRETO',
        'clima': 'SOL',
        'index': 0.05,
        'dRate': 0.12,
        'costkWh': 650,
        'module': 500,
    }


@pytest.fixture
def custom_params_high_price():
    """Parámetros personalizados con precio de excedentes alto"""
    return {
        'precio_excedentes': 500,  # COP/kWh
        'tasa_degradacion_anual': 0.005,  # 0.5%
        'porcentaje_mantenimiento': 0.03,  # 3%
        'performance_ratio_base': 0.80,  # 80%
    }


@pytest.fixture
def custom_params_conservative():
    """Parámetros conservadores (peor caso)"""
    return {
        'precio_excedentes': 200,  # COP/kWh
        'tasa_degradacion_anual': 0.007,  # 0.7%
        'porcentaje_mantenimiento': 0.07,  # 7%
        'performance_ratio_base': 0.70,  # 70%
    }
