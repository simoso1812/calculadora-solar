"""
Carbon Emissions Calculator for Mirac Solar Calculator
Calculates CO2 emissions avoided by solar PV systems in Colombia
"""

import json
import os
from typing import Dict, Any, Optional

class CarbonEmissionsCalculator:
    """
    Calculates carbon emissions avoided by solar photovoltaic systems
    Based on Colombian grid emission factors and international standards
    """

    def __init__(self):
        self.emission_factors = self._load_emission_factors()
        self.equivalency_factors = self._get_equivalency_factors()

    def _load_emission_factors(self) -> Dict[str, Any]:
        """Load emission factors from JSON file or use defaults"""
        try:
            # Try to load from file first
            factors_file = os.path.join("assets", "emission_factors.json")
            if os.path.exists(factors_file):
                with open(factors_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load emission factors file: {e}")

        # Default emission factors for Colombia (2024 data)
        return {
            "colombia_grid": {
                "national_average": 0.245,  # kg CO2/kWh
                "by_region": {
                    "BOGOTA": 0.220,
                    "MEDELLIN": 0.250,
                    "CALI": 0.240,
                    "BARRANQUILLA": 0.260,
                    "CARTAGENA": 0.255,
                    "BUCARAMANGA": 0.235,
                    "PEREIRA": 0.245,
                    "MEDELLÍN": 0.250,  # Handle accent variations
                    "CALÍ": 0.240,
                    "BARRANQUILLA": 0.260,
                    "CARTAGENA": 0.255,
                    "BUCARAMANGA": 0.235,
                    "PEREIRA": 0.245
                }
            },
            "colombia_hydro": 0.012,  # kg CO2/kWh (hydropower)
            "colombia_thermal": 0.485,  # kg CO2/kWh (thermal generation)
            "certification_rates": {
                "carbon_credit_cop_per_ton": 95000,  # Colombian carbon market rate (COP/ton CO2)
                "usd_per_ton": 25.50  # International carbon credit rate
            },
            "metadata": {
                "source": "XM Colombia 2024 Grid Mix",
                "last_updated": "2024-09-16",
                "methodology": "Lifecycle analysis including transmission losses"
            }
        }

    def _get_equivalency_factors(self) -> Dict[str, float]:
        """Get equivalency factors for environmental impact communication"""
        return {
            'tree_co2_absorption': 22,      # kg CO2/tree/year (Colombian average)
            'car_emissions': 4200,          # kg CO2/car/year (average passenger car)
            'home_electricity': 3500,       # kWh/home/year (Colombian average)
            'flight_emissions': 0.25,       # kg CO2/km (economy flight)
            'plastic_bottles': 0.06,        # kg CO2 per 500ml plastic bottle
            'smartphone_charging': 0.0083   # kg CO2 per smartphone charge
        }

    def get_grid_emission_factor(self, region: str = "BOGOTA") -> float:
        """
        Get emission factor for specific Colombian region
        Returns kg CO2 per kWh
        """
        region = region.upper().strip()

        # Try to get region-specific factor
        region_factor = self.emission_factors["colombia_grid"]["by_region"].get(region)

        if region_factor is not None:
            return region_factor

        # Fallback to national average
        return self.emission_factors["colombia_grid"]["national_average"]

    def calculate_emissions_avoided(self, annual_generation_kwh: float,
                                  region: str = "BOGOTA",
                                  system_lifetime_years: int = 25) -> Dict[str, Any]:
        """
        Calculate comprehensive carbon emissions avoided by solar system

        Args:
            annual_generation_kwh: Annual solar generation in kWh
            region: Colombian region/city
            system_lifetime_years: Expected system lifetime

        Returns:
            Dictionary with carbon metrics and equivalencies
        """

        if annual_generation_kwh <= 0:
            return self._get_empty_carbon_data()

        # Get emission factor for the region
        emission_factor = self.get_grid_emission_factor(region)

        # Calculate total emissions avoided over system lifetime
        total_emissions_avoided_kg = annual_generation_kwh * emission_factor * system_lifetime_years
        total_emissions_avoided_tons = total_emissions_avoided_kg / 1000

        # Calculate equivalency metrics
        equivalencies = self._calculate_equivalencies(total_emissions_avoided_kg, annual_generation_kwh)

        # Calculate carbon certification value
        certification_value = self._calculate_certification_value(total_emissions_avoided_tons)

        # Calculate annual metrics
        annual_emissions_avoided_kg = annual_generation_kwh * emission_factor
        annual_emissions_avoided_tons = annual_emissions_avoided_kg / 1000

        return {
            # Annual metrics
            'annual_co2_avoided_kg': annual_emissions_avoided_kg,
            'annual_co2_avoided_tons': annual_emissions_avoided_tons,

            # Lifetime metrics
            'lifetime_co2_avoided_kg': total_emissions_avoided_kg,
            'lifetime_co2_avoided_tons': total_emissions_avoided_tons,

            # Equivalency metrics (annual)
            'trees_saved_per_year': equivalencies['trees_saved'],
            'cars_off_road_per_year': equivalencies['cars_off_road'],
            'homes_powered_per_year': equivalencies['homes_powered'],
            'flights_avoided_per_year': equivalencies['flights_avoided'],

            # Certification and economic value
            'annual_certification_value_cop': certification_value['annual_cop'],
            'lifetime_certification_value_cop': certification_value['lifetime_cop'],

            # Metadata
            'emission_factor_used': emission_factor,
            'region': region,
            'system_lifetime_years': system_lifetime_years,
            'calculation_method': 'Colombian Grid Mix 2024',

            # Additional metrics
            'plastic_bottles_avoided_per_year': equivalencies['plastic_bottles'],
            'smartphone_charges_avoided_per_year': equivalencies['smartphone_charges']
        }

    def _calculate_equivalencies(self, total_emissions_kg: float,
                               annual_generation_kwh: float) -> Dict[str, float]:
        """Calculate environmental equivalency metrics"""

        # Trees saved (annual)
        trees_saved = total_emissions_kg / (self.equivalency_factors['tree_co2_absorption'] * 25)  # 25 year tree lifetime

        # Cars off road (annual)
        cars_off_road = total_emissions_kg / (self.equivalency_factors['car_emissions'] * 25)  # 25 year system lifetime

        # Homes powered (annual)
        homes_powered = annual_generation_kwh / self.equivalency_factors['home_electricity']

        # Flights avoided (annual) - equivalent to one round-trip Bogota-Miami flight
        flights_avoided = total_emissions_kg / (self.equivalency_factors['flight_emissions'] * 2 * 3960)  # Round trip distance

        # Plastic bottles avoided (annual)
        plastic_bottles = total_emissions_kg / self.equivalency_factors['plastic_bottles']

        # Smartphone charges avoided (annual)
        smartphone_charges = total_emissions_kg / self.equivalency_factors['smartphone_charging']

        return {
            'trees_saved': trees_saved,
            'cars_off_road': cars_off_road,
            'homes_powered': homes_powered,
            'flights_avoided': flights_avoided,
            'plastic_bottles': plastic_bottles,
            'smartphone_charges': smartphone_charges
        }

    def _calculate_certification_value(self, total_emissions_tons: float) -> Dict[str, float]:
        """Calculate economic value of carbon credits"""

        # Colombian carbon market rate
        cop_per_ton = self.emission_factors["certification_rates"]["carbon_credit_cop_per_ton"]

        # Calculate annual and lifetime values
        annual_value_cop = (total_emissions_tons / 25) * cop_per_ton  # Annual equivalent
        lifetime_value_cop = total_emissions_tons * cop_per_ton

        return {
            'annual_cop': annual_value_cop,
            'lifetime_cop': lifetime_value_cop,
            'rate_used_cop_per_ton': cop_per_ton
        }

    def _get_empty_carbon_data(self) -> Dict[str, Any]:
        """Return empty carbon data structure for invalid inputs"""
        return {
            'annual_co2_avoided_kg': 0,
            'annual_co2_avoided_tons': 0,
            'lifetime_co2_avoided_kg': 0,
            'lifetime_co2_avoided_tons': 0,
            'trees_saved_per_year': 0,
            'cars_off_road_per_year': 0,
            'homes_powered_per_year': 0,
            'flights_avoided_per_year': 0,
            'annual_certification_value_cop': 0,
            'lifetime_certification_value_cop': 0,
            'emission_factor_used': 0,
            'region': 'N/A',
            'system_lifetime_years': 25,
            'calculation_method': 'N/A',
            'plastic_bottles_avoided_per_year': 0,
            'smartphone_charges_avoided_per_year': 0
        }

    def get_available_regions(self) -> list:
        """Get list of available Colombian regions"""
        return list(self.emission_factors["colombia_grid"]["by_region"].keys())

    def update_emission_factors(self, new_factors: Dict[str, Any]) -> bool:
        """Update emission factors (admin function)"""
        try:
            # Validate new factors structure
            if "colombia_grid" not in new_factors:
                return False

            # Update in memory
            self.emission_factors.update(new_factors)

            # Save to file
            factors_file = os.path.join("assets", "emission_factors.json")
            os.makedirs(os.path.dirname(factors_file), exist_ok=True)

            with open(factors_file, 'w', encoding='utf-8') as f:
                json.dump(self.emission_factors, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error updating emission factors: {e}")
            return False

    def get_methodology_info(self) -> Dict[str, Any]:
        """Get information about calculation methodology"""
        return {
            "methodology": "Based on Colombian electricity grid mix (2024)",
            "data_source": "XM Colombia - Operador del Sistema Interconectado Nacional",
            "scope": "Cradle-to-gate lifecycle analysis including transmission losses",
            "uncertainty": "±10% based on grid composition variations",
            "last_updated": self.emission_factors.get("metadata", {}).get("last_updated", "Unknown"),
            "standards": ["ISO 14064-1", "WRI/WBCSD GHG Protocol", "Colombian Environmental Regulations"]
        }


# Utility functions for formatting
def format_carbon_number(value: float, unit: str = "kg", decimals: int = 1) -> str:
    """Format carbon numbers with appropriate units"""
    if unit == "kg" and value >= 1000:
        return f"{value/1000:,.{decimals}f} ton"
    elif unit == "ton" and value < 1:
        return f"{value*1000:,.0f} kg"
    else:
        return f"{value:,.{decimals}f} {unit}"


def format_currency_cop(value: float) -> str:
    """Format currency values in Colombian pesos"""
    return f"${value:,.0f} COP"


# Global instance for easy access
carbon_calculator = CarbonEmissionsCalculator()

if __name__ == "__main__":
    # Test the calculator
    calculator = CarbonEmissionsCalculator()

    # Test with sample data (5kW system, 1800 kWh/year generation)
    test_generation = 1800  # kWh/year
    result = calculator.calculate_emissions_avoided(test_generation, "BOGOTA")

    print("=== Carbon Emissions Calculator Test ===")
    print(f"Annual Generation: {test_generation} kWh")
    print(f"Region: BOGOTA")
    print(f"Emission Factor: {result['emission_factor_used']} kg CO2/kWh")
    print(f"Annual CO2 Avoided: {result['annual_co2_avoided_kg']:,.0f} kg")
    print(f"Trees Saved per Year: {result['trees_saved_per_year']:.1f}")
    print(f"Cars Off Road per Year: {result['cars_off_road_per_year']:.1f}")
    print(f"Annual Certification Value: {format_currency_cop(result['annual_certification_value_cop'])}")
    print("=" * 50)