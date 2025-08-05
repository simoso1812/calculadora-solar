import streamlit as st
import numpy_financial as npf
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF

# ==============================================================================
# 1. COPIA Y PEGA AQUÍ TODAS TUS FUNCIONES
# (recomendar_inversor, cotizacion, generar_reporte_pdf, etc.)
# ==============================================================================

# Diccionario de Horas Sol Pico
HSP_POR_CIUDAD = {
    "MEDELLIN": 4.5, "BOGOTA": 4.0, "CALI": 4.8, "BARRANQUILLA": 5.2,
    "BUCARAMANGA": 4.3, "CARTAGENA": 5.3, "PEREIRA": 4.6
}

# Función para recomendar el inversor
def recomendar_inversor(size_kwp):
    inverters_disponibles = [3, 5, 6, 8, 10]
    min_ac_power = size_kwp / 1.2
    if size_kwp <= 12:
        for inv_kw in sorted(inverters_disponibles):
            if inv_kw >= min_ac_power: return f"1 inversor de {inv_kw} kW.", inv_kw
    recomendacion, potencia_restante = {}, min_ac_power
    for inv_kw in sorted(inverters_disponibles, reverse=True):
        if potencia_restante >= inv_kw:
            num = int(potencia_restante // inv_kw)
            recomendacion[inv_kw] = num
            potencia_restante -= num * inv_kw
    if potencia_restante > 0.1:
        inverter_para_resto = min(inverters_disponibles)
        for inv_kw in sorted(inverters_disponibles):
            if inv_kw >= potencia_restante: inverter_para_resto = inv_kw; break
        recomendacion[inverter_para_resto] = recomendacion.get(inverter_para_resto, 0) + 1
    if not recomendacion: return "No se pudo generar una recomendación.", 0
    partes, total_power = [], 0
    for kw, count in sorted(recomendacion.items(), reverse=True):
        s = "s" if count > 1 else ""; partes.append(f"{count} inversor{s} de {kw} kW"); total_power += kw * count
    final_string = " y ".join(partes) + f" (Potencia AC total: {total_power} kW)."
    return final_string, total_power

# Función de análisis de sensibilidad
def imprimir_generacion_por_orientacion(potencia_ac_inversor, base_hsp, n):
    resultados = {"Sur (Ideal)": 1.00, "Este / Oeste": 0.88, "Norte": 0.65}
    data = []
    for orientacion, factor in resultados.items():
        effective_hsp = base_hsp * factor
        annual_generation = potencia_ac_inversor * effective_hsp * n * 365
        monthly_avg_generation = annual_generation / 12
        data.append({"Orientación": orientacion, "Generación Promedio Mensual (kWh)": f"{monthly_avg_generation:,.1f}"})
    return data

# Función principal de cálculo
def cotizacion(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module, ciudad=None,
               perc_financiamiento=0, tasa_interes_credito=0, plazo_credito_años=0,
               tasa_degradacion=0, precio_excedentes=0):
    HSP = 4.5
    if ciudad and ciudad.upper() in HSP_POR_CIUDAD: HSP = HSP_POR_CIUDAD[ciudad.upper()]
    n = 0.85
    life = 25
    if clima.strip().upper() == "NUBE": n -= 0.05
    recomendacion_inversor_str, potencia_ac_inversor = recomendar_inversor(size)
    potencia_efectiva_calculo = min(size, potencia_ac_inversor)               
    costo_por_kwp = 7587.7 * size**2 - 346085 * size + 7e6
    valor_proyecto_total = costo_por_kwp * size
    if cubierta.strip().upper() == "TEJA": valor_proyecto_total *= 1.03
    valor_proyecto_total = round(valor_proyecto_total, 2)
    monto_a_financiar = valor_proyecto_total * (perc_financiamiento / 100)
    cuota_mensual_credito = 0
    if monto_a_financiar > 0 and plazo_credito_años > 0 and tasa_interes_credito > 0:
        tasa_mensual_credito = tasa_interes_credito / 12
        num_pagos_credito = plazo_credito_años * 12
        cuota_mensual_credito = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_a_financiar))
    desembolso_inicial_cliente = valor_proyecto_total - monto_a_financiar
    cashflow_free, total_lifetime_generation, total_maintenance_cost_present_value = [], 0, 0
    ahorro_anual_año1 = 0
    annual_generation_init = potencia_efectiva_calculo * HSP * n * 365
    performance = [0.083, 0.080, 0.081, 0.084, 0.083, 0.080, 0.093, 0.091, 0.084, 0.084, 0.079, 0.079]
    for i in range(life):
        current_annual_generation = annual_generation_init * ((1 - tasa_degradacion) ** i)
        total_lifetime_generation += current_annual_generation
        ahorro_anual_total = 0
        for p in performance:
            gen_mes = current_annual_generation * p
            consumo_mes = Load
            if gen_mes >= consumo_mes:
                ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * precio_excedentes)
            else:
                ahorro_mes = gen_mes * costkWh
            ahorro_anual_total += ahorro_mes
        ahorro_anual_indexado = ahorro_anual_total * ((1 + index) ** i)
        if i == 0:
            ahorro_anual_año1 = ahorro_anual_total
        mantenimiento_anual = 0.05 * ahorro_anual_indexado
        total_maintenance_cost_present_value += mantenimiento_anual / ((1 + dRate)**(i+1))
        cuotas_anuales_credito = 0
        if i < plazo_credito_años: cuotas_anuales_credito = cuota_mensual_credito * 12
        flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
        cashflow_free.append(flujo_anual)
    cashflow_free.insert(0, -desembolso_inicial_cliente)
    present_value = npf.npv(dRate, cashflow_free)
    internal_rate = npf.irr(cashflow_free)
    total_cost_present_value = desembolso_inicial_cliente + total_maintenance_cost_present_value
    lcoe = total_cost_present_value / total_lifetime_generation if total_lifetime_generation > 0 else 0
    FE, Eq_trees = 0.154, 22
    trees = round(Load * 12 * FE * Eq_trees / 1000, 0)
    monthly_generation_init = [annual_generation_init * p for p in performance]
    return valor_proyecto_total, size, monto_a_financiar, cuota_mensual_credito, \
           desembolso_inicial_cliente, cashflow_free, trees, monthly_generation_init, \
           present_value, internal_rate, quantity, life, recomendacion_inversor_str, \
           lcoe, n, HSP, potencia_ac_inversor, ahorro_anual_año1

