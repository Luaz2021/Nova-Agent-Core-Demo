"""Plantillas de Word: formal y APA (sin colores) y moderno (azul marino, para actividades y presentaciones).

Las plantillas viven en redaccion/estilos/*.docx. Si Alexander quiere otro aspecto, abre la plantilla en Word,
cambia los estilos (Normal, Titulo 1, Titulo 2...) y guarda: el redactor la usa tal cual.
Si falta una plantilla se crea aqui con los valores por defecto.
"""

from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .base import DIR_ESTILOS

NEGRO = RGBColor(0, 0, 0)
GRIS = RGBColor(0x40, 0x40, 0x40)

# Colores de tablas, DAFO y cartel por estilo (word.py los usa). None = blanco y negro.
TEMAS = {
    "moderno": {
        "cabecera": "0F2240",
        "texto_cabecera": "FFFFFF",
        "alterna": "F8F9FA",
        "borde": "DEE2E6",
        "cartel": "0F2240",
        "cartel_2": "1B559B",
        "pilar": "E7F0FB",
        "pilar_texto": "1B559B",
        "dafo": {
            "D": ("FFF3CD", "B8860B"),
            "A": ("F8D7DA", "B02A37"),
            "F": ("D1E7DD", "146C43"),
            "O": ("CFE2FF", "1B559B"),
        },
    },
    None: {
        "cabecera": None,
        "texto_cabecera": "000000",
        "alterna": None,
        "borde": "000000",
        "cartel": "404040",
        "cartel_2": "595959",
        "pilar": "F2F2F2",
        "pilar_texto": "000000",
        "dafo": {k: ("F2F2F2", "000000") for k in "DAFO"},
    },
}

