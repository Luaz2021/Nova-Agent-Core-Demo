---
name: flagship-saas-experimental-patterns
description: Patrones de interaccion insignia estilo Linear, Raycast, Vercel y estudios experimentales: Command Palette Cmd+K, bordes conicos reactivos, Bento de precision, Dock/Spotlight tactile surfaces y los 6 estados UI obligatorios.
---

# Flagship SaaS & Experimental UI Patterns (Nivel 2-4)

Skill enfocada en elevar productos SaaS, herramientas developer, portfolios tecnicos y landings de producto al estandar de Linear, Raycast y Vercel sin caer en clones oscuros genericos con neon morado.

## 1. Superficies Tactiles, Iluminacion y Bento de Precision
- **Borde de 1px con luz direccional (Gradient Border / Spotlight):**
  - Usar pseudo-elementos `::before` o `mask-composite: exclude` con `radial-gradient` o `conic-gradient` ligado a variables `--mx` y `--my` actualizadas por `pointermove` (throttled con `requestAnimationFrame` y solo activo en `(pointer: fine)`).
- **Contraste controlado en modo oscuro titanio:**
  - Nunca usar negro puro `#000000` plano en todo; trabajar planos sutiles (`#09090b` fondo -> `#111115` superficie -> `rgba(255,255,255,0.08)` borde) o paletas claras editoriales estilo papel/grafito cuando la Biblia Visual lo pida.
- **Micro-interacciones de precision (`cubic-bezier(0.22, 1, 0.36, 1)`):** transiciones de `160ms - 240ms`, respuesta fisica sutil (`scale(0.98)` en `:active`), foco visible de alta nitidez (`focus-visible:outline`).

---

## 2. Componentes Insignia ("One Live Thing" con Utilidad Real)
1. **Command Palette (`Cmd+K` / `Ctrl+K`):**
   - Atajo global limpio (`keydown` escuchando `(e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k'`), boton visible en cabecera para movil/raton, cierre con `Escape` y navegacion por flechas (`ArrowUp`/`ArrowDown`/`Enter`) sin librerias pesadas.
2. **Bento Modular Interactivo:**
   - Mezclar celdas de formato asimetrico (`col-span-7` + `col-span-5`, `row-span-2`) donde al menos 1 o 2 tarjetas tengan demo viva (toggle en directo, slider de comparacion antes/despues, consola simulada limpia o grafica Canvas 2D viva).
3. **Switchers / Segmented Controls con Pildora Deslizante:**
   - Indicador activo animado con `transform: translateX(...)` o View Transitions / FLIP para cero saltos de layout.

---

## 3. Los 6 Estados Obligatorios de Producto (`frontend-design-direction`)
Cuando la web incluya formularios, buscadores, tablas, filtros o reservas, implementar explicitamente:
1. **Default / Listo**
2. **Hover / Focus-Visible** (accesible por teclado)
3. **Loading** (skeleton limpio o feedback inline, sin spinners bloqueantes)
4. **Empty** (estado vacio con accion clara)
5. **Error** (mensaje humano concreto + reintento)
6. **Success** (confirmacion clara sin romper el layout)

---

## 4. Guardrails Anti-Slop y QA
- **Cero metricas falsas ni logos inventados:** si no hay clientes reales en `datos.json`, no inventar una tira de "Trusted by Google/Stripe".
- **Rendimiento:** evitar `backdrop-filter: blur()` apilados en >4 elementos grandes simultaneos durante scroll intenso (degrada FPS en GPUs integradas).
- Verificar en `1280px` y `375px` con Playwright + `InternVL3_5:8b` que ningun bento ni modal `Cmd+K` desborde ni tape controles en movil.
