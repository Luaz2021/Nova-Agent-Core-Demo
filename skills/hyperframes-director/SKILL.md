---
name: hyperframes-director
description: "Director de video programatico ultraligero en HTML5, CSS3 y GSAP timelines: principio Audio-First, subtitulos en DOM y Safe Zones para Reels/TikTok a minimo coste de tokens."
---

# HyperFrames Director: Motor de Video Programatico Ultraligero

Genera videos de alta retencion (Reels, TikTok, Shorts y Demos de producto) usando estandares web puros: **HTML5 plano, CSS3 y coreografia GSAP** controlada mediante `seek(t)` en Chromium headless.

A diferencia de entornos pesados basados en React (Remotion), HyperFrames opera con un consumo minimo de tokens de contexto, cero dependencias complejas de compilacion y determinismo matematico frame a frame.

---

## 1. Los 5 Dogmas del Motor HyperFrames

1. **Principio Audio-First (El Audio Dicta el Tiempo):**
   - Prohibido asumir duraciones de animacion a ojo.
   - La locucion se genera primero y se extraen marcas de tiempo por palabra (*word-level timestamps*).
   - Cada escena visual adapta sus keyframes y duracion exacta a la duracion real de la voz.

2. **Subtitulos 100% en el DOM (Cero Filtro Subtitles en FFmpeg):**
   - Los subtitulos dinamicos (estilo karaoke o palabra a palabra) se renderizan como elementos HTML con CSS (`transform`, `opacity`, `text-shadow`).
   - Elimina incompatibilidades de rutas y fuentes tipograficas en FFmpeg.
   - Permite que el auditor de Safe Zones valide el contraste y colisiones en tiempo de ejecucion.

3. **Mascara de Safe Zones Estricta (9:16 Vertical - 1080x1920):**
   - **Margen Superior Seguro:** Minimo `108px` libres (evita barra de navegacion e iconos de estado).
   - **Margen Inferior Seguro:** Minimo `320px` libres (espacio reservado para descripcion, nombre de cuenta y musica).
   - **Margen Lateral Derecho:** Minimo `120px` libres (zona de botones: like, comentar, guardar y compartir).
   - **Margen Lateral Izquierdo:** Minimo `48px` libres.
   - Todo elemento focal o texto importante DEBE permanecer dentro de esta caja segura.

4. **GSAP como Motor de Tiempo Discreto:**
   - La linea de tiempo principal se define mediante `gsap.timeline({ paused: true })`.
   - La captura de frames no usa tiempo real (`Date.now()` o `requestAnimationFrame`), sino saltos deterministas: `timeline.seek(frameIndex / fps)`.
   - Esto garantiza que una maquina lenta exporte exactamente el mismo video fluido a 30 o 60 FPS sin tirones (*frame drops*).

5. **Masterizado Final FFmpeg a CRF 18 (Un Solo Paso Lossy):**
   - Los frames capturados se ensamblan con FFmpeg usando espacio de color `bt709`, formato de pixel `yuv420p` y normalizacion de audio EBU R128 (-14 LUFS para TikTok e Instagram).

---

## 2. Estructura de Proyecto HyperFrames

```text
proyecto_video/
├── 0_brief.json          <- Especificacion: plataforma, ratio (9:16), paleta y fuentes
├── 1_script.json         <- Guion desglosado por escenas con hooks de retencion
├── 2_audio_words.json    <- Locucion procesada con timestamps por palabra (start, end)
├── index.html            <- Escenario DOM, estilos CSS y contenedores de Safe Zone
├── main.js               <- Timeline GSAP y sincronizacion audio-visual
└── render.js             <- Script Puppeteer/Playwright para captura frame a frame
```

---

## 3. Plantilla Base de Escenario (`index.html`)

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>HyperFrames Stage</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      width: 1080px;
      height: 1920px;
      background: #0B0F17;
      color: #F8FAFC;
      font-family: 'Inter', -apple-system, sans-serif;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    
    /* Contenedor Safe Zone (9:16) */
    .safe-zone {
      position: absolute;
      top: 108px;
      bottom: 320px;
      left: 48px;
      right: 120px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    /* Subtitulos Dinamicos en DOM */
    .captions-box {
      font-size: 54px;
      font-weight: 800;
      text-align: center;
      line-height: 1.25;
      text-transform: uppercase;
      letter-spacing: -0.02em;
    }
    .word-highlight {
      color: #38BDF8;
      display: inline-block;
      transform-origin: center;
    }
  </style>
</head>
<body>
  <div class="safe-zone">
    <div id="visual-hook" class="visual-canvas"></div>
    <div id="captions" class="captions-box"></div>
  </div>
  <script src="main.js"></script>
</body>
</html>
```

---

## 4. Orquestacion de Tiempo con GSAP (`main.js`)

```javascript
const tl = gsap.timeline({ paused: true });

// Sincronizar palabras con locucion real
function buildCaptionsTimeline(wordTimestamps) {
  const container = document.getElementById('captions');
  
  wordTimestamps.forEach(({ word, start, end }) => {
    tl.to(container, {
      duration: end - start,
      onStart: () => {
        container.innerHTML = `<span class="word-highlight">${word}</span>`;
      }
    }, start);
  });
}

// Ejemplo de animacion visual adaptada a escena 1
tl.from("#visual-hook", {
  duration: 0.8,
  scale: 0.8,
  opacity: 0,
  ease: "back.out(1.7)"
}, 0);
```

---

## 5. Pipeline de Masterizado FFmpeg Multiplataforma

Una vez capturados los frames PNG secuenciales (`frames/frame_%05d.png`):

```bash
# Ensamblado y masterizado profesional con normalizacion de audio:
ffmpeg -y -framerate 30 -i frames/frame_%05d.png -i locucion.wav \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -colorspace bt709 \
  -af "loudnorm=I=-14:LRA=7:TP=-1.5" \
  -c:a aac -b:a 192k -shortest \
  output_final_reel.mp4
```

---

## 6. Checklist de Entrega HyperFrames (QA Pre-Render)

1. [ ] ¿El guion fue validado contra los primeros 3 segundos con gancho visual?
2. [ ] ¿La duracion de la timeline la dicta el archivo `2_audio_words.json`?
3. [ ] ¿Ningun texto o subtitulo sobrepasa la zona inferior de 320px ni la lateral de 120px?
4. [ ] ¿La timeline de GSAP esta pausada y lista para renderizado determinista `seek()`?
5. [ ] ¿El masterizado final aplica CRF 18 con espacio de color `bt709` y audio normalizado a -14 LUFS?
