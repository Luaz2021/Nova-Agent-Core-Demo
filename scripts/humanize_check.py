#!/usr/bin/env python3
"""
humanize_check.py - Escáner forense de huellas de IA y métricas estilométricas.
Basado en la literatura de detección 2024-2026 (GPTZero, Turnitin, Wikipedia AI Cleanup,
Harshaneel Humanize, Blader Humanizer y Turnitout).

Cero dependencias externas. Ejecutable en local a 0 tokens.
Uso:
    python humanize_check.py archivo.md
    cat borrador.txt | python humanize_check.py
"""

import sys
import os
import re
import math
import argparse

# 1. Catálogo de vocabulario prohibido / clichés de IA (Inglés y Español)
BANNED_VOCAB_EN = [
    r"\bdelve\b", r"\btapestry\b", r"\btestament\b", r"\bunderscore\b",
    r"\bleverage\b", r"\butilize\b", r"\brobust\b", r"\bcomprehensive\b",
    r"\bstreamline\b", r"\bfoster\b", r"\bfacilitate\b", r"\bpivotal\b",
    r"\bnuanced\b", r"\bnotable\b", r"\bnotably\b", r"\benduring\b",
    r"\bgarner\b", r"\bit is important to note\b", r"\bit is worth noting\b",
    r"\bmultifaceted\b", r"\bin the realm of\b", r"\bthe landscape of\b",
    r"\ba myriad of\b", r"\ba plethora of\b", r"\bin conclusion\b",
    r"\bfurthermore\b", r"\bmoreover\b", r"\bgame-changer\b", r"\btransformative\b",
    r"\bindelible mark\b", r"\bserves as\b", r"\bstands as\b", r"\bboasts\b",
    r"\bvibrant\b", r"\bseamless\b", r"\bbeacon\b", r"\bintertwined\b"
]

BANNED_VOCAB_ES = [
    r"\ben conclusi[oó]n\b", r"\ben el vertiginoso mundo\b", r"\bun tapiz de\b",
    r"\bsirve como testimonio\b", r"\bes crucial destacar\b", r"\bes importante se[nñ]alar\b",
    r"\bes importante destacar\b", r"\bvale la pena mencionar\b", r"\bun sinf[ií]n de\b",
    r"\bdesempe[nñ]a un papel fundamental\b", r"\bdesempe[nñ]a un rol crucial\b",
    r"\brobusto\b", r"\baprovechar al m[aá]ximo\b", r"\bfomentar\b", r"\bfacilitar\b",
    r"\bpiedra angular\b", r"\bhito fundamental\b", r"\bhuella indeleble\b",
    r"\bpionero\b", r"\btransformador\b", r"\bde vital importancia\b",
    r"\bcuenta con una amplia gama\b", r"\balberga\b", r"\bostenta\b"
]

# 2. Patrones estructurales y sintácticos
STRUCTURAL_PATTERNS = [
    (r"\bnot\s+(?:only|just)\s+[^,;]+,?\s+but\s+(?:also\s+)?", "Paralelismo negativo ('not just X, but Y')"),
    (r"\bno\s+solo\s+[^,;]+,?\s+sino\s+(?:tambi[eé]n\s+)?", "Paralelismo negativo ('no solo X, sino también Y')"),
    (r"\bno\s+es\s+[^,;]+,?\s+es\s+", "Falso pivote ('no es X, es Y')"),
    (r"\bit'?s\s+not\s+about\s+[^,;]+,?\s+it'?s\s+about\b", "Falso pivote ('it's not about X, it's about Y')"),
    (r",\s+(?:highlighting|showcasing|symbolizing|reflecting|underscoring)\b", "Gerundio de relleno colgante (shallow -ing rider)"),
    (r",\s+(?:destacando|demostrando|reflejando|subrayando|simbolizando)\b", "Gerundio de relleno colgante en español"),
    (r"\blet\s+that\s+sink\s+in\b", "Cierre melodramático forzado ('Let that sink in')"),
    (r"\bat\s+its\s+core\b", "Trascendencia artificial ('At its core')"),
    (r"\ben\s+su\s+esencia\b", "Trascendencia artificial ('En su esencia')"),
    (r"\bhere'?s\s+the\s+thing\b", "Puesta en escena artificial ('Here's the thing')")
]

# 3. Marcas de agua invisibles y artefactos
INVISIBLE_WATERMARKS = [
    (r"[\u200B\u200C\u200D\uFEFF]", "Caracter Unicode de ancho cero (Zero-width watermark)"),
    (r"oaicite:[^\s]+", "Fuga de cita interna de OpenAI (oaicite)"),
    (r"contentReference\[[^\]]+\]", "Fuga de metadatos de cita de LLM"),
    (r"utm_source=(?:chatgpt|claude|gemini)", "Parámetro UTM de exportación de IA")
]


