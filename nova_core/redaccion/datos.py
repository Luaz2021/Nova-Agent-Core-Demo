"""Documentos de DATOS: presupuesto (lo emites tu) y solicitud de presupuesto (se la pides a un proveedor).

Aqui no escribe la IA: todo sale del guion y las cuentas las hace el codigo. Lo que falte sale como [PENDIENTE: ...]
para que Nova se lo pida a Alexander en vez de inventarlo.
"""

from decimal import Decimal
from pathlib import Path

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from . import estilos, word
from .base import dinero, estilo_numeros, formato_numero

CAMPOS_PERSONA = (
    ("nombre", "nombre o razón social"),
    ("documento", "RUC / NIF / DNI"),
    ("direccion", "dirección"),
    ("contacto", "teléfono o correo"),
)


def _persona(
    guion: dict, clave: str, faltan: list[str], obligatorios=("nombre", "documento")
) -> list[str]:
    datos = guion.get(clave) or {}
    lineas = []
    for campo, etiqueta in CAMPOS_PERSONA:
        valor = str(datos.get(campo, "")).strip()
        if valor:
            lineas.append(valor)
        elif campo in obligatorios:
            lineas.append(f"[PENDIENTE: {etiqueta} del {clave}]")
            faltan.append(f"{clave}.{campo}")
    return lineas


# ---------------------------------------------------------------- presupuesto


def calcular(guion: dict) -> dict:
    """Importe de cada partida, subtotal, descuento, impuesto y total (Decimal, redondeo comercial)."""
    partidas = []
    for n, p in enumerate(guion.get("partidas", []), start=1):
        cantidad = Decimal(str(p.get("cantidad", 1)))
        precio = dinero(p.get("precio", 0))
        partidas.append(
            {
                **p,
                "n": n,
                "cantidad": cantidad,
                "precio": precio,
                "importe": dinero(cantidad * precio),
            }
        )
    subtotal = dinero(sum((p["importe"] for p in partidas), Decimal(0)))
    desc = guion.get("descuento") or {}
    descuento = (
        dinero(subtotal * Decimal(str(desc.get("porcentaje", 0))) / 100)
        if desc.get("porcentaje")
        else dinero(desc.get("importe", 0))
    )
    base = subtotal - descuento
    imp = guion.get("impuesto") or {}
    porcentaje = Decimal(str(imp.get("porcentaje", 0)))
    impuesto = dinero(base * porcentaje / 100)
    return {
        "partidas": partidas,
        "subtotal": subtotal,
        "descuento": descuento,
        "base": base,
        "porcentaje": porcentaje,
        "impuesto": impuesto,
        "total": dinero(base + impuesto),
    }


def comprobar_totales(guion: dict, c: dict) -> list[str]:
    """Si el guion trae un total escrito a mano, avisa si no cuadra con el calculado."""
    avisos = []
    esperado = guion.get("total_esperado")
    if esperado is not None and dinero(esperado) != c["total"]:
        avisos.append(
            f"El total esperado ({esperado}) no cuadra con el calculado ({c['total']}). Revisa las partidas."
        )
    return avisos


def _cant(valor: Decimal) -> str:
    return (
        str(int(valor))
        if valor == valor.to_integral_value()
        else str(valor.normalize())
    )


