import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
LEGADO · CONSTRUIR CON QWEN DESDE CERO (cadena B, retirada)

La cadena oficial es  analizar.py -> crear.py (copia fiel, sin IA) -> verificar.py (Qwen solo repara).
Este archivo sigue siendo la biblioteca que usa verificar.py (preguntar, revision_html, vestir_final...),
pero escribir la web desde cero con Qwen solo se hace pidiéndolo explícitamente:

  python construir.py --legacy [carpeta] [--pausa] [--umbral=80]   (Qwen escribe cada sección desde cero)
  python construir.py --vestir [carpeta]                           (solo vestir index.html con medios libres)

Entrada (en pruebas_Qwen/<web>/):
  fichas_secciones.md          medidas de cada sección (lo genera analizar.py)
  claude/diseno.json           sistema de diseño que define Claude (colores y fuentes con nombre) — opcional
  claude/sec_N.md              instrucciones cortas de Claude para la sección N — opcional
                               (si no existen, Qwen trabaja solo con la ficha)
Proceso, sección por sección (empezando por la cabecera):
  Qwen escribe la sección (~2.000 tokens) -> el verificador la compara con la original en PC y móvil
  -> si no llega al umbral, Qwen la corrige con las diferencias exactas (máx. 2 veces)
  -> se queda la mejor versión -> revision.html se actualiza
Salida (pruebas_Qwen/<web>/construccion/):
  index.html            el esqueleto verificado (marcos de color en lugar de fotos y vídeos)
  index_final.html      la misma página vestida con medios de libre uso (medios_libres.json)
  revision.html         original | Qwen, PC y móvil, nota y diferencias de cada sección
  pendientes_nova.md  las secciones que Qwen no consiguió arreglar (lo que repara Claude)
  analisis_fallos_qwen.md  forense: código de Qwen, qué midió el verificador, reintentos y tipo de fallo
  (y en pruebas_Qwen/: donde_falla_qwen.md con la estadística de todas las webs)
"""
import html as H
import json
import re
import shutil
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
import comparar as cmp  # noqa: E402
import medios  # noqa: E402
try:
    import auto_planos  # noqa: E402
except Exception:
    auto_planos = None
try:
    import comprimir_para_nova  # noqa: E402
except Exception:
    comprimir_para_nova = None

OLLAMA = "http://127.0.0.1:11434"


def _modelo_nova(clave, defecto):
    try:
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8")).get(clave, defecto)
    except Exception:
        return defecto


MODELO = _modelo_nova("coder", "qwen3.5:9b")
# Qwen 2.5 Coder escribe hasta 8K tokens por respuesta. Entrada + salida tienen que caber en num_ctx: con 24K caben
# ~15K de entrada (sección + plano + diferencias) y la salida entera. Medido en una RTX de 8 GB: 5,5 GB de VRAM.
# (El contexto de 128K del modelo no cabe en 8 GB: solo la memoria del contexto pasaría de 7 GB.)
NUM_PREDICT = 8192
NUM_CTX = 24576
# HTML con clases de Tailwind medido con el tokenizador de Qwen: 1,8-2,1 caracteres por token (no los ~4 de un texto).
CAR_POR_TOKEN = 1.85
OPC = {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT, "temperature": 0, "seed": 42}


def log(m):
    print(m, flush=True)


def preguntar(prompt, system):
    datos = {"model": MODELO, "prompt": prompt, "system": system, "stream": False, "think": False, "options": OPC}
    for i in range(3):
        try:
            req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(datos).encode(), headers={"Content-Type": "application/json"})
            t = time.time()
            with urllib.request.urlopen(req, timeout=900) as r:
                j = json.loads(r.read())
            log(f"      Qwen: {time.time() - t:.0f} s ({j.get('prompt_eval_count', 0)}+{j.get('eval_count', 0)} tokens)")
            if j.get("done_reason") == "length":         # se quedó sin salida: la sección vendrá cortada (el validador la descarta)
                log(f"      ojo: la respuesta se cortó en {NUM_PREDICT} tokens (sección demasiado larga para una sola respuesta)")
            return j.get("response", "")
        except Exception as e:
            log(f"      error con Ollama ({e}), reintento {i + 1}/3")
            time.sleep(5)
    return ""


def sistema_qwen(diseno):
    guia = (BASE / "GUIA_QWEN.md").read_text(encoding="utf-8")
    m = re.search(r"## B\..*?```\n(.*?)```", guia, re.S)
    s = m.group(1) if m else guia
    if diseno:
        cols = ", ".join(f"{k} = {v}" for k, v in diseno.get("colores", {}).items())
        fts = ", ".join(f"font-{k} = {v}" for k, v in diseno.get("fuentes", {}).items())
        s += f"\nSISTEMA DE DISEÑO DE ESTA WEB (úsalo con estos nombres):\n- colores: {cols} -> bg-NOMBRE, text-NOMBRE, border-NOMBRE\n- fuentes: {fts}\n"
        if diseno.get("notas"):
            s += f"- notas: {diseno['notas']}\n"
    return s


def ficha_de(fichas, n):
    m = re.search(rf"## Sección {n}\n(.*?)(?=\n## Sección |\Z)", fichas, re.S)
    cab = fichas.split("\n## Sección")[0]
    return (cab.strip() + "\n\n## Sección " + str(n) + "\n" + m.group(1).strip()) if m else ""


def limpiar(t, n):
    m = re.search(r"```(?:html)?\s*(.*?)```", t, re.S)
    t = m.group(1) if m else t
    t = re.sub(r"(?is)<!doctype.*?<body[^>]*>|</body>.*|<(script|style)[^>]*>.*?</\1>", "", t)
    i = t.find("<")
    t = t[i:].strip() if i >= 0 else "<section></section>"
    return t if f"SECCIÓN {n}" in t[:60] else f"<!-- SECCIÓN {n} -->\n{t}"


def pagina(secciones, diseno, titulo):
    fuentes = sorted(set((diseno or {}).get("fuentes", {}).values()) | {"Inter"})
    fam = "&".join("family=" + f.replace(" ", "+") + ":wght@300;400;500;600;700;800" for f in fuentes)
    conf = {"theme": {"extend": {"colors": (diseno or {}).get("colores", {}),
                                 "fontFamily": {k: [v, "sans-serif"] for k, v in (diseno or {}).get("fuentes", {}).items()}}}}
    cuerpo = "\n".join(f'<div data-clon-sec="{n}">\n{secciones[n]}\n</div>' for n in sorted(secciones))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{H.escape(titulo)}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config = {json.dumps(conf)}</script>
<link href="https://fonts.googleapis.com/css2?{fam}&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
<style>body{{margin:0;font-family:'{list((diseno or {}).get("fuentes", {"t": "Inter"}).values())[-1]}',sans-serif}}</style>
</head><body>
{cuerpo}
</body></html>
"""


