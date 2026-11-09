"""
PUENTE DE INTERACTIVIDAD (Bloque 3) · sin IA, 0 tokens

  python puente_interactividad.py [carpeta]     (sin carpeta: el último análisis)

Lleva al clon lo que midió explorador_dinamico.py (interactividad.json):
  1. Datos: la parte útil va dentro del HTML en <script type="application/json" id="clon-datos">.
  2. Runtime: clon-interacciones.js (escrito a mano una sola vez) se mete detrás; engancha pestañas, bolitas de
     color, modales/desplegables y hover por el micro-contrato data-* o, si falta, por texto dentro de cada sección.
  3. Contrato: unas líneas al final de claude/sec_N.md para que Qwen ponga los ganchos data-* (y no escriba JS).
Es idempotente: si el HTML ya lo tenía, se reemplaza.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
RUNTIME = BASE / "clon-interacciones.js"
INICIO, FIN = "<!-- clon-interacciones: inicio -->", "<!-- clon-interacciones: fin -->"
ESTILO_UTIL = ("color", "fondo", "borde", "radio", "padding", "fuente", "espaciado", "sombra", "ancho")


def _estilo(e):
    return {k: v for k, v in (e or {}).items() if k in ESTILO_UTIL and v not in ("", None)} or None


def compactar(inter):
    """De interactividad.json, solo lo que usa el runtime (sin capturas ni rutas locales)."""
    secs = {}
    for n, s in (inter.get("secciones") or {}).items():
        # "sin_seccion" = lo fijo flotante (subir arriba, WhatsApp...): la limpieza lo quita del clon, no hay a quién enganchar
        if not str(n).isdigit():
            continue
        out = {}
        tabs = [{"id": g.get("id"), "filtra_contenido": g.get("filtra_contenido"),
                 "estilo_activa": _estilo(g.get("estilo_activa")), "estilo_inactiva": _estilo(g.get("estilo_inactiva")),
                 "pestanas": [{"texto": p.get("texto"), "aria_label": p.get("aria_label"),
                               "activa_por_defecto": p.get("activa_por_defecto"),
                               "tarjetas_visibles": p.get("tarjetas_visibles") or [],
                               "panel": p.get("panel")} for p in g.get("pestanas", [])]}
                for g in s.get("pestanas", []) if g.get("pestanas")]
        colores = [{"id": g.get("id"), "producto": g.get("producto"), "conmuta_imagen": g.get("conmuta_imagen"),
                    "estilo_activa": _estilo(g.get("estilo_activa")), "estilo_inactiva": _estilo(g.get("estilo_inactiva")),
                    "colores": [{k: c.get(k) for k in ("color_nombre", "color_hex", "img_url", "img_alt", "activo_por_defecto")}
                                for c in g.get("colores", [])]}
                   # "indicador" = puntitos de los colores disponibles (Apple): se ven, pero no se pulsan
                   for g in s.get("variantes_color", []) if g.get("colores") and g.get("tipo") != "indicador"]
        modales = [{"tipo": m.get("tipo"), "disparador": {"texto": (m.get("disparador") or {}).get("texto")},
                    "titulo": m.get("titulo"),
                    "bloques": [{"tag": b.get("tag"), "texto": b.get("texto"), "estilo": _estilo(b.get("estilo"))}
                                for b in m.get("bloques", [])],
                    "imagenes": [{"src": i.get("src") or i.get("url"), "alt": i.get("alt", "")} for i in m.get("imagenes", [])
                                 if isinstance(i, dict)],
                    "enlaces": [{"texto": a.get("texto")} for a in m.get("enlaces", []) if isinstance(a, dict)],
                    "estilo": _estilo(m.get("estilo")), "capa": m.get("capa"),
                    "cerrar": {"estilo": _estilo((m.get("cerrar") or {}).get("estilo"))}}
                   for m in s.get("modales", []) if (m.get("disparador") or {}).get("texto")]
        hover = [{"elemento": h.get("elemento"), "texto": h.get("texto"), "transicion": h.get("transicion"),
                  "cambios": {k: v for k, v in (h.get("cambios") or {}).items() if k.endswith(":self")}}
                 for h in s.get("hover", []) if any(k.endswith(":self") for k in (h.get("cambios") or {}))]
        for k, v in (("pestanas", tabs), ("variantes_color", colores), ("modales", modales), ("hover", hover)):
            if v:
                out[k] = v
        if out:
            secs[str(n)] = out
    return {"secciones": secs}


def inyectar(html, carpeta):
    """Mete (o reemplaza) los datos y el runtime antes de </body>. Sin interactividad.json, deja el HTML igual."""
    html = re.sub(re.escape(INICIO) + r".*?" + re.escape(FIN) + r"\s*", "", html, flags=re.S)
    f = Path(carpeta) / "interactividad.json"
    if not f.exists() or not RUNTIME.exists():
        return html
    datos = compactar(json.loads(f.read_text(encoding="utf-8")))
    if not datos["secciones"]:
        return html
    js_datos = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    bloque = (f'{INICIO}\n<script type="application/json" id="clon-datos">{js_datos}</script>\n'
              f'<script>\n{RUNTIME.read_text(encoding="utf-8")}\n</script>\n{FIN}\n')
    i = html.lower().rfind("</body>")
    return html[:i] + bloque + html[i:] if i >= 0 else html + bloque


def contrato(carpeta):
    """Líneas del micro-contrato al final de claude/sec_N.md (40-120 tokens por sección con interacciones)."""
    f = Path(carpeta) / "interactividad.json"
    dclaude = Path(carpeta) / "claude"
    if not f.exists() or not dclaude.exists():
        return 0
    datos = compactar(json.loads(f.read_text(encoding="utf-8")))
    hechos = 0
    for n, s in datos["secciones"].items():
        L = []
        for g in s.get("pestanas", []):
            textos = "|".join(p["texto"] or p["aria_label"] or "?" for p in g["pestanas"])
            L.append(f'- Pestañas "{textos}" -> en cada botón data-tab="{g["id"]}:0..{len(g["pestanas"]) - 1}"'
                     + ("; las tarjetas se filtran solas (no escribas varias versiones)" if g.get("filtra_contenido") else ""))
        for g in s.get("variantes_color", []):
            L.append(f'- Bolitas de color de "{g["producto"]}" -> data-color="{g["id"]}:0..{len(g["colores"]) - 1}" en cada bolita; '
                     "una sola foto (la del color activo), NO pongas las fotos de los demás colores")
        for i, m in enumerate(s.get("modales", [])):
            L.append(f'- Botón "{m["disparador"]["texto"]}" -> data-modal="{n}:{i}" ({m["tipo"]}); su contenido NO lo escribes tú')
        if not L:
            continue
        sec = dclaude / f"sec_{n}.md"
        if not sec.exists():
            continue
        t = re.sub(r"\n## INTERACCIÓN \(contrato\).*", "", sec.read_text(encoding="utf-8"), flags=re.S).rstrip()
        t += ("\n\n## INTERACCIÓN (contrato)\nNo escribas JavaScript: clon-interacciones.js lo hace. Solo conserva los textos y "
              "aria-label de los botones y pon estos atributos:\n" + "\n".join(L) + "\n")
        sec.write_text(t, encoding="utf-8")
        hechos += 1
    return hechos


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    carpeta = Path(args[0]) if args else Path((BASE.parent / "workspace" / "ultimo_analisis.txt").read_text(encoding="utf-8").strip())
    out = carpeta / "construccion"
    for nombre in ("index.html", "index_base.html", "index_final.html"):
        p = out / nombre
        if p.exists():
            p.write_text(inyectar(p.read_text(encoding="utf-8"), carpeta), encoding="utf-8")
    n = contrato(carpeta)
    datos = compactar(json.loads((carpeta / "interactividad.json").read_text(encoding="utf-8"))) if (carpeta / "interactividad.json").exists() else {"secciones": {}}
    cuenta = {k: sum(len(s.get(k, [])) for s in datos["secciones"].values()) for k in ("pestanas", "variantes_color", "modales", "hover")}
    print(f"Interactividad en el clon: {cuenta['pestanas']} grupos de pestañas, {cuenta['variantes_color']} de colores, "
          f"{cuenta['modales']} modales/desplegables, {cuenta['hover']} hover · contrato en {n} sec_N.md")


if __name__ == "__main__":
    main()
