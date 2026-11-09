import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
CREAR UNA WEB DESDE CERO con Qwen + verificador de instrucciones (sin web original)

  python crear_cero.py nara              (proyecto en prueba_creacion/nara/)

Entrada (la escribe Claude):
  prueba_creacion/<proyecto>/diseno.json        colores, fuentes y notas del sistema de diseño
  prueba_creacion/<proyecto>/secciones/sec_NN.md instrucciones cortas + bloque COMPROBAR (lo que se mide)
Bloque COMPROBAR (una comprobación por línea):
  - texto "Título" | tag h1 | px 40/72 | peso 600 | color #1D1D1F      (px = móvil/PC)
  - boton "Comprar" | fondo #E8553A | color #FFFFFF | radio 999
  - fondo #FFF7EE          - columnas 1/3 (móvil/PC)      - alto 500/700 (mínimo móvil/PC)
  - imagenes 4             - superpuesto si               - carrusel si
  - debajo "etiqueta" de "12"   (el primer texto va debajo del segundo y alineado con él, en PC y móvil)
  - junto "A" a "B"        (en PC, A y B lado a lado: misma altura, sin pisarse)
  - degradado si           - texto_degradado "Palabra"   (texto con bg-clip-text y degradado)
  - sticky si              - desenfoque si (backdrop-blur)   - sale si (algo se monta sobre la sección siguiente)
  - tarjetas 3 | radio 24 | fondo #14141F | borde #26263A    (cajas con fondo/borde y esquinas redondeadas)
  - tarjeta "Equipo" | borde #8B5CF6      (la tarjeta que contiene ese texto: su borde y/o fondo)
  - boton "Empezar" | fondo no            (botón SIN relleno: solo borde o texto)
  - texto "X" | fuente Space Grotesk      (los h1/h2 se comprueban solos con la fuente "titulo" del diseno.json)
Comprobaciones CRÍTICAS (texto que no aparece, botón que no aparece, número de imágenes): si falla una,
la sección no se aprueba aunque el resto esté perfecto (tope 89 %). Las imágenes que sobran también cuentan como fallo.
Proceso por sección: Qwen escribe -> se mide en PC (1280) y móvil (375) -> lista ✅/❌ + reglas de calidad
(no se sale en móvil, HTML cerrado) -> si no llega al 90 %, Qwen corrige con los ❌ (máx. 3) -> se queda la mejor.
Salida en prueba_creacion/<proyecto>/resultado/: index.html (esqueleto), index_final.html (medios libres),
revision.html, estadisticas.md, capturas por sección.
"""
import html as H
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
import medios  # noqa: E402
from construir import MODELO, limpiar, log, pagina, preguntar, sistema_qwen  # noqa: E402
from extraer import JS_MEDIR, MOVIL, NAV_ARGS, capturar  # noqa: E402

UMBRAL = 90
CRITICAS = {"texto presente", "botón presente", "imágenes"}
JS_DESBORDE = "() => document.documentElement.scrollWidth > innerWidth + 1"
# medidas extra solo para crear desde cero (degradados, sticky, tarjetas...), por sección, en PC
JS_EXTRA = r"""
() => { const out = {};
  const hex = c => { const m = (c || '').match(/[\d.]+/g); if (!m || m.length < 3 || (m.length > 3 && +m[3] === 0)) return null;
    return '#' + m.slice(0, 3).map(x => (Math.round(+x)).toString(16).padStart(2, '0')).join('').toUpperCase(); };
  const todas = [...document.querySelectorAll('[data-clon-sec]')];
  for (const [i, sec] of todas.entries()) {
    const n = +sec.dataset.clonSec, R = sec.getBoundingClientRect();
    const sig = todas[i + 1] ? todas[i + 1].getBoundingClientRect().top : R.bottom;   // dónde empieza la siguiente sección
    const o = { degradado: false, texto_degradado: [], sticky: false, desenfoque: false, sale: false, tarjetas: [] };
    for (const e of [sec, ...sec.querySelectorAll('*')]) {
      const s = getComputedStyle(e), r = e.getBoundingClientRect();
      if (s.display === 'none' || r.width < 2 || r.height < 2) continue;
      if (/gradient/.test(s.backgroundImage)) { o.degradado = true;
        if ((s.webkitBackgroundClip || s.backgroundClip) === 'text') o.texto_degradado.push((e.innerText || '').trim().slice(0, 120)); }
      if (s.position === 'sticky' || s.position === 'fixed') o.sticky = true;
      if ((s.backdropFilter && s.backdropFilter !== 'none') || (s.webkitBackdropFilter && s.webkitBackdropFilter !== 'none')) o.desenfoque = true;
      const rad = parseFloat(s.borderTopLeftRadius) || 0, bg = hex(s.backgroundColor), bw = parseFloat(s.borderTopWidth) || 0;
      if (rad >= 8 && (bg || bw > 0 || /gradient/.test(s.backgroundImage)) && r.width >= 140 && r.height >= 90 && r.width < R.width * 0.97
          && (e.innerText || '').trim().length >= 2 && !['A', 'BUTTON', 'IMG', 'VIDEO'].includes(e.tagName))
        o.tarjetas.push({ radio: Math.round(rad), fondo: bg, borde: bw > 0 ? hex(s.borderTopColor) : null,
                          x: Math.round(r.left), y: Math.round(r.top - R.top), w: Math.round(r.width), h: Math.round(r.height) });
      // se monta sobre la siguiente: su borde inferior pasa del inicio de la siguiente sección (el margen negativo
      // colapsa y "encoge" la propia sección, por eso no basta con mirar su caja)
      if (r.height > 60 && r.bottom > Math.min(R.bottom, sig) + 24 && e.tagName !== 'SECTION' && e !== sec) o.sale = true;
    }
    const dentro = (a, b) => b.x <= a.x + 1 && b.y <= a.y + 1 && b.x + b.w >= a.x + a.w - 1 && b.y + b.h >= a.y + a.h - 1;
    o.tarjetas = o.tarjetas.filter((a, i) => !o.tarjetas.some((b, j) => j !== i && dentro(a, b) && (!dentro(b, a) || j < i)));
    out[n] = o; }
  return out; }
