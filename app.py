import streamlit as st
import numpy_financial as npf
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import json
import os
import re
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import math
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import googlemaps
from geopy.geocoders import Nominatim
import time
from docx import Document
from num2words import num2words
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
try:
    from notion_client import Client as NotionClient
except Exception:
    NotionClient = None

# Import carbon calculator module
try:
    from carbon_calculator import CarbonEmissionsCalculator, format_carbon_number, format_currency_cop
    carbon_calculator = CarbonEmissionsCalculator()
except ImportError:
    st.warning("⚠️ Módulo de cálculo de carbono no encontrado. Las funcionalidades de sostenibilidad estarán limitadas.")
    carbon_calculator = None

# ==============================================================================
# CONSTANTES Y DATOS GLOBALES
# ==============================================================================
# Reemplaza el diccionario PROMEDIOS_COSTO en tu app.py con este
HSP_MENSUAL_POR_CIUDAD = {
    # Datos de HSP promedio mensual (kWh/m²/día)
    # Fuente: PVGIS y promedios históricos de radiación solar.
    "MEDELLIN":    [4.38, 4.49, 4.51, 4.31, 4.20, 4.35, 4.80, 4.71, 4.40, 4.15, 4.05, 4.19],
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
    'IVA (Impuestos)': 11.50,
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

# ==============================================================================
# FUNCIONES DE VALIDACIÓN Y UTILIDADES
# ==============================================================================

def validar_datos_entrada(Load, size, quantity, cubierta, clima, costkWh, module):
    """Valida que los datos de entrada sean coherentes y válidos"""
    errores = []
    
    if Load <= 0:
        errores.append("El consumo mensual debe ser mayor a 0")
    
    if size <= 0:
        errores.append("El tamaño del sistema debe ser mayor a 0")
    
    if quantity <= 0:
        errores.append("La cantidad de paneles debe ser mayor a 0")
    
    if module <= 0:
        errores.append("La potencia del panel debe ser mayor a 0")
    
    if costkWh <= 0:
        errores.append("El costo por kWh debe ser mayor a 0")
    
    if cubierta not in ["LÁMINA", "TEJA"]:
        errores.append("El tipo de cubierta debe ser LÁMINA o TEJA")
    
    if clima not in ["SOL", "NUBE"]:
        errores.append("El clima debe ser SOL o NUBE")
    
    return errores

def formatear_moneda(valor):
    """Formatea un valor numérico como moneda colombiana"""
    try:
        return f"${valor:,.0f}"
    except (ValueError, TypeError):
        return "$0"

# ==============================================================================
# INTEGRACIÓN CON NOTION (CRM)
# ==============================================================================

def _build_notion_properties(nombre: str, estado: str, documento: str, direccion: str, proyecto: str, fecha):
    """Crea el diccionario de propiedades para la página de Notion según nombres configurables."""
    # Nombres de propiedades configurables por env
    prop_name = os.environ.get("NOTION_PROP_NAME", "Name")
    prop_status = os.environ.get("NOTION_PROP_STATUS", "Estado")
    prop_doc = os.environ.get("NOTION_PROP_DOCUMENTO", "Documento")
    prop_dir = os.environ.get("NOTION_PROP_DIRECCION", "Direccion")
    prop_project = os.environ.get("NOTION_PROP_PROYECTO", "Proyecto")
    prop_date = os.environ.get("NOTION_PROP_FECHA", "Fecha")

    # Fecha a ISO
    fecha_iso = None
    try:
        if hasattr(fecha, 'isoformat'):
            fecha_iso = fecha.isoformat()
        elif isinstance(fecha, str):
            fecha_iso = fecha
    except Exception:
        fecha_iso = None

    properties = {
        prop_name: {"title": [{"text": {"content": nombre or ""}}]},
        prop_doc: {"rich_text": [{"text": {"content": documento or ""}}]},
        prop_dir: {"rich_text": [{"text": {"content": direccion or ""}}]},
        prop_project: {"rich_text": [{"text": {"content": proyecto or ""}}]},
    }
    if fecha_iso:
        properties[prop_date] = {"date": {"start": fecha_iso}}

    # Intento 1: status
    properties_status = properties.copy()
    properties_status[prop_status] = {"status": {"name": estado}}

    # Intento 2: select
    properties_select = properties.copy()
    properties_select[prop_status] = {"select": {"name": estado}}

    return properties_status, properties_select


def agregar_cliente_a_notion_crm(nombre: str, documento: str, direccion: str, proyecto: str, fecha, estado: str = "En conversaciones"):
    """Agrega un registro en la base de datos de Notion CRM si las credenciales están disponibles.
    Usa el nombre de estado 'En conversaciones' por defecto.
    """
    token = os.environ.get("NOTION_API_TOKEN")
    database_id = os.environ.get("NOTION_CRM_DATABASE_ID")
    if not token or not database_id or NotionClient is None:
        # Integración deshabilitada
        return False, "Integración Notion no configurada"

    try:
        notion = NotionClient(auth=token)
        props_status, props_select = _build_notion_properties(nombre, estado, documento, direccion, proyecto, fecha)

        # Intentar crear con "status" primero
        try:
            notion.pages.create(parent={"database_id": database_id}, properties=props_status)
            return True, "Cliente agregado a Notion (status)"
        except Exception:
            # Reintentar con select
            notion.pages.create(parent={"database_id": database_id}, properties=props_select)
            return True, "Cliente agregado a Notion (select)"

    except Exception as e:
        return False, f"Error Notion: {e}"

# ==============================================================================
# COTIZADOR DE CARGADORES ELÉCTRICOS (SIN FINANCIAMIENTO)
# ==============================================================================

def cotizacion_cargadores_costos(distancia_metros: float):
    """Calcula desglose de costos para instalación de un punto de carga.
    Retorna (IVA, diseño, materiales, costo_total, costo_base).
    """
    try:
        costo_base = (35184 * float(distancia_metros) + 857195) * 1.1
        iva = 0.19 * costo_base
        diseno = 0.35 * costo_base
        materiales = 0.65 * costo_base
        costo_total = costo_base + iva
        return iva, diseno, materiales, costo_total, costo_base
    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 0.0


def calcular_materiales_cargador(distancia_metros: float):
    """Calcula lista de materiales aproximada en función de la distancia."""
    d = float(distancia_metros)
    lista = [
        ("TUBERIA EMT 3/4 Pulg", int(round(d / 3.0, 0) + 1), "UNIDADES"),
        ("UNION EMT 3/4 Pulg", int(round(d / 3.0, 0) + round(d / 6.0, 0)), "UNIDADES"),
        ("CURVA EMT 3/4 Pulg", int(round(d / 6.0, 0)), "UNIDADES"),
        ("ENTRADA CAJA EMT 3/4 Pulg", 2, "UNIDADES"),
        ("CABLE 8 AWG NEGRO", int(round(d + 3.0, 0) * 2), "METROS"),
        ("CABLE 8 AWG VERDE", int(round(d + 3.0, 0)), "METROS"),
        ("CAJA DEXSON 18X14", 1, "UNIDAD"),
    ]
    return lista


def generar_pdf_cargadores(nombre_cliente_lugar: str, distancia_metros: float):
    """Genera el PDF de cotización de cargadores usando la plantilla en assets y retorna (bytes_pdf, desglose_dict)."""
    from io import BytesIO

    plantilla_path = os.path.join("assets", "Plantilla_MIRAC_CARGADORES.pdf")
    fecha_actual = datetime.datetime.now().strftime("%d-%m-%Y")

    iva, diseno, materiales, costo_total, costo_base = cotizacion_cargadores_costos(distancia_metros)

    # PDFs temporales en memoria
    temp1 = BytesIO()
    temp2 = BytesIO()

    # Página 1 temporal (costo total y fecha y nombre)
    c1 = canvas.Canvas(temp1, pagesize=letter)
    c1.setFont("Helvetica-Bold", 26)
    c1.drawString(100, 82, f"{costo_total:,.0f}")
    c1.setFont("Helvetica-Bold", 13)
    c1.drawString(462, 757, fecha_actual)
    c1.setFont("Helvetica-Bold", 14)
    c1.drawString(195, 624, nombre_cliente_lugar)
    c1.save()
    temp1.seek(0)

    # Página 2 temporal (tabla de costos)
    c2 = canvas.Canvas(temp2, pagesize=letter)
    c2.setFont("Helvetica-Bold", 14)
    offset_y = 56
    c2.drawString(462, 757, fecha_actual)
    c2.drawString(465, 576 + offset_y, f"${diseno:,.0f}")
    c2.drawString(465, 551 + offset_y, f"${materiales:,.0f}")
    c2.drawString(465, 500 + offset_y, f"${costo_base:,.0f}")
    c2.drawString(465, 474 + offset_y, f"${iva:,.0f}")
    c2.drawString(465, 448 + offset_y, f"${costo_total:,.0f}")
    c2.save()
    temp2.seek(0)

    # Combinar con plantilla (3 páginas)
    output_buffer = BytesIO()
    reader = PdfReader(plantilla_path)
    writer = PdfWriter()

    if len(reader.pages) < 3:
        raise ValueError("La plantilla de cargadores debe tener 3 páginas")

    pagina1 = reader.pages[0]
    pagina1.merge_page(PdfReader(temp1).pages[0])
    writer.add_page(pagina1)

    pagina2 = reader.pages[1]
    pagina2.merge_page(PdfReader(temp2).pages[0])
    writer.add_page(pagina2)

    writer.add_page(reader.pages[2])
    writer.write(output_buffer)
    output_buffer.seek(0)

    desglose = {
        "Costo Base": costo_base,
        "IVA": iva,
        "Diseño": diseno,
        "Materiales": materiales,
        "Costo Total": costo_total,
    }
    return output_buffer.getvalue(), desglose

# ==============================================================================
# FUNCIONES DE CÁLCULO
# ==============================================================================

def calcular_analisis_sensibilidad(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module, 
                                  ciudad=None, hsp_lista=None, incluir_baterias=False, costo_kwh_bateria=0, 
                                  profundidad_descarga=0.9, eficiencia_bateria=0.95, dias_autonomia=2,
                                  perc_financiamiento=0, tasa_interes_credito=0, plazo_credito_años=0,
                                  precio_manual=None, horizonte_base=25):
    """
    Calcula análisis de sensibilidad con TIR a 10 y 20 años con y sin financiación
    """
    resultados = {}
    
    # Escenarios a analizar
    escenarios = [
        {"nombre": "10 años sin financiación", "horizonte": 10, "financiamiento": False},
        {"nombre": "10 años con financiación", "horizonte": 10, "financiamiento": True},
        {"nombre": "20 años sin financiación", "horizonte": 20, "financiamiento": False},
        {"nombre": "20 años con financiación", "horizonte": 20, "financiamiento": True}
    ]
    
    for escenario in escenarios:
        try:
            # Usar los mismos parámetros de financiamiento del sidebar, pero cambiar el plazo
            perc_fin_escenario = perc_financiamiento if escenario["financiamiento"] else 0
            tasa_interes_escenario = tasa_interes_credito if escenario["financiamiento"] else 0
            plazo_escenario = plazo_credito_años if escenario["financiamiento"] else 0
            
            # Calcular cotización para este escenario
            valor_proyecto_total, size_calc, monto_a_financiar, cuota_mensual_credito, \
            desembolso_inicial_cliente, fcl, trees, monthly_generation, valor_presente, \
            tasa_interna, cantidad_calc, life, recomendacion_inversor, lcoe, n_final, hsp_mensual_final, \
            potencia_ac_inversor, ahorro_año1, area_requerida, capacidad_nominal_bateria, carbon_data = \
                cotizacion(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
                          ciudad=ciudad, hsp_lista=hsp_lista,
                          perc_financiamiento=perc_fin_escenario,
                          tasa_interes_credito=tasa_interes_escenario,
                          plazo_credito_años=plazo_escenario,
                          tasa_degradacion=0.001, precio_excedentes=300.0,
                          incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                          profundidad_descarga=profundidad_descarga, eficiencia_bateria=eficiencia_bateria,
                          dias_autonomia=dias_autonomia, horizonte_tiempo=horizonte_base,
                          incluir_carbon=False)  # Disable carbon for sensitivity analysis
            
            # SIEMPRE recalcular el flujo de caja para asegurar consistencia
            if precio_manual is not None:
                valor_proyecto_total = precio_manual
                # perc_fin_escenario proviene del sidebar (0..100). Convertir a decimal.
                monto_a_financiar = valor_proyecto_total * (perc_fin_escenario / 100)
                desembolso_inicial_cliente = valor_proyecto_total - monto_a_financiar
                
                if perc_fin_escenario > 0:
                    cuota_mensual_credito = npf.pmt(tasa_interes_escenario / 12, plazo_escenario * 12, -monto_a_financiar)
                else:
                    cuota_mensual_credito = 0
            
            # Para escenarios sin financiación, recalcular con el mismo flujo de caja base
            if not escenario["financiamiento"]:
                # Recalcular el flujo de caja usando la misma lógica que la función principal
                fcl = []
                for i in range(escenario["horizonte"]):
                    # Calcular ahorro anual para cada año (misma lógica que la función principal)
                    ahorro_anual_total = 0
                    if incluir_baterias:
                        ahorro_anual_total = (Load * 12) * costkWh
                    else:  # Lógica On-Grid
                        for gen_mes in monthly_generation:
                            consumo_mes = Load
                            if gen_mes >= consumo_mes:
                                ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * 300.0)  # precio_excedentes = 300
                            else:
                                ahorro_mes = gen_mes * costkWh
                            ahorro_anual_total += ahorro_mes
                    
                    # Aplicar indexación anual
                    ahorro_anual_indexado = ahorro_anual_total * ((1 + index) ** i)
                    
                    # Mantenimiento anual
                    mantenimiento_anual = 0.05 * ahorro_anual_indexado
                    
                    # Sin cuotas de crédito para escenarios sin financiación
                    cuotas_anuales_credito = 0
                    
                    # Flujo anual
                    flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
                    fcl.append(flujo_anual)
                
                # Insertar desembolso inicial al inicio
                fcl.insert(0, -desembolso_inicial_cliente)
            else:
                # Para escenarios con financiación, recalcular el flujo de caja
                fcl = []
                for i in range(escenario["horizonte"]):
                    # Calcular ahorro anual para cada año (misma lógica que la función principal)
                    ahorro_anual_total = 0
                    if incluir_baterias:
                        ahorro_anual_total = (Load * 12) * costkWh
                    else:  # Lógica On-Grid
                        for gen_mes in monthly_generation:
                            consumo_mes = Load
                            if gen_mes >= consumo_mes:
                                ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * 300.0)  # precio_excedentes = 300
                            else:
                                ahorro_mes = gen_mes * costkWh
                            ahorro_anual_total += ahorro_mes
                    
                    # Aplicar indexación anual
                    ahorro_anual_indexado = ahorro_anual_total * ((1 + index) ** i)
                    
                    # Mantenimiento anual
                    mantenimiento_anual = 0.05 * ahorro_anual_indexado
                    
                    # Cuotas anuales del crédito
                    cuotas_anuales_credito = 0
                    if i < plazo_escenario: 
                        cuotas_anuales_credito = cuota_mensual_credito * 12
                    
                    # Flujo anual
                    flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
                    fcl.append(flujo_anual)
                
                # Insertar desembolso inicial al inicio
                fcl.insert(0, -desembolso_inicial_cliente)
            
            # Recalcular métricas financieras
            valor_presente = npf.npv(dRate, fcl)
            tasa_interna = npf.irr(fcl)
            
            # Calcular payback
            payback_simple = next((i for i, x in enumerate(np.cumsum(fcl)) if x >= 0), None)
            payback_exacto = None
            if payback_simple is not None:
                if payback_simple > 0 and (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1]) != 0:
                    payback_exacto = (payback_simple - 1) + abs(np.cumsum(fcl)[payback_simple-1]) / (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1])
                else:
                    payback_exacto = float(payback_simple)
            
            # DEBUG: Mostrar información detallada
            print(f"\n=== DEBUG ESCENARIO: {escenario['nombre']} ===")
            print(f"Financiamiento: {escenario['financiamiento']}")
            print(f"Horizonte: {escenario['horizonte']}")
            print(f"Desembolso inicial: {desembolso_inicial_cliente:,.0f}")
            print(f"Primeros 10 flujos: {[f'{x:,.0f}' for x in fcl[:10]]}")
            print(f"Payback calculado: {payback_exacto}")
            print(f"Suma acumulada primeros 6 años: {[f'{x:,.0f}' for x in np.cumsum(fcl)[:6]]}")
            print("=" * 50)
            
            
            resultados[escenario["nombre"]] = {
                "tir": tasa_interna,
                "vpn": valor_presente,
                "payback": payback_exacto,
                "valor_proyecto": valor_proyecto_total,
                "desembolso_inicial": desembolso_inicial_cliente,
                "cuota_mensual": cuota_mensual_credito if escenario["financiamiento"] else 0
            }
            
        except Exception as e:
            st.warning(f"Error calculando {escenario['nombre']}: {e}")
            resultados[escenario["nombre"]] = {
                "tir": 0, "vpn": 0, "payback": None, "valor_proyecto": 0, 
                "desembolso_inicial": 0, "cuota_mensual": 0
            }
    
    return resultados

