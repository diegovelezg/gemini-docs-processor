# GEMINI.md - Contexto del Proyecto

## 🚀 Resumen del Proyecto
Este proyecto es un procesador de documentos de Google Docs que utiliza la API de Gemini para realizar análisis profundos mediante prompts secuenciales. El flujo de trabajo principal consiste en obtener documentos de una carpeta compartida de Google Drive, extraer su contenido como texto plano y procesarlos a través de una serie de modelos de lenguaje (LLM) para generar reportes en formato Markdown.

### Tecnologías Principales
- **Lenguaje:** Python 3.9+
- **IA:** `google-generativeai` (Gemini)
- **Scraping/Web:** `requests`, `beautifulsoup4`
- **Gestión de Entorno:** `python-dotenv`
- **Opcional:** `google-cloud-aiplatform` (para procesamiento en Batch)

## 📁 Estructura del Proyecto
- `main.py`: Script central que gestiona la lógica de scraping, extracción de texto, llamadas a la API y formateo de resultados.
- `prompts/`: Contiene los archivos Markdown que definen las instrucciones para Gemini.
    - `01_disonancias.md`: Análisis de brechas de implementación.
    - `02_complejidad.md`: Análisis de tensiones y complejidad.
    - ... otros prompts específicos.
- `output/`: Directorio donde se guardan los resultados generados y el archivo de tracking.
    - `processed_documents.csv`: Registro de documentos ya procesados para evitar duplicados.
- `requirements.txt` & `pyproject.toml`: Definición de dependencias.

## ⚙️ Configuración y Uso

### Requisitos Previos
1. Python instalado.
2. API Key de Google AI Studio.
3. ID de una carpeta de Google Drive compartida públicamente.

### Instalación
```bash
pip install -r requirements.txt
```

### Variables de Entorno (.env)
Configura los siguientes valores en un archivo `.env`:
- `GEMINI_API_KEY`: Tu clave de API.
- `GEMINI_MODEL`: Modelo a usar (ej: `gemini-1.5-pro`).
- `PROMPTS_TO_USE`: Lista separada por comas de los archivos en `prompts/`.
- `SOURCE_DOC_URL`: (Opcional) URL de un doc individual.
- `DRIVE_FOLDER_ID`: ID de la carpeta en `main.py` (actualmente `1jyc53AO7qEDnVcHBfmrOPbJLj3fFCrm8`).

### Ejecución
```bash
python main.py
```

## 🛠️ Convenciones de Desarrollo
- **Modos de Procesamiento:** El script soporta modo `normal` (con caching oficial de Gemini) y modo `batch` (más económico, vía Vertex AI). Se cambia en `main.py` mediante la variable `PROCESSING_MODE`.
- **Caching:** Se utiliza el sistema de caché de Gemini para reducir costos y latencia al procesar múltiples prompts sobre el mismo documento extenso.
- **Tracking:** El archivo `output/processed_documents.csv` actúa como una base de datos simple para persistir qué documentos ya fueron analizados.
- **Scraping:** El acceso a los documentos se realiza vía exportación directa a texto plano (`/export?format=txt`), evitando la necesidad de OAuth complejo.

## 📝 Notas sobre los Prompts
Los prompts están diseñados para análisis cualitativo, priorizando la "Descripción Densa" (Thick Description) y evitando resúmenes ejecutivos superficiales. Cada prompt debe estar en un archivo `.md` dentro de `prompts/` y tener un encabezado con `#` para el título.
