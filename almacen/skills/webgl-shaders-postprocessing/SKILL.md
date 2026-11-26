---
name: webgl-shaders-postprocessing
description: Direccion tecnica WebGL nivel Awwwards (Three.js + GLSL ShaderMaterial + EffectComposer + CanvasTexture + Theatre.js / Rive) con control estricto de memoria, DPR y rendimiento 60fps. Activar por defecto en Nivel 4.
---

# WebGL, Shaders GLSL & Post-Procesado (Nivel 4)

Skill tecnica para construir experiencias inmersivas de Nivel 4 (referencia Lusion, Malvah, Immersive Garden, Bruno Simon) sin fugas de memoria ni caidas de FPS en portatiles reales.

## 1. Arquitectura Limpia de Escena Three.js
Todo modulo WebGL debe encapsularse en una clase o fabrica con ciclo de vida explicito (`init()`, `resize()`, `update()`, `destroy()`):
1. **Renderer optimizado:**
   - `new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' })`
   - `renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))` (en movil/tactil bajar a `Math.min(dpr, 1.5)`).
   - `renderer.outputColorSpace = THREE.SRGBColorSpace;` y `renderer.toneMapping = THREE.ACESFilmicToneMapping;`.
2. **Pausa automatica fuera de pantalla:** usar `IntersectionObserver` sobre el canvas y `document.visibilitychange` para detener `requestAnimationFrame` cuando no esta visible.
3. **Limpieza obligatoria (`destroy` / unmount):** recorrer `scene.traverse()` llamando `.dispose()` en cada `geometry`, `material`, `texture` y `EffectComposer` / `RenderTarget`.

---

## 2. Shaders GLSL (`ShaderMaterial`) con Proposito
Usar shaders solo cuando aporten tacto fisico o narrativa visual (no ruido arcoiris gratis):
- **Uniforms estandar limpios:**
  - `uTime` (float, delta acumulado acotado para evitar perdida de precision en sesiones largas)
  - `uResolution` (`vec2`)
  - `uMouse` (`vec2` suavizado con lerp `0.08`, nunca salto brusco)
  - `uScrollVelocity` / `uProgress` (conectado a Lenis o `ScrollTrigger`)
  - `uColorA`, `uColorB`, `uAccent` (alimentados desde las variables CSS `--bg`, `--surface`, `--accent` para coherencia total con la Biblia Visual)
- **Patrones recomendados:**
  - *Liquid / Cloth Distortion* sobre planos de imagen al hacer hover o scroll (`uScrollVelocity`).
  - *Simplex / Curl Flow Field* sutil en fondo abisal para marcas tech/editoriales oscuras.
  - *Film Grain + Vignette* procedimental en fragment shader para evitar acabados plasticos.

---

## 3. Texturas Dinamicas, Post-Procesado y Runtimes Complementarios
- **`CanvasTexture` & `VideoTexture`:** si un modelo 3D muestra una interfaz o video vivo, dibujarlo en `<canvas>` 2D offscreen y marcar `texture.needsUpdate = true` unicamente cuando haya cambios.
- **`EffectComposer`:** usar passes ligeros (`RenderPass`, `UnrealBloomPass` con umbral alto `threshold >= 0.85` y `strength <= 0.35`, o shader final de grano/aberracion cromatica leve al acelerar el scroll). Prohibido apilar >3 passes pesados en tiempo real.
- **`Theatre.js` (opcional en Nivel 4 coreografiado):** cuando una escena 3D tiene multiples actos de camara ligados al scroll, separar las curvas clave en estado serializado de Theatre.js y ligar `sheet.sequence.position` al progreso de `ScrollTrigger`.
- **`Rive` (`.riv`):** ideal para ilustraciones vectoriales interactivas o emblemas con maquina de estados reactiva al cursor/estado sin cargar un mundo WebGL entero.

---

## 4. Degradacion Inteligente y Movil
- **`prefers-reduced-motion: reduce`:** desactivar distorsion por velocidad, mantener camara en pose heroica y renderizar un unico frame nitido (sin bucle RAF continuo).
- **WebGL Fallback:** envolver inicializacion en `try/catch`; si no hay contexto WebGL2/WebGL, mostrar fallback CSS/imagen de alta calidad definido en la misma seccion.
- **Cero clipping y escala metrica (`index-motion-3d`):** 1 unidad = 1 metro, camara calculada segun altura del sujeto (`dist = (h / 2) / tan(fov / 2)`), nunca saltos instantaneos de camara dentro de mallas.
