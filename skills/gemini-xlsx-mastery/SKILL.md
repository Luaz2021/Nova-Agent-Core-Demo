---
name: gemini-xlsx-mastery
description: "Generacion y analisis profesional de hojas Excel (.xlsx/CSV) y modelos financieros (DCF, TIR, VAN) con openpyxl/pandas."
---

# Manipulacion de Hojas de Calculo & Modelado Financiero

Proporciona directivas y patrones de ejecucion para generar, inspeccionar, transformar y auditar hojas de calculo (Excel `.xlsx`, `.csv`, `.tsv`), asi como estructurar modelos financieros y de rentabilidad sin corromper formulas ni dependencias.

---

## 1. Reglas Fundamentales de Creacion y Modificacion

1. **Preservacion de formulas nativas:**
   - Jamas hardcodeo resultados calculables cuando corresponden a formulas de Excel.
   - Aplico formulas en ingles (estandar universal de ficheros XLSX): `=SUM()`, `=AVERAGE()`, `=IF()`, `=XLOOKUP()`, `=NPV()`, `=IRR()`, `=PMT()`.
   - Utilizo referencias relativas o absolutas (`$A$1`) con precision matematica para permitir arrastre sin errores.

2. **Higiene visual y ergonomia:**
   - **Autoajuste de columnas:** Calculo el ancho optimo de cada columna en funcion de la celda mas ancha mas un margen de 3 caracteres, evitando el error visual `###`.
   - **Inmovilizacion de paneles (Freeze Panes):** Inmovilizo siempre la fila superior de encabezados (`freeze_panes = "A2"`) para mantener contexto en tablas largas.
   - **Filtros automaticos:** Aplico autofiltro en el rango de encabezados para facilitar la navegacion del usuario.
   - **Formato numerico explicito:** Cada numero debe llevar formato segun su naturaleza:
     * Monedas: `#,##0.00 €`, `$#,##0.00` o `S/ #,##0.00`.
     * Porcentajes: `0.0%` o `0.00%`.
     * Fechas: `YYYY-MM-DD` o `DD/MM/YYYY`.
     * Enteros: `#,##0`.

3. **Cero dependencias pesadas de usuario:**
   - Todo procesamiento se resuelve mediante scripts reproducibles de Python (`openpyxl`, `pandas` o modulo nativo `csv`) o Node.js (`exceljs`).
   - Evito macros VBA complejas que activen alertas de seguridad o bloqueos en antivirus modernos.

---

## 2. Modulo de Modelado Financiero y Proyecciones

Cuando se estructuran hojas financieras, presupuestos o estimaciones de retorno de inversion:

### Estructura de Capas en el Libro
1. **Pestana `Supuestos` (Inputs):** Parametros base aislados en una hoja o bloque superior (tasa de inflacion, coste de capital / WACC, precio unitario, ocupacion estimada, coste de energia). Las demas hojas referencian estas celdas y nunca replican numeros magicos.
2. **Pestana `Operacion` / `Flujos`:** Proyecciones mensuales o anuales calculadas exclusivamente mediante formulas ancladas a los supuestos.
3. **Pestana `Resumen Ejecutivo` (KPIs):** Indicadores clave consolidados:
   - **VAN (Valor Actual Neto) / NPV:** `=NPV(tasa_descuento, rango_flujos_1_a_n) + inversion_inicial`.
   - **TIR (Tasa Interna de Retorno) / IRR:** `=IRR(rango_flujos_completos)`.
   - **Payback (Periodo de Recuperacion):** Mes o ano en que el flujo acumulado cruza a positivo.
   - **Margen Operativo y EBITDA:** Desglose transparente de ingresos brutos menos costes directos e indirectos.

### Analisis de Sensibilidad
Siempre que se analice viabilidad de negocio (alquileres, proyectos solares o comercio):
- Construyo tres escenarios claros: **Conservador (Pesimista)**, **Base (Moderado)** y **Optimista**.
- Modelo variaciones de volumen (ej. porcentaje de ocupacion de noches al mes) y variaciones de costes fijos/variables.

---

## 3. Patrones de Codigo Recomendados (Python con Openpyxl)

### Plantilla de Generacion Limpia

```python
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Flujo_Caja"

# Estilos base
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
align_center = Alignment(horizontal="center", vertical="center")
currency_format = "#,##0.00 €"

# Encabezados
headers = ["Concepto", "Enero", "Febrero", "Marzo", "Total Q1"]
ws.append(headers)

for col_num in range(1, len(headers) + 1):
    cell = ws.cell(row=1, column=col_num)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = align_center

# Inmovilizar panel y agregar datos con formulas
ws.freeze_panes = "A2"

# Ajustar ancho de columnas dinamicamente
for col in ws.columns:
    max_len = max(len(str(cell.value or "")) for cell in col)
    col_letter = get_column_letter(col[0].column)
    ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

wb.save("reporte_financiero.xlsx")
```

---

## 4. Auditoria de Hojas de Calculo Existentes

Cuando el usuario suministra un archivo existente para revision:
1. **Inspeccion de referencias rotas:** Detecto celdas con errores `#REF!`, `#VALUE!`, `#DIV/0!` o `#N/A`.
2. **Deteccion de valores forzados:** Identifico celdas que deberian ser resultado de calculo pero tienen un numero escrito a mano.
3. **Consistencia de rangos:** Reviso si las sumas horizontales coinciden con las sumas verticales en tablas matriciales.
4. **Validacion de tipos:** Verifico que no existan numeros almacenados como texto que impidan la ejecucion de formulas.
