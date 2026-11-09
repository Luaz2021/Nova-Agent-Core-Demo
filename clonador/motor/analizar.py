import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
PASOS 1-3 · ANALIZAR UNA WEB (todo con scripts + "ojos" opcionales)

  python analizar.py https://web.com          (o sin URL: lee url.txt)
  python analizar.py URL --sin-ojos           (sin qwen2.5vl)
  python analizar.py URL --sin-dinamico       (sin explorador_dinamico.py: análisis rápido, hover a la antigua)
  python analizar.py URL --paginas=4          (además, hasta 3 subpáginas del menú en subpaginas/)

1. ANÁLISIS: tecnología, tipo de web, iframes, sistema de diseño, componentes, hover, scroll, animaciones,
   rendimiento, accesibilidad.
2. FOTOS: página completa en PC (1280), tablet (768) y móvil (375); cada sección en PC y móvil;
   fotogramas al bajar con el scroll; antes/después del hover de botones y tarjetas.
3. OJOS (qwen2.5vl): describe la composición de cada sección en PC y en móvil.

Resultado en workspace/<web>/  (siguiente paso de la cadena oficial: crear.py -> verificar.py):
  informe_pc.md            la web en escritorio (lo primero que lee Claude)
  interactividad.json      pestañas, colores, modales, hover, vídeo/canvas/iframes (explorador_dinamico.py)
  informe_movil.md         la web en móvil
  diferencias_pc_movil.md  solo lo que cambia entre PC y móvil
  fichas_secciones.md      ficha de cada sección con medidas PC + móvil (lo que recibe Qwen Coder)
  datos.json               todo lo medido
  capturas/                imágenes
