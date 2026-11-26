---
name: scroll-video-ffmpeg-webcodecs
description: Pipeline profesional de video ligado al scroll (estilo Apple/Awwwards) usando FFmpeg local -> secuencia WebP/AV1 o WebCodecs (VideoDecoder) + HTML5 Canvas + GSAP ScrollTrigger. Usar en Nivel 3 y Nivel 4 cuando haya video o animacion de producto en scroll.
---

# Scroll-Scrubbed Video (FFmpeg + Canvas + WebCodecs)

## 1. Por que NUNCA usar `video.currentTime` crudo en Nivel 3-4
- Los MP4 estandar comprimen con keyframes (GOP largos cada 1-5s): asignar `video.currentTime = p * duration` obliga al navegador a decodificar frames intermedios hacia atras y produce saltos bruscos, especialmente en Safari y Firefox.
- Solucion profesional: convertir con **FFmpeg local** a secuencia de imagenes WebP (o video all-intra / WebCodecs `VideoDecoder`) y pintar sobre `<canvas>` con `createImageBitmap()` ligado a `ScrollTrigger`.

---

## 2. Pipeline A (Estandar Universal 60fps): FFmpeg -> WebP Sequence + Canvas

### Paso 1: Preprocesar con FFmpeg en local (0 tokens)
Mantener entre **60 y 140 frames** en total para un recorrido de scroll fluido sin reventar la RAM del navegador:
- Extraer secuencia WebP optimizada para desktop (1280-1600px ancho):
  `ffmpeg -i origen.mp4 -vf "fps=24,scale=1440:-1:flags=lanczos" -c:v libwebp -lossless 0 -q:v 80 -preset picture frames/f_%04d.webp`
- Extraer variante ligera para movil (720px ancho) si el clip supera 80 frames:
  `ffmpeg -i origen.mp4 -vf "fps=20,scale=720:-1:flags=lanczos" -c:v libwebp -q:v 72 frames_mob/f_%04d.webp`
- Si necesitas video con **fondo transparente** flotando sobre la web (WebM VP9 con canal alfa):
  `ffmpeg -i origen_mov_prores4444.mov -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 1.5M -auto-alt-ref 0 salida_alpha.webm`

### Paso 2: Motor Canvas + `createImageBitmap` + GSAP ScrollTrigger
Reglas obligatorias del controlador JS:
1. **Tamano nitido con limite DPR:** `const dpr = Math.min(window.devicePixelRatio || 1, 2);` ajustar `canvas.width = rect.width * dpr` y `canvas.height = rect.height * dpr`.
2. **Precarga inteligente (Anti-congelamiento):** cargar inmediatamente el frame `0` (o primeros 15 frames) para que el hero pinte en `< 300ms`; el resto se decodifica con `createImageBitmap(blob)` en cola paralela acotada (lotes de 6-8 peticiones) y se guarda en cache hasta liberar con `bitmap.close()` al salir si hay multiples secuencias.
3. **Dibujo estilo `object-fit: cover` en Canvas:** calcular escala `Math.max(cw / img.width, ch / img.height)` para no deformar la proporcion al redimensionar.
4. **Suavizado de indice:** interpolar el progreso del scroll (`lerp`) hacia `targetFrame` en `requestAnimationFrame` solo cuando `Math.abs(currentFrame - targetFrame) > 0.01` (cero trabajo desperdiciado cuando el usuario no mueve la rueda).
5. **Integracion con `biblioteca_web`:** usar `gsap@3.12.5` + `ScrollTrigger` declarados en `cdn.json` (version fija) y sincronizar con Lenis (`lenis.on('scroll', ScrollTrigger.update)`).

---

## 3. Pipeline B (Clips Largos / Alta Resolucion): WebCodecs + All-Intra
Cuando el clip supera 180 frames o 4K:
- Codificar un MP4 **All-Intra** (`-g 1` / `-keyint_min 1`) para que cada frame sea decodificable de forma independiente sin depender de frames anteriores:
  `ffmpeg -i origen.mp4 -vf "scale=1600:-2" -c:v libx264 -g 1 -crf 22 -pix_fmt yuv420p -movflags +faststart video_intra.mp4`
- Usar WebCodecs (`VideoDecoder` + `OffscreenCanvas` en Web Worker) o fallback automatico a Pipeline A en navegadores sin soporte completo.

---

## 4. Accesibilidad, Movil y Jurado Visual
- **`prefers-reduced-motion: reduce`:** no fijar `height: 300vh` ni bloquear el scroll; mostrar un unico contenedor `100vh` con el frame clave (ej. frame central o final) pintado de forma estatica y legible.
- **Legibilidad de texto encima:** aplicar gradiente sutil (`linear-gradient`) o zona de seguridad visual para que los titulares mantengan contraste `>= 4.5:1` en cualquier frame de la secuencia.
- **Checklist QA (`nova_tarea.py --verificar`):** verificar que en `1280px` y `375px` el canvas no genera `overflow-x` ni deja franjas negras laterales al redimensionar.
