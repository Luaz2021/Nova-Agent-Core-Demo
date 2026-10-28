---
name: gemini-ui-guidelines
description: "Auditoria frontend segun Web Interface Guidelines de Vercel: accesibilidad, estados de foco, tipografia y cero CLS."
trigger: model_decision
---

# Vercel Web Interface Guidelines (Frontend Auditor & Standards)

Esta habilidad implementa los estÃ¡ndares de producciÃ³n de Vercel Labs para interfaces de usuario modernas. Se asegura de que cada pantalla, botÃ³n, formulario o animaciÃ³n se comporte como un producto de ingenierÃ­a web de primer nivel.

---

## 1. CuÃ¡ndo se Activa Esta Habilidad

El agente activarÃ¡ esta habilidad cuando:
- El usuario pida: *"Revisa mi UI"*, *"Haz una auditorÃ­a de diseÃ±o/UX"*, *"Comprueba la accesibilidad"*, *"Revisa si el cÃ³digo cumple buenas prÃ¡cticas web"*.
- Al generar o refactorizar cualquier componente interactivo (botones, modales, formularios, tablas, listas).

---

## 2. Reglas de Oro de Vercel para UI

### A. Accesibilidad (A11y)
- **Botones con sÃ³lo icono:** Obligatorio `aria-label="AcciÃ³n"`.
- **Iconos decorativos:** Obligatorio `aria-hidden="true"`.
- **SemÃ¡ntica pura:** Usa `<button>` para acciones y `<a>`/`<Link>` para navegaciÃ³n (prohibido `<div onClick>`).
- **NavegaciÃ³n por teclado:** Todo elemento interactivo debe responder a teclado (`Enter` / `Space`).
- **JerarquÃ­a:** Un Ãºnico `<h1>` por pÃ¡gina, encabezados consecutivos sin saltos de nivel.

### B. Estados de Foco (Focus States)
- **Nunca `outline-none` a secas:** Si se quita el contorno nativo, es **obligatorio** reemplazarlo por `focus-visible:ring-2 focus-visible:ring-offset-2`.
- Preferir `:focus-visible` sobre `:focus` (evita mostrar el anillo de foco tras hacer clic con ratÃ³n).

### C. Formularios y Experiencia de Entrada (UX)
- **JamÃ¡s bloquear el pegado:** Prohibido usar `preventDefault()` en eventos `onPaste`.
- **Autocompletado:** Atributos `autocomplete` correctos (`email`, `current-password`, `new-password`, etc.).
- **Desactivar autocorrecciÃ³n en datos tÃ©cnicos:** `spellCheck={false}` en campos de usuario, cÃ³digo o emails.
- **Labels clicables:** Asociados mediante `htmlFor` o envolviendo el input.
- **Feedback inmediato:** Botones de submit muestran spinner o estado `loading...` pero no desaparecen.

### D. Animaciones y Rendimiento
- **Prohibido `transition: all`:** Especificar explÃ­citamente las propiedades (`transition: transform 150ms ease, opacity 150ms ease`).
- Solo animar propiedades aceleradas por hardware (`transform` y `opacity`).
- Respetar `prefers-reduced-motion`.

### E. TipografÃ­a y Micro-detalles de Calidad
- Usar elipsis tipogrÃ¡fica real `â€¦` (no tres puntos `...`).
- Comillas curvas tipogrÃ¡ficas `â€œ` y `â€` en textos explicativos en lugar de rectas `"`.
- Espacios de no separaciÃ³n (`&nbsp;`) en unidades (ej. `10&nbsp;MB`, `Ctrl&nbsp;+&nbsp;K`).
- Columnas numÃ©ricas en tablas con `tabular-nums` (`font-variant-numeric: tabular-nums`).
- Encabezados con `text-wrap: balance` o `text-pretty` para evitar palabras huÃ©rfanas.

### F. Manejo Robusto de Contenido
- Contenedores de texto con `truncate`, `line-clamp-*` o `break-words`.
- Hijos directos en flexbox con texto necesitan `min-w-0` para permitir truncamiento sin romper el layout.
- ImÃ¡genes con `width` y `height` explÃ­citos (o aspect-ratio) para evitar saltos acumulativos de diseÃ±o (CLS).

---

## 3. Formato de AuditorÃ­a (Conciso y Directo)

Al auditar archivos o cÃ³digo, el agente reporta las infracciones de manera concisa y directa:

```
[archivo:lÃ­nea] [Regla Incumplida]: Breve correcciÃ³n tÃ©cnica sugerida.
```

