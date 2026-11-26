---
name: index-ui-frontend
description: "Conector UI/Frontend: Nova directora de arte con el ESTUDIO WEB (ficha validada, skills por fase comprobadas, Qwen pica HTML, revisor en PC y movil), Nivel 4 por defecto, biblioteca como caja de herramientas, 6 arquetipos y mapa del almacen."
---

# Index 01 · UI, Frontend & Design Systems

## 1. Webs: Nova es la DIRECTORA DE ARTE (15/11, acuerdo con el usuario)
- **CRITERIO PRIMERO (manda sobre todo):** la web entra por los ojos, como la comida. Antes de colores o efectos: que compra el cliente (producto, espacio, experiencia, confianza o catalogo), que ve en los primeros 3 segundos y para que escala (barrio, cadena, premium). Panaderia = el pan grande y de cerca, limpio; gym = el espacio y las maquinas; lo cargado solo en e-commerce. Una web bonita que no transmite no sirve.
- **Acabado de nivel 4 siempre**, pero el EFECTO lo decide lo que se compra: espacio/experiencia -> pieza viva del sitio (video-scroll, canvas, webgl, 3d); producto -> foto o video del producto, el efecto nunca lo tapa.
- **Nova disena con lo que sabe**, como una profesional: concepto, referencias reales, paleta, tipografia, una pieza principal y composicion variada. **La biblioteca es su caja de herramientas** (efectos, CDN, buscador de fotos), NO un molde: se coge solo lo que haga falta. Nada de galerias internas tipo "apple-dark-showcase".
- **Qwen pica el volumen** (HTML de listas, cartas, fichas, formularios) con las clases que Nova definio. **El codigo revisa lo medible**; Nova y el usuario juzgan el gusto mirando 2 hojas de capturas.
- **Prohibido** (lo bloquea el estudio): neones lima/cian/magenta, Inter/Poppins/Montserrat/Space Grotesk como titular, repetir tipografia o acento de las ultimas webs, fotos con fondo blanco sobre web oscura, precios/telefonos/emails que el usuario no dio, contenido que nunca aparece al bajar.

## 2. El ESTUDIO WEB (un solo comando, pasos en orden)
`<PYTHON> "<NOVA_HOME>/antigravity/herramientas/estudio_web/estudio.py" <orden> <carpeta>`
1. `ficha <carpeta> "<pedido>"` -> crea `estudio/ficha.json` (empieza por `criterio`), dice que skills leer, que NO repetir y las correcciones del usuario en webs parecidas (`herramientas/datos/estudio_web/casos.json`).
2. Lee en 1 lote las skills que pide (lo comprueba la telemetria del hook: sin leerlas no valida).
3. `fotos <carpeta> --buscar "tema en ingles|otro tema"` -> UNA hoja numerada: mirala y elige.
4. `validar <carpeta>` -> contraste, neones, tipografias reales, repeticion, fotos. **Ensena el resumen al usuario y espera su "vale".** Crea `estudio/estilos/00_tokens.css`.
5. Nova escribe `estudio/estilos/10_*.css, 20_*.css...` (cada uno <= 150 lineas, con `/* qwen: .clase = uso */`), `estudio/secciones.json` y sus secciones a mano en `estudio/secciones/<id>.html` (portada, pieza viva, nav, pie).
6. `picar <carpeta>` (Qwen, 3 intentos por seccion; lo que no salga va a `estudio/pendientes.md`) -> `montar <carpeta>` -> `revisar <carpeta>`.
7. `revisar` baja por la web en PC (1280) y movil (390): que el primer pantallazo ensene lo que se compra, ortografia (tildes, ñ, ¿¡), fotos repetidas, demasiados botones de tienda, librerias sin usar, desbordes, huecos, contenido invisible, contraste medido en pixeles, colores fuera de paleta, fuentes que no cargan, fotos pixeladas, datos inventados, fotos descritas por InternVL. Exige haber leido las skills de cierre. Arreglos pequenos, max 3 rondas, y se ensenan `estudio/capturas/hoja_pc.jpg` y `hoja_movil.jpg`.
- `estudio.py herramientas` = lo que hay en la biblioteca (bloques de scroll, decoradores `data-efecto`, CDN, FFmpeg, WebGL).
- **Otros modos (solo si el usuario lo pide):** A) web rapida de negocio con la biblioteca: `nova_tarea.py "<pedido>" --categoria auto --datos <carpeta>\datos.json --carpeta <carpeta>`. B) web de referencia (URL): `nova_tarea.py --referencia <url> --carpeta <carpeta>` (clones_web, solo se ejecuta).

