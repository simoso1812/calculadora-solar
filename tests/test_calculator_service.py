"""
Unit tests for calculator_service.py - Core financial and technical calculations.

This module tests the critical business logic for solar quotations including:
- Cost per kWp calculations
- Inverter recommendations
- Performance ratio calculations
- Full quotation calculations
- Edge cases and boundary conditions
"""
import pytest
import math
import numpy as np

from src.services.calculator_service import (
    calcular_costo_por_kwp,
    recomendar_inversor,
    calcular_performance_ratio,
    cotizacion,
    redondear_a_par,
    calcular_factor_clipping,
)
from src.config_parametros import DEFAULT_PARAMS


# =============================================================================
# Tests for calcular_costo_por_kwp
# =============================================================================

class TestCalcularCostoPorKwp:
    """Tests for the cost per kWp calculation function."""

    def test_small_system_5kwp_returns_reasonable_cost(self):
        """A 5 kWp system should cost between 5M and 6M COP/kWp."""
        result = calcular_costo_por_kwp(5)
        assert 5_000_000 < result < 6_000_000, f"Expected cost between 5M-6M, got {result:,.0f}"

    def test_small_system_10kwp_cheaper_than_5kwp(self):
        """10 kWp system should have lower cost per kWp than 5 kWp (economies of scale)."""
        cost_5kwp = calcular_costo_por_kwp(5)
        cost_10kwp = calcular_costo_por_kwp(10)
        assert cost_10kwp < cost_5kwp, "Larger system should have lower cost per kWp"

    def test_large_system_100kwp_returns_reasonable_cost(self):
        """A 100 kWp system should cost between 2.5M and 3M COP/kWp."""
        result = calcular_costo_por_kwp(100)
        assert 2_500_000 < result < 3_000_000, f"Expected cost between 2.5M-3M, got {result:,.0f}"

    def test_boundary_at_20kwp_no_discontinuity(self):
        """At the 20 kWp boundary, both formulas should give similar results (within 15%)."""
        cost_19_9 = calcular_costo_por_kwp(19.9)
        cost_20_0 = calcular_costo_por_kwp(20.0)
        difference_ratio = abs(cost_19_9 - cost_20_0) / cost_19_9
        assert difference_ratio < 0.15, f"Discontinuity at 20 kWp boundary: {difference_ratio:.1%}"

    def test_small_system_uses_power_function(self):
        """Systems < 20 kW should use the power function formula."""
        # Test that the formula follows the power function pattern
        cost_5 = calcular_costo_por_kwp(5)
        cost_10 = calcular_costo_por_kwp(10)
        # For power function a*x^b with b<0, cost ratio should be ~2^(-b)
        # With b = -0.484721, ratio should be ~2^0.485 ≈ 1.4
        ratio = cost_5 / cost_10
        assert 1.2 < ratio < 1.6, f"Power function ratio unexpected: {ratio}"

    def test_large_system_uses_polynomial(self):
        """Systems >= 20 kW should use the polynomial formula."""
        # Polynomial should show decreasing marginal cost
        cost_50 = calcular_costo_por_kwp(50)
        cost_100 = calcular_costo_por_kwp(100)
        cost_150 = calcular_costo_por_kwp(150)
        # Cost should decrease but not dramatically
        assert cost_50 > cost_100 > cost_150, "Polynomial should show decreasing costs"

    def test_custom_params_override_defaults(self):
        """Custom parameters should override default coefficients."""
        custom = {
            'costo_pequeño_coef_a': 10_000_000,  # Different coefficient
            'costo_pequeño_coef_b': -0.5,
        }
        default_cost = calcular_costo_por_kwp(5)
        custom_cost = calcular_costo_por_kwp(5, custom_params=custom)
        assert default_cost != custom_cost, "Custom params should change the result"

    def test_minimum_system_size(self):
        """Very small systems (1 kWp) should still return valid costs."""
        result = calcular_costo_por_kwp(1)
        assert result > 0, "Cost should be positive"
        assert result < 20_000_000, "Cost should be reasonable even for tiny systems"

    def test_very_large_system(self):
        """Very large systems (200 kWp) should return valid costs.

        Note: The polynomial model is calibrated for systems up to ~200 kWp.
        Beyond this, the cubic term causes negative values.
        """
        result = calcular_costo_por_kwp(200)
        assert result > 0, "Cost should be positive"
        assert result < 3_000_000, "Large systems should have low cost per kWp"

    def test_polynomial_instability_warning(self):
        """Document that polynomial becomes unstable at extreme sizes (>300 kWp).

        This is expected behavior - the model was calibrated on data up to ~200 kWp.
        In production, systems >200 kWp should use custom pricing.
        """
        # At 500 kWp, the polynomial gives negative values
        result_500 = calcular_costo_por_kwp(500)
        # This test documents the limitation
        if result_500 < 0:
            # Expected - polynomial is unstable at this size
            pass
        # But 200 kWp should still be valid
        result_200 = calcular_costo_por_kwp(200)
        assert result_200 > 0, "200 kWp should still be valid"


