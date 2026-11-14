"""
Redactor Local de Documentos y Memorias Tecnicas para Nova (0 Tokens de Nube).

Genera documentos tecnicos y academicos completos en local usando Ollama (Capa 0: Qwen).
Soporta exportacion a Markdown (.md) y Microsoft Word (.docx) con maquetacion profesional:
- Normas APA 7ma Edicion oficial (portada para estudiantes, margenes de 1 pulgada, interlineado y jerarquia de encabezados).
- Tema Ejecutivo (paleta corporativa Navy/Slate, tablas coloreadas, cajas de llamada y pie de pagina dinamico).
- Tema Moderno (estilo minimalista Tech/Teal).
- Tema Clasico (estilo editorial formal Georgia/Crimson).

Uso:
    python redactor.py --escaleta guion.json --salida Memoria.docx --tema apa
    python redactor.py --escaleta guion.json --salida Memoria.docx --tema ejecutivo
    python redactor.py --prompt "Redacta introduccion formal para practica de PSP" --salida intro.docx
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # ollama_comun vive al lado
DOCUMENTOS_GENERADOS = Path.home() / ".gemini" / "antigravity" / "documentos_generados"  # sincronizada con Drive

from ollama_comun import ensure_ollama_service

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

# Configuracion de Temas y Paletas de Diseno
TEMAS = {
    "apa": {
        "nombre": "APA 7ma Edición Oficial",
        "fuente_principal": "Times New Roman",
        "fuente_titulos": "Times New Roman",
        "tamano_cuerpo": 12,
        "interlineado": 2.0,
        "espacio_despues": 0,
        "sangria_primera_linea": 0.5,
        "color_titulo": (0, 0, 0),
        "color_subtitulo": (0, 0, 0),
        "color_texto": (0, 0, 0),
        "color_acento": (0, 0, 0),
        "color_fondo_tabla": "F2F2F2",
        "color_header_tabla": "FFFFFF",
        "texto_header_tabla": (0, 0, 0),
        "portada_estudiante": True,
        "numeracion_superior_derecha": True,
    },
    "ejecutivo": {
        "nombre": "Corporativo Ejecutivo",
        "fuente_principal": "Calibri",
        "fuente_titulos": "Segoe UI",
        "tamano_cuerpo": 11,
        "interlineado": 1.15,
        "espacio_despues": 5,
        "sangria_primera_linea": 0.0,
        "color_titulo": (15, 34, 64),  # #0F2240 Navy
        "color_subtitulo": (27, 85, 155),  # #1B559B Azul Corporativo
        "color_texto": (33, 37, 41),  # #212529 Texto base oscuro
        "color_acento": (194, 65, 12),  # #C2410C Ambar
        "color_fondo_tabla": "F8F9FA",
        "color_header_tabla": "0F2240",
        "texto_header_tabla": (255, 255, 255),
        "portada_estudiante": False,
        "numeracion_superior_derecha": False,
    },
    "moderno": {
        "nombre": "Moderno Tech Minimalista",
        "fuente_principal": "Arial",
        "fuente_titulos": "Segoe UI",
        "tamano_cuerpo": 10.5,
        "interlineado": 1.2,
        "espacio_despues": 6,
        "sangria_primera_linea": 0.0,
        "color_titulo": (15, 23, 42),  # #0F172A Slate
        "color_subtitulo": (13, 148, 136),  # #0D9488 Teal
        "color_texto": (51, 65, 85),  # #334155
        "color_acento": (13, 148, 136),
        "color_fondo_tabla": "F1F5F9",
        "color_header_tabla": "0F172A",
        "texto_header_tabla": (255, 255, 255),
        "portada_estudiante": False,
        "numeracion_superior_derecha": False,
    },
    "clasico": {
        "nombre": "Editorial Clásico Formal",
        "fuente_principal": "Georgia",
        "fuente_titulos": "Georgia",
        "tamano_cuerpo": 11,
        "interlineado": 1.3,
        "espacio_despues": 4,
        "sangria_primera_linea": 0.3,
        "color_titulo": (44, 62, 80),  # #2C3E50 Charcoal
        "color_subtitulo": (123, 36, 28),  # #7B241C Crimson
        "color_texto": (40, 40, 40),
        "color_acento": (123, 36, 28),
        "color_fondo_tabla": "FAF9F6",
        "color_header_tabla": "2C3E50",
        "texto_header_tabla": (255, 255, 255),
        "portada_estudiante": True,
        "numeracion_superior_derecha": False,
    },
}


def _modelo_nova(
    clave: str = "coder", defecto: str = "qwen3.5:9b"  # 09/11: el viejo qwen2.5-coder-nova2026:v4 ya no existe
) -> str:
    """Obtiene el nombre oficial del modelo Qwen local configurado."""
    try:
        ruta = Path.home() / ".gemini" / "antigravity" / "scripts" / "nova_modelos.json"
        return json.loads(ruta.read_text(encoding="utf-8"))[clave]
    except Exception:
        return defecto


def consultar_ollama(
    prompt: str, sistema: str = "", modelo: str | None = None, max_tokens: int = 2000
) -> str:
    """Qwen local a 0 tokens de nube via generar_qwen (08/11: think=False, num_ctx explicito y keep_alive; antes
    keep_alive=0 recargaba el modelo en cada seccion y qwen3.5 podia gastar los tokens pensando)."""
    from ollama_comun import generar_qwen

    ensure_ollama_service()
    try:
        texto, cortado = generar_qwen(prompt, modelo or _modelo_nova("coder"), sistema=sistema, num_predict=max_tokens,
                                      num_ctx=8192, temperatura=0.35, timeout=600)
    except Exception as e:
        sys.stderr.write(f"[error] No se pudo conectar con Ollama: {e}\n")
        sys.exit(1)
    return texto.strip()


def redactar_documento(escaleta: dict, modelo: str | None = None) -> list[dict]:
    """Genera cada seccion del documento llamando a Ollama por bloques."""
    titulo_doc = escaleta.get("titulo", "Documento Tecnico")
    autor = escaleta.get("autor", "Alexander Martinez")
    asignatura = escaleta.get("asignatura", "")
    tono = escaleta.get("tono", "academico, riguroso y formal")
    sistema = (
        f"Eres un redactor tecnico senior y academico de elite. "
        f"Escribe en tono {tono}, con explicaciones directas, profundas y bien estructuradas, "
        f"utilizando parrafos fluidos, tablas conceptuales en formato Markdown cuando proceda, "
        f"y sin introducciones vacias ni rodeos meta."
    )

    secciones_redactadas = []
    lista_secciones = escaleta.get("secciones", [])

    print(
        f"[*] Redactando '{titulo_doc}' ({len(lista_secciones)} secciones con Capa 0 Ollama)..."
    )

    for idx, sec in enumerate(lista_secciones, start=1):
        nombre_sec = sec.get("titulo", f"Seccion {idx}")
        puntos = sec.get("puntos", [])
        puntos_txt = (
            "\n".join(f"- {p}" for p in puntos)
            if puntos
            else "Desarrolla el contenido tecnico correspondiente con detalle."
        )

        prompt_seccion = (
            f"Documento: '{titulo_doc}'\n"
            f"Modulo/Asignatura: '{asignatura}' | Autor: '{autor}'\n"
            f"Seccion actual a redactar: '{nombre_sec}'\n\n"
            f"Puntos obligatorios a desarrollar:\n{puntos_txt}\n\n"
            f"Instrucciones de redaccion:\n"
            f"- Desarrolla cada punto en parrafos academicos fluidos y solidos.\n"
            f"- Si procede comparar elementos, usa una tabla en formato Markdown (| Col 1 | Col 2 |).\n"
            f"- Si hay conceptos clave, destácalos con listas o citas (> concepto).\n"
            f"- Entrega el texto listo para publicacion."
        )

        print(f"  -> [{idx}/{len(lista_secciones)}] Redactando: {nombre_sec}...")
        contenido = consultar_ollama(prompt_seccion, sistema=sistema, modelo=modelo)
        secciones_redactadas.append({"titulo": nombre_sec, "contenido": contenido})

    return secciones_redactadas


def exportar_markdown(escaleta: dict, secciones: list[dict], ruta_salida: Path) -> None:
    """Guarda el documento en formato Markdown estandar."""
    lineas = [f"# {escaleta.get('titulo', 'Documento Tecnico')}\n"]
    metas = []
    if escaleta.get("autor"):
        metas.append(f"**Autor:** {escaleta['autor']}")
    if escaleta.get("asignatura"):
        metas.append(f"**Asignatura:** {escaleta['asignatura']}")
    if metas:
        lineas.append(" | ".join(metas) + "\n\n---\n")

    for sec in secciones:
        lineas.append(f"## {sec['titulo']}\n\n{sec['contenido']}\n")

    ruta_salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"[ok] Guardado en Markdown: {ruta_salida}")


def _aplicar_formato_run(
    run,
    texto: str,
    config: dict,
    bold: bool = False,
    italic: bool = False,
    color=None,
    font_name=None,
    size_pt=None,
):
    """Configura los atributos visuales de un run de texto."""
    from docx.shared import Pt, RGBColor

    run.text = texto
    run.font.name = font_name or config["fuente_principal"]
    run.font.size = Pt(size_pt or config["tamano_cuerpo"])
    col = color or config["color_texto"]
    run.font.color.rgb = RGBColor(*col)
    run.bold = bold
    run.italic = italic


def _procesar_parrafo_con_estilos(
    p,
    texto_linea: str,
    config: dict,
    size_pt=None,
    color=None,
    font_name=None,
    bold: bool = False,
    italic: bool = False,
):
    """Parsea markdown basico (**negrita**, *cursiva*) dentro de un parrafo."""
    tokens = re.split(r"(\*\*.*?\*\*|\*.*?\*)", texto_linea)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            r = p.add_run()
            _aplicar_formato_run(
                r,
                token[2:-2],
                config,
                bold=True,
                italic=italic,
                size_pt=size_pt,
                color=color,
                font_name=font_name,
            )
        elif token.startswith("*") and token.endswith("*") and len(token) >= 3:
            r = p.add_run()
            _aplicar_formato_run(
                r,
                token[1:-1],
                config,
                bold=bold,
                italic=True,
                size_pt=size_pt,
                color=color,
                font_name=font_name,
            )
        else:
            r = p.add_run()
            _aplicar_formato_run(
                r,
                token,
                config,
                bold=bold,
                italic=italic,
                size_pt=size_pt,
                color=color,
                font_name=font_name,
            )


def _insertar_numero_pagina_xml(run):
    """Inserta el campo nativo de numero de pagina dinamico de Word."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    fld1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
    instr = parse_xml(
        f'<w:instrText {nsdecls("w")} xml:space="preserve"> PAGE </w:instrText>'
    )
    fld2 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>')
    fld3 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>')
    run._r.append(fld1)
    run._r.append(instr)
    run._r.append(fld2)
    run._r.append(fld3)


