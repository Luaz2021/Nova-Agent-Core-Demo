r"""
NOVA · REVISOR SEMANAL
=============================================================
Que hizo Nova, cuanto gasto y donde fallo. Lo lee TODO en local (0 tokens).

  --recolectar   Guarda un resumen de cada conversacion de brain\ en memory\registros\actividad_nova.json
                 (Antigravity borra conversaciones viejas: asi no se pierden). Lo lanza auto_save_session.ps1 al
                 cerrar Antigravity y la tarea semanal.
  --informe      Escribe documentos_generados\informes_nova\informe_<fecha>.md con los ultimos --dias (7).

Uso:  <PYTHON> <NOVA_HOME>\antigravity\scripts\nova_revisor.py --recolectar --informe [--dias 7]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

A = Path.home() / ".gemini" / "antigravity"
BRAIN = A / "brain"
REG = A / "memory" / "registros"
LIBRO = REG / "actividad_nova.json"
TELEMETRIA = REG / "telemetria_hooks.jsonl"
SALIDA = A / "documentos_generados" / "informes_nova"

HERRAMIENTAS_LOCALES = {
    "redactor": r"redactor\.py", "resumir": r"resumir\.py|conversor\.py", "biblioteca webs": r"montar\.py",
    "obrero local (Qwen)": r"nova_local_worker\.py", "ia local": r"nova_instalar_ia_local\.py",
    "video local": r"nova_video_router\.py", "actualizador": r"actualizar_nova\.py",
}
RE_PY_ATAJO = re.compile(r"(?i)(^|[;&|(]|\bcmd(\.exe)?\s+/[ck]\s+\"?)\s*(python3?|py)(\.exe)?(?=\s|$)")
RE_DOC_SCRATCH = re.compile(r"(?i)[\\/]scratch[\\/][^\"'|;&<>\n]*\.(pdf|docx|xlsx|pptx)\b")
RE_FALLO = re.compile(r"exited with code (-?\d+)")
RE_CONV_REAL = re.compile(r"^[0-9a-f]{8}$")
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


def cuando(c: dict) -> str:
    d = local(c.get("inicio", ""))
    return f"{DIAS[d.weekday()]} {d:%d/%m %H:%M}" if d else "?"


def local(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    except (ValueError, AttributeError):
        return None


def resumir_conversacion(f: Path) -> dict:
    conv = f.parents[2].name
    r = {"conv": conv, "inicio": "", "fin": "", "titulo": "", "mensajes": 0, "llamadas_modelo": 0, "tokens_nuevos": 0,
         "tokens_cache": 0, "tokens_salida": 0, "herramientas": collections.Counter(), "locales": collections.Counter(),
         "cmd_fallidos": 0, "fallos_muestra": [], "errores": 0, "racha_max": 0, "adjuntos_nube": 0, "adjuntos_local": 0,
         "avisos_hook": 0, "python_atajo": 0, "docs_scratch": [], "repetidos": 0, "web": 0}
    racha, comandos = 0, collections.Counter()
    for linea in f.open(encoding="utf-8", errors="replace"):
        try:
            o = json.loads(linea)
        except ValueError:
            continue
        t = o.get("created_at", "")
        if t:
            r["inicio"] = r["inicio"] or t
            r["fin"] = t
        tipo = o.get("type")
        if tipo == "USER_INPUT":
            r["mensajes"] += 1
            racha = 0
            texto = str(o.get("content", "")).split("</USER_REQUEST>")[0].replace("<USER_REQUEST>", "").strip()
            if not r["titulo"]:
                r["titulo"] = re.sub(r"\s+", " ", re.sub(r"\[adjunto local:[^\]]*\]", "[adjunto]", texto))[:90]
            r["adjuntos_nube"] += len(o.get("media") or [])
            r["adjuntos_local"] += texto.count("[adjunto local:")
        elif tipo == "PLANNER_RESPONSE":
            r["llamadas_modelo"] += 1
            r["tokens_nuevos"] += o.get("input_tokens") or 0
            r["tokens_cache"] += o.get("cache_read_tokens") or 0
            r["tokens_salida"] += o.get("output_tokens") or 0
            for tc in o.get("tool_calls") or []:
                nombre = tc.get("name", "?")
                r["herramientas"][nombre] += 1
                racha += 1
                r["racha_max"] = max(r["racha_max"], racha)
                args = json.dumps(tc.get("args") or {}, ensure_ascii=False)
                cmd = str((tc.get("args") or {}).get("CommandLine", ""))
                if nombre in ("search_web", "read_url_content") or "browser" in nombre:
                    r["web"] += 1
                for etiqueta, patron in HERRAMIENTAS_LOCALES.items():
                    if re.search(patron, args, re.I):
                        r["locales"][etiqueta] += 1
                if cmd and RE_PY_ATAJO.search(cmd):
                    r["python_atajo"] += 1
                if RE_DOC_SCRATCH.search(args.replace("\\\\", "\\")) and re.search(r"write|edit|run_command", nombre):
                    r["docs_scratch"].append(re.search(RE_DOC_SCRATCH, args.replace("\\\\", "\\")).group(0)[-60:])
                if cmd:
                    comandos[cmd[:200]] += 1
        elif tipo == "EPHEMERAL_MESSAGE":
            r["avisos_hook"] += 1
        elif tipo == "GENERIC":
            c = str(o.get("content", ""))
            m = RE_FALLO.search(c)
            if (m and m.group(1) != "0") or o.get("status") == "ERROR":
                r["cmd_fallidos"] += 1
                if len(r["fallos_muestra"]) < 3:
                    trozo = c.split("Command output:", 1)[-1] if "Command output:" in c else (o.get("error") or c)
                    r["fallos_muestra"].append(re.sub(r"\s+", " ", str(trozo))[:140])
        if o.get("error"):
            r["errores"] += 1
    r["repetidos"] = sum(1 for n in comandos.values() if n >= 3)
    r["herramientas"] = dict(r["herramientas"])
    r["locales"] = dict(r["locales"])
    r["actualizado"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return r


def leer_libro() -> dict:
    try:
        return json.loads(LIBRO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def recolectar() -> int:
    libro = leer_libro()
    n = 0
    for f in BRAIN.glob("*/.system_generated/logs/transcript_full.jsonl"):
        try:
            libro[f.parents[2].name] = resumir_conversacion(f)
            n += 1
        except OSError:
            continue
    REG.mkdir(parents=True, exist_ok=True)
    LIBRO.write_text(json.dumps(libro, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


def alertas(c: dict) -> list[str]:
    a = []
    # 09/11: tokens REALES = nuevos + cache al 10 % (descuento de Gemini) + salida; mismo tope que el freno (300k)
    real = c["tokens_nuevos"] + c["tokens_cache"] // 10 + c["tokens_salida"]
    if real > 300_000:
        a.append(f"conversacion CARA (~{real // 1000}k reales: {c['tokens_nuevos']:,} nuevos + {c['tokens_cache']:,} de cache al 10 %"
                 f" + {c['tokens_salida']:,} de salida)")
    if c["racha_max"] >= 12:
        a.append(f"{c['racha_max']} herramientas seguidas sin hablar contigo (posible bucle)")
    if c["cmd_fallidos"] >= 3:
        a.append(f"{c['cmd_fallidos']} comandos fallidos")
    if c["repetidos"]:
        a.append(f"{c['repetidos']} comando(s) repetido(s) 3+ veces")
    if c["adjuntos_nube"]:
        a.append(f"{c['adjuntos_nube']} adjunto(s) subidos a la nube (sin la aduana)")
    if c["python_atajo"]:
        a.append(f"{c['python_atajo']} vez/veces 'python' a secas")
    if c["docs_scratch"]:
        a.append(f"documento(s) en scratch: {', '.join(c['docs_scratch'][:2])}")
    return a


def informe(dias: int) -> Path:
    desde = datetime.now().astimezone() - timedelta(days=dias)
    convs = [c for c in leer_libro().values() if (local(c.get("fin", "")) or desde) >= desde]
    convs.sort(key=lambda c: c.get("inicio", ""))
    tel = []
    try:
        for linea in TELEMETRIA.open(encoding="utf-8", errors="replace"):
            try:
                d = json.loads(linea)
            except ValueError:
                continue
            try:
                # solo conversaciones reales de Nova (id hexadecimal); fuera las pruebas (prueba_*, bateria, c1...).
                # Los errores del propio hook (no traen conv) se guardan aparte con su fecha.
                if datetime.strptime(d.get("t", ""), "%Y-%m-%d %H:%M:%S").astimezone() >= desde and \
                        (RE_CONV_REAL.match(str(d.get("conv", ""))) or d.get("error_hook")):
                    tel.append(d)
            except ValueError:
                pass
    except OSError:
        pass

    tn = sum(c["tokens_nuevos"] for c in convs)
    tc = sum(c["tokens_cache"] for c in convs)
    ts = sum(c["tokens_salida"] for c in convs)
    loc = collections.Counter()
    herr = collections.Counter()
    for c in convs:
        loc.update(c["locales"])
        herr.update(c["herramientas"])
    cmds = herr.get("run_command", 0)
    usos_locales = sum(loc.values())
    hoy = datetime.now()
    L = [f"# Informe semanal de Nova · {(hoy - timedelta(days=dias)):%d/%m} – {hoy:%d/%m/%Y}", "",
         "_Generado en local por `scripts/nova_revisor.py` (0 tokens). Si quieres ayudar a mejorar Nova, envialo con /enviar-informe._", "",
         "## 1. Resumen", "",
         f"| Conversaciones | Mensajes tuyos | Llamadas al modelo | Tokens nuevos | Tokens de cache | Tokens de salida | **Tokens REALES** |",
         f"|---|---|---|---|---|---|---|",
         f"| {len(convs)} | {sum(c['mensajes'] for c in convs)} | {sum(c['llamadas_modelo'] for c in convs)} | {tn:,} | {tc:,} | {ts:,} | **{tn + tc // 10 + ts:,}** |", "",
         "_Tokens reales = nuevos + cache al 10 % (Gemini cobra la cache con un 90 % de descuento) + salida._", "",
         f"- **Herramientas locales (Capa 0, 0 tokens):** {usos_locales} usos de {cmds} comandos"
         + (f" → {', '.join(f'{k} ×{v}' for k, v in loc.most_common())}" if loc else " → **ninguna** (todo en la nube)"),
         f"- **Busquedas/navegacion web:** {sum(c['web'] for c in convs)}",
         f"- **Adjuntos:** {sum(c['adjuntos_local'] for c in convs)} por la aduana (local) · "
         f"{sum(c['adjuntos_nube'] for c in convs)} subidos a la nube", ""]

    malas = [(c, alertas(c)) for c in convs]
    malas = [(c, a) for c, a in malas if a]
    L += ["## 2. Donde fallo (alertas)", ""]
    if not malas:
        L.append("Sin alertas esta semana ✅")
    for c, a in malas:
        L.append(f"- **{cuando(c)}** · _{c['titulo'] or c['conv'][:8]}_ (`{c['conv'][:8]}`)")
        L += [f"  - ⚠️ {x}" for x in a]
        L += [f"  - fallo: `{m}`" for m in c["fallos_muestra"][:2]]
    L.append("")

    # Aprendizaje (Ley 3): lecciones del inbox y entradas de la napkin con fecha dentro de la semana
    def fechas(archivo: Path, patron: str) -> list[str]:
        try:
            return [m for m in re.findall(patron, archivo.read_text(encoding="utf-8", errors="replace"))
                    if m >= f"{desde:%Y-%m-%d}"]
        except OSError:
            return []
    lecciones = fechas(A / "memory" / "inbox_lecciones.md", r"(?m)^- \[(\d{4}-\d{2}-\d{2})\]")
    napkin = fechas(A / "memory" / "napkin-global.md", r"\*\*\[(\d{4}-\d{2}-\d{2})\]")
    pedidas = sum(1 for d in tel if d.get("decision") == "pedir_leccion")
    fallos_semana = sum(c["cmd_fallidos"] for c in convs)
    L += ["## 3. Aprendizaje (lecciones y napkin)", "",
          f"- **Lecciones nuevas en `inbox_lecciones.md`:** {len(lecciones)} (el hook se las pidio a Nova {pedidas} veces)",
          f"- **Entradas nuevas en la napkin:** {len(napkin)}"]
    insistidas = sum(1 for d in tel if d.get("decision") == "leccion_continue")
    en_bruto = sum(1 for d in tel if d.get("decision") == "leccion_en_bruto")
    if insistidas or en_bruto:
        L.append(f"- Nova ignoro el aviso {insistidas} veces (el Stop le insistio); {en_bruto} las apunto el hook en bruto "
                 "como `[revisar]` en el inbox: pasarlas a limpio con Claude.")
    if fallos_semana >= 3 and not lecciones:
        L.append(f"- ⚠️ Hubo {fallos_semana} comandos fallidos y **ninguna leccion apuntada**: revisar con Claude y /destilar.")
    L += ["- Recordatorio: `/destilar` (con Claude) mueve las lecciones del inbox a su `index-*` o a la napkin y vacia el inbox.", ""]

    dec = collections.Counter(d.get("decision", "?") for d in tel if d.get("herramienta"))
    motivos = collections.Counter((d.get("decision"), str(d.get("motivo", ""))[:110]) for d in tel
                                  if d.get("decision") in ("deny", "force_ask", "ask") and d.get("motivo"))
    pre = collections.Counter(d.get("decision") for d in tel if d.get("evento") == "PreInvocation")
    errores_hook = [d for d in tel if d.get("error_hook")]
    L += ["## 4. Lo que frenaron los hooks", "",
          f"- Decisiones sobre herramientas: {', '.join(f'{k} {v}' for k, v in dec.most_common()) or 'ninguna'}",
          f"- Avisos antes de pensar: {', '.join(f'{k} {v}' for k, v in pre.most_common()) or 'ninguno'}"]
    for (d, m), n in motivos.most_common(8):
        L.append(f"  - **{d}** ×{n}: {m}")
    if errores_hook:
        L.append(f"- ❌ **{len(errores_hook)} errores dentro de los hooks** (ultimo {errores_hook[-1].get('t')}: "
                 f"`{errores_hook[-1].get('error_hook')}`). Si son de dias de pruebas, ignorar.")
    L.append("")

    L += ["## 5. Conversaciones", "", "| Cuando | Tema | Msjs | Herram. | Tokens nuevos | Cache | Fallos | Racha |",
          "|---|---|---|---|---|---|---|---|"]
    for c in convs:
        L.append(f"| {cuando(c)} | {(c['titulo'] or '-')[:45].replace('|', '/')} | {c['mensajes']} | "
                 f"{sum(c['herramientas'].values())} | {c['tokens_nuevos']:,} | {c['tokens_cache']:,} | {c['cmd_fallidos']} | {c['racha_max']} |")
    L.append("")

    L += ["## 6. Estado de los servicios", ""]
    for nombre, f, patron in [("Centinela anti-suspension", A / "sentinel.log", r"Error|ALERTA")]:
        try:
            lineas = [x for x in f.read_text(encoding="utf-8", errors="replace").splitlines()[-2000:] if re.search(patron, x, re.I)]
            L.append(f"- **{nombre}:** {len(lineas)} avisos/errores recientes" + (f" (ultimo: `{lineas[-1][:110]}`)" if lineas else " ✅"))
        except OSError:
            L.append(f"- **{nombre}:** sin registro")
    L += ["", "---", "_Umbrales de alerta: >300k tokens reales por conversacion, 12+ herramientas seguidas, 3+ comandos "
          "fallidos, comandos repetidos 3+ veces, adjuntos a la nube, 'python' a secas, documentos en scratch._"]

    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"informe_{hoy:%Y-%m-%d}.md"
    destino.write_text("\n".join(L) + "\n", encoding="utf-8")
    return destino


def main() -> int:
    ap = argparse.ArgumentParser(description="Revisor semanal de Nova (0 tokens)")
    ap.add_argument("--recolectar", action="store_true")
    ap.add_argument("--informe", action="store_true")
    ap.add_argument("--dias", type=int, default=7)
    a = ap.parse_args()
    if not (a.recolectar or a.informe):
        a.recolectar = a.informe = True
    if a.recolectar:
        n = recolectar()
        print(f"[revisor] {n} conversaciones resumidas en {LIBRO}")
    if a.informe:
        print(f"[revisor] informe: {informe(a.dias)}")
    return 0


if __name__ == "__main__":
    import sys
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