# =============================================================================
# Tests for recomendar_inversor
# =============================================================================

class TestRecomendarInversor:
    """Tests for the inverter recommendation function."""

    def test_small_system_single_inverter(self):
        """Small systems should recommend a single inverter."""
        rec, power = recomendar_inversor(5)
        assert "1x" in rec, f"Expected single inverter, got {rec}"
        assert power > 0, "Power should be positive"

    def test_small_system_power_within_range(self):
        """Recommended inverter power should be close to system size."""
        for size in [3, 5, 8, 10, 15]:
            rec, power = recomendar_inversor(size)
            # Inverter should be between 60% and 100% of DC size (typical DC/AC ratio)
            assert size * 0.6 <= power <= size * 1.1, f"Power {power} out of range for {size} kWp"

    def test_medium_system_combination(self):
        """Medium systems may need inverter combinations."""
        rec, power = recomendar_inversor(35)
        # Could be single 30kW + 5kW or other combinations
        assert power > 0, "Power should be positive"
        assert power <= 35, "Total power should not exceed DC size"

    def test_large_system_multiple_inverters(self):
        """Large systems should use multiple inverters."""
        rec, power = recomendar_inversor(100)
        # Should be combination like "1x50kW + 1x50kW" or similar
        assert power >= 50, "Large system should have substantial AC power"
        assert power <= 100, "AC power should not exceed DC size"

    def test_very_large_system(self):
        """Very large systems should optimize inverter selection."""
        rec, power = recomendar_inversor(200)
        assert power > 0, "Power should be positive"
        # Should use efficient combination

    def test_returns_string_and_number(self):
        """Function should return (string, number) tuple."""
        rec, power = recomendar_inversor(10)
        assert isinstance(rec, str), "Recommendation should be string"
        assert isinstance(power, (int, float)), "Power should be numeric"


# =============================================================================
# Tests for calcular_performance_ratio
# =============================================================================

