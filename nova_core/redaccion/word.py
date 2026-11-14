"""Piezas de Word: tablas sobrias, texto con **negrita**/*cursiva*/`codigo`, Markdown -> Word, portadas y PDF."""

import contextlib
import re
import shutil
import subprocess
from pathlib import Path

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .estilos import TEMAS

RE_INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^*\s][^*]*\*)")
DAFO_NOMBRES = {
    "D": "Debilidades",
    "A": "Amenazas",
    "F": "Fortalezas",
    "O": "Oportunidades",
}


def sombra(celda, color: str | None) -> None:
    if not color:
        return
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    celda._tc.get_or_add_tcPr().append(shd)


def _run(
    parrafo,
    texto: str,
    tam: float,
    color: str | None = None,
    negrita: bool = False,
    fuente: str | None = None,
):
    r = parrafo.add_run(texto)
    r.bold, r.font.size = negrita or None, Pt(tam)
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    if fuente:
        r.font.name = fuente
    return r


def texto_rico(parrafo, texto: str, negrita: bool = False) -> None:
    for trozo in RE_INLINE.split(texto):
        if not trozo:
            continue
        if trozo.startswith("**") and trozo.endswith("**") and len(trozo) > 4:
            parrafo.add_run(trozo[2:-2]).bold = True
        elif trozo.startswith("`") and trozo.endswith("`"):
            r = parrafo.add_run(trozo[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
        elif trozo.startswith("*") and trozo.endswith("*") and len(trozo) > 2:
            r = parrafo.add_run(trozo[1:-1])
            r.italic = True
            r.bold = negrita or None
        else:
            parrafo.add_run(trozo).bold = negrita or None


def _bordes(celda, ver: bool = True, color: str = "000000") -> None:
    tcpr = celda._tc.get_or_add_tcPr()
    bordes = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), "single" if ver else "nil")
        if ver:
            b.set(qn("w:sz"), "4")
            b.set(qn("w:color"), color)
        bordes.append(b)
    tcpr.append(bordes)


def repetir_cabecera(fila) -> None:
    trpr = fila._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trpr.append(el)


def tabla(
    doc,
    filas: list[list[str]],
    anchos_cm: list[float] | None = None,
    derecha: set[int] | None = None,
    cabecera: bool = True,
    bordes: bool = True,
    tamano: float | None = 10,
    tema: str | None = None,
):
    """Tabla con bordes finos y cabecera en negrita que se repite en cada pagina.
    tema=None: blanco y negro. tema="moderno": cabecera azul marino con texto blanco y filas alternas."""
    colores = TEMAS.get(tema, TEMAS[None])
    derecha = derecha or set()
    columnas = max(len(f) for f in filas)
    t = doc.add_table(rows=len(filas), cols=columnas)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = anchos_cm is None
    for i, datos in enumerate(filas):
        fila = t.rows[i]
        if i == 0 and cabecera:
            repetir_cabecera(fila)
        for j in range(columnas):
            celda = fila.cells[j]
            if anchos_cm and i == 0:
                t.columns[j].width = Cm(
                    anchos_cm[j]
                )  # Word lee el ancho de la rejilla, no solo el de la celda
            if anchos_cm:
                celda.width = Cm(anchos_cm[j])
            _bordes(celda, bordes, colores["borde"])
            es_cabecera = i == 0 and cabecera
            sombra(
                celda,
                colores["cabecera"]
                if es_cabecera
                else (colores["alterna"] if i % 2 else None),
            )
            p = celda.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.first_line_indent = None
            if j in derecha:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            texto_rico(
                p, datos[j] if j < len(datos) else "", negrita=(i == 0 and cabecera)
            )
            for r in p.runs:
                if tamano:
                    r.font.size = Pt(tamano)
                if es_cabecera and tema:
                    r.font.color.rgb = RGBColor.from_string(colores["texto_cabecera"])
    return t


