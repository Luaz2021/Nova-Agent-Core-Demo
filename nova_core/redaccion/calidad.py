"""Control de calidad de los textos ANTES de exportar (12/11/2026, Claude).

Por que: el 12/11 Nova entrego la actividad de IPE II sin una sola tilde (lo copia de sus reglas, escritas sin
tildes), con cifras inventadas ("40 % del tiempo", "x3 probado") y jerga de folleto. Las reglas escritas no bastan:
lo comprueba el codigo.

- TILDES  (bloquea): texto en espanol sin tildes ni enes.
- CIFRAS  (bloquea): porcentajes, multiplicadores y numeros de 2+ cifras que no aparecen en los datos dados
                     (contexto, puntos o enunciado). Si la cifra es real, se anade al "contexto" del guion.
- JERGA   (aviso):  palabras de folleto que hacen que el texto no parezca escrito por una persona.
Saltarse los bloqueos: redactar.py exportar --forzar (solo si Alexander lo dice).
"""

import re

# Palabras que en espanol SIEMPRE llevan tilde o ene (sin ambiguedad: "esta", "mas", "solo"... no estan).
SIN_TILDE = re.compile(
    r"\b(\w+cion|tecnic[oa]s?|analisis|codigo|pagina|metodo|ultim[oa]s?|unic[oa]s?|rapid[oa]s?|facil|"
    r"numero|public[oa]s?|economic[oa]s?|tambien|despues|segun|ademas|aqui|asi|basic[oa]s?|logic[oa]|"
    r"automatic[oa]s?|electronic[oa]|practic[oa]s|academic[oa]s?|estrategic[oa]s?|grafic[oa]s?|dinamic[oa]s?|"
    r"especific[oa]s?|tecnologic[oa]s?|caracteristicas?|politicas?|metricas?|catalogo|modulo|telefono|"
    r"espanol|espana|pequen[oa]s?|disen[oa]|ninera|compania|senal|ano|anos|tambien|dia|dias|mas alla)\b",
    re.IGNORECASE,
)
TILDES = re.compile(r"[áéíóúñÁÉÍÓÚÑ]")

JERGA = [
    "sinergi",
    "hipertrófic",
    "hipertrofic",
    "paradigma",
    "disrupt",
    "holístic",
    "holistic",
    "sin precedentes",
    "cabe destacar",
    "en el mundo actual",
    "es imperativo",
    "de alto impacto",
    "de excelencia",
    "360°",
    "360º",
    "revolucion",
    "revolución",
    "potenciar",
    "apalancar",
    "ecosistema agéntico",
    "ecosistema agentico",
    "de forma concluyente",
    "erradicación",
    "erradicacion",
    "terminantemente",
    "ultra-",
    "game changer",
    "next level",
    "vanguardia",
    "de clase mundial",
    "atómico",
    "atomico",
]

RE_CIFRA = re.compile(
    r"(?<![\w/.-])(x\s?\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s?x\b|\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s?%|\d{2,}(?:[.,]\d+)?)",
    re.IGNORECASE,
)


def _normal(cifra: str) -> str:
    """'1.414' == '1414' == '1,414'; '70 %' == '70%'; 'x3' == '3x'. Un % o un multiplicador solo casa con
    otro % o multiplicador (el '3' de 'Qwen 3.5' no respalda un 'x3')."""
    bajo = cifra.lower()
    marca = "x" if "x" in bajo else ("%" if "%" in bajo else "")
    return marca + re.sub(r"\D", "", bajo)


