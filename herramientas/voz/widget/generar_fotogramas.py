"""
Genera los fotogramas del monito de Nova para el widget flotante (17/11/2026, Claude).
Usa EL MISMO dibujo y animaciones de ..\\mascota.js: lo abre en un Chromium invisible, congela las animaciones y
fotografia cada cara cada 100 ms con fondo transparente -> widget\\fotogramas\\<estado>_<nn>.png
Vuelve a ejecutarlo si cambias mascota.js:   python generar_fotogramas.py
"""
import os
import shutil

from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
MASCOTA_JS = os.path.join(AQUI, "..", "mascota.js")
SALIDA = os.path.join(AQUI, "fotogramas")
ESTADOS = ["espera", "mirando", "escuchando", "pensando", "hablando", "error", "pausa"]
DURACION_MS = 6400   # 2 vueltas exactas de "flotar" (3,2 s) y un parpadeo: el bucle no da saltos
PASO_MS = 100
ESCALA = 2           # fotogramas a doble resolucion (el widget los ajusta a la escala de tu pantalla)

PAGINA = """<!doctype html><html><head><style>html,body{margin:0;background:transparent}</style></head>
<body><div style="position:fixed;left:0;top:400px;width:150px;height:30px">Settings</div></body></html>"""


def main():
    shutil.rmtree(SALIDA, ignore_errors=True)
    os.makedirs(SALIDA)
    with open(MASCOTA_JS, encoding="utf-8") as f:
        js = f.read()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page(viewport={"width": 300, "height": 500}, device_scale_factor=ESCALA)
        pag.set_content(PAGINA)
        pag.evaluate(js)
        # el texto "Settings" solo sirve para que mascota.js se coloque; luego se esconde
        pag.evaluate("document.querySelector('body > div').style.color = 'transparent'")
        pag.evaluate("window.setTimeout = () => 0")  # que "error" no vuelva solo a "espera" a mitad de las fotos
        host = pag.locator("#nova-mascota")
        total = 0
        for estado in ESTADOS:
            pag.evaluate(f"window.__novaMascota.set('{estado}')")
            pag.wait_for_timeout(700)  # que terminen las transiciones (giro de cabeza, bocadillo)
            for i, t in enumerate(range(0, DURACION_MS, PASO_MS)):
                pag.evaluate(f"document.getAnimations().forEach(a => {{ a.pause(); a.currentTime = {t}; }})")
                host.screenshot(path=os.path.join(SALIDA, f"{estado}_{i:02d}.png"), omit_background=True)
                total += 1
            pag.evaluate("document.getAnimations().forEach(a => a.play())")
        nav.close()
    print(f"{total} fotogramas en {SALIDA}")
    empaquetar()


def empaquetar(carpeta: str = SALIDA, columnas: int = 8) -> None:
    """26/11 (Claude, auditoria de Carbon): 448 PNG sueltos -> 1 hoja WebP SIN perdida por estado + hojas.json.
    Mismos pixeles (se comprueba antes de borrar los PNG); Drive sincroniza 8 archivos en vez de 448."""
    import glob
    import json
    import re
    from PIL import Image

    grupos: dict[str, list[str]] = {}
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.png"))):
        m = re.match(r"(.+)_(\d+)\.png$", os.path.basename(ruta))
        if m:
            grupos.setdefault(m.group(1), []).append(ruta)
    if not grupos:
        print("No hay PNG que empaquetar.")
        return
    meta = {}
    for estado, rutas in grupos.items():
        imgs = [Image.open(r).convert("RGBA") for r in rutas]
        w, h = imgs[0].size
        filas = -(-len(imgs) // columnas)
        hoja = Image.new("RGBA", (w * columnas, h * filas), (0, 0, 0, 0))
        for i, im in enumerate(imgs):
            hoja.paste(im, ((i % columnas) * w, (i // columnas) * h))
        destino = os.path.join(carpeta, f"{estado}.webp")
        hoja.save(destino, "WEBP", lossless=True, quality=100, method=6, exact=True)
        with Image.open(destino) as comp:  # comprobar pixel a pixel antes de borrar nada
            comp = comp.convert("RGBA")
            for i, im in enumerate(imgs):
                x, y = (i % columnas) * w, (i // columnas) * h
                if comp.crop((x, y, x + w, y + h)).tobytes() != im.tobytes():
                    raise SystemExit(f"{estado}: el fotograma {i} no sale identico; no se borra nada")
        meta[estado] = {"hoja": f"{estado}.webp", "n": len(imgs), "w": w, "h": h, "columnas": columnas}
        for im in imgs:
            im.close()
    with open(os.path.join(carpeta, "hojas.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    for rutas in grupos.values():
        for r in rutas:
            os.remove(r)
    print(f"{sum(m['n'] for m in meta.values())} fotogramas -> {len(meta)} hojas WebP (identicas) en {carpeta}")


if __name__ == "__main__":
    import sys
    empaquetar() if "--empaquetar" in sys.argv else main()