---

## 3. Matriz de Decision: Los 6 Arquetipos de Negocio (A–F) · inspiracion, no plantilla
- **CASO A · SaaS, Productividad & Dashboards (Linear, Raycast, Vercel):** Bento asimetrico, bordes 1px reactivos/conicos, `Cmd+K`, modo titanio (`#09090b`) o editorial tecnico, neo-grotesca para texto (`Geist`, `Plus Jakarta Sans`).
- **CASO B · Editoriales, Estudios & Contenido (Kinfolk, Obys, DIA):** Reticula suiza Subgrid, espacio negativo generoso, fondos calidos/editorial oscuro, display serif gigante (`Cormorant Garamond`, `Instrument Serif`) + sans.
- **CASO C · E-commerce & Servicios de Alta Conversion (Aesop, Reservas):** Seleccion tactil, ticket/confirmacion sin friccion, fotografia macro real o WebGL/3D de producto.
- **CASO D · Flagships Inmersivos, Portfolios & Experiencias (Lusion, Malvah, Immersive Garden):** Widescreen, canvas FFmpeg/WebGL + GLSL, Lenis + ScrollTrigger coreografiado.
- **CASO E · Portales Institucionales & Servicios Publicos (GOV.UK, Suizo):** Buscador central, contraste WCAG AAA, cero adornos.
- **CASO F · Estudios de Autor, Nail Art & Experiencias Tactiles:** Bento organico, `Instrument Serif` cursiva + mono para detalles, micro-interacciones magneticas.

---

## 4. Trampas de Nova & Definicion de Hecho
- Nunca bajar en silencio a una web generica: el default es Nivel 4 con el estudio.
- Nunca `video.currentTime` crudo para scroll-scrubbing (FFmpeg WebP/WebCodecs + `<canvas>`).
- Nunca reescribir una web entera desde la nube tras un freno: leer `estudio/revision.md` o `pendientes.md` y micro-editar o avisar. `nova_web_engine.py`, `gema_esqueleto` y la "Gema" markdown estan retirados.
- **Hecho =** ficha validada con el "vale" del usuario + `revisar` en OK + hojas de capturas ensenadas.

---

## 5. Mapa del Almacen (`<NOVA_HOME>/antigravity/almacen/skills/`) · el estudio dice cuales son obligatorias en cada fase
- **Entrada (la directora):** `nova-web-director` (corta: te manda al estudio)
- **Direccion (obligatorias):** `frontend-design-direction` | `typography-system` | `color-palette-builder`
- **Pieza viva (segun ficha):** `scroll-video-ffmpeg-webcodecs` | `webgl-shaders-postprocessing` | `threejs-web-experience` | `gemini-motion-artifacts`
- **Movimiento (al construir):** `site-motion-excellence-director` | `motion-design` | `cinematic-gsap-lenis-motion-system` | `gsap-scrolltrigger` | `web-motion-auditor`
- **Cierre (obligatorias):** `design-critique` | `frontend-a11y` | `web-seo-mastery` | `gemini-webperf`
- **Opcionales de direccion:** `build-awwwards-quality-sites` | `swiss-kinetic-typography-grid` | `flagship-saas-experimental-patterns` | `moodboard-builder` | `gemini-brand-tokens` | `brand-to-design-md` | `gemini-ui-artisan` | `design-doctrine` | `web-legal-compliance`
- **Jerarquia, QA & Textos:** `visual-hierarchy` | `design-qa` | `ux-writing`
- **React 19, Next.js 16 & Clones:** `nextjs-turbopack` | `react-patterns` | `react-performance` | Clonar webs: `clones_web` (solo ejecutar)
- **Sistema de Diseno, Vision & Tests:** `design-system` | `icon-system` | `gemini-ui-guidelines` | `gemini-vision-to-code` | `html-to-interaction-prompts` | `frontend-patterns` | `react-testing` | `figma-nova-bridge`
