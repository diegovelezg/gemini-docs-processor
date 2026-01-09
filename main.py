#!/usr/bin/env python3
import os
import re
import hashlib
import requests
import json
import time
import asyncio
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Gemini API - Nuevo SDK (google-genai)
from google import genai
from google.genai import types

# Procesamiento paralelo con AsyncIO
# AsyncIO permite procesar múltiples prompts en paralelo de forma eficiente
ASYNC_PROCESSING_AVAILABLE = True

# Cargar variables de entorno
load_dotenv()

# Configuración - Carpeta compartida de Google Drive
# Opción A: URL completo de la carpeta
# DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/ABC123_xyz..."

# Opción B: Solo el Folder ID (extraído del URL)
DRIVE_FOLDER_ID = "1jyc53AO7qEDnVcHBfmrOPbJLj3fFCrm8"  # Reemplazar con el ID real de tu carpeta compartida

# Configuración API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
PROMPTS_TO_USE = os.getenv("PROMPTS_TO_USE", "01_disonancias.md,02_complejidad.md, 03_clima.md, 04_hacks.md, 05_estratega.md")

# 🔧 MODO DE PROCESAMIENTO: CAMBIA AQUÍ 🔧
# Opciones: "normal" (secuencial), "parallel" (paralelo con AsyncIO - más rápido), o "batch" (Batch API - 50% más económico)
PROCESSING_MODE = "batch"  # "normal", "parallel" o "batch"

# Variables globales
client = None  # Cliente de Gemini
cached_content = None


def initialize_client():
    """Inicializa el cliente de Gemini"""
    global client
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client

def get_google_docs_from_shared_folder(folder_id: str) -> List[str]:
    """Obtiene todos los Google Docs de una carpeta compartida usando web scraping"""
    try:
        # Construir URL de la carpeta
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"

        print(f"🔍 Buscando Google Docs en carpeta: {folder_url}")

        # Headers para simular navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Hacer request a la carpeta
        response = requests.get(folder_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parsear HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar todos los links que apunten a Google Docs
        doc_urls = []

        # Método 1: Buscar en atributos data-id (más confiable)
        doc_elements = soup.find_all(['a', 'div'], {'data-id': True})
        for element in doc_elements:
            data_id = element.get('data-id', '')
            if data_id and len(data_id) > 10:  # Los IDs de documentos son largos
                doc_url = f"https://docs.google.com/document/d/{data_id}/edit"
                doc_urls.append(doc_url)

        # Método 2: Buscar en hrefs que contengan "/document/d/"
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/document/d/' in href and 'docs.google.com' in href:
                # Extraer el ID del documento
                import re
                match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', href)
                if match:
                    doc_id = match.group(1)
                    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
                    if doc_url not in doc_urls:
                        doc_urls.append(doc_url)

        # Método 3: Buscar en scripts del documento (fallback)
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                import re
                matches = re.findall(r'"[^"]*document/d/([a-zA-Z0-9_-]+)[^"]*"', script.string)
                for match in matches:
                    doc_url = f"https://docs.google.com/document/d/{match}/edit"
                    if doc_url not in doc_urls:
                        doc_urls.append(doc_url)

        # Remover duplicados y validar
        unique_docs = []
        seen_ids = set()

        for doc_url in doc_urls:
            # Extraer ID para evitar duplicados
            import re
            match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', doc_url)
            if match and match.group(1) not in seen_ids:
                seen_ids.add(match.group(1))
                unique_docs.append(doc_url)

        print(f"✅ Encontrados {len(unique_docs)} Google Docs en la carpeta")

        return unique_docs

    except Exception as e:
        print(f"❌ Error obteniendo Google Docs de la carpeta: {str(e)}")
        print("💡 Asegúrate de que la carpeta sea pública o accesible")
        return []

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

def get_real_document_title(doc_url: str, doc_id: str) -> str:
    """Obtiene el título real del documento scrapeando la página HTML"""
    try:
        # Hacer request a la página del Google Doc
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(doc_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parsear HTML con BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Método 1: Extraer del title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # Limpiar el título (remover "- Google Docs" o similar)
            title = re.sub(r'\s*-\s*Google\s+Docs.*$', '', title, flags=re.IGNORECASE)
            if title and len(title) > 1:
                return title

        # Método 2: Buscar en meta tags
        meta_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'title'})
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            if title and len(title) > 1:
                return title

        # Método 3: Buscar en JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                import json
                data = json.loads(script.string)
                if 'name' in data:
                    title = data['name'].strip()
                    if title and len(title) > 1:
                        return title
            except:
                continue

        # Si todo falla, lanzar excepción para que se use fallback
        raise ValueError("No se pudo encontrar el título del documento")

    except Exception as e:
        print(f"⚠️  No se pudo obtener título real: {str(e)}")
        # Fallback: usar ID del documento
        return f"Documento_{doc_id[:8]}"

