"""
Destilador y Resumidor Local de Documentos para el Chat de Nova (Sin API de Anthropic).

Recibe el archivo o los archivos que el usuario pasa por el chat:
- Si el documento es corto (<= 1 trozo), entrega directamente el texto limpio (0 llamadas).
- Si el documento es largo y se pide --ollama, lo resume en local con Ollama (0 tokens de nube).
- Si no se pide --ollama, extrae los encabezados, tablas y primeros fragmentos clave a 0 tokens
  para que Nova lo lea al instante en el chat sin gastar en imagenes ni APIs de pago.

Uso directo con los archivos pasados por el chat:
    python resumir.py doc1.pdf [doc2.docx tabla.xlsx ...]
    python resumir.py doc1.pdf --ollama --vinetas 8
"""

import argparse
import json
import os
import urllib.request
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # conversor y ollama_comun viven al lado
from conversor import SALIDA_POR_DEFECTO, convertir, expandir_entradas
from ollama_comun import ensure_ollama_service

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


def _modelo_nova(clave: str, defecto: str) -> str:
    """Modelo local de este equipo (perfil_usuario.json -> scripts/nova_modelos.json -> defecto)."""
    try:
        from ollama_comun import modelo_nova
        return modelo_nova(clave)
    except Exception:
        return defecto


MODELO_LOCAL = _modelo_nova("coder", "qwen3.5:9b")
PROMPT_TROZO = "Resume este fragmento en maximo 3 lineas, solo hechos y datos clave, sin introducciones:\n\n{texto}"
PROMPT_FINAL = (
    "Estos son resumenes parciales del documento '{archivo}'. "
    "Escribe un resumen ejecutivo en maximo {vinetas} vinetas claras, sin introduccion:\n\n{texto}"
)


def preguntar_ollama(
    prompt: str, max_tokens: int = 300, modelo: str = MODELO_LOCAL
) -> str:
    """Qwen local via generar_qwen (08/11): think=False (si no, qwen3.5 gasta los tokens pensando y devuelve vacio),
    num_ctx explicito y keep_alive (antes keep_alive=0 recargaba el modelo en cada trozo)."""
    from ollama_comun import generar_qwen

    ensure_ollama_service()
    texto, cortado = generar_qwen(prompt, modelo, num_predict=max_tokens, num_ctx=8192, temperatura=0.1, timeout=300)
    return texto.strip() + (" [...]" if cortado else "")


def destilado_instantaneo(doc: dict) -> str:
    """Entrega estructura y contenido clave a 0 tokens y 0 espera cuando no se usa Ollama."""
    chunks = doc.get("chunks", [])
    encabezado = (
        f"=== DOCUMENTO: {doc['archivo']} ({doc['tipo'].upper()}) ===\n"
        f"Secciones/Paginas: {doc['secciones']} | Tokens totales limpios: ~{doc['tokens_estimados']} | "
        f"Trozos: {len(chunks)} | TXT: {doc.get('txt_limpio', '')}\n"
    )
    if not chunks:
        return encabezado + "(Documento vacio)"
    if len(chunks) == 1:
        return encabezado + "\n" + chunks[0]["texto"]
    vista_previa = chunks[0]["texto"][:2500]
    return (
        f'{encabezado}\n--- Trozo 0 de {len(chunks) - 1} (Usa `python conversor.py "{doc.get("ruta_original", doc["archivo"])}" --chunk N` para leer otro trozo) ---\n'
        f"{vista_previa}"
    )


def resumir_local(
    doc: dict, vinetas: int, salida: Path, usar_ollama: bool = False
) -> str:
    if not usar_ollama:
        return destilado_instantaneo(doc)

    cache = salida / f"{Path(doc['archivo']).stem}.resumen.json"
    if cache.exists():
        previo = json.loads(cache.read_text(encoding="utf-8"))
        if previo.get("hash") == doc["hash"] and previo.get("vinetas") == vinetas:
            return previo["resumen"]

    chunks = doc["chunks"]
    if len(chunks) == 1:
        parciales = chunks[0]["texto"]
    else:
        parciales = "\n\n".join(
            f"[{c['id']}] "
            + preguntar_ollama(PROMPT_TROZO.format(texto=c["texto"]), 180)
            for c in chunks
        )
    resumen = preguntar_ollama(
        PROMPT_FINAL.format(archivo=doc["archivo"], vinetas=vinetas, texto=parciales),
        600,
    )
    cache.write_text(
        json.dumps(
            {"hash": doc["hash"], "vinetas": vinetas, "resumen": resumen},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    return resumen


def main():
    ap = argparse.ArgumentParser(
        description="Destila o resume uno o varios documentos pasados por el chat (0 tokens nube)"
    )
    ap.add_argument(
        "entradas",
        nargs="+",
        type=Path,
        help="Uno o varios documentos o .json del conversor",
    )
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    ap.add_argument("--vinetas", type=int, default=5)
    ap.add_argument(
        "--ollama",
        action="store_true",
        help="Usa Qwen local en Ollama para resumir trozos largos",
    )
    args = ap.parse_args()

    archivos = expandir_entradas(args.entradas)
    for entrada in archivos:
        if entrada.suffix.lower() == ".json":
            doc = json.loads(entrada.read_text(encoding="utf-8"))
        else:
            doc = convertir(entrada, args.salida)
        print(resumir_local(doc, args.vinetas, args.salida, usar_ollama=args.ollama))
        print()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
