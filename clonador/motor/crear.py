import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
PASO 2 · CREAR la base del clon (sin IA)  ·  cadena oficial: analizar -> crear -> verificar

  python crear.py                 (usa el último análisis)
  python crear.py <carpeta>       (workspace/<web>)

1. Clon fiel: copia la estructura y los estilos reales de cada elemento (PC + móvil), con las MISMAS secciones del análisis.
2. Lo pasa a Tailwind (clases arbitrarias, md: para escritorio).
3. Marca cada imagen, vídeo e iframe (data-medio) para cambiarlos al final por medios de libre uso.
4. Planos medidos de cada sección (auto_planos.py -> claude/): los usa verificar.py cuando Qwen repara.
Salida en workspace/<web>/construccion/:  index.html (la base que revisa 3_VERIFICAR) y base/ (clon fiel y piezas).
Las fuentes de la marca se cambian por su equivalente de Google Fonts.
"""
import json
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BASE))
from capturar import capturar_web  # noqa: E402
from convertir import convertir  # noqa: E402
import puente_interactividad  # noqa: E402


def marcar_medios(html):
    """data-medio en cada <img>/<video>/<iframe> (con su tamaño si lo trae) para vestirlos al final con medios libres."""

    def img(m):
        tag = m.group(0)
        if "data-medio=" in tag:
            return tag
        w = re.search(r'\bwidth="(\d+)', tag)
        h = re.search(r'\bheight="(\d+)', tag)
        w, h = (int(w.group(1)) if w else 800), (int(h.group(1)) if h else 600)
        tipo = "logo" if w <= 160 and h <= 90 else "foto"
        return (
            tag[:-1].rstrip("/ ") + f' data-medio="{tipo}" data-w="{w}" data-h="{h}">'
        )

    html = re.sub(r"<img\b[^>]*>", img, html, flags=re.IGNORECASE)
    html = re.sub(
        r"<video\b(?![^>]*data-medio)",
        '<video data-medio="video"',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r"<iframe\b(?![^>]*data-medio)([^>]*)>",
        lambda m: (
            f'<iframe data-medio="{"mapa" if "map" in m.group(1).lower() else "youtube"}"{m.group(1)}>'
        ),
        html,
        flags=re.IGNORECASE,
    )
    return html


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    carpeta = (
        Path(args[0])
        if args
        else Path(
            ((BASE.parent / "workspace") / "ultimo_analisis.txt")
            .read_text(encoding="utf-8")
            .strip()
        )
    )
    datos = json.loads((carpeta / "datos.json").read_text(encoding="utf-8"))
    spec = json.loads(
        (Path(datos["carpeta_referencia"]) / "spec.json").read_text(encoding="utf-8")
    )
    out = carpeta / "construccion"
    base = out / "base"
    base.mkdir(parents=True, exist_ok=True)
    print(f"CREAR - {datos['url']} · {len(spec['secciones'])} secciones")
    print("  [1/3] clon fiel (estructura y estilos reales, PC + móvil)...")
    fiel = capturar_web(
        datos["url"],
        base,
        fuentes="google",
        imagenes="originales",
        spec=spec,
        ref_dir=datos["carpeta_referencia"],
    )
    print("  [2/3] pasando a Tailwind...")
    tw = base / "clon_tailwind.html"
    convertir(fiel, tw)
    print("  [3/3] marcando imágenes y vídeos para los medios libres del final...")
    html = marcar_medios(tw.read_text(encoding="utf-8"))
    html = puente_interactividad.inyectar(
        html, carpeta
    )  # pestañas, colores, modales, hover (clon-interacciones.js)
    secs = sorted(set(int(n) for n in re.findall(r'data-clon-sec="(\d+)"', html)))
    if (out / "index.html").exists():
        shutil.copy(out / "index.html", out / "index_anterior.html")
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "index_base.html").write_text(
        html, encoding="utf-8"
    )  # la base sin tocar, por si hay que volver atrás
    print(
        f"\nListo: {out / 'index.html'}  ({len(html) // 1024} KB, secciones marcadas: {len(secs)} de {len(spec['secciones'])})"
    )
    faltan = [s["n"] for s in spec["secciones"] if s["n"] not in secs]
    if faltan:
        print(f"  ojo: secciones del análisis que no aparecen en el clon: {faltan}")
    try:  # planos frescos de ESTA web (los escritos a mano en claude/ se respetan)
        import auto_planos

        auto_planos.generar_planos(carpeta)
    except Exception as ex:
        print(f"  (aviso planos: {ex})")
    n = puente_interactividad.contrato(
        carpeta
    )  # micro-contrato data-* al final de los sec_N.md
    if n:
        print(f"  contrato de interacciones en {n} planos (sec_N.md)")
    # datos REALES para la versión React (react/datos_web.ts): los componentes los importan y nadie los escribe a mano
    try:
        sys.path.insert(0, str(BASE.parent / "herramientas"))
        import exportar_react

        exportar_react.exportar(carpeta)
    except SystemExit as ex:
        print(f"  (aviso React: {ex})")
    except Exception as ex:
        print(f"  (aviso React: {ex})")
    # el clon convertido en componentes React (react/clon/): la maqueta del clon, sección por sección
    try:
        import exportar_jsx

        exportar_jsx.exportar(carpeta)
    except Exception as ex:
        print(f"  (aviso JSX: {ex})")
    print("Siguiente paso: 3_VERIFICAR")


if __name__ == "__main__":
    main()
