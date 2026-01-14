# Calculadora Solar - Guía de Despliegue

## Despliegue en Render

### Archivos de Configuración

La aplicación incluye los siguientes archivos para el despliegue automático:

- `Procfile`: Define el comando de inicio para Render
- `render.yaml`: Configuración específica del servicio
- `requirements.txt`: Dependencias de Python

### Variables de Entorno Requeridas

Configura las siguientes variables de entorno en tu dashboard de Render:

#### Obligatorias:
```
GOOGLE_CLIENT_ID=tu_client_id_aqui
GOOGLE_CLIENT_SECRET=tu_client_secret_aqui
GOOGLE_REFRESH_TOKEN=tu_refresh_token_aqui
PARENT_FOLDER_ID=id_carpeta_padre_aqui
Maps_API_KEY=tu_api_key_google_maps_aqui
```

#### Automáticas (Render las establece):
```
RENDER=true
PORT=puerto_asignado_por_render
```

### Pasos para Desplegar

1. **Conecta tu repositorio de GitHub** a Render
2. **Configura las variables de entorno** en el dashboard de Render
3. **Selecciona el tipo de servicio**: Web Service
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

### Solución de Problemas

#### PVGIS no funciona en producción

La aplicación está optimizada para manejar problemas de conectividad con PVGIS en producción:

- **Detección automática** del entorno de producción
- **Reintentos adaptativos** (más reintentos en producción)
- **Fallback inteligente** a datos estimados cuando PVGIS falla
- **Headers optimizados** para servidores de producción

#### Errores comunes:

1. **Timeout de PVGIS**: La aplicación automáticamente usa datos estimados
2. **Variables de entorno faltantes**: Verifica que todas las credenciales estén configuradas
3. **Puerto no disponible**: Render asigna automáticamente el puerto via `$PORT`

### Monitoreo

La aplicación incluye logs detallados para monitorear:
- Conexiones exitosas/fallidas con PVGIS
- Errores de Google Drive API
- Estado de las variables de entorno

### Características de Producción

- **Detección automática** del entorno (local vs producción)
- **Configuración adaptativa** de timeouts y reintentos
- **Fallbacks robustos** para APIs externas
- **Logs informativos** para debugging