def _configurar_encabezado_pie(doc, escaleta: dict, config: dict, clave_tema: str):
    """Configura los encabezados y pies de pagina segun la norma del tema."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    section = doc.sections[0]

    # En APA 7 para estudiantes: numero de pagina arriba a la derecha
    if config.get("numeracion_superior_derecha", False):
        header = section.header
        p_head = header.paragraphs[0]
        p_head.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_head = p_head.add_run()
        r_head.font.name = config["fuente_principal"]
        r_head.font.size = Pt(config["tamano_cuerpo"])
        r_head.font.color.rgb = RGBColor(*config["color_texto"])
        _insertar_numero_pagina_xml(r_head)
    else:
        # En Ejecutivo y Moderno: pie de pagina corporativo con titulo a la izquierda y pagina a la derecha
        footer = section.footer
        p_foot = footer.paragraphs[0]
        p_foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_titulo = p_foot.add_run(escaleta.get("titulo", "Documento") + "  |  Página ")
        r_titulo.font.name = config["fuente_principal"]
        r_titulo.font.size = Pt(9)
        r_titulo.font.italic = True
        r_titulo.font.color.rgb = RGBColor(110, 120, 135)

        r_pag = p_foot.add_run()
        r_pag.font.name = config["fuente_principal"]
        r_pag.font.size = Pt(9)
        r_pag.font.bold = True
        r_pag.font.color.rgb = RGBColor(110, 120, 135)
        _insertar_numero_pagina_xml(r_pag)


def _crear_portada_apa(doc, escaleta: dict, config: dict):
    """Crea la portada oficial para estudiantes segun normas APA 7ma edicion."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    titulo = escaleta.get("titulo", "Título del Trabajo Académico")
    autor = escaleta.get("autor", "Alexander Martínez")
    institucion = escaleta.get("institucion", "Universidad / Centro de Estudios")
    asignatura = escaleta.get("asignatura", "Módulo de Especialización")
    profesor = escaleta.get("profesor", "Profesor / Docente")
    fecha = escaleta.get("fecha", "Noviembre 2026")

    # 3 a 4 saltos de linea iniciales segun APA 7
    for _ in range(4):
        doc.add_paragraph()

    # Titulo del documento (Negrita, Centrado)
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.line_spacing = config["interlineado"]
    p_tit.paragraph_format.space_after = Pt(24)
    r_tit = p_tit.add_run(titulo)
    _aplicar_formato_run(
        r_tit,
        titulo,
        config,
        bold=True,
        size_pt=14,
        font_name=config["fuente_titulos"],
        color=config["color_titulo"],
    )

    # Elementos del estudiante
    elementos = [
        autor,
        institucion,
        asignatura,
        profesor,
        fecha,
    ]

    for elem in elementos:
        if not elem:
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = config["interlineado"]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(elem)
        _aplicar_formato_run(
            r,
            elem,
            config,
            size_pt=config["tamano_cuerpo"],
            color=config["color_texto"],
        )

    # Salto de pagina estricto APA
    doc.add_page_break()


