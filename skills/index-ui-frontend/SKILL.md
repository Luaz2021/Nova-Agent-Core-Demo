---
name: index-ui-frontend
description: "Conector Supremo UI/Frontend: Manifiesto Anti-Clichés, Matriz de 6 Arquetipos de Negocio (A-F), Pipeline de 5 Fases, Oráculo Cromático, Motion/Canvas y Fábrica Local a 0 Tokens."
---

# Index 01 · UI, Frontend & Design Systems (Conector Élite 2026)

## 1. Modo "Artilleria Pesada por Defecto" & Manifiesto Anti-Slop
- **Cero Interrogatorios Tecnicos al Usuario:** Si Alexander pide *"quiero una web de [X]"* con lenguaje normal, deducir automaticamente el arquetipo (**A-F**), activar toda la artilleria estetica y jamas esperar a que pida efectos, fuentes o paletas.
- **Prohibicion Absoluta de Clichés IA:** Prohibidas las tarjetas blancas planas con `shadow-md`, los textos corporativos vacios ("La solucion definitiva"), los botones con gradientes morado/cian, los avatares con iniciales y el esqueleto rancio de 3 cajitas iguales de `nova_web_engine.py`.
- **Salto Obligatorio a las Skills (`<NOVA_HOME>\antigravity\almacen\skills\`):** Prohibido quedarse solo en este indice. Antes de planificar o escribir un contrato para Qwen, hacer **1 lectura en lote en paralelo (`read_file`)** de las skills nucleares de la web a construir:
  1. `skills\gemini-ui-artisan\SKILL.md` (sorteo de direccion `draw.mjs` sobre 247 sitios reales, activos reales `assets.mjs` y juez `inspect.mjs`) y/o `skills\build-awwwards-quality-sites\SKILL.md`.
  2. `skills\visual-hierarchy\SKILL.md` + `skills\typography-system\SKILL.md` + `skills\color-palette-builder\SKILL.md`.
  3. `skills\cinematic-gsap-lenis-motion-system\SKILL.md` (si lleva scroll/motion) + `skills\ux-writing\SKILL.md`.

---

## 2. El Pipeline Quirurgico de 5 Fases (Nova Planifica -> Qwen 9B Pica -> InternVL Audita -> Bisturi)
1. **Fase 1 · Salto a Skills, Direccion de Arte & Caso (A-F):**
   - Leer las skills en paralelo, identificar el arquetipo (**A, B, C, D, E o F**) y ejecutar `node <NOVA_HOME>\antigravity\almacen\skills\gemini-ui-artisan\scripts\draw.mjs` (09/11: los COLORES ya no se piden a `nova_color_oracle.py`, que gastaba nube: los pone la biblioteca segun el tipo de negocio y corrige el contraste sola) para fijar tokens semanticos WCAG AA/AAA, escala tipografica (>= 3:1) y **1 elemento interactivo vivo ("one live thing")**.
0. **ANTES DE TODO · ELEGIR EL MODO (por este orden, el primero que encaje):**
   - **A · Web de un NEGOCIO (por defecto; 15 categorias: hosteleria, deporte, salud, belleza, alojamiento, comercio, profesionales, educacion, oficios, eventos, ocio, inmobiliaria, motor, digital, asociaciones):** Nova NO escribe HTML. (1) Pide a Alexander los datos REALES que falten (nombre, tipo de negocio, direccion, horario, servicios/destacados, precios, forma de reservar o pedir cita, telefono/Instagram, titular y NIF). (2) Copia `<NOVA_HOME>\antigravity\almacen\biblioteca_web\plantilla_datos.json` a `<carpeta>\datos.json` y la rellena SOLO con esos datos (lo que no sepa, vacio: saldra [PENDIENTE]; nunca inventar precios, horarios ni resenas). (3) Lanza: `python <NOVA_HOME>\antigravity\scripts\nova_tarea.py "<pedido>" --categoria auto --datos <carpeta>\datos.json --carpeta <carpeta>` (deduce la categoria del tipo de negocio y usa su vocabulario: tarifas, pedir cita, habitaciones...). **ESQUELETO** (estructura de pagina): lo elige solo entre editorial, inmersivo, bento, minimal y catalogo, sin repetir el de las 3 ultimas webs (`biblioteca_web\memoria_disenos.json`), segun la direccion sorteada y, si existe, el radar del sector (lanza antes `radar_web.py --sector <sector>` para que las referencias cuenten). Si Alexander pide uno: `--esqueleto <nombre>`. Sin fotos del cliente usa las del catalogo de CDN gratis con credito. Sortea la direccion de arte, Qwen escribe solo los textos que falten, se monta con bloques de calidad fija y el pipeline la verifica (InternVL PC + movil). (4) Al terminar, ensena a Alexander: direccion sorteada, textos de Qwen y avisos [PENDIENTE]. CDN permitidos: SOLO los de `biblioteca_web\cdn.json` (versiones fijas, gratis, open source).
   - **B · Alexander da una web de REFERENCIA (URL):** `python <NOVA_HOME>\antigravity\scripts\nova_tarea.py --referencia <url> --carpeta <carpeta> [--paginas 2]`. El clonador de Claude (clones_web, protegido: solo se ejecuta) la rehace en local y deja una copia en `<carpeta>\nova_referencia\<web>\` con `resumen_referencia.json` y el careo `revision.html`. Es REFERENCIA de estructura: textos, marcas, logos y fotos de la original se cambian por los datos de Alexander. Secciones flojas (<90 %) = avisar a Alexander (las arregla Claude).
   - **C · Ninguna categoria encaja todavia:** PASO 0: radar de referencias en local: `python <NOVA_HOME>ntigravity\herramientas
adar_web.py --sector <sector de draw.mjs> --max 4` (o --urls las de Alexander) y leer SOLO `resumen.txt` (estructura y ritmo; el aspecto lo pone la direccion sorteada y mandan las skills). Despues: Nova escribe `<carpeta>\secciones.json` MASTICADO (titulo, descripcion y por cada seccion `id` + `encargo` con textos exactos, layout PC/movil y colores por variable) y lanza `python <NOVA_HOME>\antigravity\scripts\nova_secciones.py --carpeta <carpeta>` (Qwen seccion a seccion, 3 intentos; repicar una: `--solo id1,id2`). **Nova es la directora de arte**: NUNCA entregar sin revisar.
     1. Al terminar (OK o FRENO), Nova MIRA las capturas de `<carpeta>\nova_tareas\<tarea>\capturas\` (PC y movil) y lee `nova_pendiente.txt` si existe.
     2. Juzga con SUS skills (este indice: anti-cliches, jerarquia tipografica, ritmo de secciones, contraste, movil) si es una web que Alexander ensenaria a un cliente. Fallos que SIEMPRE se arreglan: fotos rotas o inventadas (Unsplash con IDs inventados = rota; sin fotos reales -> sin `<img>`, usa color, tipografia o SVG), textos cortados, cajas vacias, hero sin titular, datos inventados (precios, "primera semana gratis"...), logo o letras sueltas raras.
     3. Arregla con `edit_file` en cambios de **<= 30 lineas** (pasan sin clic) y vuelve a pasar el revisor: `python <NOVA_HOME>\antigravity\scripts\nova_tarea.py --verificar --carpeta <carpeta>`.
     4. Maximo 3 rondas. Si sigue mal, para y ensena a Alexander las capturas y lo que falla (no reescribas la web entera desde la nube: eso pide permiso).
     6. **FOTOS Y EFECTOS en `secciones.json`** (detalle: `biblioteca_web\efectos.py` y `medios.py`):
        - `"fotos": {"categoria": "salud", "n": 6}` -> fotos de CDN gratis YA COMPROBADAS (Unsplash/Picsum). Tema concreto: `"buscar": "dental clinic"` (Openverse; documentales, revisarlas). En el encargo se piden como FOTO_1, FOTO_2... (Qwen pone `{{FOTO_n}}`, el sistema la URL real). NUNCA escribir URLs de fotos.
        - Bloques de scroll del kit (sin Qwen): `{"id": "proceso", "efecto": "pasos|mascara|zoom|horizontal|apiladas|video", "datos": {...}, "foto_desde": 1}`.
        - Fondo vivo de portada: `"fondo_vivo": "malla"` o `"particulas"`. Decoradores en los encargos: `data-efecto="titular|contador|relleno|magnetico"`.
        - REGLA: 1 efecto espectacular por pagina (fondo vivo, pasos, zoom, horizontal o video) + 2-3 sutiles. Video solo con uno REAL.
     5. CDN: solo los de `biblioteca_web\cdn.json` (Google Fonts, Lenis, iconos Lucide copiados en linea).
2. **Fase 2 · Planificacion y Contratos/Diffs por Seccion para `qwen3.5:9b`:**
   - Nova arma el contrato tecnico estricto por bloques/secciones (tokens CSS, estructura DOM de la hoja de direccion, copy real sin rellenos y coreografia GSAP/Lenis).
   - **UN SOLO COMANDO (no leer el codigo del pipeline, no escribir el contrato a mano):** `python <NOVA_HOME>\antigravity\scripts\nova_tarea.py "<pedido de Alexander con sus datos>" --carpeta <carpeta> --secciones <id1,id2,...> --direccion "<paleta, tipografia y estilo elegidos>"`. Mete las skills de este indice en el contrato, Qwen pica, el linter y InternVL revisan (PC, movil y secciones). Salida 0 = leer `reporte_final_ok.json`; salida 1 = FRENO: leer `nova_pendiente.txt` (en `<carpeta>\nova_tareas\<fecha>_<proyecto>\`) y avisar a Alexander. Prohibido usar `write_file` desde la nube para escupir la web entera o para "rescatar" un freno sin permiso.
3. **Fase 3 · Doble Captura Playwright + Comparacion con `blaifa/InternVL3_5:8b`:**
   - Pasar el codigo picado por `nova_core\orquestador.py` (Biome) y `inspect.mjs`.
   - Levantar Playwright y tomar las **2 capturas obligatorias** (Escritorio `1280px`/`1440px` y Movil `375px`/`390px`) mas capturas de cada seccion que va picando Qwen.
   - Pasar las capturas por **`blaifa/InternVL3_5:8b`** (`nova_puente_capturas.py`) y revisar visualmente: apuntar en una lista numerada cada desajuste (desbordes, textos pisados, jerarquia debil, contraste o falta de aire).
4. **Fase 4 · Cirugia por Lineas Exactas (`edit_file <= 35%`, Prohibido Reemplazar Todo):**
   - Con la lista de fallos apuntada tras comparar las capturas, corregir **unicamente las lineas necesarias** usando `edit_file` puntual (o enviando el diff exacto a Qwen). Prohibido terminantemente reemplazar todo el archivo.
5. **Fase 5 · Gate Final & SEO/Legal:**
   - Re-verificar capturas y `inspect.mjs` (`0 FAIL` en 1440, 768 y 390), comprobar los 8 estados interactivos, semantica HTML5 y JSON-LD (`skills\web-seo-mastery\SKILL.md`, `skills\gemini-webperf\SKILL.md`, `skills\frontend-a11y\SKILL.md`).

---

## 3. Matriz de Decisión: Los 6 Arquetipos de Negocio

### CASO A: SaaS, Herramientas de Productividad & Dashboards (Ref: Linear, Raycast)
- **Estructura:** Bento Grid modular asimétrico con bordes finos de 1px y halos de luz difuminada.
- **Paleta:** Modo oscuro titanio (#09090b / #0f1117), cristales con `backdrop-blur` y acentos láser (esmeralda, ámbar o cobalto).
- **Tipografía:** Neo-grotesca ultra limpia (`Geist`, `Plus Jakarta Sans`, `Inter`).

### CASO B: Portales Editoriales, Bibliotecas & Contenido (Ref: Kinfolk, The Row)
- **Estructura:** Ledger tipográfico asimétrico, fichas de lectura con previsualización rápida y espacio negativo generoso.
- **Paleta:** Fondos cálidos (lino lavado, pergamino, yeso, espresso amargo o pizarra marina).
- **Tipografía:** Híbrida de alta costura (`Cormorant Garamond`, `Instrument Serif` para títulos gigantes combinada con Sans geométrica).

### CASO C: E-commerce & Servicios de Alta Conversión (Ref: Aesop, Salones, Reservas)
- **Estructura:** Selección táctil fluida, wizards por pasos sin fricción y confirmación con ticket / pase descargable.
- **Paleta:** Tonos tierra o carbón grafito suave con acentos de marca (terracota, arcilla, cromo suave). Fotografía macro obligatoria.
- **Tipografía:** Sans humanista con jerarquía estricta 3:1.

### CASO D: Cinematografía, Portafolios & Experiencias Visuales (Ref: A24, Studio Freight)
- **Estructura:** Formato widescreen (2.39:1 o 16:9 inmersivo), micro-interacciones magnéticas y canvas WebGL justificado.
- **Paleta:** Grano de celuloide 35mm, negros abisales de cámara y luces de tungsteno.
- **Motion:** GSAP ScrollTrigger + Lenis smooth scroll cinematográfico.

### CASO E: Portales Institucionales, Gobierno & Servicios Públicos (Ref: GOV.UK, Suizo)
- **Estructura:** Buscador central prominente, directorios de trámites en 1-clic y jerarquía informativa inmediata.
- **Paleta:** Fondos limpios de alto contraste (blanco tiza, pizarra neutra, acento de bandera/institución). Cero adornos.
- **Accesibilidad:** Estricta WCAG AAA, legible en cualquier dispositivo bajo el sol.

### CASO F: Estudios de Autor, Nail Art & Experiencias Táctiles de Alta Gama (Ref: Aesop, Tokyo Nail Labs, Liquid Chrome)
- **Estructura:** Bento líquido asimétrico con proporciones orgánicas y contenedores de cristal esmerilado avanzado.
- **Paleta:** Gris titanio cálido (`#121113`) / resinas líquidas, con acentos en oro rosa líquido (`#e0a996`), verde salvia botánico (`#8a9a86`) y reflejos de cromo espejo dinámico.
- **Tipografía:** Híbrida de autor (`Instrument Serif` en cursiva gigante para títulos editoriales, combinada con `Space Grotesk` o `JetBrains Mono` para datos y tiempos).
- **Motion & Canvas:** Visor interactivo tipo iframe con tarjetas de selección táctil, efectos magnéticos al hover y desglose de bioseguridad.

---

## 4. Trampas de Flash & Definicion de Hecho
- **Trampas de Flash:**
  - Nunca quedarse solo en este indice al crear una web: abrir siempre las skills del almacen en paralelo.
  - `nova_web_engine.py` esta RETIRADO (08/11): webs con la biblioteca (`--categoria auto`) o `nova_secciones.py`.
  - Nunca reemplazar todo el archivo con `write_file` para arreglar un fallo visual: apuntar las lineas tras ver las capturas y aplicar `edit_file` quirurgico (`<= 35%`).
- **Definicion de Hecho:**
  - Skills del almacen leidas + direccion `draw.mjs` / tokens aplicados.
  - Codigo picado por `qwen3.5:9b`, validado en Biome (`orquestador.py`) y auditado con las 2 capturas de Playwright (Desktop + Movil) en `blaifa/InternVL3_5:8b` (`0 FAIL` en `inspect.mjs`).

## 5. Mapa de Salto Obligatorio al Almacén (`<NOVA_HOME>\antigravity\almacen\` + ruta local)
- **Dirección de Arte & Awwwards (Obligatorio en toda web nueva):** `skills\gemini-ui-artisan\SKILL.md` | `skills\build-awwwards-quality-sites\SKILL.md`
- **Jerarquía, Doctrina & Crítica Visual:** `skills\visual-hierarchy\SKILL.md` | `skills\design-doctrine\SKILL.md` | `skills\design-critique\SKILL.md` | `skills\design-qa\SKILL.md`
- **Color, Tipografía & Textos:** `skills\color-palette-builder\SKILL.md` | `skills\typography-system\SKILL.md` | `skills\ux-writing\SKILL.md`
- **Motion & 3D:** `skills\cinematic-gsap-lenis-motion-system\SKILL.md` | `skills\threejs-web-experience\SKILL.md`
- **SEO, WebPerf & Accesibilidad:** `skills\web-seo-mastery\SKILL.md` | `skills\gemini-webperf\SKILL.md` | `skills\frontend-a11y\SKILL.md`
- **React 19, Next.js 16 & Clones:** `skills\nextjs-turbopack\SKILL.md` | `skills\react-patterns\SKILL.md` | `skills\react-performance\SKILL.md` | Clonar webs: motor `<NOVA_HOME>\antigravity\clonador` (CLONAR.bat; carpeta protegida, solo se ejecuta, no se edita)
- **Sistema de Diseno, Direccion & Iconos (alta 08/11):** `skills\design-system\SKILL.md` (tokens, DESIGN.md, deteccion AI-slop) | `skills\frontend-design-direction\SKILL.md` (direccion visual de producto) | `skills\icon-system\SKILL.md` (iconos coherentes) | `skills\gemini-ui-guidelines\SKILL.md` (auditoria Vercel: foco, tipografia, cero CLS)
- **De captura a codigo, patrones & tests (alta 08/11):** `skills\gemini-vision-to-code\SKILL.md` (boceto o captura -> HTML/React) | `skills\html-to-interaction-prompts\SKILL.md` (referencias HTML -> prompts de interaccion) | `skills\frontend-patterns\SKILL.md` (estado y composicion React/Next) | `skills\react-testing\SKILL.md` (Testing Library, Vitest, MSW, axe)
