import sys
import os
import datetime

# Add the project root to the path so we can import src
sys.path.append(os.getcwd())

from src.utils.pdf_generator import PropuestaPDF

def generate_sample_pdf():
    dummy_data = {
        "Nombre del Proyecto": "Proyecto Prueba",
        "Cliente": "Cliente Prueba",
        "Valor Total del Proyecto (COP)": "$ 50,000,000",
        "Valor Sistema FV (sin IVA)": "$ 40,000,000",
        "Valor IVA": "$ 9,500,000",
        "Tamano del Sistema (kWp)": "5.0",
        "Cantidad de Paneles": "10 de 500W",
        "Área Requerida Aprox. (m²)": "30",
        "Inversor Recomendado": "Inversor X",
        "Generacion Promedio Mensual (kWh)": "600",
        "Ahorro Estimado Primer Ano (COP)": "$ 6,000,000",
        "TIR (Tasa Interna de Retorno)": "15.0%",
        "VPN (Valor Presente Neto) (COP)": "$ 20,000,000",
        "Periodo de Retorno (anos)": "5.5",
        "Tipo de Cubierta": "TEJA",
        "Potencia de Paneles": "500",
        "Potencia AC Inversor": "5.0",
        "Árboles Equivalentes Ahorrados": "100",
        "CO2 Evitado Anual (Toneladas)": "5.5",
        "O&M (Operation & Maintenance)": "$ 1,000,000",
        "Monto a Financiar (COP)": "$ 35,000,000",
        "Cuota Mensual del Credito (COP)": "$ 800,000",
        "Desembolso Inicial (COP)": "$ 15,000,000",
        "Plazo del Crédito": "60"
    }

    pdf = PropuestaPDF(
        client_name="Cliente Prueba",
        project_name="Proyecto Prueba",
        documento="123456789",
        direccion="Calle Falsa 123",
        fecha=datetime.date.today()
    )

    # Dummy coordinates for location
    lat = 4.6097
    lon = -74.0817

    # Generate dummy graph using the SHARED utility
    from src.utils.plotting import generar_grafica_generacion
    
    # Create realistic dummy data for the graph
    Load = 500
    monthly_generation = [400, 450, 500, 550, 600, 650, 600, 550, 500, 450, 400, 350]
    incluir_baterias = False
    
    generar_grafica_generacion(monthly_generation, Load, incluir_baterias)

    try:
        pdf_bytes = pdf.generar(dummy_data, usa_financiamiento=True, lat=lat, lon=lon)
        
        output_filename = "sample_propuesta.pdf"
        with open(output_filename, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"Successfully generated {output_filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists("grafica_generacion.png"):
            os.remove("grafica_generacion.png")

if __name__ == "__main__":
    generate_sample_pdf()