def _crear_portada_ejecutiva(doc, escaleta: dict, config: dict):
    """Crea una portada moderna y corporativa para informes de empresa."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    titulo = escaleta.get("titulo", "INFORME EJECUTIVO")
    subtitulo = escaleta.get(
        "subtitulo", escaleta.get("asignatura", "Documento Estratégico y Técnico")
    )
    autor = escaleta.get("autor", "Alexander Martínez")
    fecha = escaleta.get("fecha", "2026")

    for _ in range(2):
        doc.add_paragraph()

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tit.paragraph_format.space_before = Pt(0)
    p_tit.paragraph_format.space_after = Pt(6)
    r_tit = p_tit.add_run(titulo)
    _aplicar_formato_run(
        r_tit,
        titulo,
        config,
        bold=True,
        size_pt=20,
        font_name=config["fuente_titulos"],
        color=config["color_titulo"],
    )

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run(subtitulo)
    _aplicar_formato_run(
        r_sub,
        subtitulo,
        config,
        bold=True,
        size_pt=12,
        font_name=config["fuente_titulos"],
        color=config["color_subtitulo"],
    )

    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_after = Pt(28)
    meta_txt = f"Preparado por: {autor}  |  Fecha: {fecha}  |  Versión 4.1"
    r_meta = p_meta.add_run(meta_txt)
    _aplicar_formato_run(
        r_meta, meta_txt, config, italic=True, size_pt=10, color=(110, 120, 135)
    )

    doc.add_page_break()


def _construir_tabla_docx(doc, lineas_tabla: list[str], config: dict):
    """Convierte lineas de tabla en Markdown a una tabla nativa de Word formateada."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    from docx.shared import Pt

    filas = []
    for linea in lineas_tabla:
        partes = [p.strip() for p in linea.strip().strip("|").split("|")]
        # Ignorar separador |---|---|
        if partes and all(re.match(r"^:?-+:?$", p) for p in partes):
            continue
        if any(partes):
            filas.append(partes)

    if not filas:
        return

    num_filas = len(filas)
    num_cols = max(len(f) for f in filas)

    tabla = doc.add_table(rows=num_filas, cols=num_cols)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 09/11 (Claude): anchos de columna segun el contenido (antes todas iguales: una descripcion larga quedaba
    # estrechisima y la tabla se iba a varias paginas). Ancho util 6,5" (carta con margenes de 1").
    from docx.shared import Inches
    pesos = []
    for c in range(num_cols):
        textos = [f[c].replace("**", "") for f in filas if c < len(f)]
        largo = max((len(t) for t in textos), default=4)
        palabra = max((len(p) for t in textos for p in t.split()), default=3)  # nunca partir un numero o palabra
        pesos.append(max(palabra * 1.25 + 3, min(45, largo * 0.7)))
    tabla.autofit = False
    for c in range(num_cols):
        ancho = Inches(6.5 * pesos[c] / sum(pesos))
        for fila_tabla in tabla.rows:
            fila_tabla.cells[c].width = ancho

    for row_idx, fila_datos in enumerate(filas):
        row = tabla.rows[row_idx]
        es_header = row_idx == 0
        bg_color = (
            config["color_header_tabla"]
            if es_header
            else (config["color_fondo_tabla"] if row_idx % 2 == 1 else "FFFFFF")
        )

        for col_idx in range(num_cols):
            cell = row.cells[col_idx]
            texto_celda = fila_datos[col_idx] if col_idx < len(fila_datos) else ""

            # Sombreado de celda
            tcPr = cell._tc.get_or_add_tcPr()
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
            tcPr.append(shd)

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)

            color_texto = (
                config["texto_header_tabla"] if es_header else config["color_texto"]
            )
            # 09/11 (Claude): **negrita** dentro de las celdas (antes salian los asteriscos tal cual)
            for k, trozo in enumerate(re.split(r"\*\*(.+?)\*\*", texto_celda)):
                if not trozo:
                    continue
                _aplicar_formato_run(
                    p.add_run(),
                    trozo,
                    config,
                    bold=es_header or k % 2 == 1,
                    size_pt=config["tamano_cuerpo"] - 1,
                    color=color_texto,
                )

    doc.add_paragraph()  # Espacio separador