def recomendar_inversor(size_kwp):
    # (El código de esta función no cambia)
    inverters_disponibles = [3, 5, 6, 8, 10]
    min_ac_power = size_kwp / 1.2
    if size_kwp <= 12:
        for inv_kw in sorted(inverters_disponibles):
            if inv_kw >= min_ac_power: 
                return f"1 inversor de {inv_kw} kW", inv_kw
    recomendacion, potencia_restante = {}, min_ac_power
    for inv_kw in sorted(inverters_disponibles, reverse=True):
        if potencia_restante >= inv_kw:
            num = int(potencia_restante // inv_kw)
            recomendacion[inv_kw] = num
            potencia_restante -= num * inv_kw
    if potencia_restante > 0.1:
        inverter_para_resto = min(inverters_disponibles)
        for inv_kw in sorted(inverters_disponibles):
            if inv_kw >= potencia_restante: 
                inverter_para_resto = inv_kw
                break
        recomendacion[inverter_para_resto] = recomendacion.get(inverter_para_resto, 0) + 1
    if not recomendacion: 
        return "No se pudo generar una recomendación.", 0
    partes, total_power = [], 0
    for kw, count in sorted(recomendacion.items(), reverse=True):
        s = "s" if count > 1 else ""
        partes.append(f"{count} inversor{s} de {kw} kW")
        total_power += kw * count
    final_string = " y ".join(partes) + f" (Potencia AC total: {total_power} kW)."
    return final_string, total_power

# Reemplaza tu función cotizacion completa con esta versión

# Reemplaza tu función cotizacion completa con esta versión final
def cotizacion(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module, ciudad=None,
                hsp_lista=None,
                perc_financiamiento=0, tasa_interes_credito=0, plazo_credito_años=0,
                tasa_degradacion=0, precio_excedentes=0,
                incluir_baterias=False, costo_kwh_bateria=0,
                profundidad_descarga=0.9, eficiencia_bateria=0.95, dias_autonomia=2,
                horizonte_tiempo=25, incluir_carbon=False):
    
    # Se asegura de tener la lista de HSP mensuales para el cálculo
    hsp_mensual = hsp_lista if hsp_lista is not None else HSP_MENSUAL_POR_CIUDAD.get(ciudad.upper(), HSP_MENSUAL_POR_CIUDAD["MEDELLIN"])
    
    n = 0.8
    life = horizonte_tiempo
    if clima.strip().upper() == "NUBE": n -= 0.05
    
    recomendacion_inversor_str, potencia_ac_inversor = recomendar_inversor(size)
    potencia_efectiva_calculo = min(size, potencia_ac_inversor)
    
    area_por_panel = 2.3 * 1.0
    factor_seguridad = 1.30
    area_requerida = math.ceil(quantity * area_por_panel * factor_seguridad)
    
    costo_por_kwp = 7587.7 * size**2 - 346085 * size + 7e6
    valor_proyecto_fv = costo_por_kwp * size
    if cubierta.strip().upper() == "TEJA": valor_proyecto_fv *= 1.03

    costo_bateria = 0
    capacidad_nominal_bateria = 0
    if incluir_baterias:
        consumo_diario = Load / 30
        capacidad_util_bateria = consumo_diario * dias_autonomia
        if profundidad_descarga > 0:
            capacidad_nominal_bateria = capacidad_util_bateria / profundidad_descarga
        costo_bateria = capacidad_nominal_bateria * costo_kwh_bateria
    
    valor_proyecto_total = valor_proyecto_fv + costo_bateria
    valor_proyecto_total = math.ceil(valor_proyecto_total)
    
    monto_a_financiar = valor_proyecto_total * (perc_financiamiento / 100)
    monto_a_financiar = math.ceil(monto_a_financiar)
    
    cuota_mensual_credito = 0
    if monto_a_financiar > 0 and plazo_credito_años > 0 and tasa_interes_credito > 0:
        tasa_mensual_credito = tasa_interes_credito / 12
        num_pagos_credito = plazo_credito_años * 12
        cuota_mensual_credito = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_a_financiar))
        cuota_mensual_credito = math.ceil(cuota_mensual_credito)
        
    desembolso_inicial_cliente = valor_proyecto_total - monto_a_financiar
    
    cashflow_free, total_lifetime_generation, ahorro_anual_año1 = [], 0, 0
    dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Se calcula la generación de cada mes individualmente usando los HSP mensuales
    monthly_generation_init = [potencia_efectiva_calculo * hsp * dias * n for hsp, dias in zip(hsp_mensual, dias_por_mes)]
    
    for i in range(life):
        current_monthly_generation = [gen * ((1 - tasa_degradacion) ** i) for gen in monthly_generation_init]
        total_lifetime_generation += sum(current_monthly_generation)
        
        ahorro_anual_total = 0
        if incluir_baterias:
            ahorro_anual_total = (Load * 12) * costkWh
        else: # Lógica On-Grid
            for gen_mes in current_monthly_generation:
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
        cuotas_anuales_credito = 0
        if i < plazo_credito_años: 
            cuotas_anuales_credito = cuota_mensual_credito * 12
        flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
        cashflow_free.append(flujo_anual)

    cashflow_free.insert(0, -desembolso_inicial_cliente)
    present_value = npf.npv(dRate, cashflow_free)
    internal_rate = npf.irr(cashflow_free)
    lcoe = (desembolso_inicial_cliente + npf.npv(dRate, [0.05 * ahorro_anual_total * ((1 + index) ** i) for i in range(life)])) / total_lifetime_generation if total_lifetime_generation > 0 else 0
    trees = round(Load * 12 * 0.154 * 22 / 1000, 0)

    # Carbon emissions calculation (NEW)
    carbon_data = {}
    if incluir_carbon and carbon_calculator:
        try:
            # Calculate annual generation for carbon analysis
            annual_generation = sum(monthly_generation_init) if monthly_generation_init else 0

            # Get city for emission factor (handle variations)
            ciudad_normalizada = ciudad.upper() if ciudad else "BOGOTA"
            if ciudad_normalizada == "MEDELLÍN":
                ciudad_normalizada = "MEDELLIN"
            elif ciudad_normalizada == "CALÍ":
                ciudad_normalizada = "CALI"

            carbon_data = carbon_calculator.calculate_emissions_avoided(
                annual_generation_kwh=annual_generation,
                region=ciudad_normalizada,
                system_lifetime_years=life
            )
        except Exception as e:
            print(f"Error calculating carbon emissions: {e}")
            carbon_data = carbon_calculator._get_empty_carbon_data() if carbon_calculator else {}

    # Se devuelve la lista 'hsp_mensual' en lugar de un solo valor 'HSP'
    return valor_proyecto_total, size, monto_a_financiar, cuota_mensual_credito, \
           desembolso_inicial_cliente, cashflow_free, trees, monthly_generation_init, \
           present_value, internal_rate, quantity, life, recomendacion_inversor_str, \
           lcoe, n, hsp_mensual, potencia_ac_inversor, ahorro_anual_año1, area_requerida, capacidad_nominal_bateria, carbon_data
# ==============================================================================
# CLASE PARA EL REPORTE PDF
# ==============================================================================

