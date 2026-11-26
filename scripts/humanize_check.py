#!/usr/bin/env python3
"""
humanize_check.py - Escáner forense anti-slop, estilometría en español y chequeo APA 7.
Cero dependencias externas. Ejecutable en local a 0 tokens.

Uso:
    python humanize_check.py archivo.md
    python humanize_check.py --perfil academico --apa borrador.md
    python humanize_check.py --json borrador.md
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

# 1. Catálogos de vocabulario: Nivel A (golpe único) vs Nivel B (densidad >= 3 por párrafo)
CLICHES_FUERTES_EN = [
    r"\bdelve\b",
    r"\btapestry\b",
    r"\bindelible mark\b",
    r"\bin the realm of\b",
    r"\ba myriad of\b",
    r"\ba plethora of\b",
    r"\bgame-changer\b",
    r"\bbeacon\b",
    r"\bit is important to note\b",
    r"\bit is worth noting\b",
    r"\bstands as a testament\b",
]

VOCAB_DENSIDAD_EN = [
    r"\btestament\b",
    r"\bunderscore\b",
    r"\bleverage\b",
    r"\butilize\b",
    r"\brobust\b",
    r"\bcomprehensive\b",
    r"\bstreamline\b",
    r"\bfoster\b",
    r"\bfacilitate\b",
    r"\bpivotal\b",
    r"\bnuanced\b",
    r"\bnotable\b",
    r"\bnotably\b",
    r"\benduring\b",
    r"\bgarner\b",
    r"\bmultifaceted\b",
    r"\bthe landscape of\b",
    r"\bin conclusion\b",
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\btransformative\b",
    r"\bserves as\b",
    r"\bstands as\b",
    r"\bboasts\b",
    r"\bvibrant\b",
    r"\bseamless\b",
    r"\bintertwined\b",
]

CLICHES_FUERTES_ES = [
    r"\ben el vertiginoso mundo\b",
    r"\ben el panorama actual\b",
    r"\ben el mundo actual\b",
    r"\bun tapiz de\b",
    r"\bsirve como testimonio\b",
    r"\bes crucial destacar\b",
    r"\bes importante se[nñ]alar\b",
    r"\bes importante destacar\b",
    r"\bcabe destacar\b",
    r"\bvale la pena mencionar\b",
    r"\bsin lugar a dudas\b",
    r"\bun sinf[ií]n de\b",
    r"\bdesempe[nñ]a un papel fundamental\b",
    r"\bdesempe[nñ]a un rol crucial\b",
    r"\baprovechar al m[aá]ximo\b",
    r"\bpiedra angular\b",
    r"\bhito fundamental\b",
    r"\bhito transformador\b",
    r"\bhuella indeleble\b",
    r"\bde vital importancia\b",
    r"\bcuenta con una amplia gama\b",
    r"\ba medida que avanzamos\b",
]

VOCAB_DENSIDAD_ES = [
    r"\ben conclusi[oó]n\b",
    r"\ben definitiva\b",
    r"\bcabe mencionar\b",
    r"\bjuega un papel\b",
    r"\bde (?:manera|forma) integral\b",
    r"\bhol[ií]stic[oa]s?\b",
    r"\brobust[oa]s?\b",
    r"\bfomentar\b",
    r"\bfacilitar\b",
    r"\bpotenciar\b",
    r"\bapalancar\b",
    r"\bparadigma\b",
    r"\bsinergi[as]*\b",
    r"\bpioner[oa]s?\b",
    r"\btransformador(?:a|es|as)?\b",
    r"\balberga\b",
    r"\bostenta\b",
    r"\basimismo\b",
    r"\bpor otro lado\b",
    r"\ben este sentido\b",
]

# 2. Patrones estructurales y académicos (golpe único)
STRUCTURAL_PATTERNS = [
    (
        r"\bnot\s+(?:only|just)\s+[^,;]+,?\s+but\s+(?:also\s+)?",
        "Paralelismo negativo ('not just X, but Y')",
    ),
    (
        r"\bno\s+solo\s+[^,;]+,?\s+sino\s+(?:tambi[eé]n\s+)?",
        "Paralelismo negativo ('no solo X, sino también Y')",
    ),
    (
        r"\bno\s+se\s+trata\s+(?:solo\s+)?de\s+[^,;]+,?\s+sino\s+de\b",
        "Falso pivote ('no se trata de X, sino de Y')",
    ),
    (r"\bno\s+es\s+[^,;]+,?\s+es\s+", "Falso pivote ('no es X, es Y')"),
    (
        r"\bit'?s\s+not\s+about\s+[^,;]+,?\s+it'?s\s+about\b",
        "Falso pivote ('it's not about X, it's about Y')",
    ),
    (
        r",\s+(?:highlighting|showcasing|symbolizing|reflecting|underscoring)\b",
        "Gerundio de relleno colgante (EN)",
    ),
    (
        r",\s+(?:destacando|demostrando|reflejando|subrayando|simbolizando)\b",
        "Gerundio de relleno colgante (ES)",
    ),
    (
        r"\b(?:let\s+that\s+sink\s+in|deja\s+que\s+eso\s+cale)\b",
        "Cierre melodramático forzado",
    ),
    (r"\b(?:at\s+its\s+core|en\s+su\s+esencia)\b", "Trascendencia artificial"),
    (
        r"\b(?:here'?s\s+the\s+thing|el\s+futuro\s+parece\s+prometedor)\b",
        "Fórmula artificial de relleno",
    ),
]

ACADEMIC_PATTERNS_ES = [
    (
        "ALTA",
        "Lavado de citas",
        r"\b(?:(?:los\s+)?estudios|(?:las\s+)?investigaciones|la\s+literatura|diversos\s+autores|los\s+expertos)\s+"
        r"(?:han\s+)?(?:demostrado|demuestran|se[nñ]alan?|indican?|muestran?|sugieren?|afirman?|coinciden|creen)\b"
        r"(?![^.]{0,140}(?:19|20)\d\d)",
        "Afirmación atribuida a 'estudios/expertos' sin cita (Autor, año)",
    ),
    (
        "MEDIA",
        "Relleno de manuscrito",
        r"\b(?:hasta\s+donde\s+sabemos|llena\s+un\s+vac[ií]o\s+(?:cr[ií]tico|importante)|"
        r"representa\s+un\s+avance\s+significativo|sienta\s+las\s+bases\s+para)\b",
        "Fórmula genérica de manuscrito IA",
    ),
    (
        "MEDIA",
        "Pseudoprecisión metodológica",
        r"\b(?:an[aá]lisis\s+riguroso|evaluaci[oó]n\s+cuidadosa|estudio\s+exhaustivo|revisi[oó]n\s+meticulosa)\b",
        "Autoelogio metodológico sin detallar método",
    ),
    (
        "MEDIA",
        "Evasiva de tesis",
        r"\b(?:podr[ií]a\s+argumentarse\s+que|se\s+podr[ií]a\s+sugerir\s+que|algunos\s+podr[ií]an\s+considerar)\b",
        "Fórmula evasiva en lugar de postura respaldada",
    ),
]

# 3. Marcas de agua invisibles, fuentes prohibidas UEM y stopwords para control de repeticiones
INVISIBLE_WATERMARKS = [
    (
        r"[\u200B\u200C\u200D\uFEFF]",
        "Carácter Unicode de ancho cero (Zero-width watermark)",
    ),
    (r"oaicite:[^\s]+", "Fuga de cita interna de OpenAI (oaicite)"),
    (r"contentReference\[[^\]]+\]", "Fuga de metadatos de cita de LLM"),
    (r"utm_source=(?:chatgpt|claude|gemini)", "Parámetro UTM de exportación de IA"),
    (
        r"(?i)\b(?:espero que esto te ayude|seg[uú]n mi [uú]ltima actualizaci[oó]n de entrenamiento)\b",
        "Resto de chat de LLM",
    ),
]

FUENTES_PROHIBIDAS_APA = [
    r"wikipedia\.org",
    r"rincondelvago",
    r"monografias\.com",
    r"buenastareas",
    r"brainly\.",
    r"youtube\.com",
    r"youtu\.be",
    r"tiktok\.com",
    r"blogspot\.com",
    r"wordpress\.com",
    r"\bchatgpt\b",
]

STOPWORDS_ES = frozenset(
    {
        "sobre",
        "entre",
        "desde",
        "hasta",
        "donde",
        "cuando",
        "porque",
        "aunque",
        "según",
        "hacia",
        "todos",
        "todas",
        "estas",
        "estos",
        "aquel",
        "puede",
        "pueden",
        "tiene",
        "tienen",
        "forma",
        "parte",
        "también",
        "siendo",
        "haber",
        "durante",
        "mediante",
        "través",
        "respecto",
        "dentro",
        "fuera",
        "contra",
        "mismo",
        "misma",
        "otros",
        "otras",
        "cuales",
        "quien",
        "siempre",
        "nunca",
        "datos",
        "nivel",
        "grupo",
        "casos",
        "estudio",
        "trabajo",
        "proyecto",
    }
)

ABREV_APA = re.compile(
    r"\b(?:et\s+al|pp?|p\.\s*ej|ed|eds|vol|n[uú]m|no|cap|fig|tab|art|dr|dra|sr|sra|prof|etc|ee\.\s*uu|u\.s)\.",
    re.IGNORECASE,
)

PESOS_SEVERIDAD = {"CRÍTICA": 35, "ALTA": 15, "MEDIA": 8, "BAJA": 3}


RE_SECCION_REFS = re.compile(
    r"(?im)^#{1,3}\s+(?:\d+\.?\s*)?(?:referencias|bibliograf[ií]a)\b.*$"
)


def _sin_referencias(text: str) -> str:
    """Devuelve solo la prosa antes de la sección de Referencias."""
    m = RE_SECCION_REFS.search(text)
    return text[: m.start()] if m else text


def _strip_quotes_and_code(text: str) -> str:
    """Elimina bloques de código, tablas y citas textuales para no penalizar citas ajenas."""
    limpio = re.sub(r"```.*?```", " ", _sin_referencias(text), flags=re.DOTALL)
    limpio = re.sub(r"`[^`]*`", " ", limpio)
    limpio = re.sub(r"(?m)^\s*\|.*$", " ", limpio)
    return re.sub(r"[“\"«][^”\"»]{8,}[”\"»]", " ", limpio)


def split_sentences(text: str) -> list[str]:
    """Divide texto en oraciones limpias sin romperse con citas APA 7 ni abreviaturas."""
    limpio = re.sub(r"```.*?```", "", _sin_referencias(text), flags=re.DOTALL)
    limpio = re.sub(r"`[^`]*`", "", limpio)
    limpio = re.sub(r"(?m)^\s*#{1,6}\s+.*$", "", limpio)
    limpio = re.sub(r"(?m)^\s*\|.*$", "", limpio)
    protegido = ABREV_APA.sub(lambda m: m.group(0).replace(".", "\x00"), limpio)
    protegido = re.sub(
        r"\(([^()\n]{1,120})\)",
        lambda m: "(" + m.group(1).replace(".", "\x00") + ")",
        protegido,
    )
    protegido = re.sub(
        r"(\d)\.(\d)", lambda m: f"{m.group(1)}\x00{m.group(2)}", protegido
    )
    return [
        s.replace("\x00", ".").strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", protegido)
        if len(s.strip().split()) >= 3 and not s.strip().startswith("#")
    ]


def _flag(severidad: str, tipo: str, linea: int, detalle: str) -> dict[str, object]:
    return {"severidad": severidad, "tipo": tipo, "linea": linea, "detalle": detalle}


def _mattr_es(words: list[str], window: int = 50) -> float:
    """Diversidad léxica estable en español (MATTR-50)."""
    if not words:
        return 0.0
    if len(words) < window:
        return len(set(words)) / len(words)
    step = max(1, (len(words) - window) // 100)
    ttrs = [
        len(set(words[i : i + window])) / window
        for i in range(0, len(words) - window + 1, step)
    ]
    return statistics.mean(ttrs)


def _cv(valores: list[int]) -> float:
    if len(valores) < 2:
        return 0.0
    media = statistics.mean(valores)
    return statistics.pstdev(valores) / media if media else 0.0


def _chequear_lineas(text: str, perfil: str) -> list[dict[str, object]]:
    """Patrones de golpe único: watermarks, clichés fuertes, estructura, académicos y staccato."""
    flags = [
        _flag(
            "CRÍTICA",
            "Watermark / Artefacto",
            0,
            f"{desc} ({len(matches)} ocurrencias)",
        )
        for pat, desc in INVISIBLE_WATERMARKS
        if (matches := list(re.finditer(pat, text)))
    ]
    en_codigo = False
    for idx, line in enumerate(text.splitlines(), 1):
        limpia = line.strip()
        if limpia.startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo or not limpia or limpia.startswith(("#", "|", "`")):
            continue
        sin_citas = re.sub(r"[“\"«][^”\"»]{8,}[”\"»]", " ", line)
        flags.extend(
            _flag("ALTA", "Cliché IA (EN)", idx, f"'{m.group(0)}' en: '{limpia[:80]}'")
            for pat in CLICHES_FUERTES_EN
            for m in re.finditer(pat, sin_citas, re.IGNORECASE)
        )
        flags.extend(
            _flag("ALTA", "Cliché IA (ES)", idx, f"'{m.group(0)}' en: '{limpia[:80]}'")
            for pat in CLICHES_FUERTES_ES
            for m in re.finditer(pat, sin_citas, re.IGNORECASE)
        )
        flags.extend(
            _flag("MEDIA", "Sintaxis / Estructura", idx, f"{desc} -> '{m.group(0)}'")
            for pat, desc in STRUCTURAL_PATTERNS
            for m in re.finditer(pat, sin_citas, re.IGNORECASE)
        )
        if perfil == "academico":
            flags.extend(
                _flag(sev, tipo, idx, f"{desc} -> '{m.group(0)}'")
                for sev, tipo, pat, desc in ACADEMIC_PATTERNS_ES
                for m in re.finditer(pat, sin_citas, re.IGNORECASE)
            )
        if re.fullmatch(r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,18}\.", limpia):
            flags.append(
                _flag(
                    "MEDIA",
                    "Staccato artificial",
                    idx,
                    f"Línea dramática de una palabra: '{limpia}'",
                )
            )
    return flags


def _chequear_densidad_parrafos(text: str) -> list[dict[str, object]]:
    """Puntúa vocabulario común por densidad (>= 3 en el mismo párrafo) y repetición léxica."""
    parrafos = [
        p.strip()
        for p in re.split(r"\n\s*\n", _strip_quotes_and_code(text))
        if len(p.split()) >= 15 and not p.strip().startswith("#")
    ]
    flags: list[dict[str, object]] = []
    for num, parrafo in enumerate(parrafos, 1):
        hits_es = [
            m.group(0)
            for pat in VOCAB_DENSIDAD_ES
            for m in re.finditer(pat, parrafo, re.IGNORECASE)
        ]
        if len(hits_es) >= 3:
            flags.append(
                _flag(
                    "MEDIA",
                    "Densidad léxica IA (ES)",
                    0,
                    f"Párrafo {num}: {len(hits_es)} marcadores juntos ({', '.join(hits_es[:5])})",
                )
            )
        hits_en = [
            m.group(0)
            for pat in VOCAB_DENSIDAD_EN
            for m in re.finditer(pat, parrafo, re.IGNORECASE)
        ]
        if len(hits_en) >= 3:
            flags.append(
                _flag(
                    "MEDIA",
                    "Densidad léxica IA (EN)",
                    0,
                    f"Párrafo {num}: {len(hits_en)} marcadores juntos ({', '.join(hits_en[:5])})",
                )
            )
        palabras = [
            w
            for w in re.findall(r"[a-záéíóúüñ]{5,}", parrafo.lower())
            if w not in STOPWORDS_ES
        ]
        repetidas = [
            f"'{w}' ({c}x)" for w, c in Counter(palabras).most_common(3) if c >= 4
        ]
        if repetidas:
            flags.append(
                _flag(
                    "BAJA",
                    "Repetición léxica",
                    0,
                    f"Párrafo {num}: {', '.join(repetidas)}",
                )
            )
    return flags


def _chequear_puntuacion(
    text: str, word_count: int, perfil: str
) -> list[dict[str, object]]:
    flags: list[dict[str, object]] = []
    em_dashes = text.count("—")
    if word_count > 0:
        limite = max(1, round(word_count / 300))
        if em_dashes > limite:
            flags.append(
                _flag(
                    "MEDIA",
                    "Puntuación",
                    0,
                    f"Exceso de rayas largas ('—'): {em_dashes} en {word_count} palabras (tope: {limite}).",
                )
            )
    if perfil != "academico":
        curly_quotes = len(re.findall(r"[“”‘’]", text))
        if curly_quotes > 2:
            flags.append(
                _flag(
                    "BAJA",
                    "Tipografía",
                    0,
                    f"{curly_quotes} comillas curvas ('“', '”'). En perfil general preferir comillas rectas.",
                )
            )
    return flags


def _chequear_ritmo_y_staccato(
    text: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Métricas informativas de ritmo en español sin forzar burstiness artificial."""
    sentences = split_sentences(text)
    sent_lengths = [len(s.split()) for s in sentences]
    parrafos = [
        len(p.split())
        for p in re.split(r"\n\s*\n", re.sub(r"```.*?```", "", text, flags=re.DOTALL))
        if len(p.split()) >= 10 and not p.strip().startswith("#")
    ]
    palabras_es = re.findall(r"[a-záéíóúüñ]+", _strip_quotes_and_code(text).lower())
    mattr = _mattr_es(palabras_es)
    flags: list[dict[str, object]] = []

    if len(sent_lengths) < 4:
        return {
            "mattr_50": round(mattr, 3),
            "total_oraciones": len(sent_lengths),
        }, flags

    mean_len = statistics.mean(sent_lengths)
    std_dev = statistics.pstdev(sent_lengths)
    sent_cv = _cv(sent_lengths)
    para_cv = _cv(parrafos)
    stats: dict[str, object] = {
        "total_oraciones": len(sent_lengths),
        "media_palabras": round(mean_len, 1),
        "desviacion_std": round(std_dev, 1),
        "sentence_cv": round(sent_cv, 3),
        "paragraph_cv": round(para_cv, 3),
        "min_palabras": min(sent_lengths),
        "max_palabras": max(sent_lengths),
        "spread": max(sent_lengths) - min(sent_lengths),
        "mattr_50": round(mattr, 3),
    }

    if len(sent_lengths) >= 6 and sent_cv < 0.25:
        flags.append(
            _flag(
                "MEDIA",
                "Ritmo monótono",
                0,
                f"Cadencia muy uniforme (CV={sent_cv:.2f}, desv={std_dev:.1f}). Funde o varía alguna frase con naturalidad.",
            )
        )
    if any(
        max(sent_lengths[i : i + 4]) - min(sent_lengths[i : i + 4]) <= 2
        and sent_lengths[i] >= 10
        for i in range(len(sent_lengths) - 3)
    ):
        flags.append(
            _flag(
                "BAJA",
                "Cadencia uniforme",
                0,
                "4 oraciones seguidas con longitud casi idéntica (+/- 2 palabras).",
            )
        )
    if any(
        all(n <= 4 for n in sent_lengths[i : i + 3])
        for i in range(len(sent_lengths) - 2)
    ):
        flags.append(
            _flag(
                "MEDIA",
                "Staccato artificial",
                0,
                "3+ frases seguidas <= 4 palabras (huella típica de humanizador mecánico).",
            )
        )
    if len(palabras_es) >= 80 and mattr < 0.44:
        flags.append(
            _flag(
                "BAJA",
                "Diversidad léxica baja",
                0,
                f"MATTR-50 = {mattr:.2f} (< 0.44): revisa repeticiones de vocabulario.",
            )
        )
    return stats, flags


