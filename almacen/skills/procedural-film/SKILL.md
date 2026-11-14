---
name: procedural-film
description: "Generador de video procedural y pixel art a 60fps en codigo puro (HTML5 Canvas 2D + Web Audio API, 0 assets)."
trigger: model_decision
---

# Procedural Film & Web Audio Synthesis Engine (Zero Media Assets)

Esta habilidad permite transformar un tema, guion o concepto en una pelicula vertical animada (formato Reel/TikTok de 30 segundos) generada 100% mediante codigo determinista en el navegador, sin descargar ni requerir un solo archivo de video, imagen o audio externo.

---

## 1. Filosofia de Cero Assets (Pure Code Media)

1. **Cada pixel se dibuja en `<canvas>`:** Toda forma, personaje, paisaje o transicion se genera mediante primitivas de Canvas 2D (curvas de Bezier, gradientes, transformaciones parametricas y sistemas de particulas matematicos).
2. **Cada sonido se sintetiza en tiempo real:** Toda melodia, percusion, efecto de transicion o ambiente se genera mediante la **Web Audio API** (`AudioContext`, `OscillatorNode`, `GainNode`, generadores de ruido blanco/rosa y emuladores de ondas cuadradas/triangulares).
3. **Autocontenido y Ligero:** Un video completo de 30 segundos ocupa menos de 50 KB de codigo JavaScript/HTML, corre instantaneamente a 60 fps y no requiere renderizados pesados con `ffmpeg` para su previsualizacion interactiva.

---

## 2. Modos de Produccion Visual

### A. Animacion Vectorial Matematica
- Generacion de formas organicas fluidas, geometria sagrada, transiciones de escala, revelaciones de texto y simulaciones fisicas (ondas, fluidos, gravedad, particulas).
- Control milimetrico del tiempo mediante un contador de fotogramas (`frame`) o timestamp absoluto (`performance.now()`).

### B. Photo-Doodles (Overlay Procedural sobre Foto Fija)
- Se toma una imagen base estatica (captura de producto, apartamento o foto real).
- Se superpone una capa de Canvas transparente donde se dibujan animaciones procedurales en bucle: lineas de contorno electricas, garabatos luminosos, flechas cineticas, brillos y ondas de sonido que interactuan con la imagen.

### C. Retro Pixel Art & Chiptune (Estilo NES 8-bit)
- Renderizado de baja resolucion reescalado con `image-rendering: pixelated`.
- Paleta de color retro restringida (NES o Game Boy).
- Sintetizador Chiptune nativo con 4 canales clasicos de audio:
  - Canal 1 y 2: Ondas de pulso/cuadradas (melodia y contramelodia).
  - Canal 3: Onda triangular (linea de bajo retro).
  - Canal 4: Generador de ruido pseudoaleatorio (charles, caja y percusion chiptune).

---

## 3. Pipeline de Ejecucion en 3 Fases

1. **Fase 1: Storyboard y Cronograma (Timing Budget):**
   - Definir los 30 segundos divididos en actos (Gancho: 0-3s, Nudo/Desarrollo: 3-24s, Climax/Llamada a la accion: 24-30s).
   - Calcular el presupuesto de frames a 30 o 60 fps.
2. **Fase 2: Generacion del Motor Canvas (Bucle de Render):**
   - Implementar el canvas escalable vertical (1080x1920 con soporte responsive).
   - Funciones de dibujo aisladas por escena con interpolaciones matematicas suaves (ease-in-out, springs).
3. **Fase 3: Partitura y Sintesis Web Audio:**
   - Crear el grafo de audio con disparadores sincronizados con los frames de animacion (sound triggers al impactar o cambiar de escena).
   - Generacion de atmosfera o musica de fondo procedural continua.

---

## 4. Exportacion y Despliegue

- **Previsualizacion Inmediata:** Despliegue en iframe o archivo HTML unico interactivo.
- **Exportacion a MP4:** Grabacion directa de fotogramas mediante captura de canvas (`canvas.captureStream()`) o MediaRecorder API en el navegador del cliente.
- **Modo Interactivo / Juego:** Capacidad de enlazar controles de teclado o touch para transformar la animacion en un minijuego interactivo.
