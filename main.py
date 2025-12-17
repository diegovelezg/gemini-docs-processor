#!/usr/bin/env python3
import os
import re
import hashlib
import requests
from typing import Dict, List
from dotenv import load_dotenv

# Gemini API
import google.generativeai as genai

# Cargar variables de entorno
load_dotenv()

# Configuración
SOURCE_DOC_URL = os.getenv("SOURCE_DOC_URL")
DESTINATION_FILE = os.getenv("DESTINATION_FILE", "output.md")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
PROMPTS_TO_USE = os.getenv("PROMPTS_TO_USE", "01_disonancias.md,02_complejidad.md,")

# Cache simple en memoria
cache: Dict[str, str] = {}

def load_prompts_from_files(prompt_files: str) -> List[Dict[str, str]]:
    """Carga prompts desde archivos Markdown"""
    prompts = []
    prompts_dir = "prompts"

    file_list = [f.strip() for f in prompt_files.split(',')]

    for filename in file_list:
        filepath = os.path.join(prompts_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    # Extraer título y contenido del prompt
                    lines = content.split('\n')
                    title = ""
                    prompt_content = content

                    for line in lines:
                        if line.startswith('#'):
                            title = line.replace('#', '').strip()
                            break

                    prompts.append({
                        'filename': filename,
                        'title': title,
                        'content': content
                    })
                    print(f"✅ Prompt cargado: {filename}")
                else:
                    print(f"⚠️  Prompt vacío: {filename}")

        except FileNotFoundError:
            print(f"❌ Archivo de prompt no encontrado: {filepath}")
        except Exception as e:
            print(f"❌ Error cargando prompt {filename}: {str(e)}")

    return prompts

def extract_doc_id_from_url(url: str) -> str:
    """Extrae el ID del documento de una URL de Google Docs"""
    pattern = r'/document/d/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"URL inválida de Google Docs: {url}")
    return match.group(1)

def get_public_google_docs_content(doc_url: str) -> tuple[str, str]:
    """Obtiene el contenido y título de un Google Doc público"""
    try:
        doc_id = extract_doc_id_from_url(doc_url)

        # Exportar como texto plano
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

        response = requests.get(export_url)
        response.raise_for_status()

        content = response.text.strip()

        # Intentar obtener el título del documento
        title = "Documento sin título"
        try:
            # Extraer título de las primeras líneas del contenido
            lines = content.split('\n')
            for line in lines[:5]:  # Revisar primeras 5 líneas
                line = line.strip()
                if line and len(line) > 5 and len(line) < 100:
                    # Heurística simple: primera línea significativa
                    if not line.startswith(('http', 'www', '1.', '2.', '3.', '•', '-', '*')):
                        title = line
                        break
        except:
            pass

        return content, title

    except Exception as e:
        print(f"❌ Error obteniendo Google Doc {doc_url}: {str(e)}")
        print("💡 Asegúrate de que el documento sea público o accesible para cualquiera con el enlace")
        raise

def write_to_markdown_file(file_path: str, text: str) -> None:
    """Escribe texto en un archivo Markdown (sobrescribe o crea)"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✅ Resultados guardados en {file_path}")
    except Exception as e:
        print(f"❌ Error escribiendo en archivo {file_path}: {str(e)}")
        raise

def get_cache_key(prompt: str, content: str) -> str:
    """Genera una clave única para caché"""
    combined = f"{prompt[:100]}_{content[:500]}"
    return hashlib.md5(combined.encode()).hexdigest()

def call_gemini(prompt: str, content: str) -> str:
    """Llama a Gemini API con caching"""
    # Verificar caché
    cache_key = get_cache_key(prompt, content)
    if cache_key in cache:
        print(f"📋 Usando respuesta cacheada para prompt")
        return cache[cache_key]

    try:
        # Para modelos preview, configurar la versión estable de la API
        if "preview" in GEMINI_MODEL:
            import os
            os.environ["GOOGLE_GENAI_API_VERSION"] = "v1"

        # Configurar Gemini
        genai.configure(api_key=GEMINI_API_KEY)

        # Para modelos preview, especificar configuración adicional
        if "preview" in GEMINI_MODEL:
            # Usar configuración específica para modelos preview
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                )
            )
        else:
            model = genai.GenerativeModel(GEMINI_MODEL)

        # Generar respuesta
        full_prompt = f"{prompt}\n\n--- DOCUMENTO ---\n{content}"
        response = model.generate_content(full_prompt)

        if response.text:
            # Guardar en caché
            cache[cache_key] = response.text
            print(f"🤖 Respuesta generada y cacheada")
            return response.text
        else:
            raise ValueError("La respuesta de Gemini está vacía")

    except Exception as e:
        print(f"❌ Error llamando a Gemini: {str(e)}")
        raise

def main():
    """Función principal"""
    print("🚀 Iniciando Gemini Markdown Processor...")

    try:
        # Validar configuración
        if not all([SOURCE_DOC_URL, GEMINI_API_KEY]):
            missing = []
            if not SOURCE_DOC_URL:
                missing.append("SOURCE_DOC_URL")
            if not GEMINI_API_KEY:
                missing.append("GEMINI_API_KEY")

            print(f"❌ Faltan variables de entorno: {', '.join(missing)}")
            print("Crea un archivo .env con las variables necesarias.")
            return

        print(f"🤖 Usando modelo: {GEMINI_MODEL}")

        # Leer Google Doc origen
        print(f"📄 Leyendo Google Doc origen: {SOURCE_DOC_URL}")
        source_content, doc_title = get_public_google_docs_content(SOURCE_DOC_URL)
        print(f"✅ Documento leído ({len(source_content)} caracteres)")
        print(f"📋 Título detectado: {doc_title}")

        # Cargar prompts desde archivos
        prompts = load_prompts_from_files(PROMPTS_TO_USE)
        if not prompts:
            print("❌ No se pudieron cargar los prompts. Verifica la configuración.")
            return

        print(f"\n🧠 Procesando {len(prompts)} prompts con Gemini...")
        results = []

        for i, prompt_data in enumerate(prompts, 1):
            print(f"\n📍 Prompt {i}/{len(prompts)}: {prompt_data['title']}")
            print(f"📝 Archivo: {prompt_data['filename']}")

            result = call_gemini(prompt_data['content'], source_content)
            results.append({
                "prompt_numero": i,
                "prompt_title": prompt_data['title'],
                "prompt_filename": prompt_data['filename'],
                "prompt": prompt_data['content'],
                "respuesta": result
            })

        # Formatear resultados
        formatted_output = format_results(results, doc_title, SOURCE_DOC_URL)

        # Escribir en archivo destino
        print(f"\n💾 Escribiendo resultados en: {DESTINATION_FILE}")
        write_to_markdown_file(DESTINATION_FILE, formatted_output)

        print(f"\n🎉 Procesamiento completado exitosamente!")
        print(f"📊 Se procesaron {len(prompts)} prompts")
        print(f"💾 Cache: {len(cache)} respuestas cacheadas")
        print(f"📁 Resultados guardados en: {DESTINATION_FILE}")

    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()

def format_results(results: List[Dict], doc_title: str = "Documento sin título", doc_url: str = "") -> str:
    """Formatea los resultados para el documento destino"""
    from datetime import datetime

    output = "=" * 60 + "\n"
    output += "📊 RESULTADOS DEL ANÁLISIS CON GEMINI\n"
    output += "=" * 60 + "\n"
    output += f"🕒 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    output += f"📄 Documento origen: {doc_title}\n"
    if doc_url:
        output += f"🔗 URL: {doc_url}\n"
    output += "\n"

    for result in results:
        output += f"🔹 PROMPT {result['prompt_numero']}: {result['prompt_title']}\n"
        output += f"📁 Archivo: {result['prompt_filename']}\n\n"
        output += f"💬 RESPUESTA:\n{result['respuesta']}\n"
        output += "-" * 60 + "\n\n"

    output += "\n✨ Fin del análisis\n"

    return output

if __name__ == "__main__":
    main()