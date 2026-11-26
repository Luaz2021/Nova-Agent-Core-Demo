# GUÍA DE VERSIÓN · CSS moderno (2024-2026)

Mucho de lo que antes necesitaba JavaScript o un preprocesador ahora es CSS puro. Úsalo antes de escribir JS.

## 1. Lo que ya NO hace falta
| Antes | Ahora |
|---|---|
| Sass solo para anidar | Anidado nativo con `&` |
| JS para "si el padre contiene X" | `:has()` |
| Media queries para componentes | Container queries |
| `100vh` (falla en el móvil) | `100dvh` / `100svh` / `100lvh` |
| JS para animar al hacer scroll | `animation-timeline: scroll()` / `view()` |
| Librerías para tooltips | Anchor positioning + `popover` |
| Hacks de márgenes en flex | `gap` en flex |
| Colores en Sass (`darken()`) | `color-mix()` y `oklch()` |

## 2. Sintaxis clave
```css
/* Anidado */
.card { padding: 1rem;
  & h3 { font-size: 1.25rem; }
  &:hover { translate: 0 -2px; }
  @media (width >= 768px) { padding: 2rem; } }

/* :has() — el padre reacciona al hijo */
.card:has(img) { grid-template-rows: auto 1fr; }
form:has(:user-invalid) button { opacity: .5; }

/* Container queries */
.lista { container-type: inline-size; }
@container (width >= 500px) { .item { display: grid; grid-template-columns: 1fr 2fr; } }
.titulo { font-size: clamp(1.5rem, 5cqi, 3rem); }   /* cqi = % del ancho del contenedor */

/* Rangos en media queries */
@media (400px <= width <= 900px) { ... }

/* Capas y alcance */
@layer reset, base, componentes;
@scope (.tarjeta) to (.contenido) { img { border-radius: 12px; } }

/* Color */
.btn { background: oklch(65% 0.2 40); border-color: color-mix(in oklch, var(--marca), black 20%); }
:root { color-scheme: light dark; --fondo: light-dark(#fff, #0b0b12); }

/* Texto */
h1 { text-wrap: balance; }  p { text-wrap: pretty; }

/* Variables con tipo (se pueden animar) */
@property --angulo { syntax: "<angle>"; initial-value: 0deg; inherits: false; }

/* Subgrid: hijos alineados con la rejilla del abuelo */
.tarjeta { display: grid; grid-row: span 3; grid-template-rows: subgrid; }
```

## 3. Animaciones sin JavaScript
```css
/* Entrada al aparecer (también desde display:none) */
.modal { transition: opacity .3s, display .3s allow-discrete; opacity: 1;
  @starting-style { opacity: 0; } }
.modal[hidden] { display: none; opacity: 0; }

/* Ligada al scroll de la página */
.barra-progreso { animation: crecer linear; animation-timeline: scroll(root); }
@keyframes crecer { from { scale: 0 1; } to { scale: 1 1; } }

/* Ligada a que el elemento entre en pantalla */
.revelar { animation: aparecer linear both; animation-timeline: view(); animation-range: entry 0% cover 30%; }

/* Transiciones entre páginas (multi-página) */
@view-transition { navigation: auto; }
.hero-img { view-transition-name: hero; }
```
En JS, para cambios dentro de la misma página: `document.startViewTransition(() => actualizarDOM())`.

## 4. HTML que sustituye JavaScript
- `<dialog>` + `dialog.showModal()`: modal con fondo (`::backdrop`), foco y Escape incluidos.
- `popover`: `<button popovertarget="menu">` + `<div id="menu" popover>`; sin JS.
- `<details name="faq">`: acordeón exclusivo (solo uno abierto) con el mismo `name`.
- `field-sizing: content`: textarea o input que crece con el texto.
- `inert`: desactiva una zona entera (útil detrás de un modal).
- `loading="lazy"` en `<img>` e `<iframe>`.

## 5. Anchor positioning (tooltips y menús pegados a un botón)
```css
.boton { anchor-name: --btn; }
.tip { position: absolute; position-anchor: --btn; position-area: top; margin-bottom: 8px;
       position-try-fallbacks: flip-block; }
```

## 6. Unidades y propiedades modernas
- `dvh`, `svh`, `lvh` (alto real del móvil), `cqi`/`cqb` (contenedor), `lh` (alto de línea).
- `inset: 0` en vez de `top:0; right:0; bottom:0; left:0`.
- `translate`, `rotate`, `scale` como propiedades sueltas (se animan por separado).
- `aspect-ratio: 16 / 9`, `accent-color`, `scrollbar-gutter: stable`, `overscroll-behavior: contain`.

## 7. Errores típicos de un modelo con CSS antiguo
1. `height: 100vh` en móviles → `100dvh`.
2. Márgenes negativos para separar elementos en flex → `gap`.
3. JS (IntersectionObserver) para animaciones de entrada sencillas → `animation-timeline: view()`.
4. Librerías de modal o tooltip → `<dialog>`, `popover`, anchor positioning.
5. Prefijos `-webkit-` en todo (salvo `-webkit-background-clip: text`, que aún se pone junto al estándar).
6. Sass solo por el anidado.

**Soporte:** lo de las secciones 1-4 funciona en Chrome, Safari y Firefox actuales. Las animaciones por scroll y el anchor positioning: Chrome y Safari recientes sí; en Firefox pueden faltar, así que ponles un estilo base que funcione sin ellas (mejora progresiva, con `@supports (animation-timeline: view())`).
