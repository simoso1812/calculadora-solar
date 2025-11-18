"""
Servicio para geolocalización y mapas.
"""
import os
import requests
import streamlit as st
from geopy.geocoders import Nominatim

def get_coords_from_address(address):
    """Convierte una dirección de texto en coordenadas (lat, lon)."""
    try:
        geolocator = Nominatim(user_agent="mirac_solar_calculator")
        # El timeout es importante para no sobrecargar el servidor gratuito
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except Exception as e:
        st.error(f"Error en la geocodificación: {e}")
        return None
    
def get_static_map_image(lat, lon, api_key):
    """
    Genera una URL para la API de Google Maps Static con alta resolución y
    capa híbrida, y descarga la imagen del mapa.
    """
    image_path = "assets/mapa_ubicacion.jpg"
    
    try:
        # Validar parámetros de entrada
        if not api_key or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            st.error("Parámetros inválidos para generar el mapa")
            return None
            
        # Parámetros para la imagen del mapa mejorada
        zoom = 16
        size = "600x400"
        maptype = "hybrid"
        scale = 2
        
        # Construimos la URL con los nuevos parámetros
        url = (f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom={zoom}"
               f"&size={size}&scale={scale}&maptype={maptype}"
               f"&markers=color:red%7C{lat},{lon}&key={api_key}")

        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            st.error(f"Google Maps API devolvió un error {response.status_code}.")
            return None

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(image_path), exist_ok=True)

        with open(image_path, "wb") as f:
            f.write(response.content)

        if os.path.exists(image_path) and os.path.getsize(image_path) > 1000:
            return image_path
        else:
            st.error("Se descargó un archivo de mapa vacío o inválido.")
            return None

    except Exception as e:
        st.error(f"Error al generar la imagen del mapa: {e}")
        return None

