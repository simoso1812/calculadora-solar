"""
Utilidad para generar reportes en Excel con formato profesional.
"""
import io
import pandas as pd
from datetime import datetime

def generar_excel_financiero(datos_proyecto: dict, flujo_caja: list, monthly_generation: list, 
                              horizonte: int, analisis_sensibilidad: dict = None) -> bytes:
    """
    Genera un archivo Excel con múltiples hojas para análisis financiero.
    
    Args:
        datos_proyecto: Diccionario con datos del proyecto
        flujo_caja: Lista de flujos de caja anuales
        monthly_generation: Lista de generación mensual
        horizonte: Años de análisis
        analisis_sensibilidad: Diccionario opcional con análisis de sensibilidad
    
    Returns:
        bytes: Archivo Excel en formato bytes
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FA323F',  # Brand color
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        currency_format = workbook.add_format({
            'num_format': '$ #,##0',
            'align': 'right'
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.00%',
            'align': 'center'
        })
        
        number_format = workbook.add_format({
            'num_format': '#,##0.00',
            'align': 'right'
        })
        
        # =====================================================================
        # HOJA 1: RESUMEN DEL PROYECTO
        # =====================================================================
        resumen_data = {
            'Parámetro': [
                'Cliente',
                'Proyecto',
                'Fecha',
                'Tamaño del Sistema (kWp)',
                'Cantidad de Paneles',
                'Inversor Recomendado',
                'Valor del Proyecto (COP)',
                'TIR',
                'VPN (COP)',
                'Payback (años)',
                'Ahorro Año 1 (COP)',
                'Generación Anual (kWh)',
            ],
            'Valor': [
                datos_proyecto.get('cliente', 'N/A'),
                datos_proyecto.get('proyecto', 'N/A'),
                datos_proyecto.get('fecha', datetime.now().strftime('%Y-%m-%d')),
                datos_proyecto.get('tamano_kwp', 0),
                datos_proyecto.get('cantidad_paneles', 0),
                datos_proyecto.get('inversor', 'N/A'),
                datos_proyecto.get('valor_proyecto', 0),
                datos_proyecto.get('tir', 0),
                datos_proyecto.get('vpn', 0),
                datos_proyecto.get('payback', 'N/A'),
                datos_proyecto.get('ahorro_ano1', 0),
                datos_proyecto.get('generacion_anual', 0),
            ]
        }
        df_resumen = pd.DataFrame(resumen_data)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False, startrow=1)
        
        worksheet_resumen = writer.sheets['Resumen']
        worksheet_resumen.write(0, 0, 'RESUMEN DEL PROYECTO SOLAR', header_format)
        worksheet_resumen.merge_range(0, 0, 0, 1, 'RESUMEN DEL PROYECTO SOLAR', header_format)
        worksheet_resumen.set_column('A:A', 30)
        worksheet_resumen.set_column('B:B', 25)
        
        # =====================================================================
        # HOJA 2: FLUJO DE CAJA
        # =====================================================================
        flujo_data = []
        acumulado = 0
        for i, flujo in enumerate(flujo_caja):
            acumulado += flujo
            flujo_data.append({
                'Año': i,
                'Flujo Neto (COP)': flujo,
                'Flujo Acumulado (COP)': acumulado
            })
        
        df_flujo = pd.DataFrame(flujo_data)
        df_flujo.to_excel(writer, sheet_name='Flujo de Caja', index=False, startrow=1)
        
        worksheet_flujo = writer.sheets['Flujo de Caja']
        worksheet_flujo.write(0, 0, 'FLUJO DE CAJA ANUAL', header_format)
        worksheet_flujo.merge_range(0, 0, 0, 2, 'FLUJO DE CAJA ANUAL', header_format)
        worksheet_flujo.set_column('A:A', 10)
        worksheet_flujo.set_column('B:C', 25)
        
        # Agregar gráfico de flujo de caja
        chart_flujo = workbook.add_chart({'type': 'line'})
        chart_flujo.add_series({
            'name': 'Flujo Acumulado',
            'categories': f"='Flujo de Caja'!$A$3:$A${len(flujo_caja)+2}",
            'values': f"='Flujo de Caja'!$C$3:$C${len(flujo_caja)+2}",
            'line': {'color': '#FA323F', 'width': 2}
        })
        chart_flujo.set_title({'name': 'Flujo de Caja Acumulado'})
        chart_flujo.set_x_axis({'name': 'Año'})
        chart_flujo.set_y_axis({'name': 'COP', 'num_format': '$ #,##0'})
        chart_flujo.set_size({'width': 600, 'height': 350})
        worksheet_flujo.insert_chart('E3', chart_flujo)
        
        # =====================================================================
        # HOJA 3: GENERACIÓN MENSUAL
        # =====================================================================
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        gen_data = {
            'Mes': meses,
            'Generación (kWh)': monthly_generation if monthly_generation else [0]*12
        }
        df_gen = pd.DataFrame(gen_data)
        df_gen.to_excel(writer, sheet_name='Generación Mensual', index=False, startrow=1)
        
        worksheet_gen = writer.sheets['Generación Mensual']
        worksheet_gen.write(0, 0, 'GENERACIÓN MENSUAL ESTIMADA', header_format)
        worksheet_gen.merge_range(0, 0, 0, 1, 'GENERACIÓN MENSUAL ESTIMADA', header_format)
        worksheet_gen.set_column('A:A', 15)
        worksheet_gen.set_column('B:B', 20)
        
        # Gráfico de barras para generación
        chart_gen = workbook.add_chart({'type': 'column'})
        chart_gen.add_series({
            'name': 'Generación kWh',
            'categories': "='Generación Mensual'!$A$3:$A$14",
            'values': "='Generación Mensual'!$B$3:$B$14",
            'fill': {'color': '#4ECDC4'}
        })
        chart_gen.set_title({'name': 'Generación Mensual Estimada'})
        chart_gen.set_x_axis({'name': 'Mes'})
        chart_gen.set_y_axis({'name': 'kWh'})
        chart_gen.set_size({'width': 600, 'height': 350})
        worksheet_gen.insert_chart('D3', chart_gen)
        
        # =====================================================================
        # HOJA 4: ANÁLISIS DE SENSIBILIDAD (si está disponible)
        # =====================================================================
        if analisis_sensibilidad:
            sens_data = []
            for escenario, datos in analisis_sensibilidad.items():
                sens_data.append({
                    'Escenario': escenario,
                    'TIR': datos.get('tir', 0),
                    'VPN (COP)': datos.get('vpn', 0),
                    'Payback (años)': datos.get('payback', 'N/A'),
                    'Desembolso Inicial (COP)': datos.get('desembolso_inicial', 0),
                    'Cuota Mensual (COP)': datos.get('cuota_mensual', 0)
                })
            
            df_sens = pd.DataFrame(sens_data)
            df_sens.to_excel(writer, sheet_name='Análisis Sensibilidad', index=False, startrow=1)
            
            worksheet_sens = writer.sheets['Análisis Sensibilidad']
            worksheet_sens.write(0, 0, 'ANÁLISIS DE SENSIBILIDAD', header_format)
            worksheet_sens.merge_range(0, 0, 0, 5, 'ANÁLISIS DE SENSIBILIDAD', header_format)
            worksheet_sens.set_column('A:A', 30)
            worksheet_sens.set_column('B:F', 20)
        
        # =====================================================================
        # HOJA 5: PARÁMETROS DE ENTRADA
        # =====================================================================
        params_data = {
            'Parámetro': [
                'Consumo Mensual (kWh)',
                'Costo kWh (COP)',
                'Indexación Anual (%)',
                'Tasa de Descuento (%)',
                'Horizonte de Análisis (años)',
                'Tipo de Cubierta',
                'Clima',
                'HSP Promedio (kWh/m²/día)',
            ],
            'Valor': [
                datos_proyecto.get('consumo_mensual', 0),
                datos_proyecto.get('costo_kwh', 0),
                datos_proyecto.get('indexacion', 0),
                datos_proyecto.get('tasa_descuento', 0),
                horizonte,
                datos_proyecto.get('cubierta', 'N/A'),
                datos_proyecto.get('clima', 'N/A'),
                datos_proyecto.get('hsp_promedio', 0),
            ]
        }
        df_params = pd.DataFrame(params_data)
        df_params.to_excel(writer, sheet_name='Parámetros', index=False, startrow=1)
        
        worksheet_params = writer.sheets['Parámetros']
        worksheet_params.write(0, 0, 'PARÁMETROS DE ENTRADA', header_format)
        worksheet_params.merge_range(0, 0, 0, 1, 'PARÁMETROS DE ENTRADA', header_format)
        worksheet_params.set_column('A:A', 30)
        worksheet_params.set_column('B:B', 20)
    
    output.seek(0)
    return output.getvalue()