class PropuestaPDF(FPDF):
    def __init__(self, client_name="Cliente", project_name="Proyecto", 
                 documento="", direccion="", fecha=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_name = client_name
        self.project_name = project_name
        self.documento_cliente = documento
        self.direccion_proyecto = direccion
        self.fecha_propuesta = fecha if fecha else datetime.date.today()
        
        try:
            self.add_font('DMSans', '', 'assets/DMSans-Regular.ttf')
            self.add_font('DMSans', 'B', 'assets/DMSans-Bold.ttf')
            self.add_font('Roboto', '', 'assets/Roboto-Regular.ttf')
            self.add_font('Roboto', 'B', 'assets/Roboto-Bold.ttf')
            self.font_family = 'DMSans'
        except RuntimeError as e:
            st.warning(f"No se encontraron todos los archivos de fuente (.ttf). Usando Arial. Error: {e}")
            self.font_family = 'Arial'

    def header(self): pass
    def footer(self): pass

    def crear_portada(self):
        self.add_page()
        self.image('assets/1.jpg', x=0, y=0, w=210)
        
        self.set_text_color(250, 50, 63) # Color rojo/rosado
        
        # --- Dirección del Proyecto (con MultiCell para auto-ajuste) ---
        self.set_xy(115, 47.5) 
        self.set_font(self.font_family, 'B', 30)
        # Ancho máximo de 85mm (210mm de página - 115mm de margen X - 10mm margen derecho)
        self.multi_cell(85, 12, self.direccion_proyecto, 0, 'L')
        
        # --- Nombre del Cliente (se posiciona automáticamente debajo) ---
        self.set_x(115) # Mantenemos la misma coordenada X
        self.set_font(self.font_family, '', 12)
        self.cell(0, 10, f"Sr(a): {self.client_name}")
        
        # --- Fecha (con posición Y ajustada para evitar salto de página) ---
        self.set_xy(147, 260) # Subimos un poco la fecha
        self.set_font(self.font_family, '', 12)
        self.cell(0, 10, self.fecha_propuesta.strftime('%d/%m/%Y'))

    def crear_indice(self):
        self.add_page()
        self.image('assets/2.jpg', x=0, y=0, w=210)

    def crear_resumen_ejecutivo(self, datos):
        self.add_page()
        self.image('assets/3.jpg', x=0, y=0, w=210)
        self.set_text_color(0, 0, 0) # Color negro

        # --- 1. Bloque de TIR ---
        valor_tir = datos.get('TIR (Tasa Interna de Retorno)', '0%').replace('%', '')
        self.set_font('DMSans', 'B', 40)
        self.set_xy(76, 69)
        self.cell(w=30, txt=valor_tir, align='L')

        # --- 2. Bloque de Ahorro Anual ---
        valor_ahorro_str = datos.get('Ahorro Estimado Primer Ano (COP)', '0').replace(',', '')
        valor_ahorro_millones = float(valor_ahorro_str) / 1000000
        self.set_font('DMSans', 'B', 40)
        self.set_xy(32, 106)
        self.cell(w=30, txt=f"{valor_ahorro_millones:.0f}", align='L')

        # --- 3. Bloque de Tiempo de Retorno ---
        valor_retorno = datos.get('Periodo de Retorno (anos)', '0')
        self.set_font('Roboto', 'B', 15) # Fuente y tamaño personalizados para este campo
        self.set_xy(170, 75)
        self.cell(w=20, txt=str(valor_retorno), align='L')

        # --- 4. Bloque de Potencia (kWp) ---
        valor_kwp = datos.get('Tamano del Sistema (kWp)', '0')
        self.set_font('DMSans', 'B', 40)
        self.set_xy(43, 146)
        self.cell(w=30, txt=str(valor_kwp), align='L')
        
        # --- 5. Bloque de Árboles ---
        valor_arboles = datos.get('Árboles Equivalentes Ahorrados', '0')
        self.set_font('DMSans', 'B', 40)
        self.set_xy(32.5, 188)
        self.cell(w=30, txt=f"+{valor_arboles}", align='L')
    
    def crear_detalle_sistema(self, datos):
        self.add_page()
        self.image('assets/4.jpg', x=0, y=0, w=210)
        
        cantidad_paneles = str(datos.get('Cantidad de Paneles', 'XX').split(' ')[0])

        # --- 1. Número grande al lado de la 'x' ---
        self.set_xy(43, 76) 
        self.set_font('DMSans', 'B', 45)
        # CORRECCIÓN: Color de texto a negro
        self.set_text_color(0, 0, 0) 
        self.cell(w=30, txt=cantidad_paneles, align='L')

        # --- 2. Número pequeño dentro del párrafo ---
        self.set_xy(34, 117) 
        self.set_text_color(0, 0, 0)
        # CORRECCIÓN: Estilo de fuente a normal (sin 'B')
        self.set_font('Roboto', '', 15) 
        self.cell(w=10, txt=cantidad_paneles, align='C')

    def crear_pagina_generacion_mensual(self, datos):
        self.add_page()
        self.image('assets/5.jpg', x=0, y=0, w=210)
        
        # --- 1. Colocar la gráfica de generación ---
        # Coordenadas (X, Y) y Ancho (W) estimados en mm. ¡Estos son los valores a ajustar!
        x_grafica = 15
        y_grafica = 120
        ancho_grafica = 180
        self.image('grafica_generacion.png', x=x_grafica, y=y_grafica, w=ancho_grafica)
        
        # --- 2. Escribir solo el número de la generación promedio ---
        # Coordenadas estimadas para el número. ¡Este es el otro valor a ajustar!
        self.set_xy(86, 97)
        self.set_text_color(0, 0, 0) # Texto negro
        self.set_font('Roboto', 'B', 15) # Negrita
        
        # Formateamos el número sin decimales (0f)
        valor_generacion = float(datos.get('Generacion Promedio Mensual (kWh)', '0').replace(',', ''))
        self.cell(w=30, txt=f"{valor_generacion:,.0f}", align='L')
    
    def crear_pagina_ubicacion(self, lat, lon):
        self.add_page()
        self.image('assets/6.jpg', x=0, y=0, w=210)
        
        # --- Coordenadas dinámicas ---
        # Posicionamos el cursor para escribir las coordenadas
        self.set_xy(20, 88) # Puedes ajustar esta coordenada Y si es necesario
        self.set_text_color(0, 0, 0)
        self.set_font('Roboto', '', 15)
        
        # Escribimos únicamente las coordenadas
        self.cell(w=0, h=5, txt=f"{lat:.6f}, {lon:.6f}")
        
        # --- Imagen del mapa estático ---
        x_mapa = 15
        y_mapa = 120
        ancho_mapa = 180
        
        if os.path.exists("assets/mapa_ubicacion.jpg"):
            self.image("assets/mapa_ubicacion.jpg", x=x_mapa, y=y_mapa, w=ancho_mapa)
        else:
            self.set_xy(x_mapa, y_mapa)
            self.cell(w=ancho_mapa, h=100, txt="No se pudo generar el mapa.", border=1, align='C')

    def crear_pagina_tecnica(self, datos):
        self.add_page()
        self.image('assets/7.jpg', x=0, y=0, w=210)
        
        self.set_font('Roboto', '', 14)
        self.set_text_color(0, 0, 0)
        
        # --- Posicionamos cada dato con alineación a la derecha ---
        
        # Definimos el área donde debe ir el texto.
        # El texto comenzará a escribirse desde x_inicio y terminará en x_fin.
        x_inicio = 90 # Margen izquierdo de la columna de datos (ajustable)
        ancho_total = 88 # Ancho máximo para el texto (ajustable)

        # Tipo de cubierta
        self.set_xy(x_inicio, 55)
        self.cell(w=ancho_total, txt=datos.get("Tipo de Cubierta", "N/A"), align='R')
        
        # Área Requerida
        self.set_xy(x_inicio, 64)
        self.cell(w=ancho_total, txt=f"{datos.get('Área Requerida Aprox. (m²)', 'XX')} m²", align='R')
        
        # Potencia Módulos FV
        self.set_xy(x_inicio, 108)
        self.cell(w=ancho_total, txt=f"{datos.get('Potencia de Paneles', 'XXX')} Wp", align='R')
        
        # Cantidad Módulos FV
        self.set_xy(x_inicio, 117)
        self.cell(w=ancho_total, txt=f"{datos.get('Cantidad de Paneles', 'XX').split(' ')[0]}", align='R')
        
        # Potencia total en DC
        self.set_xy(x_inicio, 126)
        self.cell(w=ancho_total, txt=f"{datos.get('Tamano del Sistema (kWp)', 'X.X')} kWp", align='R')
        
        # Referencia inversores
        self.set_xy(x_inicio, 135)
        self.cell(w=ancho_total, txt=datos.get('Inversor Recomendado', 'N/A'), align='R')

        # Potencia total en AC
        self.set_xy(x_inicio, 153)
        self.cell(w=ancho_total, txt=f"{datos.get('Potencia AC Inversor', 'X')} kW", align='R')

    def crear_pagina_alcance(self):
        self.add_page()
        self.image('assets/8.jpg', x=0, y=0, w=210)     

    def crear_pagina_terminos(self, datos):
        self.add_page()
        self.image('assets/9.jpg', x=0, y=0, w=210)
        
        self.set_text_color(0, 0, 0)
        
        # --- Posicionamos los valores con alineación a la derecha ---
        # El área de texto terminará en la coordenada X de 198mm (ajustable)
        x_fin = 190
        ancho_celda = 80

        # --- Sistema solar FV ---
        self.set_font('Roboto', '', 14) # Estilo normal
        self.set_xy(x_fin - ancho_celda, 70) # Coordenada Y estimada
        self.cell(w=ancho_celda, txt=datos.get("Valor Sistema FV (sin IVA)", "$ 0"), align='R')

        # --- IVA ---
        self.set_font('Roboto', 'B', 14) # Estilo negrita
        self.set_xy(x_fin - ancho_celda, 96) # Coordenada Y estimada
        self.cell(w=ancho_celda, txt=datos.get("Valor IVA", "$ 0"), align='R')
        
        # --- Total con IVA ---
        self.set_font('Roboto', 'B', 14) # Estilo negrita
        self.set_xy(x_fin - ancho_celda, 106) # Coordenada Y estimada
        self.cell(w=ancho_celda, txt=datos.get("Valor Total del Proyecto (COP)", "$ 0"), align='R')
    def crear_pagina_aspectos_1(self):
        self.add_page()
        self.image('assets/10.jpg', x=0, y=0, w=210)
        
    def crear_pagina_aspectos_2(self):
        self.add_page()
        self.image('assets/11.jpg', x=0, y=0, w=210)
        
    def crear_pagina_aspectos_3(self):
        self.add_page()
        self.image('assets/12.jpg', x=0, y=0, w=210)
        
    def crear_pagina_proyectos(self):
        self.add_page()
        self.image('assets/13.jpg', x=0, y=0, w=210)
        

        
    def crear_pagina_contacto(self):
        self.add_page()
        self.image('assets/14.jpg', x=0, y=0, w=210)


    def crear_pagina_financiacion(self, datos):
        self.add_page()
        self.image('assets/fin.jpg', x=0, y=0, w=210)
        
        self.set_text_color(0, 0, 0) # Texto negro
        
        # --- Posicionamos los datos de financiación (Coordenadas estimadas) ---
        
        # Anticipo (Desembolso Inicial) - formato simplificado
        self.set_font('Roboto', 'B', 35)
        self.set_xy(42, 56)
        desembolso_str = datos.get("Desembolso Inicial (COP)", "0")
        desembolso_valor = float(desembolso_str.replace("$", "").replace(",", "")) if desembolso_str != "0" else 0
        desembolso_millones = desembolso_valor / 1000000
        self.cell(w=50, txt=f"{desembolso_millones:.1f}", align='C')

        # Cuota Mensual - formato simplificado
        self.set_font('Roboto', 'B', 35)
        self.set_xy(42, 94)
        cuota_str = datos.get("Cuota Mensual del Credito (COP)", "0")
        cuota_valor = float(cuota_str.replace("$", "").replace(",", "")) if cuota_str != "0" else 0
        cuota_millones = cuota_valor / 1000000
        self.cell(w=50, txt=f"{cuota_millones:.1f}", align='C')

        # Ahorro Mensual - calcular como promedio de generación año 1 × precio del kWh
        self.set_font('Roboto', 'B', 35)
        self.set_xy(42, 132)
        ahorro_anual_str = datos.get("Ahorro Estimado Primer Ano (COP)", "0")
        ahorro_anual_valor = float(ahorro_anual_str.replace("$", "").replace(",", "")) if ahorro_anual_str != "0" else 0
        ahorro_mensual_calculado = ahorro_anual_valor / 12
        ahorro_millones = ahorro_mensual_calculado / 1000000
        self.cell(w=50, txt=f"{ahorro_millones:.1f}", align='C')
        
        # --- Variables adicionales ---
        # Obtener plazo del crédito real (en meses)
        plazo_credito = datos.get("Plazo del Crédito", "0")
        # Vida útil = plazo del crédito en años (convertir meses a años)
        vida_util = str(int(plazo_credito) // 12) if plazo_credito != "0" else "0"
        
        # Plazo del crédito
        self.set_font('Roboto', 'B', 15)
        self.set_xy(104,191)
        self.cell(w=50, txt=str(plazo_credito), align='C')
        
        # Vida útil del proyecto (igual al plazo del crédito)
        self.set_font('Roboto', 'B', 15)
        self.set_xy(19,214)
        self.cell(w=50, txt=str(vida_util), align='C')

    def generar(self, datos_calculadora, usa_financiamiento, lat=None, lon=None):
        """
        Llama a todos los métodos en orden para construir el documento.
        """
        self.crear_portada()
        self.crear_indice()
        self.crear_resumen_ejecutivo(datos_calculadora)
        self.crear_detalle_sistema(datos_calculadora)
        self.crear_pagina_generacion_mensual(datos_calculadora)
        if lat is not None and lon is not None:
            self.crear_pagina_ubicacion(lat, lon)
        self.crear_pagina_tecnica(datos_calculadora)
        self.crear_pagina_alcance()
        self.crear_pagina_terminos(datos_calculadora)
        
        # Página de financiación solo si se requiere
        if usa_financiamiento:
            self.crear_pagina_financiacion(datos_calculadora)
        
        self.crear_pagina_aspectos_1()
        self.crear_pagina_aspectos_2()
        self.crear_pagina_aspectos_3()
        self.crear_pagina_proyectos()
        self.crear_pagina_contacto()
    

        
        return bytes(self.output(dest='S'))
        

# ==============================================================================
# FUNCIONES DE INTEGRACIÓN CON GOOGLE DRIVE
# ==============================================================================

def obtener_siguiente_consecutivo(service, id_carpeta_padre):
    try:
        año_actual_corto = str(datetime.datetime.now().year)[-2:]
        query = f"'{id_carpeta_padre}' in parents and mimeType='application/vnd.google-apps.folder'"
        results = service.files().list(
            q=query, pageSize=1000, fields="files(name)",
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])
        max_num = 0
        patron = re.compile(f"FV{año_actual_corto}(\\d{{3}})")
        if items:
            for item in items:
                match = patron.search(item['name'])
                if match:
                    numero = int(match.group(1))
                    if numero > max_num: max_num = numero
        return max_num + 1
    except Exception as e:
        st.error(f"Error al buscar consecutivo en Drive: {e}")
        return 1

def crear_subcarpetas(service, id_carpeta_padre, estructura):
    for nombre_carpeta, sub_estructura in estructura.items():
        file_metadata = {'name': nombre_carpeta, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_carpeta_padre]}
        subfolder = service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute()
        if sub_estructura:
            crear_subcarpetas(service, subfolder.get('id'), sub_estructura)

def subir_pdf_a_drive(service, id_carpeta_destino, nombre_archivo, pdf_bytes):
    try:
        file_metadata = {'name': nombre_archivo, 'parents': [id_carpeta_destino]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
        file = service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True
        ).execute()
        st.info(f"📄 PDF guardado en la carpeta 'Propuesta y Contratación'.")
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Error al subir el PDF a Google Drive: {e}")
        return None
    
def subir_docx_a_drive(service, id_carpeta_destino, nombre_archivo, docx_bytes):
    try:
        file_metadata = {'name': nombre_archivo, 'parents': [id_carpeta_destino]}
        media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        st.info(f"📄 Contrato guardado en la carpeta 'Permisos y Legal'.")
    except Exception as e:
        st.error(f"Error al subir el contrato a Google Drive: {e}")

def gestionar_creacion_drive(service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf, contrato_bytes, nombre_contrato):
    try:
        folder_metadata = {'name': nombre_proyecto, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}
        folder = service.files().create(body=folder_metadata, fields='id, webViewLink', supportsAllDrives=True).execute()
        id_carpeta_principal_nueva = folder.get('id')
        
        if id_carpeta_principal_nueva:
            with st.spinner("Creando estructura de subcarpetas..."):
                crear_subcarpetas(service, id_carpeta_principal_nueva, ESTRUCTURA_CARPETAS)
            st.success("✅ Estructura de carpetas creada.")

            with st.spinner("Buscando carpeta de destino para el PDF..."):
                query = f"'{id_carpeta_principal_nueva}' in parents and name='01_Propuesta_y_Contratacion'"
                results = service.files().list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                items = results.get('files', [])
            
                if items:
                    id_carpeta_propuesta = items[0].get('id')
                    subir_pdf_a_drive(service, id_carpeta_propuesta, nombre_pdf, pdf_bytes)
                else:
                    st.warning("No se encontró la subcarpeta '01_Propuesta_y_Contratacion' para guardar el PDF.")
            with st.spinner("Buscando carpeta de destino para el contrato..."):
             query_contrato = f"'{id_carpeta_principal_nueva}' in parents and name='04_Permisos_y_Legal'"
             results_contrato = service.files().list(q=query_contrato, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
             items_contrato = results_contrato.get('files', [])
             if items_contrato:
                id_carpeta_contrato = items_contrato[0].get('id')
                subir_docx_a_drive(service, id_carpeta_contrato, nombre_contrato, contrato_bytes)
             else:
                st.warning("No se encontró la subcarpeta '04_Permisos_y_Legal'.")
        return folder.get('webViewLink')
    except Exception as e:
        st.error(f"Error en el proceso de Google Drive: {e}")
        return None
    


def calcular_lista_materiales(quantity, cubierta, module_power, inverter_info):
    """
    Calcula una lista de materiales de referencia, incluyendo los equipos principales.
    """
    if quantity <= 0:
        return {}

    # --- 1. Equipos Principales (NUEVO) ---
    lista_materiales = {
        f"Módulos Fotovoltaicos de {int(module_power)} W": int(quantity),
        "Inversor(es) Recomendado(s)": inverter_info
    }

    # --- 2. Cálculo de Perfiles ---
    paneles_por_fila_max = 4
    numero_de_filas = math.ceil(quantity / paneles_por_fila_max)
    perfiles_necesarios = numero_de_filas * 2
    perfiles_total = perfiles_necesarios + 1

    # --- 3. Cálculo de Clamps ---
    midclamps_total = (quantity * 2) + 2
    endclamps_total = (numero_de_filas * 4) + 2
    groundclamps_total = perfiles_total + 1
    
    # --- 4. Cálculo de Sujeción a Cubierta ---
    if cubierta.strip().upper() == "TEJA":
        tipo_sujecion = "Accesorio para Teja de Barro"
    else:
        tipo_sujecion = "Soporte en L (L-Feet)"
    
    longitud_total_perfiles = perfiles_total * 4.7
    sujeciones_necesarias = math.ceil(longitud_total_perfiles / 1)
    sujeciones_total = sujeciones_necesarias + 2

    # --- 5. Añadir los materiales de montaje al diccionario ---
    materiales_montaje = {
        "Perfiles de aluminio 4.7m": perfiles_total,
        "Mid Clamps (abrazaderas intermedias)": midclamps_total,
        "End Clamps (abrazaderas finales)": endclamps_total,
        "Ground Clamps (puesta a tierra)": groundclamps_total,
        tipo_sujecion: sujeciones_total
    }
    lista_materiales.update(materiales_montaje)
    
    return lista_materiales
    
# Reemplaza tu función get_pvgis_hsp con esta versión de depuración

def get_pvgis_hsp(lat, lon):
    """
    Se conecta a PVGIS, obtiene la radiación total mensual y la convierte a HSP diario.
    Incluye fallbacks robustos para datos incompletos.
    """
    try:
        # Validar coordenadas
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            st.warning("Coordenadas fuera de rango válido. Usando promedios de ciudad.")
            return None
        
        api_url = 'https://re.jrc.ec.europa.eu/api/MRcalc'
        params = {
            'lat': lat,
            'lon': lon,
            'horirrad': 1,
            'outputformat': 'json',
            'components': 1,  # Incluir componentes directos y difusos
        }
        
        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        outputs = data.get('outputs', {})
        monthly_data = outputs.get('monthly', [])

        if not monthly_data:
            st.warning("PVGIS no devolvió datos para esta ubicación. Usando promedios de ciudad.")
            return None
        
        # --- LÓGICA MEJORADA CON FALLBACKS ---
        dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        hsp_mensual = []
        
        # Intentar diferentes claves de datos de PVGIS
        for month in monthly_data:
            hsp_diario = None
            
            # Opción 1: Usar H(h)_m (radiación horizontal total)
            if 'H(h)_m' in month and month['H(h)_m'] is not None:
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    hsp_diario = month['H(h)_m'] / dias_por_mes[month_index]
            
            # Opción 2: Usar H_d (radiación difusa) + H_b (radiación directa)
            elif 'H_d' in month and 'H_b' in month:
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    hsp_diario = (month['H_d'] + month['H_b']) / dias_por_mes[month_index]
            
            # Opción 3: Usar G(i) (radiación en el plano del array)
            elif 'G(i)' in month:
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    hsp_diario = month['G(i)'] / dias_por_mes[month_index]
            
            # Si no se pudo obtener el valor, usar estimación inteligente
            if hsp_diario is None or hsp_diario <= 0:
                # Estimación basada en latitud y mes
                month_index = month.get('month', 1) - 1
                if 0 <= month_index < len(dias_por_mes):
                    # Estimación simple basada en latitud
                    if abs(lat) < 10:  # Zona ecuatorial
                        hsp_diario = 5.0 + 0.5 * math.sin(2 * math.pi * month_index / 12)
                    elif abs(lat) < 30:  # Zona tropical
                        hsp_diario = 4.5 + 0.8 * math.sin(2 * math.pi * month_index / 12)
                    else:  # Zona templada
                        hsp_diario = 3.5 + 1.5 * math.sin(2 * math.pi * month_index / 12)
                else:
                    hsp_diario = 4.5  # Valor por defecto
            
            hsp_mensual.append(round(hsp_diario, 2))
        
        # Verificar que tenemos 12 meses
        if len(hsp_mensual) != 12:
            st.warning(f"PVGIS devolvió solo {len(hsp_mensual)} meses. Completando con estimaciones.")
            # Completar meses faltantes con estimaciones
            while len(hsp_mensual) < 12:
                month_index = len(hsp_mensual)
                if abs(lat) < 10:
                    hsp_diario = 5.0 + 0.5 * math.sin(2 * math.pi * month_index / 12)
                elif abs(lat) < 30:
                    hsp_diario = 4.5 + 0.8 * math.sin(2 * math.pi * month_index / 12)
                else:
                    hsp_diario = 3.5 + 1.5 * math.sin(2 * math.pi * month_index / 12)
                hsp_mensual.append(round(hsp_diario, 2))
        
        # Validar que todos los valores sean razonables
        for i, hsp in enumerate(hsp_mensual):
            if hsp < 1.0 or hsp > 8.0:  # Rango razonable para HSP
                st.warning(f"Valor HSP anómalo en mes {i+1}: {hsp} kWh/m². Ajustando...")
                # Reemplazar con valor estimado
                if abs(lat) < 10:
                    hsp_mensual[i] = round(5.0 + 0.5 * math.sin(2 * math.pi * i / 12), 2)
                elif abs(lat) < 30:
                    hsp_mensual[i] = round(4.5 + 0.8 * math.sin(2 * math.pi * i / 12), 2)
                else:
                    hsp_mensual[i] = round(3.5 + 1.5 * math.sin(2 * math.pi * i / 12), 2)
        
        st.success(f"✅ Datos HSP obtenidos de PVGIS para lat: {lat:.4f}, lon: {lon:.4f}")
        return hsp_mensual
        
    except requests.exceptions.RequestException as e:
        st.warning(f"Error de red al conectar con PVGIS: {e}")
        st.info("Usando datos estimados basados en la ubicación.")
        return get_hsp_estimado(lat, lon)
    except Exception as e:
        st.warning(f"Error al procesar los datos de PVGIS: {e}")
        st.info("Usando datos estimados basados en la ubicación.")
        return get_hsp_estimado(lat, lon)

def get_hsp_estimado(lat, lon):
    """
    Genera estimaciones de HSP basadas en la latitud cuando PVGIS falla.
    """
    dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    hsp_mensual = []
    
    # Estimación basada en latitud y estacionalidad
    for month_index in range(12):
        # Factor estacional (seno para simular variación anual)
        seasonal_factor = math.sin(2 * math.pi * month_index / 12)
        
        if abs(lat) < 10:  # Zona ecuatorial (poca variación)
            base_hsp = 5.0
            variation = 0.5
        elif abs(lat) < 30:  # Zona tropical (variación moderada)
            base_hsp = 4.5
            variation = 0.8
        else:  # Zona templada (alta variación)
            base_hsp = 3.5
            variation = 1.5
        
        hsp_diario = base_hsp + variation * seasonal_factor
        hsp_mensual.append(round(hsp_diario, 2))
    
    st.info("📊 Usando estimaciones de HSP basadas en la ubicación geográfica.")
    return hsp_mensual

def get_coords_from_address(address):
    """Convierte una dirección de texto en coordenadas (lat, lon)."""
    try:
        geolocator = Nominatim(user_agent="mirac_solar_calculator")
        # El timeout es importante para no sobrecargar el servidor gratuito
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except Exception as e:
        st.error(f"Error en la geocodificación: {e}")
        return None
    
def get_static_map_image(lat, lon, api_key):
    """
    Genera una URL para la API de Google Maps Static con alta resolución y
    capa híbrida, y descarga la imagen del mapa.
    """
    image_path = "assets/mapa_ubicacion.jpg"
    
    try:
        # Validar parámetros de entrada
        if not api_key or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            st.error("Parámetros inválidos para generar el mapa")
            return None
            
        # Parámetros para la imagen del mapa mejorada
        zoom = 16
        size = "600x400"
        maptype = "hybrid"
        scale = 2
        
        # Construimos la URL con los nuevos parámetros
        url = (f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom={zoom}"
               f"&size={size}&scale={scale}&maptype={maptype}"
               f"&markers=color:red%7C{lat},{lon}&key={api_key}")

        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            st.error(f"Google Maps API devolvió un error {response.status_code}.")
            return None

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(image_path), exist_ok=True)

        with open(image_path, "wb") as f:
            f.write(response.content)

        if os.path.exists(image_path) and os.path.getsize(image_path) > 1000:
            return image_path
        else:
            st.error("Se descargó un archivo de mapa vacío o inválido.")
            return None

    except Exception as e:
        st.error(f"Error al generar la imagen del mapa: {e}")
        return None
    
