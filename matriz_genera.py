#!/usr/bin/env python3
import os
import re
import csv
import glob
from typing import List, Tuple
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

INPUT_DIR = os.getenv("MATRIZ_GENERA_INPUT_DIR", "output/MATRIZ_TIC_POR_DIMENS-AGENTE")
TRACKING_FILE = os.getenv("MATRIZ_GENERA_TRACKING", "output/MATRIZ_GENERA_CSV/processed_files.csv")

MATRIX_PROMPTS = [
    "prompts/genera_matriz_dim_01.md",
    "prompts/genera_matriz_dim_02.md",
    "prompts/genera_matriz_dim_03.md",
    "prompts/genera_matriz_dim_04.md",
    "prompts/genera_matriz_dim_05.md",
    "prompts/genera_matriz_dim_06.md"
]

DIMENSION_NAMES = [
    "Práctica de Alta Demanda Cognitiva",
    "Integración Transversal de Competencias Digitales",
    "Soporte e Infraestructura (Ecosistema Digital)",
    "Ciudadanía y Ética Digital",
    "Valor y Expectativas (Instrumental vs. Adaptativo)",
    "Formación Técnica (EPT) y Transición Laboral"
]

client = None


def init_client():
    global client
    if not client:
        client = genai.Client(api_key=GEMINI_API_KEY)


def load_processed_files() -> set:
    """Carga la lista de archivos ya procesados desde el tracking file"""
    processed = set()

    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    processed.add(row['md_file'])

            print(f"📋 Cargados {len(processed)} archivos ya procesados")
        except Exception as e:
            print(f"⚠️  Error leyendo tracking: {e}")

    return processed


def save_processed_file(md_file: str, csv_file: str):
    """Guarda información del archivo procesado en el tracking"""
    try:
        # Crear directorio del tracking si no existe
        tracking_dir = os.path.dirname(TRACKING_FILE)
        if tracking_dir:
            os.makedirs(tracking_dir, exist_ok=True)

        file_exists = os.path.exists(TRACKING_FILE)

        with open(TRACKING_FILE, 'a', encoding='utf-8', newline='') as f:
            fieldnames = ['timestamp', 'md_file', 'csv_file']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            from datetime import datetime
            writer.writerow({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'md_file': md_file,
                'csv_file': csv_file
            })

        print(f"   💾 Tracking actualizado")

    except Exception as e:
        print(f"⚠️  Error guardando tracking: {e}")


def load_prompt(path: str) -> str:
    """Carga el contenido de un prompt"""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def create_cache(content: str):
    """Crea cache con el contenido del documento"""
    init_client()

    cache = client.caches.create(
        model=GEMINI_MODEL,
        config=types.CreateCachedContentConfig(
            display_name='Matriz_Genera',
            contents=[{
                'parts': [{'text': content}],
                'role': 'user'
            }],
            ttl="3600s",
        )
    )

    content_size_kb = len(content.encode('utf-8')) / 1024
    print(f"      ✅ Cache | {content_size_kb:.1f} KB")
    return cache


def cleanup_cache(cache):
    """Limpia cache"""
    if cache:
        try:
            client.caches.delete(name=cache.name)
        except:
            pass


def call_gemini(prompt: str, cache=None) -> Tuple[str, int, int, int]:
    """Llama a Gemini

    Returns:
        Tuple[text, total_input_tokens, cached_tokens, output_tokens]
    """
    init_client()

    if cache:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(cached_content=cache.name)
        )
    else:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

    if not resp.text:
        raise ValueError("Respuesta vacía")

    # Tokens
    in_t = cached_t = out_t = 0
    if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
        out_t = resp.usage_metadata.candidates_token_count or 0
        in_t = resp.usage_metadata.prompt_token_count or 0
        cached_t = getattr(resp.usage_metadata, 'cached_content_token_count', 0) or 0

    return resp.text, in_t, cached_t, out_t


def process_document(doc_path: str, prompts: List[str]) -> str:
    """Procesa un documento con todos los prompts de dimensiones
    Escribe resultados fila por fila en el CSV

    Returns:
        csv_path
    """
    print(f"\n{'='*80}")
    print(f"📄 {os.path.basename(doc_path)}")
    print(f"{'='*80}")

    # Leer contenido del documento
    with open(doc_path, 'r', encoding='utf-8') as f:
        doc_content = f.read()

    print(f"   📊 Tamaño: {len(doc_content):,} caracteres")

    # Inicializar archivo CSV (crea header)
    csv_path = init_csv_file(doc_path)

    # Crear cache con el documento completo (una sola vez)
    full_doc = f"DOCUMENTO A ANALIZAR:\n\n{doc_content}"
    cache = create_cache(full_doc)

    try:
        # Procesar cada dimensión
        for dim_idx, prompt_content in enumerate(prompts):
            dim_name = DIMENSION_NAMES[dim_idx]
            print(f"\n   📐 Dimensión {dim_idx + 1}: {dim_name}")

            # Construir prompt completo (el prompt ya viene cargado)
            full_prompt = f"""{prompt_content}

---

## DOCUMENTO A ANALIZAR

El documento ha sido proporcionado en el contexto cacheado.
"""

            try:
                result, in_t, cached_t, out_t = call_gemini(full_prompt, cache)

                # Crear diccionario de resultado
                row_data = {
                    'dimension': dim_idx + 1,
                    'dimension_name': dim_name,
                    'output': result,
                    'input_tokens': in_t,
                    'cached_tokens': cached_t,
                    'output_tokens': out_t
                }

                # Escribir fila inmediatamente al CSV
                append_csv_row(csv_path, row_data)

                print(f"      ✅ Fila {dim_idx + 1} guardada")

            except Exception as e:
                print(f"      ❌ Error: {e}")
                # Guardar error en CSV
                error_row = {
                    'dimension': dim_idx + 1,
                    'dimension_name': dim_name,
                    'output': f"ERROR: {str(e)}",
                    'input_tokens': 0,
                    'cached_tokens': 0,
                    'output_tokens': 0
                }
                append_csv_row(csv_path, error_row)

    finally:
        # Limpiar cache
        cleanup_cache(cache)

    print(f"\n   💾 CSV completo: {csv_path}")

    return csv_path


