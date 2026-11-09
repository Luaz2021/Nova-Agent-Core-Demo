---
name: ppt-master
description: "Motor integral de generacion y maquetacion de presentaciones PPTX nativas: formas vectoriales, tablas editables, soporte de plantillas institucionales, control de colisiones de placeholders y exportacion de alta fidelidad."
metadata:
  version: "1.0.0"
  source: "https://github.com/hugohe3/ppt-master"
  author: "Hugo He / Adaptado a Nova"
---

# PPT Master · Native PPTX Generation Engine

Doctrina y patrones para generar presentaciones editables en PowerPoint (`.pptx`) con calidad corporativa, eliminando el aspecto "amateur" de diapositivas generadas por IA.

## 1. Principios de Arquitectura Nativa

1. **Plantilla-First (Zero Ghost Placeholders):**
   - Al cargar una plantilla institucional (`.pptx`), nunca dejar marcadores de contenido vacíos. Los placeholders vacíos generan viñetas fantasma (`•`) o bordes grises indeseados en el visor de PowerPoint.
   - Si no se usa un placeholder nativo, eliminar su elemento del árbol XML de la diapositiva:
     ```python
     def remove_shape(shape):
         sp = shape._element
         sp.getparent().remove(sp)
     ```
2. **Contraste Dinámico Estricto (WCAG AA):**
   - **Portadas o diapositivas oscuras:** Texto en blanco puro (`#FFFFFF`) para títulos principales, celestes o dorados de acento (`#60C3FF`, `#F59E0B`) para autores y subtítulos. Jamás usar azules oscuros o grises medios sobre fondos oscuros.
   - **Diapositivas de contenido claras:** Títulos en azul marino profundo (`#0B1B3D`) o gris pizarra (`#0F172A`), texto secundario en `#334155` o `#475569`.
3. **Estructura de Grid y Espaciado Proporcional (Widescreen 16:9):**
   - Dimensiones estándar: `13.333" x 7.5"` (33.86 cm x 19.05 cm).
   - Márgenes de seguridad:
     - Margen lateral izquierdo/derecho: mínimo `0.85"` a `0.92"`.
     - Margen superior para títulos: `0.35"` a `0.45"`.
     - Margen inferior para footer o banners: no rebasar `7.05"` para no pisar logotipos institucionales o números de página.
4. **Tablas Nativas de Alta Gama:**
   - Encabezados con fondo sólido de marca (`#0B1B3D`) y texto en blanco centrado o alineado a la izquierda.
   - Filas de datos con relleno alternado (`#FFFFFF` y `#F8FAFC`).
   - Márgenes internos obligatorios en cada celda (`margin_left = Inches(0.1)`, `margin_top = Inches(0.08)`).
   - Columnas balanceadas según densidad de contenido (no distribuir anchos por igual si una columna tiene 3 palabras y otra tiene párrafos).

## 2. Inyección de Evidencias e Imágenes

- Toda captura o imagen embebida debe contar con un contenedor o marco estético (fondo blanco o tarjeta redondeada `#FFFFFF` con borde `#E2E8F0`).
- Prohibido insertar capturas con fondos negros opacos sobre diapositivas con fondos claros o pasteles; la evidencia debe tener coherencia lumínica con la diapositiva.
- Los enlaces web deben llevar hipervínculo activo en PowerPoint (`run.hyperlink.address = url`) y subrayado visible.