def generate_safe_filename(title: str, doc_id: str) -> str:
    """Genera un filename seguro basado en el título real"""
    import re

    # Limpiar el título para usar como filename
    # Remover caracteres inválidos para nombres de archivo
    safe_filename = re.sub(r'[<>:"/\\|?*]', '', title)

    # Reemplazar espacios y caracteres problemáticos con guiones bajos
    safe_filename = re.sub(r'[\s\-\,\;\:\.\(\)\[\]\{\}\!\¡\?¿]+', '_', safe_filename)

    # Remover underscores duplicados
    safe_filename = re.sub(r'_+', '_', safe_filename)

    # Remover underscores al inicio y final
    safe_filename = safe_filename.strip('_')

    # Limitar longitud pero mantener palabras completas cuando sea posible
    max_length = 50
    if len(safe_filename) > max_length:
        # Cortar en límite de palabra más cercano
        truncated = safe_filename[:max_length]
        last_underscore = truncated.rfind('_')
        if last_underscore > max_length * 0.6:  # Si no corta demasiado corto
            safe_filename = truncated[:last_underscore]
        else:
            safe_filename = truncated

    # Verificar que el filename no esté vacío o sea demasiado corto
    if not safe_filename or len(safe_filename) < 3:
        # Fallback al doc_id
        safe_filename = f"doc_{doc_id[:8]}"

    # Asegurar que no sea solo caracteres especiales
    if re.match(r'^[_\-\.]+$', safe_filename):
        safe_filename = f"doc_{doc_id[:8]}"

    return safe_filename.lower()

def get_public_google_docs_content(doc_url: str) -> tuple[str, str, str]:
    """Obtiene el contenido, título y filename de un Google Doc público"""
    try:
        doc_id = extract_doc_id_from_url(doc_url)

        # Exportar como texto plano
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

        response = requests.get(export_url)
        response.raise_for_status()

        content = response.text.strip()

        # Obtener el título real del documento scrapeando la página HTML
        title = get_real_document_title(doc_url, doc_id)

        # Generar filename seguro basado en el título real
        safe_filename = generate_safe_filename(title, doc_id)
        filename = f"{safe_filename}.md"

        return content, title, filename

    except Exception as e:
        print(f"❌ Error obteniendo Google Doc {doc_url}: {str(e)}")
        print("💡 Asegúrate de que el documento sea público o accesible para cualquiera con el enlace")
        raise

def ensure_output_directory() -> str:
    """Asegura que la carpeta output exista y retorna su path"""
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

def write_to_markdown_file(file_path: str, text: str) -> None:
    """Escribe texto en un archivo Markdown (sobrescribe o crea)"""
    try:
        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✅ Resultados guardados en {file_path}")
    except Exception as e:
        print(f"❌ Error escribiendo en archivo {file_path}: {str(e)}")
        raise


