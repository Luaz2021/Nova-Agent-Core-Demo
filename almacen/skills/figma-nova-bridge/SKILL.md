---
name: figma-nova-bridge
description: "Puente operativo entre el plugin oficial de Figma MCP (17 skills) y los flujos de Nova: Estudio Web + Qwen, HTML-to-Figma para redisenos limpios, reglas de Design System por repo y Figma a Motion/Video (Remotion/Hyperframes). Leer antes de cualquier tarea con Figma."
---

# Figma <-> Nova Bridge

Esta skill no sustituye a las 17 skills oficiales del plugin de Figma (`<NOVA_HOME>/config/plugins/figma/skills/`), sino que las acopla al flujo de Nova para evitar disenos a ciegas, bloqueos del plan Starter y codigo duplicado.

## 1. Reglas de Hierro (obligatorias en cualquier tarea con Figma)
1. **Cero diseno a ciegas:** despues de CUALQUIER escritura en el lienzo (`use_figma`, `html_to_figma`, `send_code_to_figma`), llamar a `get_screenshot` sobre el nodo creado/editado y revisar visualmente alineacion, contraste, solapes y tipografia antes de ensenarlo o darlo por cerrado.
2. **Plan Starter = maximo 3 paginas, mockups ilimitados:** nunca ejecutar `createPage` por cada pantalla. Usar como maximo 3 paginas por archivo:
   - Pagina 1: `00 · Design System & Tokens`
   - Pagina 2: `01 · Auth & Flujos Core`
   - Pagina 3: `02 · App Principal & Estados`
   Dentro de cada pagina, agrupar todas las pantallas que hagan falta usando nodos `Section` y frames alineados en fila o cuadricula (gap fijo de 80-120 px).
3. **Prerrequisitos oficiales obligatorios:** cargar la skill oficial del plugin antes de su herramienta MCP:
   - `figma-use` antes de `use_figma`
   - `figma-create-new-file` antes de `create_new_file`
   - `figma-design-to-code` antes de `get_design_context`
   - `figma-code-workflows` antes de `html_to_figma` / `send_code_to_figma`
   - `figma-generate-library` y `figma-generate-design` para librerias y pantallas desde design system
4. **Criterio visual antes que nodos:** nunca dibujar una UI completa a pelo con `figma.createRectangle()` sin haber definido antes tokens, paleta y tipografia (leer `frontend-design-direction`, `typography-system` y `color-palette-builder` si el proyecto no trae design system).

---

## 2. Los 4 Flujos de Acoplamiento con Nova

### Flujo A · Figma -> Estudio Web (diseno a codigo con Qwen a 0 tokens)
Usar cuando el usuario pasa una URL de Figma para pasarla a web real:
1. Leer `figma-design-to-code`.
2. Llamar a `get_design_context`, `get_variable_defs` y `get_screenshot` del frame objetivo.
3. Mapear los tokens extraidos a `estudio/estilos/00_tokens.css` (variables `:root`) y el criterio visual a `estudio/ficha.json` via `estudio.py`.
4. Nova escribe la arquitectura CSS (archivos <= 150 lineas con comentarios `/* qwen: .clase = uso */`) y la portada/nav; **Qwen pica el volumen HTML en local** (`estudio.py picar`).
5. Cerrar siempre con `estudio.py revisar` (capturas PC 1280 y movil 390) comparando contra `get_screenshot` de Figma.

### Flujo B · HTML/Estudio Web -> Figma (redisenos limpios y entregables editables)
Usar cuando el usuario quiere rediseno completo de mockups o pasar una app/web a Figma con calidad visual alta (evita el resultado rigido de dibujar pantallas complejas con `use_figma` a mano):
1. Definir paleta, tipografia y layout limpio en HTML/CSS (o iterar el mockup HTML existente) y verificarlo visualmente primero.
2. Cargar `figma-code-workflows` (+ `figma-create-new-file` si hace falta archivo nuevo).
3. Empujar las pantallas como capas editables con `html_to_figma` o `send_code_to_figma` (aprovechando `code_layers_enabled: true`).
4. Ordenar los frames resultantes en `Section` dentro de las 3 paginas del archivo con `use_figma` y validar con `get_screenshot`.

### Flujo C · Reglas de Design System por Repo (`create-design-system-rules` + Code Connect)
Usar cuando un proyecto tiene codigo y Figma y hay que evitar deriva entre ambos:
1. Escanear tokens del repo (CSS `:root`, `tailwind.config`, variables de tema) y estructura de componentes.
2. Contrastar con `get_variable_defs` y `get_code_connect_map` del archivo de Figma.
3. Documentar las reglas del proyecto (convenciones de nombres, tokens obligatorios, componentes prohibidos/reutilizables) en el archivo de reglas del repo y vincular componentes clave con `figma-code-connect`.

### Flujo D · Figma -> Tokens (`DESIGN.md` / `:root`) y Motion/Video (enfoque OpenDesign)
Usar cuando un storyboard o pantallas de Figma deben convertirse en animacion web o video:
1. Extraer variables con `get_variable_defs` a `:root` CSS y/o `DESIGN.md` (apoyandose en `brand-to-design-md`).
2. Leer los frames clave del storyboard con `get_design_context` + `get_screenshot` tratandolos como *keyframes* (estado inicial, transiciones, estado final), no como imagenes planas.
3. Destino web interactivo: cargar `figma-implement-motion` y el carril `index-motion-3d` (GSAP / ScrollTrigger / Lenis).
4. Destino video/reels: pasar los tokens y keyframes al carril `index-ai-multimedia` (Remotion o Hyperframes + FFmpeg).

---

## 3. Diagnostico Rapido y Definicion de Hecho
- Si falla acceso, permisos o limite de peticiones: llamar a `whoami` en `figma_figma` y revisar plan/asiento.
- **Hecho =** `get_screenshot` verificado sin solapes ni texto cortado + archivo dentro del limite de 3 paginas (Starter) + tokens coherentes con el proyecto.
