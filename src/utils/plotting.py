import matplotlib.pyplot as plt
import os

def generar_grafica_generacion(monthly_generation, Load, incluir_baterias, filename="grafica_generacion.png"):
    """
    Genera y guarda la gráfica de generación mensual.
    Retorna True si se generó correctamente, False si hubo error.
    """
    try:
        fig, ax = plt.subplots(figsize=(10, 5))
        meses_grafico = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        
        if incluir_baterias:
            generacion_autoconsumida = []
            energia_a_bateria = []
            for gen_mes in monthly_generation:
                autoconsumo_mes = min(gen_mes, Load)
                bateria_mes = max(0, gen_mes - autoconsumo_mes)
                generacion_autoconsumida.append(autoconsumo_mes)
                energia_a_bateria.append(bateria_mes)
            
            ax.bar(meses_grafico, generacion_autoconsumida, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
            ax.bar(meses_grafico, energia_a_bateria, bottom=generacion_autoconsumida, color='green', edgecolor='black', label='Energía Almacenada en Batería', width=0.7)
            ax.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
            ax.set_title("Flujo de Energía Mensual Estimado (Off-Grid)", fontweight="bold")
        else:
            generacion_autoconsumida_on, excedentes_vendidos, importado_de_la_red = [], [], []
            for gen_mes in monthly_generation:
                if gen_mes >= Load:
                    generacion_autoconsumida_on.append(Load)
                    excedentes_vendidos.append(gen_mes - Load)
                    importado_de_la_red.append(0)
                else:
                    generacion_autoconsumida_on.append(gen_mes)
                    excedentes_vendidos.append(0)
                    importado_de_la_red.append(Load - gen_mes)
            
            ax.bar(meses_grafico, generacion_autoconsumida_on, color='orange', edgecolor='black', label='Generación Autoconsumida', width=0.7)
            ax.bar(meses_grafico, excedentes_vendidos, bottom=generacion_autoconsumida_on, color='red', edgecolor='black', label='Excedentes Vendidos', width=0.7)
            ax.bar(meses_grafico, importado_de_la_red, bottom=generacion_autoconsumida_on, color='#2ECC71', edgecolor='black', label='Importado de la Red', width=0.7)
            ax.axhline(y=Load, color='grey', linestyle='--', linewidth=1.5, label='Consumo Mensual')
            ax.set_title("Generación Vs. Consumo Mensual (On-Grid)", fontweight="bold")
        
        ax.legend()
        plt.tight_layout()
        plt.savefig(filename, dpi=100)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error generando gráfica: {e}")
        return False