"""


# ---------------------------------------------------------------- instrucciones
def leer_secciones(carpeta):
    out = []
    for p in sorted((carpeta / "secciones").glob("sec_*.md")):
        n = int(re.search(r"(\d+)", p.stem).group(1))
        t = p.read_text(encoding="utf-8")
        partes = re.split(r"(?im)^COMPROBAR:\s*$", t, maxsplit=1)
        instr = partes[0].strip()
        checks = [l.strip()[1:].strip() for l in (partes[1] if len(partes) > 1 else "").splitlines() if l.strip().startswith("-")]
        out.append({"n": n, "instrucciones": instr, "checks": checks, "archivo": p.name})
    return out


def parsear(check):
    """'texto "X" | tag h1 | px 40/72' -> {'tipo':'texto','valor':'X','tag':'h1','px':(40,72)}"""
    trozos = [x.strip() for x in check.split("|")]
    m = re.match(r'(\w+)\s*(?:"([^"]*)")?\s*(.*)', trozos[0])
    c = {"tipo": m.group(1).lower(), "valor": m.group(2) if m.group(2) is not None else m.group(3).strip()}
    for t in trozos[1:]:
        k, _, v = t.partition(" ")
        c[k.lower()] = v.strip()
    return c


# ---------------------------------------------------------------- medir
def medir(ruta, carpeta_img, n_list):
    """Renderiza la página en PC y móvil; devuelve medidas por sección, desborde móvil y recorta cada sección."""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    res = {"escritorio": {}, "movil": {}, "desborde": False, "extra": {}}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        for vista, (w, h) in (("escritorio", (1280, 800)), ("movil", MOVIL)):
            page = nav.new_page(viewport={"width": w, "height": h})
            css_local = os.environ.get("CLON_TAILWIND_CSS")        # solo para pruebas sin internet
            if css_local and Path(css_local).exists():
                js = "document.head.appendChild(Object.assign(document.createElement('style'),{textContent:" + json.dumps(Path(css_local).read_text()) + "}));window.tailwind={};"
                page.route("**/cdn.tailwindcss.com/**", lambda route, *_: route.fulfill(status=200, content_type="application/javascript", body=js))
            try:
                page.goto(Path(ruta).resolve().as_uri(), wait_until="networkidle", timeout=40000)
            except Exception:
                page.wait_for_timeout(3000)
            page.wait_for_timeout(800)
            datos = page.evaluate(JS_MEDIR)
            if vista == "escritorio":
                res["extra"] = {int(k): v for k, v in page.evaluate(JS_EXTRA).items()}
            if vista == "movil":
                res["desborde"] = page.evaluate(JS_DESBORDE)
            alto = min(datos["alto_total"], 20000)
            cap = carpeta_img / f"_pagina_{vista}.png"
            capturar(page, cap, w, alto)
            img = Image.open(cap)
            for s in datos["secciones"]:
                res[vista][s["n"]] = s
                if s["n"] in n_list and s["alto"] >= 4:
                    img.crop((0, max(0, s["y"]), img.width, min(img.height, s["y"] + s["alto"]))).save(
                        carpeta_img / f"sec_{s['n']}_{'pc' if vista == 'escritorio' else 'movil'}.png")
            page.close()
        nav.close()
    return res


def _hex(c):
    return (c or "").upper()[:7]


def _dist(a, b):
    try:
        return sum(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) for i in (1, 3, 5))
    except Exception:
        return 999


def _norm(t):
    return re.sub(r"[^a-z0-9áéíóúñ]+", " ", (t or "").lower()).strip()


def _buscar_texto(sec, valor):
    k = _norm(valor)
    textos = (sec or {}).get("textos", [])
    exacto = next((t for t in textos if k and k == _norm(t["t"])), None)       # primero el texto exacto ("12" no es "120 ml")
    return exacto or next((t for t in textos if k and k in _norm(t["t"])), None)


def _debajo(sec, a, b):
    """¿el texto a está debajo del texto b y en su misma columna? None si falta alguno."""
    ta, tb = _buscar_texto(sec, a), _buscar_texto(sec, b)
    if not ta or not tb:
        return None
    ca, cb = ta["x"] + ta["w"] / 2, tb["x"] + tb["w"] / 2
    return ta["y"] >= tb["y"] + tb["px"] * 0.6 and abs(ca - cb) <= max(ta["w"], tb["w"]) / 2 + 8


def _junto(sec, a, b):
    ta, tb = _buscar_texto(sec, a), _buscar_texto(sec, b)
    if not ta or not tb:
        return None
    separados = ta["x"] + ta["w"] <= tb["x"] + 6 or tb["x"] + tb["w"] <= ta["x"] + 6
    return separados and abs(ta["y"] - tb["y"]) <= 160


def _tarjeta_de(sec, ex, valor):
    t = _buscar_texto(sec, valor)
    if not t:
        return None
    cx, cy = t["x"] + t["w"] / 2, t["y"] + t["px"] / 2
    cand = [c for c in (ex or {}).get("tarjetas", []) if c["x"] - 4 <= cx <= c["x"] + c["w"] + 4 and c["y"] - 30 <= cy <= c["y"] + c["h"] + 4]
    return min(cand, key=lambda c: c["w"] * c["h"]) if cand else None


def evaluar(checks, pc, mv, desborde, extra=None, fuente_titulo=None):
    """Cada comprobación -> (ok, categoría, texto). Devuelve la lista y el % cumplido."""
    res = []

    def add(ok, cat, txt):
        res.append((ok, cat, txt))
    for ch in checks:
        c = parsear(ch)
        tipo = c["tipo"]
        if tipo == "debajo":
            q = re.findall(r'"([^"]*)"', ch)
            if len(q) < 2:
                continue
            for vista, sec in (("PC", pc), ("móvil", mv)):
                r = _debajo(sec, q[0], q[1])
                add(bool(r), "disposición", f'"{q[0][:25]}" debe ir DEBAJO de "{q[1][:25]}" y alineado con él en {vista}'
                    + (" (falta alguno de los dos textos)" if r is None else "" if r else
                       " -> mismo bloque: <div><p>{q1}</p><p>{q0}</p></div>".format(q0=q[0][:20], q1=q[1][:20])))
            continue
        ex = extra or {}
        if tipo == "junto":
            q = re.findall(r'"([^"]*)"', ch)
            if len(q) >= 2:
                r = _junto(pc, q[0], q[1])
                add(bool(r), "disposición", f'"{q[0][:25]}" y "{q[1][:25]}" lado a lado en PC'
                    + (" (falta alguno de los dos textos)" if r is None else "" if r else " -> dos columnas: md:grid-cols-2 o md:flex"))
            continue
        if tipo in ("degradado", "sticky", "desenfoque", "sale"):
            quiere = c["valor"] != "no"
            pistas = {"degradado": "fondo con degradado: bg-gradient-to-r from-[...] to-[...]", "sticky": "barra fija al hacer scroll: sticky top-0 z-50",
                      "desenfoque": "fondo translúcido desenfocado: bg-[...]/70 backdrop-blur-md",
                      "sale": "el elemento se monta sobre la sección siguiente: margen negativo (-mb-[...]) y relative z-10"}
            add(bool(ex.get(tipo)) == quiere, "efectos", (pistas[tipo] if quiere else f"sin {tipo}"))
            continue
        if tipo == "texto_degradado":
            ok = any(_norm(c["valor"]) in _norm(t) for t in ex.get("texto_degradado", []))
            add(ok, "efectos", f'"{c["valor"][:30]}" con texto degradado -> bg-gradient-to-r from-[...] to-[...] bg-clip-text text-transparent')
            continue
        if tipo == "tarjeta":
            tj = _tarjeta_de(pc, ex, c["valor"])
            add(bool(tj), "tarjetas", f'"{c["valor"][:25]}" dentro de una tarjeta (caja con fondo o borde y esquinas redondeadas)')
            if tj and "borde" in c:
                add(_dist(tj["borde"] or "", c["borde"].upper()) < 30, "tarjeta destacada",
                    f'la tarjeta de "{c["valor"][:25]}" con borde {c["borde"]} (tiene {tj["borde"]}) -> border-2 border-[{c["borde"]}]')
            if tj and "fondo" in c:
                add(_dist(tj["fondo"] or "", c["fondo"].upper()) < 15, "tarjeta destacada",
                    f'la tarjeta de "{c["valor"][:25]}" con fondo {c["fondo"]} (tiene {tj["fondo"]}) -> bg-[{c["fondo"]}]')
            continue
        if tipo == "tarjetas":
            k, ts = int(c["valor"]), ex.get("tarjetas", [])
            add(len(ts) >= k, "tarjetas", f"{k} tarjetas (cajas con fondo o borde y esquinas redondeadas; hay {len(ts)})")
            if not ts:
                continue
            ref = sorted(ts, key=lambda t: -t["w"] * t["h"])[:k]
            if "radio" in c:
                r = int(c["radio"])
                buenos = sum(1 for t in ref if abs(t["radio"] - r) <= 2)
                add(buenos >= len(ref) * 0.66, "tarjetas", f"tarjetas con esquinas rounded-[{r}px] (tienen {', '.join(str(t['radio']) for t in ref)})")
            if "fondo" in c:
                buenos = sum(1 for t in ref if _dist(t["fondo"] or "", c["fondo"].upper()) < 15)
                add(buenos >= len(ref) * 0.66, "tarjetas", f"tarjetas con fondo bg-[{c['fondo']}] (tienen {', '.join(str(t['fondo']) for t in ref)})")
            if "borde" in c:
                buenos = sum(1 for t in ref if _dist(t["borde"] or "", c["borde"].upper()) < 30)
                add(buenos >= len(ref) * 0.66, "tarjetas", f"tarjetas con borde border border-[{c['borde']}] (tienen {', '.join(str(t['borde']) for t in ref)})")
            continue
        if tipo == "texto":
            tp, tm = _buscar_texto(pc, c["valor"]), _buscar_texto(mv, c["valor"])
            add(bool(tp), "texto presente", f'texto "{c["valor"][:40]}"' + ("" if tp else " NO aparece"))
            if not tp:
                continue
            if "tag" in c:
                add(tp["tag"] == c["tag"], "etiqueta", f'"{c["valor"][:30]}" debe ser <{c["tag"]}> (es <{tp["tag"]}>)')
            if "px" in c:
                pm, pp = [int(x) for x in c["px"].split("/")]
                add(abs(tp["px"] - pp) <= max(2, pp * 0.08), "tamaño PC", f'"{c["valor"][:30]}" en PC {pp}px (mide {tp["px"]}px) -> md:text-[{pp}px]')
                if tm:
                    add(abs(tm["px"] - pm) <= max(2, pm * 0.08), "tamaño móvil", f'"{c["valor"][:30]}" en móvil {pm}px (mide {tm["px"]}px) -> text-[{pm}px]')
            fu = c.get("fuente") or (fuente_titulo if c.get("tag") in ("h1", "h2") else None)
            if fu:
                add(fu.lower() in (tp.get("fuente") or "").lower(), "fuente",
                    f'"{c["valor"][:30]}" con la fuente {fu} (usa {tp.get("fuente")}) -> font-titulo' if not c.get("fuente") else
                    f'"{c["valor"][:30]}" con la fuente {fu} (usa {tp.get("fuente")})')
            if "peso" in c:
                add(abs(tp["peso"] - int(c["peso"])) < 100, "peso", f'"{c["valor"][:30]}" peso {c["peso"]} (es {tp["peso"]}) -> font-[{c["peso"]}]')
            if "color" in c:
                add(_dist(_hex(tp["color"]), c["color"].upper()) < 30, "color texto", f'"{c["valor"][:30]}" color {c["color"]} (es {tp["color"]}) -> text-[{c["color"]}]')
        elif tipo == "boton":
            b = next((x for x in (pc or {}).get("botones", []) if _norm(c["valor"]) in _norm(x["t"])), None)
            if c.get("fondo") == "no":
                limpio = not b or _dist(_hex(b["fondo"]), _hex((pc or {}).get("fondo"))) < 15
                add(bool(_buscar_texto(pc, c["valor"])), "botón presente", f'botón "{c["valor"]}"' + ("" if _buscar_texto(pc, c["valor"]) else " NO aparece"))
                add(limpio, "botón", f'botón "{c["valor"]}" SIN relleno (es {b["fondo"] if b else "—"}) -> quita el bg-..., deja border border-[...] bg-transparent')
                continue
            add(bool(b), "botón presente", f'botón "{c["valor"]}"' + ("" if b else " NO aparece con fondo (pon bg-[...] al <a>/<button>)"))
            if not b:
                continue
            if "fondo" in c:
                add(_dist(_hex(b["fondo"]), c["fondo"].upper()) < 40, "botón", f'botón "{c["valor"]}" fondo {c["fondo"]} (es {b["fondo"]}) -> bg-[{c["fondo"]}]')
            if "color" in c:
                add(_dist(_hex(b["color"]), c["color"].upper()) < 40, "botón", f'botón "{c["valor"]}" texto {c["color"]} (es {b["color"]}) -> text-[{c["color"]}]')
            if "radio" in c:
                r = int(c["radio"])
                add((b["radio"] >= b["h"] / 2 - 1) if r >= 99 else abs(b["radio"] - r) <= 2, "botón",
                    f'botón "{c["valor"]}" radio {"píldora (rounded-full)" if r >= 99 else str(r) + "px"} (es {b["radio"]}px)')
        elif tipo == "fondo":
            add(_dist(_hex((pc or {}).get("fondo")), c["valor"].upper()) < 15, "fondo", f'fondo de la sección {c["valor"]} (es {(pc or {}).get("fondo")}) -> bg-[{c["valor"]}]')
        elif tipo == "columnas":
            m_, p_ = [int(x) for x in c["valor"].split("/")]
            add((pc or {}).get("columnas", 1) == p_, "columnas PC", f"{p_} columnas en PC (tiene {(pc or {}).get('columnas', 1)}) -> md:grid-cols-{p_}")
            add((mv or {}).get("columnas", 1) == m_, "columnas móvil", f"{m_} columna(s) en móvil (tiene {(mv or {}).get('columnas', 1)}) -> grid-cols-{m_}")
        elif tipo == "alto":
            m_, p_ = [int(x) for x in c["valor"].split("/")]
            add((pc or {}).get("alto", 0) >= p_ * 0.9, "alto", f"alto mínimo {p_}px en PC (mide {(pc or {}).get('alto', 0)}px) -> min-h-[{p_}px]")
            add((mv or {}).get("alto", 0) >= m_ * 0.9, "alto", f"alto mínimo {m_}px en móvil (mide {(mv or {}).get('alto', 0)}px) -> min-h-[{m_}px]")
        elif tipo == "imagenes":
            k = int(c["valor"])
            have = len([i for i in (pc or {}).get("imagenes", []) if i["tipo"] != "svg"])
            add(have >= k, "imágenes", f"{k} imágenes/vídeos (hay {have})" + (" -> añade la imagen con su marco" if have < k else ""))
            if have > k:
                add(False, "imágenes de más", f"sobran {have - k} imagen(es): pide {k} (quita las <img> que no están en las instrucciones)")
        elif tipo == "superpuesto":
            add(bool((pc or {}).get("superpuesto")) == (c["valor"] == "si"), "estructura",
                "texto ENCIMA de la imagen (relative + img absolute inset-0)" if c["valor"] == "si" else "el texto NO va encima de la imagen")
        elif tipo == "carrusel":
            add(bool((pc or {}).get("carrusel")) == (c["valor"] == "si"), "estructura",
                "carrusel horizontal (flex overflow-x-auto snap-x; tarjetas shrink-0)" if c["valor"] == "si" else "no debe ser carrusel")
    add(not desborde, "calidad", "nada se sale de la pantalla en móvil (sin scroll horizontal)")
    hechas = sum(1 for ok, _, _ in res if ok)
    pct = round(100 * hechas / max(len(res), 1))
    if any(not ok and cat in CRITICAS for ok, cat, _ in res):
        pct = min(pct, UMBRAL - 1)          # falta algo esencial: no se aprueba
    return res, pct


# ---------------------------------------------------------------- informe
def revision(estado, titulo):
    filas = []
    for n in sorted(estado):
        e = estado[n]
        color = "#16a34a" if e["pct"] >= UMBRAL else ("#ca8a04" if e["pct"] >= 70 else "#dc2626")
        lis = "".join(f"<li style='color:{'#15803d' if ok else '#b91c1c'}'>{'✅' if ok else '❌'} {'<b>[CRÍTICA]</b> ' if (not ok and c in CRITICAS) else ''}{H.escape(t)}</li>"
                      for ok, c, t in e["checks"])
        filas.append(f"<section><h2>Sección {n} <span style='background:{color}'>{e['pct']}%</span> <small>{e['intentos']} corrección(es) · "
                     f"Qwen {e['segundos']} s</small></h2><div class='par'><div><b>PC</b><img src='img/sec_{n}_pc.png'></div>"
                     f"<div class='m'><b>Móvil</b><img src='img/sec_{n}_movil.png'></div></div><ul>{lis}</ul></section>")
    media = round(sum(e["pct"] for e in estado.values()) / max(len(estado), 1))
    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revisión {H.escape(titulo)}</title><style>body{{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f4f4f5;color:#18181b}}
section{{background:#fff;border-radius:10px;padding:14px;margin:0 0 16px}}h2{{font-size:18px;margin:0 0 10px}}h2 span{{color:#fff;padding:2px 8px;border-radius:6px}}
small{{color:#71717a;font-weight:400}}.par{{display:grid;grid-template-columns:1fr 300px;gap:12px}}.par img{{width:100%;border:1px solid #e4e4e7}}
ul{{font-size:13px;padding-left:16px}}</style></head><body><h1>{H.escape(titulo)} · cumplimiento medio {media}%</h1>{''.join(filas)}</body></html>"""