def generar_contrato_docx(datos_contrato):
    """
    Carga la plantilla de Word, reemplaza los placeholders y devuelve el documento en bytes.
    """
    try:
        # Cargamos la plantilla desde la carpeta assets
        doc = Document('assets/contrato_plantilla.docx')

        # Creamos un diccionario con los placeholders y sus valores
        context = {
            '{{NOMBRE_CLIENTE}}': datos_contrato.get('Cliente', ''),
            '{{DOCUMENTO_CLIENTE}}': datos_contrato.get('Documento del Cliente', ''),
            '{{DIRECCION_PROYECTO}}': datos_contrato.get('Dirección del Proyecto', ''),
            '{{TAMANO_DEL_SISTEMA_KWP}}': str(datos_contrato.get('Tamano del Sistema (kWp)', '')),
            '{{CANTIDAD_PANELES}}': str(datos_contrato.get('Cantidad de Paneles', '')).split(' ')[0],
            '{{POTENCIA_PANEL}}': str(datos_contrato.get('Potencia de Paneles', '')),
            '{{INVERSOR_RECOMENDADO}}': datos_contrato.get('Inversor Recomendado', ''),
            '{{VALOR_TOTAL_PROYECTO_NUMEROS}}': datos_contrato.get('Valor Total del Proyecto (COP)', ''),
            '{{FECHA_FIRMA}}': datos_contrato.get('Fecha de la Propuesta', '').strftime('%d de %B de %Y'),
        }

        # Convertimos el valor numérico a letras
        try:
            valor_str = datos_contrato.get('Valor Total del Proyecto (COP)', '$0')
            # Limpiar el string de caracteres no numéricos
            valor_limpio = valor_str.replace('$', '').replace(',', '').replace(' ', '')
            valor_numerico = int(float(valor_limpio))
            context['{{VALOR_TOTAL_PROYECTO_LETRAS}}'] = num2words(valor_numerico, lang='es').upper() + " PESOS M/CTE"
        except (ValueError, TypeError, AttributeError) as e:
            st.warning(f"No se pudo convertir el valor a letras: {e}")
            context['{{VALOR_TOTAL_PROYECTO_LETRAS}}'] = "CERO PESOS M/CTE"
        
        # Convertir fecha a español
        try:
            fecha = datos_contrato.get('Fecha de la Propuesta', datetime.date.today())
            
            # Manejar diferentes tipos de fecha
            if isinstance(fecha, str):
                # Intentar diferentes formatos de fecha
                formatos_fecha = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']
                fecha_parseada = None
                
                for formato in formatos_fecha:
                    try:
                        fecha_parseada = datetime.datetime.strptime(fecha, formato).date()
                        break
                    except ValueError:
                        continue
                
                if fecha_parseada:
                    fecha = fecha_parseada
                else:
                    raise ValueError(f"No se pudo parsear la fecha: {fecha}")
            
            # Diccionario de meses en español
            meses_espanol = {
                1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
            }
            
            # Formatear fecha en español
            dia = fecha.day
            mes = meses_espanol[fecha.month]
            año = fecha.year
            
            fecha_espanol = f"{dia} de {mes} de {año}"
            context['{{FECHA_FIRMA}}'] = fecha_espanol
            
        except Exception as e:
            st.warning(f"No se pudo formatear la fecha en español: {e}")
            # Fallback a formato básico
            try:
                if hasattr(datos_contrato.get('Fecha de la Propuesta', ''), 'strftime'):
                    context['{{FECHA_FIRMA}}'] = datos_contrato.get('Fecha de la Propuesta', '').strftime('%d/%m/%Y')
                else:
                    context['{{FECHA_FIRMA}}'] = "fecha no disponible"
            except:
                context['{{FECHA_FIRMA}}'] = "fecha no disponible"

        # Reemplazamos los placeholders en los párrafos
        for p in doc.paragraphs:
            for key, value in context.items():
                if key in p.text:
                    inline = p.runs
                    # Reemplazamos el texto manteniendo el formato original
                    for i in range(len(inline)):
                        if key in inline[i].text:
                            text = inline[i].text.replace(key, value)
                            inline[i].text = text
        
        # Guardamos el documento en la memoria
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        
        return file_stream.getvalue()

    except Exception as e:
        st.error(f"Error al generar el contrato: {e}")
        return None
# ==============================================================================
# INTERFAZ Y LÓGICA PRINCIPAL DE LA APLICACIÓN
# ==============================================================================

# ==============================================================================
# INTERFAZ Y LÓGICA PRINCIPAL DE LA APLICACIÓN
# ==============================================================================

def detect_mobile_device():
    """Función simple para detectar modo móvil"""
    return st.session_state.get('force_mobile', False)

def apply_responsive_css():
    """Aplica CSS responsive para móviles"""
    st.markdown("""
    <style>
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

def render_mobile_interface():
    """Interfaz optimizada para móviles"""
    # Debug visual - confirmar que estamos en modo móvil
    st.markdown("""
    <div style="background: #ff6b6b; color: white; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; border: 3px solid #ff4757;">
        <h1 style="margin: 0; color: white;">📱 MODO MÓVIL ACTIVADO 📱</h1>
        <p style="margin: 10px 0; font-size: 18px;">Interfaz optimizada para dispositivos móviles</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header móvil con indicador claro
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.markdown("📱")
    with col2:
        st.title("☀️ Calculadora Solar")
    with col3:
        st.markdown("📱")
    
    st.success("✅ Interfaz móvil cargada correctamente")
    
    # Información del modo móvil
    with st.expander("ℹ️ Información del Modo Móvil", expanded=False):
        st.markdown("""
        **Características del modo móvil:**
        - 📱 Interfaz optimizada para pantallas pequeñas
        - 🗂️ Navegación por tabs para mejor organización
        - 📍 Mapa interactivo para ubicación
        - ⚡ Cálculos automáticos del sistema
        - 📊 Generación completa de documentos
        - ☁️ Integración con Google Drive
        """)
    
    # Tabs principales con Ubicación
    tab1, tabUbic, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👤 Cliente", "📍 Ubicación", "⚡ Sistema", "💰 Finanzas", "📊 Resultados", "📁 Archivos", "🔌 Cargadores"
    ])
    
    with tab1:
        render_tab_cliente_mobile()
    with tabUbic:
        render_tab_ubicacion_mobile()
    with tab2:
        render_tab_sistema_mobile()
    with tab3:
        render_tab_finanzas_mobile()
    with tab4:
        render_tab_resultados_mobile()
    with tab5:
        render_tab_archivos_mobile()
    with tab6:
        render_tab_cargadores_mobile()

def render_tab_cliente_mobile():
    """Tab de cliente para interfaz móvil"""
    st.header("👤 Datos del Cliente")
        
        # Datos del cliente
    nombre_cliente = st.text_input("Nombre del Cliente", key="nombre_mobile")
    documento_cliente = st.text_input("Documento del Cliente (CC o NIT)", key="doc_mobile")
    direccion_proyecto = st.text_input("Dirección del Proyecto", key="dir_mobile")
    fecha_propuesta = st.date_input("Fecha de la Propuesta", datetime.date.today(), key="fecha_mobile")
    
    if st.button("💾 Guardar Datos del Cliente", use_container_width=True):
        st.session_state.cliente_data = {
            'nombre': nombre_cliente,
            'documento': documento_cliente,
            'direccion': direccion_proyecto,
            'fecha': fecha_propuesta
        }
        st.success("✅ Datos del cliente guardados")

def render_tab_ubicacion_mobile():
    """Tab de ubicación con mapa y PVGIS para móviles"""
    st.header("📍 Ubicación del Proyecto")
    
    # Búsqueda opcional si hay API key
    gmaps = None
    try:
        gmaps = googlemaps.Client(key=os.environ.get("Maps_API_KEY"))
    except Exception:
        pass
    
    address = st.text_input("Buscar dirección o lugar:", placeholder="Ej: Cl. 77 Sur #40-168, Sabaneta", key="address_search_mobile")
    if st.button("🔎 Buscar Dirección", key="buscar_dir_mobile") and address and gmaps:
        with st.spinner("Buscando dirección..."):
            res = gmaps.geocode(address, region='CO')
            if res:
                loc = res[0]['geometry']['location']
                coords = [loc['lat'], loc['lng']]
                st.session_state.map_state = st.session_state.get('map_state', {"center":[4.5709,-74.2973],"zoom":6,"marker":None})
                st.session_state.map_state["marker"] = coords
                st.session_state.map_state["center"] = coords
                st.session_state.map_state["zoom"] = 16
                st.rerun()
            else:
                st.warning("Dirección no encontrada.")
    
    # Estado de mapa
    if "map_state" not in st.session_state:
        st.session_state.map_state = {"center":[4.5709,-74.2973],"zoom":6,"marker":None}
    
    m = folium.Map(location=st.session_state.map_state["center"], zoom_start=st.session_state.map_state["zoom"])
    if st.session_state.map_state["marker"]:
        folium.Marker(location=st.session_state.map_state["marker"], popup="Ubicación", icon=folium.Icon(color="red")).add_to(m)
    
    map_data = st_folium(m, width=700, height=400, key="folium_map_mobile")
    if map_data and map_data.get("last_clicked"):
        st.session_state.map_state["marker"] = [map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]]
        st.session_state.map_state["center"] = st.session_state.map_state["marker"]
        st.session_state.map_state["zoom"] = 16
        st.rerun()
    
    # PVGIS
    hsp_mensual_calculado = None
    latitud = longitud = None
    if st.session_state.map_state["marker"]:
        latitud, longitud = st.session_state.map_state["marker"]
        st.write(f"Coordenadas: `{latitud:.6f}`, `{longitud:.6f}`")
        if 'pvgis_data' not in st.session_state or st.session_state.get('last_coords') != (latitud, longitud):
            with st.spinner("Consultando PVGIS..."):
                st.session_state.pvgis_data = get_pvgis_hsp(latitud, longitud)
                st.session_state.last_coords = (latitud, longitud)
        hsp_mensual_calculado = st.session_state.pvgis_data
        if hsp_mensual_calculado:
            prom = sum(hsp_mensual_calculado)/len(hsp_mensual_calculado)
            st.metric("Promedio Diario Anual (HSP)", f"{prom:.2f} kWh/m²")
            with st.expander("📊 HSP mensual"):
                meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
                for mes, hsp in zip(meses, hsp_mensual_calculado):
                    st.write(f"{mes}: {hsp:.2f}")
    else:
        st.info("Toca el mapa para fijar la ubicación.")

