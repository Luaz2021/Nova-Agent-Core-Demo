"""
RADAR WEB - mira varias webs reales de un sector EN LOCAL (0 tokens de nube) y devuelve un RESUMEN corto para Nova:
que secciones usa el sector y en que orden, tipo de hero, escala tipografica, densidad, roles de color y cuanto
usan fotos. Toma ESTRUCTURA y OFICIO, nunca identidad: no guarda textos, logos ni fotos ajenas.

    python radar_web.py --sector health            # webs del sector sacadas de las 202 de draw.mjs (sites.json)
    python radar_web.py --urls https://a.com,https://b.com
    python radar_web.py --lista urls.txt [--max 5] [--sin-vision] [--out <carpeta>]

Salida (por defecto herramientas/datos/referencias_web/<sector o 'lista'>/):
  resumen.txt   <- lo UNICO que lee Nova (unas 20 lineas)
  resumen.json  <- lo mismo en datos
  <dominio>/medidas.json + pc.png + movil.png (capturas solo locales, NO se suben a la nube)

Buenas maneras: respeta robots.txt, 4 s de pausa entre webs, cierra banners de cookies, una web que falla se apunta
como fallo y se sigue con la siguiente (nunca un resumen inventado).
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import statistics
import sys
import time
import urllib.request
import urllib.robotparser
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

NOVA = Path.home() / ".gemini"
SITES = NOVA / "antigravity" / "almacen" / "skills" / "gemini-ui-artisan" / "library" / "sites.json"
DATOS = Path(__file__).resolve().parent / "datos" / "referencias_web"
OLLAMA = "http://127.0.0.1:11434/api/chat"
AGENTE = "NovaRadar/1.0 (referencias de diseno, uso local)"
PAUSA = 4

JS_MEDIDAS = r"""() => {
  const vw = innerWidth, vh = innerHeight, H = document.documentElement.scrollHeight;
  const cs = (e) => getComputedStyle(e);
  const vis = (e) => { const r = e.getBoundingClientRect(), s = cs(e); return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const px = (v) => parseFloat(v) || 0;
  // bloques de primer nivel = secciones (hijos altos de main o body)
  // baja por los envoltorios (div#app > div > main...) hasta el nivel donde hay 3 o mas bloques altos
  const altos = (e) => [...e.children].filter(c => vis(c) && c.getBoundingClientRect().height > 160);
  let raiz = document.body, bloques = altos(raiz);
  for (let n = 0; n < 8 && bloques.length < 3; n++) {
    const mayor = [...raiz.children].filter(vis).sort((a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height)[0];
    if (!mayor) break; raiz = mayor; bloques = altos(raiz);
  }
  const secs = [...document.querySelectorAll('section')].filter(e => vis(e) && e.getBoundingClientRect().height > 160 && !e.parentElement.closest('section'));
  if (secs.length > bloques.length) bloques = secs;
  const tipo = (e) => {
    const r = e.getBoundingClientRect(), t = (e.innerText || '').toLowerCase();
    const imgs = [...e.querySelectorAll('img, picture, video, canvas')].filter(vis);
    const areaImg = imgs.reduce((a, i) => { const b = i.getBoundingClientRect(); return a + b.width * b.height; }, 0) / Math.max(1, r.width * r.height);
    const tarjetas = Math.max(0, ...[...e.querySelectorAll('*')].slice(0, 400).map(x => { const k = [...x.children].filter(vis); return k.length >= 3 && k.every(c => Math.abs(c.getBoundingClientRect().width - k[0].getBoundingClientRect().width) < 8) ? k.length : 0; }));
    if (e.tagName === 'FOOTER' || r.top + window.scrollY > H - 700 && /©|aviso legal|privacy|privacidad/.test(t)) return 'pie';
    if (e.querySelector('form input, form textarea')) return 'formulario';
    if (/€|\$|\/mes|\/month|precio|pricing|plan/.test(t) && tarjetas >= 2) return 'precios';
    if (/faq|preguntas|frequently/.test(t)) return 'faq';
    if (/opini|testimon|review|rese[nñ]a|clientes dicen/.test(t)) return 'opiniones';
    if (areaImg > 0.55) return 'galeria-o-foto';
    if (tarjetas >= 3) return 'tarjetas-' + Math.min(tarjetas, 6);
    if (e.querySelectorAll('h2, h3').length >= 1 && areaImg > 0.2) return 'texto+imagen';
    return 'texto';
  };
  const secciones = bloques.slice(0, 16).map((e, i) => i === 0 && e.getBoundingClientRect().top < vh ? 'hero' : tipo(e));
  // hero
  const h0 = bloques[0] ? bloques[0].getBoundingClientRect() : { height: 0 };
  const media0 = bloques[0] ? [...bloques[0].querySelectorAll('img, video, canvas, picture')].filter(vis) : [];
  const areaMedia0 = media0.reduce((a, i) => { const b = i.getBoundingClientRect(); return a + b.width * b.height; }, 0) / Math.max(1, vw * Math.min(h0.height, vh));
  const h1 = [...document.querySelectorAll('h1')].find(vis);
  const h1r = h1 ? h1.getBoundingClientRect() : null;
  const hero = areaMedia0 > 0.6 ? 'foto/video a sangre' : (areaMedia0 > 0.2 && h1r && h1r.width < vw * 0.6 ? 'partido (texto + imagen)' :
               (h1 && px(cs(h1).fontSize) > vw * 0.07 ? 'tipografico gigante' : 'tipografico'));
  // tipografia
  const tam = (sel) => { const v = [...document.querySelectorAll(sel)].filter(vis).slice(0, 12).map(e => px(cs(e).fontSize)).sort((a, b) => a - b); return v.length ? v[v.length >> 1] : 0; };
  const fam = (e) => e ? cs(e).fontFamily.split(',')[0].replace(/["']/g, '').trim() : '';
  const generica = (e) => { if (!e) return ''; const f = cs(e).fontFamily.toLowerCase(); return /serif/.test(f) && !/sans-serif/.test(f) ? 'serif' : /mono/.test(f) ? 'mono' : 'sans'; };
  const p = [...document.querySelectorAll('p')].find(e => vis(e) && (e.innerText || '').length > 40);
  // color por superficie
  const rgb = (c) => { const n = (c.match(/[\d.]+/g) || []).map(Number); return c.startsWith('color(') ? n.slice(0, 3).map(x => x * 255).concat(n.slice(3)) : n; };
  const lum = (c) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const area = {};
  for (const e of [document.body, ...document.querySelectorAll('body *')].slice(0, 2500)) {
    const c = cs(e).backgroundColor, n = rgb(c); if (n.length < 3 || (n.length > 3 && n[3] < 0.5)) continue;
    const r = e.getBoundingClientRect(); const a = Math.min(r.width, vw) * Math.min(r.height, H); if (a < 2000) continue;
    const k = n.slice(0, 3).map(Math.round).join(','); area[k] = (area[k] || 0) + a;
  }
  const fondos = Object.entries(area).sort((a, b) => b[1] - a[1]);
  const total = fondos.reduce((a, x) => a + x[1], 0) || 1;
  const botones = [...document.querySelectorAll('a, button')].filter(e => vis(e) && px(cs(e).paddingLeft) >= 10 && rgb(cs(e).backgroundColor).length >= 3 && (rgb(cs(e).backgroundColor)[3] ?? 1) > 0.5).slice(0, 20);
  const acento = Object.entries(botones.reduce((m, b) => { const k = rgb(cs(b).backgroundColor).slice(0, 3).map(Math.round).join(','); m[k] = (m[k] || 0) + 1; return m; }, {})).sort((a, b) => b[1] - a[1])[0];
  const fondoMain = fondos[0] ? fondos[0][0].split(',').map(Number) : [255, 255, 255];
  // densidad y formas
  const pads = bloques.map(e => px(cs(e).paddingTop) + px(cs(e).paddingBottom)).filter(x => x > 0).sort((a, b) => a - b);
  const anchos = [...document.querySelectorAll('body *')].slice(0, 1500).filter(e => vis(e) && (e.innerText || '').length > 80).map(e => e.getBoundingClientRect().width).filter(w => w < vw - 20).sort((a, b) => a - b);
  const radios = [...botones, ...document.querySelectorAll('[class*=card], article')].filter(vis).slice(0, 30).map(e => px(cs(e).borderTopLeftRadius)).sort((a, b) => a - b);
  const sombras = [...document.querySelectorAll('body *')].slice(0, 1500).filter(e => cs(e).boxShadow !== 'none').length;
  const imgs = [...document.images].filter(vis); const areaImgs = imgs.reduce((a, i) => { const b = i.getBoundingClientRect(); return a + b.width * b.height; }, 0) / Math.max(1, vw * H);
  const mitad = (v) => v.length ? v[v.length >> 1] : 0;
  const vars = {}; for (const sh of document.styleSheets) { try { for (const ru of sh.cssRules) if (ru.selectorText === ':root')
    for (const pr of ru.style) if (pr.startsWith('--') && Object.keys(vars).length < 24) vars[pr] = ru.style.getPropertyValue(pr).trim(); } catch (x) {} }
  return {
    secciones, n_secciones: secciones.length, alto_pantallas: +(H / vh).toFixed(1), hero,
    tipo: { titular_px: tam('h1'), h2_px: tam('h2'), texto_px: tam('p'), titular_familia: generica(h1), texto_familia: generica(p),
            titular_fuente: fam(h1), texto_fuente: fam(p), ratio_titular_texto: tam('p') ? +(tam('h1') / tam('p')).toFixed(1) : null },
    color: { tema: lum(fondoMain) > 0.5 ? 'claro' : 'oscuro', fondos: fondos.slice(0, 4).map(([k, a]) => [k, Math.round(100 * a / total)]),
             acento: acento ? acento[0] : null, colores_de_fondo: fondos.filter(f => f[1] / total > 0.05).length },
    densidad: { aire_seccion_px: mitad(pads), ancho_texto_px: Math.round(mitad(anchos)) },
    formas: { radio_px: mitad(radios), con_sombras: sombras > 8 },
    fotos: { porcentaje_pagina: Math.round(100 * areaImgs), n_imagenes: imgs.length },
    variables_css: vars,
    movimiento: { animaciones_css: [...document.querySelectorAll('body *')].slice(0, 1500).filter(e => cs(e).animationName !== 'none' || cs(e).transitionDuration !== '0s').length }
  };
}"""

JS_COOKIES = r"""() => {
  const t = /^(aceptar|accept|acepto|agree|ok|entendido|rechazar|reject|decline|solo necesarias|only necessary|close|cerrar)/i;
  for (const b of [...document.querySelectorAll('button, a[role=button], [class*=cookie] button, [id*=cookie] button')].slice(0, 200)) {
    if (t.test((b.innerText || b.getAttribute('aria-label') || '').trim())) { b.click(); return true; } }
  return false; }"""


def webs_del_sector(sector: str, maximo: int) -> list[str]:
    sitios = json.loads(SITES.read_text(encoding="utf-8"))
    propias = [s for s in sitios if s.get("kind") == sector and s.get("url")]
    propias.sort(key=lambda s: -float(s.get("score") or 0))
    return [s["url"] for s in propias[:maximo]]


def permitido(url: str) -> bool:
    partes = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(f"{partes.scheme}://{partes.netloc}/robots.txt", headers={"User-Agent": AGENTE})
        with urllib.request.urlopen(req, timeout=8) as r:
            rp.parse(r.read().decode("utf-8", "ignore").splitlines())
    except Exception:
        return True  # sin robots.txt legible: se permite (norma habitual)
    return rp.can_fetch(AGENTE, url)


def vision(png: Path) -> tuple[str | None, str | None]:
    """(descripcion, error). Un fallo es un fallo: nunca se guarda el error como si fuera el analisis."""
    try:
        modelo = json.loads((NOVA / "antigravity" / "scripts" / "nova_modelos.json").read_text(encoding="utf-8")).get("vl", "blaifa/InternVL3_5:8b")
    except (OSError, ValueError):
        modelo = "blaifa/InternVL3_5:8b"
    cuerpo = {"model": modelo, "stream": False, "keep_alive": "10m", "options": {"temperature": 0.2, "num_predict": 220},
              "messages": [{"role": "user", "images": [base64.b64encode(png.read_bytes()).decode()],
                            "content": "Describe en 3 frases cortas, en espanol, SOLO la composicion de esta primera pantalla de una web: "
                                       "1) como es la portada (texto, imagen, reparto), 2) estilo (claro/oscuro, sobrio/llamativo, "
                                       "tipografia grande o no), 3) un recurso de diseno que destaque. No leas ni copies textos."}]}
    try:
        req = urllib.request.Request(OLLAMA, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            texto = (json.loads(r.read()).get("message") or {}).get("content", "").strip()
        return (texto or None), (None if texto else "respuesta vacia")
    except Exception as ex:
        return None, f"{type(ex).__name__}: {ex}"


def medir(url: str, carpeta: Path, con_vision: bool, navegador) -> dict:
    dominio = urlparse(url).netloc.replace("www.", "")
    destino = carpeta / re.sub(r"[^\w.-]", "_", dominio)
    destino.mkdir(parents=True, exist_ok=True)
    fila = {"url": url, "dominio": dominio}
    if not permitido(url):
        return {**fila, "error": "robots.txt no lo permite"}
    try:
        ctx = navegador.new_context(viewport={"width": 1280, "height": 800}, user_agent=None, locale="es-ES")
        pg = ctx.new_page()
        pg.goto(url, wait_until="load", timeout=45000)
        pg.wait_for_timeout(2500)
        if pg.evaluate(JS_COOKIES):
            pg.wait_for_timeout(800)
        pg.evaluate("async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += 700) { scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } scrollTo(0, 0); }")
        pg.wait_for_timeout(800)
        fila["medidas"] = pg.evaluate(JS_MEDIDAS)
        pg.screenshot(path=str(destino / "pc.png"))
        ctx.close()
        m = navegador.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2, locale="es-ES")
        pm = m.new_page()
        pm.goto(url, wait_until="load", timeout=45000)
        pm.wait_for_timeout(2000)
        pm.evaluate(JS_COOKIES)
        pm.wait_for_timeout(500)
        pm.screenshot(path=str(destino / "movil.png"))
        m.close()
    except Exception as ex:
        return {**fila, "error": f"{type(ex).__name__}: {str(ex)[:160]}"}
    if con_vision:
        fila["vision"], err = vision(destino / "pc.png")
        if err:
            fila["vision_error"] = err
    (destino / "medidas.json").write_text(json.dumps(fila, ensure_ascii=False, indent=2), encoding="utf-8")
    return fila


def resumir(filas: list[dict], etiqueta: str) -> tuple[dict, str]:
    ok = [f for f in filas if f.get("medidas")]
    if not ok:
        return {"webs_ok": 0, "fallos": [f"{f['dominio']}: {f.get('error')}" for f in filas]}, "RADAR: ninguna web se pudo medir."
    M = [f["medidas"] for f in ok]
    med = lambda v: round(statistics.median(v), 1) if v else None  # noqa: E731
    cuenta = Counter(s for m in M for s in dict.fromkeys(m["secciones"][1:]))
    orden = Counter(" > ".join(m["secciones"][:6]) for m in M).most_common(1)[0][0]
    temas = Counter(m["color"]["tema"] for m in M)
    heroes = Counter(m["hero"] for m in M)
    familias = Counter(f"{m['tipo']['titular_familia']} + {m['tipo']['texto_familia']}" for m in M)
    res = {
        "etiqueta": etiqueta, "webs_ok": len(ok), "fallos": [f"{f['dominio']}: {f.get('error')}" for f in filas if not f.get("medidas")],
        "secciones_mas_usadas": cuenta.most_common(8), "orden_tipico": orden,
        "n_secciones_mediana": med([m["n_secciones"] for m in M]), "alto_en_pantallas": med([m["alto_pantallas"] for m in M]),
        "hero": heroes.most_common(3), "tema": temas.most_common(), "familias": familias.most_common(3),
        "ratio_titular_texto": med([m["tipo"]["ratio_titular_texto"] for m in M if m["tipo"]["ratio_titular_texto"]]),
        "texto_px": med([m["tipo"]["texto_px"] for m in M if m["tipo"]["texto_px"]]),
        "aire_seccion_px": med([m["densidad"]["aire_seccion_px"] for m in M if m["densidad"]["aire_seccion_px"]]),
        "ancho_texto_px": med([m["densidad"]["ancho_texto_px"] for m in M if m["densidad"]["ancho_texto_px"]]),
        "radio_px": med([m["formas"]["radio_px"] for m in M]), "con_sombras": sum(m["formas"]["con_sombras"] for m in M),
        "colores_de_fondo": med([m["color"]["colores_de_fondo"] for m in M]),
        "fotos_porcentaje": med([m["fotos"]["porcentaje_pagina"] for m in M]),
        "vision": [f"{f['dominio']}: {f['vision']}" for f in ok if f.get("vision")],
    }
    lineas = [
        f"RADAR {etiqueta}: {len(ok)} webs medidas" + (f" ({len(res['fallos'])} fallaron)" if res["fallos"] else ""),
        f"- Secciones que mas se repiten: {', '.join(f'{s} ({n}/{len(ok)})' for s, n in res['secciones_mas_usadas'])}",
        *[f"- Orden en {f['dominio']}: {' > '.join(f['medidas']['secciones'][:8]) or '(no se pudo leer)'}" for f in ok[:4]],
        f"- Largo: ~{res['n_secciones_mediana']} secciones, ~{res['alto_en_pantallas']} pantallas de alto",
        f"- Hero: {', '.join(f'{h} ({n})' for h, n in res['hero'])}",
        f"- Tema: {', '.join(f'{t} ({n})' for t, n in res['tema'])}; colores de fondo distintos por pagina: ~{res['colores_de_fondo']}",
        f"- Tipografia: {', '.join(f'{x} ({n})' for x, n in res['familias'])}; titular = {res['ratio_titular_texto']}x el texto; texto ~{res['texto_px']}px",
        f"- Densidad: ~{res['aire_seccion_px']}px de aire vertical por seccion; lineas de texto de ~{res['ancho_texto_px']}px",
        f"- Formas: radio ~{res['radio_px']}px; sombras en {res['con_sombras']}/{len(ok)} webs",
        f"- Fotos: ~{res['fotos_porcentaje']}% de la pagina es imagen",
        "USO (Nova): toma ESTRUCTURA, ritmo y densidad. El ASPECTO lo pone la direccion sorteada (draw.mjs) y mandan las skills "
        "(contraste, anti-cliches). Nunca copies textos, marcas ni la combinacion de colores y fuentes de una web concreta.",
    ]
    sin_citas = [re.sub(r"[\"“«][^\"”»]{3,}[\"”»]", "(texto)", v) for v in res["vision"][:3]]  # nada de textos ajenos
    lineas += [f"- Vista: {re.sub(r'\s+', ' ', v)[:220]}" for v in sin_citas]
    return res, "\n".join(lineas)


def main() -> int:
    ap = argparse.ArgumentParser(description="Radar de webs de referencia (local, 0 tokens)")
    ap.add_argument("--sector", default="", help="Sector de draw.mjs: health, restaurant, hospitality, real-estate, saas, agency...")
    ap.add_argument("--urls", default="", help="URLs separadas por comas (p. ej. las que de Alexander)")
    ap.add_argument("--lista", default="", help="Archivo con una URL por linea")
    ap.add_argument("--max", type=int, default=4)
    ap.add_argument("--sin-vision", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    urls = [u.strip() for u in a.urls.split(",") if u.strip()]
    if a.lista:
        urls += [u.strip() for u in Path(a.lista).read_text(encoding="utf-8").splitlines() if u.strip().startswith("http")]
    if a.sector:
        urls += webs_del_sector(a.sector, a.max)
    urls = list(dict.fromkeys(urls))[: max(a.max, len(a.urls.split(",")) if a.urls else 0)]
    if not urls:
        print("[RADAR] Sin webs: usa --sector (de draw.mjs), --urls o --lista.")
        return 2
    etiqueta = a.sector or "lista"
    carpeta = Path(a.out).resolve() if a.out else DATOS / etiqueta
    carpeta.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    filas = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        for i, url in enumerate(urls):
            if i:
                time.sleep(PAUSA)
            t0 = time.time()
            fila = medir(url, carpeta, not a.sin_vision, nav)
            filas.append(fila)
            print(f"[RADAR] {fila['dominio']}: {'FALLO ' + fila['error'] if fila.get('error') else 'ok'} ({round(time.time() - t0)} s)"
                  + (f" · vision: {fila['vision_error']}" if fila.get("vision_error") else ""), flush=True)
        nav.close()
    res, texto = resumir(filas, etiqueta)
    (carpeta / "resumen.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / "resumen.txt").write_text(texto, encoding="utf-8")
    print("\n" + texto + f"\n\n[RADAR] Resumen para Nova: {carpeta / 'resumen.txt'}")
    return 0 if res.get("webs_ok") else 1


if __name__ == "__main__":
    sys.exit(main())