def _clave_apellido(texto: str) -> str:
    limpio = re.sub(
        r"^(?:véase|ver|cfr\.?|en|adaptado de|tomado de)\s+",
        "",
        texto.strip(),
        flags=re.IGNORECASE,
    )
    m = re.match(r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]+)", limpio)
    return m.group(1).lower() if m else ""


def _validar_apa(text: str) -> list[dict[str, object]]:
    """Valida fuentes prohibidas UEM y correspondencia 1 a 1 entre citas y Referencias."""
    flags = [
        _flag(
            "ALTA",
            "Fuente no académica (APA/UEM)",
            0,
            f"Fuente prohibida detectada: '{m.group(0)}'",
        )
        for pat in FUENTES_PROHIBIDAS_APA
        for m in re.finditer(pat, text, re.IGNORECASE)
    ]
    m_ref = re.search(
        r"(?im)^#{1,3}\s+(?:\d+\.?\s*)?(?:referencias|bibliograf[ií]a)\b.*$", text
    )
    if not m_ref:
        return flags

    cuerpo = text[: m_ref.start()]
    bloque_refs = text[m_ref.end() :]
    m_anexo = re.search(r"(?im)^#{1,3}\s+(?:\d+\.?\s*)?anexos?\b", bloque_refs)
    if m_anexo:
        bloque_refs = bloque_refs[: m_anexo.start()]

    if re.search(r"\bwikipedia\b", bloque_refs, re.IGNORECASE):
        flags.append(
            _flag(
                "ALTA",
                "Fuente no académica (APA/UEM)",
                0,
                "Wikipedia aparece en Referencias.",
            )
        )

    citas: set[tuple[str, str]] = set()
    for bloque in re.findall(
        r"\(([^()\n]{4,140}(?:19|20)\d{2}[a-z]?[^()\n]{0,40})\)", cuerpo
    ):
        for parte in bloque.split(";"):
            m_par = re.search(r"(.+?),\s*((?:19|20)\d{2})", parte)
            if m_par and (ap := _clave_apellido(m_par.group(1))):
                citas.add((ap, m_par.group(2)))
    for ap, anio in re.findall(
        r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]+)?)(?:\s+et\s+al\.|\s+y\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]+)?\s*\(((?:19|20)\d{2})[a-z]?\)",
        cuerpo,
    ):
        if clave := _clave_apellido(ap):
            citas.add((clave, anio))

    refs: set[tuple[str, str]] = set()
    for linea in bloque_refs.splitlines():
        limpia = linea.strip(" -*")
        m_yr = re.search(r"\(((?:19|20)\d{2})[a-z]?(?:,[^)]+)?\)", limpia)
        if m_yr and (ap := _clave_apellido(limpia)):
            refs.add((ap, m_yr.group(1)))

    faltan_en_refs = sorted(f"{ap.title()} ({an})" for ap, an in citas - refs)
    sobran_en_refs = sorted(f"{ap.title()} ({an})" for ap, an in refs - citas)
    if faltan_en_refs:
        flags.append(
            _flag(
                "ALTA",
                "APA 7 citas sin referencia",
                0,
                f"Citadas en texto pero faltan en Referencias: {', '.join(faltan_en_refs[:8])}",
            )
        )
    if sobran_en_refs:
        flags.append(
            _flag(
                "MEDIA",
                "APA 7 referencia no citada",
                0,
                f"En Referencias pero no citadas en texto: {', '.join(sobran_en_refs[:8])}",
            )
        )
    return flags


