"""
Utilidad para generar el PDF de la propuesta solar.
"""
from fpdf import FPDF
import datetime
import os
import math
import re
import streamlit as st

class PropuestaPDF(FPDF):
    BRAND_COLOR = (250, 50, 63)
    TEXT_COLOR = (0, 0, 0)

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

    def _format_currency(self, value):
        """Formatea valores monetarios."""
        def _ceil_to_100(amount: float) -> float:
            # Redondeo comercial hacia arriba a la centena más cercana (COP)
            # Mantiene consistencia entre flujos (desktop/mobile) y evita decimales.
            try:
                return float(math.ceil(amount / 100.0) * 100)
            except Exception:
                return 0.0

        if isinstance(value, (int, float)):
            rounded = _ceil_to_100(float(value))
            return f"$ {rounded:,.0f}"
        if isinstance(value, str):
            value = value.replace('$', '').replace(',', '').strip()
            try:
                val_float = float(value)
                rounded = _ceil_to_100(val_float)
                return f"$ {rounded:,.0f}"
            except ValueError:
                pass
        return "$ 0"

    def _format_number(self, value, decimals=0):
        """Formatea números con decimales opcionales."""
        if isinstance(value, (int, float)):
            val_float = float(value)
        elif isinstance(value, str):
            value = value.replace(',', '').strip()
            try:
                val_float = float(value)
            except ValueError:
                return "0"
        else:
            return "0"
            
        if decimals == 0:
            return f"{val_float:,.0f}"
        return f"{val_float:,.{decimals}f}"

    def header(self): pass
    def footer(self): pass

    def crear_portada(self):
        self.add_page()
        self.image('assets/1.jpg', x=0, y=0, w=210)
        
        self.set_text_color(*self.BRAND_COLOR)
        
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

    def crear_resumen_ejecutivo(self, datos):
        self.add_page()
        self.image('assets/3.jpg', x=0, y=0, w=210)
        self.set_text_color(*self.TEXT_COLOR)
        
        # Definir color amarillo MIRAC
        YELLOW_MIRAC = (250, 193, 7)  # Amarillo similar al de la marca

        # --- 1. Bloque de kWp instalados ---
        kwp_instalados = datos.get('Tamano del Sistema (kWp)', '0')
        kwp_formatted = self._format_number(kwp_instalados, decimals=1)
        
        self.set_font(self.font_family, 'B', 40)
        self.set_xy(36, 60)
        self.set_text_color(*self.TEXT_COLOR)
        
        # Calculate width of number to place 'k' immediately after
        w_num = self.get_string_width(kwp_formatted)
        self.cell(w=w_num + 2, text=kwp_formatted, align='L')
        
        # Agregar "kWp" con la "k" en amarillo y "Wp" en negro
        self.set_text_color(*YELLOW_MIRAC)
        self.cell(w=10, text="k", align='L')
        self.set_text_color(*self.TEXT_COLOR)
        self.cell(w=35, text="Wp", align='L')

        # --- 2. Bloque de Cantidad de Módulos Fotovoltaicos ---
        cantidad_paneles = datos.get('Cantidad de Paneles', '0')
        if ' de ' in cantidad_paneles:
            cantidad_paneles = cantidad_paneles.split(' de ')[0]
        
        cantidad_num = self._format_number(cantidad_paneles)
        
        self.set_font(self.font_family, 'B', 40)
        self.set_xy(49, 106)
        self.set_text_color(*self.TEXT_COLOR)
        self.cell(w=30, text=cantidad_num, align='L')

        # --- 3. Bloque de Número de Árboles ---
        valor_arboles = datos.get('Árboles Equivalentes Ahorrados', '0')
        if isinstance(valor_arboles, str):
            valor_arboles = valor_arboles.replace('+', '').strip()
        
        arboles_num = self._format_number(valor_arboles)
        
        self.set_font(self.font_family, 'B', 40)
        self.set_xy(38, 152)
        self.set_text_color(*self.TEXT_COLOR)
        self.cell(w=30, text=arboles_num, align='L')

        # --- 4. Bloque de Toneladas de CO2 Evitadas ---
        co2_tons = datos.get('CO2 Evitado Anual (Toneladas)', '0')
        co2_formatted = self._format_number(co2_tons, decimals=1)
        
        self.set_font(self.font_family, 'B', 40)
        self.set_xy(25, 191)
        self.set_text_color(*self.TEXT_COLOR)
        
        # Draw number and unit together to avoid overlap
        w_co2 = self.get_string_width(co2_formatted)
        self.cell(w=w_co2 + 2, text=co2_formatted, align='L')
        
        # Agregar "Ton" en amarillo MIRAC
        self.set_text_color(*YELLOW_MIRAC)
        self.cell(w=50, text="Ton", align='L')
    
    def crear_pagina_generacion_mensual(self, datos):
        self.add_page()
        self.image('assets/5.jpg', x=0, y=0, w=210)
        
        # --- 1. Colocar la gráfica de generación ---
        x_grafica = 15
        y_grafica = 120
        ancho_grafica = 180
        if os.path.exists('grafica_generacion.png'):
            self.image('grafica_generacion.png', x=x_grafica, y=y_grafica, w=ancho_grafica)
        
        # --- 2. Escribir solo el número de la generación promedio ---
        self.set_xy(86, 98)
        self.set_text_color(*self.TEXT_COLOR)
        self.set_font('Roboto', 'B', 15)
        
        valor_generacion = datos.get('Generacion Promedio Mensual (kWh)', '0')
        formatted_gen = self._format_number(valor_generacion)

        # Imprimir número + unidad "kWh" (solicitado)
        w_num = self.get_string_width(formatted_gen)
        self.cell(w=w_num + 1, txt=formatted_gen, align='L')
        # Misma fuente/tamaño que el número
        self.set_font('Roboto', 'B', 15)
        self.cell(w=0, txt=" kWh", align='L')
    
    def crear_pagina_smartmeter(self):
        """Página de Smart Meter (medidor inteligente)."""
        self.add_page()
        if os.path.exists('assets/smartmeter.jpg'):
            self.image('assets/smartmeter.jpg', x=0, y=0, w=210)
        else:
            # Fallback si no existe la imagen
            self.set_font(self.font_family, 'B', 24)
            self.set_xy(20, 100)
            self.cell(0, 10, "Smart Meter", align='C')
    
    def crear_pagina_ubicacion(self, lat, lon):
        self.add_page()
        self.image('assets/6.jpg', x=0, y=0, w=210)
        
        # --- Coordenadas dinámicas ---
        self.set_xy(20, 88)
        self.set_text_color(*self.TEXT_COLOR)
        self.set_font('Roboto', '', 15)
        
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
        self.set_text_color(*self.TEXT_COLOR)
        
        # --- Posicionamos cada dato con alineación a la derecha ---
        x_inicio = 90
        ancho_total = 88

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
        
        # Cantidad de inversores (extraer del formato "2x10kW" o "1x50kW + 1x30kW")
        inversor_recomendado = datos.get('Inversor Recomendado', 'N/A')
        cantidad_inversores = 0
        if inversor_recomendado and inversor_recomendado != 'N/A':
            # Buscar todos los patrones "NxXXkW" y sumar las cantidades
            matches = re.findall(r'(\d+)x\d+kW', inversor_recomendado)
            cantidad_inversores = sum(int(m) for m in matches) if matches else 1
        
        self.set_xy(x_inicio, 135)
        self.cell(w=ancho_total, txt=str(cantidad_inversores) if cantidad_inversores > 0 else "N/A", align='R')
        
        # Referencia inversores (incluye marca si está especificada)
        referencia_inversor = datos.get('Referencia Inversor', '')
        if not referencia_inversor:
            referencia_inversor = inversor_recomendado
        
        self.set_xy(x_inicio, 144)
        self.cell(w=ancho_total, txt=referencia_inversor, align='R')

        # Potencia total en AC
        self.set_xy(x_inicio, 153)
        self.cell(w=ancho_total, txt=f"{datos.get('Potencia AC Inversor', 'X')} kW", align='R')

    def crear_pagina_alcance(self):
        self.add_page()
        self.image('assets/8.jpg', x=0, y=0, w=210)     

    def crear_pagina_terminos(self, datos):
        self.add_page()
        self.image('assets/9.jpg', x=0, y=0, w=210)
        
        self.set_text_color(*self.TEXT_COLOR)
        
        x_fin = 190
        ancho_celda = 80

        # --- Sistema solar FV ---
        self.set_font('Roboto', '', 14)
        self.set_xy(x_fin - ancho_celda, 70)
        val_sistema = self._format_currency(datos.get("Valor Sistema FV (sin IVA)", "0"))
        self.cell(w=ancho_celda, txt=val_sistema, align='R')

        # --- IVA ---
        self.set_font('Roboto', 'B', 14)
        self.set_xy(x_fin - ancho_celda, 96)
        val_iva = self._format_currency(datos.get("Valor IVA", "0"))
        self.cell(w=ancho_celda, txt=val_iva, align='R')
        
        # --- Total con IVA ---
        self.set_font('Roboto', 'B', 14)
        self.set_xy(x_fin - ancho_celda, 106)
        val_total = self._format_currency(datos.get("Valor Total del Proyecto (COP)", "0"))
        self.cell(w=ancho_celda, txt=val_total, align='R')
        
        # --- O&M (Operation & Maintenance) ---
        self.set_font('Roboto', 'B', 14)
        self.set_xy(x_fin - ancho_celda, 115)
        val_om = self._format_currency(datos.get("O&M (Operation & Maintenance)", "0"))
        self.cell(w=ancho_celda, txt=val_om, align='R')
    
    def _format_large_money(self, value_str):
        """Formatea valor monetario a corto (7.9M, 638k) y devuelve tupla (valor, sufijo)."""
        try:
            val_float = float(str(value_str).replace('$', '').replace(',', '').strip())
        except:
            return "0", ""
            
        if val_float >= 1000000:
            val = val_float / 1000000
            return f"{val:.1f}", "M"
        elif val_float >= 1000:
            val = val_float / 1000
            return f"{val:.1f}", "k"
        
        return f"{int(val_float)}", ""

    def crear_pagina_info_financiera(self, datos):
        """Página de Resumen Financiero con TIR, ahorro, O&M y deducible."""
        self.add_page()
        self.image('assets/info_financiera.jpg', x=0, y=0, w=210)
        
        YELLOW_MIRAC = (250, 193, 7)
        X_ALIGN = 25  # Alineación vertical común
        
        # --- 1. TIR (Tasa Interna de Retorno) ---
        tir_str = datos.get('TIR (Tasa Interna de Retorno)', '0%')
        tir_val = tir_str.replace('%', '').strip()
        
        # Posición TIR
        self.set_xy(46, 68) 
        self.set_font(self.font_family, 'B', 40)
        self.set_text_color(*self.TEXT_COLOR)
        
        # "TIR"
        self.cell(w=self.get_string_width("TIR ") + 2, txt="TIR ", align='L')
        # Valor
        self.cell(w=self.get_string_width(tir_val) + 2, txt=tir_val, align='L')
        # "%" en amarillo
        self.set_text_color(*YELLOW_MIRAC)
        self.cell(w=15, txt="%", align='L')
        
        # --- 2. Tiempo de retorno (años) ---
        # --- 2. Tiempo de retorno (años) ---
        periodo_retorno = datos.get('Periodo de Retorno (anos)', '0')
        self.set_font('Roboto', 'B', 15) # Texto resaltado dentro del párrafo del background
        self.set_text_color(*self.TEXT_COLOR)
        # Ajustamos posición para caer justo donde debería ir el número en la plantilla
        # Asumiendo que el texto "Tiempo de retorno..." ya está impreso en la imagen
        self.set_xy(153, 75) 
        self.cell(w=30, h=6, txt=f"{self._format_number(periodo_retorno, decimals=1)} años", align='R')

        # --- Base font setup for values ---
        self.set_font(self.font_family, 'B', 40)
        
        # --- 3. Ahorro anual aproximado ---
        ahorro_raw = datos.get('Ahorro Estimado Primer Ano (COP)', '0')
        val, suffix = self._format_large_money(ahorro_raw)
        
        target_y_1 = 107
        self.set_xy(X_ALIGN, target_y_1)
        
        self.set_text_color(*self.TEXT_COLOR)
        self.cell(w=10, txt="$ ", align='L')
        self.cell(w=self.get_string_width(val) + 2, txt=val, align='L')
        self.set_text_color(*YELLOW_MIRAC)
        self.cell(w=10, txt=suffix, align='L')
        
        # --- 4. Precio anual O&M ---
        om_raw = datos.get('O&M (Operation & Maintenance)', '0')
        val_om, suffix_om = self._format_large_money(om_raw)
        
        target_y_2 = 148  # Subido un poco respecto a 163
        self.set_xy(X_ALIGN, target_y_2)
        
        self.set_text_color(*self.TEXT_COLOR)
        self.cell(w=10, txt="$ ", align='L')
        self.cell(w=self.get_string_width(val_om) + 2, txt=val_om, align='L')
        self.set_text_color(*YELLOW_MIRAC)
        self.cell(w=10, txt=suffix_om, align='L')
        
        # --- 5. Deducible impuesto de renta ---
        valor_sistema_str = datos.get('Valor Sistema FV (sin IVA)', '0')
        try:
            valor_sistema = float(str(valor_sistema_str).replace('$', '').replace(',', '').strip())
            deducible = valor_sistema * 0.44
        except:
            deducible = 0
            
        val_ded, suffix_ded = self._format_large_money(deducible)
        
        target_y_3 = 187 # Subido significativamente de 213 (estaba muy abajo)
        self.set_xy(X_ALIGN, target_y_3) # Movido más a la izquierda (X=25)
        
        self.set_text_color(*self.TEXT_COLOR)
        self.cell(w=10, txt="$ ", align='L')
        self.cell(w=self.get_string_width(val_ded) + 2, txt=val_ded, align='L')
        self.set_text_color(*YELLOW_MIRAC)
        self.cell(w=10, txt=suffix_ded, align='L')
    
    def crear_pagina_aspectos_a(self):
        """Primera página de aspectos (reemplaza aspectos 1, 2, 3)."""
        self.add_page()
        self.image('assets/aspectos_a.jpg', x=0, y=0, w=210)
        
    def crear_pagina_aspectos_b(self):
        """Segunda página de aspectos (reemplaza aspectos 1, 2, 3)."""
        self.add_page()
        self.image('assets/aspectos_b.jpg', x=0, y=0, w=210)
        
    def crear_pagina_proyectos(self):
        self.add_page()
        self.image('assets/13.jpg', x=0, y=0, w=210)
        
        
    def crear_pagina_contacto(self):
        self.add_page()
        self.image('assets/14.jpg', x=0, y=0, w=210)


    def crear_pagina_financiacion(self, datos):
        self.add_page()
        self.image('assets/fin.jpg', x=0, y=0, w=210)
        
        self.set_text_color(*self.TEXT_COLOR)
        
        # Anticipo (Desembolso Inicial)
        self.set_font('Roboto', 'B', 35)
        self.set_xy(42, 56)
        desembolso_str = datos.get("Desembolso Inicial (COP)", "0")
        try:
            desembolso_valor = float(desembolso_str.replace("$", "").replace(",", ""))
        except:
            desembolso_valor = 0
        desembolso_millones = desembolso_valor / 1000000
        self.cell(w=50, txt=f"{desembolso_millones:.1f}", align='C')

        # Cuota Mensual
        self.set_font('Roboto', 'B', 35)
        self.set_xy(42, 94)
        cuota_str = datos.get("Cuota Mensual del Credito (COP)", "0")
        try:
            cuota_valor = float(cuota_str.replace("$", "").replace(",", ""))
        except:
            cuota_valor = 0
        cuota_millones = cuota_valor / 1000000
        self.cell(w=50, txt=f"{cuota_millones:.1f}", align='C')

        # Ahorro Mensual
        self.set_font('Roboto', 'B', 35)
        self.set_xy(42, 132)
        ahorro_anual_str = datos.get("Ahorro Estimado Primer Ano (COP)", "0")
        try:
            ahorro_anual_valor = float(ahorro_anual_str.replace("$", "").replace(",", ""))
        except:
            ahorro_anual_valor = 0
        ahorro_mensual_calculado = ahorro_anual_valor / 12
        ahorro_millones = ahorro_mensual_calculado / 1000000
        self.cell(w=50, txt=f"{ahorro_millones:.1f}", align='C')
        
        # --- Variables adicionales ---
        plazo_credito = datos.get("Plazo del Crédito", "0")
        try:
            vida_util = str(int(plazo_credito) // 12)
        except:
            vida_util = "0"
        
        # Plazo del crédito
        self.set_font('Roboto', 'B', 15)
        self.set_xy(104,191)
        self.cell(w=50, txt=str(plazo_credito), align='C')
        
        # Vida útil del proyecto
        self.set_font('Roboto', 'B', 15)
        self.set_xy(19,214)
        self.cell(w=50, txt=str(vida_util), align='C')

    def generar(self, datos_calculadora, usa_financiamiento, lat=None, lon=None, incluir_smartmeter=False):
        """
        Llama a todos los métodos en orden para construir el documento.
        
        Nueva estructura:
        1. Portada
        2. Resumen Ejecutivo (kWp, módulos, árboles, CO2)
        3. Generación Mensual
        4. Ubicación
        5. Smart Meter (si aplica)
        6. Ficha Técnica
        7. Alcance
        8. Términos/Costos
        9. Info Financiera (TIR, ahorro, O&M, deducible)
        10. Financiación (si aplica)
        11. Aspectos A
        12. Aspectos B
        13. Proyectos
        14. Contacto
        """
        self.crear_portada()
        self.crear_resumen_ejecutivo(datos_calculadora)
        self.crear_pagina_generacion_mensual(datos_calculadora)
        if lat is not None and lon is not None:
            self.crear_pagina_ubicacion(lat, lon)
        
        # Página de Smart Meter (después de ubicación)
        if incluir_smartmeter:
            self.crear_pagina_smartmeter()
        
        self.crear_pagina_tecnica(datos_calculadora)
        self.crear_pagina_alcance()
        self.crear_pagina_terminos(datos_calculadora)
        self.crear_pagina_info_financiera(datos_calculadora)
        
        # Página de financiación solo si se requiere
        if usa_financiamiento:
            self.crear_pagina_financiacion(datos_calculadora)
        
        self.crear_pagina_aspectos_a()
        self.crear_pagina_aspectos_b()
        self.crear_pagina_proyectos()
        self.crear_pagina_contacto()
    
        return bytes(self.output(dest='S'))

