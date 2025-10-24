#!/usr/bin/env python3
"""
Test script for the new cash flow calculations with tax benefits and 6-month delay.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import cotizacion

def test_cash_flow_with_benefits():
    """Test the cash flow calculation with different benefit scenarios."""

    # Test parameters
    Load = 700  # kWh/month
    size = 10   # kWp
    quantity = 40  # panels
    cubierta = "LÁMINA"
    clima = "SOL"
    index = 0.05  # 5%
    dRate = 0.10  # 10%
    costkWh = 850  # COP/kWh
    module = 615  # W

    print("Testing Cash Flow Calculations with Tax Benefits and 6-Month Delay")
    print("=" * 80)

    # Test 1: No benefits (baseline)
    print("\nTest 1: No tax benefits, no delay")
    val1, size1, monto1, cuota1, desembolso1, fcl1, trees1, monthly_gen1, vpn1, tir1, cant1, life1, inv1, lcoe1, n1, hsp1, pot_ac1, ahorro1, area1, cap_bat1, carbon1 = cotizacion(
        Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
        ciudad="MEDELLIN",
        incluir_beneficios_tributarios=False,
        tipo_beneficio_tributario="deduccion_renta",
        demora_6_meses=False
    )

    print(f"TIR: {tir1:.1%}")
    print(f"VPN: ${vpn1:,.0f}")
    print(f"Payback: N/A")
    print(f"Year 1 cash flow: ${fcl1[1]:,.0f}")
    print(f"Year 2 cash flow: ${fcl1[2]:,.0f}")
    print(f"Year 3 cash flow: ${fcl1[3]:,.0f}")

    # Test 2: Income deduction benefit
    print("\nTest 2: Income deduction benefit (17.5% of indexed CAPEX in year 2)")
    val2, size2, monto2, cuota2, desembolso2, fcl2, trees2, monthly_gen2, vpn2, tir2, cant2, life2, inv2, lcoe2, n2, hsp2, pot_ac2, ahorro2, area2, cap_bat2, carbon2 = cotizacion(
        Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
        ciudad="MEDELLIN",
        incluir_beneficios_tributarios=True,
        tipo_beneficio_tributario="deduccion_renta",
        demora_6_meses=False
    )

    print(f"TIR: {tir2:.1%}")
    print(f"VPN: ${vpn2:,.0f}")
    print(f"Payback: N/A")
    benefit_year2 = fcl2[2] - fcl1[2]
    capex_indexed_year2 = val2 * ((1 + index) ** 2)
    expected_benefit = capex_indexed_year2 * 0.175
    print(f"Year 2 benefit: ${benefit_year2:,.0f} (expected: ${expected_benefit:,.0f})")
    print(f"Year 1 cash flow: ${fcl2[1]:,.0f}")
    print(f"Year 2 cash flow: ${fcl2[2]:,.0f}")
    print(f"Year 3 cash flow: ${fcl2[3]:,.0f}")

    # Test 3: Accelerated depreciation benefit
    print("\nTest 3: Accelerated depreciation benefit (33% of CAPEX in years 1-3)")
    val3, size3, monto3, cuota3, desembolso3, fcl3, trees3, monthly_gen3, vpn3, tir3, cant3, life3, inv3, lcoe3, n3, hsp3, pot_ac3, ahorro3, area3, cap_bat3, carbon3 = cotizacion(
        Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
        ciudad="MEDELLIN",
        incluir_beneficios_tributarios=True,
        tipo_beneficio_tributario="depreciacion_acelerada",
        demora_6_meses=False
    )

    print(f"TIR: {tir3:.1%}")
    print(f"VPN: ${vpn3:,.0f}")
    print(f"Payback: N/A")
    benefit_year1 = fcl3[1] - fcl1[1]
    benefit_year2 = fcl3[2] - fcl1[2]
    benefit_year3 = fcl3[3] - fcl1[3]
    expected_benefit = val3 * 0.33
    print(f"Year 1 benefit: ${benefit_year1:,.0f} (expected: ${expected_benefit:,.0f})")
    print(f"Year 2 benefit: ${benefit_year2:,.0f} (expected: ${expected_benefit:,.0f})")
    print(f"Year 3 benefit: ${benefit_year3:,.0f} (expected: ${expected_benefit:,.0f})")

    # Test 4: 6-month delay
    print("\nTest 4: 6-month delay (50% reduction in year 1 benefits)")
    val4, size4, monto4, cuota4, desembolso4, fcl4, trees4, monthly_gen4, vpn4, tir4, cant4, life4, inv4, lcoe4, n4, hsp4, pot_ac4, ahorro4, area4, cap_bat4, carbon4 = cotizacion(
        Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
        ciudad="MEDELLIN",
        incluir_beneficios_tributarios=False,
        tipo_beneficio_tributario="deduccion_renta",
        demora_6_meses=True
    )

    print(f"TIR: {tir4:.1%}")
    print(f"VPN: ${vpn4:,.0f}")
    print(f"Payback: N/A")
    year1_reduction = fcl1[1] - fcl4[1]
    expected_reduction = fcl1[1] * 0.5
    print(f"Year 1 reduction: ${year1_reduction:,.0f} (expected: ${expected_reduction:,.0f})")
    print(f"Year 1 cash flow: ${fcl4[1]:,.0f}")
    print(f"Year 2 cash flow: ${fcl4[2]:,.0f}")
    print(f"Year 3 cash flow: ${fcl4[3]:,.0f}")

    # Test 5: Combined benefits
    print("\nTest 5: Combined - Income deduction + 6-month delay")
    val5, size5, monto5, cuota5, desembolso5, fcl5, trees5, monthly_gen5, vpn5, tir5, cant5, life5, inv5, lcoe5, n5, hsp5, pot_ac5, ahorro5, area5, cap_bat5, carbon5 = cotizacion(
        Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
        ciudad="MEDELLIN",
        incluir_beneficios_tributarios=True,
        tipo_beneficio_tributario="deduccion_renta",
        demora_6_meses=True
    )

    print(f"TIR: {tir5:.1%}")
    print(f"VPN: ${vpn5:,.0f}")
    print(f"Payback: N/A")
    print(f"Year 1 cash flow: ${fcl5[1]:,.0f} (should be 50% of no-delay)")
    print(f"Year 2 cash flow: ${fcl5[2]:,.0f} (should include tax benefit)")

    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    test_cash_flow_with_benefits()