def analyze_text(
    text: str, perfil: str = "general", check_apa: bool = False
) -> dict[str, object]:
    """Analiza un texto y devuelve score (0-100), banderas y métricas estilométricas."""
    word_count = len(text.split())
    flags = [
        *_chequear_lineas(text, perfil),
        *_chequear_densidad_parrafos(text),
        *_chequear_puntuacion(text, word_count, perfil),
    ]
    burstiness_stats, rhythm_flags = _chequear_ritmo_y_staccato(text)
    flags.extend(rhythm_flags)
    if check_apa:
        flags.extend(_validar_apa(text))

    score_points = sum(PESOS_SEVERIDAD.get(str(f["severidad"]), 0) for f in flags)
    return {
        "perfil": perfil,
        "word_count": word_count,
        "ai_score": min(100, score_points),
        "flags": flags,
        "burstiness": burstiness_stats,
    }


def print_report(results: dict[str, object], filename: str | None = None) -> None:
    score = int(results["ai_score"])
    words = int(results["word_count"])
    flags = list(results["flags"])
    b = dict(results["burstiness"])
    perfil = results.get("perfil", "general")

    header = f"AUDITORIA ANTI-SLOP / ESTILOMETRIA ({perfil.upper()})"
    if filename:
        header += f": {filename}"
    print("=" * 72)
    print(header)
    print("=" * 72)

    veredicto = (
        "ALTA PROBABILIDAD DE IA (ALERTA ROJA - Revisar antes de entregar)"
        if score >= 50
        else "SOSPECHOSO (ZONA AMARILLA - Pulir hallazgos marcados)"
        if score >= 20
        else "LIMPIO / HUMANO (ZONA VERDE - Meta < 20 cumplida)"
    )
    print(f"Total palabras: {words:,}")
    print(f"Score de riesgo: {score}/100 -> {veredicto}")

    if b.get("total_oraciones", 0) >= 4:
        print("-" * 72)
        print("METRICAS DE RITMO Y DIVERSIDAD LEXICA (INFORMATIVAS):")
        print(
            f"  - Oraciones analizadas: {b['total_oraciones']} (media {b['media_palabras']} pal., desv {b['desviacion_std']})"
        )
        print(
            f"  - Coef. variacion frases (CV): {b['sentence_cv']} | parrafos (CV): {b['paragraph_cv']}"
        )
        print(
            f"  - Rango (min / max): {b['min_palabras']} / {b['max_palabras']} palabras (Spread: {b['spread']})"
        )
        print(f"  - Diversidad lexica MATTR-50: {b['mattr_50']} (meta >= 0.44)")

    print("-" * 72)
    if not flags:
        print("Cero banderas detectadas.")
    else:
        print(f"HALLAZGOS DETECTADOS ({len(flags)}):")
        for idx, f in enumerate(flags, 1):
            line_str = f"Línea {f['linea']}" if f["linea"] else "Global"
            print(
                f"  {idx}. [{f['severidad']}] [{f['tipo']}] ({line_str}): {f['detalle']}"
            )
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auditor anti-slop, ritmo en español y APA 7"
    )
    parser.add_argument(
        "path", nargs="?", default=None, help="Archivo a auditar (.txt o .md)"
    )
    parser.add_argument("--perfil", choices=["general", "academico"], default="general")
    parser.add_argument(
        "--apa",
        action="store_true",
        help="Activa chequeo de fuentes prohibidas y cruce citas-referencias",
    )
    parser.add_argument(
        "--json", action="store_true", help="Salida estructurada en JSON"
    )
    parser.add_argument(
        "--fail-on-warning", action="store_true", help="Salida 1 si score >= 20"
    )
    args = parser.parse_args()

    if args.path:
        ruta = Path(args.path)
        if not ruta.exists():
            print(f"Error: El archivo '{args.path}' no existe.", file=sys.stderr)
            sys.exit(2)
        text = ruta.read_text(encoding="utf-8", errors="replace")
        filename: str | None = ruta.name
    else:
        if sys.stdin.isatty():
            print("Pega el texto a auditar (Ctrl+D o Ctrl+Z para terminar):")
        text = sys.stdin.read()
        filename = "Entrada stdin"

    if not text.strip():
        print("Texto vacio. Nada que auditar.")
        sys.exit(0)

    results = analyze_text(text, perfil=args.perfil, check_apa=args.apa)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_report(results, filename)

    if args.fail_on_warning and int(results["ai_score"]) >= 20:
        sys.exit(1)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