def presupuesto_docx(guion: dict, ruta: Path) -> list[str]:
    faltan: list[str] = []
    c = calcular(guion)
    num = estilo_numeros(guion)
    moneda = guion.get("moneda", "S/")
    doc = estilos.abrir("formal")

    # Cabecera: emisor a la izquierda, datos del documento a la derecha (sin bordes)
    emisor = _persona(guion, "emisor", faltan)
    derecha = [
        f"**{guion.get('titulo_documento', 'PRESUPUESTO')}**",
        f"Nº {guion.get('numero') or '[PENDIENTE: número]'}",
        f"Fecha: {guion.get('fecha') or '[PENDIENTE: fecha]'}",
    ]
    if guion.get("validez_dias"):
        derecha.append(f"Validez: {guion['validez_dias']} días")
    filas = [
        [
            (f"**{emisor[0]}**" if i == 0 else emisor[i]) if i < len(emisor) else "",
            derecha[i] if i < len(derecha) else "",
        ]
        for i in range(max(len(emisor), len(derecha)))
    ]
    word.tabla(
        doc,
        filas,
        anchos_cm=[10, 6],
        derecha={1},
        cabecera=False,
        bordes=False,
        tamano=10,
    )
    word.hueco(doc)

    p = doc.add_paragraph()
    p.add_run("Cliente").bold = True
    for linea in _persona(guion, "cliente", faltan, obligatorios=("nombre",)):
        doc.add_paragraph(linea).paragraph_format.space_after = Pt(0)
    word.hueco(doc)
    p = doc.add_paragraph()
    p.add_run("Asunto: ").bold = True
    p.add_run(guion.get("asunto") or "[PENDIENTE: asunto]")
    if guion.get("alcance"):
        word.texto_rico(doc.add_paragraph(style="Cuerpo"), guion["alcance"])

    if not c["partidas"]:
        faltan.append("partidas")
    filas = [
        ["Nº", "Descripción", "Cant.", f"P. unit. ({moneda})", f"Importe ({moneda})"]
    ]
    for pa in c["partidas"]:
        desc = pa.get("descripcion") or "[PENDIENTE: descripción]"
        if pa.get("detalle"):
            desc += f"\n{pa['detalle']}"
        filas.append(
            [
                str(pa["n"]),
                desc,
                _cant(pa["cantidad"]),
                formato_numero(pa["precio"], num),
                formato_numero(pa["importe"], num),
            ]
        )
    word.hueco(doc)
    word.tabla(doc, filas, anchos_cm=[0.9, 9.4, 1.2, 2.25, 2.25], derecha={0, 2, 3, 4})

    imp = guion.get("impuesto") or {}
    totales = [["Subtotal", f"{moneda} {formato_numero(c['subtotal'], num)}"]]
    if c["descuento"]:
        totales.append(
            ["Descuento", f"- {moneda} {formato_numero(c['descuento'], num)}"]
        )
    if imp:
        totales.append(
            [
                f"{imp.get('nombre', 'Impuesto')} ({_cant(c['porcentaje'])} %)",
                f"{moneda} {formato_numero(c['impuesto'], num)}",
            ]
        )
    totales.append(["**TOTAL**", f"**{moneda} {formato_numero(c['total'], num)}**"])
    word.hueco(doc)
    t = word.tabla(doc, totales, anchos_cm=[4, 3.5], derecha={0, 1}, cabecera=False)
    t.alignment = WD_TABLE_ALIGNMENT.RIGHT
    if imp.get("nota"):
        doc.add_paragraph(imp["nota"], style="Nota")

    for titulo, clave in (("Condiciones", "condiciones"), ("Observaciones", "notas")):
        if guion.get(clave):
            doc.add_heading(titulo, level=2)
            for linea in guion[clave]:
                word.texto_rico(doc.add_paragraph(style="List Bullet"), linea)

    if guion.get("aceptacion", True):
        # la firma nunca sola en una pagina: arrastra consigo la ultima linea anterior
        doc.paragraphs[-1].paragraph_format.keep_with_next = True
        hueco = doc.add_paragraph()
        hueco.paragraph_format.space_before = Pt(20)
        hueco.paragraph_format.keep_with_next = True
        t = word.tabla(
            doc,
            [
                ["______________________________", "______________________________"],
                [f"{emisor[0]}", "Aceptación del cliente (firma y fecha)"],
            ],
            anchos_cm=[8, 8],
            cabecera=False,
            bordes=False,
            tamano=9,
        )
        for celda in t.rows[0].cells:
            celda.paragraphs[0].paragraph_format.keep_with_next = True
    doc.save(str(ruta))
    return faltan