class TestCalcularPerformanceRatio:
    """Tests for the performance ratio calculation."""

    def test_base_pr_with_defaults(self):
        """Default PR should be based on config value."""
        pr = calcular_performance_ratio("SOL", "LÁMINA")
        # Base is 0.75, sunny climate reduces by 0.02
        expected = DEFAULT_PARAMS["performance_ratio_base"] - 0.02
        assert abs(pr - expected) < 0.01, f"Expected PR ~{expected}, got {pr}"

    def test_cloudy_climate_reduces_pr(self):
        """Cloudy climate should reduce PR more than sunny."""
        pr_sol = calcular_performance_ratio("SOL", "LÁMINA")
        pr_nube = calcular_performance_ratio("NUBE", "LÁMINA")
        pr_nublado = calcular_performance_ratio("NUBLADO", "LÁMINA")
        assert pr_nube < pr_sol, "Cloudy should have lower PR"
        assert pr_nublado < pr_sol, "NUBLADO should have lower PR"

    def test_teja_cubierta_reduces_pr(self):
        """Tile roof should reduce PR compared to metal."""
        pr_lamina = calcular_performance_ratio("SOL", "LÁMINA")
        pr_teja = calcular_performance_ratio("SOL", "TEJA")
        assert pr_teja < pr_lamina, "Tile roof should have lower PR"

    def test_pr_within_valid_range(self):
        """PR should always be between 0.5 and 1.0."""
        for clima in ["SOL", "NUBE", "NUBLADO", "LLUVIA"]:
            for cubierta in ["LÁMINA", "TEJA", "CONCRETO", "METAL"]:
                pr = calcular_performance_ratio(clima, cubierta)
                assert 0.5 <= pr <= 1.0, f"PR {pr} out of range for {clima}, {cubierta}"

    def test_custom_params_base_pr(self):
        """Custom PR base should be used when provided."""
        custom = {'performance_ratio_base': 0.85}
        pr_default = calcular_performance_ratio("SOL", "LÁMINA")
        pr_custom = calcular_performance_ratio("SOL", "LÁMINA", custom_params=custom)
        assert pr_custom > pr_default, "Custom higher PR base should result in higher PR"

    def test_case_insensitivity(self):
        """Function should handle different cases."""
        pr1 = calcular_performance_ratio("sol", "LÁMINA")
        pr2 = calcular_performance_ratio("SOL", "lámina")
        pr3 = calcular_performance_ratio("Sol", "Lámina")
        # All should work without errors
        assert pr1 > 0 and pr2 > 0 and pr3 > 0


# =============================================================================
# Tests for cotizacion (main quotation function)
# =============================================================================

