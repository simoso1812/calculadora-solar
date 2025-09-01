# ☀️ Calculadora Solar Profesional - Mirac

## 📋 Descripción

Calculadora solar profesional para la empresa Mirac que automatiza el proceso de cotización, generación de propuestas detalladas y contratos para sistemas fotovoltaicos. La aplicación incluye análisis financiero completo, integración con Google Drive y generación automática de documentos.

## 🚀 Características Principales

### ✨ Funcionalidades Core
- **Cálculo Automático**: Dimensionamiento de sistemas solares por consumo o cantidad de paneles
- **Análisis Financiero**: TIR, VPN, período de retorno y flujo de caja
- **Generación de Propuestas**: PDFs profesionales con diseño personalizado
- **Contratos Automáticos**: Generación de contratos en Word con plantillas
- **Integración Google Drive**: Creación automática de carpetas y subida de archivos

### 🌍 Características Avanzadas
- **Datos Satelitales**: Integración con PVGIS para datos de radiación solar precisos
- **Mapas Interactivos**: Selección de ubicación con Folium y Google Maps
- **Sistemas Off-Grid**: Soporte para baterías y sistemas aislados
- **Financiamiento**: Cálculo de cuotas y análisis de crédito
- **Responsive Design**: Interfaz optimizada para móviles y desktop

## 🛠️ Instalación

### Prerrequisitos
- Python 3.8 o superior
- Cuenta de Google Cloud Platform con APIs habilitadas
- API Key de Google Maps

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd calculadora-solar
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**
```bash
# Crear archivo .env o configurar en el sistema
GOOGLE_CLIENT_ID=tu_client_id
GOOGLE_CLIENT_SECRET=tu_client_secret
GOOGLE_REFRESH_TOKEN=tu_refresh_token
PARENT_FOLDER_ID=id_carpeta_google_drive
Maps_API_KEY=tu_api_key_google_maps
```

4. **Ejecutar la aplicación**
```bash
streamlit run app.py
```

## 🔧 Configuración

### APIs de Google
1. **Google Drive API**: Para creación de carpetas y subida de archivos
2. **Google Maps API**: Para generación de mapas estáticos
3. **OAuth 2.0**: Para autenticación con Google Drive

### Estructura de Carpetas
La aplicación crea automáticamente una estructura organizada en Google Drive:
```
📁 FV[YY][NNN] - [Cliente] - [Ubicación]
├── 📁 00_Contacto_y_Venta
├── 📁 01_Propuesta_y_Contratacion
├── 📁 02_Ingenieria_y_Diseno
├── 📁 03_Adquisiciones_y_Logistica
├── 📁 04_Permisos_y_Legal
├── 📁 05_Instalacion_y_Construccion
├── 📁 06_Puesta_en_Marcha_y_Entrega
├── 📁 07_Operacion_y_Mantenimiento_OM
├── 📁 08_Administrativo_y_Financiero
└── 📁 09_Material_Grafico_y_Marketing
```

## 📊 Uso de la Aplicación

### 1. Datos del Cliente
- Nombre, documento y dirección del proyecto
- Fecha de propuesta
- Ubicación geográfica

### 2. Parámetros del Sistema
- **Método de dimensionamiento**:
  - Por consumo mensual (kWh)
  - Por cantidad de paneles
- Tipo de cubierta (Lámina o Teja)
- Clima predominante (Sol o Nube)

### 3. Configuración Financiera
- Costo por kWh
- Indexación de energía
- Tasa de descuento
- Financiamiento opcional
- Configuración de baterías

### 4. Resultados y Reportes
- Análisis financiero completo
- Gráficos de generación vs consumo
- Flujo de caja acumulado
- Propuesta en PDF
- Contrato en Word

## 🎯 Cálculos Técnicos

### Dimensionamiento del Sistema
```
Tamaño (kWp) = Consumo Mensual × Ratio / (HSP × 30 × Eficiencia)
```

### Generación Mensual
```
Generación = Potencia Efectiva × HSP Mensual × Días × Eficiencia
```

### Análisis Financiero
- **TIR**: Tasa Interna de Retorno
- **VPN**: Valor Presente Neto
- **Payback**: Período de retorno de la inversión
- **LCOE**: Costo Nivelado de Energía

## 🔒 Seguridad

- Las API keys se manejan como variables de entorno
- No se almacenan datos sensibles en el código
- Autenticación OAuth 2.0 para Google Drive
- Validación de datos de entrada

## 🐛 Solución de Problemas

### Error de Google Drive
- Verificar que las credenciales OAuth sean válidas
- Confirmar que la API de Drive esté habilitada
- Revisar permisos de la carpeta padre

### Error de Google Maps
- Verificar que la API key sea válida
- Confirmar que la API de Maps esté habilitada
- Revisar cuotas de uso de la API

### Error de PVGIS
- Verificar conexión a internet
- Confirmar que las coordenadas sean válidas
- Revisar que la ubicación esté en el rango soportado

## 📈 Mejoras Futuras

- [ ] Integración con CRM
- [ ] Múltiples idiomas
- [ ] Plantillas personalizables
- [ ] Análisis de competencia
- [ ] Dashboard de métricas
- [ ] Notificaciones automáticas
- [ ] Backup automático en la nube

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 📞 Soporte

Para soporte técnico o consultas comerciales:
- **Email**: [email@mirac.com]
- **Teléfono**: [+57 XXX XXX XXXX]
- **Sitio Web**: [www.mirac.com]

## 🙏 Agradecimientos

- **PVGIS**: Datos de radiación solar
- **Google APIs**: Integración con servicios de Google
- **Streamlit**: Framework de la aplicación web
- **Comunidad Python**: Librerías y herramientas utilizadas

---

**Desarrollado con ❤️ por el equipo de Mirac**