def create_cached_content(document_text: str):
    """Crea contenido cacheado para reutilizar con múltiples prompts usando la nueva API"""
    try:
        initialize_client()

        # Crear contenido cacheado con el documento
        # Usar la nueva API: client.caches.create()
        cache = client.caches.create(
            model=GEMINI_MODEL,
            config=types.CreateCachedContentConfig(
                display_name='Document Analysis Context',
                contents=[{'parts': [{'text': document_text}]}],
                ttl="3600s",  # 1 hora de TTL
            )
        )

        print(f"✅ Contenido cacheado creado (ID: {cache.name})")

        # Acceder a los metadatos si están disponibles
        if hasattr(cache, 'usage_metadata'):
            print(f"💾 Tokens cacheados: {cache.usage_metadata.total_token_count:,}")
        else:
            print(f"💾 Contenido cacheado creado exitosamente")

        return cache

    except Exception as e:
        print(f"❌ Error creando contenido cacheado: {str(e)}")
        print("💡 El script continuará sin caching oficial")
        return None

def call_gemini_with_cache(prompt: str, cache=None) -> Tuple[str, int, int]:
    """Llama a Gemini API usando contenido cacheado con la nueva API"""
    try:
        initialize_client()

        if cache:
            # Usar contenido cacheado
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(cached_content=cache.name)
            )

            if response.text:
                # Extraer tokens de los metadatos
                input_tokens = 0
                output_tokens = 0

                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    output_tokens = response.usage_metadata.candidates_token_count
                    input_tokens = response.usage_metadata.prompt_token_count
                else:
                    output_tokens = len(response.text.split()) // 4
                    input_tokens = len(prompt.split()) // 4

                print(f"🤖 Respuesta generada con caching (Prompt: {input_tokens:,}, Output: {output_tokens:,} tokens)")
                return response.text, input_tokens, output_tokens
            else:
                raise ValueError("La respuesta de Gemini está vacía")
        else:
            # Fallback sin caching
            return call_gemini_without_cache(prompt)

    except Exception as e:
        print(f"❌ Error llamando a Gemini con caching: {str(e)}")
        print("🔄 Intentando sin caching...")
        return call_gemini_without_cache(prompt)

async def call_gemini_async(prompt: str, cache=None) -> Tuple[str, int, int]:
    """Llama a Gemini API de forma asíncrona usando contenido cacheado con la nueva API"""
    try:
        initialize_client()

        if cache:
            # Usar contenido cacheado
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(cached_content=cache.name)
            )
        else:
            # Sin caché
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

        if response.text:
            # Extraer tokens
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                output_tokens = response.usage_metadata.candidates_token_count
                input_tokens = response.usage_metadata.prompt_token_count
            else:
                output_tokens = len(response.text.split()) // 4
                input_tokens = len(prompt.split()) // 4

            cache_status = "con caching" if cache else "sin caching"
            print(f"🤖 Respuesta generada {cache_status} (Prompt: {input_tokens:,}, Output: {output_tokens:,} tokens)")
            return response.text, input_tokens, output_tokens
        else:
            raise ValueError("La respuesta de Gemini está vacía")

    except Exception as e:
        print(f"❌ Error en llamada asíncrona: {str(e)}")
        raise


def call_gemini_without_cache(prompt: str) -> Tuple[str, int, int]:
    """Fallback sin caching usando la nueva API"""
    try:
        initialize_client()

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if response.text:
            # Extraer tokens
            input_tokens = 0
            output_tokens = 0

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                output_tokens = response.usage_metadata.candidates_token_count
                input_tokens = response.usage_metadata.prompt_token_count
            else:
                input_tokens = len(prompt.split()) // 4
                output_tokens = len(response.text.split()) // 4

            print(f"🤖 Respuesta generada sin caching (Input: {input_tokens:,}, Output: {output_tokens:,} tokens)")
            return response.text, input_tokens, output_tokens
        else:
            raise ValueError("La respuesta de Gemini está vacía")

    except Exception as e:
        print(f"❌ Error en fallback: {str(e)}")
        raise

def cleanup_cached_content(cache):
    """Limpia el contenido cacheado usando la nueva API"""
    try:
        if cache:
            initialize_client()
            client.caches.delete(name=cache.name)
            print(f"🗑️  Contenido cacheado eliminado")
    except Exception as e:
        print(f"⚠️  Error limpiando caché: {str(e)}")