# Clase para el PDF
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte de Cotizacion Solar', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

# Función para generar PDF
def generar_reporte_pdf(datos_reporte):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Resumen de la Propuesta Financiera y Tecnica', 0, 1, 'L')
    for key, value in datos_reporte.items():
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 8, f'{key}:', border=1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(95, 8, str(value), border=1)
        pdf.ln()
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Analisis de Generacion y Consumo (Ano 1)', 0, 1, 'L')
    pdf.image('grafica_generacion.png', x=10, w=pdf.w - 20)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Analisis de Flujo de Caja y Retorno de Inversion', 0, 1, 'L')
    pdf.image('grafica_flujo_caja.png', x=10, w=pdf.w - 20)
    nombre_archivo = "Reporte_Solar.pdf"
    return bytes(pdf.output(dest='S'))


# ==============================================================================
# 2. INTERFAZ DE STREAMLIT
# ==============================================================================

def main():
    st.set_page_config(page_title="Calculadora Solar", layout="wide", initial_sidebar_state="expanded")
    st.title("☀️ Calculadora y Cotizador Solar Profesional")

    with st.sidebar:
        st.header("Parámetros de Entrada")
        opcion = st.radio("Método para dimensionar el sistema:",
                          ["Por Consumo Mensual (kWh)", "Por Cantidad de Paneles"],
                          horizontal=True)

        if opcion == "Por Consumo Mensual (kWh)":
            Load = st.number_input("Consumo mensual promedio (kWh)", min_value=50, value=500, step=50)
            module = st.number_input("Potencia del panel solar (W)", min_value=300, value=550, step=10)
            
            HSP_aprox = 4.5 
            n_aprox = 0.85
            Ratio = 1.2
            size = round(Load * Ratio / (HSP_aprox * 30 * n_aprox), 2)
            quantity = round(size * 1000 / module)
            size = round(quantity * module / 1000, 2)
            st.info(f"Sistema estimado: **{size:.2f} kWp** ({int(quantity)} paneles)")
        else: # Por Cantidad de Paneles
            module = st.number_input("Potencia del panel solar (W)", min_value=300, value=550, step=10)
            quantity = st.number_input("Cantidad de paneles a instalar", min_value=1, value=10, step=1)
            Load = st.number_input("Consumo mensual (para análisis financiero)", min_value=50, value=500, step=50)
            size = round((quantity * module) / 1000, 2)
            st.info(f"Sistema dimensionado: **{size:.2f} kWp**")

        st.subheader("Datos Generales")
        ciudad_input = st.selectbox("Ciudad", list(HSP_POR_CIUDAD.keys()))
        cubierta = st.selectbox("Tipo de cubierta", ["LÁMINA", "TEJA"])
        clima = st.selectbox("Clima predominante", ["SOL", "NUBE"])

        st.subheader("Parámetros Financieros")
        costkWh = st.number_input("Costo actual por kWh (COP)", min_value=200, value=850, step=10)
        index_input = st.slider("Tasa de indexación de la energía (%)", 0.0, 20.0, 5.0, 0.5)
        dRate_input = st.slider("Tasa de descuento (%)", 0.0, 25.0, 10.0, 0.5)
        
        st.subheader("Financiamiento")
        usa_financiamiento = st.toggle("Incluir financiamiento")
        if usa_financiamiento:
            perc_financiamiento = st.slider("Porcentaje a financiar (%)", 0, 100, 70)
            tasa_interes_input = st.slider("Tasa de interés anual del crédito (%)", 0.0, 30.0, 15.0, 0.5)
            plazo_credito_años = st.number_input("Plazo del crédito en años", 1, 20, 5)
        else:
            perc_financiamiento, tasa_interes_input, plazo_credito_años = 0, 0, 0

    if st.button("📊 Calcular y Generar Reporte", use_container_width=True):
        with st.spinner('Realizando cálculos... ⏳'):
            index = index_input / 100
            dRate = dRate_input / 100
            tasa_interes_credito = tasa_interes_input / 100

            valor_proyecto_total, size_calc, monto_a_financiar, cuota_mensual_credito, \
            desembolso_inicial_cliente, fcl, trees, monthly_generation, valor_presente, \
            tasa_interna, cantidad_calc, life, recomendacion_inversor, lcoe, n_final, HSP_final, \
            potencia_ac_inversor, ahorro_año1 = \
                cotizacion(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module, ciudad=ciudad_input,
                           perc_financiamiento=perc_financiamiento, tasa_interes_credito=tasa_interes_credito,
                           plazo_credito_años=plazo_credito_años, tasa_degradacion=0.001,
                           precio_excedentes=300.0)
            
            generacion_promedio_mensual = sum(monthly_generation) / len(monthly_generation)
            payback_simple = next((i for i, x in enumerate(np.cumsum(fcl)) if x >= 0), None)
            payback_exacto = None
            if payback_simple is not None:
                if payback_simple > 0 and (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1]) != 0:
                    payback_exacto = (payback_simple - 1) + abs(np.cumsum(fcl)[payback_simple-1]) / (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1])
                else:
                    payback_exacto = float(payback_simple)

            st.header("Resultados de la Propuesta")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Valor del Proyecto", f"${valor_proyecto_total:,.0f}")
            col2.metric("TIR", f"{tasa_interna:.2%}")
            col3.metric("Payback (años)", f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A")
            col4.metric("Ahorro Año 1", f"${ahorro_año1:,.0f}")

            with st.expander("Ver detalles del resumen técnico y financiero"):
                 # ... (puedes agregar más detalles aquí)
                 st.write("Detalles completos en el reporte PDF.")

            st.header("Análisis Gráfico")
            fig1, ax1 = plt.subplots(figsize=(10, 5))
            meses_grafico = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
            generacion_autoconsumida, excedentes_vendidos, importado_de_la_red = [], [], []
            for gen_mes in monthly_generation:
                if gen_mes >= Load:
                    generacion_autoconsumida.append(Load); excedentes_vendidos.append(gen_mes - Load); importado_de_la_red.append(0)
                else:
                    generacion_autoconsumida.append(gen_mes); excedentes_vendidos.append(0); importado_de_la_red.append(Load - gen_mes)
            ax1.bar(meses_grafico, generacion_autoconsumida, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
            ax1.bar(meses_grafico, excedentes_vendidos, bottom=generacion_autoconsumida, color='red', edgecolor='black', label='Excedentes Vendidos', width=0.7)
            ax1.bar(meses_grafico, importado_de_la_red, bottom=generacion_autoconsumida, color='#2ECC71', edgecolor='black', label='Importado de la Red', width=0.7)
            ax1.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
            ax1.set_ylabel("Energía (kWh)", fontweight="bold")
            ax1.set_title("Generación Vs. Consumo Mensual (Año 1)", fontweight="bold")
            ax1.legend()
            st.pyplot(fig1)

            fig2, ax2 = plt.subplots(figsize=(10, 5))
            fcl_acumulado = np.cumsum(fcl)
            años = np.arange(0, life + 1)
            ax2.plot(años, fcl_acumulado, marker='o', linestyle='-', color='green', label='Flujo de Caja Acumulado')
            ax2.plot(0, fcl_acumulado[0], marker='X', markersize=10, color='red', label='Desembolso Inicial (Año 0)')
            if payback_exacto is not None:
                ax2.axvline(x=payback_exacto, color='red', linestyle='--', label=f'Payback Simple: {payback_exacto:.2f} años')
            ax2.axhline(0, color='grey', linestyle='--', linewidth=0.8)
            ax2.set_ylabel("Flujo de Caja Acumulado (COP)", fontweight="bold")
            ax2.set_xlabel("Año", fontweight="bold")
            ax2.set_title("Flujo de Caja Acumulado y Período de Retorno", fontweight="bold")
            ax2.legend()
            st.pyplot(fig2)
            
            # Generar PDF para la descarga
            fig1.savefig('grafica_generacion.png', bbox_inches='tight')
            fig2.savefig('grafica_flujo_caja.png', bbox_inches='tight')
            
            datos_para_pdf = {
                "Valor Total del Proyecto (COP)": f"{valor_proyecto_total:,.2f}",
                "Tamano del Sistema (kWp)": f"{size}",
                "Cantidad de Paneles": f"{int(quantity)} de {int(module)}W",
                "Inversor Recomendado": f"{recomendacion_inversor}",
                "Generacion Promedio Mensual (kWh)": f"{generacion_promedio_mensual:,.1f}",
                "Ahorro Estimado Primer Ano (COP)": f"{ahorro_año1:,.2f}",
                "TIR (Tasa Interna de Retorno)": f"{tasa_interna:.2%}",
                "VPN (Valor Presente Neto) (COP)": f"{valor_presente:,.2f}",
                "Periodo de Retorno (anos)": f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A"
            }
            if usa_financiamiento:
                datos_para_pdf["--- Detalles de Financiamiento ---"] = ""
                datos_para_pdf["Monto a Financiar (COP)"] = f"{monto_a_financiar:,.2f}"
                datos_para_pdf["Cuota Mensual del Credito (COP)"] = f"{cuota_mensual_credito:,.2f}"
                datos_para_pdf["Desembolso Inicial (COP)"] = f"{desembolso_inicial_cliente:,.2f}"
            
            pdf_bytes = generar_reporte_pdf(datos_para_pdf)
            st.download_button(
                label="📥 Descargar Reporte Completo en PDF",
                data=pdf_bytes,
                file_name="Reporte_Solar.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.success('¡Análisis completado!')

if __name__ == '__main__':
    main()