def dafo(doc, lineas: list[str], tema: str | None = None) -> None:
    """Bloque :::dafo -> cuadro 2x2 (Debilidades/Amenazas arriba, Fortalezas/Oportunidades abajo).
    Lineas: 'D: texto' (una por punto) o 'Debilidades:' seguido de '- punto'."""
    puntos: dict[str, list[str]] = {k: [] for k in "DAFO"}
    actual = None
    for linea in lineas:
        limpia = linea.strip()
        if m := re.match(
            r"(?i)^(D|A|F|O|debilidades|amenazas|fortalezas|oportunidades)\s*:\s*(.*)$",
            limpia,
        ):
            actual = m.group(1)[0].upper()
            if m.group(2).strip():
                puntos[actual].append(m.group(2).strip())
        elif actual and (m := re.match(r"^[-*•]\s*(.+)", limpia)):
            puntos[actual].append(m.group(1).strip())
    colores = TEMAS.get(tema, TEMAS[None])["dafo"]
    t = doc.add_table(rows=2, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for celda, letra, origen in zip(
        (t.cell(0, 0), t.cell(0, 1), t.cell(1, 0), t.cell(1, 1)),
        "DAFO",
        ("internas", "externas", "internas", "externas"),
    ):
        fondo, tinta = colores[letra]
        sombra(celda, fondo)
        celda.width = Cm(8)
        _run(
            celda.paragraphs[0],
            f"{DAFO_NOMBRES[letra].upper()} ({origen})",
            11,
            tinta,
            True,
        )
        for n, punto in enumerate(puntos[letra] or ["[PENDIENTE]"], start=1):
            p = celda.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            texto_rico(p, f"{letra}{n}. {punto}")
            for r in p.runs:
                r.font.size = Pt(9.5)
    doc.add_paragraph()


def cartel(doc, lineas: list[str], tema: str | None = None) -> None:
    """Bloque :::cartel -> anuncio visual. '# Titular', texto suelto = subtitulo, '- Pilar | explicacion', '> pie'."""
    titular, subtitulo, pilares, pie = "", [], [], []
    for linea in lineas:
        limpia = linea.strip()
        if not limpia:
            continue
        if m := re.match(r"^#+\s*(.+)", limpia):
            titular = m.group(1)
        elif m := re.match(r"^[-*•]\s*(.+)", limpia):
            nombre, _, texto = m.group(1).partition("|")
            pilares.append((nombre.strip(" *"), texto.strip()))
        elif limpia.startswith(">"):
            pie.append(limpia.lstrip("> "))
        else:
            subtitulo.append(limpia)
    c = TEMAS.get(tema, TEMAS[None])

    def banda(color, grande, pequenos):
        t = doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        celda = t.rows[0].cells[0]
        sombra(celda, color)
        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p, grande, 14 if pequenos is subtitulo else 11, "FFFFFF", True, "Segoe UI")
        for texto in pequenos:
            q = celda.add_paragraph()
            q.alignment = WD_ALIGN_PARAGRAPH.CENTER
            texto_rico(q, texto)
            for r in q.runs:
                r.font.size, r.font.color.rgb = Pt(10.5), RGBColor.from_string("FFFFFF")

    banda(c["cartel"], titular or "[PENDIENTE: titular]", subtitulo)
    if pilares:
        t = doc.add_table(rows=1, cols=len(pilares))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for celda, (nombre, texto) in zip(t.rows[0].cells, pilares):
            sombra(celda, c["pilar"])
            p = celda.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _run(p, nombre, 11.5, c["pilar_texto"], True, "Segoe UI")
            if texto:
                q = celda.add_paragraph()
                q.alignment = WD_ALIGN_PARAGRAPH.CENTER
                texto_rico(q, texto)
                for r in q.runs:
                    r.font.size = Pt(9.5)
    if pie:
        banda(c["cartel_2"], pie[0], pie[1:])
    doc.add_paragraph()


def _filas_md(lineas: list[str]) -> list[list[str]]:
    filas = []
    for linea in lineas:
        partes = [p.strip() for p in linea.strip().strip("|").split("|")]
        if partes and all(re.fullmatch(r":?-{2,}:?", p) for p in partes):
            continue
        filas.append(partes)
    return filas


def _es_numero(texto: str) -> bool:
    return bool(
        re.fullmatch(r"[\s\w/$€.]*?[\d.,]+\s*%?", texto.replace("**", "").strip())
    ) and any(c.isdigit() for c in texto)


def markdown_a_word(
    doc, md: str, estilo_cuerpo: str = "Cuerpo", tema: str | None = None
) -> None:
    """Markdown sencillo -> estilos de la plantilla (### subtitulo, listas, > cita, tablas, ```codigo```).
    Bloques especiales:  :::dafo ... :::   y   :::cartel ... :::   (ver dafo() y cartel())."""
    lineas = md.splitlines()
    i = 0
    while i < len(lineas):
        linea = lineas[i].rstrip()
        limpia = linea.strip()
        if m := re.match(r"^:::\s*(dafo|cartel)\s*$", limpia, re.IGNORECASE):
            bloque = []
            i += 1
            while i < len(lineas) and lineas[i].strip() != ":::":
                bloque.append(lineas[i])
                i += 1
            i += 1
            (dafo if m.group(1).lower() == "dafo" else cartel)(doc, bloque, tema)
            continue
        if limpia.startswith("```"):
            i += 1
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                doc.add_paragraph(lineas[i].rstrip() or " ", style="Codigo")
                i += 1
            i += 1
            doc.add_paragraph()
            continue
        if limpia.startswith("|"):
            bloque = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                bloque.append(lineas[i])
                i += 1
            filas = _filas_md(bloque)
            if filas:
                derecha = {
                    j
                    for j in range(len(filas[0]))
                    if all(_es_numero(f[j]) for f in filas[1:] if j < len(f) and f[j])
                }
                tabla(doc, filas, derecha=derecha, tema=tema)
                doc.add_paragraph()
            continue
        i += 1
        if not limpia:
            continue
        if m := re.match(r"^(#{3,6})\s+(.*)", limpia):
            doc.add_heading(
                m.group(2).strip("* "), level=2 if len(m.group(1)) == 3 else 3
            )  # APA: nivel 2 bajo cada seccion
        elif re.match(r"^[-*•]\s+", limpia):
            texto_rico(
                doc.add_paragraph(style="List Bullet"), re.sub(r"^[-*•]\s+", "", limpia)
            )
        elif re.match(r"^\d+[.)]\s+", limpia):
            texto_rico(
                doc.add_paragraph(style="List Number"),
                re.sub(r"^\d+[.)]\s+", "", limpia),
            )
        elif limpia.startswith(">"):
            texto_rico(doc.add_paragraph(style="Quote"), limpia.lstrip("> "))
        else:
            texto_rico(doc.add_paragraph(style=estilo_cuerpo), limpia)