def create_batch_job(prompts_data: List[Dict], document_text: str):
    """Crea un batch job usando la API oficial de Gemini"""
    try:
        initialize_client()

        # Preparar inline requests para el batch
        inline_requests = []
        for prompt_data in prompts_data:
            full_prompt = f"{prompt_data['content']}\n\n--- DOCUMENTO ---\n{document_text}"
            request = {
                'contents': [{
                    'parts': [{'text': full_prompt}],
                    'role': 'user'
                }]
            }
            inline_requests.append(request)

        # Crear el batch job
        batch_job = client.batches.create(
            model=GEMINI_MODEL,
            src=inline_requests,
            config={
                'display_name': f"Document_Analysis_{int(time.time())}",
            },
        )

        print(f"🚀 Batch job creado: {batch_job.name}")
        print(f"📊 Prompts encolados: {len(prompts_data)}")
        print(f"⏳ El batch job tardará hasta 24 horas en completarse")

        return batch_job

    except Exception as e:
        print(f"❌ Error creando batch job: {str(e)}")
        raise

def monitor_batch_job(batch_job, timeout_minutes=30):
    """Monitorea el progreso del batch job hasta completarse"""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    print(f"⏳ Monitoreando batch job (timeout: {timeout_minutes} min)...")

    completed_states = {
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED'
    }

    while True:
        try:
            # Obtener estado actual
            current_job = client.batches.get(name=batch_job.name)

            # Verificar si terminó
            if current_job.state.name in completed_states:
                print(f"✅ Batch job completado con estado: {current_job.state.name}")
                if current_job.state.name == 'JOB_STATE_FAILED':
                    print(f"❌ Error: {current_job.error}")
                return current_job

            # Verificar timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise Exception(f"Batch job timeout después de {timeout_minutes} minutos")

            # Mostrar progreso
            print(f"⏳ Estado actual: {current_job.state.name} (elapsed: {int(elapsed)}s)")

            # Esperar antes de volver a verificar
            time.sleep(30)  # Esperar 30 segundos

        except Exception as e:
            print(f"❌ Error monitoreando batch job: {str(e)}")
            raise

def extract_batch_results(completed_job, prompts_data: List[Dict]):
    """Extrae los resultados del batch job completado"""
    try:
        results = []

        # Verificar si el job fue exitoso
        if completed_job.state.name != 'JOB_STATE_SUCCEEDED':
            raise Exception(f"Batch job no completó exitosamente: {completed_job.state.name}")

        # Obtener respuestas inline
        if hasattr(completed_job, 'dest') and hasattr(completed_job.dest, 'inlined_responses'):
            inline_responses = completed_job.dest.inlined_responses

            for i, inline_response in enumerate(inline_responses):
                if i >= len(prompts_data):
                    break

                if inline_response.response:
                    # Extraer texto de la respuesta
                    response_text = inline_response.response.text if hasattr(inline_response.response, 'text') else str(inline_response.response)

                    # Extraer tokens si están disponibles
                    input_tokens = 0
                    output_tokens = 0

                    if hasattr(inline_response.response, 'usage_metadata'):
                        metadata = inline_response.response.usage_metadata
                        input_tokens = getattr(metadata, 'prompt_token_count', 0)
                        output_tokens = getattr(metadata, 'candidates_token_count', 0)

                    results.append({
                        "prompt_numero": i + 1,
                        "prompt_title": prompts_data[i]["title"],
                        "prompt_filename": prompts_data[i]["filename"],
                        "prompt": prompts_data[i]["content"],
                        "respuesta": response_text,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "error": None,
                        "cache_usado": False
                    })
                else:
                    # Error en la respuesta
                    error_msg = inline_response.error if hasattr(inline_response, 'error') else "No se obtuvo respuesta"
                    results.append({
                        "prompt_numero": i + 1,
                        "prompt_title": prompts_data[i]["title"],
                        "prompt_filename": prompts_data[i]["filename"],
                        "prompt": prompts_data[i]["content"],
                        "respuesta": "",
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "error": error_msg,
                        "cache_usado": False
                    })
        else:
            raise Exception("No se encontraron respuestas inline en el batch job")

        return results

    except Exception as e:
        print(f"❌ Error extrayendo resultados: {str(e)}")
        raise