def exportar_docx(
    escaleta: dict,
    secciones: list[dict],
    ruta_salida: Path,
    tema_nombre: str = "apa",
    interlineado_custom: float | None = None,
) -> None:
    """Guarda el documento formateado como Microsoft Word (.docx) con maquetacion profesional."""
    try:
        import docx
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Inches, Pt
    except ImportError:
        sys.stderr.write(
            "[error] python-docx no esta disponible. Exportando a Markdown en su lugar.\n"
        )
        exportar_markdown(escaleta, secciones, ruta_salida.with_suffix(".md"))
        return

    clave_tema = tema_nombre.lower() if tema_nombre.lower() in TEMAS else "apa"
    config = TEMAS[clave_tema].copy()

    if interlineado_custom:
        config["interlineado"] = interlineado_custom

    doc = docx.Document()

    # Margenes normativos: 1 pulgada (2.54 cm) en todos los lados
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)

    # Configurar Encabezados y Numeracion
    _configurar_encabezado_pie(doc, escaleta, config, clave_tema)

    # Crear Portada segun el Tema ("sin_portada": true en la escaleta para cartas, cotizaciones o documentos de 1 hoja)
    if escaleta.get("sin_portada"):
        pass
    elif config.get("portada_estudiante", False):
        _crear_portada_apa(doc, escaleta, config)
    else:
        _crear_portada_ejecutiva(doc, escaleta, config)

    # Procesar Cada Seccion
    for sec in secciones:
        titulo_sec = sec.get("titulo", "Sección")
        contenido = sec.get("contenido", "")

        # Encabezado Nivel 1
        p_h1 = doc.add_paragraph()
        p_h1.paragraph_format.keep_with_next = True
        p_h1.paragraph_format.space_before = Pt(16)
        p_h1.paragraph_format.space_after = Pt(6)

        if clave_tema == "apa":
            # APA 7 Nivel 1: Centrado, Negrita
            p_h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            p_h1.alignment = WD_ALIGN_PARAGRAPH.LEFT

        r_h1 = p_h1.add_run(titulo_sec)
        _aplicar_formato_run(
            r_h1,
            titulo_sec,
            config,
            bold=True,
            size_pt=14,
            font_name=config["fuente_titulos"],
            color=config["color_titulo"],
        )

        # Procesar bloques de contenido
        lineas_raw = contenido.split("\n")
        buffer_tabla = []
        en_tabla = False

        for linea in lineas_raw:
            linea_str = linea.strip()

            # Deteccion de tablas Markdown (| col | col |)
            if linea_str.startswith("|") and linea_str.endswith("|"):
                en_tabla = True
                buffer_tabla.append(linea_str)
                continue
            if en_tabla:
                en_tabla = False
                _construir_tabla_docx(doc, buffer_tabla, config)
                buffer_tabla = []

            if not linea_str:
                continue

            # Deteccion de Subtitulos Nivel 2 (## Subtitulo o 1.1 Subtitulo)
            if (
                linea_str.startswith("### ")
                or linea_str.startswith("## ")
                or re.match(r"^\d+\.\d+\.?\s+", linea_str)
            ):
                sub_txt = re.sub(r"^#+\s+", "", linea_str).strip()
                p_sub = doc.add_paragraph()
                p_sub.paragraph_format.keep_with_next = True
                p_sub.paragraph_format.space_before = Pt(12)
                p_sub.paragraph_format.space_after = Pt(4)
                p_sub.alignment = WD_ALIGN_PARAGRAPH.LEFT

                r_sub = p_sub.add_run(sub_txt)
                _aplicar_formato_run(
                    r_sub,
                    sub_txt,
                    config,
                    bold=True,
                    italic=(clave_tema == "apa" and linea_str.startswith("### ")),
                    size_pt=12,
                    font_name=config["fuente_titulos"],
                    color=config["color_subtitulo"],
                )
                continue

            # Deteccion de Listas con Viñetas (- o *)
            if linea_str.startswith("- ") or linea_str.startswith("* "):
                elem_txt = linea_str.lstrip("-* ").strip()
                p_list = doc.add_paragraph(style="List Bullet")
                p_list.paragraph_format.space_before = Pt(0)
                p_list.paragraph_format.space_after = Pt(2)
                p_list.paragraph_format.line_spacing = config["interlineado"]
                _procesar_parrafo_con_estilos(p_list, elem_txt, config)
                continue

            # Deteccion de Citas o Llamadas (> texto)
            if linea_str.startswith("> "):
                cita_txt = linea_str[2:].strip()
                p_cita = doc.add_paragraph()
                p_cita.paragraph_format.left_indent = Inches(0.5)
                p_cita.paragraph_format.right_indent = Inches(0.5)
                p_cita.paragraph_format.space_before = Pt(4)
                p_cita.paragraph_format.space_after = Pt(4)
                p_cita.paragraph_format.line_spacing = config["interlineado"]
                _procesar_parrafo_con_estilos(
                    p_cita, cita_txt, config, italic=True, color=config["color_acento"]
                )
                continue

            # Parrafo regular de cuerpo
            p_cuerpo = doc.add_paragraph()
            p_cuerpo.paragraph_format.line_spacing = config["interlineado"]
            p_cuerpo.paragraph_format.space_after = Pt(config["espacio_despues"])

            # Sangria de primera linea segun APA 7
            if config["sangria_primera_linea"] > 0:
                p_cuerpo.paragraph_format.first_line_indent = Inches(
                    config["sangria_primera_linea"]
                )

            _procesar_parrafo_con_estilos(p_cuerpo, linea_str, config)

        if buffer_tabla:
            _construir_tabla_docx(doc, buffer_tabla, config)

    doc.save(str(ruta_salida))
    print(
        f"[ok] Guardado con éxito en Word con tema '{config['nombre']}': {ruta_salida}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Redactor Local a 0 Tokens de Nube para Nova con Maquetacion Avanzada (APA 7 / Ejecutivo)."
    )
    parser.add_argument(
        "--escaleta",
        "-e",
        help="Ruta al archivo JSON con el guion o escaleta del documento",
    )
    parser.add_argument(
        "--prompt", "-p", help="Prompt directo para una redaccion simple"
    )
    parser.add_argument(
        "--salida", "-s", required=True,
        help="Archivo de salida .docx, .pdf o .md. Si es solo un nombre, se guarda en antigravity\\documentos_generados",
    )
    parser.add_argument(
        "--modelo", "-m", help="Nombre del modelo en Ollama (por defecto el 'coder' de scripts\\nova_modelos.json)"
    )
    parser.add_argument(
        "--tema",
        "-t",
        choices=["apa", "ejecutivo", "moderno", "clasico"],
        default="apa",
        help="Tema de maquetacion Word (apa, ejecutivo, moderno, clasico)",
    )
    parser.add_argument(
        "--interlineado",
        "-i",
        type=float,
        help="Interlineado personalizado (ej: 1.5, 2.0)",
    )
    parser.add_argument(
        "--profesor", help="Nombre del profesor para portada academica APA"
    )
    parser.add_argument(
        "--institucion", help="Institucion o Universidad para portada academica APA"
    )
    parser.add_argument("--fecha", help="Fecha para la portada")
    args = parser.parse_args()
    sys.stderr.write("[aviso] redactor.py es el redactor ANTIGUO. Usa nova_core\\redactar.py (por tipos, formal): "
                     "redactar.py tipos\n")

    ruta_salida = Path(args.salida)
    if not ruta_salida.is_absolute() and ruta_salida.parent == Path("."):
        DOCUMENTOS_GENERADOS.mkdir(parents=True, exist_ok=True)
        ruta_salida = DOCUMENTOS_GENERADOS / ruta_salida.name

    # Caso 1: Prompt directo
    if args.prompt:
        escaleta = {
            "titulo": "Documento Tecnico",
            "secciones": [{"titulo": "Contenido", "puntos": [args.prompt]}],
        }
    # Caso 2: Escaleta JSON
    elif args.escaleta:
        ruta_esc = Path(args.escaleta)
        if not ruta_esc.exists():
            sys.stderr.write(f"[error] No existe el archivo de escaleta: {ruta_esc}\n")
            sys.exit(1)
        escaleta = json.loads(ruta_esc.read_text(encoding="utf-8"))
    else:
        sys.stderr.write(
            "[error] Debes indicar --escaleta <archivo.json> o --prompt <texto>\n"
        )
        sys.exit(1)

    if args.profesor and "profesor" not in escaleta:
        escaleta["profesor"] = args.profesor
    if args.institucion and "institucion" not in escaleta:
        escaleta["institucion"] = args.institucion
    if args.fecha and "fecha" not in escaleta:
        escaleta["fecha"] = args.fecha

    tema_seleccionado = escaleta.get("tema", args.tema)

    secciones = redactar_documento(escaleta, modelo=args.modelo)

    if ruta_salida.suffix.lower() == ".pdf":
        docx = ruta_salida.with_suffix(".docx")
        exportar_docx(escaleta, secciones, docx, tema_nombre=tema_seleccionado, interlineado_custom=args.interlineado)
        exportar_markdown(escaleta, secciones, ruta_salida.with_suffix(".md"))
        motor = docx_a_pdf(docx, ruta_salida)
        print(f"[ok] PDF ({motor}): {ruta_salida}" if motor else "[aviso] No se pudo crear el PDF; queda el .docx")
    elif ruta_salida.suffix.lower() == ".docx":
        exportar_docx(
            escaleta,
            secciones,
            ruta_salida,
            tema_nombre=tema_seleccionado,
            interlineado_custom=args.interlineado,
        )
    else:
        exportar_markdown(escaleta, secciones, ruta_salida)


