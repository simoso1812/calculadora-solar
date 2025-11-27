"""
Servicio de cálculos financieros y técnicos para sistemas solares.
"""
import math
import io
import pandas as pd
import numpy_financial as npf
import numpy as np
import streamlit as st
from src.config import HSP_MENSUAL_POR_CIUDAD, PROMEDIOS_COSTO

try:
    from carbon_calculator import CarbonEmissionsCalculator
    carbon_calculator = CarbonEmissionsCalculator()
except ImportError:
    carbon_calculator = None

def calcular_costo_por_kwp(size_kwp):
    """
    Calcula el costo por kWp según el tamaño del proyecto.
    - Para proyectos < 20 kW: usa función potencia optimizada basada en 42 datos (26 reales + 16 teóricos)
    - Para proyectos >= 20 kW: usa polinomial grado 3 optimizada basada en 38 proyectos
    """
    if size_kwp < 20:
        # Función potencia optimizada: a * size^b
        # Basada en regresión de 42 datos (26 proyectos reales + 16 calculados)
        # R² = 0.8693, MAE = $426,945/kWp, Error promedio: 7.87% con datos reales
        # Actualizada: 2025-01-27
        costo_por_kwp = 11917544 * (size_kwp ** -0.484721)
    else:
        # Polinomial grado 3 optimizada: ax³ + bx² + cx + d
        # Basada en regresión de 38 proyectos (R² = 0.9892, MAE = $11,210/kWp)
        # Error promedio: 0.41%
        # Actualizada: 2025-01-27
        costo_por_kwp = -0.265979 * size_kwp**3 + 103.58 * size_kwp**2 - 14285.52 * size_kwp + 3286846.42
    
    return costo_por_kwp

def redondear_a_par(numero):
    """
    Redondea un número al entero par más cercano (hacia arriba si es necesario).
    Siempre retorna un número par.
    """
    numero_int = int(round(numero))
    if numero_int % 2 == 0:
        return numero_int
    else:
        return numero_int + 1

def calcular_margen_inversor(size_kwp):
    """
    Calcula el margen aceptable para el inversor basado en el tamaño del sistema.
    Sistemas más grandes permiten mayor margen (menor relación inversor/DC).
    
    Args:
        size_kwp: Tamaño del sistema en kWp
        
    Returns:
        float: Margen máximo permitido (0.2 a 0.35)
    """
    if size_kwp < 20:
        return 0.2  # 20% margin (80% minimum)
    elif size_kwp < 50:
        return 0.25  # 25% margin (75% minimum)
    elif size_kwp < 100:
        return 0.30  # 30% margin (70% minimum)
    else:
        return 0.35  # 35% margin (65% minimum) for very large systems

