"""Plantillas de Word: formal y APA (sin colores) y moderno (azul marino, para actividades y presentaciones).

Las plantillas viven en redaccion/estilos/*.docx. Si el usuario quiere otro aspecto, abre la plantilla en Word,
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
    "uem": {
        "cabecera": "C8102E",
        "texto_cabecera": "FFFFFF",
        "alterna": "F8F9FA",
        "borde": "DEE2E6",
        "cartel": "C8102E",
        "cartel_2": "8C0B20",
        "pilar": "FDF2F4",
        "pilar_texto": "C8102E",
        "dafo": {
            "D": ("FDF2F4", "8C0B20"),
            "A": ("F8D7DA", "B02A37"),
            "F": ("E9ECEF", "212529"),
            "O": ("F1F3F5", "495057"),
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
    "uem": {
        "fuente": "Verdana",
        "fuente_titulos": "Verdana",
        "tamano": 11,
        "interlineado": 1.5,
        "espacio_despues": 6,
        "sangria": 0,
        "margenes": {"top": 2.5, "bottom": 2.5, "left": 3.0, "right": 2.5},
        "titulos": [
            (16, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (14, True, False, WD_ALIGN_PARAGRAPH.LEFT),
            (12, True, False, WD_ALIGN_PARAGRAPH.LEFT),
        ],
        "colores": {
            "texto": "000000",
            "h1": "C8102E",
            "h2": "C8102E",
            "h3": "C8102E",
            "titulo": "C8102E",
            "subtitulo": "404040",
            "nota": "595959",
        },
        "numero_pagina": "pie",
        "ocultar_numero_portada": True,
    },
}


def _fijar_idioma(estilo, lang: str = "es-ES") -> None:
    rpr = estilo.element.get_or_add_rPr()
    el = rpr.find(qn("w:lang"))
    if el is None:
        el = OxmlElement("w:lang")
        rpr.append(el)
    el.set(qn("w:val"), lang)


def _activar_update_fields(doc) -> None:
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        el = OxmlElement("w:updateFields")
        el.set(qn("w:val"), "true")
        settings.append(el)


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
    margenes = cfg.get("margenes") or {
        "top": cfg["margen"],
        "bottom": cfg["margen"],
        "left": cfg["margen"],
        "right": cfg["margen"],
    }
    for s in doc.sections:  # A4
        s.page_width, s.page_height = Cm(21), Cm(29.7)
        s.top_margin = Cm(margenes["top"])
        s.bottom_margin = Cm(margenes["bottom"])
        s.left_margin = Cm(margenes["left"])
        s.right_margin = Cm(margenes["right"])
        if cfg.get("ocultar_numero_portada"):
            s.different_first_page_header_footer = True

    normal = doc.styles["Normal"]
    _fuente(normal, cfg["fuente"], cfg["tamano"], color=_color(cfg, "texto"))
    _fijar_idioma(normal, "es-ES")
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
            cfg["interlineado"] if nombre in ("apa", "uem") else 1.0
        )

    _fuente(
        doc.styles["Title"],
        f_titulos,
        {"formal": 20, "moderno": 18, "uem": 20}.get(nombre, 12),
        negrita=True,
        color=_color(cfg, "titulo"),
    )
    doc.styles["Title"].paragraph_format.space_after = Pt(6)
    _fuente(
        doc.styles["Subtitle"],
        f_titulos,
        12,
        negrita=nombre in ("moderno", "uem"),
        color=_color(cfg, "subtitulo", GRIS),
    )
    for lista in ("List Bullet", "List Number"):
        _fuente(doc.styles[lista], cfg["fuente"], cfg["tamano"])
        doc.styles[lista].paragraph_format.space_after = Pt(2)
    _fuente(doc.styles["Quote"], cfg["fuente"], cfg["tamano"], cursiva=True)
    doc.styles["Quote"].paragraph_format.left_indent = Cm(1.27)

    nombres_est = {s.name for s in doc.styles}
    if "Cuerpo" not in nombres_est:
        cuerpo = doc.styles.add_style("Cuerpo", WD_STYLE_TYPE.PARAGRAPH)
        cuerpo.base_style = normal
        cuerpo.paragraph_format.first_line_indent = (
            Cm(cfg["sangria"]) if cfg["sangria"] else None
        )
        cuerpo.paragraph_format.alignment = (
            WD_ALIGN_PARAGRAPH.JUSTIFY
            if nombre in ("formal", "moderno", "uem")
            else WD_ALIGN_PARAGRAPH.LEFT
        )
    if "Codigo" not in nombres_est:
        codigo = doc.styles.add_style("Codigo", WD_STYLE_TYPE.PARAGRAPH)
        codigo.base_style = normal
        _fuente(codigo, "Consolas", 9)
        codigo.paragraph_format.line_spacing = 1.0
        codigo.paragraph_format.space_after = Pt(0)
        codigo.paragraph_format.left_indent = Cm(0.5)
    if "Nota" not in nombres_est:
        pequeno = doc.styles.add_style("Nota", WD_STYLE_TYPE.PARAGRAPH)
        pequeno.base_style = normal
        _fuente(pequeno, cfg["fuente"], 9, color=_color(cfg, "nota", GRIS))
    if "Referencia" not in nombres_est:
        ref = doc.styles.add_style("Referencia", WD_STYLE_TYPE.PARAGRAPH)
        ref.base_style = normal
        ref.paragraph_format.left_indent = Cm(1.27)
        ref.paragraph_format.first_line_indent = Cm(-1.27)
        ref.paragraph_format.space_after = Pt(6)
        ref.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    _numero_pagina(doc, cfg["numero_pagina"], cfg)
    _activar_update_fields(doc)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(ruta))


def abrir(nombre: str = "formal", plantilla: str | Path | None = None):
    """Documento vacio con los estilos de la plantilla (o plantilla externa conservando su portada)."""
    if plantilla and Path(plantilla).exists():
        doc = Document(str(plantilla))
        _activar_update_fields(doc)
        return doc
    nombre = nombre if nombre in ESTILOS else "formal"
    ruta = DIR_ESTILOS / f"{nombre}.docx"
    if not ruta.exists():
        crear_plantilla(nombre, ruta)
    doc = Document(str(ruta))
    cuerpo = doc.element.body
    for hijo in list(cuerpo):
        if hijo.tag != qn("w:sectPr"):
            cuerpo.remove(hijo)
    _activar_update_fields(doc)
    return doc
