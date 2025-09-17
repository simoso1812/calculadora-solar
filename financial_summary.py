"""
Financial Summary Generator for Solar Calculator
Creates comprehensive financial reports for financiers
"""

import json
import pandas as pd
import numpy as np
from fpdf import FPDF
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Any, Optional
import datetime

class FinancialSummaryGenerator:
    """
    Generates comprehensive financial summaries for solar projects
    """

    def __init__(self):
        self.font_family = 'Arial'

    def generate_financial_summary(self, project_data: Dict, scenario_data: Dict = None,
                                 calculation_data: Dict = None) -> bytes:
        """
        Generate comprehensive financial summary PDF

        Args:
            project_data: Project information
            scenario_data: Scenario-specific data (optional)
            calculation_data: Base calculation results

        Returns:
            PDF bytes
        """
        pdf = FPDF()
        pdf.add_page()

        # Title
        pdf.set_font(self.font_family, 'B', 16)
        pdf.cell(0, 10, '💼 RESUMEN FINANCIERO PARA FINANCIEROS', 0, 1, 'C')
        pdf.ln(10)

        # Project Information
        self._add_project_info(pdf, project_data)

        # Financial Metrics Summary
        if calculation_data and 'results_data' in calculation_data:
            results = calculation_data['results_data']
            self._add_financial_metrics(pdf, results)

        # Cost Breakdown Analysis
        if calculation_data:
            self._add_cost_breakdown(pdf, calculation_data)

        # Cash Flow Projections
        if calculation_data and 'results_data' in calculation_data:
            results = calculation_data['results_data']
            self._add_cash_flow_projections(pdf, results)

        # Sensitivity Analysis
        if scenario_data:
            self._add_sensitivity_analysis(pdf, scenario_data)

        # Additional Metrics
        if calculation_data:
            self._add_additional_metrics(pdf, calculation_data)

        # Recommendations
        self._add_recommendations(pdf)

        return pdf.output(dest='S').encode('latin-1')

    def _add_project_info(self, pdf: FPDF, project_data: Dict):
        """Add project information section"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '📊 INFORMACIÓN DEL PROYECTO', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 12)

        info_items = [
            ('Cliente:', project_data.get('client_name', 'N/A')),
            ('Proyecto:', project_data.get('project_name', 'N/A')),
            ('Ubicación:', project_data.get('location', 'N/A')),
            ('Fecha de Análisis:', datetime.datetime.now().strftime('%d/%m/%Y')),
            ('ID del Proyecto:', project_data.get('project_id', 'N/A'))
        ]

        for label, value in info_items:
            pdf.cell(50, 8, label, 0, 0)
            pdf.cell(0, 8, str(value), 0, 1)

        pdf.ln(10)

    def _add_financial_metrics(self, pdf: FPDF, results: Dict):
        """Add key financial metrics section"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '🎯 MÉTRICAS FINANCIERAS CLAVE', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 12)

        # Extract key metrics
        tir = results.get('tir', 0)
        vpn = results.get('vpn', 0)
        payback = results.get('payback', 0)
        lcoe = results.get('lcoe', 0)
        valor_proyecto = results.get('valor_proyecto', 0)

        metrics = [
            ('Valor del Proyecto:', f"${valor_proyecto:,.0f} COP"),
            ('TIR (Tasa Interna de Retorno):', f"{tir:.2%}" if tir else "N/A"),
            ('VPN (Valor Presente Neto):', f"${vpn:,.0f} COP" if vpn else "N/A"),
            ('Payback (años):', f"{payback:.1f}" if payback else "N/A"),
            ('LCOE (Costo Nivelado de Energía):', f"${lcoe:,.0f} COP/kWh" if lcoe else "N/A")
        ]

        for label, value in metrics:
            pdf.cell(80, 8, label, 0, 0)
            pdf.cell(0, 8, value, 0, 1)

        pdf.ln(10)

    def _add_cost_breakdown(self, pdf: FPDF, calculation_data: Dict):
        """Add detailed cost breakdown analysis"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '💰 DESGLOSE DE COSTOS DETALLADO', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 10)

        # Create cost breakdown table
        if 'results_data' in calculation_data:
            results = calculation_data['results_data']

            # Equipment costs
            pdf.cell(0, 8, 'EQUIPOS Y MATERIALES:', 0, 1, 'L')
            pdf.cell(0, 8, f"• Sistema FV: ${results.get('valor_sistema_fv', 0):,.0f} COP", 0, 1)
            pdf.cell(0, 8, f"• Inversor: ${results.get('costo_inversor', 0):,.0f} COP", 0, 1)
            pdf.cell(0, 8, f"• Baterías: ${results.get('costo_baterias', 0):,.0f} COP", 0, 1)
            pdf.cell(0, 8, f"• Estructura y Montaje: ${results.get('costo_montaje', 0):,.0f} COP", 0, 1)

            pdf.ln(5)

            # Operational costs
            pdf.cell(0, 8, 'COSTOS OPERACIONALES (25 años):', 0, 1, 'L')
            pdf.cell(0, 8, f"• Mantenimiento Anual: ${results.get('mantenimiento_anual', 0):,.0f} COP", 0, 1)
            pdf.cell(0, 8, f"• Total Mantenimiento: ${results.get('total_mantenimiento', 0):,.0f} COP", 0, 1)

            pdf.ln(5)

            # Financing costs (if applicable)
            if results.get('usa_financiamiento', False):
                pdf.cell(0, 8, 'COSTOS DE FINANCIAMIENTO:', 0, 1, 'L')
                pdf.cell(0, 8, f"• Cuota Mensual: ${results.get('cuota_mensual', 0):,.0f} COP", 0, 1)
                pdf.cell(0, 8, f"• Total Intereses: ${results.get('total_intereses', 0):,.0f} COP", 0, 1)

        pdf.ln(10)

    def _add_cash_flow_projections(self, pdf: FPDF, results: Dict):
        """Add cash flow projections section"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '📈 PROYECCIONES DE FLUJO DE CAJA', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 10)

        # Summary of cash flows
        fcl = results.get('fcl', [])
        if fcl:
            # Initial investment
            pdf.cell(0, 8, f"• Inversión Inicial: ${fcl[0]:,.0f} COP", 0, 1)

            # Annual cash flows (show first 5 years and final year)
            pdf.cell(0, 8, 'FLUJO ANUAL PROMEDIO:', 0, 1, 'L')
            annual_flows = fcl[1:]  # Exclude initial investment
            avg_annual = sum(annual_flows) / len(annual_flows) if annual_flows else 0
            pdf.cell(0, 8, f"• Promedio Anual: ${avg_annual:,.0f} COP", 0, 1)

            # Year 1 specifically
            if len(annual_flows) > 0:
                pdf.cell(0, 8, f"• Año 1: ${annual_flows[0]:,.0f} COP", 0, 1)

            # Final year
            if len(annual_flows) > 1:
                pdf.cell(0, 8, f"• Año Final: ${annual_flows[-1]:,.0f} COP", 0, 1)

            # Cumulative at key points
            cumulative = np.cumsum(fcl)
            pdf.cell(0, 8, f"• Acumulado a 5 años: ${cumulative[5]:,.0f} COP", 0, 1)
            pdf.cell(0, 8, f"• Acumulado Final: ${cumulative[-1]:,.0f} COP", 0, 1)

        pdf.ln(10)

    def _add_sensitivity_analysis(self, pdf: FPDF, scenario_data: Dict):
        """Add sensitivity analysis section"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '🔍 ANÁLISIS DE SENSIBILIDAD', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 10)

        # Show different scenarios
        scenarios = scenario_data.get('scenarios', [])
        if scenarios:
            for scenario in scenarios[:3]:  # Show up to 3 scenarios
                pdf.cell(0, 8, f"ESCENARIO: {scenario.get('scenario_name', 'N/A')}", 0, 1, 'L')
                metrics = scenario.get('financial_metrics', {})

                tir = metrics.get('tir', 0)
                vpn = metrics.get('vpn', 0)
                payback = metrics.get('payback', 0)

                pdf.cell(0, 6, f"• TIR: {tir:.2%} | VPN: ${vpn:,.0f} | Payback: {payback:.1f} años", 0, 1)
                pdf.ln(2)

        pdf.ln(5)

        # Risk factors
        pdf.cell(0, 8, 'FACTORES DE RIESGO EVALUADOS:', 0, 1, 'L')
        pdf.cell(0, 6, '• Variación en precio de energía (+/- 20%)', 0, 1)
        pdf.cell(0, 6, '• Cambios en radiación solar (+/- 10%)', 0, 1)
        pdf.cell(0, 6, '• Incremento en costos de mantenimiento', 0, 1)
        pdf.cell(0, 6, '• Variaciones en tasas de descuento', 0, 1)

        pdf.ln(10)

    def _add_additional_metrics(self, pdf: FPDF, calculation_data: Dict):
        """Add additional financial and technical metrics"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '📊 MÉTRICAS ADICIONALES', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 10)

        if 'results_data' in calculation_data:
            results = calculation_data['results_data']

            # Technical metrics
            pdf.cell(0, 8, 'MÉTRICAS TÉCNICAS:', 0, 1, 'L')
            pdf.cell(0, 6, f"• Capacidad Instalada: {results.get('size', 0):.1f} kWp", 0, 1)
            pdf.cell(0, 6, f"• Generación Anual: {results.get('generacion_anual', 0):,.0f} kWh", 0, 1)
            pdf.cell(0, 6, f"• Eficiencia del Sistema: {results.get('eficiencia', 0):.1%}", 0, 1)

            pdf.ln(5)

            # Environmental metrics
            pdf.cell(0, 8, 'MÉTRICAS AMBIENTALES:', 0, 1, 'L')
            pdf.cell(0, 6, f"• CO2 Evitado Anual: {results.get('co2_anual', 0):,.0f} kg", 0, 1)
            pdf.cell(0, 6, f"• Árboles Equivalentes: {results.get('arboles', 0):.0f}", 0, 1)
            pdf.cell(0, 6, f"• Valor Carbono: ${results.get('valor_carbono', 0):,.0f} COP", 0, 1)

            pdf.ln(5)

            # Risk metrics
            pdf.cell(0, 8, 'MÉTRICAS DE RIESGO:', 0, 1, 'L')
            pdf.cell(0, 6, f"• Ratio Deuda/Capital: {results.get('debt_equity_ratio', 0):.2f}", 0, 1)
            pdf.cell(0, 6, f"• Cobertura de Intereses: {results.get('interest_coverage', 0):.1f}x", 0, 1)
            pdf.cell(0, 6, f"• Punto de Equilibrio: {results.get('break_even_year', 0)} años", 0, 1)

        pdf.ln(10)

    def _add_recommendations(self, pdf: FPDF):
        """Add investment recommendations section"""
        pdf.set_font(self.font_family, 'B', 14)
        pdf.cell(0, 10, '🎯 RECOMENDACIONES DE INVERSIÓN', 0, 1)
        pdf.ln(5)

        pdf.set_font(self.font_family, '', 10)

        recommendations = [
            "✅ TIR superior al 10% indica rentabilidad atractiva",
            "✅ Payback menor a 8 años es considerado óptimo",
            "✅ VPN positivo confirma viabilidad del proyecto",
            "✅ Diversificación geográfica reduce riesgo de radiación",
            "✅ Contratos de suministro de energía a largo plazo recomendados",
            "✅ Monitoreo continuo de desempeño del sistema",
            "✅ Plan de mantenimiento preventivo obligatorio"
        ]

        for rec in recommendations:
            pdf.cell(0, 6, rec, 0, 1)

        pdf.ln(10)

        # Footer
        pdf.set_font(self.font_family, 'I', 8)
        pdf.cell(0, 10, f'Reporte generado el {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')

    def generate_excel_summary(self, project_data: Dict, scenario_data: Dict = None,
                             calculation_data: Dict = None) -> bytes:
        """
        Generate Excel version of financial summary

        Returns:
            Excel file bytes
        """
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Project Info Sheet
            project_df = pd.DataFrame([{
                'Cliente': project_data.get('client_name', ''),
                'Proyecto': project_data.get('project_name', ''),
                'Ubicación': project_data.get('location', ''),
                'Fecha': datetime.datetime.now().strftime('%d/%m/%Y'),
                'ID Proyecto': project_data.get('project_id', '')
            }])
            project_df.to_excel(writer, sheet_name='Información', index=False)

            # Financial Metrics Sheet
            if calculation_data and 'results_data' in calculation_data:
                results = calculation_data['results_data']
                metrics_df = pd.DataFrame([{
                    'Métrica': ['Valor Proyecto', 'TIR', 'VPN', 'Payback', 'LCOE'],
                    'Valor': [
                        f"${results.get('valor_proyecto', 0):,.0f}",
                        f"{results.get('tir', 0):.2%}",
                        f"${results.get('vpn', 0):,.0f}",
                        f"{results.get('payback', 0):.1f} años",
                        f"${results.get('lcoe', 0):,.0f}"
                    ]
                }])
                metrics_df.to_excel(writer, sheet_name='Métricas', index=False)

            # Cash Flow Sheet
            if calculation_data and 'results_data' in calculation_data:
                results = calculation_data['results_data']
                fcl = results.get('fcl', [])
                if fcl:
                    years = ['Inicial'] + [f'Año {i}' for i in range(1, len(fcl))]
                    cf_df = pd.DataFrame({
                        'Período': years,
                        'Flujo de Caja': fcl,
                        'Acumulado': np.cumsum(fcl)
                    })
                    cf_df.to_excel(writer, sheet_name='Flujo_Caja', index=False)

        output.seek(0)
        return output.getvalue()

# Global instance
financial_summary_generator = FinancialSummaryGenerator()