def process_prompts_batch(prompts_data: List[Dict], document_text: str):
    """Procesa prompts usando Batch API oficial"""
    try:
        print(f"🚀 Usando BATCH API (50% más económico, tiempo de espera: hasta 24 horas)")

        # Crear batch job
        batch_job = create_batch_job(prompts_data, document_text)

        # Monitorear y obtener resultados (con timeout de 30 min para demo)
        print(f"⚠️  NOTA: Para producción, considera aumentar el timeout o implementar polling asíncrono")
        completed_job = monitor_batch_job(batch_job, timeout_minutes=30)

        # Extraer resultados
        results = extract_batch_results(completed_job, prompts_data)

        return results

    except Exception as e:
        print(f"❌ Error en batch processing: {str(e)}")
        print("🔄 Fallback a modo normal con caché...")
        return process_prompts_normal(prompts_data, document_text, None)

async def process_single_prompt_async(prompt_data: Dict, cache=None) -> Dict:
    """Procesa un solo prompt de forma asíncrona"""
    try:
        if cache:
            # Con caché oficial: solo enviar el prompt
            full_prompt = f"{prompt_data['content']}\n\n--- ANALIZAR EL DOCUMENTO CACHEADO ---"
        else:
            # Sin caché: enviar prompt + documento completo
            full_prompt = f"{prompt_data['content']}\n\n--- DOCUMENTO ---\n{prompt_data.get('document_text', '')}"

        result, input_tokens, output_tokens = await call_gemini_async(full_prompt, cache)

        return {
            "prompt_numero": prompt_data.get('index', 0) + 1,
            "prompt_title": prompt_data["title"],
            "prompt_filename": prompt_data["filename"],
            "prompt": prompt_data["content"],
            "respuesta": result,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "error": None,
            "cache_usado": cache is not None
        }
    except Exception as e:
        return {
            "prompt_numero": prompt_data.get('index', 0) + 1,
            "prompt_title": prompt_data["title"],
            "prompt_filename": prompt_data["filename"],
            "prompt": prompt_data["content"],
            "respuesta": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "error": str(e),
            "cache_usado": False
        }


async def process_prompts_parallel_async(prompts_data: List[Dict], document_text: str, cache=None):
    """Procesa múltiples prompts en paralelo usando AsyncIO"""
    print(f"🚀 Procesando {len(prompts_data)} prompts en paralelo con AsyncIO...")

    # Preparar prompts con el documento
    enriched_prompts = []
    for i, prompt_data in enumerate(prompts_data):
        prompt_copy = prompt_data.copy()
        prompt_copy['index'] = i
        if not cache:
            prompt_copy['document_text'] = document_text
        enriched_prompts.append(prompt_copy)

    # Crear tareas asíncronas para procesar todos los prompts en paralelo
    tasks = [
        process_single_prompt_async(prompt_data, cache)
        for prompt_data in enriched_prompts
    ]

    # Ejecutar todas las tareas en paralelo y esperar resultados
    results = await asyncio.gather(*tasks, return_exceptions=False)

    print(f"✅ Todos los prompts procesados en paralelo")
    return results


def process_prompts_parallel(prompts_data: List[Dict], document_text: str, cache=None):
    """Wrapper síncrono para procesar prompts en paralelo"""
    try:
        # Ejecutar la función asíncrona
        results = asyncio.run(process_prompts_parallel_async(prompts_data, document_text, cache))
        return results
    except Exception as e:
        print(f"❌ Error en procesamiento paralelo: {str(e)}")
        print("🔄 Fallback a modo normal...")
        return process_prompts_normal(prompts_data, document_text, cache)

