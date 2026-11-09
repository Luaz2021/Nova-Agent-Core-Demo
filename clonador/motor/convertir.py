import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
# -*- coding: utf-8 -*-
"""
CONVERSOR (v8): pasa el clon fiel (CSS por elemento) a clases de Tailwind, sin IA.

Cada regla .kN{prop:valor} se convierte en clases del propio elemento:
  - las más comunes con su forma habitual: flex, items-center, text-[14px], bg-[#F45096], px-[16px]...
  - el resto como "propiedad arbitraria" de Tailwind: [aspect-ratio:1/1]
  - escritorio con prefijo md:
Lo que Tailwind no puede expresar bien en una clase (pseudo-elementos ::before/::after, imágenes de fondo
con url(), listas de fuentes con comillas, sombras con varias capas) se queda en un <style> pequeño.

Resultado: clon_tailwind.html (misma apariencia, código en clases de utilidad).
"""
import re
from pathlib import Path

COMPLEJAS = {"background-image", "font-family", "box-shadow", "text-shadow", "filter", "clip-path",
             "grid-template-columns", "grid-template-rows", "transform", "content", "mix-blend-mode"}

FIJAS = {
    ("display", "flex"): "flex", ("display", "grid"): "grid", ("display", "block"): "block", ("display", "none"): "hidden",
    ("display", "inline-block"): "inline-block", ("display", "inline-flex"): "inline-flex", ("display", "inline"): "inline",
    ("display", "contents"): "contents", ("display", "inline-grid"): "inline-grid", ("display", "table"): "table",
    ("position", "relative"): "relative", ("position", "absolute"): "absolute", ("position", "sticky"): "sticky",
    ("position", "static"): "static", ("flex-direction", "column"): "flex-col", ("flex-direction", "row"): "flex-row",
    ("flex-wrap", "wrap"): "flex-wrap", ("flex-wrap", "nowrap"): "flex-nowrap",
    ("justify-content", "center"): "justify-center", ("justify-content", "space-between"): "justify-between",
    ("justify-content", "flex-start"): "justify-start", ("justify-content", "flex-end"): "justify-end",
    ("justify-content", "space-around"): "justify-around", ("justify-content", "space-evenly"): "justify-evenly",
    ("align-items", "center"): "items-center", ("align-items", "flex-start"): "items-start", ("align-items", "flex-end"): "items-end",
    ("align-items", "stretch"): "items-stretch", ("align-items", "baseline"): "items-baseline",
    ("text-align", "center"): "text-center", ("text-align", "left"): "text-left", ("text-align", "right"): "text-right",
    ("text-align", "start"): "text-start", ("text-transform", "uppercase"): "uppercase", ("text-transform", "none"): "normal-case",
    ("text-transform", "lowercase"): "lowercase", ("text-transform", "capitalize"): "capitalize",
    ("font-style", "italic"): "italic", ("font-style", "normal"): "not-italic",
    ("overflow-x", "hidden"): "overflow-x-hidden", ("overflow-y", "hidden"): "overflow-y-hidden",
    ("overflow-x", "auto"): "overflow-x-auto", ("overflow-y", "auto"): "overflow-y-auto",
    ("overflow-x", "clip"): "overflow-x-clip", ("overflow-y", "clip"): "overflow-y-clip",
    ("object-fit", "cover"): "object-cover", ("object-fit", "contain"): "object-contain",
    ("white-space", "nowrap"): "whitespace-nowrap", ("text-decoration-line", "underline"): "underline",
    ("text-decoration-line", "none"): "no-underline", ("visibility", "hidden"): "invisible", ("box-sizing", "border-box"): "box-border",
    ("box-sizing", "content-box"): "box-content", ("list-style-type", "none"): "list-none", ("cursor", "pointer"): "cursor-pointer",
}
PREFIJO = {  # propiedad -> prefijo de Tailwind con valor arbitrario
    "width": "w", "height": "h", "min-width": "min-w", "min-height": "min-h", "max-width": "max-w", "max-height": "max-h",
    "margin-top": "mt", "margin-right": "mr", "margin-bottom": "mb", "margin-left": "ml",
    "padding-top": "pt", "padding-right": "pr", "padding-bottom": "pb", "padding-left": "pl",
    "top": "top", "right": "right", "bottom": "bottom", "left": "left", "z-index": "z",
    "font-size": "text", "font-weight": "font", "line-height": "leading", "letter-spacing": "tracking",
    "row-gap": "gap-y", "column-gap": "gap-x", "flex-grow": "grow", "flex-shrink": "shrink", "flex-basis": "basis",
    "order": "order", "opacity": "opacity",
    "border-top-left-radius": "rounded-tl", "border-top-right-radius": "rounded-tr",
    "border-bottom-right-radius": "rounded-br", "border-bottom-left-radius": "rounded-bl",
}
COLORES = {"color": "text", "background-color": "bg", "border-top-color": "border-t", "border-right-color": "border-r",
           "border-bottom-color": "border-b", "border-left-color": "border-l", "text-decoration-color": "decoration",
           "fill": "fill", "stroke": "stroke"}


