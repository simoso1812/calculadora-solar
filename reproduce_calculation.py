
import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from src.services.calculator_service import cotizacion, HSP_MENSUAL_POR_CIUDAD

def reproduce():
    size = 12.0 # kWp
    ciudad = "MEDELLIN"
    hsp_mensual = HSP_MENSUAL_POR_CIUDAD[ciudad]
    
    print(f"Reproducing calculation for {size} kWp in {ciudad}")
    print(f"HSP Monthly: {hsp_mensual}")
    
    # Mock parameters
    Load = 1000 # Irrelevant for generation calculation
    quantity = 20 # Irrelevant for generation calculation logic mostly, but needed for args
    cubierta = "METAL" # Default
    clima = "TEMPLADO" # Default, no adjustment
    index = 0.05
    dRate = 0.1
    costkWh = 800
    module = "Generic"
    
    # Call cotizacion
    results = cotizacion(
        Load=Load,
        size=size,
        quantity=quantity,
        cubierta=cubierta,
        clima=clima,
        index=index,
        dRate=dRate,
        costkWh=costkWh,
        module=module,
        ciudad=ciudad,
        hsp_lista=hsp_mensual,
        incluir_baterias=False
    )
    
    monthly_generation = results[7] # 8th return value is monthly_generation_init
    n = results[14] # 15th return value is n (PR)
    
    print(f"Performance Ratio (PR): {n}")
    print("Monthly Generation (kWh):")
    for i, gen in enumerate(monthly_generation):
        print(f"Month {i+1}: {gen:.2f}")
        
    print(f"Total Annual Generation: {sum(monthly_generation):.2f}")
    print(f"Average Monthly Generation: {sum(monthly_generation)/12:.2f}")

if __name__ == "__main__":
    reproduce()