def process_prompts_normal(prompts_data: List[Dict], document_text: str, cache=None):
    """Procesa prompts usando API normal con caché oficial optimizado"""
    results = []

    for i, prompt_data in enumerate(prompts_data):
        print(f"\n📍 Prompt {i+1}/{len(prompts_data)}: {prompt_data['title']}")
        print(f"📝 Archivo: {prompt_data['filename']}")

        if cache:
            # ✅ Con caché oficial: solo enviar el prompt (documento ya cacheado)
            full_prompt = f"{prompt_data['content']}\n\n--- ANALIZAR EL DOCUMENTO CACHEADO ---"
            print(f"🚀 Usando caché oficial (documento pre-cargado)")
        else:
            # ❌ Fallback sin caché: enviar prompt + documento completo
            full_prompt = f"{prompt_data['content']}\n\n--- DOCUMENTO ---\n{document_text}"
            print(f"⚠️  Modo fallback (sin caché)")

        result, input_tokens, output_tokens = call_gemini_with_cache(full_prompt, cache)
        results.append({
            "prompt_numero": i + 1,
            "prompt_title": prompt_data["title"],
            "prompt_filename": prompt_data["filename"],
            "prompt": prompt_data["content"],
            "respuesta": result,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "error": None,
            "cache_usado": cache is not None
        })

    return results

def process_single_document(doc_url: str, doc_index: int, total_docs: int, prompts: List[Dict], output_dir: str):
    """Procesa un solo documento y genera su archivo .md"""
    print(f"\n📄 [{doc_index+1}/{total_docs}] Procesando: {doc_url}")

    try:
        # Leer Google Doc
        source_content, doc_title, doc_filename = get_public_google_docs_content(doc_url)
        print(f"✅ Documento leído ({len(source_content)} caracteres)")
        print(f"📋 Título: {doc_title}")
        print(f"📁 Filename: {doc_filename}")

        # Crear caché para este documento
        print(f"🚀 Creando caché del documento...")
        cache = create_cached_content(source_content)

        # Procesar prompts
        print(f"🧠 Procesando {len(prompts)} prompts...")
        if PROCESSING_MODE == "batch":
            print(f"⚡ Usando BATCH API (50% más económico)")
            results = process_prompts_batch(prompts, source_content)
        elif PROCESSING_MODE == "parallel":
            print(f"⚡ Usando MODO PARALELO (AsyncIO)")
            results = process_prompts_parallel(prompts, source_content, cache)
        else:
            print(f"📝 Usando MODO NORMAL (secuencial)")
            results = process_prompts_normal(prompts, source_content, cache)

        # Formatear resultados
        formatted_output = format_results(results, doc_title, doc_url)

        # Guardar archivo individual
        output_path = os.path.join(output_dir, doc_filename)
        write_to_markdown_file(output_path, formatted_output)

        print(f"✅ Documento {doc_index+1} completado: {output_path}")

        # Limpiar caché
        if cache:
            cleanup_cached_content(cache)

        return output_path

    except Exception as e:
        print(f"❌ Error procesando documento {doc_index+1}: {str(e)}")
        # Limpiar caché en caso de error
        if 'cache' in locals() and cache:
            cleanup_cached_content(cache)
        return None

def load_processed_documents() -> set:
    """Carga la lista de documentos ya procesados desde el archivo de tracking"""
    tracking_file = os.path.join("output", "processed_documents.csv")
    processed_docs = set()

    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:  # Saltar header
                    parts = line.strip().split(',')
                    if len(parts) >= 1:
                        doc_id = parts[0].strip()
                        if doc_id:
                            processed_docs.add(doc_id)
            print(f"📋 Cargados {len(processed_docs)} documentos ya procesados")
        except Exception as e:
            print(f"⚠️  Error leyendo archivo de tracking: {str(e)}")

    return processed_docs

def save_processed_document(doc_url: str, doc_title: str, output_file: str, tokens_used: int):
    """Guarda información del documento procesado en el archivo de tracking"""
    tracking_file = os.path.join("output", "processed_documents.csv")

    try:
        # Extraer ID del documento
        import re
        match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', doc_url)
        doc_id = match.group(1) if match else doc_url

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Verificar si ya existe el archivo y encabezado
        file_exists = os.path.exists(tracking_file)

        with open(tracking_file, 'a', encoding='utf-8') as f:
            if not file_exists:
                # Escribir header
                f.write("doc_id,doc_url,doc_title,output_file,tokens_used,timestamp\n")

            # Escribir datos del documento
            f.write(f"{doc_id},{doc_url},{doc_title},{output_file},{tokens_used},{timestamp}\n")

        print(f"💾 Documento guardado en tracking: {doc_title}")

    except Exception as e:
        print(f"⚠️  Error guardando tracking: {str(e)}")

