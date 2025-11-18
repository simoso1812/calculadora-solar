"""
Funciones de utilidad y validación para la aplicación.
"""

def validar_datos_entrada(Load, size, quantity, cubierta, clima, costkWh, module):
    """Valida que los datos de entrada sean coherentes y válidos"""
    errores = []
    
    if Load <= 0:
        errores.append("El consumo mensual debe ser mayor a 0")
    
    if size <= 0:
        errores.append("El tamaño del sistema debe ser mayor a 0")
    
    if quantity <= 0:
        errores.append("La cantidad de paneles debe ser mayor a 0")
    
    if module <= 0:
        errores.append("La potencia del panel debe ser mayor a 0")
    
    if costkWh <= 0:
        errores.append("El costo por kWh debe ser mayor a 0")
    
    if cubierta not in ["LÁMINA", "TEJA"]:
        errores.append("El tipo de cubierta debe ser LÁMINA o TEJA")
    
    if clima not in ["SOL", "NUBE"]:
        errores.append("El clima debe ser SOL o NUBE")
    
    return errores

def formatear_moneda(valor):
    """Formatea un valor numérico como moneda colombiana"""
    try:
        return f"${valor:,.0f}"
    except (ValueError, TypeError):
        return "$0"