def clean_csv_text(text: str) -> str:
    """Limpia el texto para formato CSV válido
    - Elimina tags HTML
    - Escapa comillas dobles
    - Reemplaza saltos de línea por espacios
    """
    if not text:
        return ""

    # Eliminar tags HTML
    import re
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)

    # Escapar comillas dobles (reemplazar " por "")
    text = text.replace('"', '""')

    # Reemplazar saltos de línea por espacios
    text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')

    # Eliminar tabs
    text = text.replace('\t', ' ')

    # Eliminar caracteres especiales problemáticos para CSV
    text = text.replace('|', ' ').replace('—', '-')

    # Reducir espacios múltiples a uno solo
    text = re.sub(r' +', ' ', text)

    return text.strip()


def init_csv_file(doc_path: str) -> str:
    """Crea el archivo CSV con header y retorna la ruta"""
    doc_dir = os.path.dirname(doc_path)
    base_name = os.path.splitext(os.path.basename(doc_path))[0]
    csv_filename = f"{base_name}_matriz.csv"
    csv_path = os.path.join(doc_dir, csv_filename)

    fieldnames = ['dimension', 'dimension_name', 'output']

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    print(f"   📄 CSV inicializado: {csv_path}")
    return csv_path


def append_csv_row(csv_path: str, result: dict):
    """Agrega una fila al CSV existente"""
    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
        fieldnames = ['dimension', 'dimension_name', 'output']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow({
            'dimension': result['dimension'],
            'dimension_name': result['dimension_name'],
            'output': clean_csv_text(result['output'])
        })


def main():
    print("🚀 MATRIZ GENERA - Análisis por Dimensiones\n")

    if not GEMINI_API_KEY:
        print("❌ Falta GEMINI_API_KEY")
        return

    print(f"🤖 Modelo: {GEMINI_MODEL}")
    print(f"📂 Input: {INPUT_DIR}")
    print(f"📋 Tracking: {TRACKING_FILE}\n")

    # Verificar directorio de entrada
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Directorio de entrada no existe: {INPUT_DIR}")
        return

    # Cargar tracking de archivos ya procesados
    print("📋 Cargando tracking...")
    processed_files = load_processed_files()

    # Cargar prompts
    print("📝 Cargando prompts de dimensiones...")
    for i, prompt_path in enumerate(MATRIX_PROMPTS, 1):
        if not os.path.exists(prompt_path):
            print(f"   ❌ Prompt no encontrado: {prompt_path}")
            return
        print(f"   ✅ Dim {i}: {prompt_path}")
    print()

    # Buscar archivos MD
    md_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.md")))

    if not md_files:
        print(f"⚠️  No se encontraron archivos .md en {INPUT_DIR}")
        return

    # Filtrar archivos pendientes
    pending_files = [f for f in md_files if os.path.basename(f) not in processed_files]
    skipped = len(md_files) - len(pending_files)

    print(f"📄 Total MD: {len(md_files)}")
    print(f"✅ Ya procesados: {skipped}")
    print(f"⏳ Pendientes: {len(pending_files)}\n")

    if not pending_files:
        print("✨ Todos los archivos ya han sido procesados")
        return

    # Cargar prompts en memoria
    prompts = [load_prompt(p) for p in MATRIX_PROMPTS]

    # Procesar cada archivo pendiente
    ok = 0
    fail = 0

    for i, md_path in enumerate(pending_files, 1):
        print(f"\n{'#'*80}")
        print(f"# ARCHIVO [{i}/{len(pending_files)}]: {os.path.basename(md_path)}")
        print(f"{'#'*80}")

        try:
            csv_path = process_document(md_path, prompts)

            # Guardar en tracking
            save_processed_file(md_path, csv_path)
            ok += 1

        except Exception as e:
            print(f"❌ Error procesando {md_path}: {e}")
            import traceback
            traceback.print_exc()
            fail += 1

    # Resumen
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN")
    print(f"{'='*80}")
    print(f"✅ {ok} archivos nuevos procesados")
    print(f"⏭️  {skipped} archivos ya procesados (omitidos)")
    print(f"❌ {fail} archivos fallidos")
    print(f"📁 Input/Output: {INPUT_DIR}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