def filter_unprocessed_documents(all_docs: List[str], processed_docs: set) -> List[str]:
    """Filtra documentos que no han sido procesados aún"""
    unprocessed = []
    processed_count = 0

    for doc_url in all_docs:
        # Extraer ID para comparación
        import re
        match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', doc_url)
        doc_id = match.group(1) if match else doc_url

        if doc_id not in processed_docs:
            unprocessed.append(doc_url)
        else:
            processed_count += 1

    print(f"📊 Documentos filtrados:")
    print(f"  ✅ Ya procesados: {processed_count}")
    print(f"  ⏳ Pendientes: {len(unprocessed)}")

    return unprocessed

def show_tracking_summary():
    """Muestra un resumen del procesamiento actual"""
    tracking_file = os.path.join("output", "processed_documents.csv")

    if not os.path.exists(tracking_file):
        print("📋 No hay documentos procesados aún")
        return

    try:
        with open(tracking_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"\n" + "="*60)
        print(f"📊 RESUMEN DE PROCESAMIENTO")
        print(f"="*60)
        print(f"📚 Documentos procesados: {len(lines) - 1}")
        print(f"📁 Archivo de tracking: {tracking_file}")

        if len(lines) > 1:
            # Último procesado
            last_line = lines[-1].strip().split(',')
            if len(last_line) >= 4:
                print(f"✅ Último documento: {last_line[2]}")
                print(f"📁 Salida: {last_line[3]}")
                print(f"⏰ Fecha: {last_line[5] if len(last_line) > 5 else 'N/A'}")

        print(f"="*60)

    except Exception as e:
        print(f"⚠️  Error leyendo resumen: {str(e)}")

