"""Ortografia y gramatica con el corrector de WORD en espanol (el que el usuario ya tiene instalado). 12/11/2026, Claude.

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
  $d.Content.LanguageID = __LANG_ID__
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


def _separar_por_idioma(texto: str) -> tuple[str, str]:
    """Separa el bloque Abstract (inglés) del resto del texto (español)."""
    lineas_es, lineas_en = [], []
    en_abstract = False
    for linea in texto.splitlines():
        limpia = linea.strip()
        if re.match(r"(?i)^(?:#{1,6}\s+)?abstract\b", limpia):
            en_abstract = True
            continue
        if en_abstract and re.match(
            r"(?i)^(?:#{1,6}\s+|(?:\d+\.\s*)?(?:introducci[oó]n|objetivos|marco\s+te[oó]rico|metodolog[ií]a|desarrollo|conclusiones|referencias|anexos)\b)",
            limpia,
        ):
            en_abstract = False
        (lineas_en if en_abstract else lineas_es).append(linea)
    return "\n".join(lineas_es), "\n".join(lineas_en)


def _limpiar_para_word(texto: str) -> str:
    texto = re.sub(r"\s*\(\s*`[^`]*`\s*\)", "", texto)
    texto = re.sub(
        r"`[^`]*`|https?://\S+|\S+\.(?:py|md|json|docx|pdf|com|org|es|io)\b\S*",
        "Nova",
        texto,
    )
    texto = re.sub(r"(?m)^\s*(?:#{1,6}|>|[-*•]|\d+[.)])\s+", "", texto)
    texto = re.sub(r"(?m)^:::.*$|^\s*\|?\s*:?-{2,}.*$", "", texto)
    texto = re.sub(r"\s*\|\s*", "\n", texto.replace("**", ""))
    return re.sub(r"(?m)^([DAFO]):\s", "", texto)


def _revisar_bloque_word(texto: str, lang_id: int) -> dict:
    import docx

    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "revision.docx"
        doc = docx.Document()
        for parrafo in texto.split("\n"):
            if parrafo.strip():
                doc.add_paragraph(parrafo.strip())
        doc.save(str(ruta))
        ps = _PS.replace("__DOCX__", str(ruta).replace("'", "''")).replace(
            "__LANG_ID__", str(lang_id)
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=240,
            encoding="utf-8",
            errors="replace",
        )
        return json.loads(r.stdout.strip() or "{}")


def revisar_texto(texto: str, extra: str = "") -> tuple[list[str], list[str]]:
    """(palabras_mal_escritas, frases_con_fallos_de_gramatica). Revisa español (3082) y Abstract en inglés (1033)."""
    texto_es, texto_en = _separar_por_idioma(texto)
    conocidas = diccionario(extra)
    malas, gramatica = [], []
    for bloque, lang_id in ((texto_es, 3082), (texto_en, 1033)):
        limpio = _limpiar_para_word(bloque).strip()
        if not limpio:
            continue
        try:
            datos = _revisar_bloque_word(limpio, lang_id)
        except (subprocess.TimeoutExpired, ValueError, OSError) as e:  # v3.2: OSError = sin PowerShell/Word (macOS/Linux)
            return [], [
                f"No se pudo usar el corrector de Word ({e.__class__.__name__})"
            ]
        malas.extend(
            p
            for raw in (datos.get("ortografia") or [])
            if (p := str(raw).strip()) and not _ignorar(p, conocidas) and p not in malas
        )
        gramatica.extend(
            str(g).strip()[:120]
            for g in (datos.get("gramatica") or [])
            if _es_frase(str(g))
        )
    return malas, gramatica


def _es_frase(texto: str) -> bool:
    """Word marca como 'gramatica' fragmentos que no son frases: celdas, etiquetas 'Modulo: X', el cartel..."""
    texto = texto.strip()
    return (
        len(texto.split()) >= 5
        and not re.search(r"·| / |\.\.$", texto)
        and not re.match(r"^[\wÁÉÍÓÚáéíóú ]{1,20}:\s*[^.]*$", texto)
    )