def recomendar_inversor(size_kwp):
    """
    Recomienda la combinación de inversores ÓPTIMA para maximizar la potencia AC,
    respetando las reglas de diseño para diferentes tamaños de sistema.
    """
    inverters_disponibles = [3, 5, 6, 8, 10, 20, 30, 40, 50, 100]
    
    if size_kwp <= 0:
        return "Potencia del sistema no válida.", 0
    
    margen = calcular_margen_inversor(size_kwp)
    min_power = size_kwp * (1 - margen)
    max_power = int(math.floor(size_kwp))
    
    if max_power <= 0:
        return "Potencia del sistema demasiado baja para recomendar inversor.", 0

    best_combo_details = {'combo': None, 'total_power': 0}

    # 1. Evaluar inversores únicos
    for inv in inverters_disponibles:
        if min_power <= inv <= max_power:
            if inv > best_combo_details['total_power']:
                best_combo_details['combo'] = {inv: 1}
                best_combo_details['total_power'] = inv

    # 2. Evaluar combinaciones según el tamaño del sistema
    if size_kwp < 20:
        # Lógica de programación dinámica para sistemas pequeños
        disponibles = [inv for inv in inverters_disponibles if inv <= max_power]
        if disponibles:
            dp = {0: {}}
            for inv in disponibles:
                for total, combo in list(dp.items()):
                    new_total = total + inv
                    if new_total <= max_power:
                        if new_total not in dp or sum(dp[new_total].values()) > sum(combo.values()) + 1:
                            new_combo = combo.copy()
                            new_combo[inv] = new_combo.get(inv, 0) + 1
                            dp[new_total] = new_combo
            
            # Buscar la mejor combinación en DP que cumpla el margen
            for total in range(max_power, int(min_power) - 1, -1):
                if total in dp and total > best_combo_details['total_power']:
                    best_combo_details['combo'] = dp[total]
                    best_combo_details['total_power'] = total
                    break # Encontramos la mejor posible
    
    elif size_kwp < 100:
        # Lógica para sistemas medianos (máx 2 inversores >= 20kW)
        disponibles = [inv for inv in inverters_disponibles if inv >= 20 and inv <= max_power]
        for i, inv1 in enumerate(disponibles):
            for inv2 in disponibles[i:]:
                total = inv1 + inv2
                if min_power <= total <= max_power and total > best_combo_details['total_power']:
                    best_combo_details['total_power'] = total
                    best_combo_details['combo'] = {inv1: 0, inv2: 0}
                    best_combo_details['combo'][inv1] += 1
                    best_combo_details['combo'][inv2] += 1

    else: # size_kwp >= 100
        # Lógica para sistemas grandes (máx 3 inversores, secundarios >= 25% del total)
        min_secondary = max(20, size_kwp * 0.25)
        disponibles = [inv for inv in inverters_disponibles if inv >= min_secondary and inv <= max_power]
        
        # Combinaciones de 2
        for i, inv1 in enumerate(disponibles):
            for inv2 in disponibles[i:]:
                total = inv1 + inv2
                if min_power <= total <= max_power and total > best_combo_details['total_power']:
                    best_combo_details['total_power'] = total
                    best_combo_details['combo'] = {inv1: 0, inv2: 0}
                    best_combo_details['combo'][inv1] += 1
                    best_combo_details['combo'][inv2] += 1

        # Combinaciones de 3
        for i, inv1 in enumerate(disponibles):
            for j, inv2 in enumerate(disponibles[i:]):
                for inv3 in disponibles[j:]:
                    total = inv1 + inv2 + inv3
                    if min_power <= total <= max_power and total > best_combo_details['total_power']:
                        best_combo_details['total_power'] = total
                        best_combo_details['combo'] = {inv1: 0, inv2: 0, inv3: 0}
                        best_combo_details['combo'][inv1] += 1
                        best_combo_details['combo'][inv2] += 1
                        best_combo_details['combo'][inv3] += 1

    # 3. Formatear y devolver la mejor opción encontrada
    if not best_combo_details['combo']:
        # Fallback si no se encontró ninguna combinación adecuada
        disponibles = [inv for inv in inverters_disponibles if inv <= max_power]
        if not disponibles:
            return "No hay inversores disponibles.", 0
        
        # Devolver el inversor individual más grande posible como último recurso
        best_single = max(disponibles)
        return f"1x{int(best_single)}kW", best_single

    partes = []
    # Ordenar por tamaño de inversor para un formato consistente
    for kw, count in sorted(best_combo_details['combo'].items(), reverse=True):
        if count > 0:
            partes.append(f"{count}x{int(kw)}kW")
            
    return " + ".join(partes), best_combo_details['total_power']

def calcular_performance_ratio(clima, cubierta):
    """
    Calcula el Performance Ratio (PR) del sistema basado en el clima y tipo de cubierta.
    """
    PR_BASE = 0.75  # Nuevo PR base más conservador (antes 0.85)

    # Ajuste por clima
    clima_upper = clima.strip().upper()
    if clima_upper == "NUBE":
        PR_BASE -= 0.05  # -5% por clima nublado
    elif clima_upper == "SOL":
        PR_BASE -= 0.02  # -2% por calor excesivo

    # Ajuste por tipo de cubierta
    cubierta_upper = cubierta.strip().upper()
    if cubierta_upper == "TEJA":
        PR_BASE -= 0.01  # -1% por complejidad de teja

    return round(PR_BASE, 3)

def calcular_factor_clipping(dc_ac_ratio):
    """
    Estima el porcentaje de pérdida de energía anual debido al clipping
    basado en el DC/AC ratio. Es una aproximación empírica.
    """
    if dc_ac_ratio <= 1.05:
        return 0.0  # Pérdida insignificante
    elif dc_ac_ratio <= 1.15:
        return 0.005 # 0.5% de pérdida
    elif dc_ac_ratio <= 1.25:
        return 0.015 # 1.5% de pérdida
    elif dc_ac_ratio <= 1.35:
        return 0.03  # 3.0% de pérdida
    else:
        return 0.05  # >35% de sobrecarga, cap a 5% de pérdida