def salto_pagina(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def portada(doc, guion: dict, tipo_portada: str) -> None:
    """formal: titulo, subtitulo y datos; apa: portada de estudiante (APA 7); cabecera: bloque compacto arriba."""
    centrado = WD_ALIGN_PARAGRAPH.CENTER
    if tipo_portada == "cabecera":
        p = doc.add_paragraph(guion.get("titulo", "").upper(), style="Title")
        p.alignment = centrado
        if guion.get("subtitulo"):
            doc.add_paragraph(guion["subtitulo"], style="Subtitle").alignment = centrado
        datos = []
        for claves, etiqueta in (
            (("modulo", "asignatura"), "Módulo"),
            (("autor",), "Alumno"),
            (("fecha",), ""),
        ):
            valor = next((guion[k] for k in claves if guion.get(k)), None)
            if valor:
                datos.append(f"{etiqueta}: {valor}" if etiqueta else str(valor))
        if datos:
            p = doc.add_paragraph("  |  ".join(datos), style="Nota")
            p.alignment = centrado
            p.runs[0].italic = True
            p.paragraph_format.space_after = Pt(14)
        return
    if tipo_portada == "apa":
        for _ in range(3):
            doc.add_paragraph()
        p = doc.add_paragraph()
        p.alignment = centrado
        p.add_run(guion.get("titulo", "")).bold = True
        doc.add_paragraph()
        # se aceptan los nombres que suele usar Nova (centro, curso, modulo, docente)
        for claves in (
            ("autor",),
            ("institucion", "centro"),
            ("curso", "ciclo"),
            ("asignatura", "modulo"),
            ("profesor", "docente"),
            ("fecha",),
        ):
            valor = next((guion[k] for k in claves if guion.get(k)), None)
            if valor:
                p = doc.add_paragraph(str(valor))
                p.alignment = centrado
        salto_pagina(doc)
        return
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph(guion.get("titulo", ""), style="Title")
    p.alignment = centrado
    if guion.get("subtitulo"):
        p = doc.add_paragraph(guion["subtitulo"], style="Subtitle")
        p.alignment = centrado
    for _ in range(10):
        doc.add_paragraph()
    for clave, etiqueta in (
        ("autor", "Elaborado por"),
        ("cliente_nombre", "Para"),
        ("fecha", "Fecha"),
        ("version", "Versión"),
    ):
        if guion.get(clave):
            p = doc.add_paragraph()
            p.alignment = centrado
            p.add_run(f"{etiqueta}: ").bold = True
            p.add_run(str(guion[clave]))
    salto_pagina(doc)


def a_pdf(docx: Path) -> Path | None:
    """Word (identico al .docx) -> LibreOffice. Devuelve la ruta del PDF o None."""
    pdf = docx.with_suffix(".pdf")
    pdf.unlink(missing_ok=True)
    ruta_doc, ruta_pdf = str(docx).replace("'", "''"), str(pdf).replace("'", "''")
    ps = (
        "$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
        f"try {{ $d = $w.Documents.Open('{ruta_doc}', $false, $true); $d.ExportAsFixedFormat('{ruta_pdf}', 17); "
        "$d.Close($false) } finally { $w.Quit() }"
    )
    with contextlib.suppress(Exception):
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            timeout=180,
        )
    if pdf.exists():
        return pdf
    soffice = shutil.which("soffice") or next(
        (
            str(x)
            for x in (Path("C:/Program Files/LibreOffice/program/soffice.exe"),)
            if x.exists()
        ),
        None,
    )
    if soffice:
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(pdf.parent),
                str(docx),
            ],
            capture_output=True,
            timeout=180,
        )
    return pdf if pdf.exists() else None


def hueco(doc):
    """Separacion pequena (un parrafo vacio de 9 pt, sin espacio despues)."""
    p = doc.add_paragraph(style="Nota")
    p.paragraph_format.space_after = Pt(0)
    return p
