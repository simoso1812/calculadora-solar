"""
Utilidades para el cálculo y generación de cotizaciones de cargadores eléctricos.
"""
import os
import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter

def cotizacion_cargadores_costos(distancia_metros: float):
    """Calcula desglose de costos para instalación de un punto de carga.
    Retorna (IVA, diseño, materiales, costo_total, costo_base).
    """
    try:
        costo_base = (63640 * float(distancia_metros) + 857195) * 1.1
        iva = 0.19 * costo_base
        diseno = 0.35 * costo_base
        materiales = 0.65 * costo_base
        costo_total_sin_prima = costo_base + iva
        prima_aiu = costo_total_sin_prima * 0.20  # Prima extra de 20% para AIU
        costo_total = costo_total_sin_prima + prima_aiu
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
    
    try:
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
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return None, None

    desglose = {
        "Costo Base": costo_base,
        "IVA": iva,
        "Diseño": diseno,
        "Materiales": materiales,
        "Costo Total": costo_total,
    }

    return output_buffer.getvalue(), desglose