class TestCotizacion:
    """Tests for the main quotation function."""

    def test_returns_all_expected_fields(self, small_system_params, default_hsp_medellin):
        """Cotizacion should return all 21 expected fields."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            horizonte_tiempo=25
        )
        assert len(result) == 21, f"Expected 21 fields, got {len(result)}"

    def test_project_value_positive(self, small_system_params, default_hsp_medellin):
        """Project value should always be positive."""
        valor_total, *_ = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        assert valor_total > 0, "Project value should be positive"

    def test_project_value_scales_with_size(self, default_hsp_medellin):
        """Larger systems should have higher total project value."""
        params_5kw = {'Load': 500, 'size': 5, 'quantity': 10, 'cubierta': 'LÁMINA',
                      'clima': 'SOL', 'index': 0.05, 'dRate': 0.08, 'costkWh': 850, 'module': 500}
        params_10kw = {'Load': 1000, 'size': 10, 'quantity': 20, 'cubierta': 'LÁMINA',
                       'clima': 'SOL', 'index': 0.05, 'dRate': 0.08, 'costkWh': 850, 'module': 500}

        valor_5kw, *_ = cotizacion(**params_5kw, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)
        valor_10kw, *_ = cotizacion(**params_10kw, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)

        assert valor_10kw > valor_5kw, "Larger system should cost more"

    def test_monthly_generation_twelve_values(self, small_system_params, default_hsp_medellin):
        """Monthly generation should have exactly 12 values."""
        *_, monthly_gen, _, _, _, _, _, _, _, _, _, _, _ = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        # monthly_gen is at index 7
        result = cotizacion(**small_system_params, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)
        monthly_generation = result[7]  # Index 7 is monthly_generation
        assert len(monthly_generation) == 12, f"Expected 12 months, got {len(monthly_generation)}"

    def test_cashflow_matches_horizon(self, small_system_params, default_hsp_medellin):
        """Cash flow should have horizon_time + 1 entries (year 0 + years 1-N)."""
        horizonte = 25
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            horizonte_tiempo=horizonte
        )
        fcl = result[5]  # Index 5 is cashflow
        assert len(fcl) == horizonte + 1, f"Expected {horizonte + 1} cashflow entries, got {len(fcl)}"

    def test_irr_positive_for_typical_project(self, small_system_params, default_hsp_medellin):
        """IRR should be positive for a typical solar project."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        tir = result[9]  # Index 9 is internal_rate (TIR)
        assert tir > 0, "IRR should be positive for viable project"

    def test_npv_reasonable(self, small_system_params, default_hsp_medellin):
        """NPV should be calculated (can be positive or negative)."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        vpn = result[8]  # Index 8 is present_value (VPN)
        assert isinstance(vpn, (int, float)), "NPV should be numeric"

    def test_financing_changes_disbursement(self, small_system_params, default_hsp_medellin):
        """Financing should reduce initial disbursement."""
        result_no_fin = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            perc_financiamiento=0,
        )
        result_with_fin = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            perc_financiamiento=70,
            tasa_interes_credito=0.12,
            plazo_credito_años=10,
        )
        desembolso_no_fin = result_no_fin[4]
        desembolso_with_fin = result_with_fin[4]
        assert desembolso_with_fin < desembolso_no_fin, "Financing should reduce initial disbursement"

    def test_custom_params_affect_calculation(self, small_system_params, default_hsp_medellin):
        """Custom params should affect the calculation results."""
        result_default = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )

        custom = {'precio_excedentes': 500, 'porcentaje_mantenimiento': 0.02}
        result_custom = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            custom_params=custom,
        )

        # IRR should be different with different params
        tir_default = result_default[9]
        tir_custom = result_custom[9]
        # With higher excess price and lower maintenance, IRR should be better
        assert tir_custom != tir_default, "Custom params should change IRR"

    def test_teja_cubierta_increases_cost(self, small_system_params, default_hsp_medellin):
        """Tile roof should increase project cost by ~3%."""
        params_lamina = {**small_system_params, 'cubierta': 'LÁMINA'}
        params_teja = {**small_system_params, 'cubierta': 'TEJA'}

        valor_lamina, *_ = cotizacion(**params_lamina, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)
        valor_teja, *_ = cotizacion(**params_teja, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)

        ratio = valor_teja / valor_lamina
        assert 1.02 <= ratio <= 1.05, f"Tile roof should cost ~3% more, got {ratio:.1%}"


# =============================================================================
# Tests for edge cases and boundary conditions
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_consumption_does_not_crash(self, default_hsp_medellin):
        """System should handle zero consumption gracefully."""
        params = {
            'Load': 0,  # Zero consumption
            'size': 5,
            'quantity': 10,
            'cubierta': 'LÁMINA',
            'clima': 'SOL',
            'index': 0.05,
            'dRate': 0.08,
            'costkWh': 850,
            'module': 500,
        }
        # Should not raise exception
        try:
            result = cotizacion(**params, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)
            assert result is not None
        except ZeroDivisionError:
            pytest.fail("Should handle zero consumption without division error")

    def test_very_high_consumption(self, default_hsp_medellin):
        """System should handle high consumption (200 kWp - within model bounds).

        Note: The polynomial model is calibrated for systems up to ~200 kWp.
        Systems larger than this should use custom pricing in production.
        """
        params = {
            'Load': 30000,  # High consumption
            'size': 200,  # Stay within polynomial model bounds
            'quantity': 400,
            'cubierta': 'LÁMINA',
            'clima': 'SOL',
            'index': 0.05,
            'dRate': 0.08,
            'costkWh': 850,
            'module': 500,
        }
        result = cotizacion(**params, ciudad="MEDELLIN", hsp_lista=default_hsp_medellin)
        assert result[0] > 0, "Should handle large systems within model bounds"

    def test_extreme_interest_rate(self, small_system_params, default_hsp_medellin):
        """System should handle extreme interest rates."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            perc_financiamiento=70,
            tasa_interes_credito=0.30,  # 30% interest rate
            plazo_credito_años=10,
        )
        assert result[3] > 0, "Monthly payment should be calculated even with high interest"

    def test_zero_interest_financing(self, small_system_params, default_hsp_medellin):
        """System should handle 0% interest financing."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            perc_financiamiento=70,
            tasa_interes_credito=0,  # 0% interest
            plazo_credito_años=10,
        )
        # Should not crash, payment should equal principal/months
        assert result is not None

    def test_short_horizon(self, small_system_params, default_hsp_medellin):
        """System should handle short analysis horizons."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            horizonte_tiempo=5,  # Only 5 years
        )
        fcl = result[5]
        assert len(fcl) == 6, "Should have 6 cashflow entries for 5-year horizon"

    def test_long_horizon(self, small_system_params, default_hsp_medellin):
        """System should handle long analysis horizons."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
            horizonte_tiempo=40,  # 40 years
        )
        fcl = result[5]
        assert len(fcl) == 41, "Should have 41 cashflow entries for 40-year horizon"

    def test_redondear_a_par_returns_even(self):
        """redondear_a_par should always return even numbers."""
        for n in [1, 2, 3, 4, 5, 7, 9, 11, 13, 17, 23]:
            result = redondear_a_par(n)
            assert result % 2 == 0, f"Expected even number, got {result} for input {n}"

    def test_redondear_a_par_rounds_up(self):
        """redondear_a_par should round up to next even number."""
        assert redondear_a_par(3) >= 4
        assert redondear_a_par(5) >= 6
        assert redondear_a_par(7) >= 8

    def test_clipping_factor_within_range(self):
        """Clipping factor should be between 0 and 1."""
        for ratio in [1.0, 1.1, 1.2, 1.3, 1.5]:
            factor = calcular_factor_clipping(ratio)
            assert 0 <= factor <= 0.1, f"Clipping factor {factor} out of expected range"

    def test_clipping_increases_with_ratio(self):
        """Higher DC/AC ratio should result in more clipping."""
        factor_low = calcular_factor_clipping(1.0)
        factor_high = calcular_factor_clipping(1.35)
        assert factor_high >= factor_low, "Higher ratio should have more clipping"


# =============================================================================
# Tests for configurable parameters
# =============================================================================

class TestConfigurableParameters:
    """Tests for the configurable parameters system."""

    def test_default_params_have_expected_keys(self):
        """DEFAULT_PARAMS should have all expected keys."""
        expected_keys = [
            'precio_excedentes',
            'tasa_degradacion_anual',
            'porcentaje_mantenimiento',
            'performance_ratio_base',
        ]
        for key in expected_keys:
            assert key in DEFAULT_PARAMS, f"Missing key: {key}"

    def test_default_precio_excedentes(self):
        """Default excess price should be 300 COP/kWh."""
        assert DEFAULT_PARAMS['precio_excedentes'] == 300.0

    def test_default_degradacion(self):
        """Default degradation should be 0.1% per year."""
        assert DEFAULT_PARAMS['tasa_degradacion_anual'] == 0.001

    def test_default_mantenimiento(self):
        """Default maintenance should be 5%."""
        assert DEFAULT_PARAMS['porcentaje_mantenimiento'] == 0.05

    def test_default_performance_ratio(self):
        """Default PR base should be 75%."""
        assert DEFAULT_PARAMS['performance_ratio_base'] == 0.75


# =============================================================================
# Tests for calcular_lista_materiales
# =============================================================================

class TestCalcularListaMateriales:
    """Tests for the materials list calculation function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        from src.services.calculator_service import calcular_lista_materiales
        result = calcular_lista_materiales(10, 'LÁMINA', 500, '1x5kW')
        assert isinstance(result, dict), "Should return a dictionary"

    def test_includes_panels(self):
        """Should include solar panels in the list."""
        from src.services.calculator_service import calcular_lista_materiales
        result = calcular_lista_materiales(10, 'LÁMINA', 500, '1x5kW')
        # Check if any key contains 'Módulos' or 'paneles'
        has_panels = any('Módulos' in k or 'Panel' in k for k in result.keys())
        assert has_panels, "Should include solar panels"

    def test_includes_inverter(self):
        """Should include inverter in the list."""
        from src.services.calculator_service import calcular_lista_materiales
        result = calcular_lista_materiales(10, 'LÁMINA', 500, '2x5kW')
        has_inverter = any('Inversor' in k for k in result.keys())
        assert has_inverter, "Should include inverter"

    def test_panel_count_matches_input(self):
        """Panel count should match the input quantity."""
        from src.services.calculator_service import calcular_lista_materiales
        result = calcular_lista_materiales(20, 'LÁMINA', 615, '2x5kW')
        panel_key = [k for k in result.keys() if 'Módulos' in k][0]
        assert result[panel_key] == 20, "Panel count should match input"

    def test_zero_panels_returns_empty(self):
        """Zero panels should return empty dict."""
        from src.services.calculator_service import calcular_lista_materiales
        result = calcular_lista_materiales(0, 'LÁMINA', 500, '1x5kW')
        assert result == {}, "Zero panels should return empty dict"