def _hex(v):
    m = re.fullmatch(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)", v.strip())
    if not m:
        return None
    r, g, b = (int(float(x)) for x in m.groups()[:3])
    a = m.group(4)
    if a is not None and float(a) < 1:
        return f"#{r:02X}{g:02X}{b:02X}{int(round(float(a) * 255)):02X}"
    return f"#{r:02X}{g:02X}{b:02X}"


def _arb(v):
    """Valor seguro dentro de [...] de Tailwind (los espacios se escriben como _)."""
    return v.strip().replace("_", "\\_").replace(" ", "_")


def clase(prop, valor):
    """Devuelve la clase de Tailwind o None si debe quedarse en CSS."""
    v = valor.strip()
    # "revert" (en escritorio vuelve al valor por defecto lo que el móvil cambió: flex-col -> fila, acordeón oculto ->
    # visible, letra de 10px -> la heredada) TIENE que ser utilidad: md:[flex-direction:revert] va en la misma hoja que
    # flex-col y gana; como regla aparte en <style>, el CDN de Tailwind se inyecta después y la de móvil se colaba en PC.
    if v in ("revert", "inherit"):
        return f"[{prop}:{v}]"
    if prop in COMPLEJAS or "url(" in v or "var(" in v or '"' in v or "'" in v:
        return None
    if (prop, v) in FIJAS:
        return FIJAS[(prop, v)]
    if prop in COLORES:
        h = _hex(v)
        return f"{COLORES[prop]}-[{h}]" if h else None
    if prop in PREFIJO:
        if prop == "font-size":
            return f"text-[length:{_arb(v)}]"
        if prop == "line-height" and v == "normal":
            return "leading-normal"
        return f"{PREFIJO[prop]}-[{_arb(v)}]"
    if prop.startswith("border-") and prop.endswith("-width"):
        lado = prop.split("-")[1][0]
        return f"border-{lado}-[length:{_arb(v)}]"
    if prop.startswith("border-") and prop.endswith("-style"):
        return f"[{prop}:{_arb(v)}]"
    return f"[{prop}:{_arb(v)}]"


def compactar(cl):
    """Une lados iguales: mt/mr/mb/ml -> m, pt/pb -> py, rounded-tl/tr/br/bl -> rounded... (por prefijo md: o sin él)."""
    out = list(cl)
    for pre in ("", "md:"):
        def val(nombre):
            for c in out:
                if c.startswith(pre + nombre + "-["):
                    return c[len(pre + nombre) + 1:]
            return None
        for todos, lados, xy in (("m", ("mt", "mr", "mb", "ml"), ("my", "mx")), ("p", ("pt", "pr", "pb", "pl"), ("py", "px"))):
            v = [val(x) for x in lados]
            if all(v) and len(set(v)) == 1:
                out = [c for c in out if c not in [pre + x + "-" + v[0] for x in lados]] + [pre + todos + "-" + v[0]]
            else:
                if v[0] and v[0] == v[2]:
                    out = [c for c in out if c not in (pre + lados[0] + "-" + v[0], pre + lados[2] + "-" + v[0])] + [pre + xy[0] + "-" + v[0]]
                if v[1] and v[1] == v[3]:
                    out = [c for c in out if c not in (pre + lados[1] + "-" + v[1], pre + lados[3] + "-" + v[1])] + [pre + xy[1] + "-" + v[1]]
        r = [val(x) for x in ("rounded-tl", "rounded-tr", "rounded-br", "rounded-bl")]
        if all(r) and len(set(r)) == 1:
            out = [c for c in out if not any(c == pre + x + "-" + r[0] for x in ("rounded-tl", "rounded-tr", "rounded-br", "rounded-bl"))] + [pre + "rounded-" + r[0]]
    return out