"""
import base64
import hashlib
import io
import shutil
import json
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
import diseccionar as dz  # noqa: E402
import medios  # noqa: E402
from extraer import (CSS_DESPLEGAR, JS_DESPLEGAR, JS_LIMPIAR, JS_MEDIR, JS_SECCIONES, LOCALE, MAX_SECCIONES, NAV_ARGS, nombre_web,  # noqa: E402
                     MAX_ALTO, PaginaVacia, capturar, comprobar_pagina, extraer, fuente_google, preparar_pagina, remapear)

OLLAMA = "http://127.0.0.1:11434"
def _modelo_nova(clave, defecto):
    try:
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8")).get(clave, defecto)
    except Exception:
        return defecto

MODELO_OJOS = _modelo_nova("vl", "blaifa/InternVL3_5:8b")
SALIDA = BASE.parent / "workspace"

PASOS = 9
_T0 = [0.0]


def barra(paso, texto, total=PASOS):
    """Línea de progreso: [######------] 45%  paso 4/9 · hojas de estilo  (0:52)"""
    if not _T0[0]:
        _T0[0] = time.time()
    pct = int(100 * paso / total)
    llenos = pct * 24 // 100
    t = int(time.time() - _T0[0])
    print(f"  [{'#' * llenos}{'-' * (24 - llenos)}] {pct:3d}%  paso {int(paso)}/{total} · {texto}  ({t // 60}:{t % 60:02d})", flush=True)


JS_HOVER_CANDIDATOS = r"""
() => {
  const out = []; const vistos = new Set();
  const cands = [...document.querySelectorAll('a, button, [role="button"], [class*="card"], [class*="product"]')];
  for (const e of cands) {
    const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    if (r.width < 40 || r.height < 20 || r.height > innerHeight * 2 || r.top + scrollY < 0 || s.visibility === 'hidden' || s.display === 'none') continue;
    if (r.top >= 0 && r.top < innerHeight - 10) { const p = document.elementFromPoint(r.left + r.width / 2, r.top + Math.min(r.height / 2, 20));
      if (p && p !== e && !e.contains(p) && !p.contains(e) && p.tagName !== 'CANVAS') continue; }   // tapado por otra capa (un canvas 3D no cuenta)
    const t = (e.innerText || e.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim().slice(0, 40);
    const clave = e.tagName + Math.round(r.width) + 'x' + Math.round(r.height) + s.backgroundColor;
    if (vistos.has(clave)) continue; vistos.add(clave);
    const tipo = (e.tagName === 'BUTTON' || /btn|button/i.test(e.className) || (s.backgroundColor !== 'rgba(0, 0, 0, 0)' && r.height < 80)) ? 'botón'
               : (r.height > 150 ? 'tarjeta' : 'enlace');
    e.setAttribute('data-clon-hover', out.length);
    out.push({ i: out.length, tipo, texto: t, w: Math.round(r.width), h: Math.round(r.height) });
    if (out.length >= 10) break;
  }
  return out;
}
"""
JS_ESTILO = r"""
(sel) => { const e = document.querySelector(sel); if (!e) return null; const s = getComputedStyle(e);
  const o = {}; for (const p of ['color', 'background-color', 'border-color', 'box-shadow', 'transform', 'opacity', 'text-decoration-line', 'filter', 'scale', 'translate'])
    o[p] = s.getPropertyValue(p);
  const img = e.querySelector('img'); if (img) { const si = getComputedStyle(img); o['img-transform'] = si.transform; o['img-opacity'] = si.opacity; }
  const r = e.getBoundingClientRect(); o['caja'] = [Math.round(r.left), Math.round(r.top + scrollY), Math.round(r.width), Math.round(r.height)].join(',');
  return o; }
"""


def hover_forzado(page, sel):
    """Activa :hover desde las herramientas de desarrollo (CDP), sin ratón: sirve aunque un canvas 3D tape el botón."""
    cdp = page.context.new_cdp_session(page)
    try:
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        raiz = cdp.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        nodo = cdp.send("DOM.querySelector", {"nodeId": raiz, "selector": sel})["nodeId"]
        if not nodo:
            return None
        cdp.send("CSS.forcePseudoState", {"nodeId": nodo, "forcedPseudoClasses": ["hover"]})
        page.wait_for_timeout(500)
        despues = page.evaluate(JS_ESTILO, sel)
        cdp.send("CSS.forcePseudoState", {"nodeId": nodo, "forcedPseudoClasses": []})
        return despues
    finally:
        try:
            cdp.detach()
        except Exception:
            pass


def probar_hover(page, carpeta):
    """Pasa el ratón por botones y tarjetas y anota qué cambia (y foto antes/después del primero de cada tipo)."""
    resultados = []
    try:
        page.add_style_tag(content=CSS_DESPLEGAR)
        page.evaluate(JS_LIMPIAR)            # quitar banners de cookies y capas que tapan el ratón
        page.wait_for_timeout(300)
        cands = page.evaluate(JS_HOVER_CANDIDATOS)
    except Exception:
        return resultados
    fotos = set()

    def foto(el, nombre):
        try:
            el.screenshot(path=str(carpeta / nombre), timeout=3000)
        except Exception:
            pass
    for c in cands:
        sel = f'[data-clon-hover="{c["i"]}"]'
        el = page.locator(sel).first
        try:
            el.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        page.mouse.move(2, 2)
        page.wait_for_timeout(250)
        antes = page.evaluate(JS_ESTILO, sel)
        if not antes:
            continue
        primera = c["tipo"] not in fotos
        if primera:
            foto(el, f"hover_{c['tipo']}_antes.png")
        try:
            try:
                el.hover(timeout=2500)
            except Exception:              # algo tapa el elemento: mover el ratón a su centro igualmente
                b = el.bounding_box()
                if b:
                    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + min(b["height"] / 2, 20))
            page.wait_for_timeout(600)
        except Exception:
            pass
        despues = page.evaluate(JS_ESTILO, sel) or antes
        cambios = {p: (antes[p], despues[p]) for p in antes if antes[p] != despues[p] and p != "caja"}
        forzado = False
        if not cambios:                       # el ratón no llegó (canvas encima, scroll virtual...): :hover forzado
            try:
                forz = hover_forzado(page, sel)
                if forz:
                    cambios = {p: (antes[p], forz[p]) for p in antes if antes[p] != forz[p] and p != "caja"}
                    forzado = bool(cambios)
            except Exception:
                pass
        if primera:
            foto(el, f"hover_{c['tipo']}_despues.png")
            fotos.add(c["tipo"])
        if antes["caja"] != despues["caja"]:
            cambios["posición/tamaño"] = (antes["caja"], despues["caja"])
        resultados.append({**c, "cambios": cambios, "forzado": forzado})
    page.mouse.move(2, 2)
    return resultados


def fotogramas_scroll(page, carpeta, max_fotos=6):
    """Fotos de la pantalla bajando con la RUEDA del ratón (las webs con scroll suave o 3D ignoran scrollTo)."""
    alto = page.evaluate("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)")
    vh = page.evaluate("innerHeight")
    paso = max(vh * 0.8, alto / max_fotos)
    page.mouse.move(640, vh / 2)
    for n in range(max_fotos):
        page.screenshot(path=str(carpeta / f"scroll_{n:02d}.png"))
        antes = page.evaluate("scrollY")
        for _ in range(4):
            page.mouse.wheel(0, paso / 4)
            page.wait_for_timeout(150)
        page.wait_for_timeout(700)
        if page.evaluate("scrollY") == antes and alto > vh * 1.2:
            page.evaluate(f"window.scrollTo(0, {int(antes + paso)})")      # la rueda no movió: scroll normal
            page.wait_for_timeout(500)
    page.evaluate("window.scrollTo(0,0)")
    return max_fotos


