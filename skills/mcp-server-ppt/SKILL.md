---
name: mcp-server-ppt
description: "Automatizacion y control de Microsoft PowerPoint en Windows mediante COM API nativa (PowerPoint.Application). Creacion, edicion en vivo, exportacion de diapositivas a PNG/PDF y manipulacion de formas, tablas y notas."
metadata:
  version: "1.0.0"
  source: "https://github.com/trsdn/mcp-server-ppt"
  author: "trsdn / Adaptado a Nova"
---

# MCP Server PPT · Windows COM Automation

Herramientas y patrones para interactuar directamente con la instalación local de Microsoft PowerPoint en Windows vía COM Interop o scripts PowerShell/C#.

## 1. Capacidades Principales

- **Inspección y Exportación Visual Rápida:**
  - Exportar diapositivas a PNG a máxima resolución sin abrir interfaz visual:
    ```powershell
    $ppt = New-Object -ComObject PowerPoint.Application
    $pres = $ppt.Presentations.Open($fullPath, [Microsoft.Office.Core.MsoTriState]::msoTrue, $false, $false)
    $pres.SaveAs($outputDir, 18) # 18 = ppSaveAsPNG
    $pres.Close()
    $ppt.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($ppt) | Out-Null
    ```
- **Manipulación de Presentaciones Abiertas:**
  - Control de transiciones de diapositivas (`Push`, `Fade`, `Wipe`).
  - Adición y formateo dinámico de tablas nativas con estilos corporativos.
  - Inserción de notas de orador (`NotesPage`) y metadatos de presentación.

## 2. Reglas de Operación Segura

1. Siempre liberar el objeto COM de Windows al terminar (`Marshal.ReleaseComObject`) para evitar procesos huérfanos de `POWERPNT.EXE` en segundo plano.
2. Usar rutas absolutas de Windows con letras de unidad nativas.
3. Comprobar si el archivo está bloqueado o en uso por otra ventana antes de escribir.
