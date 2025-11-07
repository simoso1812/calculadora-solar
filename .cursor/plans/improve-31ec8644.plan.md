<!-- 31ec8644-d9c8-4bc5-914b-25f48e7254b1 5d27f3f8-26f3-4869-aa4d-db7f625ea6a2 -->
# Plan: Refine Energy Generation Calculation

## Objective

To improve the accuracy of the solar energy generation forecast by making the Performance Ratio (PR) more dynamic and less conservative.

## 1. Create a `calcular_performance_ratio` Function

I will add a new helper function in `app.py`, right before the `cotizacion` function. This function will contain the new, more detailed logic for calculating the system's overall efficiency (`n`).

```python
def calcular_performance_ratio(clima, cubierta):
    """
    Calcula el Performance Ratio (PR) del sistema basado en el clima y tipo de cubierta.
    """
    PR_BASE = 0.85  # Nuevo PR base más optimista

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
```

## 2. Update the `cotizacion` Function in `app.py`

I will modify the `cotizacion` function to use this new helper. I will replace the old static logic for `n` with a call to the new function.

**File to Modify**: `app.py`

**Current code to be removed (around lines 965-967):**

```python
    n = 0.8
    life = horizonte_tiempo
    if clima.strip().upper() == "NUBE": n -= 0.05
```

**New code to be inserted:**

```python
    life = horizonte_tiempo
    n = calcular_performance_ratio(clima, cubierta)
```

## 3. Test the Changes

After implementing the changes, I will run a few test cases by calling the `cotizacion` function with different `clima` and `cubierta` values to ensure the new PR is being calculated and used correctly, leading to a higher energy generation estimate.

This plan will result in a more realistic and less conservative energy forecast, aligning better with the real-world performance you've observed.

### To-dos

- [ ] Add calcular_margen_inversor function to calculate variable margins based on system size
- [ ] Refactor recomendar_inversor function to implement tiered selection logic with size-based constraints
- [ ] Test the new inverter selection logic with various system sizes to verify correct behavior