def _reglas(bloque):
    out = {}
    for sel, cuerpo in re.findall(r"\.(k\d+)\{([^}]*)\}", bloque):
        props = {}
        for decl in re.split(r";(?![^(]*\))", cuerpo):
            if ":" in decl:
                p, v = decl.split(":", 1)
                props[p.strip()] = v.strip()
        out[sel] = props
    return out


def convertir(ruta_fiel, ruta_salida):
    html = Path(ruta_fiel).read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", html, re.S)
    css = m.group(1)
    i = css.find("@media (min-width: 768px){")
    previo, media = (css[:i], css[i + len("@media (min-width: 768px){"):css.rfind("}")]) if i >= 0 else (css, "")
    # lo que no son reglas .kN (fuentes, reset) se conserva tal cual
    cabecera = re.sub(r"\.k\d+(::?(before|after))?\{[^}]*\}\n?", "", previo)
    pseudo_base = re.findall(r"(\.k\d+::(?:before|after)\{[^}]*\})", previo)
    pseudo_md = re.findall(r"(\.k\d+::(?:before|after)\{[^}]*\})", media)
    base = _reglas(re.sub(r"\.k\d+::(before|after)\{[^}]*\}", "", previo))
    md = _reglas(re.sub(r"\.k\d+::(before|after)\{[^}]*\}", "", media))

    clases, resto_base, resto_md = {}, [], []
    for k in set(base) | set(md):
        cl, rb, rm = [], {}, {}
        for p, v in base.get(k, {}).items():
            c = clase(p, v)
            (cl.append(c) if c else rb.__setitem__(p, v))
        for p, v in md.get(k, {}).items():
            c = clase(p, v)
            if c:
                cl.append("md:" + c)
            else:
                rm[p] = v
        clases[k] = " ".join(compactar(cl))
        if rb:
            resto_base.append(f".{k}{{{';'.join(f'{p}:{v}' for p, v in rb.items())}}}")
        if rm:   # .kN.kN: más específica que una utilidad de móvil de Tailwind (que se inyecta después que este <style>)
            resto_md.append(f".{k}.{k}{{{';'.join(f'{p}:{v}' for p, v in rm.items())}}}")

    def sustituir(mt):
        k = mt.group(1)
        extra = clases.get(k, "")
        return f'class="{k}{(" " + extra) if extra else ""}"'
    cuerpo = re.sub(r'class="(k\d+)"', sustituir, html[html.find("<body>"):])
    estilo = (cabecera.strip() + "\n" + "\n".join(resto_base + pseudo_base)
              + "\n@media (min-width: 768px){\n" + "\n".join(resto_md + pseudo_md) + "\n}\n")
    cabeza = html[:m.start()] + "<script src=\"https://cdn.tailwindcss.com\"></script>\n<script>tailwind.config={corePlugins:{preflight:false}}</script>\n<style>" + estilo + "</style>\n</head>\n"
    Path(ruta_salida).write_text(cabeza + cuerpo, encoding="utf-8")
    total = sum(len(c.split()) for c in clases.values())
    print(f"  Tailwind: {total} clases de utilidad, {len(resto_base) + len(resto_md) + len(pseudo_base) + len(pseudo_md)} reglas CSS complejas -> {Path(ruta_salida).name}")
    return Path(ruta_salida)


if __name__ == "__main__":
    import sys
    convertir(sys.argv[1], sys.argv[2])
