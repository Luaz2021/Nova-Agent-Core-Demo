"""Coste por modelo y % del cupo semanal de Antigravity.

20/11/2026 (Claude, medido con el usuario). 24/11/2026 (Claude): Antigravity 2.35 tiene DOS bolsas (visor View Usage):
  - "Gemini Models": TODOS los Gemini (Hydrogen, Neon, Carbon, el orquestador...) en una sola bolsa que se gasta
    segun el precio de la API de cada modelo (blog oficial "changes to antigravity plans").
  - "Claude and GPT models": Claude Opus/Sonnet y GPT, bolsa aparte.
  Cada bolsa tiene limite semanal y de 5 horas. Gemini 3.8 Flash y Gemini 4 Argon se retiran el 30/11/2026: la base
  de Nova pasa a Hydrogen y la escalera pesada a Carbon/Neon.

Una sola fuente de verdad para nova_hook.py (freno de gasto), nova_hook_turno.py (vigilante del orquestador) y los
informes. Nada de red: solo lee el transcript.jsonl de la conversacion.

- Tokens REALES = nuevos + cache al 10 % + salida (como siempre).
- Coste PONDERADO = reales x peso del modelo DENTRO de su bolsa (Hydrogen = 1; Neon/Carbon/orquestador ~4 por precio
  de API; Claude Opus 10 frente a Sonnet 4). PESOS Y CUPO_1PC SON ESTIMACIONES: se recalibran con capturas del visor
  (memory\\registros\\cupo_lecturas.txt) antes y despues de una tarea medida.
"""

import json

PRECIO_CACHE = 0.10
PESO = {"gemini": 1, "pesado": 4, "claude": 4, "claude_opus": 10, "gpt": 1}
BOLSA = {"gemini": "gemini", "pesado": "gemini", "claude": "claude_gpt", "claude_opus": "claude_gpt", "gpt": "claude_gpt"}
# tokens PONDERADOS que gastan ~1 % de cada limite. CALIBRADO el 25/11 con el visor (memory\registros\cupo_lecturas.txt):
# Hydrogen 307k reales + Neon High 145k reales (x4) = ~886k ponderados -> 5h bajo ~4 % (100 -> 96) y semanal ~1 %
# (91 -> 90). Una sola llamada de Neon High (39k reales) bajo 1 % del 5h: peso 4 plausible. El visor redondea a enteros:
# el SEMANAL es el mas impreciso (puede ser entre ~470k y bastante mas); afinar con mas lecturas. claude_gpt: sin medir.
CUPO_1PC = {"gemini": 880_000, "claude_gpt": None}  # semanal
CUPO_1PC_5H = {"gemini": 220_000, "claude_gpt": None}  # limite de 5 horas (el que antes se agota)
NOMBRE_CUPO = {"gemini": "Gemini", "claude_gpt": "Claude/GPT"}


def familia(modelo: str) -> str:
    m = (modelo or "").lower()
    if "claude" in m:
        return "claude_opus" if "opus" in m else "claude"
    if "gpt" in m:
        return "gpt"
    if any(k in m for k in ("orchestrator", "neon", "argon", "carbon")) or m.endswith("-pro") or "-pro-" in m:
        return "pesado"
    return "gemini"  # Hydrogen (tambien el asesor tiered-xhigh y el ejecutor flash-worker del orquestador) y Flash


def medir(transcript: str) -> dict:
    """Mide una conversacion. Devuelve un dict con todo lo que necesitan el hook, el vigilante y los informes."""
    r = {
        "nuevos": 0, "cache": 0, "salida": 0, "contexto": 0, "seguidas": 0, "llamadas": 0,
        "relevos": 0, "revisiones": 0, "caches_perdidas": 0, "orquestador": False,
        "por_familia": {}, "por_modelo": {},
    }
    previo, ctx_previo = None, 0
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for linea in f:
                if "[plan review" in linea:
                    r["revisiones"] += linea.count("[plan review due]")
                try:
                    o = json.loads(linea)
                except ValueError:
                    continue
                tipo = o.get("type")
                if tipo == "USER_INPUT":
                    r["seguidas"] = 0
                r["seguidas"] += len(o.get("tool_calls") or [])
                if tipo != "PLANNER_RESPONSE":
                    continue
                modelo = str(o.get("model") or "?")
                n, c, s = (int(o.get(k) or 0) for k in ("input_tokens", "cache_read_tokens", "output_tokens"))
                real = n + c * PRECIO_CACHE + s
                fam = familia(modelo)
                r["nuevos"] += n
                r["cache"] += c
                r["salida"] += s
                r["llamadas"] += 1
                r["contexto"] = n + c
                r["por_familia"][fam] = r["por_familia"].get(fam, 0) + real
                pm = r["por_modelo"].setdefault(modelo, {"llamadas": 0, "real": 0, "nuevos": 0})
                pm["llamadas"] += 1
                pm["real"] += real
                pm["nuevos"] += n
                if "orchestrator" in modelo:
                    r["orquestador"] = True
                if previo and modelo != previo:
                    r["relevos"] += 1
                elif previo and n > 30_000 and ctx_previo > 30_000:
                    r["caches_perdidas"] += 1  # mismo modelo y vuelve a pagar >30k de golpe
                previo, ctx_previo = modelo, n + c
    except OSError:
        pass
    r["real"] = int(r["nuevos"] + r["cache"] * PRECIO_CACHE + r["salida"])
    r["bruto"] = r["nuevos"] + r["cache"] + r["salida"]
    r["ponderado"] = int(sum(v * PESO.get(f, 1) for f, v in r["por_familia"].items()))
    por_bolsa: dict[str, float] = {}
    for f, v in r["por_familia"].items():
        b = BOLSA.get(f, "gemini")
        por_bolsa[b] = por_bolsa.get(b, 0) + v * PESO.get(f, 1)
    r["por_bolsa"] = {k: int(v) for k, v in por_bolsa.items()}
    r["pct"] = {k: round(por_bolsa.get(k, 0) / v, 2) for k, v in CUPO_1PC.items() if v}
    r["pct_5h"] = {k: round(por_bolsa.get(k, 0) / v, 2) for k, v in CUPO_1PC_5H.items() if v}
    return r


def linea_cupo(r: dict) -> str:
    """'~0.9 % Gemini (5h ~3.6 %) + 120k ponderados Claude/GPT' (solo las bolsas con gasto). El texto lo sigue
    rematando el que llama con 'del cupo semanal': el % principal es el semanal; el de 5h va entre parentesis."""
    trozos = [f"~{r['pct'][k]:.1f} % {NOMBRE_CUPO[k]} (5h ~{r.get('pct_5h', {}).get(k, 0):.1f} %)"
              for k in r.get("pct", {}) if r["pct"][k]]
    for k, v in (r.get("por_bolsa") or {}).items():
        if v and not CUPO_1PC.get(k):
            trozos.append(f"{v // 1000}k ponderados {NOMBRE_CUPO.get(k, k)}")
    return " + ".join(trozos) or "0 %"