def generar_csv_flujo_caja_detallado(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
                                      ciudad=None, hsp_lista=None, perc_financiamiento=0, tasa_interes_credito=0,
                                      plazo_credito_años=0, incluir_baterias=False, costo_kwh_bateria=0,
                                      profundidad_descarga=0.9, eficiencia_bateria=0.95, dias_autonomia=2,
                                      horizonte_tiempo=25, precio_manual=None, fcl=None, monthly_generation=None,
                                      incluir_beneficios_tributarios=False, incluir_deduccion_renta=False,
                                      incluir_depreciacion_acelerada=False):
    """
    Genera CSV super detallado del flujo de caja con métricas financieras y técnicas completas
    """
    import io

    # Configuración inicial
    hsp_mensual = hsp_lista if hsp_lista is not None else HSP_MENSUAL_POR_CIUDAD.get(ciudad.upper(), HSP_MENSUAL_POR_CIUDAD["MEDELLIN"])
    n = 0.8
    life = horizonte_tiempo
    if clima.strip().upper() == "NUBE": n -= 0.05

    recomendacion_inversor_str, potencia_ac_inversor = recomendar_inversor(size)
    potencia_efectiva_calculo = min(size, potencia_ac_inversor)

    # Costos del proyecto
    costo_por_kwp = calcular_costo_por_kwp(size)
    valor_proyecto_fv = costo_por_kwp * size
    if cubierta.strip().upper() == "TEJA": valor_proyecto_fv *= 1.03

    costo_bateria = 0
    if incluir_baterias:
        consumo_diario = Load / 30
        capacidad_util_bateria = consumo_diario * dias_autonomia
        capacidad_nominal_bateria = capacidad_util_bateria / profundidad_descarga
        costo_bateria = capacidad_nominal_bateria * costo_kwh_bateria

    valor_proyecto_total = valor_proyecto_fv + costo_bateria
    valor_proyecto_total = math.ceil(valor_proyecto_total)

    # Aplicar precio manual si existe
    if precio_manual:
        valor_proyecto_total = precio_manual

    # Financiamiento
    monto_a_financiar = valor_proyecto_total * (perc_financiamiento / 100)
    monto_a_financiar = math.ceil(monto_a_financiar)

    cuota_mensual_credito = 0
    if monto_a_financiar > 0 and plazo_credito_años > 0 and tasa_interes_credito > 0:
        tasa_mensual_credito = tasa_interes_credito / 12
        num_pagos_credito = plazo_credito_años * 12
        cuota_mensual_credito = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_a_financiar))
        cuota_mensual_credito = math.ceil(cuota_mensual_credito)

    desembolso_inicial_cliente = valor_proyecto_total - monto_a_financiar

    # Generación mensual base
    dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthly_generation_init = [potencia_efectiva_calculo * hsp * dias * n for hsp, dias in zip(hsp_mensual, dias_por_mes)]

    # Si no se pasaron fcl y monthly_generation, calcularlos
    if fcl is None or monthly_generation is None:
        # Calcular flujo de caja básico
        cashflow_free = []
        for i in range(life):
            current_monthly_generation = [gen * ((1 - 0.001) ** i) for gen in monthly_generation_init]

            ahorro_anual_total = 0
            if incluir_baterias:
                ahorro_anual_total = (Load * 12) * costkWh
            else:  # Lógica On-Grid
                for gen_mes in current_monthly_generation:
                    consumo_mes = Load
                    if gen_mes >= consumo_mes:
                        ahorro_mes = (consumo_mes * costkWh) + ((gen_mes - consumo_mes) * 300.0)
                    else:
                        ahorro_mes = gen_mes * costkWh
                    ahorro_anual_total += ahorro_mes

            ahorro_anual_indexado = ahorro_anual_total * ((1 + index) ** i)
            mantenimiento_anual = 0.05 * ahorro_anual_indexado
            cuotas_anuales_credito = 0
            if i < plazo_credito_años:
                cuotas_anuales_credito = cuota_mensual_credito * 12
            flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito
            cashflow_free.append(flujo_anual)

        cashflow_free.insert(0, -desembolso_inicial_cliente)
        fcl = cashflow_free
        monthly_generation = monthly_generation_init

    # Calcular flujo de caja detallado
    data_rows = []
    flujos_acumulados = []

    # Año 0: Inversión inicial
    data_rows.append({
        'Año': 0,
        'Inversión_Inicial_COP': desembolso_inicial_cliente,
        'Generación_Anual_kWh': 0,
        'Consumo_Anual_kWh': 0,
        'Excedentes_Vendidos_kWh': 0,
        'Cobertura_Consumo_Porc': 0,
        'Costo_Energia_Indexado_COP_kWh': 0,
        'Ahorro_Anual_COP': 0,
        'Ingresos_Excedentes_COP': 0,
        'Mantenimiento_COP': 0,
        'Cuotas_Credito_COP': 0,
        'Flujo_Neto_Anual_COP': -desembolso_inicial_cliente,
        'Flujo_Acumulado_COP': -desembolso_inicial_cliente,
        'VPN_Parcial_COP': -desembolso_inicial_cliente,
        'TIR_Parcial_Porc': 0,
        'Degradación_Aplicada_Porc': 0
    })

    flujos_acumulados = [-desembolso_inicial_cliente]

    # Años 1-N: Flujos anuales con métricas detalladas
    for i in range(life):
        # Generación del año con degradación
        degradacion_anual = 0.001  # 0.1% por año
        current_monthly_generation = [gen * ((1 - degradacion_anual) ** i) for gen in monthly_generation]
        generacion_anual_total = sum(current_monthly_generation)

        # Consumo y excedentes
        consumo_anual = Load * 12
        excedentes_totales = 0
        ahorro_anual_total = 0
        ingresos_excedentes = 0

        if incluir_baterias:
            # Sistema Off-Grid: todo el consumo se ahorra
            ahorro_anual_total = consumo_anual * costkWh
            cobertura_consumo = 100.0
        else:
            # Sistema On-Grid: cálculo mensual detallado
            for gen_mes in current_monthly_generation:
                consumo_mes = Load
                if gen_mes >= consumo_mes:
                    # Consumo cubierto + excedentes vendidos
                    ahorro_mes = consumo_mes * costkWh
                    excedentes_mes = gen_mes - consumo_mes
                    ingresos_excedentes_mes = excedentes_mes * 300.0  # precio excedentes
                    excedentes_totales += excedentes_mes
                    ingresos_excedentes += ingresos_excedentes_mes
                else:
                    # Consumo parcialmente cubierto
                    ahorro_mes = gen_mes * costkWh
                    excedentes_totales += 0

                ahorro_anual_total += ahorro_mes

            # Calcular cobertura de consumo
            cobertura_consumo = min(100.0, (generacion_anual_total / consumo_anual) * 100) if consumo_anual > 0 else 0

        # Costo de energía indexado
        costo_energia_indexado = costkWh * ((1 + index) ** i)

        # Aplicar indexación al ahorro
        ahorro_anual_indexado = ahorro_anual_total * ((1 + index) ** i)
        ingresos_excedentes_indexados = ingresos_excedentes * ((1 + index) ** i)

        # Mantenimiento
        mantenimiento_anual = 0.05 * ahorro_anual_indexado

        # Cuotas anuales del crédito
        cuotas_anuales_credito = 0
        if i < plazo_credito_años:
            cuotas_anuales_credito = cuota_mensual_credito * 12

        # Beneficios tributarios
        beneficio_tributario_total = 0
        beneficio_deduccion_renta = 0
        beneficio_depreciacion_acelerada = 0

        if incluir_beneficios_tributarios:
            if incluir_deduccion_renta and i == 1:  # Año 2
                # 17.5% del CAPEX indexado al año 2
                capex_indexado_año2 = valor_proyecto_total * ((1 + index) ** i)
                beneficio_deduccion_renta = capex_indexado_año2 * 0.175
                beneficio_tributario_total += beneficio_deduccion_renta

            if incluir_depreciacion_acelerada and i < 3:  # Años 1-3
                # 33% del CAPEX cada año por 3 años
                beneficio_depreciacion_acelerada = valor_proyecto_total * 0.33
                beneficio_tributario_total += beneficio_depreciacion_acelerada

        # Flujo neto del año
        flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito + beneficio_tributario_total
        flujo_acumulado = sum(flujos_acumulados) + flujo_anual
        flujos_acumulados.append(flujo_anual)

        # TIR y VPN parciales hasta este año
        tir_parcial = 0
        vpn_parcial = flujo_acumulado

        if len(flujos_acumulados) > 1:
            try:
                tir_parcial = npf.irr(flujos_acumulados) * 100
                vpn_parcial = npf.npv(dRate, flujos_acumulados)
            except:
                tir_parcial = 0
                vpn_parcial = flujo_acumulado

        data_rows.append({
            'Año': i + 1,
            'Inversión_Inicial_COP': 0,
            'Generación_Anual_kWh': generacion_anual_total,
            'Consumo_Anual_kWh': consumo_anual,
            'Excedentes_Vendidos_kWh': excedentes_totales,
            'Cobertura_Consumo_Porc': cobertura_consumo,
            'Costo_Energia_Indexado_COP_kWh': costo_energia_indexado,
            'Ahorro_Anual_COP': ahorro_anual_indexado,
            'Ingresos_Excedentes_COP': ingresos_excedentes_indexados,
            'Mantenimiento_COP': mantenimiento_anual,
            'Cuotas_Credito_COP': cuotas_anuales_credito,
            'Beneficio_Deduccion_Renta_COP': beneficio_deduccion_renta,
            'Beneficio_Depreciacion_Acelerada_COP': beneficio_depreciacion_acelerada,
            'Beneficio_Tributario_Total_COP': beneficio_tributario_total,
            'Flujo_Neto_Anual_COP': flujo_anual,
            'Flujo_Acumulado_COP': flujo_acumulado,
            'VPN_Parcial_COP': vpn_parcial,
            'TIR_Parcial_Porc': tir_parcial,
            'Degradación_Aplicada_Porc': degradacion_anual * 100
        })

    # Crear DataFrame y CSV
    df = pd.DataFrame(data_rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, float_format='%.2f')
    csv_content = csv_buffer.getvalue()

    return csv_content

