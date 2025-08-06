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
# ==============================================================================
# CONSTANTES Y DATOS GLOBALES
# ==============================================================================
# Reemplaza el diccionario PROMEDIOS_COSTO en tu app.py con este

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
# FUNCIONES DE CÁLCULO
# ==============================================================================

def recomendar_inversor(size_kwp):
    # (El código de esta función no cambia)
    inverters_disponibles = [3, 5, 6, 8, 10]
    min_ac_power = size_kwp / 1.2
    if size_kwp <= 12:
        for inv_kw in sorted(inverters_disponibles):
            if inv_kw >= min_ac_power: return f"1 inversor de {inv_kw} kW", inv_kw
    recomendacion, potencia_restante = {}, min_ac_power
    for inv_kw in sorted(inverters_disponibles, reverse=True):
        if potencia_restante >= inv_kw:
            num = int(potencia_restante // inv_kw)
            recomendacion[inv_kw] = num; potencia_restante -= num * inv_kw
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

def cotizacion(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module, ciudad=None,
               perc_financiamiento=0, tasa_interes_credito=0, plazo_credito_años=0,
               tasa_degradacion=0, precio_excedentes=0,
               incluir_baterias=False, costo_kwh_bateria=0, 
               profundidad_descarga=0.9, eficiencia_bateria=0.95):
    
    # =====================================================================
    # LÍNEAS DE CÁLCULO DE ÁREA (RESTAURADAS)
    # =====================================================================
    area_por_panel = 2.3 * 1.0  # Dimensiones de 2.3m x 1m
    factor_seguridad = 1.30     # Se añade un 30% para mantenimiento
    area_requerida = math.ceil(quantity * area_por_panel * factor_seguridad)
    # =====================================================================

    HSP = HSP_POR_CIUDAD.get(ciudad.upper(), 4.5)
    n = 0.85
    life = 25
    if clima.strip().upper() == "NUBE": n -= 0.05
    
    recomendacion_inversor_str, potencia_ac_inversor = recomendar_inversor(size)
    potencia_efectiva_calculo = min(size, potencia_ac_inversor)
    
    costo_por_kwp = 7587.7 * size**2 - 346085 * size + 7e6
    valor_proyecto_fv = costo_por_kwp * size
    if cubierta.strip().upper() == "TEJA": valor_proyecto_fv *= 1.03

    costo_bateria = 0
    capacidad_nominal_bateria = 0
    if incluir_baterias:
        consumo_diario = Load / 30
        generacion_diaria_promedio = (potencia_efectiva_calculo * HSP * n * 365 / 12) / 30
        excedente_diario = max(0, generacion_diaria_promedio - consumo_diario)
        capacidad_util_bateria = excedente_diario
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
        cuotas_anuales_credito = 0
        if i < plazo_credito_años: cuotas_anuales_credito = cuota_mensual_credito * 12
        flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
        cashflow_free.append(flujo_anual)
    cashflow_free.insert(0, -desembolso_inicial_cliente)
    present_value = npf.npv(dRate, cashflow_free)
    internal_rate = npf.irr(cashflow_free)
    lcoe = (desembolso_inicial_cliente + npf.npv(dRate, [0.05 * ahorro_anual_total * ((1 + index) ** i) for i in range(life)])) / total_lifetime_generation if total_lifetime_generation > 0 else 0
    trees = round(Load * 12 * 0.154 * 22 / 1000, 0)
    monthly_generation_init = [annual_generation_init * p for p in performance]

    return valor_proyecto_total, size, monto_a_financiar, cuota_mensual_credito, \
           desembolso_inicial_cliente, cashflow_free, trees, monthly_generation_init, \
           present_value, internal_rate, quantity, life, recomendacion_inversor_str, \
           lcoe, n, HSP, potencia_ac_inversor, ahorro_anual_año1, area_requerida, capacidad_nominal_bateria
# ==============================================================================
# CLASE PARA EL REPORTE PDF
# ==============================================================================

class PropuestaPDF(FPDF):
    def __init__(self, client_name="Cliente", project_name="Proyecto", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_name = client_name
        self.project_name = project_name

    def header(self): pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Copyright © 2024 Mirac - All Rights Reserved.', 0, 0, 'C')
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

    def crear_portada(self):
        self.add_page()
        self.set_font('Arial', 'B', 24)
        self.cell(0, 100, '', 0, 1)
        self.cell(0, 10, 'Propuesta Comercial Detallada', 0, 1, 'C')
        self.ln(20)
        self.set_font('Arial', 'I', 16)
        self.cell(0, 10, f'Para: {self.client_name}', 0, 1, 'C')
        self.cell(0, 10, f'Proyecto: {self.project_name}', 0, 1, 'C')

    def crear_resumen_ejecutivo(self, datos):
        self.add_page()
        self.set_font('Arial', 'B', 24)
        self.cell(0, 10, 'Resumen Ejecutivo', 0, 1, 'C')
        self.ln(10)
        self.set_font('Arial', '', 12)
        for key, value in datos.items():
            self.cell(0, 8, f"{key}: {value}", 0, 1)

    def crear_detalle_sistema(self):
        self.add_page()
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Detalles del Sistema y Gráficas', 0, 1, 'L')
        self.ln(5)
        self.image('grafica_generacion.png', w=180)
        self.ln(5)
        self.image('grafica_flujo_caja.png', w=180)

    def generar(self, datos_calculadora):
        self.crear_portada()
        self.crear_resumen_ejecutivo(datos_calculadora)
        self.crear_detalle_sistema()
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

def gestionar_creacion_drive(service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf):
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
        return folder.get('webViewLink')
    except Exception as e:
        st.error(f"Error en el proceso de Google Drive: {e}")
        return None
# Reemplaza esta función en tu app.py

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
# ==============================================================================
# INTERFAZ Y LÓGICA PRINCIPAL DE LA APLICACIÓN
# ==============================================================================

def main():
    st.set_page_config(page_title="Calculadora Solar", layout="wide", initial_sidebar_state="expanded")
    st.title("☀️ Calculadora y Cotizador Solar Profesional")

    drive_service = None
    numero_proyecto_del_año = 1
    try:
        creds = Credentials(
            None, refresh_token=st.secrets["GOOGLE_REFRESH_TOKEN"],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=st.secrets["GOOGLE_CLIENT_ID"], client_secret=st.secrets["GOOGLE_CLIENT_SECRET"],
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=creds)
        parent_folder_id = st.secrets["PARENT_FOLDER_ID"]
        numero_proyecto_del_año = obtener_siguiente_consecutivo(drive_service, parent_folder_id)
    except Exception:
        st.warning("Secretos de Google Drive no configurados. La creación de carpetas está desactivada.")

    with st.sidebar:
        st.header("Parámetros de Entrada")
        st.subheader("Información del Proyecto")
        nombre_cliente = st.text_input("Nombre del Cliente", "Andres Pinzón")
        ubicacion = st.text_input("Ubicación (Opcional)", "Villa Roca 1")
        st.text_input("Número de Proyecto del Año (Automático)", value=numero_proyecto_del_año, disabled=True)
        
        opcion = st.radio("Método para dimensionar:", ["Por Consumo Mensual (kWh)", "Por Cantidad de Paneles"], horizontal=True)

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
        ciudad_input = st.selectbox("Ciudad", list(HSP_POR_CIUDAD.keys()))
        cubierta = st.selectbox("Tipo de cubierta", ["LÁMINA", "TEJA"])
        clima = st.selectbox("Clima predominante", ["SOL", "NUBE"])

        st.subheader("Parámetros Financieros")
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
            
        st.subheader("Almacenamiento (Baterías)")
        incluir_baterias = st.toggle("Añadir baterías al sistema")
        
        costo_kwh_bateria = 0
        profundidad_descarga = 90.0
        eficiencia_bateria = 95.0

        if incluir_baterias:
            costo_kwh_bateria = st.number_input("Costo por kWh de batería (COP)", min_value=100000, value=2500000, step=100000)
            profundidad_descarga = st.slider("Profundidad de Descarga (DoD) permitida (%)", 50.0, 100.0, 90.0, 0.5)
            eficiencia_bateria = st.slider("Eficiencia de Carga/Descarga (%)", 80.0, 100.0, 95.0, 0.5)


    if st.button("📊 Calcular y Generar Reporte", use_container_width=True):
        with st.spinner('Realizando cálculos y creando archivos... ⏳'):
            año_actual = str(datetime.datetime.now().year)[-2:]
            numero_formateado = f"{numero_proyecto_del_año:03d}"
            codigo_proyecto = f"FV{año_actual}{numero_formateado}"
            nombre_proyecto = f"{codigo_proyecto} - {nombre_cliente}" + (f" - {ubicacion}" if ubicacion else "")
            st.success(f"Proyecto Generado: {nombre_proyecto}")

            valor_proyecto_total, size_calc, monto_a_financiar, cuota_mensual_credito, \
            desembolso_inicial_cliente, fcl, trees, monthly_generation, valor_presente, \
            tasa_interna, cantidad_calc, life, recomendacion_inversor, lcoe, n_final, HSP_final, \
            potencia_ac_inversor, ahorro_año1, area_requerida, capacidad_bateria_kwh = \
                cotizacion(Load, size, quantity, cubierta, clima, index_input / 100, dRate_input / 100, costkWh, module, 
                           ciudad=ciudad_input, perc_financiamiento=perc_financiamiento, 
                           tasa_interes_credito=tasa_interes_input / 100, plazo_credito_años=plazo_credito_años, 
                           tasa_degradacion=0.001, precio_excedentes=300.0,
                           # Nuevos argumentos que se pasan a la función:
                           incluir_baterias=incluir_baterias, costo_kwh_bateria=costo_kwh_bateria,
                           profundidad_descarga=profundidad_descarga / 100,
                           eficiencia_bateria=eficiencia_bateria / 100)
            
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
            if incluir_baterias:
                col4.metric("Batería Recomendada", f"{capacidad_bateria_kwh:.1f} kWh")
            # --- SECCIÓN DE ANÁLISIS FINANCIERO INTERNO (DETALLADO Y REDONDEADO) ---
            with st.expander("📊 Ver Análisis Financiero Interno (Presupuesto Guía)"):
                st.subheader("Desglose Basado en Promedios Históricos")
                
                # Usamos los promedios para calcular el presupuesto guía detallado
                presupuesto_equipos = valor_proyecto_total * (PROMEDIOS_COSTO['Equipos'] / 100)
                presupuesto_materiales = valor_proyecto_total * (PROMEDIOS_COSTO['Materiales'] / 100)
                provision_iva_guia = valor_proyecto_total * (PROMEDIOS_COSTO['IVA (Impuestos)'] / 100)
                ganancia_estimada_guia = valor_proyecto_total * (PROMEDIOS_COSTO['Margen (Ganancia)'] / 100)
                
                st.info(f"""
                Basado en el **Valor Total del Proyecto de ${valor_proyecto_total:,.0f} COP**, el presupuesto guía según tu historial es:
                """)

                col_guia1, col_guia2, col_guia3, col_guia4 = st.columns(4)
                col_guia1.metric(
                    label=f"Equipos ({PROMEDIOS_COSTO['Equipos']:.2f}%)",
                    value=f"${math.ceil(presupuesto_equipos):,.0f}"
                )
                col_guia2.metric(
                    label=f"Materiales ({PROMEDIOS_COSTO['Materiales']:.2f}%)",
                    value=f"${math.ceil(presupuesto_materiales):,.0f}"
                )
                col_guia3.metric(
                    label=f"Provisión IVA ({PROMEDIOS_COSTO['IVA (Impuestos)']:.2f}%)",
                    value=f"${math.ceil(provision_iva_guia):,.0f}"
                )
                col_guia4.metric(
                    label=f"Ganancia Estimada ({PROMEDIOS_COSTO['Margen (Ganancia)']:.2f}%)",
                    value=f"${math.ceil(ganancia_estimada_guia):,.0f}"
                )
               
                
                st.warning("Nota: Esta sección es una guía interna y no se incluirá en el reporte PDF del cliente.")
            with st.expander("📋 Ver Lista de Materiales (Referencia Interna)"):
                st.subheader("Materiales de Montaje Estimados")

                # Llamamos a la nueva función con los resultados del cálculo
                lista_materiales = calcular_lista_materiales(cantidad_calc, cubierta, module, recomendacion_inversor)
                
                if lista_materiales:
                    # Convertimos el diccionario a un formato más legible para la tabla
                    df_materiales = pd.DataFrame(lista_materiales.items(), columns=['Material', 'Cantidad Estimada'])
                    df_materiales.index = df_materiales.index + 1
                    st.table(df_materiales)
                else:
                    st.write("No se calcularon materiales (cantidad de paneles es cero).")
                
                st.warning("Nota: Esta es una lista de referencia para montaje y no incluye todos los componentes eléctricos. Las cantidades incluyen un pequeño margen de emergencia.")


            
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
            ax1.set_ylabel("Energía (kWh)", fontweight="bold"); ax1.set_title("Generación Vs. Consumo Mensual (Año 1)", fontweight="bold"); ax1.legend()
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
            
            datos_para_pdf = {
                "Nombre del Proyecto": nombre_proyecto, "Cliente": nombre_cliente,
                "Valor Total del Proyecto (COP)": f"{valor_proyecto_total:,.2f}",
                "Tamano del Sistema (kWp)": f"{size}",
                "Cantidad de Paneles": f"{int(quantity)} de {int(module)}W","Área Requerida Aprox. (m²)": f"{area_requerida}",
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
            
            pdf = PropuestaPDF(client_name=nombre_cliente, project_name=nombre_proyecto)
            pdf_bytes = pdf.generar(datos_para_pdf)
            nombre_pdf_final = f"{nombre_proyecto}.pdf"

            if drive_service:
                link_carpeta = gestionar_creacion_drive(
                    drive_service, parent_folder_id, nombre_proyecto, pdf_bytes, nombre_pdf_final
                )
                if link_carpeta:
                    st.info(f"➡️ [Abrir carpeta del proyecto en Google Drive]({link_carpeta})")
            
            st.download_button(
                label="📥 Descargar Reporte en PDF (Copia Local)",
                data=pdf_bytes, file_name=nombre_pdf_final,
                mime="application/pdf", use_container_width=True
            )
            st.success('¡Proceso completado!')

if __name__ == '__main__':
    main()



