def main():
    """Función principal"""
    print("🚀 Iniciando Gemini Markdown Processor...")

    try:
        # Validar configuración
        if not GEMINI_API_KEY:
            print("❌ Falta GEMINI_API_KEY")
            print("Crea un archivo .env con la variable necesaria.")
            return

        # Validar que el folder ID no sea el ejemplo
        if not DRIVE_FOLDER_ID or "ABC123_xyz" in DRIVE_FOLDER_ID:
            print("❌ DRIVE_FOLDER_ID está configurado con el ID de ejemplo")
            print("Reemplaza con el ID real de tu carpeta compartida de Google Drive.")
            print("💡 El ID se extrae del URL: https://drive.google.com/drive/folders/TU_ID_AQUI")
            return

        print(f"🤖 Usando modelo: {GEMINI_MODEL}")
        if PROCESSING_MODE == "batch":
            mode_name = "BATCH API (50% más económico)"
        elif PROCESSING_MODE == "parallel":
            mode_name = "PARALELO (AsyncIO)"
        else:
            mode_name = "NORMAL (secuencial)"
        print(f"⚡ Modo de procesamiento: {mode_name}")

        # Obtener documentos automáticamente de la carpeta compartida
        print(f"📂 Obteniendo Google Docs de la carpeta compartida...")
        all_docs = get_google_docs_from_shared_folder(DRIVE_FOLDER_ID)

        if not all_docs:
            print("❌ No se encontraron Google Docs en la carpeta compartida")
            print("💡 Verifica que:")
            print("   - La carpeta compartida sea pública")
            print("   - La carpeta contenga Google Docs")
            print("   - El DRIVE_FOLDER_ID sea correcto")
            return

        print(f"📚 Encontrados {len(all_docs)} documentos totales en la carpeta")

        # Cargar documentos ya procesados y filtrar pendientes
        processed_docs = load_processed_documents()
        source_docs = filter_unprocessed_documents(all_docs, processed_docs)

        if not source_docs:
            print(f"🎉 Todos los documentos ya han sido procesados!")
            show_tracking_summary()
            return

        print(f"📈 Se procesarán {len(source_docs)} documentos pendientes")

        # Cargar prompts una sola vez
        prompts = load_prompts_from_files(PROMPTS_TO_USE)
        if not prompts:
            print("❌ No se pudieron cargar los prompts. Verifica la configuración.")
            return

        print(f"✅ {len(prompts)} prompts cargados")

        # Asegurar carpeta de salida
        output_dir = ensure_output_directory()

        # Procesar documentos uno a uno con confirmación
        successful_docs = []
        failed_docs = []

        for i, doc_url in enumerate(source_docs):
            print(f"\n" + "="*50)
            print(f"📄 [{i+1}/{len(source_docs)}] ¿Procesar siguiente documento?")
            print(f"🔗 URL: {doc_url}")

            # Pausar para confirmación (excepto el primero)
            if i > 0:
                try:
                    user_input = input("¿Continuar? [S/n/quit]: ").strip().lower()
                    if user_input in ['n', 'no', 'quit', 'q']:
                        print("⏹️  Procesamiento detenido por el usuario")
                        break
                except KeyboardInterrupt:
                    print("\n⏹️  Procesamiento detenido por el usuario")
                    break

            # Procesar documento
            print(f"🚀 Procesando documento {i+1}...")
            output_file = process_single_document(doc_url, i, len(source_docs), prompts, output_dir)

            if output_file:
                successful_docs.append(output_file)

                # Calcular tokens usados aproximados (basado en longitud del documento)
                try:
                    source_content, doc_title, _ = get_public_google_docs_content(doc_url)
                    tokens_used = len(source_content) // 4  # Estimación simple
                    save_processed_document(doc_url, doc_title, output_file, tokens_used)
                except Exception as e:
                    print(f"⚠️  Error guardando tracking: {str(e)}")
            else:
                failed_docs.append(doc_url)
                print(f"❌ Documento fallido: {doc_url}")

        # Mostrar resumen final y tracking
        show_tracking_summary()
        print(f"\n" + "="*60)
        print(f"📊 SESIÓN COMPLETADA")
        print(f"="*60)
        print(f"📚 Documentos procesados en esta sesión: {len(successful_docs)}")
        print(f"❌ Documentos fallidos en esta sesión: {len(failed_docs)}")
        print(f"📁 Documentos pendientes: {len(source_docs) - len(successful_docs)}")
        print(f"\n💡 Puedes ejecutar el script nuevamente para continuar desde donde quedó")
        print(f"🔗 Carpeta origen: https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}")

    except Exception as e:
        print(f"\n❌ Error fatal: {str(e)}")
        import traceback
        traceback.print_exc()

def format_results(results: List[Dict], doc_title: str = "Documento sin título", doc_url: str = "") -> str:
    """Formatea los resultados para el documento destino"""
    from datetime import datetime

    # Calcular totales de tokens
    total_input_tokens = sum(r.get('input_tokens', 0) for r in results)
    total_output_tokens = sum(r.get('output_tokens', 0) for r in results)
    total_all_tokens = sum(r.get('total_tokens', 0) for r in results)

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
        output += f"📊 Tokens del prompt: Input: {result.get('input_tokens', 0):,} | Output: {result.get('output_tokens', 0):,} | Total: {result.get('total_tokens', 0):,}\n"
        output += "-" * 60 + "\n\n"

    # Agregar resumen de tokens al final
    output += "=" * 60 + "\n"
    output += "📊 ESTADÍSTICAS DE USO DE TOKENS\n"
    output += "=" * 60 + "\n"
    output += f"🔢 Total Input Tokens: {total_input_tokens:,}\n"
    output += f"🔤 Total Output Tokens: {total_output_tokens:,}\n"
    output += f"🎯 Total General: {total_all_tokens:,}\n"
    output += f"📈 Promedio por prompt: Input: {total_input_tokens/len(results):.0f} | Output: {total_output_tokens/len(results):.0f} | Total: {total_all_tokens/len(results):.0f}\n"
    output += "\n"

    output += "\n✨ Fin del análisis\n"

    return output

if __name__ == "__main__":
    main()