def cotizacion(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module, ciudad=None,
                hsp_lista=None,
                perc_financiamiento=0, tasa_interes_credito=0, plazo_credito_años=0,
                tasa_degradacion=0, precio_excedentes=0,
                incluir_baterias=False, costo_kwh_bateria=0,
                profundidad_descarga=0.9, eficiencia_bateria=0.95, dias_autonomia=2,
                horizonte_tiempo=25, incluir_carbon=False,
                incluir_beneficios_tributarios=False, incluir_deduccion_renta=False,
                incluir_depreciacion_acelerada=False, demora_6_meses=False):
    
    # Se asegura de tener la lista de HSP mensuales para el cálculo
    hsp_mensual = hsp_lista if hsp_lista is not None else HSP_MENSUAL_POR_CIUDAD.get(ciudad.upper(), HSP_MENSUAL_POR_CIUDAD["MEDELLIN"])
    
    life = horizonte_tiempo
    n = calcular_performance_ratio(clima, cubierta)
    
    recomendacion_inversor_str, potencia_ac_inversor = recomendar_inversor(size)
    
    # --- Nueva Lógica de Clipping ---
    dc_ac_ratio = size / potencia_ac_inversor if potencia_ac_inversor > 0 else 1.0
    factor_clipping = calcular_factor_clipping(dc_ac_ratio)
    # --- Fin Nueva Lógica ---
    
    area_por_panel = 2.3 * 1.0
    factor_seguridad = 1.30
    area_requerida = math.ceil(quantity * area_por_panel * factor_seguridad)
    
    costo_por_kwp = calcular_costo_por_kwp(size)
    valor_proyecto_fv = costo_por_kwp * size
    if cubierta.strip().upper() == "TEJA": valor_proyecto_fv *= 1.03

    costo_bateria = 0
    capacidad_nominal_bateria = 0
    if incluir_baterias:
        consumo_diario = Load / 30
        capacidad_util_bateria = consumo_diario * dias_autonomia
        if profundidad_descarga > 0 and profundidad_descarga <= 1.0:
            capacidad_nominal_bateria = capacidad_util_bateria / profundidad_descarga
        else:
            # Valor por defecto si profundidad_descarga es inválida
            capacidad_nominal_bateria = capacidad_util_bateria / 0.8  # 80% por defecto
        costo_bateria = capacidad_nominal_bateria * costo_kwh_bateria
    
    valor_proyecto_total = valor_proyecto_fv + costo_bateria
    valor_proyecto_total = math.ceil(valor_proyecto_total)
    
    monto_a_financiar = valor_proyecto_total * (perc_financiamiento / 100)
    monto_a_financiar = math.ceil(monto_a_financiar)
    
    cuota_mensual_credito = 0
    if monto_a_financiar > 0 and plazo_credito_años > 0 and tasa_interes_credito > 0:
        tasa_mensual_credito = tasa_interes_credito / 12
        num_pagos_credito = plazo_credito_años * 12
        try:
            cuota_mensual_credito = abs(npf.pmt(tasa_mensual_credito, num_pagos_credito, -monto_a_financiar))
            cuota_mensual_credito = math.ceil(cuota_mensual_credito)
        except (ValueError, ZeroDivisionError):
            cuota_mensual_credito = 0
        
    desembolso_inicial_cliente = valor_proyecto_total - monto_a_financiar
    
    cashflow_free, total_lifetime_generation, ahorro_anual_año1 = [], 0, 0
    dias_por_mes = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # Se calcula la generación de cada mes individualmente usando los HSP mensuales
    monthly_generation_init = [(size * hsp * dias * n) * (1 - factor_clipping) for hsp, dias in zip(hsp_mensual, dias_por_mes)]
    
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

        # Aplicar demora de 6 meses si está habilitada
        if demora_6_meses and i == 0:  # Solo afecta el año 1
            ahorro_anual_indexado *= 0.5  # 50% para 6 meses de operación

        mantenimiento_anual = 0.05 * ahorro_anual_indexado
        cuotas_anuales_credito = 0
        if i < plazo_credito_años:
            cuotas_anuales_credito = cuota_mensual_credito * 12
        flujo_anual = ahorro_anual_indexado - mantenimiento_anual - cuotas_anuales_credito

        # Aplicar beneficios tributarios (pueden aplicarse ambos simultáneamente)
        beneficio_tributario_total = 0
        if incluir_beneficios_tributarios:
            if incluir_deduccion_renta and i == 1:  # Año 2
                # 17.5% del CAPEX indexado al año 2
                capex_indexado_año2 = valor_proyecto_total * ((1 + index) ** i)
                beneficio_deduccion = capex_indexado_año2 * 0.175
                beneficio_tributario_total += beneficio_deduccion

            if incluir_depreciacion_acelerada and i < 3:  # Años 1-3
                # 33% del CAPEX cada año por 3 años
                beneficio_depreciacion = valor_proyecto_total * 0.33
                beneficio_tributario_total += beneficio_depreciacion

        flujo_anual += beneficio_tributario_total

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