def grabar_scroll(nav, url, carpeta, segundos=36):
    """Graba vídeo WebM bajando sección a sección: espera 3-4s por bloque y prueba rolls laterales (izq-der) y verticales."""
    tmp = carpeta / "_video"
    ctx = nav.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=str(tmp),
                          record_video_size={"width": 1920, "height": 1080}, locale=LOCALE)
    page = ctx.new_page()
    try:
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
        except Exception:
            page.wait_for_timeout(4000)
        page.evaluate(JS_LIMPIAR)
        page.wait_for_timeout(3000)

        # paradas: el principio de cada sección (o cada 850 px si la web no marca secciones)
        paradas = page.evaluate("""() => {
            const sels = Array.from(document.querySelectorAll('section, main > div, [data-unit-id], .unit-wrapper'));
            const tops = sels.map(el => Math.round(el.getBoundingClientRect().top + window.scrollY))
                             .filter(top => top >= 0);
            const unicos = Array.from(new Set(tops)).sort((a,b) => a - b);
            if (unicos.length >= 3) return unicos.slice(0, 10);
            
            // Si no hay secciones sem?nticas, generar paradas por viewport (1080px)
            const maxH = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
            const res = [];
            for (let y = 0; y < maxH; y += 850) res.push(y);
            return res.slice(0, 10);
        }""")
        for y in paradas:
            # baja hasta la sección y espera a que acaben sus animaciones de entrada
            page.evaluate(f"window.scrollTo({{ top: {y}, behavior: 'smooth' }})")
            page.wait_for_timeout(1000)

            # tiempo para que se vea la sección quieta en el vídeo
            page.wait_for_timeout(3500)

            # ¿hay un carrusel horizontal en pantalla? se le da un roll lateral (ida y vuelta)
            tiene_roll = page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('*'));
                for (const el of els) {
                    const r = el.getBoundingClientRect();
                    if (r.top >= 0 && r.bottom <= window.innerHeight && el.scrollWidth > el.clientWidth + 60) {
                        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
                    }
                }
                return null;
            }""")
            if tiene_roll:
                page.mouse.move(tiene_roll["x"], tiene_roll["y"])
                page.mouse.wheel(400, 0)
                page.wait_for_timeout(1500)
                page.mouse.wheel(-400, 0)
                page.wait_for_timeout(1000)

            # roll vertical corto para disparar efectos ligados al scroll
            page.mouse.wheel(0, 150)
            page.wait_for_timeout(500)
        page.wait_for_timeout(1000)
    finally:
        ctx.close()
    videos = sorted(tmp.glob("*.webm"))
    if videos:
        shutil.move(str(videos[-1]), carpeta / "scroll_pc.webm")
    shutil.rmtree(tmp, ignore_errors=True)
    return bool(videos)


def interceptar_red_assets(page, carpeta_assets, max_assets=120):
    """Guarda assets de red críticos (imágenes, webp, svg, fuentes) sin fugas de disco ni RAM."""
    carpeta_assets = Path(carpeta_assets)
    carpeta_assets.mkdir(parents=True, exist_ok=True)
    guardados = set()
    mapa = {}  # URL -> archivo en assets/ (lo lee herramientas/exportar_react.py)

    def al_responder(response):
        try:
            if len(guardados) >= max_assets:
                return
            url = response.url
            if not url or url.startswith("data:") or url in guardados:
                return
            url_baja = url.lower()
            if any(t in url_baja for t in ("analytics", "tracker", "telemetry", "metrics", "doubleclick", "facebook", "clarity", "hotjar")):
                return
            ct = response.headers.get("content-type", "").lower()
            if not any(t in ct for t in ("image/", "font/", "svg")):
                return
            if response.status >= 400:
                return
            body = response.body()
            if not body or len(body) > 12 * 1024 * 1024:
                return
            parsed = urlparse(url)
            nombre = Path(parsed.path).name
            if not nombre or len(nombre) > 50 or "." not in nombre:
                ext = (".png" if "png" in ct else ".jpg" if "jpeg" in ct or "jpg" in ct else ".svg" if "svg" in ct
                       else ".webp" if "webp" in ct else ".bin")
                nombre = f"asset_{len(guardados):03d}{ext}"
            nombre_limpio = "".join(c if c.isalnum() or c in ".-_" else "_" for c in nombre)
            destino = carpeta_assets / nombre_limpio
            # mismo nombre y otra URL (p. ej. las portadas de Apple TV: todas «1250x668sr.jpg»): no pisar, añadir hash
            if nombre_limpio in mapa.values():
                destino = carpeta_assets / f"{destino.stem}_{hashlib.sha1(url.encode()).hexdigest()[:8]}{destino.suffix}"
            destino.write_bytes(body)
            guardados.add(url)
            mapa[url] = destino.name
            (carpeta_assets / "_mapa.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=0), encoding="utf-8")
        except Exception:
            return

    page.on("response", al_responder)


def extraer_rutas_internas(page, host, max_rutas=5):
    """Extrae enlaces internos del menú de navegación sin bucles, páginas externas ni archivos binarios."""
    js = """
    (host) => {
        const out = [];
        const seen = new Set();
        const links = Array.from(document.querySelectorAll('nav a[href], header a[href], [role="navigation"] a[href]'));
        for (const a of links) {
            let href = a.getAttribute('href') || '';
            if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:')) continue;
            try {
                const u = new URL(href, window.location.origin);
                if (u.hostname.replace('www.', '') !== host.replace('www.', '')) continue;
                if (/\\.(pdf|zip|mp4|webm|jpg|png|webp|dmg|exe)$/i.test(u.pathname)) continue;
                let p = u.pathname.replace(/\\/+$/, '') || '/';
                if (p === '/' || seen.has(p)) continue;
                seen.add(p);
                const texto = (a.innerText || a.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
                out.push({ ruta: p, url: u.href, texto: texto || p });
            } catch (e) {}
        }
        return out;
    }
    """
    try:
        candidatos = page.evaluate(js, host)
        return candidatos[:max_rutas]
    except Exception:
        return []


def ojos_disponibles():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=5) as r:
            return any(MODELO_OJOS in m["name"] or "internvl" in m["name"].lower() or "vl" in m["name"].lower() for m in json.loads(r.read())["models"])
    except Exception:
        return False


def describir(ruta, vista):
    from PIL import Image
    with Image.open(ruta) as raw:
        img = raw.convert("RGB")
    if img.height > 1600:
        c = img.crop((0, 0, img.width, 1600))
        img.close()
        img = c
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    try:
        img.save(buf, "PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode()
    finally:
        buf.close()
        img.close()
    prompt = (f"Esta imagen es una franja de una página web vista en {'ordenador' if vista == 'pc' else 'móvil'}. "
              "Describe en español, en 3 a 5 frases cortas, SOLO la composición: qué hay a la izquierda, centro y derecha (o arriba/abajo), "
              "tipo de imágenes (foto de producto, foto de personas, ilustración, icono, logo, captura de app), fondos, tarjetas, bordes, sombras "
              "y esquinas. No transcribas los textos.")
    datos = {"model": MODELO_OJOS, "prompt": prompt, "images": [b64_img], "stream": False,
             "options": {"temperature": 0, "seed": 42, "num_predict": 220}}
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(datos).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return " ".join(json.loads(r.read())["response"].split())


# ---------------------------------------------------------------- informes
def _sec_linea(s, cols=None):
    primero = s["textos"][0]["t"][:40] if s["textos"] else "(sin texto)"
    c = f" · col {cols}" if cols else f" · {s.get('columnas', 1)} col"
    return (f"- **S{s['n']}** {s['alto']}px · fondo `{s['fondo']}`{c} · {s.get('total_textos', len(s['textos']))} textos, "
            f"{len(s['botones'])} botones, {len(s['imagenes'])} img · \"{primero}\"")


def informe_pc(d):
    base = dz.informe_md(d)                     # tecnología, diseño, componentes, movimiento, secciones, rendimiento
    extra = []
    if d.get("avisos"):
        extra += ["", "## ⚠ Avisos"] + [f"- {a}" for a in d["avisos"]]
    extra += ["", "## Hover (pasando el ratón)"]
    if d["hover"]:
        for h in d["hover"][:8]:
            cambios = "; ".join(f"{p}: {a[:28]} → {b[:28]}" for p, (a, b) in list(h["cambios"].items())[:3]) or "sin cambios visibles"
            extra.append(f"- {h['tipo']} \"{h['texto'][:25]}\" ({h['w']}x{h['h']}): {cambios}")
    elif d.get("hover_fuente"):
        extra.append(f"- lo mide el explorador dinámico: ver {d['hover_fuente']} (resumen al final de este informe)")
    else:
        extra.append("- (no se pudo probar)")
    if d.get("ojos"):
        extra += ["", "## Composición por sección (ojos, PC)"]
        extra += [f"- **S{n}:** {v['pc']}" for n, v in sorted(d["ojos"].items(), key=lambda x: int(x[0])) if v.get("pc")]
    if d.get("video_scroll"):
        extra += ["", "## Vídeo", "- vídeo del scroll en PC (24 s, bajando con la rueda): `capturas/scroll_pc.webm`"]
    extra += ["", f"_Capturas: {d['capturas']}_"]
    return base.replace("# Disección:", "# Informe PC (1280px):", 1) + "\n".join(extra) + "\n"


def informe_movil(d):
    L = [f"# Informe MÓVIL (375px): {d['url']}", ""]
    m = d["movil"]
    L.append(f"- alto total {m['alto_total']}px (PC {d.get('alto_pc', '?')}px) · {len(m['secciones'])} secciones medidas")
    L.append(f"- menú: {d['menu_movil']}")
    if d["movimiento"]["fijos"]:
        L.append(f"- fijos/sticky en PC: {len(d['movimiento']['fijos'])} (revisar si siguen en móvil)")
    L += ["", "## Secciones en móvil"]
    pc = {s["n"]: s for s in d["secciones"]}
    for s in m["secciones"]:
        L.append(_sec_linea(s))
        for t in s["textos"][:4]:
            L.append(f"  - <{t['tag']}> \"{t['t'][:50]}\" {t['px']}px p{t['peso']} {t['color']}{' MAYÚS' if t['may'] else ''}")
    if d.get("ojos"):
        L += ["", "## Composición por sección (ojos, móvil)"]
        L += [f"- **S{n}:** {v['movil']}" for n, v in sorted(d["ojos"].items(), key=lambda x: int(x[0])) if v.get("movil")]
    return "\n".join(L) + "\n"


def diferencias(d):
    L = [f"# Diferencias PC → móvil: {d['url']}", "", f"- menú: {d['menu_movil']}"]
    pc = {s["n"]: s for s in d["secciones"]}
    mv = {s["n"]: s for s in d["movil"]["secciones"]}
    for n in sorted(pc):
        p, m = pc[n], mv.get(n)
        cambios = []
        if not m or m["alto"] < 5:
            L.append(f"- **S{n}:** NO aparece en móvil")
            continue
        cp = p.get("columnas_por_ancho", {})
        if cp.get("escritorio") != cp.get("movil"):
            cambios.append(f"columnas {cp.get('escritorio')} → {cp.get('movil')}" + (f" (tablet {cp.get('tablet')})" if cp.get("tablet") not in (cp.get("escritorio"), cp.get("movil")) else ""))
        if p["alto"] and abs(m["alto"] - p["alto"]) / p["alto"] > 0.2:
            cambios.append(f"alto {p['alto']} → {m['alto']}px")
        if p["fondo"] != m["fondo"] and not p.get("fondo_dudoso") and not p.get("fondo_css"):   # con canvas/vídeo de fondo el CSS no es fiable
            cambios.append(f"fondo {p['fondo']} → {m['fondo']}")
        tp = {t["t"]: t for t in p["textos"]}
        tm = {t["t"]: t for t in m["textos"]}
        for t, a in list(tp.items())[:30]:
            b = tm.get(t)
            if b and abs(a["px"] - b["px"]) >= 4:
                cambios.append(f"\"{t[:25]}\" {a['px']} → {b['px']}px")
        solo_pc = [t for t in tp if t not in tm]
        solo_m = [t for t in tm if t not in tp]
        if solo_pc:
            cambios.append(f"solo en PC: {len(solo_pc)} textos (p. ej. \"{solo_pc[0][:25]}\")")
        if solo_m:
            cambios.append(f"solo en móvil: {len(solo_m)} textos (p. ej. \"{solo_m[0][:25]}\")")
        if len(p["imagenes"]) != len(m["imagenes"]):
            cambios.append(f"imágenes {len(p['imagenes'])} → {len(m['imagenes'])}")
        L.append(f"- **S{n}:** " + ("; ".join(cambios[:7]) if cambios else "igual (solo se estrecha)"))
    return "\n".join(L) + "\n"


def fichas(d):
    fg = d["fuentes_google"]
    mv = {s["n"]: s for s in d["movil"]["secciones"]}
    L = [f"# Fichas por sección (PC + móvil) — {d['url']}", "",
         "Tokens: fuentes " + ", ".join(f"{k}→{v}" for k, v in list(fg.items())[:4]) +
         " · texto " + ", ".join(c for c, _ in d["diseno"]["colores_texto"][:5]) +
         " · fondos " + ", ".join(c for c, _ in d["diseno"]["colores_fondo"][:5]), ""]
    for s in d["secciones"]:
        m = mv.get(s["n"], {})
        cp = s.get("columnas_por_ancho", {})
        L.append(f"## Sección {s['n']}")
        if s.get("escena"):
            L.append(f"- **{s['escena'].upper()}** de {s['alto']}px: NO la escribe Qwen; el clon pone el vídeo del scroll o un fotograma a pantalla completa.")
        if s.get("fondo_dudoso") and any(c["contexto"].startswith("webgl") and c["fijo"] for c in d["especiales"].get("lienzos", [])):
            L.append("- ojo: el fondo lo pinta un canvas 3D fijo; el color de la ficha es aproximado (mira los fotogramas del scroll)")
        L.append(f"- PC: alto {s['alto']}px, {cp.get('escritorio', '?')} col · tablet {cp.get('tablet', '?')} col · móvil: alto {m.get('alto', '?')}px, {cp.get('movil', '?')} col · fondo {s['fondo']} · alineación {s.get('alineacion', '?')}")
        if d.get("ojos", {}).get(str(s["n"])):
            o = d["ojos"][str(s["n"])]
            if o.get("pc"):
                L.append(f"- composición PC: {o['pc']}")
            if o.get("movil"):
                L.append(f"- composición móvil: {o['movil']}")
        tm = {t["t"]: t for t in m.get("textos", [])}
        for t in s["textos"][:18]:
            b = tm.get(t["t"])
            mvpx = f" (móvil {b['px']}px)" if b and b["px"] != t["px"] else ("" if b else " (no se ve en móvil)")
            L.append(f"  - <{t['tag']}> \"{t['t'][:90]}\" {t['px']}px{mvpx} p{t['peso']} {t['color']} {fg.get(t['fuente'], 'Inter')}{' MAYÚS' if t['may'] else ''} {t['alinea']}")
        if s.get("total_textos", 0) > 18:
            L.append(f"  - (+{s['total_textos'] - 18} textos más)")
        for b in s["botones"][:4]:
            L.append(f"  - botón \"{b['t'][:30]}\" fondo {b['fondo']} texto {b['color']} radio {b['radio']}px pad {b['pad']} {b['px']}px")
        for im in [i for i in s["imagenes"] if i.get("tipo") != "svg"][:8]:
            L.append(f"  - {medios.tipo_imagen(im)} {im['w']}x{im['h']} en ({im['x']},{im['y']}) → marco aspect-[{medios.proporcion(im['w'], im['h'])}] color #{im.get('color', 'DDDDDD')}")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- principal
def analizar(url, con_ojos=True, max_paginas=1, dinamico=True):
    try:
        return _analizar(url, con_ojos, max_paginas, dinamico)
    except PaginaVacia as ex:
        out = SALIDA / nombre_web(url)
        out.mkdir(parents=True, exist_ok=True)
        aviso = (f"# ⚠ No se pudo analizar {url}\n\n**Motivo:** {ex}.\n\n"
                 "Muchas plataformas grandes (Behance, Instagram, LinkedIn, Amazon...) bloquean a los navegadores automáticos. "
                 "Prueba con otra web: landings de marcas, startups o tiendas pequeñas suelen funcionar.\n")
        (out / "AVISO.md").write_text(aviso, encoding="utf-8")
        print("\n" + "=" * 62 + f"\n  ⚠  NO SE PUDO ANALIZAR ESTA WEB\n  {ex}\n  Prueba con otra web.\n" + "=" * 62)
        sys.exit(2)


def _analizar(url, con_ojos=True, max_paginas=1, dinamico=True):
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    print(f"ANALIZAR - {url}")
    _T0[0] = time.time()
    host = urlparse(url).netloc.replace("www.", "") or "local"
    out = SALIDA / nombre_web(url)
    cap = out / "capturas"
    shutil.rmtree(cap, ignore_errors=True)          # fotos de un análisis anterior de la misma web
    cap.mkdir(parents=True, exist_ok=True)
    barra(0, "secciones y recortes PC + móvil (lo más largo)")
    spec, carpeta_sec = extraer(url, carpeta=out / "referencia", forzar=True)
    d = {"url": url, "fecha": time.strftime("%Y-%m-%d %H:%M"), "fuentes_google": spec["fuentes_google"],
         "capturas": str(cap)}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=NAV_ARGS)
        page = nav.new_context(viewport={"width": 1920, "height": 1080}, locale=LOCALE).new_page()
        interceptar_red_assets(page, out / 'assets')
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
        except Exception:
            page.wait_for_timeout(4000)
        page.wait_for_timeout(1500)
        comprobar_pagina(page)
        barra(1, "tecnología, contenido especial, rendimiento")
        d["tecnologia"] = page.evaluate(dz.JS_TECNOLOGIA)
        d["rendimiento"] = page.evaluate(dz.JS_RENDIMIENTO)
        d["especiales"] = page.evaluate(dz.JS_ESPECIALES)
        barra(2, "movimiento: animaciones, scroll y fotogramas")
        d["movimiento"] = page.evaluate(dz.JS_MOVIMIENTO)
        try:
            d["movimiento"]["scroll"] = dz.detectar_movimiento_scroll(page)
        except Exception:
            d["movimiento"]["scroll"] = []
        try:
            es3d = any(c["contexto"].startswith("webgl") for c in d["especiales"].get("lienzos", []))
            d["fotogramas_scroll"] = fotogramas_scroll(page, cap, 10 if es3d else 6)
        except Exception:
            d["fotogramas_scroll"] = 0
        barra(3, "hojas de estilo")
        d["css"] = dz.css_de_la_web(page)
        if dinamico:                              # una sola fuente de verdad: el explorador dinámico (al final)
            barra(4, "hover: lo mide el explorador dinámico al final")
            d["hover"], d["hover_fuente"] = [], "interactividad.json"
        else:
            barra(4, "hover de botones y tarjetas")
            d["hover"] = probar_hover(page, cap)
        barra(5, "diseño y componentes")
        preparar_pagina(page, url)
        page.evaluate(JS_SECCIONES, MAX_SECCIONES)
        remapear(page, spec["secciones"])
        d["diseno"] = page.evaluate(dz.JS_DISENO)
        d["componentes"] = page.evaluate(dz.JS_COMPONENTES)
        d["alto_pc"] = page.evaluate("document.documentElement.scrollHeight")
        mov = (len(d["movimiento"]["scroll"]) > 15 or d["movimiento"]["animaciones"]
               or any(e["cat"] == "3d" or "Lenis" in e["nombre"] or "Locomotive" in e["nombre"] for e in d["tecnologia"]["evidencias"])
               or any(c["contexto"].startswith("webgl") for c in d["especiales"].get("lienzos", [])) or any(s.get("carrusel") for s in spec.get("secciones", [])))
        if mov:
            barra(5.5, "grabando vídeo del scroll (la web tiene movimiento o 3D)")
            try:
                d["video_scroll"] = grabar_scroll(nav, url, cap)
            except Exception as ex:
                print(f"    (no se pudo grabar el vídeo: {ex})")
        barra(6, "fotos en PC, tablet y móvil")
        cols = {}
        for nombre, (w, h) in dz.ANCHOS.items():
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(1000)
            page.add_style_tag(content=CSS_DESPLEGAR)
            page.evaluate(JS_DESPLEGAR)
            page.evaluate(JS_LIMPIAR)
            for n, c, _ in page.evaluate(dz.JS_COLUMNAS):
                cols.setdefault(n, {})[nombre] = c
            if nombre == "movil":
                d["movil"] = spec.get("movil_medido") or page.evaluate(JS_MEDIR)     # medido en la carga móvil de verdad
                for s_ in spec["secciones"]:
                    cols.setdefault(s_["n"], {})["movil"] = s_.get("columnas_movil", cols.get(s_["n"], {}).get("movil", 1))
                vis = page.evaluate("""() => { const h = document.querySelector('header') || document.querySelector('[data-clon-sec="1"]'); if (!h) return null;
                    const links = [...h.querySelectorAll('a')].filter(a => a.getBoundingClientRect().width > 0 && (a.innerText||'').trim()).length;
                    const boton = [...h.querySelectorAll('button,summary,[aria-label*="menu" i],[class*="burger" i],[class*="menu-toggle" i]')].some(b => b.getBoundingClientRect().width > 0);
                    return {links, boton}; }""")
                d["menu_movil"] = ("hamburguesa (botón de menú, enlaces ocultos)" if vis and vis["boton"] and vis["links"] < 4
                                   else f"{vis['links']} enlaces visibles" if vis else "no detectado")
            alto = min(page.evaluate("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)"), MAX_ALTO)
            ref_m = carpeta_sec / "original_movil.png"
            try:
                if nombre == "movil" and ref_m.exists():
                    shutil.copy(ref_m, cap / "pagina_movil.png")     # la foto de la carga móvil de verdad
                else:
                    capturar(page, cap / f"pagina_{nombre}.png", w, alto)
            except Exception as ex:
                print(f"    (captura {nombre} falló: {ex})")
        nav.close()
    for s in spec["secciones"]:
        s["columnas_por_ancho"] = cols.get(s["n"], {})
        for v in ("escritorio", "movil"):
            p = carpeta_sec / f"sec_{s['n']}_{v}.png"
            if p.exists():
                (cap / f"sec_{s['n']}_{'pc' if v == 'escritorio' else 'movil'}.png").write_bytes(p.read_bytes())
    d["secciones"] = spec["secciones"]
    d["avisos"] = []
    if spec.get("tope_secciones"):
        d["avisos"].append(f"se llegó al máximo de secciones ({len(spec['secciones'])}): lo que haya después de la última no está analizado")
    if spec.get("alto_real", 0) > spec.get("alto_medido", 0) + 200:
        d["avisos"].append(f"la página mide {spec['alto_real']} px y se analizaron {spec['alto_medido']} px" + (" (scroll infinito: carga más al bajar)" if spec.get("infinita") else ""))
    # escenas: bloques muy altos con casi nada de texto = animación de scroll "fijada" (3D, vídeo, secuencia).
    # Qwen no las escribe: el clon pone el vídeo del scroll o un fotograma en su lugar.
    hay_gl = any(c["contexto"].startswith("webgl") for c in d["especiales"].get("lienzos", []))
    for s in d["secciones"]:
        alto_s, textos_s = s.get("alto_escritorio", s["alto"]), s.get("total_textos", len(s["textos"]))
        if (alto_s > 2400 and textos_s <= 3) or (alto_s > 1440 and textos_s <= 1):
            s["escena"] = "escena 3D (canvas WebGL)" if hay_gl else "escena animada con el scroll"
    spec_path = carpeta_sec / "spec.json"           # construir.py lee el spec: que también sepa cuáles son escenas
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    d["carpeta_referencia"] = str(carpeta_sec)
    d["clasificacion"] = dz.clasificar(d["tecnologia"], d["especiales"], d["diseno"], d["componentes"], d["secciones"], d["rendimiento"])
    d["recomendaciones"] = dz.recomendaciones(d)

    if max_paginas > 1:
        barra(6.5, f"descubriendo subpaginas (limite {max_paginas} rutas)")
        with sync_playwright() as pw_sub:
            nav_sub = pw_sub.chromium.launch(args=NAV_ARGS)
            try:
                ctx_sub = nav_sub.new_context(viewport={"width": 1920, "height": 1080}, locale=LOCALE)
                p_sub = ctx_sub.new_page()
                try:
                    p_sub.goto(url, wait_until="domcontentloaded", timeout=30000)
                    rutas = extraer_rutas_internas(p_sub, host, max_rutas=max_paginas - 1)
                finally:
                    p_sub.close()
                    ctx_sub.close()

                d["rutas_internas"] = rutas
                if rutas:
                    sub_dir = out / "subpaginas"
                    sub_dir.mkdir(parents=True, exist_ok=True)
                    arbol = {"raiz": url, "layout_compartido": ["Navbar", "Footer"], "paginas": [{"ruta": "/", "titulo": "Inicio", "carpeta": "."}]}
                    for r_idx, r in enumerate(rutas):
                        slug = r["ruta"].strip("/").replace("/", "_") or f"pag_{r_idx + 1}"
                        r_carpeta = sub_dir / slug
                        r_carpeta.mkdir(parents=True, exist_ok=True)
                        arbol["paginas"].append({"ruta": r["ruta"], "titulo": r["texto"], "carpeta": f"subpaginas/{slug}"})
                        ctx_r = nav_sub.new_context(viewport={"width": 1920, "height": 1080}, locale=LOCALE)
                        p_r = ctx_r.new_page()
                        try:
                            p_r.goto(r["url"], wait_until="domcontentloaded", timeout=30000)
                            p_r.wait_for_timeout(2000)
                            p_r.screenshot(path=str(r_carpeta / "pagina_pc.png"))
                            sub_spec = p_r.evaluate("""() => {
                                const main = document.querySelector('main, [role="main"], article') || document.body;
                                return {
                                    titulo: document.title,
                                    textos: Array.from(main.querySelectorAll('h1, h2, h3, p, button, a')).slice(0, 30).map(e => ({
                                        tag: e.tagName.toLowerCase(),
                                        texto: (e.innerText || '').trim().slice(0, 80)
                                    })).filter(x => x.texto.length > 2)
                                };
                            }""")
                            (r_carpeta / "resumen.json").write_text(json.dumps(sub_spec, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception as ex_r:
                            print(f"    (subpagina {r['ruta']} omitida: {ex_r})")
                        finally:
                            p_r.close()
                            ctx_r.close()
                    (out / "arbol_rutas.json").write_text(json.dumps(arbol, ensure_ascii=False, indent=2), encoding="utf-8")
            finally:
                try:
                    nav_sub.close()
                except Exception:
                    pass

    d["ojos"] = {}
    if con_ojos and ojos_disponibles():
        barra(7, f"ojos ({MODELO_OJOS}) describiendo {len(d['secciones'])} secciones")
        for i, s in enumerate(d["secciones"]):
            o = {}
            for vista in ("pc", "movil"):
                p = cap / f"sec_{s['n']}_{vista}.png"
                if p.exists():
                    try:
                        o[vista] = describir(p, vista)
                    except Exception as ex:
                        print(f"    (ojos S{s['n']} {vista}: {ex})")
            d["ojos"][str(s["n"])] = o
            barra(7 + (i + 1) / len(d["secciones"]), f"ojos: sección {s['n']} descrita")
    elif con_ojos:
        barra(8, "ojos: qwen2.5vl no disponible, sigo sin descripciones")

    (out / "datos.json").write_text(json.dumps(d, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    textos = {"informe_pc.md": informe_pc(d), "informe_movil.md": informe_movil(d),
              "diferencias_pc_movil.md": diferencias(d), "fichas_secciones.md": fichas(d)}
    for nombre, txt in textos.items():
        (out / nombre).write_text(txt, encoding="utf-8")
    (SALIDA / "ultimo_analisis.txt").write_text(str(out), encoding="utf-8")
    try:
        from interacciones import explorar_interacciones
        explorar_interacciones(url, carpeta_salida=out)
    except Exception as ex_interact:
        print(f"  (Aviso interacciones: {ex_interact})")
    if dinamico:
        try:
            from explorador_dinamico import explorar, resumen_md
            print("\nEXPLORADOR DINÁMICO (pestañas, colores, modales, hover, vídeo/canvas/iframes) — --sin-dinamico para saltarlo")
            res = explorar(url, carpeta_salida=out)
            textos["informe_pc.md"] += ("\n\n## Interactividad (explorador dinámico · detalle en interactividad.json)\n"
                                        + "\n".join(resumen_md(res)) + "\n")
            (out / "informe_pc.md").write_text(textos["informe_pc.md"], encoding="utf-8")
        except Exception as ex_din:
            print(f"  (Aviso explorador dinámico: {ex_din})")
    barra(PASOS, "terminado")
    print(f"\nListo en {time.time() - t0:.0f} s -> {out}")
    for nombre, txt in textos.items():
        print(f"  {nombre}: ~{len(txt) // 4} tokens")
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else (BASE / "url.txt").read_text(encoding="utf-8").strip().splitlines()[0].strip()
    con_ojos = "--sin-ojos" not in sys.argv
    max_pags = 1
    for a in sys.argv[1:]:
        if a.startswith("--paginas="):
            try:
                max_pags = max(1, int(a.split("=")[1]))
            except ValueError:
                pass
        elif a.startswith("--paginas"):
            idx = sys.argv.index(a)
            if idx + 1 < len(sys.argv) and sys.argv[idx + 1].isdigit():
                max_pags = max(1, int(sys.argv[idx + 1]))
    analizar(url, con_ojos=con_ojos, max_paginas=max_pags, dinamico="--sin-dinamico" not in sys.argv)