def split_sentences(text):
    """Divide texto en oraciones limpias."""
    # Eliminar bloques de código antes de contar
    clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'`.*?`', '', clean_text)
    # Split por puntos, signos de exclamación o interrogación seguidos de espacio o fin
    raw_sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        # Ignorar encabezados markdown puros o líneas de lista vacías
        if s_clean and not s_clean.startswith('#') and len(s_clean.split()) >= 3:
            sentences.append(s_clean)
    return sentences


def analyze_text(text):
    lines = text.splitlines()
    word_count = len(text.split())
    flags = []

    # 1. Chequeo de Marcas Invisibles y Artefactos
    for pattern, desc in INVISIBLE_WATERMARKS:
        matches = list(re.finditer(pattern, text))
        if matches:
            flags.append({
                "severidad": "CRÍTICA",
                "tipo": "Watermark / Artefacto",
                "linea": 0,
                "detalle": f"{desc} detectado ({len(matches)} ocurrencias)"
            })

    # 2. Chequeo línea por línea de vocabulario y estructura
    for i, line in enumerate(lines, 1):
        # Ignorar bloques de código en el chequeo de vocabulario
        if line.strip().startswith("```") or line.strip().startswith("`"):
            continue

        # Vocabulario inglés
        for pat in BANNED_VOCAB_EN:
            for m in re.finditer(pat, line, re.IGNORECASE):
                flags.append({
                    "severidad": "ALTA",
                    "tipo": "Vocabulario IA Cliché (EN)",
                    "linea": i,
                    "detalle": f"Término '{m.group(0)}' en: '{line.strip()[:80]}'"
                })

        # Vocabulario español
        for pat in BANNED_VOCAB_ES:
            for m in re.finditer(pat, line, re.IGNORECASE):
                flags.append({
                    "severidad": "ALTA",
                    "tipo": "Vocabulario IA Cliché (ES)",
                    "linea": i,
                    "detalle": f"Término '{m.group(0)}' en: '{line.strip()[:80]}'"
                })

        # Patrones estructurales
        for pat, desc in STRUCTURAL_PATTERNS:
            for m in re.finditer(pat, line, re.IGNORECASE):
                flags.append({
                    "severidad": "MEDIA",
                    "tipo": "Sintaxis / Estructura",
                    "linea": i,
                    "detalle": f"{desc} -> '{m.group(0)}'"
                })

    # 3. Puntuación y tipografía
    em_dashes = len(re.findall(r'—', text))
    if word_count > 0:
        em_dash_ratio = (em_dashes / word_count) * 300
        if word_count < 300 and em_dashes > 0:
            flags.append({
                "severidad": "MEDIA",
                "tipo": "Puntuación",
                "linea": 0,
                "detalle": f"{em_dashes} raya(s) larga(s) (em dash '—') en texto menor a 300 palabras. Límite: 0."
            })
        elif em_dash_ratio > 1.5:
            flags.append({
                "severidad": "MEDIA",
                "tipo": "Puntuación",
                "linea": 0,
                "detalle": f"Densidad excesiva de em dashes: {em_dashes} en {word_count} palabras (> 1 por cada 300)."
            })

    curly_quotes = len(re.findall(r'[“”‘’]', text))
    if curly_quotes > 2:
        flags.append({
            "severidad": "BAJA",
            "tipo": "Tipografía",
            "linea": 0,
            "detalle": f"{curly_quotes} comillas tipográficas curvadas ('“', '”'). Preferir comillas rectas ('\"')."
        })

    # 4. Burstiness y Distribución Métrica de Oraciones
    sentences = split_sentences(text)
    sent_lengths = [len(s.split()) for s in sentences]

    burstiness_stats = {}
    if len(sent_lengths) >= 4:
        mean_len = sum(sent_lengths) / len(sent_lengths)
        variance = sum((x - mean_len) ** 2 for x in sent_lengths) / len(sent_lengths)
        std_dev = math.sqrt(variance)
        min_len = min(sent_lengths)
        max_len = max(sent_lengths)
        spread = max_len - min_len

        # Proporción de oraciones en la zona de peligro de IA (10 a 20 palabras)
        danger_zone = sum(1 for x in sent_lengths if 10 <= x <= 20)
        danger_pct = (danger_zone / len(sent_lengths)) * 100

        burstiness_stats = {
            "total_oraciones": len(sent_lengths),
            "media_palabras": round(mean_len, 1),
            "desviacion_std": round(std_dev, 1),
            "min_palabras": min_len,
            "max_palabras": max_len,
            "spread": spread,
            "danger_zone_pct": round(danger_pct, 1)
        }

        # Regla 1: Desviación estándar baja (metrónomo)
        if std_dev < 6.0:
            flags.append({
                "severidad": "ALTA",
                "tipo": "Burstiness Deficit",
                "linea": 0,
                "detalle": f"Ritmo de metrónomo detectado: desviación estándar = {std_dev:.1f} palabras (humano típico: > 9.0)."
            })

        # Regla 2: Falta de spread (< 20 palabras entre max y min en texto mediano)
        if word_count > 100 and spread < 18:
            flags.append({
                "severidad": "ALTA",
                "tipo": "Burstiness Spread",
                "linea": 0,
                "detalle": f"Amplitud insuficiente entre la oración más larga ({max_len}) y la más corta ({min_len}): {spread} palabras (debe ser >= 20)."
            })

        # Regla 3: Concentración excesiva en la banda 10-20
        if danger_pct > 55.0:
            flags.append({
                "severidad": "MEDIA",
                "tipo": "Agrupamiento de Longitud",
                "linea": 0,
                "detalle": f"{danger_pct:.1f}% de las oraciones están en la banda 10-20 palabras (límite recomendado: < 45%)."
            })

        # Regla 4: Tres oraciones consecutivas idénticas (+/- 3 palabras)
        for idx in range(len(sent_lengths) - 2):
            w1, w2, w3 = sent_lengths[idx], sent_lengths[idx+1], sent_lengths[idx+2]
            if max(w1, w2, w3) - min(w1, w2, w3) <= 3 and w1 >= 10:
                flags.append({
                    "severidad": "MEDIA",
                    "tipo": "Cadencia Uniforme",
                    "linea": 0,
                    "detalle": f"3 oraciones consecutivas con longitud casi idéntica ({w1}, {w2}, {w3} palabras)."
                })
                break

    # Cálculo de Score de Probabilidad de IA (0 a 100)
    score_points = 0
    for f in flags:
        if f["severidad"] == "CRÍTICA":
            score_points += 35
        elif f["severidad"] == "ALTA":
            score_points += 15
        elif f["severidad"] == "MEDIA":
            score_points += 8
        elif f["severidad"] == "BAJA":
            score_points += 3

    ai_score = min(100, score_points)

    return {
        "word_count": word_count,
        "ai_score": ai_score,
        "flags": flags,
        "burstiness": burstiness_stats
    }


