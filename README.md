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
- **🌱 Análisis de Sostenibilidad**: Cálculo de emisiones de carbono evitadas y equivalencias ambientales

## 🛠️ Instalación

### Prerrequisitos
- Python 3.8 o superior
- Cuenta de Google Cloud Platform con APIs habilitadas
- API Key de Google Maps
- Archivo `assets/emission_factors.json` (incluido en el repositorio)

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

### Archivos de Configuración
```
📁 assets/
├── 📄 emission_factors.json          # Factores de emisión de carbono
├── 📄 1.jpg to 14.jpg               # Plantillas PDF
├── 📄 contrato_plantilla.docx       # Plantilla de contrato
├── 📄 DMSans-Bold.ttf               # Fuentes
└── 📄 DMSans-Regular.ttf
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
- 🌱 Análisis de sostenibilidad (opcional)

### 4. Resultados y Reportes
- Análisis financiero completo
- 🌱 Impacto ambiental y sostenibilidad
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

### 🌱 Cálculos de Sostenibilidad
- **Emisiones de CO2 Evitadas**: Basado en factores de emisión de la red colombiana
- **Equivalencias Ambientales**: Árboles salvados, autos equivalentes, vuelos evitados
- **Valor de Certificación**: Potencial valor económico de créditos de carbono
- **Factores Regionales**: Emisiones específicas por ciudad en Colombia

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

### Error en Cálculos de Carbono
- Verificar que `assets/emission_factors.json` exista
- Confirmar que el módulo `carbon_calculator.py` esté presente
- Revisar que las dependencias estén instaladas correctamente

## 🌱 Análisis de Sostenibilidad

### Características del Módulo de Carbono

La aplicación incluye un módulo avanzado de cálculo de emisiones de carbono que permite:

#### 📊 Métricas Principales
- **CO2 Evitado Anual**: Toneladas de CO2 que deja de emitirse por año
- **Árboles Salvados**: Número de árboles equivalentes en absorción de CO2
- **Valor de Certificación**: Valor potencial de créditos de carbono en COP
- **Autos Equivalentes**: Número de vehículos que dejarían de circular
- **Vuelos Evitados**: Número de vuelos de ida y vuelta equivalentes
- **Botellas de Plástico**: Cantidad de botellas recicladas equivalentes
- **Cargas de Celular**: Número de cargas de batería equivalentes

#### 🗺️ Factores de Emisión Regionales
- **Bogotá**: 0.220 kg CO2/kWh (menor por mayor participación hidroeléctrica)
- **Medellín**: 0.250 kg CO2/kWh (mezcla hidro y térmica)
- **Cali**: 0.240 kg CO2/kWh (mezcla balanceada)
- **Barranquilla**: 0.260 kg CO2/kWh (mayor participación térmica)
- **Cartagena**: 0.255 kg CO2/kWh (plantas térmicas costeras)
- **Bucaramanga**: 0.235 kg CO2/kWh (mezcla industrial variada)
- **Pereira**: 0.245 kg CO2/kWh (región agrícola moderada)

#### 📋 Metodología
- **Fuente**: XM Colombia - Análisis de mezcla de generación 2024
- **Estándares**: ISO 14064-1, GHG Protocol, Regulaciones Ambientales Colombianas
- **Incertidumbre**: ±10% basado en variaciones de composición de la red
- **Alcance**: Análisis de ciclo de vida incluyendo pérdidas de transmisión

### Configuración del Análisis de Sostenibilidad

1. **Activar en Interfaz Móvil**: En la pestaña "💰 Finanzas" → "🌱 Cálculo de Emisiones de Carbono"
2. **Activar en Interfaz Desktop**: En el sidebar → "🌱 Cálculo de Emisiones de Carbono"
3. **Visualizar Resultados**: Métricas aparecen automáticamente en la sección de resultados
4. **Personalización**: Los factores de emisión se pueden actualizar en `assets/emission_factors.json`

## 📈 Mejoras Futuras

- [ ] Integración con CRM
- [ ] Múltiples idiomas
- [ ] Plantillas personalizables
- [ ] Análisis de competencia
- [ ] Dashboard de métricas
- [ ] Notificaciones automáticas
- [ ] Backup automático en la nube
- [x] **🌱 Análisis de Sostenibilidad (Implementado)**

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
- **XM Colombia**: Datos de emisiones de la red eléctrica
- **Streamlit**: Framework de la aplicación web
- **Comunidad Python**: Librerías y herramientas utilizadas

---

**Desarrollado con ❤️ por el equipo de Mirac**
