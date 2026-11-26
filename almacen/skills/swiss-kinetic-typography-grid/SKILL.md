---
name: swiss-kinetic-typography-grid
description: Diseno grafico editorial, reticulas suizas asimetricas con CSS Subgrid, tipografia variable reactiva y composicion sin cajas genericas (Ref. Josef Muller-Brockmann, Studio Dumbar, DIA Studio, ECAL/ZHdK).
---

# Swiss Grid & Kinetic Typography (Nivel 2-4)

Skill de diseno grafico y composicion tipografica para romper el aspecto "web generica de cajas centradas" e inyectar rigor editorial suizo con movimiento cinetico controlado.

## 1. Sistema Reticular Suizo (CSS Grid + Subgrid)
- **Asimetria intencional con ritmo matematico:** usar reticulas de 12 columnas en desktop (`grid-template-columns: repeat(12, minmax(0, 1fr))`) y colapsar limpiamente a 4 columnas en movil (`@media (max-width: 759px)`).
- **Alineacion real entre tarjetas heterogeneas:** cuando una fila tiene bloques con titulo, subtitulo, metadato y CTA, usar `grid-template-rows: subgrid; grid-row: span 4;` en el hijo para que las lineas base y los botones de toda la fila queden milimetricamente nivelados.
- **Lineas estructurales (Hairlines), no sombras:** sustituir `box-shadow` repetitivos por divisiones limpias `1px solid color-mix(in srgb, var(--ink) 14%, transparent)` y aire generoso (`padding` amplio, `gap` consistente).
- **Regla de Oro Anti-Caja:** prohibido encerrar cada parrafo y cada feature dentro de una tarjeta redondeada. Dejar que la tipografia, las proporciones y el espacio negativo respiren directo sobre `--bg`.

---

## 2. Tipografia Escala Monumental & Variable Fonts
- **Contraste de escala real:** titular Hero `clamp(2.8rem, 8.5vw, 8.5rem)` con `line-height: 0.9` a `0.98` y `letter-spacing: -0.03em` a `-0.045em`; cuerpo legible en `1rem - 1.125rem` (`45ch - 75ch` maximo por linea, nunca parrafos de lado a lado).
- **Axes de Variable Fonts (`font-variation-settings`):** usar fuentes variables OFL (ej. `Plus Jakarta Sans`, `Instrument Sans`, `Fraunces`, `Recursive`, `Syne`, `Inter`) y mapear peso (`wght`), ancho (`wdth`) o inclinacion (`slnt`) a variables CSS `--p` de scroll o puntero con transicion suave.
- **Advertencia de rendimiento:** animar `font-variation-settings` solo en un **titular puntual o banda cinetica corta**, nunca en parrafos completos (genera re-layout de texto). Para letras/palabras que entran en viewport, usar siempre `overflow: hidden` en linea + `transform: translate3d(0, 100%, 0)` en GPU.

---

## 3. Patrones Cineticos (Studio Dumbar / DIA / Obys)
1. **Mask Reveal por Linea/Palabra:** envolver lineas en `.clip-line` (`overflow: hidden`) y elevar el hijo con `cubic-bezier(0.16, 1, 0.3, 1)` al entrar en viewport o al ritmo de `ScrollTrigger`.
2. **Marquee Tipografico Tactil (Kinetic Ticker):** cinta continua con duplicacion exacta en DOM (minimo 2 copias + `aria-hidden="true"` en la duplicada), pausada al `hover`, enfocable sin trap y detenida en `prefers-reduced-motion: reduce`.
3. **Indice Numerado Editorial (`01 / 02 / 03`):** usar `font-variant-numeric: tabular-nums` y fuente monoespaciada sutil (`JetBrains Mono` / `IBM Plex Mono`) para coordenadas, tiempos y indices tecnicos.

---

## 4. Accesibilidad & Movil
- En `< 760px`, reducir titulares gigantes mediante `clamp(...)` para evitar palabras partidas en 2 lineas o `overflow-x`.
- Si una palabra larga no cabe en movil, asegurar `overflow-wrap: break-word` sin romper `hyphens` en titulares clave.
- `prefers-reduced-motion: reduce`: texto 100% visible en su estado final desde el frame 0 (`transform: none; opacity: 1`).
