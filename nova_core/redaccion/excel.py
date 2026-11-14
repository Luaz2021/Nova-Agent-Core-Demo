"""Excel de verdad (.xlsx) para cualquier tabla: redactar.py excel --datos tabla.json --carpeta X (12/11/2026, Claude).

Por que: el 11/11 Nova entrego un CSV separado por comas "para abrir en Excel". En este Windows el separador de
listas es ";", asi que Excel lo metio todo en una sola columna. Nunca CSV para Alexander: siempre .xlsx.

tabla.json:
{
  "archivo": "Precios_Flor_de_Punga",
  "titulo": "Precios y márgenes",              (opcional: fila de titulo encima de la tabla)
  "hojas": [{
    "nombre": "Precios",
    "columnas": ["Producto", "Coste", "Venta", "Margen"],
    "filas": [["Cerveza", "S/ 5.20", 8, "=C{fila}-B{fila}"]],   ({fila} = numero de fila de Excel)
    "formatos": {"Coste": "moneda", "Venta": "moneda", "Margen": "moneda"},  (moneda | porcentaje | entero | decimal | texto | fecha)
    "moneda": "S/",
    "totales": ["Coste", "Venta", "Margen"],    (fila TOTAL con =SUMA)
    "editables": ["Venta"]                       (columnas en amarillo claro: las que Alexander cambia a mano)
  }]
}
Tambien acepta un .csv (detecta "," o ";") o una tabla Markdown (| a | b |).
"""

import csv
import io
import json
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY, CLARO, EDITABLE, BORDE = "0F2240", "F8F9FA", "FFF8E1", "DEE2E6"
FORMATOS = {
    "entero": "#,##0",
    "decimal": "#,##0.00",
    "porcentaje": "0.0%",
    "fecha": "DD/MM/YYYY",
    "texto": "@",
}
RE_NUMERO = re.compile(
    r"^\s*(?:S/\.?|\$|€|USD|EUR|PEN)?\s*(-?[\d.,]+)\s*(%|€)?\s*$", re.IGNORECASE
)


def a_numero(valor):
    """'S/ 8.50' -> 8.5 · '1.234,50 €' -> 1234.5 · '15%' -> 0.15 · lo demas se queda como texto."""
    if not isinstance(valor, str) or valor.startswith("="):
        return valor
    m = RE_NUMERO.match(valor)
    if not m:
        return valor
    cifra = m.group(1)
    if "," in cifra and "." in cifra:  # el ultimo separador es el decimal
        cifra = (
            cifra.replace(".", "").replace(",", ".")
            if cifra.rfind(",") > cifra.rfind(".")
            else cifra.replace(",", "")
        )
    elif "," in cifra:
        partes = cifra.split(",")
        cifra = (
            cifra.replace(",", ".") if len(partes[-1]) != 3 else cifra.replace(",", "")
        )
    try:
        numero = float(cifra)
    except ValueError:
        return valor
    return (
        numero / 100
        if m.group(2) == "%"
        else (int(numero) if numero.is_integer() and "." not in m.group(1) else numero)
    )


