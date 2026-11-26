# GUÍA DE VERSIÓN · Tailwind CSS 4 (actual: 4.3)

Escribe SIEMPRE Tailwind 4. Lo que aprendiste es Tailwind 3: varias cosas cambiaron de nombre o ya no existen.

## 1. Instalación y configuración (ya NO hay tailwind.config.js)

En el navegador (sin compilar):
```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style type="text/tailwindcss">
  @theme {
    --color-marca: #F26B21;
    --color-tinta: #1D1D1F;
    --font-titulo: "Space Grotesk", sans-serif;
    --breakpoint-3xl: 1920px;
  }
</style>
```
En un proyecto, el CSS principal:
```css
@import "tailwindcss";
@theme { --color-marca: #F26B21; }
```
- Cada variable de `@theme` crea sus clases: `--color-marca` → `bg-marca`, `text-marca`, `border-marca`; `--font-titulo` → `font-titulo`.
- Nombres de variables: `--color-*`, `--font-*`, `--text-*` (tamaños), `--font-weight-*`, `--tracking-*`, `--leading-*`, `--radius-*`, `--shadow-*`, `--breakpoint-*`, `--container-*`, `--aspect-*`, `--ease-*`, `--spacing` (un único multiplicador).
- Ya no existen `@tailwind base; @tailwind components; @tailwind utilities;` → es `@import "tailwindcss";`.
- Plugins: `@plugin "@tailwindcss/typography";` · rutas extra: `@source "../otra-carpeta";` (el resto se detecta solo).
- Utilidades propias: `@utility nombre { ... }` (no `@layer utilities`). Variantes propias: `@custom-variant`.
- En CSS usa `var(--color-marca)`, no `theme('colors.marca')`.
- Modo oscuro por clase: `@custom-variant dark (&:where(.dark, .dark *));` (por defecto sigue al sistema).
- Vite: plugin `@tailwindcss/vite`. PostCSS: `@tailwindcss/postcss`. Autoprefixer ya va incluido.

## 2. Clases que cambiaron de nombre (lo que más fallas)

| Tailwind 3 (NO uses) | Tailwind 4 (usa) |
|---|---|
| `shadow-sm` | `shadow-xs` |
| `shadow` | `shadow-sm` |
| `rounded-sm` | `rounded-xs` |
| `rounded` | `rounded-sm` |
| `blur-sm` / `blur` | `blur-xs` / `blur-sm` |
| `backdrop-blur-sm` / `backdrop-blur` | `backdrop-blur-xs` / `backdrop-blur-sm` |
| `drop-shadow-sm` / `drop-shadow` | `drop-shadow-xs` / `drop-shadow-sm` |
| `outline-none` | `outline-hidden` (el nuevo `outline-none` es otra cosa) |
| `ring` (3 px) | `ring-3` (`ring` ahora es 1 px) |
| `bg-opacity-50`, `text-opacity-75` | `bg-black/50`, `text-tinta/75` |
| `flex-shrink-0`, `flex-grow` | `shrink-0`, `grow` |
| `overflow-ellipsis` | `text-ellipsis` |
| `decoration-slice` / `decoration-clone` | `box-decoration-slice` / `box-decoration-clone` |
| `bg-gradient-to-r` | `bg-linear-to-r` |
| `bg-[--mi-var]` | `bg-(--mi-var)` |
| `!font-bold` (importante delante) | `font-bold!` (importante al final) |
| `tw-flex` (prefijo) | `tw:flex` |
| `max-w-screen-lg` | `max-w-(--breakpoint-lg)` o `max-w-[1024px]` |

En versiones recientes también están marcadas como obsoletas: `start-0`/`end-0` → `inset-s-0`/`inset-e-0`, `bg-left-top` → `bg-top-left`, `object-left-top` → `object-top-left`, `break-words` → `wrap-break-word`, `order-none` → `order-0`.

## 3. Valores por defecto que cambiaron (ponlos tú si los necesitas)

- `border` sin color usa el color del texto (`currentColor`), ya NO gris. Escribe siempre el color: `border border-gray-200`.
- `ring` sin color también usa `currentColor`, y mide 1 px.
- El texto de ejemplo de los inputs (placeholder) es el color del texto a media opacidad, no gris-400.
- Los `<button>` tienen el cursor normal: añade `cursor-pointer` si lo quieres de mano.
- `hover:` solo se aplica en dispositivos con ratón (en el móvil, tocar no activa el hover).
- `space-y-*` y `divide-y-*` cambiaron su selector: con elementos en línea o con huecos raros, mejor `flex flex-col gap-*`.
- Las variantes se aplican de izquierda a derecha: `*:first:pt-0`, no al revés.
- Necesita navegadores modernos: Safari 16.4+, Chrome 111+, Firefox 128+.

## 4. Lo nuevo que ya puedes usar

- **Container queries** (sin plugin): el padre `@container`, los hijos `@sm:grid-cols-2 @lg:grid-cols-3`.
- **Degradados:** `bg-linear-to-r from-violeta to-cian`, en ángulo `bg-linear-45`, `bg-radial`, `bg-conic`.
- **3D:** `perspective-distant`, `rotate-x-12`, `rotate-y-6`, `transform-3d`.
- **Variantes:** `not-hover:`, `in-[.grupo]:` (en lugar de `group-[]`), `nth-3:`, `starting:` (estilo inicial de entrada para animar al aparecer), `inert:`, `**:` (todos los descendientes, antes `[&_*]:`).
- **Formularios:** `field-sizing-content` (textarea que crece sola).
- **4.1:** sombras de texto `text-shadow-sm`, `text-shadow-lg/50`, y máscaras `mask-b-from-50%`, `mask-radial-*`.
- **Colores:** la paleta usa `oklch` (más vivos). Con hex exactos sigue igual: `bg-[#F26B21]`.
- `aspect-video` y `aspect-[4/3]` vienen de serie (ya no hace falta el plugin aspect-ratio).
- Espaciado dinámico: `w-17`, `mt-13`, `grid-cols-15` funcionan sin configurar nada.

## 5. Errores típicos de un modelo con Tailwind 3 en la cabeza

1. Crear `tailwind.config.js` o `tailwind.config = {...}` en un `<script>`. En v4 es `@theme` dentro del CSS.
2. Usar `shadow`, `rounded`, `blur`, `ring` con su tamaño antiguo (ver la tabla).
3. `bg-opacity-*` / `text-opacity-*`: ya no existen.
4. `border` sin color esperando que salga gris.
5. `bg-gradient-to-*`: usa `bg-linear-to-*`.
6. `!` delante de la clase: ahora va detrás.
7. `bg-[--var]`: ahora es `bg-(--var)`.
8. Instalar el plugin de container queries o el de aspect-ratio: ya vienen dentro.

## 6. Ejemplo completo correcto (v4)

```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style type="text/tailwindcss">
  @theme { --color-noche: #0B0B12; --color-violeta: #8B5CF6; --color-cian: #22D3EE; --font-titulo: "Space Grotesk", sans-serif; }
</style>
<section class="@container bg-noche py-20">
  <div class="mx-auto grid max-w-[1200px] gap-5 px-5 @md:grid-cols-3">
    <article class="rounded-3xl border border-white/10 bg-white/5 p-7 shadow-sm backdrop-blur-sm">
      <h3 class="font-titulo text-2xl font-semibold text-white">Título</h3>
      <p class="mt-2 text-white/60">Texto secundario.</p>
      <button class="mt-6 cursor-pointer rounded-xl bg-linear-to-r from-violeta to-cian px-6 py-3 font-semibold text-white outline-hidden">Empezar</button>
    </article>
  </div>
</section>
```
