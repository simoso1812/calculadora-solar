"""
Utilidad para generar el PDF de la propuesta solar.
"""
from fpdf import FPDF
import datetime
import os
import streamlit as st

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

        # --- 1. Bloque de Ahorro Anual (redondeado a entero en millones) ---
        valor_ahorro_str = datos.get('Ahorro Estimado Primer Ano (COP)', '0').replace(',', '').replace('$', '')
        try:
            valor_ahorro_millones = float(valor_ahorro_str) / 1000000
            valor_ahorro_entero = int(round(valor_ahorro_millones))
        except:
            valor_ahorro_entero = 0
        self.set_font('DMSans', 'B', 40)
        self.set_xy(52, 58)  # Ajustar coordenadas según la nueva plantilla
        self.cell(w=30, text=str(valor_ahorro_entero), align='L')

        # --- 2. Bloque de Cantidad de Módulos Fotovoltaicos ---
        cantidad_paneles = datos.get('Cantidad de Paneles', '0')
        # Extraer solo el número si viene en formato "XX de XXXW"
        if ' de ' in cantidad_paneles:
            cantidad_paneles = cantidad_paneles.split(' de ')[0]
        try:
            cantidad_num = int(cantidad_paneles)
        except:
            cantidad_num = 0
        self.set_font('DMSans', 'B', 40)
        self.set_xy(51, 105)  # Ajustar coordenadas según la nueva plantilla
        self.cell(w=30, text=str(cantidad_num), align='L')

        # --- 3. Bloque de Número de Árboles ---
        valor_arboles = datos.get('Árboles Equivalentes Ahorrados', '0')
        # Si viene como string, extraer número
        if isinstance(valor_arboles, str):
            valor_arboles = valor_arboles.replace('+', '').strip()
        try:
            arboles_num = int(round(float(valor_arboles)))
        except:
            arboles_num = 0
        self.set_font('DMSans', 'B', 40)
        self.set_xy(51, 153)  # Ajustar coordenadas según la nueva plantilla
        self.cell(w=30, text=str(arboles_num), align='L')

        # --- 4. Bloque de Toneladas de CO2 Evitadas ---
        co2_tons = datos.get('CO2 Evitado Anual (Toneladas)', '0')
        try:
            co2_tons_num = float(co2_tons)
            co2_tons_redondeado = round(co2_tons_num, 1)  # Una decimal
        except:
            co2_tons_redondeado = 0.0
        self.set_font('DMSans', 'B', 40)
        self.set_xy(16, 189)  # Ajustar coordenadas según la nueva plantilla
        self.cell(w=30, text=f"{co2_tons_redondeado:.1f}", align='L')
    
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
        if os.path.exists('grafica_generacion.png'):
            self.image('grafica_generacion.png', x=x_grafica, y=y_grafica, w=ancho_grafica)
        
        # --- 2. Escribir solo el número de la generación promedio ---
        # Coordenadas estimadas para el número. ¡Este es el otro valor a ajustar!
        self.set_xy(86, 97)
        self.set_text_color(0, 0, 0) # Texto negro
        self.set_font('Roboto', 'B', 15) # Negrita
        
        # Formateamos el número sin decimales (0f)
        try:
            valor_generacion = float(datos.get('Generacion Promedio Mensual (kWh)', '0').replace(',', ''))
            self.cell(w=30, txt=f"{valor_generacion:,.0f}", align='L')
        except ValueError:
            pass
    
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
        
        # --- O&M (Operation & Maintenance) ---
        self.set_font('Roboto', 'B', 14) # Estilo normal
        self.set_xy(x_fin - ancho_celda, 115) # Coordenada Y estimada (10mm debajo del total)
        self.cell(w=ancho_celda, txt=datos.get("O&M (Operation & Maintenance)", "$ 0"), align='R')
    
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

