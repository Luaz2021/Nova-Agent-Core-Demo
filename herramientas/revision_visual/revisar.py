r"""
REVISION VISUAL de Nova (23/11/2026, Claude). Regla web-001 de memory\aprendido.jsonl, el error que mas se repitio (x5):
"dijo listo midiendo numeros o porque compila, sin mirar la imagen" (la ultima: un marco de movil como una salchicha).

Mira la web COMO LA VE EL USUARIO: capturas sin cache en 1366x768, 1920x1080 y movil 390x844, comprobaciones
automaticas (scroll horizontal, cosas que se salen de la pantalla, imagenes rotas, errores de consola) e InternVL
revisando cada captura con ojos de persona. Deja informe.md + capturas y devuelve OK / REVISAR.

Uso (Nova):
  <PYTHON> "<NOVA_HOME>/antigravity/herramientas/revision_visual/revisar.py" "<carpeta o .html o URL>"
  opciones: --paginas a.html,b.html (solo esas) · --todas (todas las .html de la carpeta) · --minutos 120 (por defecto:
  las .html cambiadas en ese tiempo; si cambio un .css/.js, todas) · --marco .phone-frame (mide que ese elemento tenga
  proporcion de movil real y quepa en pantalla) · --sin-vista (sin InternVL, solo comprobaciones)
Salida: antigravity\temporal\revision_visual\<fecha>_<nombre>\ (informe.md + capturas\). En tu respuesta al usuario
pon el veredicto, los problemas y la ruta del informe.
"""

import argparse
import base64
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

NOVA_HOME = Path.home() / ".gemini"
SALIDA = NOVA_HOME / "antigravity" / "temporal" / "revision_visual"
OLLAMA = "http://127.0.0.1:11434"
TAMANOS = (("pc_1366x768", 1366, 768, False), ("pc_1920x1080", 1920, 1080, False), ("movil_390x844", 390, 844, True))
MAX_PAGINAS = 8
PROMPT = (
    "Eres un revisor humano exigente. Esta captura es una web o app vista en {tam}. Mira SOLO lo que se ve. "
    "Primera palabra: OK o FALLO. Despues, si hay fallos, una lista corta y concreta en espanol: cosas cortadas, "
    "solapadas o que se salen, proporciones raras (por ejemplo un movil dibujado demasiado alto o estrecho, o "
    "achatado), textos ilegibles o con poco contraste, huecos enormes, elementos descolocados o vacios. "
    "No inventes nada que no se vea. Maximo 70 palabras.")

MEDIR = r"""(marco) => {
  const W = innerWidth, H = innerHeight, d = document.documentElement;
  const fuera = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (!r.width || !r.height || cs.position === 'fixed' || cs.visibility === 'hidden') continue;
    if (r.right > W + 4 || r.left < -4) { fuera.push((el.tagName + '.' + (el.className || '')).slice(0, 60)); }
    if (fuera.length >= 5) break;
  }
  const rotas = [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src.split('/').pop()).slice(0, 5);
  let m = null;
  if (marco) { const e = document.querySelector(marco);
    if (e) { const r = e.getBoundingClientRect();
      m = {ancho: Math.round(r.width), alto: Math.round(r.height), proporcion: +(r.height / r.width).toFixed(2),
           cabe: r.bottom <= H + 2 && r.top >= -2}; } }
  return {scroll_horizontal: d.scrollWidth > W + 2, fuera, rotas, marco: m};
}"""


def ollama_vl(img: Path, tam: str) -> str:
    try:
        f = NOVA_HOME / "antigravity" / "scripts" / "nova_modelos.json"
        modelo = json.loads(f.read_text(encoding="utf-8")).get("vl") or "blaifa/InternVL3_5:8b"
    except Exception:
        modelo = "blaifa/InternVL3_5:8b"
    cuerpo = {"model": modelo, "prompt": PROMPT.format(tam=tam), "stream": False, "keep_alive": "2m",
              "images": [base64.b64encode(img.read_bytes()).decode()], "options": {"temperature": 0.1, "num_ctx": 4096}}
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=json.dumps(cuerpo).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return (json.loads(r.read().decode()).get("response") or "").strip()


