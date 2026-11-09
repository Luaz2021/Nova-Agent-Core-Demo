---
name: index-ui-frontend
description: "Conector Supremo UI/Frontend: Manifiesto Anti-Clichés, Matriz de 6 Arquetipos de Negocio (A-F), Flujo de Webs con Biblioteca Local, Motion/Canvas y Fábrica Local a 0 Tokens."
---

# Index 01 · UI, Frontend & Design Systems (Conector Élite 2026)

## 1. Modo "Artilleria Pesada por Defecto" & Manifiesto Anti-Slop
- **Cero Interrogatorios Tecnicos al Usuario:** Si el usuario pide *"quiero una web de [X]"* con lenguaje normal, deducir automaticamente el arquetipo (**A-F**), activar toda la artilleria estetica y jamas esperar a que pida efectos, fuentes o paletas.
- **Salto Obligatorio a las Skills (`<NOVA_HOME>/antigravity/skills/`):** Prohibido quedarse solo en este indice. Antes de planificar o escribir un contrato para Qwen, hacer **1 lectura en lote en paralelo (`read_file`)** de las skills nucleares de la web a construir:
  1. `skills\gemini-ui-artisan\SKILL.md` (sorteo de direccion `draw.mjs` sobre 247 sitios reales, activos reales `assets.mjs` y juez `inspect.mjs`) y/o `skills\build-awwwards-quality-sites\SKILL.md`.
  2. `skills\visual-hierarchy\SKILL.md` + `skills\typography-system\SKILL.md` + `skills\color-palette-builder\SKILL.md`.
  3. `skills\cinematic-gsap-lenis-motion-system\SKILL.md` (si lleva scroll/motion) + `skills\ux-writing\SKILL.md`.

---

## 2. El Flujo de Webs de Nova (Capa 0 primero, la nube dirige y repara)
0. **ANTES DE TODO · ELEGIR EL MODO (el primero que encaje):**
   - **A · Web de un NEGOCIO (por defecto; 15 categorias: hosteleria, deporte, salud, belleza, alojamiento, comercio, profesionales, educacion, oficios, eventos, ocio, inmobiliaria, motor, digital, asociaciones):** Nova NO escribe HTML. (1) Pide al usuario los datos REALES que falten (nombre, tipo de negocio, direccion, horario, servicios, precios, forma de reservar, telefono/redes, titular). (2) Copia `<NOVA_HOME>/antigravity/almacen/biblioteca_web/plantilla_datos.json` a `<carpeta>/datos.json` y la rellena SOLO con esos datos (lo que no sepa, vacio: saldra [PENDIENTE]; nunca inventar precios, horarios ni resenas). (3) Lanza: `<PYTHON> <NOVA_HOME>/antigravity/almacen/biblioteca_web/montar.py --datos <carpeta>/datos.json --categoria auto --out <carpeta>/index.html`. La biblioteca elige sola esqueleto, estilo, paleta, fotos con licencia libre (con credito) y efectos segun el tipo de negocio, sin repetir los ultimos. (4) Ensena al usuario el resultado y los avisos [PENDIENTE]. CDN permitidos: SOLO los de `biblioteca_web/cdn.json`.
   - **B · El usuario da una web de REFERENCIA (URL + "referencia", "parecida a", "al estilo de"):** solo entonces la nube puede escribir la web (el hook lo permite). Se copian PRINCIPIOS (estructura, ritmo, jerarquia, densidad), nunca marcas, logos, textos ni fotos de la original: todo se cambia por los datos del usuario.
   - **C · Ninguna categoria encaja:** Nova escribe hasta 150 lineas por archivo con `edit_file`/`write_file`; lo grande y autocontenido lo pica el obrero local (`<PYTHON> <NOVA_HOME>/antigravity/scripts/nova_local_worker.py --task "<encargo masticado por seccion>"`). Si el usuario dice "escribelo tu", lo escribe Nova.
1. **Revision obligatoria (Nova es la directora de arte):** nunca entregar sin mirar. Si hay MCP de Playwright, capturas a 1280px y 375px; si no, pedir al usuario que la abra. Fallos que SIEMPRE se arreglan: fotos rotas o inventadas, textos cortados, cajas vacias, hero sin titular, datos inventados, desbordes horizontales en movil.
2. **Cirugia por lineas (`edit_file` <= 30 lineas por cambio):** arreglar solo lo necesario y volver a mirar. Maximo 3 rondas; si sigue mal, parar y ensenar al usuario lo que falla (no reescribir la web entera desde la nube sin permiso).
3. **Gate final & SEO/Legal:** semantica HTML5, estados interactivos, JSON-LD y accesibilidad (`skills/web-seo-mastery/SKILL.md`, `skills/gemini-webperf/SKILL.md`, `skills/frontend-a11y/SKILL.md`).

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
  - Nunca quedarse solo en este indice al crear una web: abrir siempre las skills del almacen en paralelo.
  - Nunca reemplazar todo el archivo con `write_file` para arreglar un fallo visual: apuntar las lineas tras ver las capturas y aplicar `edit_file` quirurgico (`<= 35%`).
  - Skills del almacen leidas + direccion `draw.mjs` / tokens aplicados.

## 5. Mapa de Salto Obligatorio a las Skills (`<NOVA_HOME>/antigravity/` + la ruta `skills/...` de cada entrada)
- **Dirección de Arte & Awwwards (Obligatorio en toda web nueva):** `skills\gemini-ui-artisan\SKILL.md` | `skills\build-awwwards-quality-sites\SKILL.md`
- **Jerarquía, Doctrina & Crítica Visual:** `skills\visual-hierarchy\SKILL.md` | `skills\design-doctrine\SKILL.md` | `skills\design-critique\SKILL.md` | `skills\design-qa\SKILL.md`
- **Color, Tipografía & Textos:** `skills\color-palette-builder\SKILL.md` | `skills\typography-system\SKILL.md` | `skills\ux-writing\SKILL.md`
- **Motion & 3D:** `skills\cinematic-gsap-lenis-motion-system\SKILL.md` | `skills\threejs-web-experience\SKILL.md`
- **SEO, WebPerf & Accesibilidad:** `skills\web-seo-mastery\SKILL.md` | `skills\gemini-webperf\SKILL.md` | `skills\frontend-a11y\SKILL.md`
- **Sistema de Diseno, Direccion & Iconos (alta 08/11):** `skills\design-system\SKILL.md` (tokens, DESIGN.md, deteccion AI-slop) | `skills\frontend-design-direction\SKILL.md` (direccion visual de producto) | `skills\icon-system\SKILL.md` (iconos coherentes) | `skills\gemini-ui-guidelines\SKILL.md` (auditoria Vercel: foco, tipografia, cero CLS)
- **De captura a codigo, patrones & tests (alta 08/11):** `skills\gemini-vision-to-code\SKILL.md` (boceto o captura -> HTML/React) | `skills\html-to-interaction-prompts\SKILL.md` (referencias HTML -> prompts de interaccion) | `skills\frontend-patterns\SKILL.md` (estado y composicion React/Next) | `skills\react-testing\SKILL.md` (Testing Library, Vitest, MSW, axe)
