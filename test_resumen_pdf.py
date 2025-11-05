"""
Script para probar la página del resumen con valores de ejemplo
y verificar las coordenadas de los campos
"""

from fpdf import FPDF
import datetime

class TestPDF(FPDF):
    def __init__(self):
        super().__init__()
        try:
            self.add_font('DMSans', '', 'assets/DMSans-Regular.ttf')
            self.add_font('DMSans', 'B', 'assets/DMSans-Bold.ttf')
            self.add_font('Roboto', '', 'assets/Roboto-Regular.ttf')
            self.add_font('Roboto', 'B', 'assets/Roboto-Bold.ttf')
            self.font_family = 'DMSans'
        except:
            self.font_family = 'Arial'

    def header(self): pass
    def footer(self): pass

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
        self.set_xy(52, 58)  # Coordenadas ajustadas
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
        self.set_xy(51, 105)  # Coordenadas ajustadas
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
        self.set_xy(51, 153)  # Coordenadas ajustadas
        self.cell(w=30, text=str(arboles_num), align='L')

        # --- 4. Bloque de Toneladas de CO2 Evitadas ---
        co2_tons = datos.get('CO2 Evitado Anual (Toneladas)', '0')
        try:
            co2_tons_num = float(co2_tons)
            co2_tons_redondeado = round(co2_tons_num, 1)  # Una decimal
        except:
            co2_tons_redondeado = 0.0
        self.set_font('DMSans', 'B', 40)
        self.set_xy(16, 189)  # Coordenadas ajustadas
        self.cell(w=30, text=f"{co2_tons_redondeado:.1f}", align='L')

# Datos de prueba
datos_prueba = {
    "Ahorro Estimado Primer Ano (COP)": "30000000",  # 30 millones
    "Cantidad de Paneles": "42 de 615W",
    "Árboles Equivalentes Ahorrados": "125",
    "CO2 Evitado Anual (Toneladas)": "12.5",
}

print("Generando PDF de prueba con valores:")
print(f"  Ahorro anual: {datos_prueba['Ahorro Estimado Primer Ano (COP)']} COP -> {int(round(30000000/1000000))} millones")
print(f"  Cantidad paneles: {datos_prueba['Cantidad de Paneles']} -> 42")
print(f"  Arboles: {datos_prueba['Árboles Equivalentes Ahorrados']}")
print(f"  CO2: {datos_prueba['CO2 Evitado Anual (Toneladas)']} ton")
print("\nCoordenadas actuales:")
print(f"  Ahorro: (52, 58)")
print(f"  Modulos: (51, 105)")
print(f"  Arboles: (51, 153)")
print(f"  CO2: (16, 189)")

pdf = TestPDF()
pdf.crear_resumen_ejecutivo(datos_prueba)
pdf.output('test_resumen_final.pdf', 'F')

print("\nPDF de prueba generado: test_resumen_final.pdf")
print("   Abre el archivo y verifica las posiciones de los valores.")