def docx_a_pdf(docx: Path, pdf: Path) -> str:
    """Word (mejor calidad, respeta el tema) -> LibreOffice -> navegador (desde el .md). Devuelve el motor usado o ''."""
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{docx}'); $d.ExportAsFixedFormat('{pdf}', 17); $d.Close($false); $w.Quit()")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=180)
        if pdf.exists():
            return "Word"
    except Exception:
        pass
    soffice = shutil.which("soffice") or next((str(x) for x in (Path("C:/Program Files/LibreOffice/program/soffice.exe"),) if x.exists()), None)
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf.parent), str(docx)], capture_output=True, timeout=180)
        if pdf.exists():
            return "LibreOffice"
    try:  # ultimo recurso: el .md en HTML sencillo -> PDF con Chromium (Playwright)
        import html as _h
        from playwright.sync_api import sync_playwright
        md = docx.with_suffix(".md").read_text(encoding="utf-8")
        cuerpo = "".join(f"<h1>{_h.escape(l[2:])}</h1>" if l.startswith("# ") else f"<h2>{_h.escape(l[3:])}</h2>" if l.startswith("## ")
                         else f"<h3>{_h.escape(l[4:])}</h3>" if l.startswith("### ") else f"<p>{_h.escape(l)}</p>" if l.strip() else ""
                         for l in md.splitlines())
        pagina = ("<html><head><meta charset='utf-8'><style>body{font-family:Georgia,serif;font-size:12pt;line-height:1.5;margin:2.5cm}"
                  "h1{font-size:22pt}h2{font-size:15pt;margin-top:1.4em}p{text-align:justify}</style></head><body>" + cuerpo + "</body></html>")
        with sync_playwright() as pw:
            b = pw.chromium.launch(); pg = b.new_page(); pg.set_content(pagina); pg.pdf(path=str(pdf), format="A4"); b.close()
        return "navegador" if pdf.exists() else ""
    except Exception:
        return ""


if __name__ == "__main__":
    main()
