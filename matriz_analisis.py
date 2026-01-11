#!/usr/bin/env python3
import os
import re
import requests
from typing import List, Tuple
from dotenv import load_dotenv
from bs4 import BeautifulSoup

from google import genai
from google.genai import types

load_dotenv()

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1kwoGjcvX39sM1at1KW5Rhx9ZfADCqBYy")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

DIMENSION_PROMPTS = [
    "prompts/unificado_dim_01.md",
    "prompts/unificado_dim_02.md",
    "prompts/unificado_dim_03.md",
    "prompts/unificado_dim_04.md"
]
ESCUELAS_FILE = "prompts/06_matriz_escuelas.md"

client = None


def init_client():
    global client
    if not client:
        client = genai.Client(api_key=GEMINI_API_KEY)


def load_prompt(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def load_escuelas() -> List[str]:
    with open(ESCUELAS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    prefixes = []
    for line in lines:
        m = re.search(r'"([^"]+)"', line)
        if m:
            prefixes.append(m.group(1))

    print(f"✅ {len(prefixes)} escuelas")
    return prefixes


def scrape_folder(folder_id: str, depth: int = 0) -> List[str]:
    """
    Scrapea carpeta de Drive.
    Nivel 0: asume todo son subcarpetas
    Nivel 1+: asume todo son documentos
    """
    indent = "  " * depth
    url = f"https://drive.google.com/drive/folders/{folder_id}"

    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, 'html.parser')

        # Extraer todos los data-id
        ids = set()
        for el in soup.find_all(['div', 'a'], {'data-id': True}):
            did = el.get('data-id')
            if did and len(did) > 10:
                ids.add(did)

        print(f"{indent}📁 {len(ids)} elementos")

        # Nivel 0: son subcarpetas, entrar recursivamente
        if depth == 0:
            all_docs = []
            for fid in ids:
                docs = scrape_folder(fid, depth + 1)
                all_docs.extend(docs)

            # Deduplicar
            seen = set()
            unique = []
            for d in all_docs:
                if d not in seen:
                    seen.add(d)
                    unique.append(d)

            print(f"\n📊 TOTAL: {len(unique)} documentos\n")
            return unique

        # Nivel 1+: son documentos, retornar URLs
        else:
            urls = [f"https://docs.google.com/document/d/{did}/edit" for did in ids]
            return urls

    except Exception as e:
        print(f"{indent}❌ {e}")
        return []


def get_title(doc_url: str) -> str:
    """Obtiene título de documento"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(doc_url, headers=headers, timeout=10)

        soup = BeautifulSoup(r.text, 'html.parser')
        title_tag = soup.find('title')

        if title_tag:
            title = title_tag.get_text().strip()
            title = re.sub(r'\s*-\s*Google\s+Docs.*$', '', title, flags=re.IGNORECASE)
            if title:
                return title

        # Fallback: extraer ID
        m = re.search(r'/document/d/([a-zA-Z0-9_-]+)', doc_url)
        return f"Doc_{m.group(1)[:8]}" if m else "Unknown"

    except:
        return "Unknown"


def get_content(doc_url: str) -> str:
    """Obtiene contenido de documento"""
    m = re.search(r'/document/d/([a-zA-Z0-9_-]+)', doc_url)
    if not m:
        raise ValueError(f"URL inválida: {doc_url}")

    doc_id = m.group(1)
    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

    r = requests.get(export_url)
    r.raise_for_status()

    return r.text.strip()


def filter_by_prefix(docs: List[str], prefix: str) -> List[str]:
    """Filtra por prefijo (case insensitive)"""
    filtered = []
    prefix_lower = prefix.lower()

    for url in docs:
        title = get_title(url)
        if prefix_lower in title.lower():
            filtered.append(url)

    print(f"   ✓ {len(filtered)} docs para '{prefix}'")
    return filtered


def create_cache(content: str):
    """Crea cache"""
    init_client()

    cache = client.caches.create(
        model=GEMINI_MODEL,
        config=types.CreateCachedContentConfig(
            display_name='Matriz',
            contents=[{
                'parts': [{'text': content}],
                'role': 'user'
            }],
            ttl="3600s",
        )
    )

    content_size_kb = len(content.encode('utf-8')) / 1024
    print(f"   ✅ Cache | {content_size_kb:.1f} KB")
    return cache


def cleanup_cache(cache):
    """Limpia cache"""
    if cache:
        try:
            client.caches.delete(name=cache.name)
        except:
            pass


def call_gemini(prompt: str, cache=None) -> Tuple[str, int, int]:
    """Llama a Gemini"""
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
    in_t = out_t = 0
    if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
        out_t = resp.usage_metadata.candidates_token_count
        in_t = resp.usage_metadata.prompt_token_count

    return resp.text, in_t, out_t


def process_escuela(escuela: str, dim_prompts: List[str], all_docs: List[str], out_dir: str):
    """Procesa todos los documentos de una escuela con todas las dimensiones"""

    print(f"\n{'='*80}")
    print(f"📊 {escuela}")
    print(f"{'='*80}")

    # Filtrar docs de esta escuela
    escuela_docs = filter_by_prefix(all_docs, escuela)

    if not escuela_docs:
        print(f"⚠️  Sin docs")
        return None

    # Crear UN SOLO archivo de salida para esta escuela
    safe_name = escuela.replace('_', '').replace('-', '').lower()
    filename = f"{safe_name}_matriz_completa.md"
    filepath = os.path.join(out_dir, filename)

    # Header del archivo
    from datetime import datetime
    header = "=" * 80 + "\n"
    header += "📊 MATRIZ DE ANÁLISIS - ESCUELA\n"
    header += "=" * 80 + "\n"
    header += f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    header += f"🏫 Escuela: {escuela}\n"
    header += f"📄 Docs: {len(escuela_docs)}\n"
    header += f"📐 Dimensiones: 4\n"
    header += "\n" + "=" * 80 + "\n\n"

    # Inicializar archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(header)

    # Token counters por dimensión
    tokens_por_dim = [[0, 0] for _ in range(4)]  # [in, out] para cada dimensión

    # Procesar cada documento
    for doc_idx, doc_url in enumerate(escuela_docs, 1):
        title = get_title(doc_url)
        content = get_content(doc_url)

        print(f"\n   📖 [{doc_idx}/{len(escuela_docs)}] {title} ({len(content):,} chars)")

        # Crear cache con este documento (se reusa para las 4 dimensiones)
        full_doc = f"DOCUMENTO: {title}\nURL: {doc_url}\n\n{content}"
        cache = create_cache(full_doc)

        # Header del documento en el MD
        doc_header = f"\n{'#'*80}\n"
        doc_header += f"# DOCUMENTO {doc_idx}: {title}\n"
        doc_header += f"{'#'*80}\n\n"

        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(doc_header)

        # Aplicar los 4 prompts al mismo documento (reutilizando cache)
        for dim_idx, dim_prompt in enumerate(dim_prompts):
            full_prompt = f"{dim_prompt}\n\n--- DOCUMENTO A ANALIZAR ---\n{full_doc}"

            try:
                result, in_t, out_t = call_gemini(full_prompt, cache)

                # Formatear resultado
                formatted = f"\n{'='*80}\n"
                formatted += f"📐 DIMENSIÓN {dim_idx + 1}\n"
                formatted += f"{'='*80}\n\n"
                formatted += result
                formatted += f"\n{'='*80}\n\n"

                # Agregar al archivo
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(formatted)

                # Acumular tokens
                tokens_por_dim[dim_idx][0] += in_t
                tokens_por_dim[dim_idx][1] += out_t

                print(f"      ✅ Dim {dim_idx + 1}: IN={in_t:,} OUT={out_t:,}")

            except Exception as e:
                print(f"      ❌ Dim {dim_idx + 1}: {e}")
                error_msg = f"\n{'='*80}\n❌ ERROR EN DIMENSIÓN {dim_idx + 1}: {e}\n{'='*80}\n\n"
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(error_msg)

        # Limpiar cache después de procesar las 4 dimensiones
        cleanup_cache(cache)
        print(f"      🗑️  Cache limpiado")

    # Footer con resumen de tokens
    footer = "\n" + "=" * 80 + "\n"
    footer += "📊 RESUMEN DE TOKENS POR DIMENSIÓN\n"
    footer += "=" * 80 + "\n"

    for dim_idx in range(4):
        footer += f"Dim {dim_idx + 1}: IN={tokens_por_dim[dim_idx][0]:,} OUT={tokens_por_dim[dim_idx][1]:,} TOTAL={tokens_por_dim[dim_idx][0] + tokens_por_dim[dim_idx][1]:,}\n"

    total_in = sum(t[0] for t in tokens_por_dim)
    total_out = sum(t[1] for t in tokens_por_dim)

    footer += "-" * 80 + "\n"
    footer += f"TOTAL: IN={total_in:,} OUT={total_out:,} TOTAL={total_in + total_out:,}\n"
    footer += "=" * 80 + "\n"
    footer += "✨ Fin\n"
    footer += "=" * 80 + "\n"

    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(footer)

    print(f"\n   ✅ {filepath}")
    print(f"   🤖 Total: IN={total_in:,} OUT={total_out:,}")

    return filepath


def main():
    print("🚀 MATRIZ DE ANÁLISIS\n")

    if not GEMINI_API_KEY:
        print("❌ Falta GEMINI_API_KEY")
        return

    print(f"🤖 {GEMINI_MODEL}\n")

    # Cargar prompts
    print("📝 Prompts unificados...")
    dim_prompts = [load_prompt(f) for f in DIMENSION_PROMPTS]
    print("✅ Prompts cargados\n")

    # Escuelas
    escuelas = load_escuelas()

    # Obtener docs
    print("📂 Obteniendo documentos...")
    all_docs = scrape_folder(DRIVE_FOLDER_ID)

    if not all_docs:
        print("❌ Sin documentos")
        return

    # Output
    out_dir = "output/matriz"
    os.makedirs(out_dir, exist_ok=True)

    # Procesar
    print(f"🎯 {len(escuelas)} escuelas × {len(dim_prompts)} dimensiones\n")

    ok = 0
    fail = 0

    for i, esc in enumerate(escuelas, 1):
        print(f"\n{'#'*80}")
        print(f"# ESCUELA [{i}/{len(escuelas)}]: {esc}")
        print(f"{'#'*80}")

        try:
            result = process_escuela(esc, dim_prompts, all_docs, out_dir)
            if result:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"❌ Error procesando {esc}: {e}")
            fail += 1

    # Resumen
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN")
    print(f"{'='*80}")
    print(f"✅ {ok} escuelas procesadas")
    print(f"❌ {fail} escuelas fallidas")
    print(f"📁 {out_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