def calcular_analisis_sensibilidad(Load, size, quantity, cubierta, clima, index, dRate, costkWh, module,
                                    ciudad=None, hsp_lista=None, incluir_baterias=False, costo_kwh_bateria=0,
                                    profundidad_descarga=0.9, eficiencia_bateria=0.95, dias_autonomia=2,
                                    perc_financiamiento=0, tasa_interes_credito=0, plazo_credito_años=0,
                                    precio_manual=None, horizonte_base=25, incluir_beneficios_tributarios=False,
                                    incluir_deduccion_renta=False, incluir_depreciacion_acelerada=False):
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
                          incluir_carbon=False, incluir_beneficios_tributarios=incluir_beneficios_tributarios,
                          incluir_deduccion_renta=incluir_deduccion_renta,
                          incluir_depreciacion_acelerada=incluir_depreciacion_acelerada,
                          demora_6_meses=False)  # Disable carbon and tax benefits for sensitivity analysis
            
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
            
            # Recalcular métricas financieras con manejo de errores
            try:
                valor_presente = npf.npv(dRate, fcl)
                if valor_presente is None or np.isnan(valor_presente):
                    valor_presente = 0
            except (ValueError, TypeError):
                valor_presente = 0
                
            try:
                tasa_interna = npf.irr(fcl)
                if tasa_interna is None or np.isnan(tasa_interna):
                    tasa_interna = 0
            except (ValueError, TypeError):
                tasa_interna = 0
            
            # Calcular payback con manejo de errores
            payback_simple = None
            payback_exacto = None
            
            try:
                cumsum_fcl = np.cumsum(fcl)
                payback_simple = next((i for i, x in enumerate(cumsum_fcl) if x >= 0), None)
                
                if payback_simple is not None:
                    if payback_simple > 0 and len(cumsum_fcl) > payback_simple:
                        denominator = cumsum_fcl[payback_simple] - cumsum_fcl[payback_simple-1]
                        if abs(denominator) > 1e-10:  # Evitar división por cero
                            payback_exacto = (payback_simple - 1) + abs(cumsum_fcl[payback_simple-1]) / denominator
                        else:
                            payback_exacto = float(payback_simple)
                    else:
                        payback_exacto = float(payback_simple)
            except (IndexError, ValueError, ZeroDivisionError) as e:
                print(f"Error calculating payback: {e}")
                payback_exacto = None
            
            
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