def print_report(results, filename=None):
    score = results["ai_score"]
    words = results["word_count"]
    flags = results["flags"]
    b = results["burstiness"]

    header = f"AUDITORIA FORENSE ANTI-SLOP / DETECCION IA"
    if filename:
        header += f": {filename}"
    print("=" * 70)
    print(header)
    print("=" * 70)

    # Estado del semáforo
    if score >= 60:
        veredicto = "ALTA PROBABILIDAD DE IA (ALERTA ROJA - Disparara GPTZero/Turnitin)"
    elif score >= 25:
        veredicto = "SOSPECHOSO (ZONA AMARILLA - Patrones hibridos detectables)"
    else:
        veredicto = "LIMPIO / HUMANO (ZONA VERDE - Huella estadistica organica)"

    print(f"Total palabras: {words:,}")
    print(f"Score de riesgo de IA: {score}/100 -> {veredicto}")

    if b:
        print("-" * 70)
        print("METRICAS DE BURSTINESS & RITMO (GPTZero Core):")
        print(f"  - Oraciones analizadas: {b['total_oraciones']}")
        print(f"  - Longitud media: {b['media_palabras']} palabras")
        print(f"  - Desviacion estandar (sigma): {b['desviacion_std']} (Meta: >= 9.0)")
        print(f"  - Rango (min / max): {b['min_palabras']} / {b['max_palabras']} palabras (Spread: {b['spread']})")
        print(f"  - Concentracion en banda 10-20: {b['danger_zone_pct']}% (Meta: < 45%)")

    print("-" * 70)
    if not flags:
        print("Cero banderas detectadas. El texto no presenta sesgos evidentes de LLM.")
    else:
        print(f"HALLAZGOS DETECTADOS ({len(flags)}):")
        for idx, f in enumerate(flags, 1):
            line_str = f"Línea {f['linea']}" if f['linea'] > 0 else "Global"
            print(f"  {idx}. [{f['severidad']}] [{f['tipo']}] ({line_str}):")
            print(f"     {f['detalle']}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Auditor forense de texto contra detectores de IA")
    parser.add_argument("path", nargs="?", default=None, help="Ruta al archivo a auditar (.txt o .md)")
    parser.add_argument("--fail-on-warning", action="store_true", help="Retornar codigo de salida 1 si score >= 30")
    args = parser.parse_args()

    if args.path:
        if not os.path.exists(args.path):
            print(f"Error: El archivo '{args.path}' no existe.", file=sys.stderr)
            sys.exit(2)
        with open(args.path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        filename = os.path.basename(args.path)
    else:
        if sys.stdin.isatty():
            print("Pega el texto a auditar (presiona Ctrl+D o Ctrl+Z para terminar):")
        text = sys.stdin.read()
        filename = "Entrada stdin"

    if not text.strip():
        print("Texto vacio. Nada que auditar.")
        sys.exit(0)

    results = analyze_text(text)
    print_report(results, filename)

    if args.fail_on_warning and results["ai_score"] >= 30:
        sys.exit(1)


if __name__ == "__main__":
    main()
