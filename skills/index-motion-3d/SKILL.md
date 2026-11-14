---
name: index-motion-3d
description: "Indice Macro Motion & 3D: Animaciones GSAP (Core, Timeline, ScrollTrigger, React), Lenis smooth scroll, micro-interacciones y escenas Three.js."
---

# Index 02 · Motion Design, GSAP, Lenis & Three.js (1-Hop Router)

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **Salto Obligatorio al Almacen:** Al construir animaciones web, scroll narrativo o escenas 3D, queda **prohibido** quedarse solo en este resumen: abrir obligatoriamente `skills\cinematic-gsap-lenis-motion-system\SKILL.md` (y `skills\threejs-web-experience\SKILL.md` si lleva WebGL) antes de redactar el contrato para `qwen3.5:9b`.
- **Rendimiento a 60fps:** Animar exclusivamente propiedades compuestas por GPU (`transform: translate3d, scale, rotate` y `opacity`). Prohibido animar `top`, `left`, `width`, `height` o `margin` (causan *layout thrashing*).
- **GSAP en React / Next.js:** Usar siempre el hook oficial `useGSAP()` o `gsap.context()` acotado a un `ref` contenedor para garantizar limpieza automatica (`revert()`) al desmontar. Registrar plugins (`gsap.registerPlugin(ScrollTrigger)`) una sola vez fuera del render.
- **Accesibilidad de Movimiento:** Envolver coreografias intensas en `gsap.matchMedia()` respetando `prefers-reduced-motion: reduce` con fallback instantaneo sin mareo.
- **Three.js / WebGL:** Disponer explicitamente geometrias, materiales y texturas (`dispose()`) al desmontar escena, limitar `devicePixelRatio` a `Math.min(window.devicePixelRatio, 2)` y pausar el `requestAnimationFrame` cuando el canvas salga del viewport (`IntersectionObserver`).

## Trampas de Flash (errores reales ya cometidos)
- Camara calculada, no a ojo: `dist = (alto / 2) / tan(fov / 2)`, FOV 35, distancia >= 3.2 m. Nunca saltos de camara sin transicion (clipping dentro del modelo).
- Comprobar la orientacion de ejes: la camara va delante de la cara del modelo (`rotation.y = Math.PI` si mira al reves).
- Sets aislados por coordenadas (acto 1 x=0, 2 x=100, 3 x=200, 4 x=300) y actores fuera de plano con `visible = false`.
- Escala 1 unidad = 1 metro y un unico bloque `CONFIG` editable al inicio.
- Blender `bpy`: usar enums estables (`BLENDER_EEVEE`, `BLENDER_WORKBENCH`), nunca nombres experimentales.

## Definicion de hecho
- Hoja de contacto con un fotograma por acto revisada antes de entregar: sin clipping ni geometria tapando textos o subtitulos.
- Solo se animan `transform` y `opacity`; `dispose()` y limpieza de `requestAnimationFrame` al desmontar.

## 2. Mapa de Salto al Almacen (`<NOVA_HOME>\antigravity\almacen\` + la ruta `skills\...` de cada entrada; copia local, nunca leer de G:)
Abrir en paralelo con `read_file` al planificar o auditar motion/3D (y validar el resultado final con capturas en `blaifa/InternVL3_5:8b` + `edit_file <= 35%`):
- **Suite Oficial GSAP:** `skills\gsap-core\SKILL.md` | `skills\gsap-timeline\SKILL.md` | `skills\gsap-scrolltrigger\SKILL.md` | `skills\gsap-react\SKILL.md` | `skills\gsap-plugins\SKILL.md` | `skills\gsap-utils\SKILL.md` | `skills\gsap-performance\SKILL.md` | `skills\gsap-frameworks\SKILL.md`
- **Sistemas Cinematicos & Lenis:** `skills\cinematic-gsap-lenis-motion-system\SKILL.md` | `skills\site-motion-excellence-director\SKILL.md` | `skills\motion-design\SKILL.md` | `skills\web-motion-auditor\SKILL.md`
- **3D & Artefactos Interactivos:** `skills\threejs-web-experience\SKILL.md` | `skills\gemini-motion-artifacts\SKILL.md` | `skills\procedural-film\SKILL.md`
