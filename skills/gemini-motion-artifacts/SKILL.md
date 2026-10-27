---
name: gemini-motion-artifacts
description: Produce high-craft, self-contained HTML artifacts, interactive sandboxed iframes, and code-driven animations or motion graphics with Canvas/SVG. Use when asked for interactive plans, dashboards, side-by-side comparisons, flowcharts, slide decks, triage editors, or code-generated videos and animations (timelines, frame captures, WebM export).
---

# Motion & HTML Artifacts

Combina la disciplina de artefactos HTML autocontenidos de alta densidad visual con un motor de motion graphics y video generado con codigo dentro de iframes o canvas aislados.

## 1. Criterio de Activacion (Cuando usar cada formato)

### Usa Markdown cuando:
- La respuesta es conversacional, puntual o de pocos parrafos.
- Es codigo puro, un script, una configuracion o un comando de terminal.
- El usuario quiere una respuesta rapida y descartable.

### Salta a Artefacto HTML Interactivo cuando:
- **Comparativas:** Dos o mas enfoques o arquitecturas evaluadas lado a lado.
- **Informacion espacial:** Diffs interactivos, grafos de llamadas, mapas de arquitectura, flowcharts, timelines historicos.
- **Datos y metricas:** Tablas con ordenamiento/filtrado o graficos interactivos.
- **Editores de ida y vuelta:** Tableros Kanban, selectores de flags o afinadores de prompts cuyo estado final siempre se puede copiar como texto/JSON.
- **Documentos de entrega:** Propuestas para clientes, informes ejecutivos, especificaciones de arquitectura o presentaciones de diapositivas.

### Salta a Motion Graphics / Video con Codigo cuando:
- El usuario pide explicar visualmente un algoritmo, flujo de datos o arquitectura en movimiento.
- Se solicitan reels, animaciones o infografias animadas para redes sociales o docencia.
- Se requiere generar secuencias de video descargables directamente desde el navegador (WebM/MP4).

---

## 2. Reglas Universales de Artefactos

1. **Un unico archivo autocontenido (.html):** Todo el CSS en `<style>`, el JavaScript en `<script>` y los iconos o graficos como inline SVG o Canvas. Cero dependencias externas que requieran conexion a internet en runtime, salvo las autorizadas por el entorno.
2. **Comprensible en 5 segundos:** Debe iniciar con un encabezado claro y un parrafo de encuadre o resumen ejecutivo (TL;DR) antes de entrar al detalle interactivo.
3. **Diseno intencional y sobrio:** Tipografia cuidada (60-75 caracteres por linea), soporte nativo para tema claro y oscuro (`prefers-color-scheme` y `[data-theme]`), y paletas con contraste semantico. Prohibidos los gradientes chillones innecesarios y las cajas decorativas sin funcion.
4. **Seguridad y Compatibilidad en iframe sandbox:**
   - Todo acceso a `localStorage`, `sessionStorage` o cookies debe envolverse estrictamente en bloques `try / catch` para no bloquearse en contextos aislados o con dominios opacos.
   - Enlaces externos: en sandboxes sin `allow-popups`, interceptar clicks para invocar `openLink` o evitar enlaces muertos.
   - Imagenes externas: pre-procesar e incrustar como Data URLs base64 (`data:image/...`) para sortear politicas CSP y bloqueos de referrers en CDNs.
   - Tema oscuro: desactivar `mix-blend-mode: multiply` en dark mode (`:root.dark { mix-blend-mode: normal }`) para evitar que imagenes o fondos desaparezcan.
5. **Los editores siempre exportan a texto:** Cualquier manipulacion de estado interactivo debe incluir un boton visible de "Copiar como Markdown / JSON / Prompt".
6. **Principios de Motion Design:** Para micro-interacciones, curvas de aceleracion, staggers (<500ms), duraciones realistas y fisica creible, consulta la skill dedicada `motion-design`.

---

## 3. Motor de Motion Graphics & Video con Codigo

Cuando se genera una animacion para consumo multimedia o video:

### Timeline Determinista
Nunca anclar la posicion de la animacion a `Date.now()`. La funcion de renderizado debe depender unicamente del progreso normalizado `t` (de 0.0 a 1.0) o del numero de fotograma:

```javascript
function renderFrame(t, ctx, width, height) {
  ctx.clearRect(0, 0, width, height);
  // Dibujar estado exacto en el punto t
}
```

### Grabacion Nativa en un Clic
Toda animacion de motion graphics debe incluir un panel de control con:
1. Boton Play / Pause y control de velocidad.
2. Barra de reproduccion (scrubber) para avanzar o retroceder manualmente.
3. Boton "Grabar / Descargar Video" que use `canvas.captureStream(60)` y `MediaRecorder` para descargar el `.webm` inmediatamente.

### Protocolo de Captura por postMessage (Arquitectura Open-Artifacts)
Si el iframe se ejecuta dentro de un contenedor padre que orquesta capturas:
- Escucha eventos `{ type: "CAPTURE_FRAME", frameIndex, totalFrames }`.
- Renderiza el frame correspondiente y responde con `{ type: "FRAME_DATA", frameIndex, dataUrl }`.
- Si se requiere congelar una seccion del DOM que no es canvas, inyectar el listener de `html2canvas` para rasterizar y transmitir el recorte.

---

## 4. Integracion con Antigravity

- **Renderizado Inline en Chat:** Si el artefacto es compacto (menos de 500px de altura), se puede incrustar usando:
  `<agent-embed src="file:///ruta/al/artefacto.html"></agent-embed>`
  En este caso, la etiqueta `<body>` debe ser transparente (`bg-transparent`) para integrarse con el lienzo del chat.
- **Variables de Tema:** Para que el artefacto herede los colores de la aplicacion de forma transparente, aprovecha las variables de superficie (`--background`, `--card`, `--foreground`, `--border`, `--muted-foreground`).
- **CDN Permitida de Tailwind:** En el entorno Antigravity se puede incluir:
  `<script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>`

---

## 5. Indice de Guias de Referencia

En la carpeta `references/` se encuentran las pautas detalladas para cada tipo de entrega:
- `code-to-video-motion.md`: Protocolo de animacion determinista, MediaRecorder y exportacion con ffmpeg.
- `exploration-and-planning.md`: Comparativas y planes de implementacion tecnicos.
- `custom-editors.md`: Tableros de triage y editores interactivos que exportan estado.
- `data-and-charts.md`: Dashboards, tablas con ordenamiento y visualizacion de datos.
- `diagrams-and-illustrations.md`: Diagramas de flujo y arquitectura con SVG y Canvas.
- `decks.md`: Diapositivas interactivas para exposiciones navegables por teclado.
- `matching-your-style.md`: Lineamientos visuales, tipografia y paletas no genericas.
- `verify-before-delivering.md`: Protocolo de verificacion previa antes de entregar al usuario.