def presupuesto_xlsx(guion: dict, ruta: Path) -> None:
    """Excel con FORMULAS reales: si cambias una cantidad o un precio, todo se recalcula."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side

    c = calcular(guion)
    moneda = guion.get("moneda", "S/")
    wb = Workbook()
    ws = wb.active
    ws.title = "Presupuesto"
    fino = Side(style="thin", color="000000")
    borde = Border(top=fino, bottom=fino, left=fino, right=fino)
    formato = "#,##0.00"
    ws["A1"] = guion.get("titulo_documento", "PRESUPUESTO")
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Nº {guion.get('numero', '')}   Fecha: {guion.get('fecha', '')}"
    ws["A3"] = f"Emisor: {(guion.get('emisor') or {}).get('nombre', '')}"
    ws["A4"] = f"Cliente: {(guion.get('cliente') or {}).get('nombre', '')}"
    ws["A5"] = f"Asunto: {guion.get('asunto', '')}"
    fila0 = 7
    for col, texto in enumerate(
        ["Nº", "Descripción", "Cant.", f"P. unit. ({moneda})", f"Importe ({moneda})"],
        start=1,
    ):
        celda = ws.cell(fila0, col, texto)
        celda.font, celda.border = Font(bold=True), borde
    for i, pa in enumerate(c["partidas"], start=1):
        f = fila0 + i
        ws.cell(f, 1, pa["n"])
        ws.cell(f, 2, pa.get("descripcion", ""))
        ws.cell(f, 3, float(pa["cantidad"]))
        ws.cell(f, 4, float(pa["precio"])).number_format = formato
        ws.cell(f, 5, f"=ROUND(C{f}*D{f},2)").number_format = formato
        for col in range(1, 6):
            ws.cell(f, col).border = borde
    ultima = fila0 + len(c["partidas"])
    f = ultima + 2
    filas_tot = [("Subtotal", f"=SUM(E{fila0 + 1}:E{ultima})")]
    desc = guion.get("descuento") or {}
    if desc.get("porcentaje"):
        filas_tot.append(
            (
                f"Descuento ({desc['porcentaje']} %)",
                f"=-ROUND(E{f}*{desc['porcentaje']}/100,2)",
            )
        )
    elif desc.get("importe"):
        filas_tot.append(("Descuento", f"=-{desc['importe']}"))
    imp = guion.get("impuesto") or {}
    if imp:
        filas_tot.append(
            (
                f"{imp.get('nombre', 'Impuesto')} ({imp.get('porcentaje', 0)} %)",
                f"=ROUND(SUM(E{f}:E{f + len(filas_tot) - 1})*{imp.get('porcentaje', 0)}/100,2)",
            )
        )
    for k, (etiqueta, formula) in enumerate(filas_tot):
        ws.cell(f + k, 4, etiqueta).alignment = Alignment(horizontal="right")
        ws.cell(f + k, 5, formula).number_format = formato
    ft = f + len(filas_tot)
    ws.cell(ft, 4, "TOTAL").font = Font(bold=True)
    ws.cell(ft, 4).alignment = Alignment(horizontal="right")
    ws.cell(ft, 5, f"=SUM(E{f}:E{ft - 1})").number_format = formato
    ws.cell(ft, 5).font = Font(bold=True)
    for col, ancho in zip("ABCDE", (5, 60, 8, 16, 16), strict=True):
        ws.column_dimensions[col].width = ancho
    ws.cell(
        ft + 2, 1, "Las fórmulas se recalculan solas al cambiar cantidades o precios."
    ).font = Font(italic=True, size=9)
    wb.save(str(ruta))


def presupuesto_md(guion: dict) -> str:
    """Vista corta para que Nova la ensene en el chat (no es el documento)."""
    c = calcular(guion)
    num, moneda = estilo_numeros(guion), guion.get("moneda", "S/")
    lineas = [
        f"**{guion.get('titulo_documento', 'PRESUPUESTO')} Nº {guion.get('numero', '?')}** · {guion.get('asunto', '')}",
        "",
        "| Nº | Descripción | Cant. | P. unit. | Importe |",
        "|---|---|---|---|---|",
    ]
    lineas += [
        f"| {p['n']} | {p.get('descripcion', '')} | {_cant(p['cantidad'])} | {formato_numero(p['precio'], num)} | "
        f"{formato_numero(p['importe'], num)} |"
        for p in c["partidas"]
    ]
    lineas += [
        "",
        f"Subtotal {moneda} {formato_numero(c['subtotal'], num)} · Impuesto {moneda} "
        f"{formato_numero(c['impuesto'], num)} · **Total {moneda} {formato_numero(c['total'], num)}**",
    ]
    return "\n".join(lineas)


# ------------------------------------------------------ solicitud de presupuesto


def _texto_solicitud(guion: dict) -> tuple[str, list[str], list[str]]:
    """(saludo + introduccion, lineas de peticion, cierre) en tono formal, sin IA."""
    intro = guion.get("mensaje") or (
        "Por medio de la presente les solicitamos presupuesto para el suministro de los artículos y/o servicios que se "
        "detallan a continuación."
    )
    peticion = [
        "Precio unitario y precio total de cada partida, indicando si incluyen impuestos.",
        "Plazo de entrega y gastos de envío, si los hubiera.",
        "Forma de pago y garantía.",
        "Periodo de validez de la oferta.",
    ]
    peticion += guion.get("pedir_ademas", [])
    cierre = []
    if guion.get("lugar_entrega"):
        cierre.append(f"El lugar de entrega será: {guion['lugar_entrega']}.")
    if guion.get("plazo_respuesta"):
        cierre.append(
            f"Les agradeceríamos recibir su oferta antes del {guion['plazo_respuesta']}."
        )
    contacto = (guion.get("emisor") or {}).get("contacto")
    if contacto:
        cierre.append(f"Para cualquier aclaración pueden contactarnos en {contacto}.")
    cierre.append("Quedamos a la espera de su respuesta. Atentamente,")
    return intro, peticion, cierre


def solicitud_docx(guion: dict, ruta: Path) -> list[str]:
    faltan: list[str] = []
    doc = estilos.abrir("formal")
    for linea in _persona(guion, "emisor", faltan, obligatorios=("nombre",)):
        doc.add_paragraph(linea).paragraph_format.space_after = Pt(0)
    doc.add_paragraph()
    p = doc.add_paragraph(
        f"{guion.get('lugar', '')}{', ' if guion.get('lugar') else ''}{guion.get('fecha') or '[PENDIENTE: fecha]'}"
    )
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    doc.add_paragraph()
    for linea in _persona(guion, "proveedor", faltan, obligatorios=("nombre",)):
        doc.add_paragraph(linea).paragraph_format.space_after = Pt(0)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.add_run("Asunto: ").bold = True
    p.add_run(guion.get("asunto") or "Solicitud de presupuesto")
    if guion.get("referencia"):
        p = doc.add_paragraph()
        p.add_run("Referencia: ").bold = True
        p.add_run(guion["referencia"])
    doc.add_paragraph()
    intro, peticion, cierre = _texto_solicitud(guion)
    doc.add_paragraph(guion.get("saludo", "Estimados señores:"))
    word.texto_rico(doc.add_paragraph(style="Cuerpo"), intro)
    necesidades = guion.get("necesidades", [])
    if not necesidades:
        faltan.append("necesidades")
    filas = [["Nº", "Descripción", "Cant.", "Especificaciones"]]
    filas += [
        [
            str(n),
            x.get("descripcion", ""),
            str(x.get("cantidad", "")),
            x.get("especificaciones", ""),
        ]
        for n, x in enumerate(necesidades, start=1)
    ]
    word.tabla(doc, filas, anchos_cm=[1, 6.5, 1.5, 7], derecha={0, 2})
    doc.add_paragraph()
    doc.add_paragraph("En su oferta les rogamos que indiquen:", style="Cuerpo")
    for linea in peticion:
        doc.add_paragraph(linea, style="List Bullet")
    doc.add_paragraph()
    for linea in cierre:
        doc.add_paragraph(linea, style="Cuerpo")
    for _ in range(3):
        doc.add_paragraph()
    firma = (
        (guion.get("emisor") or {}).get("firmante")
        or (guion.get("emisor") or {}).get("nombre")
        or ""
    )
    doc.add_paragraph(firma)
    if (guion.get("emisor") or {}).get("cargo"):
        doc.add_paragraph(guion["emisor"]["cargo"])
    doc.save(str(ruta))
    return faltan


def solicitud_correo(guion: dict) -> str:
    """El mismo texto listo para pegar en un correo."""
    intro, peticion, cierre = _texto_solicitud(guion)
    lineas = [
        f"Asunto: {guion.get('asunto', 'Solicitud de presupuesto')}",
        "",
        guion.get("saludo", "Estimados señores:"),
        "",
        intro,
        "",
    ]
    for n, x in enumerate(guion.get("necesidades", []), start=1):
        extra = f" ({x['especificaciones']})" if x.get("especificaciones") else ""
        lineas.append(
            f"{n}. {x.get('descripcion', '')} — cantidad: {x.get('cantidad', '')}{extra}"
        )
    lineas += (
        ["", "En su oferta les rogamos que indiquen:"]
        + [f"- {p}" for p in peticion]
        + [""]
        + cierre
    )
    emisor = guion.get("emisor") or {}
    lineas += [
        "",
        emisor.get("firmante") or emisor.get("nombre", ""),
        emisor.get("cargo", ""),
    ]
    return "\n".join(lineas).strip() + "\n"