def descargar_vl() -> None:
    try:
        f = NOVA_HOME / "antigravity" / "scripts" / "nova_modelos.json"
        modelo = json.loads(f.read_text(encoding="utf-8")).get("vl") or "blaifa/InternVL3_5:8b"
        req = urllib.request.Request(f"{OLLAMA}/api/generate", data=json.dumps({"model": modelo, "keep_alive": 0}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        pass


def servidor(raiz: Path) -> str:
    """Sirve la carpeta por http en un puerto libre y SIN cache (con file:// fallan fetch, modulos y localStorage)."""
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class SinCache(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *args):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(SinCache, directory=str(raiz)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}/"


def elegir_paginas(entrada: str, a) -> list[str]:
    if re.match(r"https?://", entrada):
        return [entrada]
    p = Path(entrada)
    if p.is_file():
        return [servidor(p.parent) + p.name]
    htmls = sorted(p.glob("*.html"))
    if a.paginas:
        quiero = {x.strip().lower() for x in a.paginas.split(",")}
        elegidas = [h for h in htmls if h.name.lower() in quiero]
    elif a.todas:
        elegidas = htmls
    else:
        limite = time.time() - a.minutos * 60
        recientes = [f for f in p.rglob("*") if f.suffix.lower() in (".css", ".js") and f.stat().st_mtime > limite
                     and "node_modules" not in f.parts]
        elegidas = htmls if recientes else [h for h in htmls if h.stat().st_mtime > limite]
        if not elegidas:
            elegidas = htmls[:1]
    if len(elegidas) > MAX_PAGINAS:
        print(f"(hay {len(elegidas)} paginas: reviso {MAX_PAGINAS}; usa --paginas para elegir otras)")
        elegidas = elegidas[:MAX_PAGINAS]
    base = servidor(p.resolve())
    return [base + h.name for h in elegidas]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Revision visual como la ve el usuario")
    ap.add_argument("entrada")
    ap.add_argument("--paginas", default="")
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--minutos", type=int, default=120)
    ap.add_argument("--marco", default="")
    ap.add_argument("--sin-vista", action="store_true")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright

    paginas = elegir_paginas(a.entrada, a)
    nombre = re.sub(r"[^\w-]+", "_", Path(a.entrada.rstrip("/\\")).name or "web")[:40]
    out = SALIDA / f"{datetime.now():%Y%m%d_%H%M}_{nombre}"
    (out / "capturas").mkdir(parents=True, exist_ok=True)
    filas, problemas = [], 0
    t0 = time.time()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for url in paginas:
            pagina = url.split("/")[-1].split("?")[0] or "index"
            for tam, w, h, movil in TAMANOS:
                ctx = nav.new_context(viewport={"width": w, "height": h}, is_mobile=movil, has_touch=movil,
                                      device_scale_factor=1)  # contexto nuevo = sin cache
                pg = ctx.new_page()
                errores = []
                pg.on("pageerror", lambda e, errores=errores: errores.append(str(e)[:120]))
                pg.on("console", lambda m, errores=errores: m.type == "error" and errores.append(m.text[:120]))
                try:
                    pg.goto(url, wait_until="networkidle", timeout=20000)
                except Exception as e:
                    errores.append(f"no carga: {str(e)[:100]}")
                pg.wait_for_timeout(600)
                med = pg.evaluate(MEDIR, a.marco or None)
                img = out / "capturas" / f"{Path(pagina).stem}_{tam}.png"
                pg.screenshot(path=str(img))
                ctx.close()
                fallos = []
                if med["scroll_horizontal"]:
                    fallos.append("scroll horizontal (algo se sale de lado)")
                if med["fuera"]:
                    fallos.append("se salen de la pantalla: " + ", ".join(med["fuera"][:3]))
                if med["rotas"]:
                    fallos.append("imagenes rotas: " + ", ".join(med["rotas"]))
                if errores:
                    fallos.append("errores de consola: " + " | ".join(errores[:2]))
                m = med.get("marco")
                if a.marco and not movil:
                    if not m:
                        fallos.append(f"no encuentro {a.marco}")
                    else:
                        if not 1.9 <= m["proporcion"] <= 2.3:
                            fallos.append(f"{a.marco} con proporcion {m['proporcion']} (movil real ~2,0-2,2)")
                        if not m["cabe"]:
                            fallos.append(f"{a.marco} no cabe en la pantalla ({m['alto']}px de alto)")
                vista = ""
                if not a.sin_vista:
                    try:
                        vista = ollama_vl(img, f"{w}x{h}" + (" (movil)" if movil else " (ordenador)"))
                    except Exception as e:
                        vista = f"(InternVL no respondio: {str(e)[:60]})"
                    if re.match(r"\W*FALLO", vista, re.I):
                        fallos.append("InternVL: " + re.sub(r"^\W*FALLO\W*", "", vista, flags=re.I)[:200])
                problemas += bool(fallos)
                filas.append((pagina, tam, img.name, fallos, vista, m))
                print(f"{'REVISAR' if fallos else 'OK     '} {pagina:34} {tam:14} {'; '.join(fallos)[:150]}")
        nav.close()
    if not a.sin_vista:
        descargar_vl()
    veredicto = "OK" if not problemas else f"REVISAR ({problemas} capturas con problemas)"
    with open(out / "informe.md", "w", encoding="utf-8") as f:
        f.write(f"# Revision visual: {veredicto}\n\n> {datetime.now():%d/%m/%Y %H:%M} | {len(paginas)} paginas x 3 tamanos "
                f"| sin cache | {round(time.time() - t0)} s\n\n")
        for pagina, tam, img, fallos, vista, m in filas:
            f.write(f"## {pagina} · {tam} · {'REVISAR' if fallos else 'OK'}\n![](capturas/{img})\n\n")
            for x in fallos:
                f.write(f"- {x}\n")
            if m:
                f.write(f"- marco: {m['ancho']}x{m['alto']} px, proporcion {m['proporcion']}, cabe: {m['cabe']}\n")
            if vista and not fallos:
                f.write(f"- InternVL: {vista[:300]}\n")
            f.write("\n")
    print(f"\nVEREDICTO: {veredicto}\nInforme: {out / 'informe.md'}")
    print(json.dumps({"revision_visual": veredicto, "informe": str(out / "informe.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
