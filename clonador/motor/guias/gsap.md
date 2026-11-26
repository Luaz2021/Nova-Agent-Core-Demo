# GUÍA DE VERSIÓN · GSAP 3 (3.13 o superior)

Desde 2025 GSAP es 100 % gratis, con TODOS los plugins (antes de pago): SplitText, ScrollSmoother, MorphSVG, DrawSVG, Inertia… Ya no hay "Club GSAP", ni versiones de prueba, ni registro privado de npm.

## 1. Instalar
```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/ScrollTrigger.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/SplitText.min.js"></script>
```
```js
// npm i gsap   (los plugins vienen dentro del paquete público)
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
gsap.registerPlugin(ScrollTrigger, SplitText);   // SIEMPRE registrar los plugins
```

## 2. Lo antiguo que NO debes escribir
| GSAP 2 o viejo (NO) | GSAP 3 (SÍ) |
|---|---|
| `TweenMax.to(...)`, `TweenLite`, `TimelineMax` | `gsap.to(...)`, `gsap.timeline()` |
| `ease: Power2.easeOut` | `ease: "power2.out"` |
| `ease: Back.easeInOut.config(2)` | `ease: "back.inOut(2)"` |
| `new TimelineMax({ delay: 1 })` | `gsap.timeline({ delay: 1 })` |
| `duration` como 2.º argumento: `to(el, 1, {...})` | dentro del objeto: `to(el, { duration: 1, ... })` |
| `npm i gsap@npm:@gsap/shockingly`, `.npmrc` con token | `npm i gsap` |
| Archivos "-trial" de SplitText | `gsap/SplitText` normal |
| `x: "+=100px"` en CSS transform a mano | `x`, `y`, `rotation`, `scale`, `xPercent` |

## 3. Lo básico bien escrito
```js
gsap.to(".caja", { x: 200, rotation: 360, duration: 1, ease: "power2.out" });
gsap.from(".titulo", { y: 40, opacity: 0, duration: .8, stagger: .1 });
gsap.fromTo(".barra", { scaleX: 0 }, { scaleX: 1, transformOrigin: "left center" });

const tl = gsap.timeline({ defaults: { duration: .6, ease: "power3.out" } });
tl.from(".logo", { y: -30, opacity: 0 })
  .from(".menu a", { y: -20, opacity: 0, stagger: .05 }, "<0.2")   // "<" = a la vez que el anterior
  .from(".hero h1", { y: 60, opacity: 0 }, "-=0.3");
```
Usa `autoAlpha` en vez de `opacity` cuando el elemento empieza oculto (también pone `visibility`).

## 4. ScrollTrigger
```js
gsap.from(".tarjeta", {
  y: 80, autoAlpha: 0, stagger: .15,
  scrollTrigger: { trigger: ".tarjetas", start: "top 80%", end: "bottom 60%", toggleActions: "play none none reverse" }
});
// Fijar una sección y animar mientras se hace scroll
gsap.timeline({ scrollTrigger: { trigger: ".historia", start: "top top", end: "+=2000", pin: true, scrub: 1 } })
  .to(".capa1", { xPercent: -100 }).to(".capa2", { opacity: 1 });
```
- `markers: true` solo para depurar; quítalo al terminar.
- Tras cambiar el contenido o cargar imágenes: `ScrollTrigger.refresh()`.

## 5. SplitText (reescrito en 3.13)
```js
SplitText.create(".titular", {
  type: "words, chars", mask: "lines", autoSplit: true,   // autoSplit: se vuelve a partir al cambiar el tamaño o la fuente
  onSplit(self) { return gsap.from(self.chars, { yPercent: 100, stagger: .02, duration: .6, ease: "expo.out" }); }
});
```
Con `autoSplit` crea la animación DENTRO de `onSplit` y devuélvela, para que se rehaga sola.

## 6. Responsive y limpieza
```js
const mm = gsap.matchMedia();
mm.add("(min-width: 768px)", () => { gsap.to(".panel", { x: 300 }); });   // se deshace sola al salir del rango
mm.add("(prefers-reduced-motion: reduce)", () => { gsap.globalTimeline.timeScale(100); });

const ctx = gsap.context(() => { /* animaciones */ }, contenedor);
ctx.revert();   // deshace todo (al desmontar un componente)
```
En React: `import { useGSAP } from "@gsap/react";` → `useGSAP(() => { gsap.from(".x", {...}); }, { scope: ref });` (limpia sola).

## 7. Errores típicos
1. Olvidar `gsap.registerPlugin(...)` → el plugin no hace nada sin avisar.
2. Sintaxis de TweenMax o eases con mayúscula (`Power2.easeOut`).
3. Animar `top`/`left`/`width` en vez de `x`/`y`/`scale` (va a tirones).
4. ScrollTrigger dentro de un timeline hijo: va en el timeline padre o en el tween suelto, no en los dos.
5. No respetar `prefers-reduced-motion`.
6. En React, animar en `useEffect` sin limpiar → usa `useGSAP`.