ESTILOS = {
    "formal": {
        "fuente": "Calibri",
        "tamano": 11,
        "interlineado": 1.15,
        "espacio_despues": 6,
        "sangria": 0,
        "margen": 2.5,
        "titulos": [
            (16, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (13, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (11, True, True, WD_ALIGN_PARAGRAPH.LEFT),
        ],
        "numero_pagina": "pie",
    },
    "apa": {
        "fuente": "Times New Roman",
        "tamano": 12,
        "interlineado": 2.0,
        "espacio_despues": 0,
        "sangria": 1.27,
        "margen": 2.54,
        "titulos": [
            (12, True, False, WD_ALIGN_PARAGRAPH.CENTER),
            (12, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (12, True, True, WD_ALIGN_PARAGRAPH.LEFT),
        ],
        "numero_pagina": "cabecera",
    },
    "moderno": {
        "fuente": "Calibri",
        "fuente_titulos": "Segoe UI",
        "tamano": 11,
        "interlineado": 1.15,
        "espacio_despues": 6,
        "sangria": 0,
        "margen": 2.54,
        "titulos": [
            (13.5, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (11.5, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (11, True, True, WD_ALIGN_PARAGRAPH.LEFT),
        ],
        "colores": {
            "texto": "212529",
            "h1": "0F2240",
            "h2": "1B559B",
            "h3": "1B559B",
            "titulo": "0F2240",
            "subtitulo": "1B559B",
            "nota": "6C757D",
        },
        "numero_pagina": "pie",
    },
}


def _color(cfg: dict, clave: str, defecto=NEGRO):
    valor = cfg.get("colores", {}).get(clave)
    return RGBColor.from_string(valor) if valor else defecto


def _fuente(
    estilo,
    nombre: str,
    tamano: int,
    negrita: bool = False,
    cursiva: bool = False,
    color=NEGRO,
) -> None:
    estilo.font.name = nombre
    estilo.font.size = Pt(tamano)
    estilo.font.bold = negrita
    estilo.font.italic = cursiva
    estilo.font.color.rgb = color
    rpr = estilo.element.get_or_add_rPr()
    fuentes = rpr.find(qn("w:rFonts"))
    if fuentes is None:
        fuentes = OxmlElement("w:rFonts")
        rpr.append(fuentes)
    for clave in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fuentes.set(qn(clave), nombre)
    for clave in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fuentes.attrib.pop(qn(clave), None)


def campo(run, codigo: str) -> None:
    """Campo de Word (PAGE, NUMPAGES...)."""
    for tipo, texto in (
        ("begin", None),
        (None, f" {codigo} "),
        ("separate", None),
        ("end", None),
    ):
        if tipo:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tipo)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = texto
        run._r.append(el)


def _numero_pagina(doc, donde: str, cfg: dict) -> None:
    seccion = doc.sections[0]
    if donde == "cabecera":
        p = seccion.header.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p.add_run()
        campo(r, "PAGE")
        r.font.size = Pt(cfg["tamano"])
        return
    p = seccion.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for texto, codigo in (("Página ", "PAGE"), (" de ", "NUMPAGES")):
        r = p.add_run(texto)
        r.font.size, r.font.color.rgb = Pt(9), GRIS
        r = p.add_run()
        campo(r, codigo)
        r.font.size, r.font.color.rgb = Pt(9), GRIS


def crear_plantilla(nombre: str, ruta: Path) -> None:
    cfg = ESTILOS[nombre]
    doc = Document()
    for s in doc.sections:  # A4
        s.page_width, s.page_height = Cm(21), Cm(29.7)
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Cm(
            cfg["margen"]
        )

    normal = doc.styles["Normal"]
    _fuente(normal, cfg["fuente"], cfg["tamano"], color=_color(cfg, "texto"))
    f_titulos = cfg.get("fuente_titulos", cfg["fuente"])
    pf = normal.paragraph_format
    pf.line_spacing = cfg["interlineado"]
    pf.space_after = Pt(cfg["espacio_despues"])
    pf.space_before = Pt(0)

    for nivel, (tam, negrita, cursiva, alineado) in enumerate(cfg["titulos"], start=1):
        est = doc.styles[f"Heading {nivel}"]
        _fuente(est, f_titulos, tam, negrita, cursiva, color=_color(cfg, f"h{nivel}"))
        est.paragraph_format.alignment = alineado
        est.paragraph_format.space_before = Pt(18 if nivel == 1 else 12)
        est.paragraph_format.space_after = Pt(6)
        est.paragraph_format.keep_with_next = True
        est.paragraph_format.line_spacing = (
            cfg["interlineado"] if nombre == "apa" else 1.0
        )

    _fuente(
        doc.styles["Title"],
        f_titulos,
        {"formal": 20, "moderno": 18}.get(nombre, 12),
        negrita=True,
        color=_color(cfg, "titulo"),
    )
    doc.styles["Title"].paragraph_format.space_after = Pt(6)
    _fuente(
        doc.styles["Subtitle"],
        f_titulos,
        12,
        negrita=nombre == "moderno",
        color=_color(cfg, "subtitulo", GRIS),
    )
    for lista in ("List Bullet", "List Number"):
        _fuente(doc.styles[lista], cfg["fuente"], cfg["tamano"])
        doc.styles[lista].paragraph_format.space_after = Pt(2)
    _fuente(doc.styles["Quote"], cfg["fuente"], cfg["tamano"], cursiva=True)
    doc.styles["Quote"].paragraph_format.left_indent = Cm(1.27)

    if "Cuerpo" not in [s.name for s in doc.styles]:
        cuerpo = doc.styles.add_style("Cuerpo", WD_STYLE_TYPE.PARAGRAPH)
        cuerpo.base_style = normal
        cuerpo.paragraph_format.first_line_indent = (
            Cm(cfg["sangria"]) if cfg["sangria"] else None
        )
        cuerpo.paragraph_format.alignment = (
            WD_ALIGN_PARAGRAPH.JUSTIFY
            if nombre in ("formal", "moderno")
            else WD_ALIGN_PARAGRAPH.LEFT
        )
    codigo = doc.styles.add_style("Codigo", WD_STYLE_TYPE.PARAGRAPH)
    codigo.base_style = normal
    _fuente(codigo, "Consolas", 9)
    codigo.paragraph_format.line_spacing = 1.0
    codigo.paragraph_format.space_after = Pt(0)
    codigo.paragraph_format.left_indent = Cm(0.5)
    pequeno = doc.styles.add_style("Nota", WD_STYLE_TYPE.PARAGRAPH)
    pequeno.base_style = normal
    _fuente(pequeno, cfg["fuente"], 9, color=_color(cfg, "nota", GRIS))

    _numero_pagina(doc, cfg["numero_pagina"], cfg)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(ruta))


def abrir(nombre: str = "formal"):
    """Documento vacio con los estilos de la plantilla."""
    nombre = nombre if nombre in ESTILOS else "formal"
    ruta = DIR_ESTILOS / f"{nombre}.docx"
    if not ruta.exists():
        crear_plantilla(nombre, ruta)
    doc = Document(str(ruta))
    cuerpo = doc.element.body
    for hijo in list(cuerpo):
        if hijo.tag != qn("w:sectPr"):
            cuerpo.remove(hijo)
    return doc
