import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
PROBAR UNA GUÍA DE VERSIÓN: ¿Qwen comete menos errores de versión con la guía delante?

  python probar_guia.py tailwind4

Le pide a Qwen las mismas tareas dos veces (sin guía y con guías/<nombre>.md en el prompt) y cuenta
con reglas automáticas cuántas cosas "antiguas" escribe. Resultado: guias/resultado_<nombre>.md
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
from construir import MODELO  # noqa: E402  (qwen3.5:9b, solo código; ver nova_modelos.json)

PRUEBAS = {
    "tailwind4": {
        "tareas": [
            "Página HTML completa con Tailwind CSS 4 cargado por CDN en el navegador, con dos colores propios de marca (#F26B21 'marca' y #1D1D1F 'tinta') y la fuente 'Inter' configurados para usarlos como clases.",
            "Tarjeta de producto con Tailwind CSS 4: imagen arriba con esquinas pequeñas redondeadas, sombra suave, borde gris claro, título, precio y botón con fondo negro al 80 % de opacidad.",
            "Hero con Tailwind CSS 4: fondo con degradado de izquierda a derecha de violeta a cian, título grande y un botón que al pasar el ratón muestra un anillo (ring) de 3 px.",
            "Rejilla de 3 tarjetas con Tailwind CSS 4 que se adapta al ancho del CONTENEDOR (no de la pantalla): 1 columna si el contenedor es estrecho, 3 si es ancho.",
            "Barra de navegación con Tailwind CSS 4: fija arriba, fondo blanco translúcido con desenfoque, un input de búsqueda sin contorno al enfocarlo y un texto que se corta con puntos suspensivos.",
            "Modal con Tailwind CSS 4: fondo oscuro semitransparente encima de la página, caja centrada con esquinas redondeadas, y una clase marcada como !important para forzar el z-index.",
        ],
        # (regla, explicación) -> cada coincidencia cuenta como un error de versión antigua
        "malas": [
            (r"tailwind\.config\s*=|tailwind\.config\.js|module\.exports\s*=\s*\{", "config de v3 (tailwind.config) en vez de @theme"),
            (r"cdn\.tailwindcss\.com", "CDN de Tailwind 3 (cdn.tailwindcss.com)"),
            (r"tailwindcss@[123]\b|tailwind(\.min)?\.css", "Tailwind 1/2/3 por hoja CSS precompilada"),
            (r"@tailwind\s+(base|components|utilities)", "@tailwind base/components/utilities (v3)"),
            (r"\b(bg|text|border|ring|divide|placeholder)-opacity-\d+", "*-opacity-N (eliminado en v4)"),
            (r"\bflex-(shrink|grow)(-0)?\b", "flex-shrink / flex-grow (ahora shrink / grow)"),
            (r"\boverflow-ellipsis\b", "overflow-ellipsis (ahora text-ellipsis)"),
            (r"\bbg-gradient-to-[trbl]{1,2}\b", "bg-gradient-to-* (ahora bg-linear-to-*)"),
            (r"(?<=[\s\"'])!(?!important)(?=[a-z])", "! delante de la clase (ahora va detrás)"),
            (r"\b[\w-]+-\[--[\w-]+\]", "[--variable] (ahora (--variable))"),
            (r"@tailwindcss/container-queries|@tailwindcss/aspect-ratio", "plugin que ya viene incluido"),
        ],
        "buenas": [
            (r"@theme\b", "@theme"),
            (r"@tailwindcss/browser", "CDN de v4"),
            (r"\bbg-linear-to-[trbl]{1,2}\b", "bg-linear-to-*"),
            (r"\b@container\b|class=\"[^\"]*@container", "container queries"),
            (r"\b@(sm|md|lg|xl):", "variantes @sm:/@md:"),
            (r"\boutline-hidden\b", "outline-hidden"),
            (r"\bring-3\b", "ring-3"),
            (r"\b[\w-]+!(?=[\s\"])", "! al final"),
        ],
    },
}


def preguntar(prompt, sistema):
    datos = json.dumps({"model": MODELO, "prompt": prompt, "system": sistema, "stream": False, "think": False,
                        "options": {"num_ctx": 16384, "num_predict": 2048, "temperature": 0, "seed": 42}}).encode()
    r = urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", data=datos,
                                                      headers={"Content-Type": "application/json"}), timeout=600)
    return json.loads(r.read())["response"]


def contar(codigo, reglas):
    out = []
    for patron, nombre in reglas:
        n = len(re.findall(patron, codigo, re.I))
        if n:
            out.append((nombre, n))
    return out


def main():
    nombre = sys.argv[1] if len(sys.argv) > 1 else "tailwind4"
    p = PRUEBAS[nombre]
    guia = (BASE / "guias" / f"{nombre}.md").read_text(encoding="utf-8")
    base_sis = "Eres un programador web. Responde SOLO con el código HTML completo en un bloque ```html, sin explicaciones."
    filas, tot = [], {"sin": [0, 0], "con": [0, 0]}
    print(f"PROBAR GUÍA {nombre} · {len(p['tareas'])} tareas × 2 (sin guía / con guía) · {MODELO}", flush=True)
    for i, tarea in enumerate(p["tareas"], 1):
        fila = {"tarea": tarea}
        for modo in ("sin", "con"):
            sis = base_sis + ("\n\nGUÍA DE VERSIÓN (OBLIGATORIA, manda sobre lo que recuerdes):\n" + guia if modo == "con" else "")
            t = time.time()
            cod = preguntar(tarea, sis)
            malas, buenas = contar(cod, p["malas"]), contar(cod, p["buenas"])
            fila[modo] = {"malas": malas, "buenas": buenas, "seg": round(time.time() - t)}
            tot[modo][0] += sum(n for _, n in malas)
            tot[modo][1] += sum(n for _, n in buenas)
            (BASE / "guias" / "salidas").mkdir(parents=True, exist_ok=True)
            (BASE / "guias" / "salidas" / f"{nombre}_{i}_{modo}.html").write_text(cod, encoding="utf-8")
            print(f"  tarea {i} {modo} guía: {sum(n for _, n in malas)} errores de versión · {sum(n for _, n in buenas)} aciertos v4", flush=True)
        filas.append(fila)
    L = [f"# Prueba de la guía «{nombre}»", "", f"_{time.strftime('%Y-%m-%d %H:%M')} · {MODELO} · temperatura 0_", "",
         "| | Sin guía | Con guía |", "|---|---|---|",
         f"| Errores de versión antigua (total) | **{tot['sin'][0]}** | **{tot['con'][0]}** |",
         f"| Usos de sintaxis nueva (total) | {tot['sin'][1]} | {tot['con'][1]} |", "", "## Por tarea", ""]
    for i, f in enumerate(filas, 1):
        L.append(f"### {i}. {f['tarea']}")
        for modo in ("sin", "con"):
            m = ", ".join(f"{a} ×{n}" for a, n in f[modo]["malas"]) or "ninguno"
            b = ", ".join(f"{a} ×{n}" for a, n in f[modo]["buenas"]) or "ninguno"
            L.append(f"- **{modo} guía:** errores: {m} · nuevo: {b}")
        L.append("")
    (BASE / "guias" / f"resultado_{nombre}.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\nSin guía: {tot['sin'][0]} errores · Con guía: {tot['con'][0]} errores  ->  guias/resultado_{nombre}.md", flush=True)


if __name__ == "__main__":
    main()
