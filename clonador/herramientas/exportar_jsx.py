"""
EXPORTAR A JSX · el clon HTML (construccion/index.html, Tailwind) convertido en componentes React, sin IA y en local

  python herramientas/exportar_jsx.py [carpeta]          (sin carpeta: el último análisis)

Escribe workspace/<web>/react/clon/:
  Pagina.tsx        todo el <body> del clon; cada sección marcada (data-clon-sec="N") se cambia por <SeccionN />
  SeccionN.tsx      una por sección, con data-sec="N" en su raíz (lo usa la medición del React)
  estilos.css       el CSS propio del clon dentro de @layer clon (por debajo de las utilidades de Tailwind,
                    como en el HTML, donde el CDN de Tailwind inyecta sus estilos después)
  index.ts          exporta Pagina
y copia a react/assets/ las fotos que encuentra en assets/_mapa.json (URL -> archivo de analizar.py).

Por qué: el React escrito a mano sobre datos_web.ts sacó 67 %; el clon HTML, 93 %. Convertido, el React empieza
con la misma maqueta que el clon y lo que falte se arregla en el motor.
"""

import json
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # clones_web/
sys.dont_write_bytecode = True

VACIOS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}
FUERA = {
    "script",
    "noscript",
    "template",
    "title",
    "meta",
    "link",
    "base",
}  # no van al JSX
# html.parser pasa todo a minúsculas: nombres de SVG que React necesita en camelCase
ETIQUETAS_SVG = {
    t.lower(): t
    for t in (
        "linearGradient",
        "radialGradient",
        "clipPath",
        "foreignObject",
        "textPath",
        "feGaussianBlur",
        "feOffset",
        "feBlend",
        "feColorMatrix",
        "feComposite",
        "feFlood",
        "feMerge",
        "feMergeNode",
        "feMorphology",
        "feTurbulence",
        "feDisplacementMap",
        "feDropShadow",
        "animateTransform",
        "animateMotion",
    )
}
ATRIBUTOS = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "srcset": "srcSet",
    "crossorigin": "crossOrigin",
    "autoplay": "autoPlay",
    "playsinline": "playsInline",
    "readonly": "readOnly",
    "maxlength": "maxLength",
    "colspan": "colSpan",
    "rowspan": "rowSpan",
    "frameborder": "frameBorder",
    "allowfullscreen": "allowFullScreen",
    "referrerpolicy": "referrerPolicy",
    "datetime": "dateTime",
    "enterkeyhint": "enterKeyHint",
    "autocomplete": "autoComplete",
    "spellcheck": "spellCheck",
    "contenteditable": "contentEditable",
    "fetchpriority": "fetchPriority",
    "novalidate": "noValidate",
    "accesskey": "accessKey",
    "xlink:href": "xlinkHref",
    "xml:space": "xmlSpace",
    "xmlns:xlink": "xmlnsXlink",
    "http-equiv": "httpEquiv",
}
ATRIBUTOS.update(
    {
        a.lower(): a
        for a in (
            "viewBox",
            "preserveAspectRatio",
            "gradientUnits",
            "gradientTransform",
            "patternUnits",
            "patternTransform",
            "clipPathUnits",
            "maskUnits",
            "maskContentUnits",
            "textLength",
            "lengthAdjust",
            "baseFrequency",
            "stdDeviation",
            "numOctaves",
            "markerWidth",
            "markerHeight",
            "refX",
            "refY",
            "pathLength",
            "spreadMethod",
            "startOffset",
            "filterUnits",
            "primitiveUnits",
            "kernelMatrix",
            "tableValues",
            "attributeName",
            "repeatCount",
            "keyTimes",
            "keySplines",
            "calcMode",
        )
    }
)
BOOLEANOS = {
    "hidden",
    "disabled",
    "muted",
    "controls",
    "loop",
    "autoplay",
    "playsinline",
    "checked",
    "selected",
    "readonly",
    "required",
    "multiple",
    "open",
    "defer",
    "async",
    "allowfullscreen",
    "novalidate",
    "inert",
}


class Nodo:
    def __init__(self, tag, attrs, padre=None):
        self.tag, self.attrs, self.padre, self.hijos = tag, attrs, padre, []