def desde_texto(ruta: Path) -> dict:
    """CSV (con , o ;) o tabla Markdown -> estructura de tabla.json."""
    texto = ruta.read_text(encoding="utf-8-sig")
    if ruta.suffix.lower() == ".md" or texto.lstrip().startswith("|"):
        filas = [
            [c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in texto.splitlines()
            if ln.strip().startswith("|")
        ]
        filas = [f for f in filas if not all(re.fullmatch(r":?-{2,}:?", c) for c in f)]
    else:
        dialecto = csv.Sniffer().sniff(texto[:2000], delimiters=",;\t")
        filas = list(csv.reader(io.StringIO(texto), dialecto))
    return {
        "archivo": ruta.stem,
        "hojas": [{"nombre": ruta.stem[:31], "columnas": filas[0], "filas": filas[1:]}],
    }


def _hoja(ws, hoja: dict, titulo: str | None) -> None:
    columnas = hoja["columnas"]
    formatos = hoja.get("formatos", {})
    moneda = hoja.get("moneda", "S/")
    editables = set(hoja.get("editables", []))
    fino = Side(style="thin", color=BORDE)
    borde = Border(left=fino, right=fino, top=fino, bottom=fino)
    fila0 = 1
    if titulo:
        ws.cell(1, 1, titulo).font = Font(
            name="Segoe UI", size=14, bold=True, color=NAVY
        )
        fila0 = 3
    for j, nombre in enumerate(columnas, start=1):
        c = ws.cell(fila0, j, nombre)
        c.font = Font(name="Segoe UI", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = borde
    for i, fila in enumerate(hoja["filas"], start=fila0 + 1):
        for j, valor in enumerate(fila, start=1):
            nombre = columnas[j - 1] if j <= len(columnas) else ""
            if isinstance(valor, str):
                valor = valor.replace("{fila}", str(i))
            valor = valor if formatos.get(nombre) == "texto" else a_numero(valor)
            c = ws.cell(i, j, valor)
            c.border = borde
            c.font = Font(name="Calibri", size=11)
            fmt = formatos.get(nombre)
            if fmt == "moneda":
                c.number_format = f'"{moneda} "#,##0.00'
            elif fmt in FORMATOS:
                c.number_format = FORMATOS[fmt]
            if nombre in editables:
                c.fill = PatternFill("solid", fgColor=EDITABLE)
            elif (i - fila0) % 2 == 0:
                c.fill = PatternFill("solid", fgColor=CLARO)
    ultima = fila0 + len(hoja["filas"])
    if hoja.get("totales") and hoja["filas"]:
        t = ultima + 1
        ws.cell(t, 1, "TOTAL").font = Font(bold=True, color=NAVY)
        for nombre in hoja["totales"]:
            if nombre in columnas:
                j = columnas.index(nombre) + 1
                letra = get_column_letter(j)
                c = ws.cell(t, j, f"=SUM({letra}{fila0 + 1}:{letra}{ultima})")
                c.font = Font(bold=True, color=NAVY)
                c.border = Border(top=Side(style="medium", color=NAVY))
                fmt = formatos.get(nombre)
                c.number_format = (
                    f'"{moneda} "#,##0.00'
                    if fmt == "moneda"
                    else FORMATOS.get(fmt, "General")
                )
    for j, nombre in enumerate(columnas, start=1):  # ancho segun el contenido mas largo
        largos = [len(str(nombre))] + [
            len(str(f[j - 1]))
            for f in hoja["filas"]
            if j <= len(f) and not str(f[j - 1]).startswith("=")
        ]
        ws.column_dimensions[get_column_letter(j)].width = min(max(largos) + 4, 60)
    ws.freeze_panes = ws.cell(fila0 + 1, 1)
    ws.auto_filter.ref = f"A{fila0}:{get_column_letter(len(columnas))}{ultima}"


def crear(datos: dict, destino: Path) -> Path:
    libro = Workbook()
    libro.remove(libro.active)
    for n, hoja in enumerate(datos["hojas"]):
        ws = libro.create_sheet(
            re.sub(r"[\\/*?:\[\]]", "", hoja.get("nombre") or f"Hoja{n + 1}")[:31]
        )
        _hoja(ws, hoja, datos.get("titulo") if n == 0 else hoja.get("titulo"))
    libro.save(destino)
    return destino


def formatos_auto(hoja: dict) -> dict:
    """Si una columna trae 'S/ 5.20' o '35%', recuerda que es moneda o porcentaje (salvo que ya venga indicado)."""
    formatos = dict(hoja.get("formatos", {}))
    for j, nombre in enumerate(hoja["columnas"]):
        valores = [str(f[j]) for f in hoja["filas"] if j < len(f) and str(f[j]).strip()]
        if nombre in formatos or not valores:
            continue
        if all(v.strip().endswith("%") for v in valores):
            formatos[nombre] = "porcentaje"
        elif all(
            re.match(r"^\s*(S/|\$|€|USD|EUR|PEN)", v, re.IGNORECASE)
            or v.strip().endswith("€")
            for v in valores
        ):
            formatos[nombre] = "moneda"
            if valores[0].strip().endswith("€") or "€" in valores[0]:
                hoja.setdefault("moneda", "€")
    return formatos


def cargar(ruta: Path) -> dict:
    datos = (
        json.loads(ruta.read_text(encoding="utf-8-sig"))
        if ruta.suffix.lower() == ".json"
        else desde_texto(ruta)
    )
    for hoja in datos["hojas"]:
        hoja["formatos"] = formatos_auto(hoja)
    return datos
