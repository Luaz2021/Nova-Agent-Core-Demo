---
name: gemini-ui-guidelines
description: "Auditoria frontend segun Web Interface Guidelines de Vercel: accesibilidad, estados de foco, tipografia y cero CLS."
trigger: model_decision
---

# Vercel Web Interface Guidelines (Frontend Auditor & Standards)

Esta habilidad implementa los estándares de producción de Vercel Labs para interfaces de usuario modernas. Se asegura de que cada pantalla, botón, formulario o animación se comporte como un producto de ingeniería web de primer nivel.

---

## 1. Cuándo se Activa Esta Habilidad

El agente activará esta habilidad cuando:
- El usuario pida: *"Revisa mi UI"*, *"Haz una auditoría de diseño/UX"*, *"Comprueba la accesibilidad"*, *"Revisa si el código cumple buenas prácticas web"*.
- Al generar o refactorizar cualquier componente interactivo (botones, modales, formularios, tablas, listas).

---

## 2. Reglas de Oro de Vercel para UI

### A. Accesibilidad (A11y)
- **Botones con sólo icono:** Obligatorio `aria-label="Acción"`.
- **Iconos decorativos:** Obligatorio `aria-hidden="true"`.
- **Semántica pura:** Usa `<button>` para acciones y `<a>`/`<Link>` para navegación (prohibido `<div onClick>`).
- **Navegación por teclado:** Todo elemento interactivo debe responder a teclado (`Enter` / `Space`).
- **Jerarquía:** Un único `<h1>` por página, encabezados consecutivos sin saltos de nivel.

### B. Estados de Foco (Focus States)
- **Nunca `outline-none` a secas:** Si se quita el contorno nativo, es **obligatorio** reemplazarlo por `focus-visible:ring-2 focus-visible:ring-offset-2`.
- Preferir `:focus-visible` sobre `:focus` (evita mostrar el anillo de foco tras hacer clic con ratón).

### C. Formularios y Experiencia de Entrada (UX)
- **Jamás bloquear el pegado:** Prohibido usar `preventDefault()` en eventos `onPaste`.
- **Autocompletado:** Atributos `autocomplete` correctos (`email`, `current-password`, `new-password`, etc.).
- **Desactivar autocorrección en datos técnicos:** `spellCheck={false}` en campos de usuario, código o emails.
- **Labels clicables:** Asociados mediante `htmlFor` o envolviendo el input.
- **Feedback inmediato:** Botones de submit muestran spinner o estado `loading...` pero no desaparecen.

### D. Animaciones y Rendimiento
- **Prohibido `transition: all`:** Especificar explícitamente las propiedades (`transition: transform 150ms ease, opacity 150ms ease`).
- Solo animar propiedades aceleradas por hardware (`transform` y `opacity`).
- Respetar `prefers-reduced-motion`.

### E. Tipografía y Micro-detalles de Calidad
- Usar elipsis tipográfica real `…` (no tres puntos `...`).
- Comillas curvas tipográficas `“` y `”` en textos explicativos en lugar de rectas `"`.
- Espacios de no separación (`&nbsp;`) en unidades (ej. `10&nbsp;MB`, `Ctrl&nbsp;+&nbsp;K`).
- Columnas numéricas en tablas con `tabular-nums` (`font-variant-numeric: tabular-nums`).
- Encabezados con `text-wrap: balance` o `text-pretty` para evitar palabras huérfanas.

### F. Manejo Robusto de Contenido
- Contenedores de texto con `truncate`, `line-clamp-*` o `break-words`.
- Hijos directos en flexbox con texto necesitan `min-w-0` para permitir truncamiento sin romper el layout.
- Imágenes con `width` y `height` explícitos (o aspect-ratio) para evitar saltos acumulativos de diseño (CLS).

---

## 3. Formato de Auditoría (Conciso y Directo)

Al auditar archivos o código, el agente reporta las infracciones de manera concisa y directa:

```
[archivo:línea] [Regla Incumplida]: Breve corrección técnica sugerida.
```