class Arbol(HTMLParser):
    """HTML -> árbol sencillo (el clon es HTML bien formado, sale del navegador)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo("#raiz", [])
        self.actual = self.raiz

    def handle_starttag(self, tag, attrs):
        n = Nodo(tag, attrs, self.actual)
        self.actual.hijos.append(n)
        if tag not in VACIOS:
            self.actual = n

    def handle_startendtag(self, tag, attrs):
        self.actual.hijos.append(Nodo(tag, attrs, self.actual))

    def handle_endtag(self, tag):
        n = self.actual
        while (
            n is not self.raiz and n.tag != tag
        ):  # cierra lo que quedara abierto (p sin cerrar, etc.)
            n = n.padre
        if n is not self.raiz:
            self.actual = n.padre

    def handle_data(self, data):
        self.actual.hijos.append(data)


def _camel(nombre):
    return re.sub(r"-([a-z])", lambda m: m.group(1).upper(), nombre)


def _estilo(css):
    """'color: red; font-size: 2px' -> {color: "red", fontSize: "2px"} (las variables --x se quedan entre comillas)."""
    pares = []
    for decl in re.split(r";(?![^(]*\))", css):
        if ":" not in decl:
            continue
        k, v = decl.split(":", 1)
        k, v = k.strip(), v.strip()
        if not k or not v:
            continue
        clave = (
            json.dumps(k)
            if k.startswith("--")
            else _camel(k.lower())
            if not k.startswith("-ms-")
            else "ms" + _camel(k[3:]).capitalize()
        )
        pares.append(f"{clave}: {json.dumps(v, ensure_ascii=False)}")
    return "{{" + ", ".join(pares) + "}}"


def _texto(t):
    """Texto -> JSX. Los espacios entre etiquetas importan en línea («Ver regalos ›»): se dejan como {" "}."""
    if not t.strip():
        return '{" "}' if t else ""
    t = re.sub(r"\s+", " ", t)
    return "{" + json.dumps(t, ensure_ascii=False) + "}"


class Conversor:
    def __init__(self, mapa, assets_origen, assets_destino):
        self.mapa, self.origen, self.destino = mapa, assets_origen, assets_destino
        self.secciones = {}  # n -> jsx
        self.copiadas = set()
        self.base = None  # construccion/base/assets (fotos de vídeos/canvas que hace el clon)

    def url(self, u):
        """URL de foto -> /assets/archivo si el motor la tiene: descargada (mapa de analizar.py) o hecha por el clon
        (assets/kN_escritorio.png: foto de un vídeo/canvas/iframe, en construccion/base/assets)."""
        if u.startswith("assets/") and self.base and (self.base / u[7:]).exists():
            origen, archivo = self.base / u[7:], u[7:]
        else:
            archivo = self.mapa.get(u) or self.mapa.get(u.split("?")[0])
            if not archivo or not (self.origen / archivo).exists():
                return u
            origen = self.origen / archivo
        if archivo not in self.copiadas:
            shutil.copy(origen, self.destino / archivo)
            self.copiadas.add(archivo)
        return "/assets/" + archivo

    def srcset(self, v):
        return ", ".join(
            " ".join([self.url(p.split()[0])] + p.split()[1:])
            for p in v.split(",")
            if p.strip()
        )

    def atributos(self, tag, attrs):
        out = []
        for k, v in attrs:
            if k.startswith("on") or k in ("xmlns",) and tag != "svg":
                continue
            if k == "style":
                if v and v.strip():
                    out.append(f"style={_estilo(v)}")
                continue
            if k in ("src", "poster") and v:
                v = self.url(v)
            elif k == "srcset" and v:
                v = self.srcset(v)
            nombre = ATRIBUTOS.get(k) or (
                k if k.startswith(("data-", "aria-")) else _camel(k)
            )
            if v is None or (k in BOOLEANOS and v in ("", k)):
                out.append(nombre if v is None or k in BOOLEANOS else f'{nombre}=""')
            else:
                out.append(f"{nombre}={{{json.dumps(v, ensure_ascii=False)}}}")
        return out

    def jsx(self, nodo, nivel=0):
        if isinstance(nodo, str):
            return _texto(nodo)
        if nodo.tag in FUERA:
            return ""
        attrs = dict(nodo.attrs)
        sec = attrs.get("data-clon-sec")
        if sec and nivel > 0 and sec.isdigit():
            n = int(sec)
            # la raíz de la sección se convierte aparte; aquí solo queda la llamada al componente
            self.secciones[n] = self.jsx(nodo, 0)
            return f"<Seccion{n} />"
        tag = ETIQUETAS_SVG.get(nodo.tag, nodo.tag)
        lista = self.atributos(nodo.tag, nodo.attrs)
        if sec and nivel == 0:
            lista.append(f'data-sec="{sec}"')
        abre = f"<{tag}{(' ' + ' '.join(lista)) if lista else ''}"
        if nodo.tag in VACIOS:
            return abre + " />"
        if nodo.tag in ("textarea",):  # el valor inicial va como defaultValue
            return (
                abre
                + f" defaultValue={{{json.dumps(''.join(h for h in nodo.hijos if isinstance(h, str)))}}} />"
            )
        dentro = "".join(self.jsx(h, nivel + 1) for h in nodo.hijos)
        return f"{abre}>{dentro}</{tag}>" if dentro else abre + " />"


def _componente(nombre, jsx, imports=""):
    return (
        f"// Generado por clones_web/herramientas/exportar_jsx.py desde el clon HTML: no se edita a mano (se regenera).\n"
        f"{imports}export default function {nombre}() {{\n  return (\n    <>{jsx}</>\n  )\n}}\n"
    )


def exportar(carpeta):
    carpeta = Path(carpeta).resolve()
    html = (carpeta / "construccion" / "index.html").read_text(encoding="utf-8")
    cab, cuerpo = html[: html.find("<body")], html[html.find("<body") :]
    destino = carpeta / "react" / "clon"
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    (carpeta / "react" / "assets").mkdir(parents=True, exist_ok=True)
    fm = carpeta / "assets" / "_mapa.json"
    mapa = json.loads(fm.read_text(encoding="utf-8")) if fm.exists() else {}

    # CSS propio del clon -> @layer clon (por debajo de las utilidades de Tailwind); fotos de url() también a /assets
    conv = Conversor(mapa, carpeta / "assets", carpeta / "react" / "assets")
    conv.base = carpeta / "construccion" / "base" / "assets"
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", cab, re.DOTALL))
    css = re.sub(
        r'url\((["\']?)([^)"\']+)\1\)', lambda m: f'url("{conv.url(m.group(2))}")', css
    )
    fuentes = re.findall(r'<link[^>]+href="(https://fonts\.googleapis\.com[^"]+)"', cab)
    (destino / "estilos.css").write_text(
        "/* Generado por exportar_jsx.py: CSS propio del clon. Va en @layer clon, por debajo de las utilidades de Tailwind. */\n"
        + "".join(f'@import url("{f}");\n' for f in fuentes)
        + "@layer clon {\n"
        + css
        + "\n}\n",
        encoding="utf-8",
    )

    arbol = Arbol()
    arbol.feed(cuerpo)
    body = next(
        (h for h in arbol.raiz.hijos if isinstance(h, Nodo) and h.tag == "body"),
        arbol.raiz,
    )
    pagina = "".join(conv.jsx(h, 1) for h in body.hijos)

    imports = "".join(
        f'import Seccion{n} from "./Seccion{n}";\n' for n in sorted(conv.secciones)
    )
    (destino / "Pagina.tsx").write_text(
        _componente("Pagina", pagina, imports + 'import "./estilos.css";\n\n'),
        encoding="utf-8",
    )
    for n, jsx in conv.secciones.items():
        (destino / f"Seccion{n}.tsx").write_text(
            _componente(f"Seccion{n}", jsx), encoding="utf-8"
        )
    (destino / "index.ts").write_text(
        'export { default as Pagina } from "./Pagina";\n', encoding="utf-8"
    )
    print(
        f"JSX: {len(conv.secciones)} secciones ({', '.join(map(str, sorted(conv.secciones)))}) + Pagina, "
        f"{len(conv.copiadas)} fotos locales, CSS {len(css) // 1024} KB -> {destino}"
    )
    return destino


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    carpeta = (
        Path(args[0])
        if args
        else Path(
            (RAIZ / "workspace" / "ultimo_analisis.txt")
            .read_text(encoding="utf-8")
            .strip()
        )
    )
    exportar(carpeta)


if __name__ == "__main__":
    main()
