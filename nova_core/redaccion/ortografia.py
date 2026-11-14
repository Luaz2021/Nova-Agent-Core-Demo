"""Ortografia y gramatica con el corrector de WORD en espanol (el que Alexander ya tiene instalado). 12/11/2026, Claude.

Se pasa el texto a un .docx temporal marcado como espanol (es-ES), Word lo revisa y devuelve las palabras mal
escritas y las frases con fallos de gramatica. Sin internet, sin tokens, sin instalar nada.
Palabras que Word no conoce pero estan bien (Nova, Qwen, GitHub...): redaccion/diccionario.txt (una por linea)
+ las palabras del propio guion (titulo, contexto, datos). Siglas, palabras con mayusculas en medio o con
numeros se ignoran solas.
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path

DICCIONARIO = Path(__file__).resolve().parent / "diccionario.txt"

_PS = r"""
$ErrorActionPreference = 'Stop'
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
  $d = $w.Documents.Open('__DOCX__', $false, $true)
  $d.Content.LanguageID = 3082
  $d.Content.NoProofing = $false
  $orto = @($d.SpellingErrors | ForEach-Object { $_.Text })
  $gram = @($d.GrammaticalErrors | Select-Object -First 25 | ForEach-Object { $_.Text })
  $d.Close($false)
  @{ ortografia = $orto; gramatica = $gram } | ConvertTo-Json -Compress
} finally { $w.Quit() }
"""


def diccionario(extra: str = "") -> set[str]:
    palabras = set()
    if DICCIONARIO.exists():
        palabras |= {
            p.strip().lower()
            for p in DICCIONARIO.read_text(encoding="utf-8").splitlines()
            if p.strip()
        }
    palabras |= {p.lower() for p in re.findall(r"[\wÁÉÍÓÚáéíóúñÑ]+", extra)}
    return palabras


def _ignorar(palabra: str, conocidas: set[str]) -> bool:
    return (
        palabra.lower() in conocidas
        or any(c.isdigit() for c in palabra)
        or palabra.isupper()  # siglas: DAFO, RGPD
        or bool(re.search(r"[a-záéíóú][A-Z]", palabra))  # GitHub, InternVL
        or len(palabra) <= 2
    )


def revisar_texto(texto: str, extra: str = "") -> tuple[list[str], list[str]]:
    """(palabras_mal_escritas, frases_con_fallos_de_gramatica). Si Word no esta, ([], ['aviso'])."""
    import docx

    texto = re.sub(
        r"\s*\(\s*`[^`]*`\s*\)", "", texto
    )  # "vigilante (`nova_hook.py`)" -> "vigilante"
    texto = re.sub(
        r"`[^`]*`|https?://\S+|\S+\.(?:py|md|json|docx|pdf|com|org|es|io)\b\S*",
        "Nova",
        texto,
    )
    texto = re.sub(
        r"(?m)^\s*(?:#{1,6}|>|[-*•]|\d+[.)])\s+", "", texto
    )  # marcas de titulo, cita y lista
    texto = re.sub(
        r"(?m)^:::.*$|^\s*\|?\s*:?-{2,}.*$", "", texto
    )  # bloques ::: y separadores de tabla
    texto = re.sub(
        r"\s*\|\s*", "\n", texto.replace("**", "")
    )  # celdas de tabla: cada una en su linea
    texto = re.sub(r"(?m)^([DAFO]):\s", "", texto)  # puntos del bloque :::dafo
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "revision.docx"
        doc = docx.Document()
        for parrafo in texto.split("\n"):
            if parrafo.strip():
                doc.add_paragraph(parrafo.strip())
        doc.save(str(ruta))
        ps = _PS.replace("__DOCX__", str(ruta).replace("'", "''"))
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=240,
                encoding="utf-8",
                errors="replace",
            )
            datos = json.loads(r.stdout.strip() or "{}")
        except (subprocess.TimeoutExpired, ValueError) as e:
            return [], [
                f"No se pudo usar el corrector de Word ({e.__class__.__name__})"
            ]
    conocidas = diccionario(extra)
    malas = []
    for p in datos.get("ortografia") or []:
        p = str(p).strip()
        if p and not _ignorar(p, conocidas) and p not in malas:
            malas.append(p)
    gramatica = [
        str(g).strip()[:120]
        for g in (datos.get("gramatica") or [])
        if _es_frase(str(g))
    ]
    return malas, gramatica


def _es_frase(texto: str) -> bool:
    """Word marca como 'gramatica' fragmentos que no son frases: celdas, etiquetas 'Modulo: X', el cartel..."""
    texto = texto.strip()
    return (
        len(texto.split()) >= 5
        and not re.search(r"·| / |\.\.$", texto)
        and not re.match(r"^[\wÁÉÍÓÚáéíóú ]{1,20}:\s*[^.]*$", texto)
    )