def _quitar_codigo(texto: str) -> str:
    texto = re.sub(r"```.*?```", " ", texto, flags=re.DOTALL)
    texto = re.sub(r"`[^`]*`", " ", texto)
    texto = re.sub(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", " ", texto)  # fechas 12/11/2026
    texto = re.sub(
        r"\b[A-Z]{2,}[\s-]?\d+\w*", " ", texto
    )  # modelos: RTX 5060, APA 7, RGPD
    return re.sub(
        r"https?://\S+|\b[\w.-]+\.(?:com|org|es|io|py|md|json|docx|pdf)\b\S*",
        " ",
        texto,
    )


def tildes(texto: str) -> str | None:
    limpio = _quitar_codigo(texto)
    palabras = len(limpio.split())
    if palabras < 40:
        return None
    malas = sorted({m.group(0).lower() for m in SIN_TILDE.finditer(limpio)})
    buenas = len(TILDES.findall(limpio))
    if len(malas) >= 4 and buenas < palabras * 0.02:
        return f"texto sin tildes ni eñes ({buenas} tildes en {palabras} palabras). Ejemplos: {', '.join(malas[:6])}"
    return None


def _cifras(texto: str, fuentes: str) -> list[str]:
    conocidas = {_normal(m.group(0)) for m in RE_CIFRA.finditer(fuentes)}
    conocidas |= {_normal(n) for n in re.findall(r"\d+", fuentes)}
    raras = []
    for m in RE_CIFRA.finditer(_quitar_codigo(texto)):
        cifra = m.group(0).strip()
        if re.fullmatch(r"(19|20)\d\d", cifra):  # anos
            continue
        if _normal(cifra) not in conocidas and cifra not in raras:
            raras.append(cifra)
    return raras


def jerga(texto: str) -> list[str]:
    bajo = texto.lower()
    return [j for j in JERGA if j in bajo]


# Huellas de IA en espanol (catalogo de la skill gemini-humanizer-prose + lo visto en Nova el 12/11)
HUELLAS_IA = [
    "es crucial destacar",
    "es importante señalar",
    "es importante destacar",
    "vale la pena mencionar",
    "desempeña un papel fundamental",
    "juega un papel",
    "aprovechar al máximo",
    "en el vertiginoso mundo",
    "un tapiz de",
    "sirve como testimonio",
    "hito transformador",
    "huella indeleble",
    "en conclusión",
    "a medida que avanzamos",
    "no solo",
    "en definitiva",
    "cabe mencionar",
    "de manera integral",
    "de forma integral",
    "robusto",
    "robusta",
    "fomentar",
    "potente y versátil",
    "sin lugar a dudas",
]
MAX_PALABRAS_FRASE = 45


def _humanize_check():
    """El escaner que ya tenia Nova (antigravity/scripts/humanize_check.py): ritmo y paralelismos."""
    import importlib.util
    from pathlib import Path

    ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "humanize_check.py"
    if not ruta.exists():
        return None
    spec = importlib.util.spec_from_file_location("humanize_check", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def humano(texto: str) -> tuple[str | None, list[str]]:
    """(bloqueo, avisos) sobre si el texto suena a persona."""
    limpio = _quitar_codigo(
        re.sub(r"(?m)^\s*\|.*$|^:::.*$", " ", texto)
    )  # sin tablas ni bloques
    frases = [f for f in re.split(r"(?<=[.!?])\s+|\n+", limpio) if f.strip()]
    largas = [len(f.split()) for f in frases if len(f.split()) > MAX_PALABRAS_FRASE]
    bajo = limpio.lower()
    huellas = [h for h in HUELLAS_IA if h in bajo] + jerga(limpio)
    avisos = []
    if hc := _humanize_check():
        for f in hc.analyze_text(limpio).get("flags", []):
            if f.get("severidad") in ("ALTA", "MEDIA"):
                avisos.append(f"{f['tipo']}: {f['detalle'][:140]}")
    problemas = []
    if largas:
        problemas.append(
            f"{len(largas)} frase(s) de más de {MAX_PALABRAS_FRASE} palabras (la mayor: {max(largas)})"
        )
    if len(huellas) >= 3:
        problemas.append(f"suena a IA: {', '.join(huellas[:6])}")
    elif huellas:
        avisos.append(f"frases de IA: {', '.join(huellas)}")
    return ("; ".join(problemas) or None), avisos


def revisar(
    secciones: list[dict], fuentes: str, cifras: bool = True
) -> tuple[list[str], list[str]]:
    comprobar_cifras, cifras_raras = cifras, _cifras
    """secciones: [{'titulo', 'cuerpo'}]. Devuelve (bloqueos, avisos)."""
    bloqueos, avisos = [], []
    for s in secciones:
        nombre = s["titulo"][:50]
        texto = f"{s['titulo']}\n{s['cuerpo']}"
        if problema := tildes(texto):
            bloqueos.append(
                f"[TILDES] '{nombre}': {problema}. Reescríbela en español correcto."
            )
        if comprobar_cifras and (raras := cifras_raras(texto, fuentes)):
            bloqueos.append(
                f"[CIFRAS] '{nombre}': {', '.join(raras[:8])} no aparecen en los datos dados. "
                "Quítalas, o si son reales ponlas en el 'contexto' del guion."
            )
        bloqueo, notas = humano(s["cuerpo"])
        if bloqueo:
            bloqueos.append(
                f"[HUMANO] '{nombre}': {bloqueo}. Parte las frases y dilo como lo diría una persona."
            )
        avisos += [f"[HUMANO] '{nombre}': {n}" for n in notas]
    return bloqueos, avisos