def main():
    nombre = sys.argv[1] if len(sys.argv) > 1 else "nara"
    carpeta = BASE / "prueba_creacion" / nombre
    out = carpeta / "resultado"
    img = out / "img"
    img.mkdir(parents=True, exist_ok=True)
    diseno = json.loads((carpeta / "diseno.json").read_text(encoding="utf-8"))
    secs = leer_secciones(carpeta)
    system = sistema_qwen(diseno).replace("a partir de una FICHA con medidas reales", "a partir de las INSTRUCCIONES del arquitecto") \
        .replace("La ficha manda: no inventes estilo, traduce las medidas a código.", "Las instrucciones mandan: cumple cada punto con las clases exactas.")
    titulo = diseno.get("titulo", nombre)
    log(f"CREAR DESDE CERO - {titulo} · {len(secs)} secciones · {MODELO}")
    hechas, estado, t0 = {}, {}, time.time()
    for i, s in enumerate(secs):
        n = s["n"]
        pct = int(100 * i / len(secs))
        log(f"\n  [{'#' * (pct * 24 // 100)}{'-' * (24 - pct * 24 // 100)}] {pct:3d}%  sección {n} ({i + 1}/{len(secs)})")
        lista_ck = "\n".join(f"- {c}" for c in s["checks"])
        prompt = (f"INSTRUCCIONES DE LA SECCIÓN {n}:\n{s['instrucciones']}\n\nDEBE CUMPLIR (se medirá):\n{lista_ck}\n\n"
                  f"Escribe SOLO la sección {n}: <!-- SECCIÓN {n} --> y un único <section>.")
        t = time.time()
        codigo = medios.esqueleto(limpiar(preguntar(prompt, system), n), [])
        seg = time.time() - t
        mejor, historial, intento = None, [], 0
        while True:
            hechas[n] = codigo
            (out / "index.html").write_text(pagina(hechas, diseno, titulo), encoding="utf-8")
            med = medir(out / "index.html", img, [n])
            res, p = evaluar(s["checks"], med["escritorio"].get(n), med["movil"].get(n), med["desborde"], med["extra"].get(n),
                             diseno.get("fuentes", {}).get("titulo"))
            historial.append({"pct": p, "fallos": [t_ for ok, _, t_ in res if not ok]})
            log(f"      cumple {p}% ({sum(1 for r in res if r[0])}/{len(res)})")
            if not mejor or p > mejor[1]:
                mejor = (codigo, p, res)
                for v in ("pc", "movil"):
                    if (img / f"sec_{n}_{v}.png").exists():
                        shutil.copy(img / f"sec_{n}_{v}.png", img / f"mejor_{n}_{v}.png")
            if p >= 100 or intento == 3:          # aprueba con 90, pero Qwen intenta dejarla perfecta (es local, no cuesta)
                break
            intento += 1
            fallos = "\n".join(f"- {'IMPRESCINDIBLE: ' if c_ in CRITICAS else ''}{t_}"
                                for ok, c_, t_ in sorted(res, key=lambda r: r[1] not in CRITICAS) if not ok)
            log(f"      Qwen corrige (intento {intento}/3)")
            t = time.time()
            codigo = medios.esqueleto(limpiar(preguntar(
                f"INSTRUCCIONES DE LA SECCIÓN {n}:\n{s['instrucciones']}\n\nCÓDIGO ACTUAL:\n{mejor[0]}\n\n"
                f"UN VERIFICADOR MIDIÓ TU SECCIÓN. NO CUMPLE ESTO:\n{fallos}\n\nCorrige SOLO eso y devuelve la sección {n} completa.", system), n), [])
            seg += time.time() - t
        hechas[n] = mejor[0]
        for v in ("pc", "movil"):
            if (img / f"mejor_{n}_{v}.png").exists():
                shutil.move(img / f"mejor_{n}_{v}.png", img / f"sec_{n}_{v}.png")
        estado[n] = {"pct": mejor[1], "checks": mejor[2], "intentos": intento, "segundos": round(seg), "historial": historial}
        (out / "index.html").write_text(pagina(hechas, diseno, titulo), encoding="utf-8")
        (out / "revision.html").write_text(revision(estado, titulo), encoding="utf-8")

    # --- estadísticas
    cats = {}
    for e in estado.values():
        for ok, cat, _ in e["checks"]:
            a = cats.setdefault(cat, [0, 0])
            a[0] += ok
            a[1] += 1
    primera = round(sum(e["historial"][0]["pct"] for e in estado.values()) / len(estado))
    final = round(sum(e["pct"] for e in estado.values()) / len(estado))
    aprob = sum(1 for e in estado.values() if e["pct"] >= UMBRAL)
    total_ck = sum(len(e["checks"]) for e in estado.values())
    L = [f"# Estadísticas — {titulo} (creada desde cero)", "", f"_Modelo {MODELO} · {time.strftime('%Y-%m-%d %H:%M')} · {round(time.time() - t0)} s en total_", "",
         "## Resumen", "", "| | |", "|---|---|",
         f"| Secciones | {len(estado)} |", f"| Comprobaciones pedidas | {total_ck} |",
         f"| Cumplimiento a la PRIMERA (sin correcciones) | **{primera}%** |",
         f"| Cumplimiento FINAL (tras correcciones de Qwen) | **{final}%** |",
         f"| Secciones aprobadas (≥ {UMBRAL}%) | **{aprob}/{len(estado)}** |",
         f"| Correcciones usadas | {sum(e['intentos'] for e in estado.values())} |",
         f"| Tiempo de Qwen escribiendo | {sum(e['segundos'] for e in estado.values())} s |", "",
         "## Por tipo de instrucción (qué obedece y qué no)", "", "| Tipo | Cumplidas | % |", "|---|---|---|"]
    L += [f"| {k} | {v[0]}/{v[1]} | {round(100 * v[0] / v[1])}% |" for k, v in sorted(cats.items(), key=lambda x: x[1][0] / x[1][1])]
    L += ["", "## Por sección", "", "| Sección | 1.ª vez | Final | Correcciones | Fallos que quedan |", "|---|---|---|---|---|"]
    for n, e in sorted(estado.items()):
        quedan = "; ".join(t_ for ok, _, t_ in e["checks"] if not ok)[:180] or "—"
        L.append(f"| S{n} | {e['historial'][0]['pct']}% | {e['pct']}% | {e['intentos']} | {quedan} |")
    (out / "estadisticas.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out / "datos_prueba.json").write_text(json.dumps({str(k): {**v, "checks": [list(c) for c in v["checks"]]} for k, v in estado.items()},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
    # lo que Qwen no pudo arreglar en 3 intentos: lo arregla Claude con código (y lo apunta en correcciones.md)
    P = [f"# Pendientes para Claude — {titulo}", "", "Secciones que no llegaron al 100 % tras 3 correcciones de Qwen. Arreglar SOLO con código "
         "en index.html (y repetir en index_final.html); apuntar cada cambio en correcciones.md (antes → después).", ""]
    for n, e in sorted(estado.items()):
        quedan = [t_ for ok, _, t_ in e["checks"] if not ok]
        if quedan:
            P += [f"## Sección {n} · {e['pct']}%", ""] + [f"- {q}" for q in quedan] + ["", "```html", hechas[n].strip(), "```", ""]
    (out / "pendientes_nova.md").write_text("\n".join(P) + "\n", encoding="utf-8")
    if not (out / "correcciones.md").exists():
        (out / "correcciones.md").write_text(f"# Correcciones de Claude — {titulo}\n\n| Sección | Fallo | Antes | Después |\n|---|---|---|---|\n", encoding="utf-8")
    final_html = medios.vestir((out / "index.html").read_text(encoding="utf-8"), medios.cargar_libres(BASE), semilla=nombre)
    (out / "index_final.html").write_text(final_html, encoding="utf-8")
    for f in img.glob("_pagina_*.png"):
        f.unlink()
    log("\n" + "\n".join(L[4:13]) + f"\n\nRevisión: {out / 'revision.html'}\nEstadísticas: {out / 'estadisticas.md'}")


if __name__ == "__main__":
    main()