def render_tab_sistema_mobile():
    """Tab de sistema para interfaz móvil"""
    st.header("⚡ Configuración del Sistema")
    
    # Parámetros del sistema
    consumo = st.number_input("Consumo mensual promedio (kWh)", min_value=100, max_value=10000, value=700, step=50, key="consumo_mobile")
    potencia_panel = st.selectbox("Potencia del panel (W)", [400, 450, 500, 550, 600, 615, 650, 700, 750], index=5, key="pot_panel_mobile")
    cubierta = st.selectbox("Tipo de cubierta", ["LÁMINA", "TEJA", "CONCRETO"], key="cubierta_mobile")
    clima = st.selectbox("Clima predominante", ["SOL", "NUBLADO", "LLUVIA"], key="clima_mobile")
    
    # Cálculo automático de cantidad y tamaño
    cantidad = max(1, round((consumo * 1.2) / (4.5 * 30 * 0.85) * 1000 // int(potencia_panel)))
    size = round(cantidad * potencia_panel / 1000, 2)
    
    st.info(f"📊 Sistema calculado: {cantidad} paneles de {potencia_panel}W = {size} kWp")
    
    if st.button("💾 Guardar Configuración del Sistema", use_container_width=True):
        st.session_state.sistema_data = {
            'consumo': consumo,
            'potencia_panel': potencia_panel,
            'cubierta': cubierta,
            'clima': clima,
            'quantity': cantidad,
            'size': size
        }
        st.success("✅ Configuración del sistema guardada")

def render_tab_finanzas_mobile():
    """Tab de finanzas para interfaz móvil"""
    st.header("💰 Parámetros Financieros")
    
    
    # Opción de precio manual para emergencias y descuentos
    precio_manual = st.toggle("💰 Precio Manual (Emergencias/Descuentos)", help="Activa esta opción para ingresar un precio personalizado del proyecto", key="precio_manual_mobile")
    
    if precio_manual:
        precio_manual_valor = st.number_input("Precio Manual del Proyecto (COP)", min_value=1000000, value=50000000, step=100000, help="Ingresa el precio total del proyecto en COP", key="precio_manual_valor_mobile")
        st.warning("⚠️ **Modo Precio Manual Activado** - Se usará este valor en lugar del cálculo automático")
    else:
        precio_manual_valor = None
    
    # Horizonte de tiempo para análisis financiero
    horizonte_tiempo = st.selectbox(
        "📅 Horizonte de Análisis (años)", 
        [15, 20, 25, 30, 35, 40], 
        index=2,  # 25 años por defecto
        help="Selecciona el período de análisis para calcular TIR, VPN y Payback",
        key="horizonte_mobile"
    )
    
    # Análisis de sensibilidad
    incluir_analisis_sensibilidad = st.toggle(
        "🔍 Análisis de Sensibilidad", 
        help="Genera un análisis comparativo de TIR a 10 y 20 años con y sin financiación",
        key="sensibilidad_mobile"
    )
    
    if incluir_analisis_sensibilidad:
        st.info("📈 **Análisis de Sensibilidad**: Se calculará TIR a 10 y 20 años con y sin financiación")
    
    # Parámetros financieros
    costo_kwh = st.number_input("Costo del kWh (COP)", min_value=100, max_value=2000, value=850, step=50, key="costo_mobile")
    indexacion = st.slider("Inflación anual (%)", 0.0, 20.0, 5.0, 0.5, key="index_mobile")
    tasa_descuento = st.slider("Tasa de descuento (%)", 5.0, 25.0, 10.0, 0.5, key="tasa_mobile")
    
    # Financiamiento
    usa_financiamiento = st.checkbox("¿Incluir financiamiento?", key="fin_check_mobile")
    
    if usa_financiamiento:
        porcentaje = st.slider("Porcentaje financiado (%)", 0, 100, 70, 5, key="porc_mobile")
        tasa_interes = st.slider("Tasa de interés anual (%)", 0.0, 30.0, 15.0, 0.5, key="tasa_int_mobile")
        plazo = st.slider("Plazo del crédito (años)", 1, 20, 10, 1, key="plazo_mobile")
    else:
        porcentaje = 0
        tasa_interes = 0.0
        plazo = 0
    
    # Baterías
    incluir_baterias = st.checkbox("¿Incluir baterías?", key="bat_check_mobile")
    
    if incluir_baterias:
        dias_autonomia = st.slider("Días de autonomía", 1, 7, 2, 1, key="dias_mobile")
        costo_bateria = st.number_input("Costo por kWh de batería (COP)", min_value=500000, max_value=2000000, value=1000000, step=50000, key="costo_bat_mobile")
    else:
        dias_autonomia = 2
        costo_bateria = 0
    
    st.subheader("🌱 Cálculo de Emisiones de Carbono")
    incluir_carbon = st.toggle(
        "🌱 Incluir análisis de sostenibilidad",
        help="Calcula las emisiones de CO2 evitadas y equivalencias ambientales",
        key="incluir_carbon_mobile"
    )
    
    if st.button("💾 Guardar Parámetros Financieros", use_container_width=True):
        st.session_state.finanzas_data = {
            'costo_kwh': costo_kwh,
            'indexacion': indexacion,
            'tasa_descuento': tasa_descuento,
            'precio_manual': precio_manual,
            'precio_manual_valor': precio_manual_valor,
            'horizonte_tiempo': horizonte_tiempo,
            'incluir_analisis_sensibilidad': incluir_analisis_sensibilidad,
            'usa_financiamiento': usa_financiamiento,
            'porcentaje': porcentaje,
            'tasa_interes': tasa_interes,
            'plazo': plazo,
            'incluir_baterias': incluir_baterias,
            'dias_autonomia': dias_autonomia,
            'costo_bateria': costo_bateria,
            'incluir_carbon': incluir_carbon
        }
        st.success("✅ Parámetros financieros guardados")

def render_tab_resultados_mobile():
    """Tab de resultados para interfaz móvil"""
    st.header("📊 Resultados del Cálculo")

    if not all(k in st.session_state for k in ['cliente_data', 'sistema_data', 'finanzas_data']):
        st.warning("Completa Cliente, Sistema y Finanzas antes de ver resultados.")
        return

    # Mostrar resumen de datos ingresados
    with st.expander("📋 Resumen de Datos"):
        st.write("**Cliente:**", st.session_state.cliente_data.get('nombre', 'N/A'))
        st.write("**Sistema:**", f"{st.session_state.sistema_data.get('size', 'N/A')} kWp")
        st.write("**Consumo:**", f"{st.session_state.sistema_data.get('consumo', 'N/A')} kWh/mes")

    # Check if carbon analysis is enabled
    fin = st.session_state.finanzas_data
    incluir_carbon = bool(fin.get('incluir_carbon', False))

    if incluir_carbon:
        st.header("🌱 Impacto Ambiental y Sostenibilidad")
        st.info("📊 **Análisis de Sostenibilidad Activado**: Se calcularán las emisiones de carbono evitadas, equivalencias ambientales y valor de certificación.")

        # Carbon metrics in columns (mobile optimized)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.metric(
                "CO2 Evitado Anual",
                "Calculado al generar",
                help="Toneladas de CO2 evitadas por año"
            )
            st.metric(
                "Árboles Salvados",
                "Calculado al generar",
                help="Árboles equivalentes salvados por año"
            )
        with col_c2:
            st.metric(
                "Valor Carbono",
                "Calculado al generar",
                help="Valor potencial de certificación de carbono"
            )
            st.metric(
                "Autos Equivalentes",
                "Calculado al generar",
                help="Autos que dejarían de circular por año"
            )

        st.info("Los resultados detallados de sostenibilidad se mostrarán al generar la propuesta en el tab '📁 Archivos'.")

    st.info("Los resultados detallados se mostrarán al generar la propuesta en el tab '📁 Archivos'.")

def render_tab_archivos_mobile():
    """Generación real de propuesta, contrato, gráficos y subida a Drive"""
    st.header("📁 Archivos y Acciones")
    
    if not all(k in st.session_state for k in ['cliente_data','sistema_data','finanzas_data']):
        st.warning("Completa Cliente, Ubicación, Sistema y Finanzas antes de generar.")
        return
    
    cliente = st.session_state.cliente_data
    sistema = st.session_state.sistema_data
    fin = st.session_state.finanzas_data
    ciudad_input = st.selectbox("Ciudad (respaldo HSP si no hay PVGIS)", list(HSP_MENSUAL_POR_CIUDAD.keys()), key="ciudad_mobile")
    
    if st.button("🚀 Generar propuesta, contrato y gráficos", use_container_width=True, key="mobile_generar_full"):
        try:
            consumo = float(sistema.get('consumo',700))
            pot_panel = float(sistema.get('potencia_panel',615))
            cantidad = int(sistema.get('quantity') or max(1, round((consumo*1.2)/(4.5*30*0.85))*1000//int(pot_panel)))
            size = float(sistema.get('size') or round(cantidad*pot_panel/1000,2))
            cubierta = sistema.get('cubierta','LÁMINA')
            clima = sistema.get('clima','SOL')
            costkWh = float(fin.get('costo_kwh',850))
            index_input = float(fin.get('indexacion',5.0))/100.0
            dRate_input = float(fin.get('tasa_descuento',10.0))/100.0
            usa_fin = bool(fin.get('usa_financiamiento', False))
            perc_fin = int(fin.get('porcentaje',0)) if usa_fin else 0
            tasa_int = float(fin.get('tasa_interes',0.0))/100.0 if usa_fin else 0.0
            plazo = int(fin.get('plazo',0)) if usa_fin else 0
            incluir_bat = bool(fin.get('incluir_baterias', False))
            dias_auto = int(fin.get('dias_autonomia',2)) if incluir_bat else 2
            costo_kwh_bat = int(fin.get('costo_bateria',0)) if incluir_bat else 0
            
            hsp_data = st.session_state.get('pvgis_data') or HSP_MENSUAL_POR_CIUDAD[ciudad_input]
            ciudad_calc = (
                f"Coord. ({st.session_state.map_state['marker'][0]:.2f}, {st.session_state.map_state['marker'][1]:.2f})"
                if st.session_state.get('map_state',{}).get('marker') else ciudad_input
            )
            
            # Obtener horizonte de tiempo de los datos financieros
            horizonte_tiempo = fin.get('horizonte_tiempo', 25)

            # Sostenibilidad: usar la preferencia de Finanzas (móvil)
            incluir_carbon = bool(fin.get('incluir_carbon', False))

            val_total, size_calc, monto_fin, cuota_mensual, desembolso_ini, fcl, trees, monthly_gen, vpn, tir, cant_calc, life, rec_inv, lcoe, n_final, hsp_final, pot_ac, ahorro_a1, area_req, cap_bat, carbon_data = \
                cotizacion(consumo, size, cantidad, cubierta, clima, index_input, dRate_input, costkWh, int(pot_panel),
                    ciudad=ciudad_calc, hsp_lista=hsp_data,
                    perc_financiamiento=perc_fin, tasa_interes_credito=tasa_int, plazo_credito_años=plazo,
                    tasa_degradacion=0.001, precio_excedentes=300.0,
                    incluir_baterias=incluir_bat, costo_kwh_bateria=costo_kwh_bat,
                    profundidad_descarga=0.9, eficiencia_bateria=0.95, dias_autonomia=dias_auto,
                    horizonte_tiempo=horizonte_tiempo, incluir_carbon=incluir_carbon)
            
            # Aplicar precio manual si está activado
            precio_manual = fin.get('precio_manual', False)
            precio_manual_valor = fin.get('precio_manual_valor', None)
            
            if precio_manual and precio_manual_valor:
                val_total = precio_manual_valor
                # Recalcular financiamiento con el precio manual
                monto_fin = val_total * (perc_fin / 100)
                monto_fin = math.ceil(monto_fin)
                
                cuota_mensual = 0
                if monto_fin > 0 and plazo > 0 and tasa_int > 0:
                    tasa_mensual_credito = tasa_int / 12
                    num_pagos_credito = plazo * 12
                    cuota_mensual = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_fin))
                    cuota_mensual = math.ceil(cuota_mensual)
                
                desembolso_ini = val_total - monto_fin
                
                # RECALCULAR FLUJO DE CAJA COMPLETO con el precio manual
                fcl = []  # Reiniciar flujo de caja
                for i in range(life):
                    # Calcular ahorro anual para cada año
                    ahorro_anual_total = 0
                    if incluir_bat:
                        ahorro_anual_total = (consumo * 12) * costkWh
                    else:  # Lógica On-Grid
                        for gen_mes in monthly_gen:
                            consumo_mes = consumo
                            if gen_mes >= consumo_mes:
                                ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * 300.0)  # precio_excedentes = 300
                            else:
                                ahorro_mes = gen_mes * costkWh
                            ahorro_anual_total += ahorro_mes
                    
                    # Aplicar indexación
                    ahorro_anual_indexado = ahorro_anual_total * ((1 + index_input) ** i)
                    if i == 0: 
                        ahorro_a1 = ahorro_anual_total
                    
                    # Mantenimiento anual
                    mantenimiento_anual = 0.05 * ahorro_anual_indexado
                    
                    # Cuotas anuales del crédito
                    cuotas_anuales_credito = 0
                    if i < plazo: 
                        cuotas_anuales_credito = cuota_mensual * 12
                    
                    # Flujo anual
                    flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
                    fcl.append(flujo_anual)
                
                # Insertar desembolso inicial al inicio
                fcl.insert(0, -desembolso_ini)
                
                # Recalcular métricas financieras
                vpn = npf.npv(dRate_input, fcl)
                tir = npf.irr(fcl)
                
                st.success(f"✅ **Precio Manual Aplicado**: ${val_total:,.0f} COP")
                st.info("🔄 **Flujo de caja recalculado** con el precio manual para métricas correctas")
            
            # Mapa estático si hay coords
            lat = lon = None
            if st.session_state.get('map_state',{}).get('marker'):
                lat, lon = st.session_state.map_state['marker']
                api_key = os.environ.get("Maps_API_KEY")
                if api_key:
                    get_static_map_image(lat, lon, api_key)
            
            # Gráficos
            fig1, ax1 = plt.subplots(figsize=(10,5))
            meses_grafico = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
            if incluir_bat:
                gen_autoc = [min(g, consumo) for g in monthly_gen]
                bat = [max(0, g - min(g, consumo)) for g in monthly_gen]
                ax1.bar(meses_grafico, gen_autoc, color='orange', edgecolor='black', label='Autoconsumida')
                ax1.bar(meses_grafico, bat, bottom=gen_autoc, color='green', edgecolor='black', label='A batería')
                ax1.axhline(y=consumo, color='grey', linestyle='--', linewidth=1.0, label='Consumo')
            else:
                gen_autoc = []
                exc = []
                imp = []
                for g in monthly_gen:
                    if g >= consumo:
                        gen_autoc.append(consumo); exc.append(g - consumo); imp.append(0)
                    else:
                        gen_autoc.append(g); exc.append(0); imp.append(consumo - g)
                ax1.bar(meses_grafico, gen_autoc, color='orange', edgecolor='black', label='Autoconsumida')
                ax1.bar(meses_grafico, exc, bottom=gen_autoc, color='red', edgecolor='black', label='Excedentes')
                ax1.bar(meses_grafico, imp, bottom=gen_autoc, color='#2ECC71', edgecolor='black', label='Red')
                ax1.axhline(y=consumo, color='grey', linestyle='--', linewidth=1.0, label='Consumo')
            ax1.legend(); st.pyplot(fig1); fig1.savefig('grafica_generacion.png', bbox_inches='tight')
            
            fig2, ax2 = plt.subplots(figsize=(10,5))
            acum = np.cumsum(fcl)
            ax2.plot(np.arange(0, life+1), acum, marker='o', linestyle='-', color='green')
            ax2.axhline(0, color='grey', linestyle='--', linewidth=0.8)
            st.pyplot(fig2); fig2.savefig('grafica_flujo_caja.png', bbox_inches='tight')
            
            prom_gen = sum(monthly_gen)/len(monthly_gen) if monthly_gen else 0
            valor_total_red = math.ceil(val_total/100)*100
            valor_iva = math.ceil((valor_total_red * (PROMEDIOS_COSTO['IVA (Impuestos)']/100))/100)*100
            valor_sin_iva = valor_total_red - valor_iva
            
            datos_pdf = {
                "Nombre del Proyecto": f"{cliente.get('nombre','Cliente')} - {cliente.get('ubicacion','Proyecto')}",
                "Cliente": cliente.get('nombre','Cliente'),
                "Valor Total del Proyecto (COP)": f"${valor_total_red:,.0f}",
                "Valor Sistema FV (sin IVA)": f"${valor_sin_iva:,.0f}",
                "Valor IVA": f"${valor_iva:,.0f}",
                "Tamano del Sistema (kWp)": f"{size}",
                "Cantidad de Paneles": f"{int(cantidad)} de {int(pot_panel)}W",
                "Área Requerida Aprox. (m²)": f"{area_req}",
                "Inversor Recomendado": f"{rec_inv}",
                "Generacion Promedio Mensual (kWh)": f"{prom_gen:,.1f}",
                "Ahorro Estimado Primer Ano (COP)": f"{ahorro_a1:,.2f}",
                "TIR (Tasa Interna de Retorno)": f"{tir:.1%}",
                "VPN (Valor Presente Neto) (COP)": f"{vpn:,.2f}",
                "Periodo de Retorno (anos)": "N/A",
                "Tipo de Cubierta": cubierta,
                "Potencia de Paneles": f"{int(pot_panel)}",
                "Potencia AC Inversor": f"{pot_ac}",
                "Desembolso Inicial (COP)": f"${desembolso_ini:,.0f}",
                "Cuota Mensual del Credito (COP)": f"${cuota_mensual:,.0f}",
                "Plazo del Crédito": str(plazo * 12) if usa_fin else "0",
            }
            
            # Determinar si hay financiamiento
            usa_financiamiento = fin.get('usa_financiamiento', False)
            
            pdf = PropuestaPDF(client_name=cliente.get('nombre','Cliente'), project_name=datos_pdf["Nombre del Proyecto"], documento=cliente.get('documento',''), direccion=cliente.get('direccion',''), fecha=cliente.get('fecha', datetime.date.today()))
            pdf_bytes = pdf.generar(datos_pdf, usa_financiamiento, lat, lon)
            nombre_proyecto = datos_pdf["Nombre del Proyecto"]
            nombre_pdf_final = f"{nombre_proyecto}.pdf"
            datos_contrato = datos_pdf.copy(); datos_contrato['Fecha de la Propuesta'] = cliente.get('fecha', datetime.date.today())
            contrato_bytes = generar_contrato_docx(datos_contrato)
            
            # Subida a Drive (si hay credenciales)
            link_carpeta = None
            try:
                parent_folder_id = os.environ.get("PARENT_FOLDER_ID")
                creds = Credentials(None, refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"), token_uri='https://oauth2.googleapis.com/token', client_id=os.environ.get("GOOGLE_CLIENT_ID"), client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"), scopes=['https://www.googleapis.com/auth/drive'])
                drive_service = build('drive', 'v3', credentials=creds) if parent_folder_id else None
                if drive_service and parent_folder_id:
                    link_carpeta = gestionar_creacion_drive(drive_service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf_final, contrato_bytes, f"Contrato - {nombre_proyecto}.docx")
            except Exception:
                st.info("Google Drive no configurado, se omite subida.")
            
            # Análisis de Sensibilidad en móvil
            incluir_analisis_sensibilidad = fin.get('incluir_analisis_sensibilidad', False)
            if incluir_analisis_sensibilidad:
                st.header("📊 Análisis de Sensibilidad")
                st.info("🔍 **Análisis comparativo** de TIR a 10 y 20 años con y sin financiación")
                
                with st.spinner("Calculando análisis de sensibilidad..."):
                    # Calcular análisis de sensibilidad
                    analisis_sensibilidad = calcular_analisis_sensibilidad(
                        consumo, size, cantidad, cubierta, clima, index_input, dRate_input, 
                        costkWh, int(pot_panel), ciudad=ciudad_calc, hsp_lista=hsp_data,
                        incluir_baterias=incluir_bat, costo_kwh_bateria=costo_kwh_bat,
                        profundidad_descarga=0.9, eficiencia_bateria=0.95, 
                        dias_autonomia=dias_auto, perc_financiamiento=perc_fin, 
                        tasa_interes_credito=tasa_int, plazo_credito_años=plazo
                    )
                
                # Crear tabla comparativa
                st.subheader("📈 Comparativa de Escenarios")
                
                # Preparar datos para la tabla
                datos_tabla = []
                for escenario, datos in analisis_sensibilidad.items():
                    datos_tabla.append({
                        "Escenario": escenario,
                        "TIR": f"{datos['tir']:.1%}" if datos['tir'] is not None else "N/A",
                        "VPN (COP)": f"${datos['vpn']:,.0f}" if datos['vpn'] is not None else "N/A",
                        "Payback (años)": f"{datos['payback']:.2f}" if datos['payback'] is not None else "N/A",
                        "Desembolso Inicial": f"${datos['desembolso_inicial']:,.0f}",
                        "Cuota Mensual": f"${datos['cuota_mensual']:,.0f}" if datos['cuota_mensual'] > 0 else "N/A"
                    })
                
                # Mostrar tabla
                df_sensibilidad = pd.DataFrame(datos_tabla)
                st.dataframe(df_sensibilidad, use_container_width=True)
                
                # Análisis de conclusiones
                st.subheader("💡 Conclusiones del Análisis")
                
                # Encontrar mejores escenarios
                mejor_tir_10 = max([(k, v['tir']) for k, v in analisis_sensibilidad.items() if '10 años' in k and v['tir'] is not None], key=lambda x: x[1], default=(None, 0))
                mejor_tir_20 = max([(k, v['tir']) for k, v in analisis_sensibilidad.items() if '20 años' in k and v['tir'] is not None], key=lambda x: x[1], default=(None, 0))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Mejor TIR a 10 años", f"{mejor_tir_10[1]:.1%}" if mejor_tir_10[0] else "N/A", 
                             help=f"Escenario: {mejor_tir_10[0]}" if mejor_tir_10[0] else "")
                
                with col2:
                    st.metric("Mejor TIR a 20 años", f"{mejor_tir_20[1]:.1%}" if mejor_tir_20[0] else "N/A",
                             help=f"Escenario: {mejor_tir_20[0]}" if mejor_tir_20[0] else "")
                
                # Recomendaciones
                st.info("""
                **📋 Recomendaciones:**
                - **TIR más alta**: Indica mayor rentabilidad del proyecto
                - **Payback más bajo**: Indica recuperación más rápida de la inversión
                - **Con financiación**: Reduce desembolso inicial pero puede afectar TIR
                - **Sin financiación**: Mayor desembolso inicial pero potencialmente mejor TIR
                """)

            st.download_button("📥 Descargar Propuesta PDF", data=pdf_bytes, file_name=nombre_pdf_final, mime="application/pdf", use_container_width=True)
            if contrato_bytes:
                st.download_button("📝 Descargar Contrato Word", data=contrato_bytes, file_name=f"Contrato - {nombre_proyecto}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            if link_carpeta:
                st.info(f"➡️ [Abrir carpeta del proyecto en Google Drive]({link_carpeta})")
            st.success("✅ Propuesta, contrato y gráficos generados")

            # Notion CRM - agregar a "En conversaciones"
            agregado, msg = agregar_cliente_a_notion_crm(
                nombre=cliente.get('nombre',''),
                documento=cliente.get('documento',''),
                direccion=cliente.get('direccion',''),
                proyecto=datos_pdf.get('Nombre del Proyecto',''),
                fecha=cliente.get('fecha', datetime.date.today()),
                estado="En conversaciones"
            )
            if agregado:
                st.info("🗂️ Cliente agregado a Notion: En conversaciones")
            else:
                st.caption(f"Notion: {msg}")
        except Exception as e:
            st.error(f"❌ Error al generar: {e}")

def render_tab_cargadores_mobile():
    """Pestaña móvil para cotizar cargadores (sin financiamiento)."""
    st.header("🔌 Cotizador de Cargadores")
    nombre_cliente_lugar = st.text_input("Nombre del Cliente y Lugar", key="ev_nombre_mobile")
    distancia_m = st.number_input("Distancia parqueadero a subestación (m)", min_value=1.0, value=10.0, step=1.0, key="ev_dist_mobile")
    if st.button("🧮 Calcular y generar PDF de cargadores", use_container_width=True, key="ev_gen_mobile"):
        try:
            pdf_bytes, desglose = generar_pdf_cargadores(nombre_cliente_lugar or "Cliente", distancia_m)
            st.success("✅ Cotización generada")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Costo Base", formatear_moneda(desglose.get("Costo Base", 0)))
            col2.metric("IVA (19%)", formatear_moneda(desglose.get("IVA", 0)))
            col3.metric("Diseño (35%)", formatear_moneda(desglose.get("Diseño", 0)))
            col4.metric("Materiales (65%)", formatear_moneda(desglose.get("Materiales", 0)))
            st.metric("Costo Total", formatear_moneda(desglose.get("Costo Total", 0)))

            st.subheader("📋 Materiales estimados")
            lista = calcular_materiales_cargador(distancia_m)
            if lista:
                df_mat = pd.DataFrame(lista, columns=["Material", "Cantidad", "Unidad"])
                st.table(df_mat)

            nombre_pdf = f"Propuesta Mirac {nombre_cliente_lugar or 'Cliente'}.pdf"
            st.download_button("📥 Descargar PDF de Cargadores", data=pdf_bytes, file_name=nombre_pdf, mime="application/pdf", use_container_width=True)
        except Exception as ex:
            st.error(f"❌ Error generando la cotización de cargadores: {ex}")

def render_desktop_interface():
    """Interfaz optimizada para desktop (tu interfaz actual)"""
    # Debug visual - confirmar que estamos en modo desktop
    st.markdown("""
    <div style="background: #4ecdc4; color: white; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; border: 3px solid #45b7d1;">
        <h1 style="margin: 0; color: white;">🖥️ MODO DESKTOP ACTIVADO 🖥️</h1>
        <p style="margin: 10px 0; font-size: 18px;">Interfaz completa con sidebar</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header desktop con indicador claro
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.markdown("🖥️")
    with col2:
        st.title("☀️ Calculadora y Cotizador Solar Profesional")
    with col3:
        st.markdown("🖥️")
    
    st.success("✅ Interfaz desktop cargada correctamente")

    # --- INICIALIZACIÓN DE SERVICIOS Y DATOS ---
    drive_service = None
    numero_proyecto_del_año = 1
    parent_folder_id = None
    try:
        creds = Credentials(
            None, refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get("GOOGLE_CLIENT_ID"), 
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=creds)
        parent_folder_id = os.environ.get("PARENT_FOLDER_ID")
        if parent_folder_id:
            numero_proyecto_del_año = obtener_siguiente_consecutivo(drive_service, parent_folder_id)
        else:
            st.warning("ID de la carpeta padre no encontrado. El consecutivo iniciará en 1.")
    except Exception as e:
        st.warning(f"Secretos de Google Drive no configurados o inválidos. La creación de carpetas está desactivada.")

    # ==============================================================================
    # INTERFAZ EN LA BARRA LATERAL (SIDEBAR)
    # ==============================================================================
    with st.sidebar:
        st.header("Parámetros de Entrada")
        
        st.subheader("Datos del Cliente y Propuesta")
        nombre_cliente = st.text_input("Nombre del Cliente", "Andres Pinzón")
        documento_cliente = st.text_input("Documento del Cliente (CC o NIT)", "123.456.789-0")
        direccion_proyecto = st.text_input("Dirección del Proyecto", "Villa Roca 1 Int. 9B, Copacabana")
        fecha_propuesta = st.date_input("Fecha de la Propuesta", datetime.date.today()) 
        
        st.subheader("Información del Proyecto (Interna)")
        ubicacion = st.text_input("Ubicación (Etiqueta para carpeta)", "Villa Roca 1")
        st.text_input("Número de Proyecto del Año (Automático)", value=numero_proyecto_del_año, disabled=True)
        
        st.subheader("Ubicación Geográfica")
        gmaps = None
        try:
            gmaps = googlemaps.Client(key=os.environ.get("Maps_API_KEY"))
        except Exception as e:
            st.warning(f"API Key de Google Maps no configurada o inválida. La búsqueda está desactivada. Error: {e}")

        address = st.text_input("Buscar dirección o lugar:", placeholder="Ej: Cl. 77 Sur #40-168, Sabaneta", key="address_search")
        if st.button("Buscar Dirección"):
            if address and gmaps:
                with st.spinner("Buscando dirección..."):
                    geocode_result = gmaps.geocode(address, region='CO')
                    if geocode_result:
                        location = geocode_result[0]['geometry']['location']
                        coords = [location['lat'], location['lng']]
                        st.session_state.map_state["marker"] = coords
                        st.session_state.map_state["center"] = coords
                        st.session_state.map_state["zoom"] = 16
                        st.rerun()
                    else:
                        st.error("Dirección no encontrada.")
            elif not address:
                st.warning("Por favor, ingresa una dirección para buscar.")

        if "map_state" not in st.session_state:
            st.session_state.map_state = {"center": [4.5709, -74.2973], "zoom": 6, "marker": None}

        m = folium.Map(location=st.session_state.map_state["center"], zoom_start=st.session_state.map_state["zoom"])
        if st.session_state.map_state["marker"]:
            folium.Marker(location=st.session_state.map_state["marker"], popup="Ubicación del Proyecto", icon=folium.Icon(color="red")).add_to(m)
        map_data = st_folium(m, width=700, height=400, key="folium_map_main")
        if map_data and map_data["last_clicked"]:
            st.session_state.map_state["marker"] = [map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]]
            st.rerun()

        hsp_mensual_calculado = None
        latitud, longitud = None, None
        if st.session_state.map_state["marker"]:
            latitud, longitud = st.session_state.map_state["marker"]
            st.write(f"**Coordenadas Seleccionadas:** Lat: `{latitud:.6f}` | Long: `{longitud:.6f}`")
            if 'pvgis_data' not in st.session_state or st.session_state.get('last_coords') != (latitud, longitud):
                with st.spinner("Consultando base de datos satelital (PVGIS)..."):
                    st.session_state.pvgis_data = get_pvgis_hsp(latitud, longitud)
                    st.session_state.last_coords = (latitud, longitud)
            hsp_mensual_calculado = st.session_state.pvgis_data
            if hsp_mensual_calculado:
                promedio_hsp_anual = sum(hsp_mensual_calculado) / len(hsp_mensual_calculado)
                st.success("✅ Datos de HSP obtenidos de PVGIS.")
                st.metric(label="Promedio Diario Anual (HSP)", value=f"{promedio_hsp_anual:.2f} kWh/m²")
                
                # Mostrar detalles mensuales
                with st.expander("📊 Ver datos mensuales detallados"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**HSP Mensual (kWh/m²/día):**")
                        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
                        for i, (mes, hsp) in enumerate(zip(meses, hsp_mensual_calculado)):
                            st.write(f"{mes}: {hsp:.2f}")
                    
                    with col2:
                        st.write("**Análisis:**")
                        max_hsp = max(hsp_mensual_calculado)
                        min_hsp = min(hsp_mensual_calculado)
                        variacion = ((max_hsp - min_hsp) / promedio_hsp_anual) * 100
                        st.write(f"• Máximo: {max_hsp:.2f} kWh/m²")
                        st.write(f"• Mínimo: {min_hsp:.2f} kWh/m²")
                        st.write(f"• Variación: {variacion:.1f}%")
                
                # Mostrar calidad de los datos
                if any(hsp < 1.0 or hsp > 8.0 for hsp in hsp_mensual_calculado):
                    st.warning("⚠️ Algunos valores HSP están fuera del rango típico. Se han ajustado automáticamente.")
        else:
            st.info("👈 Escribe una dirección, busca, o haz clic directamente en el mapa.")

        ciudad_input = st.selectbox("Ciudad (usada como respaldo)", list(HSP_MENSUAL_POR_CIUDAD.keys()))
        
        if hsp_mensual_calculado:
            hsp_a_usar = hsp_mensual_calculado
            ciudad_para_calculo = f"Coord. ({latitud:.2f}, {longitud:.2f})"
        else:
            hsp_a_usar = HSP_MENSUAL_POR_CIUDAD[ciudad_input]
            ciudad_para_calculo = ciudad_input
        
        opcion = st.radio("Método para dimensionar:", ["Por Consumo Mensual (kWh)", "Por Cantidad de Paneles"], horizontal=True, key="metodo_dimensionamiento")

        if opcion == "Por Consumo Mensual (kWh)":
            Load = st.number_input("Consumo mensual (kWh)", min_value=50, value=700, step=50)
            module = st.number_input("Potencia del panel (W)", min_value=300, value=615, step=10)
            HSP_aprox = 4.5; n_aprox = 0.85; Ratio = 1.2
            size = round(Load * Ratio / (HSP_aprox * 30 * n_aprox), 2)
            quantity = round(size * 1000 / module)
            size = round(quantity * module / 1000, 2)
            st.info(f"Sistema estimado: **{size:.2f} kWp** ({int(quantity)} paneles)")
        else:
            module = st.number_input("Potencia del panel (W)", min_value=300, value=615, step=10)
            quantity = st.number_input("Cantidad de paneles", min_value=1, value=12, step=1)
            Load = st.number_input("Consumo mensual (kWh)", min_value=50, value=700, step=50)
            size = round((quantity * module) / 1000, 2)
            st.info(f"Sistema dimensionado: **{size:.2f} kWp**")

        st.subheader("Datos Generales")
        cubierta = st.selectbox("Tipo de cubierta", ["LÁMINA", "TEJA"])
        clima = st.selectbox("Clima predominante", ["SOL", "NUBE"])

        st.subheader("Parámetros Financieros")
        
        # Opción de precio manual para emergencias y descuentos
        precio_manual = st.toggle("💰 Precio Manual (Emergencias/Descuentos)", help="Activa esta opción para ingresar un precio personalizado del proyecto")
        
        if precio_manual:
            precio_manual_valor = st.number_input("Precio Manual del Proyecto (COP)", min_value=1000000, value=50000000, step=100000, help="Ingresa el precio total del proyecto en COP")
            st.warning("⚠️ **Modo Precio Manual Activado** - Se usará este valor en lugar del cálculo automático")
        else:
            precio_manual_valor = None
        
        # Horizonte de tiempo para análisis financiero
        horizonte_tiempo = st.selectbox(
            "📅 Horizonte de Análisis (años)", 
            [15, 20, 25, 30, 35, 40], 
            index=2,  # 25 años por defecto
            help="Selecciona el período de análisis para calcular TIR, VPN y Payback"
        )
        
        # Análisis de sensibilidad
        st.subheader("📊 Análisis de Sensibilidad")
        incluir_analisis_sensibilidad = st.toggle(
            "🔍 Incluir Análisis de Sensibilidad", 
            help="Genera un análisis comparativo de TIR a 10 y 20 años con y sin financiación"
        )
        
        # Debug: Mostrar el valor del toggle
        st.write(f"🔧 Debug - Toggle activado: {incluir_analisis_sensibilidad}")
        
        if incluir_analisis_sensibilidad:
            st.info("📈 **Análisis de Sensibilidad**: Se calculará TIR a 10 y 20 años con y sin financiación para mostrar la robustez del proyecto")
        
        costkWh = st.number_input("Costo por kWh (COP)", min_value=200, value=850, step=10)
        index_input = st.slider("Indexación de energía (%)", 0.0, 20.0, 5.0, 0.5)
        dRate_input = st.slider("Tasa de descuento (%)", 0.0, 25.0, 10.0, 0.5)
        
        st.subheader("Financiamiento")
        usa_financiamiento = st.toggle("Incluir financiamiento")
        perc_financiamiento, tasa_interes_input, plazo_credito_años = 0, 0, 0
        if usa_financiamiento:
            perc_financiamiento = st.slider("Porcentaje a financiar (%)", 0, 100, 70)
            tasa_interes_input = st.slider("Tasa de interés anual (%)", 0.0, 30.0, 15.0, 0.5)
            plazo_credito_años = st.number_input("Plazo del crédito (años)", 1, 20, 5)
        
        st.subheader("Almacenamiento (Baterías) - Modo Off-Grid")
        incluir_baterias = st.toggle("Añadir baterías (asumir sistema aislado)")
        dias_autonomia = 2
        if incluir_baterias:
            dias_autonomia = st.number_input("Días de autonomía deseados", 1, 7, 2, help="Días que el sistema debe soportar el consumo sin sol.")
            costo_kwh_bateria = st.number_input("Costo por kWh de batería (COP)", 100000, 5000000, 2500000, 100000)
            profundidad_descarga = st.slider("Profundidad de Descarga (DoD) (%)", 50.0, 100.0, 90.0, 0.5)
            eficiencia_bateria = st.slider("Eficiencia Carga/Descarga (%)", 80.0, 100.0, 95.0, 0.5)
        else:
            costo_kwh_bateria, profundidad_descarga, eficiencia_bateria = 0, 0, 0

        st.markdown("---")
        st.subheader("🌱 Cálculo de Emisiones de Carbono")
        incluir_carbon = st.toggle(
            "🌱 Incluir análisis de sostenibilidad",
            help="Calcula las emisiones de CO2 evitadas y equivalencias ambientales"
        )
        if incluir_carbon:
            st.info("📊 **Análisis de Sostenibilidad Activado**: Se calcularán las emisiones de carbono evitadas, equivalencias ambientales y valor de certificación.")

        st.markdown("---")
        st.subheader("🔌 Cotizador de Cargadores")
        ev_nombre = st.text_input("Cliente y Lugar (Cargadores)", "")
        ev_dist = st.number_input("Distancia parqueadero a subestación (m)", min_value=1.0, value=10.0, step=1.0)
        if st.button("Generar PDF Cargadores", use_container_width=True, key="ev_gen_desktop"):
            try:
                ev_pdf, ev_desglose = generar_pdf_cargadores(ev_nombre or "Cliente", ev_dist)
                st.success("✅ Cotización de Cargadores generada")
                col_ev1, col_ev2 = st.columns(2)
                with col_ev1:
                    st.metric("Costo Base", formatear_moneda(ev_desglose.get("Costo Base", 0)))
                    st.metric("IVA (19%)", formatear_moneda(ev_desglose.get("IVA", 0)))
                with col_ev2:
                    st.metric("Diseño (35%)", formatear_moneda(ev_desglose.get("Diseño", 0)))
                    st.metric("Materiales (65%)", formatear_moneda(ev_desglose.get("Materiales", 0)))
                st.metric("Costo Total", formatear_moneda(ev_desglose.get("Costo Total", 0)))
                st.download_button("📥 Descargar PDF de Cargadores", data=ev_pdf, file_name=f"Propuesta Mirac {ev_nombre or 'Cliente'}.pdf", mime="application/pdf", use_container_width=True)
            except Exception as ev_ex:
                st.error(f"❌ Error generando la cotización de cargadores: {ev_ex}")

    # ==============================================================================
    # LÓGICA DE CÁLCULO Y VISUALIZACIÓN (AL PRESIONAR EL BOTÓN)
    # ==============================================================================
    if st.button("   Calcular y Generar Reporte", use_container_width=True):
        # Validar datos de entrada
        errores_validacion = validar_datos_entrada(Load, size, quantity, cubierta, clima, costkWh, module)
        
        if errores_validacion:
            st.error("❌ Errores de validación encontrados:")
            for error in errores_validacion:
                st.error(f"• {error}")
            return
        
        with st.spinner('Realizando cálculos y creando archivos... ⏳'):
            nombre_proyecto = f"FV{str(datetime.datetime.now().year)[-2:]}{numero_proyecto_del_año:03d} - {nombre_cliente}" + (f" - {ubicacion}" if ubicacion else "")
            st.success(f"Proyecto Generado: {nombre_proyecto}")

            valor_proyecto_total, size_calc, monto_a_financiar, cuota_mensual_credito, \
            desembolso_inicial_cliente, fcl, trees, monthly_generation, valor_presente, \
            tasa_interna, cantidad_calc, life, recomendacion_inversor, lcoe, n_final, hsp_mensual_final, \
            potencia_ac_inversor, ahorro_año1, area_requerida, capacidad_nominal_bateria, carbon_data = \
                cotizacion(Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100, costkWh, module,
                            ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                            perc_financiamiento=perc_financiamiento, tasa_interes_credito=tasa_interes_input / 100,
                            plazo_credito_años=plazo_credito_años, tasa_degradacion=0.001, precio_excedentes=300.0,
                            incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                            profundidad_descarga=profundidad_descarga / 100,
                            eficiencia_bateria=eficiencia_bateria / 100, dias_autonomia=dias_autonomia,
                            horizonte_tiempo=horizonte_tiempo, incluir_carbon=incluir_carbon)
            
            # Aplicar precio manual si está activado
            if precio_manual and precio_manual_valor:
                valor_proyecto_total = precio_manual_valor
                # Recalcular financiamiento con el precio manual
                monto_a_financiar = valor_proyecto_total * (perc_financiamiento / 100)
                monto_a_financiar = math.ceil(monto_a_financiar)
                
                cuota_mensual_credito = 0
                if monto_a_financiar > 0 and plazo_credito_años > 0 and tasa_interes_input > 0:
                    tasa_mensual_credito = (tasa_interes_input / 100) / 12
                    num_pagos_credito = plazo_credito_años * 12
                    cuota_mensual_credito = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_a_financiar))
                    cuota_mensual_credito = math.ceil(cuota_mensual_credito)
                
                desembolso_inicial_cliente = valor_proyecto_total - monto_a_financiar
                
                # RECALCULAR FLUJO DE CAJA COMPLETO con el precio manual
                fcl = []  # Reiniciar flujo de caja
                for i in range(life):
                    # Calcular ahorro anual para cada año
                    ahorro_anual_total = 0
                    if incluir_baterias:
                        ahorro_anual_total = (Load * 12) * costkWh
                    else:  # Lógica On-Grid
                        for gen_mes in monthly_generation:
                            consumo_mes = Load
                            if gen_mes >= consumo_mes:
                                ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * 300.0)  # precio_excedentes = 300
                            else:
                                ahorro_mes = gen_mes * costkWh
                            ahorro_anual_total += ahorro_mes
                    
                    # Aplicar indexación
                    ahorro_anual_indexado = ahorro_anual_total * ((1 + index_input / 100) ** i)
                    if i == 0: 
                        ahorro_año1 = ahorro_anual_total
                    
                    # Mantenimiento anual
                    mantenimiento_anual = 0.05 * ahorro_anual_indexado
                    
                    # Cuotas anuales del crédito
                    cuotas_anuales_credito = 0
                    if i < plazo_credito_años: 
                        cuotas_anuales_credito = cuota_mensual_credito * 12
                    
                    # Flujo anual
                    flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
                    fcl.append(flujo_anual)
                
                # Insertar desembolso inicial al inicio
                fcl.insert(0, -desembolso_inicial_cliente)
                
                # Recalcular métricas financieras
                valor_presente = npf.npv(dRate_input / 100, fcl)
                tasa_interna = npf.irr(fcl)
                
                st.success(f"✅ **Precio Manual Aplicado**: ${valor_proyecto_total:,.0f} COP")
                st.info("🔄 **Flujo de caja recalculado** con el precio manual para métricas correctas")
            
            generacion_promedio_mensual = sum(monthly_generation) / len(monthly_generation) if monthly_generation else 0
            payback_simple = next((i for i, x in enumerate(np.cumsum(fcl)) if x >= 0), None)
            payback_exacto = None
            if payback_simple is not None:
                if payback_simple > 0 and (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1]) != 0:
                    payback_exacto = (payback_simple - 1) + abs(np.cumsum(fcl)[payback_simple-1]) / (np.cumsum(fcl)[payback_simple] - np.cumsum(fcl)[payback_simple-1])
                else:
                    payback_exacto = float(payback_simple)
            
            # DEBUG: Mostrar información del cálculo principal
            print(f"\n=== DEBUG CÁLCULO PRINCIPAL ===")
            print(f"Horizonte: {horizonte_tiempo}")
            print(f"Desembolso inicial: {desembolso_inicial_cliente:,.0f}")
            print(f"Primeros 10 flujos: {[f'{x:,.0f}' for x in fcl[:10]]}")
            print(f"Payback calculado: {payback_exacto}")
            print(f"Suma acumulada primeros 6 años: {[f'{x:,.0f}' for x in np.cumsum(fcl)[:6]]}")
            print("=" * 50)

            st.header("Resultados de la Propuesta")
            
            # Indicador del horizonte de tiempo
            st.info(f"📅 **Análisis financiero a {horizonte_tiempo} años** - TIR, VPN y Payback calculados para este período")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Valor del Proyecto", f"${valor_proyecto_total:,.0f}")
            col2.metric("TIR", f"{tasa_interna:.1%}")
            col3.metric("Payback (años)", f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A")
            if incluir_baterias:
                col4.metric("Batería Recomendada", f"{capacidad_nominal_bateria:.1f} kWh")
            else:
                col4.metric("Ahorro Año 1", f"${ahorro_año1:,.0f}")

            # Display carbon metrics if available
            if incluir_carbon and carbon_data and 'annual_co2_avoided_tons' in carbon_data:
                st.markdown("---")
                st.header("🌱 Impacto Ambiental y Sostenibilidad")

                # Carbon metrics in columns
                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                col_c1.metric(
                    "CO2 Evitado Anual",
                    f"{carbon_data['annual_co2_avoided_tons']:.1f} ton",
                    help="Toneladas de CO2 evitadas por año"
                )
                col_c2.metric(
                    "Árboles Salvados",
                    f"{carbon_data['trees_saved_per_year']:.0f}",
                    help="Árboles equivalentes salvados por año"
                )
                col_c3.metric(
                    "Valor Carbono",
                    f"${carbon_data['annual_certification_value_cop']:,.0f}",
                    help="Valor potencial de certificación de carbono"
                )
                col_c4.metric(
                    "Autos Equivalentes",
                    f"{carbon_data['cars_off_road_per_year']:.1f}",
                    help="Autos que dejarían de circular por año"
                )

                # Additional equivalencies
                with st.expander("📊 Ver más equivalencias ambientales"):
                    st.markdown("**Impacto Ambiental Detallado:**")
                    st.write(f"• **Vuelos evitados**: {carbon_data['flights_avoided_per_year']:.0f} vuelos de ida y vuelta")
                    st.write(f"• **Botellas de plástico**: {carbon_data['plastic_bottles_avoided_per_year']:,.0f} botellas recicladas")
                    st.write(f"• **Cargas de celular**: {carbon_data['smartphone_charges_avoided_per_year']:,.0f} cargas de batería")

                    if 'lifetime_co2_avoided_tons' in carbon_data:
                        st.markdown("**Impacto a Largo Plazo:**")
                        st.write(f"• **CO2 total evitado**: {carbon_data['lifetime_co2_avoided_tons']:.1f} toneladas en {life} años")
                        st.write(f"• **Valor total carbono**: ${carbon_data['lifetime_certification_value_cop']:,.0f} COP")

            # Análisis de Sensibilidad
            st.write(f"🔧 Debug - Verificando toggle: {incluir_analisis_sensibilidad}")
            if incluir_analisis_sensibilidad:
                st.header("📊 Análisis de Sensibilidad")
                st.info("🔍 **Análisis comparativo** de TIR a 10 y 20 años con y sin financiación para evaluar la robustez del proyecto")
                
                with st.spinner("Calculando análisis de sensibilidad..."):
                    # Calcular análisis de sensibilidad
                    analisis_sensibilidad = calcular_analisis_sensibilidad(
                        Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100, 
                        costkWh, module, ciudad=ciudad_para_calculo, hsp_lista=hsp_a_usar,
                        incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                        profundidad_descarga=profundidad_descarga / 100, eficiencia_bateria=eficiencia_bateria / 100, 
                        dias_autonomia=dias_autonomia, perc_financiamiento=perc_financiamiento, 
                        tasa_interes_credito=tasa_interes_input / 100, plazo_credito_años=plazo_credito_años,
                        precio_manual=precio_manual_valor, horizonte_base=horizonte_tiempo
                    )
                
                # Crear tabla comparativa
                st.subheader("📈 Comparativa de Escenarios")
                
                # Preparar datos para la tabla
                datos_tabla = []
                for escenario, datos in analisis_sensibilidad.items():
                    datos_tabla.append({
                        "Escenario": escenario,
                        "TIR": f"{datos['tir']:.1%}" if datos['tir'] is not None else "N/A",
                        "VPN (COP)": f"${datos['vpn']:,.0f}" if datos['vpn'] is not None else "N/A",
                        "Payback (años)": f"{datos['payback']:.2f}" if datos['payback'] is not None else "N/A",
                        "Desembolso Inicial": f"${datos['desembolso_inicial']:,.0f}",
                        "Cuota Mensual": f"${datos['cuota_mensual']:,.0f}" if datos['cuota_mensual'] > 0 else "N/A"
                    })
                
                # Mostrar tabla
                df_sensibilidad = pd.DataFrame(datos_tabla)
                st.dataframe(df_sensibilidad, use_container_width=True)
                
                # Análisis de conclusiones
                st.subheader("💡 Conclusiones del Análisis")
                
                # Encontrar mejores escenarios
                mejor_tir_10 = max([(k, v['tir']) for k, v in analisis_sensibilidad.items() if '10 años' in k and v['tir'] is not None], key=lambda x: x[1], default=(None, 0))
                mejor_tir_20 = max([(k, v['tir']) for k, v in analisis_sensibilidad.items() if '20 años' in k and v['tir'] is not None], key=lambda x: x[1], default=(None, 0))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Mejor TIR a 10 años", f"{mejor_tir_10[1]:.1%}" if mejor_tir_10[0] else "N/A", 
                             help=f"Escenario: {mejor_tir_10[0]}" if mejor_tir_10[0] else "")
                
                with col2:
                    st.metric("Mejor TIR a 20 años", f"{mejor_tir_20[1]:.1%}" if mejor_tir_20[0] else "N/A",
                             help=f"Escenario: {mejor_tir_20[0]}" if mejor_tir_20[0] else "")
                
                # Recomendaciones
                st.info("""
                **📋 Recomendaciones:**
                - **TIR más alta**: Indica mayor rentabilidad del proyecto
                - **Payback más bajo**: Indica recuperación más rápida de la inversión
                - **Con financiación**: Reduce desembolso inicial pero puede afectar TIR
                - **Sin financiación**: Mayor desembolso inicial pero potencialmente mejor TIR
                """)

            with st.expander("📊 Ver Análisis Financiero Interno (Presupuesto Guía)"):
                st.subheader("Desglose Basado en Promedios Históricos")
                presupuesto_equipos = valor_proyecto_total * (PROMEDIOS_COSTO['Equipos'] / 100)
                presupuesto_materiales = valor_proyecto_total * (PROMEDIOS_COSTO['Materiales'] / 100)
                provision_iva_guia = valor_proyecto_total * (PROMEDIOS_COSTO['IVA (Impuestos)'] / 100)
                ganancia_estimada_guia = valor_proyecto_total * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
                st.info(f"""Basado en el **Valor Total del Proyecto de ${valor_proyecto_total:,.0f} COP**, el presupuesto guía según tu historial es:""")
                col_guia1, col_guia2, col_guia3, col_guia4 = st.columns(4)
                col_guia1.metric(f"Equipos ({PROMEDIOS_COSTO['Equipos']:.2f}%)", f"${math.ceil(presupuesto_equipos):,.0f}")
                col_guia2.metric(f"Materiales ({PROMEDIOS_COSTO['Materiales']:.2f}%)", f"${math.ceil(presupuesto_materiales):,.0f}")
                col_guia3.metric(f"Provisión IVA ({PROMEDIOS_COSTO['IVA (Impuestos)']:.2f}%)", f"${math.ceil(provision_iva_guia):,.0f}")
                col_guia4.metric(f"Ganancia Estimada ({PROMEDIOS_COSTO['Margen (Ganancia)']:.2f}%)", f"${math.ceil(ganancia_estimada_guia):,.0f}")
                st.warning("Nota: Esta sección es una guía interna y no se incluirá en el reporte PDF del cliente.")

            with st.expander("📋 Ver Lista de Materiales (Referencia Interna)"):
                st.subheader("Materiales de Montaje Estimados")
                lista_materiales = calcular_lista_materiales(cantidad_calc, cubierta, module, recomendacion_inversor)
                if lista_materiales:
                    df_materiales = pd.DataFrame(lista_materiales.items(), columns=['Material', 'Cantidad Estimada'])
                    df_materiales.index = df_materiales.index + 1
                    st.table(df_materiales)
                else:
                    st.write("No se calcularon materiales (cantidad de paneles es cero).")
                st.warning("Nota: Esta es una lista de referencia y no incluye todos los componentes.")
        
            st.header("Análisis Gráfico")
            
            lat, lon = None, None
            if st.session_state.map_state["marker"]:
                lat, lon = st.session_state.map_state["marker"]
                api_key = os.environ.get("Maps_API_KEY") 
                if api_key and gmaps:
                    with st.spinner("Generando imagen del mapa..."):
                        get_static_map_image(lat, lon, api_key)

            # --- CÓDIGO DEL GRÁFICO 1 (GENERACIÓN VS CONSUMO) ---
            fig1, ax1 = plt.subplots(figsize=(10, 5))
            meses_grafico = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

            if incluir_baterias:
                # --- LÓGICA PARA GRÁFICA OFF-GRID (CON BATERÍAS) ---
                st.subheader("Flujo de Energía Mensual (Off-Grid)")
                generacion_autoconsumida = []
                energia_a_bateria = []
                
                for gen_mes in monthly_generation:
                    # Lo que se consume directamente es el mínimo entre lo que se genera y lo que se necesita
                    autoconsumo_mes = min(gen_mes, Load)
                    # Lo que va a la batería es todo el excedente
                    bateria_mes = max(0, gen_mes - autoconsumo_mes)
                    
                    generacion_autoconsumida.append(autoconsumo_mes)
                    energia_a_bateria.append(bateria_mes)

                ax1.bar(meses_grafico, generacion_autoconsumida, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
                ax1.bar(meses_grafico, energia_a_bateria, bottom=generacion_autoconsumida, color='green', edgecolor='black', label='Energía Almacenada en Batería', width=0.7)
                ax1.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
                ax1.set_ylabel("Energía (kWh)", fontweight="bold")
                ax1.set_title("Flujo de Energía Mensual Estimado (Off-Grid)", fontweight="bold")
                ax1.legend()

            else:
                # --- LÓGICA PARA GRÁFICA ON-GRID (SIN BATERÍAS) ---
                st.subheader("Generación Vs. Consumo Mensual (On-Grid)")
                generacion_autoconsumida_on, excedentes_vendidos, importado_de_la_red = [], [], []
                for gen_mes in monthly_generation:
                    if gen_mes >= Load:
                        generacion_autoconsumida_on.append(Load); excedentes_vendidos.append(gen_mes - Load); importado_de_la_red.append(0)
                    else:
                        generacion_autoconsumida_on.append(gen_mes); excedentes_vendidos.append(0); importado_de_la_red.append(Load - gen_mes)
                
                ax1.bar(meses_grafico, generacion_autoconsumida_on, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
                ax1.bar(meses_grafico, excedentes_vendidos, bottom=generacion_autoconsumida_on, color='red', edgecolor='black', label='Excedentes Vendidos', width=0.7)
                ax1.bar(meses_grafico, importado_de_la_red, bottom=generacion_autoconsumida_on, color='#2ECC71', edgecolor='black', label='Importado de la Red', width=0.7)
                ax1.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
                ax1.set_ylabel("Energía (kWh)", fontweight="bold")
                ax1.set_title("Generación Vs. Consumo Mensual (On-Grid)", fontweight="bold")
                ax1.legend()

            st.pyplot(fig1)

            fig2, ax2 = plt.subplots(figsize=(10, 5))
            fcl_acumulado = np.cumsum(fcl)
            años = np.arange(0, life + 1)
            ax2.plot(años, fcl_acumulado, marker='o', linestyle='-', color='green', label='Flujo de Caja Acumulado')
            ax2.plot(0, fcl_acumulado[0], marker='X', markersize=10, color='red', label='Desembolso Inicial (Año 0)')
            if payback_exacto is not None: ax2.axvline(x=payback_exacto, color='red', linestyle='--', label=f'Payback Simple: {payback_exacto:.2f} años')
            ax2.axhline(0, color='grey', linestyle='--', linewidth=0.8)
            ax2.set_ylabel("Flujo de Caja Acumulado (COP)", fontweight="bold"); ax2.set_xlabel("Año", fontweight="bold")
            ax2.set_title("Flujo de Caja Acumulado y Período de Retorno", fontweight="bold"); ax2.legend()
            st.pyplot(fig2)
            
            fig1.savefig('grafica_generacion.png', bbox_inches='tight')
            fig2.savefig('grafica_flujo_caja.png', bbox_inches='tight')

            presupuesto_equipos = valor_proyecto_total * (PROMEDIOS_COSTO['Equipos'] / 100)
            presupuesto_materiales = valor_proyecto_total * (PROMEDIOS_COSTO['Materiales'] / 100)
            provision_iva_guia = valor_proyecto_total * (PROMEDIOS_COSTO['IVA (Impuestos)'] / 100)
            ganancia_estimada_guia = valor_proyecto_total * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
            valor_total_redondeado = math.ceil(valor_proyecto_total / 100) * 100
            valor_iva_redondeado = math.ceil(provision_iva_guia / 100) * 100
            valor_sistema_sin_iva_redondeado = valor_total_redondeado - valor_iva_redondeado

            datos_para_pdf = {
                "Nombre del Proyecto": nombre_proyecto, "Cliente": nombre_cliente,
                "Valor Total del Proyecto (COP)": f"${valor_total_redondeado:,.0f}",
                "Valor Sistema FV (sin IVA)": f"${valor_sistema_sin_iva_redondeado:,.0f}",
                "Valor IVA": f"${valor_iva_redondeado:,.0f}",
                "Tamano del Sistema (kWp)": f"{size}",
                "Cantidad de Paneles": f"{int(quantity)} de {int(module)}W","Área Requerida Aprox. (m²)": f"{area_requerida}",
                "Inversor Recomendado": f"{recomendacion_inversor}",
                "Generacion Promedio Mensual (kWh)": f"{generacion_promedio_mensual:,.1f}",
                "Ahorro Estimado Primer Ano (COP)": f"{ahorro_año1:,.2f}",
                "TIR (Tasa Interna de Retorno)": f"{tasa_interna:.1%}",
                "VPN (Valor Presente Neto) (COP)": f"{valor_presente:,.2f}",
                "Periodo de Retorno (anos)": f"{payback_exacto:.2f}" if payback_exacto is not None else "N/A",
                "Tipo de Cubierta": cubierta,
                "Potencia de Paneles": f"{int(module)}",
                "Potencia AC Inversor": f"{potencia_ac_inversor}",
            }
            if usa_financiamiento:
                monto_a_financiar_redondeado = math.ceil(monto_a_financiar / 100) * 100
                desembolso_inicial_redondeado = valor_total_redondeado - monto_a_financiar_redondeado
                
                datos_para_pdf["--- Detalles de Financiamiento ---"] = ""
                datos_para_pdf["Monto a Financiar (COP)"] = f"{monto_a_financiar_redondeado:,.0f}"
                datos_para_pdf["Cuota Mensual del Credito (COP)"] = f"{cuota_mensual_credito:,.0f}"
                datos_para_pdf["Desembolso Inicial (COP)"] = f"{desembolso_inicial_redondeado:,.0f}"
                datos_para_pdf["Plazo del Crédito"] = str(plazo_credito_años * 12)
            
            datos_para_contrato = datos_para_pdf.copy() # Copiamos los datos
            datos_para_contrato['Fecha de la Propuesta'] = fecha_propuesta

            pdf = PropuestaPDF(
                client_name=nombre_cliente, 
                project_name=nombre_proyecto,
                documento=documento_cliente,
                direccion=direccion_proyecto,
                fecha=fecha_propuesta 
            )

            pdf_bytes = pdf.generar(datos_para_pdf, usa_financiamiento, lat, lon)
            nombre_pdf_final = f"{nombre_proyecto}.pdf"
            
            nombre_contrato_final = f"Contrato - {nombre_proyecto}.docx"
            contrato_bytes = generar_contrato_docx(datos_para_contrato)

            if drive_service:
                link_carpeta = gestionar_creacion_drive(
                    drive_service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf_final,contrato_bytes, nombre_contrato_final
                )
                if link_carpeta:
                    st.info(f"➡️ [Abrir carpeta del proyecto en Google Drive]({link_carpeta})")
            
            st.download_button(
                label="📥 Descargar Reporte en PDF (Copia Local)",
                data=pdf_bytes, file_name=nombre_pdf_final,
                mime="application/pdf", use_container_width=True
            )
            if contrato_bytes:
                st.download_button(
                    label="   Descargar Contrato en Word (.docx)",
                    data=contrato_bytes,
                    file_name=nombre_contrato_final,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            st.success('¡Proceso completado!')

            # Notion CRM - agregar a "En conversaciones" (flujo desktop)
            agregado, msg = agregar_cliente_a_notion_crm(
                nombre=nombre_cliente,
                documento=documento_cliente,
                direccion=direccion_proyecto,
                proyecto=nombre_proyecto,
                fecha=fecha_propuesta,
                estado="En conversaciones"
            )
            if agregado:
                st.info("🗂️ Cliente agregado a Notion: En conversaciones")
            else:
                st.caption(f"Notion: {msg}")

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

def main():
    # Configuración básica
    st.set_page_config(
        page_title="Calculadora Solar", 
        layout="wide", 
        initial_sidebar_state="collapsed"
    )
    
    # Mensaje de bienvenida y instrucciones
    if 'first_load' not in st.session_state:
        st.success("🚀 **Calculadora Solar Cargada Correctamente**")
        st.info("""
        **Para cambiar entre modo móvil y desktop:**
        1. 📱 **Abre el sidebar** (menú lateral)
        2. 🔘 **Usa los botones** para cambiar entre modos
        3. 🔄 **Cambio instantáneo** sin recargas
        
        **Modo actual:** Desktop (por defecto)
        """)
        st.session_state.first_load = True
    
    # Inicializar session_state si no existe
    if 'force_mobile' not in st.session_state:
        st.session_state.force_mobile = False
    
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












































