def revision_html(estado, ref_dir, img_dir, titulo):
    filas = []
    for n in sorted(estado):
        e = estado[n]
        color = ("#6366f1" if e["estado"].startswith("escena") else "#16a34a" if e["nota"] >= e["umbral"]
                 else ("#ca8a04" if e["nota"] >= e["umbral"] - 15 else "#dc2626"))
        difs = "".join(f"<li>{H.escape(d)}</li>" for d in e["diferencias"][:8]) or "<li>sin diferencias medibles</li>"
        imgs = ""
        for vista, rv in (("pc", "escritorio"), ("movil", "movil")):
            o, g = f"img/orig_{n}_{vista}.png", f"img/gen_{n}_{vista}.png"
            imgs += f'<div class="par {vista}"><div><b>Original {vista}</b><img src="{o}"></div><div><b>Qwen {vista}</b><img src="{g}"></div></div>'
        filas.append(f'<section><h2>Sección {n} <span style="background:{color}">{e["nota"]}%</span> '
                     f'<small>PC {e["pc"]}% · móvil {e["movil"]}% · {e["intentos"]} intento(s) · {e["estado"]}</small></h2>{imgs}<ul>{difs}</ul></section>')
    normales = [e for e in estado.values() if not e["estado"].startswith("escena")]
    total = round(sum(e["nota"] for e in normales) / max(len(normales), 1))
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisión {H.escape(titulo)}</title><meta http-equiv="refresh" content="15">
<style>body{{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f4f4f5;color:#18181b}}h1{{margin:0 0 12px}}
section{{background:#fff;border-radius:10px;padding:14px;margin:0 0 16px;box-shadow:0 1px 3px #0002}}
h2{{font-size:18px;margin:0 0 10px}}h2 span{{color:#fff;padding:2px 8px;border-radius:6px;margin-left:6px}}small{{color:#71717a;font-weight:400;margin-left:8px}}
.par{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}}.movil{{grid-template-columns:300px 300px}}.par img{{width:100%;border:1px solid #e4e4e7;display:block}}
.par b{{font-size:12px;color:#52525b}}ul{{margin:6px 0 0;padding-left:18px;font-size:13px;color:#3f3f46}}</style></head>
<body><h1>Revisión sección por sección · media {total}%</h1>
<p style="color:#52525b">Verde = aprobada · amarillo = cerca · rojo = la repara Claude · morado = escena 3D/animada (va el vídeo). La página se recarga sola cada 15 s.</p>
{''.join(filas)}</body></html>"""


def copiar_imgs(n, ref_dir, med_dir, img_dir):
    for vista, rv in (("pc", "escritorio"), ("movil", "movil")):
        o = Path(ref_dir) / f"sec_{n}_{rv}.png"
        g = Path(med_dir) / f"gen_{n}_{rv}.png"
        if o.exists():
            shutil.copy(o, img_dir / f"orig_{n}_{vista}.png")
        if g.exists():
            shutil.copy(g, img_dir / f"gen_{n}_{vista}.png")


# ---------------------------------------------------------------- análisis forense de los fallos de Qwen
TIPOS_FALLO = [
    ("tamaño de letra (redondea o no pone md:)", r"tamaño \d+px|en móvil \d+px"),
    ("color de texto aproximado", r"color #"),
    ("fondo de sección", r"^Fondo de la sección"),
    ("altura / espaciado (paddings)", r"^Altura en escritorio"),
    ("columnas en escritorio", r"^Columnas en escritorio"),
    ("columnas en móvil (responsive)", r"^Columnas en móvil"),
    ("texto que falta o cambiado", r"^Falta el texto"),
    ("peso de la letra", r"peso \d+"),
    ("mayúsculas", r"mayúsculas"),
    ("alineación", r"alineación"),
]


def clasificar_fallos(difs):
    cuenta = {}
    for d in difs:
        for nombre, patron in TIPOS_FALLO:
            if re.search(patron, d):
                cuenta[nombre] = cuenta.get(nombre, 0) + 1
    return cuenta


def problemas_codigo(codigo):
    """Errores de escritura que no mide el verificador visual."""
    p = []
    if codigo.count("<section") != codigo.count("</section>") or codigo.count("<div") != codigo.count("</div>"):
        p.append("HTML desequilibrado (etiquetas sin cerrar)")
    if re.search(r'class="[^"]*\bcontainer\b', codigo):
        p.append('usa la clase "container" (prohibida)')
    if "@apply" in codigo or "<style" in codigo:
        p.append("mete CSS propio (@apply/<style>)")
    if re.search(r"\btext-(xs|sm|base|lg|xl|[2-9]xl)\b", codigo):
        p.append("tamaños de Tailwind redondeados (text-xl…) en vez de text-[NNpx]")
    if re.search(r"\b(bg|text)-(gray|slate|zinc|neutral|stone|red|blue|green)-\d{2,3}\b", codigo):
        p.append("colores de la paleta de Tailwind (gray-500…) en vez del hex exacto")
    if re.search(r'class="[^"]*\bfa-(?!solid|regular|brands)[a-z-]+', codigo) and "fa-solid" not in codigo and "fa-regular" not in codigo:
        p.append("iconos Font Awesome sin familia (fa-solid/fa-regular)")
    return p


def escribir_forense(out, carpeta, datos, historial, estado, umbral):
    """analisis_fallos_qwen.md de esta web + acumulado de todas las webs (pruebas_Qwen/fallos_qwen_acumulado.json)."""
    L = [f"# Análisis forense de Qwen — {datos['url']}", "",
         f"_Modelo: {MODELO} · umbral {umbral}% · {time.strftime('%Y-%m-%d %H:%M')}_", "",
         "Cada sección que no llegó al umbral: qué escribió Qwen, qué midió el verificador, qué hicieron los reintentos y el tipo de fallo.",
         "Debajo de cada una, Claude añade el código corregido en el paso de reparación.", ""]
    total = {}
    for n, intentos in sorted(historial.items()):
        e = estado[n]
        if e["estado"] == "aprobada" or e["estado"].startswith("escena"):
            continue
        mejor_cod = intentos[max(range(len(intentos)), key=lambda i: intentos[i][1]["similitud"])][0]
        tipos = clasificar_fallos(e["diferencias"])
        cod = problemas_codigo(mejor_cod)
        for k, v in tipos.items():
            total[k] = total.get(k, 0) + v
        for k in cod:
            total[k] = total.get(k, 0) + 1
        L += [f"## Sección {n} — {e['nota']}% (PC {e['pc']}%, móvil {e['movil']}%)", ""]
        L.append("**Reintentos:** " + " → ".join(f"{r['similitud']}%" for _, r in intentos)
                 + ("  (las correcciones no mejoraron)" if len(intentos) > 1 and intentos[-1][1]["similitud"] <= intentos[0][1]["similitud"] else ""))
        L.append("**Tipo de fallo:** " + (", ".join(f"{k} ×{v}" for k, v in sorted(tipos.items(), key=lambda x: -x[1])) or "visual sin clasificar"))
        if cod:
            L.append("**Errores de escritura:** " + "; ".join(cod))
        L += ["", "**Lo que midió el verificador:**"] + [f"- {d}" for d in e["diferencias"][:10]]
        recorte = mejor_cod if len(mejor_cod) < 2500 else mejor_cod[:2500] + "\n<!-- … recortado … -->"
        L += ["", "<details><summary>Código de Qwen (mejor versión)</summary>", "", "```html", recorte, "```", "</details>", "",
              f"**Imágenes:** construccion/img/orig_{n}_pc.png · gen_{n}_pc.png", "", "**Corregido por Claude:** _(pendiente)_", ""]
    if total:
        L[6:6] = ["## Resumen de esta web", ""] + [f"- {k}: {v}" for k, v in sorted(total.items(), key=lambda x: -x[1])] + [""]
    (out / "analisis_fallos_qwen.md").write_text("\n".join(L), encoding="utf-8")
    # acumulado entre webs
    acum_p = (BASE.parent / "workspace") / "fallos_qwen_acumulado.json"
    if not acum_p.exists():
        acum_p.write_text("{}", encoding="utf-8")
    try:
        acum = json.loads(acum_p.read_text(encoding="utf-8"))
        if not isinstance(acum, dict) or "webs" not in acum:
            acum = {"webs": {}}
    except Exception:
        acum = {"webs": {}}
    acum["webs"][Path(carpeta).name] = {"modelo": MODELO, "fecha": time.strftime("%Y-%m-%d %H:%M"), "fallos": total,
                                         "secciones": len(estado), "aprobadas": sum(1 for e in estado.values() if e["estado"] == "aprobada")}
    acum_p.write_text(json.dumps(acum, ensure_ascii=False, indent=1), encoding="utf-8")
    suma = {}
    for w in acum["webs"].values():
        for k, v in w["fallos"].items():
            suma[k] = suma.get(k, 0) + v
    tot = sum(suma.values()) or 1
    R = ["# Dónde falla Qwen (todas las webs construidas)", "", f"Webs: {len(acum['webs'])} · " +
         ", ".join(f"{k} ({v['aprobadas']}/{v['secciones']} aprobadas)" for k, v in acum["webs"].items()), "",
         "| Tipo de fallo | Veces | % |", "|---|---|---|"] + [f"| {k} | {v} | {round(100 * v / tot)}% |" for k, v in sorted(suma.items(), key=lambda x: -x[1])]
    ((BASE.parent / "workspace") / "donde_falla_qwen.md").write_text("\n".join(R) + "\n", encoding="utf-8")


def vestir_final(out, carpeta):
    """Paso final: el esqueleto verificado (index.html) se viste con medios de libre uso -> index_final.html."""
    html = (out / "index.html").read_text(encoding="utf-8")
    # las escenas llevan la grabación de la web original: en la versión final, también un vídeo libre
    html = re.sub(r'(<section data-escena[^>]*>)<video[^>]*></video>',
                  lambda m: m.group(1) + '<video data-medio="video" class="absolute inset-0 w-full h-full object-cover" autoplay muted loop playsinline></video>', html)
    html = re.sub(r'(<section data-escena[^>]*>)<img[^>]*>',
                  lambda m: m.group(1) + '<video data-medio="video" class="absolute inset-0 w-full h-full object-cover" autoplay muted loop playsinline></video>', html)
    final = medios.vestir(html, medios.cargar_libres(BASE), semilla=Path(carpeta).name[:12])
    (out / "index_final.html").write_text(final, encoding="utf-8")
    log(f"  Versión final con medios de libre uso: {out / 'index_final.html'}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pausa = "--pausa" in sys.argv
    umbral = 80
    for a in sys.argv:
        if a.startswith("--umbral="):
            umbral = int(a.split("=")[1])
    carpeta = Path(args[0]) if args else Path(((BASE.parent / "workspace") / "ultimo_analisis.txt").read_text(encoding="utf-8").strip())
    if "--vestir" in sys.argv:                # solo el paso final (p. ej. tras cambiar medios_libres.json o reparar index.html)
        vestir_final(carpeta / "construccion", carpeta)
        return
    if "--legacy" not in sys.argv:
        log("construir.py (Qwen escribe la web desde cero) está retirado: escribiría encima de construccion/index.html de crear.py.\n"
            "Cadena oficial:  python crear.py [carpeta]  y luego  python verificar.py [carpeta]\n"
            "Si de verdad quieres la cadena antigua:  python construir.py --legacy [carpeta]")
        sys.exit(2)
    datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8"))
    fichas = (carpeta / "fichas_secciones.md").read_text(encoding="utf-8")
    ref_dir = Path(datos["carpeta_referencia"])
    spec = json.loads((ref_dir / "spec.json").read_text(encoding="utf-8"))
    dclaude = carpeta / "claude"
    if auto_planos:                           # siempre frescos (los escritos a mano en claude/ se respetan)
        auto_planos.generar_planos(carpeta)
    diseno = json.loads((dclaude / "diseno.json").read_text(encoding="utf-8")) if (dclaude / "diseno.json").exists() else None
    out = carpeta / "construccion"
    img_dir = out / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    system = sistema_qwen(diseno)
    titulo = f"Clon de estudio · {datos['url']}"
    log(f"CONSTRUIR - {datos['url']} · {len(spec['secciones'])} secciones · umbral {umbral}% · " +
        ("con sistema de diseño de Claude" if diseno else "sin diseno.json (Qwen usa solo las fichas)"))

    hechas, estado, historial = {}, {}, {}
    abierta = False
    t_ini = time.time()
    total = len(spec["secciones"])
    for i_sec, s in enumerate(spec["secciones"]):
        n = s["n"]
        instr = (dclaude / f"sec_{n}.md").read_text(encoding="utf-8").strip() if (dclaude / f"sec_{n}.md").exists() else ""
        ficha = ficha_de(fichas, n)
        pct = int(100 * i_sec / total)
        t = int(time.time() - t_ini)
        log(f"\n  [{'#' * (pct * 24 // 100)}{'-' * (24 - pct * 24 // 100)}] {pct:3d}%  sección {n} ({i_sec + 1}/{total})  ({t // 60}:{t % 60:02d})"
            + ("  · con instrucciones de Claude" if instr else ""))
        if s.get("escena"):
            # escena 3D/animada: no la escribe Qwen. Vídeo del scroll (o fotograma) a pantalla completa.
            cap = carpeta / "capturas"
            for src, dst in ((cap / "scroll_pc.webm", img_dir / "scroll_pc.webm"), (cap / "scroll_01.png", img_dir / f"escena_{n}.png")):
                if src.exists() and not dst.exists():
                    shutil.copy(src, dst)
            video = (img_dir / "scroll_pc.webm").exists()
            fondo = s.get("fondo", "#000000")
            medio = (f'<video class="absolute inset-0 w-full h-full object-cover" src="img/scroll_pc.webm" poster="img/escena_{n}.png" autoplay muted loop playsinline></video>'
                     if video else f'<img class="absolute inset-0 w-full h-full object-cover" src="img/escena_{n}.png" alt="">')
            hechas[n] = f'<!-- SECCIÓN {n}: {s["escena"]} (vídeo en lugar del 3D) -->\n<section data-escena class="relative w-full h-[100vh] overflow-hidden bg-[{fondo}]">{medio}</section>'
            estado[n] = {"nota": 0, "pc": 0, "movil": 0, "diferencias": [f"{s['escena']}: sustituida por el vídeo del scroll; no se compara"],
                         "intentos": 0, "umbral": umbral, "estado": "escena (vídeo)"}
            copiar_imgs(n, ref_dir, out / "_medidas", img_dir)
            log(f"      {s['escena']}: se pone el vídeo del scroll (Qwen no la escribe)")
            (out / "index.html").write_text(pagina(hechas, diseno, titulo), encoding="utf-8")
            continue
        prompt = ficha + ("\n\nINSTRUCCIONES DEL ARQUITECTO (mandan sobre la ficha si hay conflicto):\n" + instr if instr else "") + \
            f"\n\nEscribe SOLO la sección {n}: <!-- SECCIÓN {n} --> y un único <section>."
        fotos = [i for i in s["imagenes"] if i.get("tipo") not in ("svg", "video")]
        codigo = medios.esqueleto(limpiar(preguntar(prompt, system), n), fotos)
        mejor = None
        for intento in range(3):
            hechas[n] = codigo
            ruta = out / "index.html"
            ruta.write_text(pagina(hechas, diseno, titulo), encoding="utf-8")
            med = out / "_medidas"
            r = cmp.comparar(spec, ref_dir, ruta, med)["secciones"].get(n, {"similitud": 0, "escritorio": 0, "movil": 0, "diferencias": ["no se pudo medir"]})
            log(f"      verificación: {r['similitud']}% (PC {r['escritorio']}%, móvil {r['movil']}%)")
            historial.setdefault(n, []).append((codigo, r))
            mejora = r["similitud"] - (mejor[1]["similitud"] if mejor else -100)
            if mejora > 0:
                mejor = (codigo, r)
                copiar_imgs(n, ref_dir, med, img_dir)
            if r["similitud"] >= umbral or not r["diferencias"] or intento == 2:
                break
            if intento > 0 and mejora < 2:
                log("      la corrección no mejora: se queda la mejor versión (la repasa Claude)")
                break
            lista = "\n".join(f"  - {d}" for d in r["diferencias"][:8])
            log(f"      corrigiendo ({len(r['diferencias'])} diferencias)")
            codigo = medios.esqueleto(limpiar(preguntar(ficha + ("\n\nINSTRUCCIONES DEL ARQUITECTO:\n" + instr if instr else "") + f"\n\nCÓDIGO ACTUAL DE LA SECCIÓN {n}:\n{mejor[0]}\n\nUN VERIFICADOR MIDIÓ TU SECCIÓN CONTRA LA ORIGINAL. "
                                       f"CORRIGE SOLO ESTO:\n{lista}\n\nDevuelve la sección {n} completa corregida.", system), n), fotos)
        hechas[n] = mejor[0]
        rr = mejor[1]
        estado[n] = {"nota": rr["similitud"], "pc": rr["escritorio"], "movil": rr["movil"], "diferencias": rr["diferencias"],
                     "intentos": intento + 1, "umbral": umbral, "estado": "aprobada" if rr["similitud"] >= umbral else "para Claude"}
        (out / "revision.html").write_text(revision_html(estado, ref_dir, img_dir, titulo), encoding="utf-8")
        (out / "index.html").write_text(pagina(hechas, diseno, titulo), encoding="utf-8")
        if pausa:
            if not abierta:
                webbrowser.open((out / "revision.html").resolve().as_uri())
                abierta = True
            input(f"  -> Sección {n}: {rr['similitud']}%. Mírala en revision.html y pulsa Enter para seguir...")

    escenas = [n for n, e in estado.items() if e["estado"].startswith("escena")]
    estado_med = {n: e for n, e in estado.items() if n not in escenas}
    pend = [n for n, e in estado_med.items() if e["estado"] != "aprobada"]
    L = [f"# Pendientes para Claude — {datos['url']}", "",
         f"Media: {round(sum(e['nota'] for e in estado_med.values()) / max(len(estado_med), 1))}% · aprobadas {len(estado_med) - len(pend)}/{len(estado_med)} (umbral {umbral}%)"
         + (f" · escenas con vídeo (no cuentan): {', '.join('S' + str(n) for n in escenas)}" if escenas else ""), ""]
    for n in pend:
        e = estado[n]
        L.append(f"## Sección {n}: {e['nota']}% (PC {e['pc']}%, móvil {e['movil']}%)")
        L += [f"- {d}" for d in e["diferencias"][:10]]
        L.append(f"- imágenes: construccion/img/orig_{n}_pc.png vs gen_{n}_pc.png (y _movil)")
        L.append("")
    (out / "pendientes_nova.md").write_text("\n".join(L), encoding="utf-8")
    escribir_forense(out, carpeta, datos, historial, estado, umbral)
    vestir_final(out, carpeta)
    if comprimir_para_nova:
        try:
            comprimir_para_nova.optimizar_careo(carpeta)
        except Exception:
            pass
    shutil.rmtree(out / "_medidas", ignore_errors=True)
    t = int(time.time() - t_ini)
    log(f"\n  [{'#' * 24}] 100%  terminado ({t // 60}:{t % 60:02d})")
    log("\n" + "\n".join(L[:4]) + f"\n\nPágina: {out / 'index.html'}\nRevisión: {out / 'revision.html'}")


if __name__ == "__main__":
    main()

