import sys
import os
import datetime
import math

# Add the project root to the path so we can import src
sys.path.append(os.getcwd())

from src.utils.pdf_generator import PropuestaPDF
from src.services.calculator_service import cotizacion, redondear_a_par
from src.config import HSP_MENSUAL_POR_CIUDAD, HSP_POR_CIUDAD, PROMEDIOS_COSTO
from src.utils.plotting import generar_grafica_generacion

def generate_sample_pdf():
    # --------------------------------------------------------------------------------
    # Scenario: "realistic cotizacion" (Medellín-style) with financing enabled
    # --------------------------------------------------------------------------------
    ciudad = "MEDELLIN"
    nombre_cliente = "Cliente Prueba"
    documento = "123456789"
    direccion = "Medellín, Antioquia"
    fecha = datetime.date.today()

    # Inputs aligned with app defaults
    Load = 700  # kWh/mes
    module_w = 615  # W
    cubierta = "LÁMINA"
    clima = "SOL"

    costkWh = 850  # COP/kWh
    index = 0.05
    dRate = 0.10
    horizonte_tiempo = 25

    # Financing (enabled)
    usa_financiamiento = True
    perc_financiamiento = 70
    tasa_interes_credito = 0.15  # anual (decimal)
    plazo_credito_años = 5

    # Carbon analysis for a richer PDF (safe fallback to 0s if unavailable)
    incluir_carbon = True

    # Location (used in PDF location page)
    lat = 6.2442
    lon = -75.5812

    # HSP list for the city
    hsp_mensual = HSP_MENSUAL_POR_CIUDAD[ciudad]
    hsp_promedio = HSP_POR_CIUDAD.get(ciudad, sum(hsp_mensual) / len(hsp_mensual))

    # Sizing similar to desktop "Por Consumo Mensual"
    factor_seguridad = 1.10  # 10% default in UI
    n_aprox = 0.85
    size_teorico = (Load * factor_seguridad) / (hsp_promedio * 30 * n_aprox)
    quantity_calc = math.ceil(size_teorico * 1000 / module_w)
    quantity = int(redondear_a_par(quantity_calc))
    size_kwp = round(quantity * module_w / 1000, 2)

    # Run the same engine used by the app
    (
        valor_proyecto_total,
        size_calc,
        monto_a_financiar,
        cuota_mensual_credito,
        desembolso_inicial_cliente,
        fcl,
        _trees_legacy,
        monthly_generation,
        valor_presente,
        tasa_interna,
        cantidad_calc,
        life,
        recomendacion_inversor,
        lcoe,
        n_final,
        _hsp_mensual_final,
        potencia_ac_inversor,
        ahorro_año1,
        area_requerida,
        _capacidad_nominal_bateria,
        carbon_data,
    ) = cotizacion(
        Load=Load,
        size=size_kwp,
        quantity=quantity,
        cubierta=cubierta,
        clima=clima,
        index=index,
        dRate=dRate,
        costkWh=costkWh,
        module=module_w,
        ciudad=ciudad,
        hsp_lista=hsp_mensual,
        perc_financiamiento=perc_financiamiento if usa_financiamiento else 0,
        tasa_interes_credito=tasa_interes_credito if usa_financiamiento else 0,
        plazo_credito_años=plazo_credito_años if usa_financiamiento else 0,
        tasa_degradacion=0.001,
        precio_excedentes=300.0,
        incluir_baterias=False,
        horizonte_tiempo=horizonte_tiempo,
        incluir_carbon=incluir_carbon,
        incluir_beneficios_tributarios=False,
        incluir_deduccion_renta=False,
        incluir_depreciacion_acelerada=False,
        demora_6_meses=False,
    )

    # Generation chart used by the proposal PDF
    generar_grafica_generacion(monthly_generation, Load, incluir_baterias=False)

    # Payback (years) consistent with UI
    payback_simple = next((i for i, x in enumerate(__import__("numpy").cumsum(fcl)) if x >= 0), None)
    payback_exacto = None
    if payback_simple is not None:
        cumsum_fcl = __import__("numpy").cumsum(fcl)
        if payback_simple > 0 and (cumsum_fcl[payback_simple] - cumsum_fcl[payback_simple - 1]) != 0:
            payback_exacto = (payback_simple - 1) + abs(cumsum_fcl[payback_simple - 1]) / (
                cumsum_fcl[payback_simple] - cumsum_fcl[payback_simple - 1]
            )
        else:
            payback_exacto = float(payback_simple)

    # Price breakdown for PDF (mirror desktop logic)
    valor_pdf_redondeado = math.ceil(valor_proyecto_total / 100) * 100
    presupuesto_materiales_pdf = valor_pdf_redondeado * (PROMEDIOS_COSTO["Materiales"] / 100)
    ganancia_estimada_pdf = valor_pdf_redondeado * (PROMEDIOS_COSTO["Margen (Ganancia)"] / 100)
    valor_iva_pdf = math.ceil(((presupuesto_materiales_pdf + ganancia_estimada_pdf) * 0.19) / 100) * 100
    valor_sistema_sin_iva_pdf = valor_pdf_redondeado - valor_iva_pdf

    generacion_promedio_mensual = sum(monthly_generation) / len(monthly_generation) if monthly_generation else 0

    # Carbon fields
    arboles_equivalentes = 0
    co2_evitado_tons = 0.0
    if incluir_carbon and isinstance(carbon_data, dict):
        arboles_equivalentes = carbon_data.get("trees_saved_per_year", 0) or 0
        co2_evitado_tons = carbon_data.get("annual_co2_avoided_tons", 0.0) or 0.0

    # O&M used by PDF page
    om_anual = valor_pdf_redondeado * 0.02

    datos_para_pdf = {
        "Nombre del Proyecto": f"FV{str(fecha.year)[-2:]}001 - {nombre_cliente} - {ciudad}",
        "Cliente": nombre_cliente,
        "Valor Total del Proyecto (COP)": f"${valor_pdf_redondeado:,.0f}",
        "Valor Sistema FV (sin IVA)": f"${valor_sistema_sin_iva_pdf:,.0f}",
        "Valor IVA": f"${valor_iva_pdf:,.0f}",
        "Tamano del Sistema (kWp)": f"{size_kwp:.1f}",
        "Cantidad de Paneles": f"{int(quantity)} de {int(module_w)}W",
        "Área Requerida Aprox. (m²)": f"{area_requerida}",
        "Inversor Recomendado": f"{recomendacion_inversor}",
        "Generacion Promedio Mensual (kWh)": f"{generacion_promedio_mensual:,.1f}",
        "Ahorro Estimado Primer Ano (COP)": f"{ahorro_año1:,.2f}",
        "TIR (Tasa Interna de Retorno)": f"{tasa_interna:.1%}",
        "VPN (Valor Presente Neto) (COP)": f"{valor_presente:,.2f}",
        "Periodo de Retorno (anos)": f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A",
        "Tipo de Cubierta": cubierta,
        "Potencia de Paneles": f"{int(module_w)}",
        "Potencia AC Inversor": f"{potencia_ac_inversor}",
        "Árboles Equivalentes Ahorrados": str(int(round(arboles_equivalentes))),
        "CO2 Evitado Anual (Toneladas)": f"{co2_evitado_tons:.2f}",
        "O&M (Operation & Maintenance)": f"${om_anual:,.0f}",
    }

    if usa_financiamiento:
        datos_para_pdf["--- Detalles de Financiamiento ---"] = ""
        datos_para_pdf["Monto a Financiar (COP)"] = f"{math.ceil(monto_a_financiar):,.0f}"
        datos_para_pdf["Cuota Mensual del Credito (COP)"] = f"{math.ceil(cuota_mensual_credito):,.0f}"
        datos_para_pdf["Desembolso Inicial (COP)"] = f"{math.ceil(desembolso_inicial_cliente):,.0f}"
        datos_para_pdf["Plazo del Crédito"] = str(plazo_credito_años * 12)

    pdf = PropuestaPDF(
        client_name=nombre_cliente,
        project_name=datos_para_pdf["Nombre del Proyecto"],
        documento=documento,
        direccion=direccion,
        fecha=fecha,
    )

    try:
        pdf_bytes = pdf.generar(datos_para_pdf, usa_financiamiento=usa_financiamiento, lat=lat, lon=lon)
        
        output_filename = "sample_propuesta_real.pdf"
        with open(output_filename, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"Successfully generated {output_filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_sample_pdf()
