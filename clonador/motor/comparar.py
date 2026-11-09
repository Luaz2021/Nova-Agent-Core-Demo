import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
COMPARADOR: mide cuánto se parece la página generada a la original, sección por sección.

  - Similitud visual por sección (SSIM, el estándar de la industria para comparar imágenes,
    más colores y altura), en escritorio (1280px) y móvil (375px).
  - Diferencias de estilo elemento a elemento: empareja los textos de la original con los de
    la generada y compara tamaño, peso, color, mayúsculas y alineación. Devuelve correcciones
    exactas en lenguaje Tailwind ("usa text-[44px] en vez de 28px").
"""
import json
import os
import re
from pathlib import Path

import numpy as np
from PIL import Image

from extraer import ESCRITORIO, MAX_ALTO, MOVIL, NAV_ARGS, JS_MEDIR, capturar

ANCHO_CMP = 640


# ---------------------------------------------------------------- similitud de imágenes
def _gris(img, tam):
    return np.asarray(img.convert("L").resize(tam, Image.BILINEAR), dtype=np.float64)


def _caja(a, k=7):
    """Media local con ventana k×k (filtro de caja con sumas acumuladas)."""
    p = k // 2
    a = np.pad(a, p, mode="edge")
    c = a.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def ssim(a, b):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    ma, mb = _caja(a), _caja(b)
    va, vb = _caja(a * a) - ma ** 2, _caja(b * b) - mb ** 2
    cov = _caja(a * b) - ma * mb
    m = ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))
    return float(np.clip(m.mean(), 0, 1))


def tapar(img, cajas):
    """Fotos y vídeos tapados con una caja gris en su sitio: se compara la MAQUETA (posición y tamaño de cada medio),
    no qué foto o qué fotograma del vídeo salió."""
    if not cajas:
        return img
    from PIL import ImageDraw
    img = img.copy()
    d = ImageDraw.Draw(img)
    for c in cajas:
        if c.get("w", 0) >= 40 and c.get("h", 0) >= 30:
            d.rectangle((c["x"], c["y"], c["x"] + c["w"], c["y"] + c["h"]), outline=(128, 128, 128), width=2)
    return img


def similitud(ruta_ref, ruta_gen, cajas_ref=None, cajas_gen=None):
    """0-100. 50% SSIM (estructura), 30% colores, 20% altura parecida. Con cajas: fotos y vídeos tapados en las dos."""
    ref, gen = Image.open(ruta_ref).convert("RGB"), Image.open(ruta_gen).convert("RGB")
    ref, gen = tapar(ref, cajas_ref), tapar(gen, cajas_gen)
    alto = max(8, int(ref.height * ANCHO_CMP / ref.width))
    tam = (ANCHO_CMP, min(alto, 1600))
    s = ssim(_gris(ref, tam), _gris(gen, tam))
    ha = np.asarray(ref.resize((80, 80)).quantize(24).convert("RGB")).reshape(-1, 3) // 32
    hb = np.asarray(gen.resize((80, 80)).quantize(24).convert("RGB")).reshape(-1, 3) // 32
    ka = {}
    for c in map(tuple, ha):
        ka[c] = ka.get(c, 0) + 1
    kb = {}
    for c in map(tuple, hb):
        kb[c] = kb.get(c, 0) + 1
    col = sum(min(v, kb.get(k, 0)) for k, v in ka.items()) / len(ha)
    alt = max(0.0, 1 - abs(gen.height - ref.height) / max(ref.height, 1))
    return round(100 * (0.5 * s + 0.3 * col + 0.2 * alt))


# ---------------------------------------------------------------- medir la página generada
def medir_generada(ruta_html, carpeta):
    """Renderiza la página generada, recorta cada <div data-clon-sec> y mide sus textos."""
    from playwright.sync_api import sync_playwright
    carpeta = Path(carpeta)
    res = {}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        for nombre, (w, h) in (("escritorio", ESCRITORIO), ("movil", MOVIL)):
            page = nav.new_page(viewport={"width": w, "height": h})
            css_local = os.environ.get("CLON_TAILWIND_CSS")       # solo para pruebas sin internet
            if css_local and Path(css_local).exists():
                js = "document.head.appendChild(Object.assign(document.createElement('style'),{textContent:" + json.dumps(Path(css_local).read_text()) + "}));window.tailwind={};"
                def servir(route, *_):
                    route.fulfill(status=200, content_type="application/javascript", body=js)
                page.route("**/cdn.tailwindcss.com/**", servir)
            try:
                page.goto(Path(ruta_html).resolve().as_uri(), wait_until="networkidle", timeout=40000)
            except Exception:
                page.wait_for_timeout(3000)
            page.wait_for_timeout(700)
            datos = page.evaluate(JS_MEDIR)
            alto = min(datos["alto_total"], MAX_ALTO)
            cap = carpeta / f"generada_{nombre}.png"
            capturar(page, cap, w, alto)
            ancho_real = page.evaluate("document.documentElement.scrollWidth")
            img = Image.open(cap)
            for s in datos["secciones"]:
                # con su caja propia, como las fotos de la original (captura del elemento, solapes incluidos)
                y, a = s.get("y_caja", s["y"]), s.get("alto_caja", s["alto"])
                y0, y1 = max(0, y), min(img.height, y + max(a, 1))
                if y1 - y0 >= 4:
                    img.crop((0, y0, img.width, y1)).save(carpeta / f"gen_{s['n']}_{nombre}.png")
                d = res.setdefault(s["n"], {})
                d[nombre] = s
            res.setdefault("_desborde", {})[nombre] = ancho_real > w + 1
            page.close()
        nav.close()
    return res


# ---------------------------------------------------------------- diferencias de estilo
def _norm(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _dist_color(a, b):
    if not a or not b:
        return 0
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return sum((x - y) ** 2 for x, y in zip(pa, pb)) ** 0.5


def diferencias(sec_ref, gen, limite=14):
    """Lista de correcciones exactas para una sección."""
    out = []
    g_esc = gen.get("escritorio") if gen else None
    if not g_esc:
        return [f"La sección {sec_ref['n']} no aparece en tu HTML: créala dentro de su <div data-clon-sec=\"{sec_ref['n']}\">."]
    if _dist_color(sec_ref["fondo"], g_esc["fondo"]) > 30:
        out.append(f"Fondo de la sección: es {g_esc['fondo']} y debe ser {sec_ref['fondo']} -> bg-[{sec_ref['fondo']}]")
    ra, ga = sec_ref["alto"], g_esc["alto"]
    if ra and abs(ga - ra) / ra > 0.3:
        out.append(f"Altura en escritorio: mide {ga}px y la original {ra}px -> ajusta paddings/tamaños (py-, h-[{ra}px] si es un bloque fijo)")
    if sec_ref.get("columnas", 1) != g_esc.get("columnas", 1):
        out.append(f"Columnas en escritorio: tienes {g_esc.get('columnas', 1)} y la original tiene {sec_ref['columnas']} -> md:grid-cols-{sec_ref['columnas']} o md:flex-row")
    g_mov = gen.get("movil")
    if g_mov and sec_ref.get("columnas_movil", 1) != g_mov.get("columnas", 1):
        out.append(f"Columnas en móvil: tienes {g_mov.get('columnas', 1)} y deben ser {sec_ref['columnas_movil']} -> grid-cols-{sec_ref['columnas_movil']} (sin prefijo)")
    if sec_ref.get("carrusel") and not g_esc.get("carrusel"):
        out.append("Estructura: la original es un CARRUSEL horizontal (tarjetas en fila que se deslizan) y la tuya no "
                   "-> contenedor flex gap-[20px] overflow-x-auto snap-x snap-mandatory; cada tarjeta snap-start shrink-0 w-[85%] md:w-[NNNpx]")
    if sec_ref.get("superpuesto") and not g_esc.get("superpuesto"):
        out.append("Estructura: en la original el texto va ENCIMA de la imagen/vídeo y en la tuya no "
                   "-> sección relative; imagen absolute inset-0 w-full h-full object-cover; texto en un div absolute (bottom/left)")
    if not sec_ref.get("superpuesto") and g_esc.get("superpuesto"):
        out.append("Estructura: en la original el texto NO va encima de la imagen: sácalo fuera (debajo o al lado)")
    gen_textos = {_norm(t["t"]): t for t in g_esc["textos"]}
    gen_mov = {_norm(t["t"]): t for t in (g_mov or {}).get("textos", [])}
    for t in sec_ref["textos"]:
        k = _norm(t["t"])
        if len(k) < 3:
            continue
        g = gen_textos.get(k) or next((v for kk, v in gen_textos.items() if k in kk or (len(kk) > 8 and kk in k)), None)
        corto = t["t"][:60]
        if not g:
            out.append(f'Falta el texto "{corto}" ({t["px"]}px, peso {t["peso"]}, color {t["color"]})')
            continue
        cambios = []
        if abs(g["px"] - t["px"]) / max(t["px"], 1) > 0.12:
            cambios.append(f"tamaño {g['px']}px -> md:text-[{t['px']}px]")
        if abs(g["peso"] - t["peso"]) >= 200:
            cambios.append(f"peso {g['peso']} -> font-[{t['peso']}]")
        if _dist_color(g["color"], t["color"]) > 45:
            cambios.append(f"color {g['color']} -> text-[{t['color']}]")
        if t["may"] != g["may"]:
            cambios.append("mayúsculas -> " + ("uppercase" if t["may"] else "quita uppercase (escribe el texto tal cual)"))
        if t["alinea"] in ("center", "left", "start") and g["alinea"] != t["alinea"] and \
                {t["alinea"], g["alinea"]} not in ({"left", "start"},):
            cambios.append(f"alineación -> text-{'center' if t['alinea'] == 'center' else 'left'}")
        gm = gen_mov.get(k)
        if gm and t.get("px_movil") and abs(gm["px"] - t["px_movil"]) / max(t["px_movil"], 1) > 0.15:
            cambios.append(f"en móvil {gm['px']}px -> text-[{t['px_movil']}px]")
        if cambios:
            out.append(f'Texto "{corto}": ' + ", ".join(cambios))
    return out[:limite]


def lista_comprobacion(sec_ref, difs_completas):
    """% de la lista automática (sacada de las medidas de la original) que cumple el clon."""
    total = 6 + sum(5 + (1 if t.get("px_movil") else 0) for t in sec_ref["textos"] if len(_norm(t["t"])) >= 3)
    fallos = 0
    for d in difs_completas:
        if d.startswith('Texto "'):
            fallos += 1 + d.count(", ")
        elif d.startswith("Falta el texto"):
            fallos += 5
        elif d.startswith("La sección"):
            fallos += total
        else:
            fallos += 1
    return max(0, round(100 * (1 - fallos / max(total, 1)))), total


def comparar(spec, carpeta_orig, ruta_html, carpeta_trabajo):
    carpeta_orig, carpeta_trabajo = Path(carpeta_orig), Path(carpeta_trabajo)
    carpeta_trabajo.mkdir(parents=True, exist_ok=True)
    gen = medir_generada(ruta_html, carpeta_trabajo)
    por_sec = {}
    total_peso, total = 0, 0.0
    for s in spec["secciones"]:
        n = s["n"]
        sims = {}
        mov_ref = {x["n"]: x for x in ((spec.get("movil_medido") or {}).get("secciones") or [])}
        for vista in ("escritorio", "movil"):
            ref, g = carpeta_orig / f"sec_{n}_{vista}.png", carpeta_trabajo / f"gen_{n}_{vista}.png"
            c_ref = s.get("imagenes") if vista == "escritorio" else mov_ref.get(n, {}).get("imagenes")
            c_gen = ((gen.get(n) or {}).get(vista) or {}).get("imagenes")
            # sin foto de la original en esa vista (el análisis no localizó la sección en móvil) no hay con qué
            # comparar: esa vista no cuenta; si la original la tiene y el clon no, es un 0
            sims[vista] = (similitud(ref, g, c_ref, c_gen) if g.exists() else 0) if ref.exists() else None
        if sims["movil"] is None or sims["escritorio"] is None:
            sim = round(sims["escritorio"] if sims["movil"] is None else sims["movil"] or 0)
        else:
            sim = round(0.6 * sims["escritorio"] + 0.4 * sims["movil"])
        completas = diferencias(s, gen.get(n), limite=999)
        lista, checks = lista_comprobacion(s, completas)
        por_sec[n] = {"similitud": sim, "escritorio": "—" if sims["escritorio"] is None else sims["escritorio"],
                      "movil": "—" if sims["movil"] is None else sims["movil"], "diferencias": completas[:14],
                      "lista": lista, "comprobaciones": checks}
        peso = max(s["alto"], 60)
        total_peso += peso
        total += sim * peso
    desb = gen.get("_desborde", {})
    return {"similitud_global": round(total / max(total_peso, 1)), "secciones": por_sec,
            "desborde_movil": bool(desb.get("movil"))}


def imagen_comparativa(carpeta_orig, carpeta_trabajo, destino, vista="escritorio", ancho=520):
    """Original a la izquierda, generada a la derecha."""
    a = Image.open(Path(carpeta_orig) / f"original_{vista}.png").convert("RGB")
    b = Image.open(Path(carpeta_trabajo) / f"generada_{vista}.png").convert("RGB")
    a = a.resize((ancho, int(a.height * ancho / a.width)))
    b = b.resize((ancho, int(b.height * ancho / b.width)))
    lienzo = Image.new("RGB", (ancho * 2 + 16, max(a.height, b.height)), "white")
    lienzo.paste(a, (0, 0))
    lienzo.paste(b, (ancho + 16, 0))
    lienzo.save(destino)
