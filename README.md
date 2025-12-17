# 🚀 Gemini Google Docs → Markdown Processor

Script Python simple que lee un Google Doc público, lo procesa con Gemini API usando múltiples prompts, y guarda los resultados en un archivo Markdown local.

## 📋 Características

- ✅ Lectura de Google Docs públicos (origen)
- ✅ Procesamiento con Gemini API
- ✅ Caching simple en memoria
- ✅ Múltiples prompts secuenciales
- ✅ Escritura en Markdown local (destino)
- ✅ Sin dependencias de Google OAuth

## 🚀 Configuración Rápida

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Obtener Gemini API Key
1. Ir a [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Crear nueva API key
3. Copiar la key

### 3. Configurar Google Doc (Origen)
1. Ve a tu Google Doc
2. Comparte el documento: **Compartir → General → Cualquier persona con el enlace**
3. Copia la URL del documento

### 4. Configurar variables de entorno
```bash
cp .env.example .env
```

Editar `.env` con tus valores:
```env
SOURCE_DOC_URL=https://docs.google.com/document/d/TU_DOC_ID/edit
DESTINATION_FILE=output.md
GEMINI_API_KEY=tu_gemini_api_key_aqui
GEMINI_MODEL=gemini-1.5-pro
PROMPTS_TO_USE=01_resumen_ejecutivo.md,02_puntos_clave.md,03_analisis_detallado.md
```

## 🤖 Modelos Disponibles

- **`gemini-1.5-pro`** - Más potente, mejor para análisis complejos (más lento)
- **`gemini-1.5-flash`** - Rápido, bueno para tareas simples y resúmenes
- **`gemini-1.0-pro`** - Modelo anterior, más económico

Recomendación: Usa `gemini-1.5-pro` para análisis detallado y `gemini-1.5-flash` para respuestas rápidas.

## 🎯 Ejecutar

```bash
python main.py
```

No requiere autenticación. Solo necesitas tu API key de Gemini y el Google Doc debe ser público.

## 📝 Prompts Desde Archivos

Los prompts se cargan desde archivos en la carpeta `prompts/`:

### Prompts Disponibles:
- **`01_resumen_ejecutivo.md`** - Resumen conciso con objetivo, puntos clave y conclusiones
- **`02_puntos_clave.md`** - Los 5 insights más importantes con explicaciones
- **`03_analisis_detallado.md`** - Análisis estructural: argumentos, sesgos, fortalezas y debilidades
- **`04_extraccion_datos.md`** - Extracción y categorización de datos cuantitativos y cualitativos
- **`05_propuestas_accion.md`** - Propuestas de acción con implementación y KPIs

### Configurar Prompts a Usar:

En tu archivo `.env`, especifica qué prompts quieres ejecutar:

```env
# Usar todos los prompts
PROMPTS_TO_USE=01_resumen_ejecutivo.md,02_puntos_clave.md,03_analisis_detallado.md,04_extraccion_datos.md,05_propuestas_accion.md

# Usar solo algunos prompts
PROMPTS_TO_USE=01_resumen_ejecutivo.md,03_analisis_detallado.md

# Usar un solo prompt
PROMPTS_TO_USE=02_puntos_clave.md
```

### Crear Nuevos Prompts:

1. Crea un nuevo archivo `.md` en la carpeta `prompts/`
2. Usa formato Markdown con título principal usando `#`
3. Agrega tu prompt en el contenido
4. Incluye el nombre del archivo en `PROMPTS_TO_USE`

**Ejemplo:**
```markdown
# Mi Prompt Personalizado

Analiza el documento y enfócate en...
```

Guarda como `prompts/06_mi_prompt.md` y usa:
```env
PROMPTS_TO_USE=06_mi_prompt.md
```

## 📂 Estructura del Proyecto

```
├── main.py              # Script principal
├── requirements.txt     # Dependencias
├── .env.example        # Plantilla de configuración
├── .env                # Tu configuración (no compartir)
├── prompts/            # Carpeta de prompts
│   ├── 01_resumen_ejecutivo.md
│   ├── 02_puntos_clave.md
│   ├── 03_analisis_detallado.md
│   ├── 04_extraccion_datos.md
│   └── 05_propuestas_accion.md
└── output.md           # Resultados generados (se crea automáticamente)
```

## 🔧 Cómo Funciona

1. **Exporta Google Doc** → Convierte el Google Doc público a texto plano
2. **Ejecuta prompts** → Llama a Gemini con caché en memoria
3. **Guarda resultados** → Escribe análisis en archivo Markdown local

## 🐛 Problemas Comunes

**❌ "No se puede acceder al documento"**
- Asegúrate de que el Google Doc sea público o accesible para "Cualquier persona con el enlace"
- Verifica que la URL del Google Doc sea correcta

**❌ "API key inválida"**
- Verifica que tu Gemini API key sea correcta
- Asegúrate de que la API esté activa

**❌ "Error de encoding"**
- El archivo de salida se creará automáticamente en UTF-8
- Usa editores de texto modernos para leer el resultado

## 🔄 Cache

El script usa un cache simple en memoria para evitar llamadas repetitivas a Gemini API. El cache se vacía cada vez que ejecutas el script.

## 📄 Ejemplo de Uso

**Google Doc Público:** (compartido con "Cualquier persona con el enlace")
```
https://docs.google.com/document/d/12345abcde/edit
```

**Configuración .env:**
```env
SOURCE_DOC_URL=https://docs.google.com/document/d/12345abcde/edit
DESTINATION_FILE=analisis_documento.md
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-1.5-pro
```

**Ejecución:**
```bash
python main.py
```

**output.md:** (se crea automáticamente con el análisis completo)

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de modificarlo y adaptarlo a tus necesidades.