"""
Conversor y Destilador de documentos a texto limpio para Nova (Entrada por Chat, 0 tokens).

Recibe el archivo o los archivos que el usuario pasa por el chat (PDF, Word, Excel,
PowerPoint, HTML, CSV, TXT, MD), extrae el texto EN LOCAL sin usar APIs ni gastar
tokens en vision, limpia cabeceras/pies repetidos y entrega el contenido listo para leer.

Uso directo con los archivos pasados por el chat:
    python conversor.py doc1.pdf [doc2.docx tabla.xlsx carpeta_docs/ ...]
    python conversor.py doc1.pdf --imprimir          # imprime directo el texto limpio para Nova
    python conversor.py doc1.pdf --chunk 0           # imprime solo el trozo 0 para lecturas grandes
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

CHARS_POR_TOKEN = 4
EXTENSIONES = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xlsm",
    ".pptx",
    ".txt",
    ".md",
    ".csv",
    ".html",
    ".htm",
}
SALIDA_POR_DEFECTO = Path(__file__).resolve().parent / "salida_docs"


def estimar_tokens(texto: str) -> int:
    return max(1, len(texto) // CHARS_POR_TOKEN)


# ---------- Extractores ----------


def extraer_pdf(ruta: Path) -> list[str]:
    import pymupdf

    with pymupdf.open(ruta) as doc:
        return [pagina.get_text("text") for pagina in doc]


def extraer_docx(ruta: Path) -> list[str]:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = docx.Document(ruta)
    partes = []
    for elem in doc.element.body.iterchildren():
        if elem.tag.endswith("}p"):
            texto = Paragraph(elem, doc).text
            if texto.strip():
                partes.append(texto)
        elif elem.tag.endswith("}tbl"):
            for fila in Table(elem, doc).rows:
                celdas = []
                for c in fila.cells:
                    t = c.text.strip()
                    if not celdas or t != celdas[-1]:
                        celdas.append(t)
                if any(celdas):
                    partes.append(" | ".join(celdas))
    return ["\n".join(partes)]


def extraer_xlsx(ruta: Path) -> list[str]:
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    hojas = []
    for hoja in libro.worksheets:
        buf = io.StringIO()
        escritor = csv.writer(buf)
        for fila in hoja.iter_rows(values_only=True):
            valores = ["" if v is None else str(v).strip() for v in fila]
            while valores and not valores[-1]:
                valores.pop()
            if valores:
                escritor.writerow(valores)
        contenido = buf.getvalue().strip()
        if contenido:
            hojas.append(f"## Hoja: {hoja.title}\n{contenido}")
    libro.close()
    return hojas


def extraer_pptx(ruta: Path) -> list[str]:
    from pptx import Presentation

    diapositivas = []
    for i, slide in enumerate(Presentation(ruta).slides, 1):
        textos = [
            s.text_frame.text
            for s in slide.shapes
            if s.has_text_frame and s.text_frame.text.strip()
        ]
        if textos:
            diapositivas.append(f"## Diapositiva {i}\n" + "\n".join(textos))
    return diapositivas


def extraer_html(ruta: Path) -> list[str]:
    html = ruta.read_text(encoding="utf-8", errors="ignore")
    html = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", html)
    texto = re.sub(r"(?s)<[^>]+>", " ", html)
    return [texto]


def extraer_texto_plano(ruta: Path) -> list[str]:
    return [ruta.read_text(encoding="utf-8", errors="ignore")]


EXTRACTORES = {
    ".pdf": extraer_pdf,
    ".docx": extraer_docx,
    ".xlsx": extraer_xlsx,
    ".xlsm": extraer_xlsx,
    ".pptx": extraer_pptx,
    ".html": extraer_html,
    ".htm": extraer_html,
    ".txt": extraer_texto_plano,
    ".md": extraer_texto_plano,
    ".csv": extraer_texto_plano,
}


# ---------- Limpieza ----------

PATRON_NUM_PAGINA = re.compile(
    r"^\s*(p[aá]gina\s*)?\d+(\s*(de|/)\s*\d+)?\s*$", re.IGNORECASE
)


def quitar_encabezados_repetidos(paginas: list[str]) -> list[str]:
    """Quita lineas que se repiten en mas de la mitad de las paginas (encabezados/pies)."""
    if len(paginas) < 3:
        return paginas
    conteo = Counter()
    for p in paginas:
        conteo.update({l.strip() for l in p.splitlines() if l.strip()})
    repetidas = {l for l, n in conteo.items() if n > len(paginas) / 2 and len(l) < 120}
    return [
        "\n".join(l for l in p.splitlines() if l.strip() not in repetidas)
        for p in paginas
    ]


def limpiar(texto: str) -> str:
    lineas = []
    for linea in texto.splitlines():
        linea = re.sub(r"[ \t\u00a0]+", " ", linea).strip()
        if PATRON_NUM_PAGINA.match(linea):
            continue
        lineas.append(linea)
    texto = "\n".join(lineas)
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


# ---------- Division en trozos ----------


def dividir(texto: str, chunk_tokens: int) -> list[str]:
    max_chars = chunk_tokens * CHARS_POR_TOKEN
    trozos, actual = [], ""
    for parrafo in texto.split("\n\n"):
        piezas = [parrafo] if len(parrafo) <= max_chars else parrafo.splitlines()
        for pieza in piezas:
            if len(actual) + len(pieza) + 2 > max_chars and actual:
                trozos.append(actual.strip())
                actual = ""
            while len(pieza) > max_chars:
                trozos.append(pieza[:max_chars])
                pieza = pieza[max_chars:]
            actual += pieza + "\n\n"
    if actual.strip():
        trozos.append(actual.strip())
    return trozos


# ---------- Proceso principal ----------


def hash_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()[:16]


def convertir(
    ruta: Path, salida: Path = SALIDA_POR_DEFECTO, chunk_tokens: int = 3000
) -> dict:
    ext = ruta.suffix.lower()
    if ext not in EXTRACTORES:
        raise ValueError(f"Formato no soportado: {ext}")

    huella = hash_archivo(ruta)
    destino_json = salida / f"{ruta.stem}.json"
    if destino_json.exists():
        previo = json.loads(destino_json.read_text(encoding="utf-8"))
        if previo.get("hash") == huella and previo.get("chunk_tokens") == chunk_tokens:
            print(
                f"[cache] {ruta.name} ({previo['secciones']} secciones, ~{previo['tokens_estimados']} tokens, {len(previo['chunks'])} trozos) -> {destino_json}"
            )
            return previo

    secciones = EXTRACTORES[ext](ruta)
    if ext == ".pdf":
        secciones = quitar_encabezados_repetidos(secciones)
    texto = limpiar("\n\n".join(secciones))
    trozos = dividir(texto, chunk_tokens)

    resultado = {
        "archivo": ruta.name,
        "ruta_original": str(ruta.resolve()),
        "tipo": ext.lstrip("."),
        "hash": huella,
        "secciones": len(secciones),
        "tokens_estimados": estimar_tokens(texto),
        "chunk_tokens": chunk_tokens,
        "txt_limpio": str((salida / f"{ruta.stem}.txt").resolve()),
        "chunks": [
            {"id": i, "tokens": estimar_tokens(t), "texto": t}
            for i, t in enumerate(trozos)
        ],
    }

    salida.mkdir(parents=True, exist_ok=True)
    destino_json.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (salida / f"{ruta.stem}.txt").write_text(texto, encoding="utf-8")
    print(
        f"[ok] {ruta.name}: {resultado['secciones']} secciones, "
        f"~{resultado['tokens_estimados']} tokens, {len(trozos)} trozos -> {destino_json}"
    )
    return resultado


def expandir_entradas(entradas: list[Path]) -> list[Path]:
    archivos: list[Path] = []
    for entrada in entradas:
        if entrada.is_dir():
            archivos.extend(
                sorted(
                    p
                    for p in entrada.rglob("*")
                    if p.is_file() and p.suffix.lower() in EXTENSIONES
                )
            )
        elif entrada.is_file():
            archivos.append(entrada)
    return archivos


def main():
    ap = argparse.ArgumentParser(
        description="Convierte uno o varios documentos pasados por el chat a texto limpio (0 tokens)"
    )
    ap.add_argument(
        "entradas",
        nargs="+",
        type=Path,
        help="Uno o varios archivos o carpetas pasados por el chat",
    )
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    ap.add_argument("--chunk-tokens", type=int, default=3000)
    ap.add_argument(
        "--imprimir",
        action="store_true",
        help="Imprime el texto limpio si es corto o el primer trozo",
    )
    ap.add_argument(
        "--chunk", type=int, default=None, help="Imprime un trozo especifico por su ID"
    )
    args = ap.parse_args()

    archivos = expandir_entradas(args.entradas)
    if not archivos:
        print(
            "[error] No se encontraron documentos validos en las rutas indicadas.",
            file=sys.stderr,
        )
        sys.exit(1)

    errores = 0
    for archivo in archivos:
        try:
            doc = convertir(archivo, args.salida, args.chunk_tokens)
            if args.chunk is not None:
                chunks = doc.get("chunks", [])
                if 0 <= args.chunk < len(chunks):
                    print(
                        f"\n--- {doc['archivo']} [Trozo {args.chunk}/{len(chunks) - 1}] ---\n{chunks[args.chunk]['texto']}"
                    )
            elif args.imprimir and doc.get("chunks"):
                print(
                    f"\n--- {doc['archivo']} [Trozo 0/{len(doc['chunks']) - 1}] ---\n{doc['chunks'][0]['texto']}"
                )
        except Exception as e:  # noqa: BLE001
            errores += 1
            print(f"[error] {archivo.name}: {e}", file=sys.stderr)
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