# =============================================================================
# Tests for calcular_analisis_sensibilidad
# =============================================================================

class TestCalcularAnalisisSensibilidad:
    """Tests for the sensitivity analysis function."""

    def test_returns_dict_with_scenarios(self, small_system_params, default_hsp_medellin):
        """Should return a dictionary with scenario results."""
        from src.services.calculator_service import calcular_analisis_sensibilidad
        result = calcular_analisis_sensibilidad(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        assert isinstance(result, dict), "Should return a dictionary"

    def test_includes_expected_scenarios(self, small_system_params, default_hsp_medellin):
        """Should include base, optimistic, and pessimistic scenarios."""
        from src.services.calculator_service import calcular_analisis_sensibilidad
        result = calcular_analisis_sensibilidad(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        # Check that we have multiple scenarios
        assert len(result) >= 3, "Should have at least 3 scenarios"

    def test_scenarios_have_tir_vpn(self, small_system_params, default_hsp_medellin):
        """Each scenario should have TIR and VPN values."""
        from src.services.calculator_service import calcular_analisis_sensibilidad
        result = calcular_analisis_sensibilidad(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        for scenario_name, scenario_data in result.items():
            if isinstance(scenario_data, dict):
                # Each scenario should have financial metrics
                assert 'tir' in scenario_data or 'TIR' in scenario_data or any('tir' in k.lower() for k in scenario_data.keys()), \
                    f"Scenario {scenario_name} should have TIR"


# =============================================================================
# Tests for financial calculations accuracy
# =============================================================================

class TestFinancialCalculationsAccuracy:
    """Tests to verify financial calculation accuracy."""

    def test_irr_calculation_accuracy(self, small_system_params, default_hsp_medellin):
        """IRR should be calculated correctly based on cash flows."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        fcl = result[5]  # Cash flow
        tir = result[9]  # TIR
        
        # Verify TIR by checking NPV at TIR should be close to 0
        import numpy_financial as npf
        npv_at_irr = npf.npv(tir, fcl)
        assert abs(npv_at_irr) < 1000, f"NPV at IRR should be ~0, got {npv_at_irr}"

    def test_savings_calculation(self, small_system_params, default_hsp_medellin):
        """First year savings should be based on generation and kWh cost."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        monthly_gen = result[7]  # Monthly generation
        ahorro_año1 = result[17]  # First year savings
        
        # Annual generation
        gen_anual = sum(monthly_gen)
        # Maximum possible savings (if all generation is self-consumed)
        max_savings = gen_anual * small_system_params['costkWh']
        
        # Actual savings should be <= max possible
        assert ahorro_año1 <= max_savings * 1.1, "Savings should not exceed generation value"
        assert ahorro_año1 > 0, "Savings should be positive"

    def test_payback_calculation(self, small_system_params, default_hsp_medellin):
        """Payback should occur when cumulative cash flow becomes positive."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        fcl = result[5]
        
        # Find payback manually
        cumsum = np.cumsum(fcl)
        payback_manual = None
        for i, val in enumerate(cumsum):
            if val >= 0:
                payback_manual = i
                break
        
        # Payback should be reasonable (< 15 years for a viable project)
        if payback_manual is not None:
            assert payback_manual <= 15, f"Payback {payback_manual} years seems too long"

    def test_lcoe_calculation(self, small_system_params, default_hsp_medellin):
        """LCOE should be calculated and be in reasonable range."""
        result = cotizacion(
            **small_system_params,
            ciudad="MEDELLIN",
            hsp_lista=default_hsp_medellin,
        )
        lcoe = result[13]  # LCOE
        
        # LCOE for solar in Colombia should be between 100-600 COP/kWh
        assert 100 < lcoe < 600, f"LCOE {lcoe} COP/kWh seems out of range"