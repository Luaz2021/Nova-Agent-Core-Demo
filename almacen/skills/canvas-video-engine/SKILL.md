---
name: canvas-video-engine
description: "Arquitectura de 5 Capas de Video Programatico Zero-NPM: Motor 1 (Canvas 2.5D + WebCodecs Mp4Mux + WSOLA + edge-tts Base64), Motor 2 (Python NumPy Shaders + Audio Synth BPM + FFmpeg Pipe), Juez Visual Hoja de Contacto con blaifa/InternVL3_5:8b, Ensamblaje Whisper/MoviePy/FFmpeg y Puente FCPXML/DaVinci."
---

# Nova Video Studio · Arquitectura de 5 Capas (Zero-NPM & Local VL QA)

## 1. Enrutador de Motores: Que Motor Usar Segun el Pedido

| Motor | Tecnologia Base | Caso de Uso Ideal | Ventaja Clave |
| :--- | :--- | :--- | :--- |
| **Motor 1: Canvas 2.5D WebCodecs** | HTML5 `<canvas>` + `WebCodecs` (`VideoEncoder`/`AudioEncoder`) + `Mp4Mux` + `edge-tts` | Videos explicativos (1 a 3 min), casos B2B, flujos IT/OT, algoritmos estilo Motion Canvas. | Pesa ~65 KB, cero `node_modules`, exporta H.264+AAC offline a toda velocidad en 16:9, 4:5 y 9:16. |
| **Motor 2: Python Shaders & Synth** | Python + `NumPy` + `Pillow` + Sintetizador WAV + Pipe `rawvideo` a `FFmpeg` | Intros de marca (5 a 15 s), trailers cyberpunk, tipografia estroboscopica, particulas y bloom neon. | Post-procesado por pixel (bloom gaussiano, aberracion cromatica, glitch, scanlines CRT) y musica sintetizada al BPM sin archivos externos. |
| **Motor 3: HyperFrames 3D / B-Roll** | Three.js WebGL / GSAP DOM (`skills\hyperframes-director\SKILL.md`) | Reels 9:16 con personajes 3D procedurales (lip-sync 30 Hz) o montaje rapido editorial con fotos reales. | Camara 9:16 calibrada (`vFOV=50`) y mascara de Safe Zones para TikTok/Reels. |
| **Motor 4: Remotion React Studio** | React + Tailwind + Remotion (`skills\remotion-video-agent\SKILL.md`) | Demos de componentes UI reales de proyectos React/Next.js existentes, Bento Grids animados. | Reutiliza directamente el codigo React del frontend en produccion. |

Plantillas ejecutables listas en: `<NOVA_HOME>\antigravity\herramientas\video\`.

---

## 2. Capa 1: Pipeline Audio-First (Voz Neuronal, WSOLA y Sintesis Musical)

### 2.1 Locucion Neuronal y Empaquetado Base64 (`generar_voz.py`)
Genera `audio/escena1.mp3 ... escenaN.mp3` con `edge-tts` (`es-ES-ElviraNeural`, `rate="+0%"`, `pitch="-2Hz"`) y embebe todos los MP3 en Base64 dentro de `audio/voces.js` (`window.VOCES = [...]`).
- **Por que Base64 en `voces.js`:** Permite abrir el archivo `.html` directamente con doble clic (`file://`) y decodificar el audio con `OfflineAudioContext` sin errores de bloqueo CORS ni selectores manuales de archivos.
- **Alineacion Palabra por Palabra (`Whisper`):** Para subtitulos dinamicos tipo karaoke o cortes sincronizados al habla, extraer timestamps con `faster-whisper` (`word_timestamps=True`).

### 2.2 Algoritmo WSOLA de Time-Stretching en JS Puro (`stretch(x, rate)`)
Acelera o ralentiza la voz (`0.9x` a `1.3x`) en el navegador mediante correlacion cruzada de ventanas Hanning (`N=1536`) sin alterar el tono vocal:
```javascript
function stretch(x, rate) {
  if (Math.abs(rate - 1) < 1e-3) return x;
  const N = 1536, Hs = N >> 1, Ha = Math.round(Hs * rate), tol = Hs >> 1;
  const win = new Float32Array(N);
  for (let i = 0; i < N; i++) win[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N);
  const outLen = Math.ceil(x.length / rate) + N, y = new Float32Array(outLen);
  let prev = 0;
  for (let k = 0; ; k++) {
    const ideal = k * Ha, o = k * Hs;
    if (ideal + N + tol >= x.length || o + N >= outLen) break;
    let best = ideal, nat = prev + Hs;
    if (k > 0 && nat + N < x.length) {
      let bc = -Infinity;
      for (let d = -tol; d <= tol; d += 2) {
        const q = ideal + d; if (q < 0) continue;
        let c = 0; for (let j = 0; j < N; j += 4) c += x[q + j] * x[nat + j];
        if (c > bc) { bc = c; best = q; }
      }
    }
    for (let j = 0; j < N; j++) y[o + j] += x[best + j] * win[j];
    prev = best;
  }
  return y;
}
```

### 2.3 Sintetizador Musical Procedural en NumPy (`nova_intro_template.py`)
Para intros y reels de ritmo electronico (ej. 120 BPM, `BEAT = 0.5s`), sintetizar la pista WAV estereo a 44.1 kHz en memoria sin MP3 externos:
- **Bombo (`bombo`):** Senoide con barrido exponencial de frecuencia (`f = 45 + 110 * exp(-x * 30)`) y decaimiento (`exp(-x * 9)`).
- **Hi-Hat (`ruido`):** Ruido blanco filtrado en agudos (`r - convolve(r, ones(6)/6)`) con caida rapida (`exp(-x * 60)`).
- **Sub-Drop de Impacto (`impacto`):** Sub-grave de `38 Hz` + rafaga de ruido en cada cambio de acto.
- **Riser (`subida`):** Barrido ascendente cuadratico (`200 Hz -> 2000 Hz`) previo a los cortes principales.
- **Bajo con Sidechain (`bajo`):** Onda de `55 Hz` modulada por `sin(2 * pi * tt / BEAT * 0.5) ** 2`.

---

## 3. Capa 2: Primitivas de los Motores Visuales

### 3.1 Motor 1: Canvas 2.5D Isometrico + Exportador WebCodecs `Mp4Mux`
- **Primitivas Reutilizables:**
  - Tiempo y curvas: `seg(t, a, b)`, `eo(x)` (EaseOutCubic), `eio(x)` (EaseInOut), `back(x)` (Overshoot), `lerp(a, b, x)`.
  - Composicion: `A(alpha, fn)` (opacidad aislada), `S(x, y, scale, fn)` (traslacion y escala aisladas).
  - Objetos de escena: `cube(x, y, a, col, o)` (proyeccion 2.5D con caras iluminada `1.3`, base `1.0` y sombra `0.78`), `person()` (estados `smile`/`sad`/`wow`, sudor animado, brazos y tablet), `printer()` (estados `idle`/`print`/`error`/`done`, humo y barra de progreso), `sheet()` (Excel animado), `windowBox()` + `field()` (formulario con escritura progresiva y cursor parpadeante), `phone()`, `bubble()` (bocadillos estilo WhatsApp), `icon()`, `card()`, `tag()`.
- **Multi-Formato Automatico (`compose(t, i)`):**
  Renderiza siempre la escena base en un canvas interno `sc16` (1920x1080) y la proyecta al vuelo en:
  - `16:9` (1920x1080 horizontal directo).
  - `4:5` (1080x1350 Instagram) y `9:16` (1080x1920 TikTok/Reels): genera un fondo desenfocado a partir de un canvas miniatura `64x36` escalado con `imageSmoothingQuality = 'high'`, superpone tarjeta redondeada con sombra para la escena 16:9 en el centro, badge de progreso y titulo arriba, y subtitulos grandes con borde debajo dentro de la Safe Zone.
- **Exportacion Offline Ultra-Rapida (`fastExport` + `Mp4Mux`):**
  Usa `OfflineAudioContext` para mezclar las voces estiradas con `stretch()`, codifica el audio con `AudioEncoder` (`mp4a.40.2`), recorre un bucle determinista `for (let f = 0; f < nF; f++) { render(f / FPS); ve.encode(new VideoFrame(cv, ...)); }` con `VideoEncoder` (`avc1.640028`) y empaqueta los chunks binarios en memoria con `Mp4Mux` (cajas ISO BMFF `ftyp`, `moov`, `trak`, `avc1`, `mp4a`, `stts`, `stco`, `stss`, `mdat`).

### 3.2 Motor 2: Python Shaders, Trazado Vectorial y Particulas (`nova_intro_template.py`)
- **Trazado Parcial por Longitud de Arco (`poli_parcial(pts, p)`):**
  Recorre cualquier poligono o polilinea hasta la fraccion `p` (`0.0 -> 1.0`) calculando distancias euclideas entre vertices (`math.dist`), imitando `stroke-dashoffset` en Pillow.
- **Convergencia de Particulas (`puntos_logo(n)`):**
  Muestrea `N=900` puntos sobre los segmentos del logo y los interpola desde coordenadas aleatorias exteriores con retardos individuales (`RETRASO`).
- **Compositor Multicapa con Bloom a Media Resolucion (`brillo`):**
  Separa `base`, `relleno` y `linea`. Redimensiona `linea` a `(W // 2, H // 2)`, suma 3 desenfoques gaussianos (`radios 6, 18, 42`, `fuerza 1.0, 0.8, 0.6`) en `float32` y reescala a `(W, H)` para lograr luz neon real a alta velocidad.
- **Post-Procesado NumPy:**
  - `aberracion(a, px)`: desplaza canales R (`+px`) y B (`-px`) con `np.roll` al ritmo de `golpe(t, BEAT)`.
  - `glitch_bandas(a, fuerza, semilla)`: desplaza franjas horizontales aleatorias.
  - Mascaras fijas precalculadas: `SCAN` (scanlines cada 3 filas a `0.86`) * `VINETA` (caida radial eliptica) + ruido gaussiano (`rng.normal(0, 4.0)`).
- **Tuberia Directa `rawvideo` a FFmpeg:**
  Envia `frame(i).tobytes()` (`rgb24`) directamente al `stdin` de `ffmpeg` (`-f rawvideo -pix_fmt rgb24 -s 1920x1080 -r 30 -i - -i pista.wav -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart`).

---

## 4. Capa 3: El Juez Visual Local (`blaifa/InternVL3_5:8b` + Hoja de Contacto)

Prohibido entregar un video a ciegas sin pasar por la aduana visual de hoja de contacto:
1. **Extraccion de Fotogramas Clave:**
   - En Motor Python: `python nova_intro.py --frames 20,60,110,160,210,260`
   - En Motor HTML Canvas: `python capturar_fotogramas.py 2,15,35,60,90,120`
2. **Montaje y Auditoria en 720p (`herramientas\video\auditar_hoja_vl.py`):**
   - Ensambla una cuadricula 3x2 (`hoja_final.png`) redimensionada a ancho 1280x720 (Regla 14/19: inferencia `< 30s`).
   - Envia la imagen a `blaifa/InternVL3_5:8b` en Ollama local (`http://127.0.0.1:11434/api/generate`) a **0 tokens de nube**.
   - Verifica 4 criterios: (1) cero textos cortados o solapados, (2) respeto de margenes y Safe Zones, (3) contraste legible sobre el fondo, (4) ausencia de fotogramas vacios o negros accidentales.
   - Si detecta un fallo, se corrige la coordenada o escala antes de lanzar el render MP4 completo.

---

## 5. Capa 4 y 5: Ensamblaje (`MoviePy` / `FFmpeg`) y Puente de Post-Produccion (`DaVinci Resolve`)

- **Ensamblaje Multi-Clip (`MoviePy` + `FFmpeg`):**
  Para combinar una intro del Motor 2 con un explicador del Motor 1 y grabaciones de pantalla reales, usar `ffmpeg -f concat` o `MoviePy` con *audio ducking* y normalizacion final EBU R128 (`-af loudnorm=I=-14:TP=-1.5:LRA=11`).
- **Puente Profesional (FCPXML / OpenTimelineIO / DaVinci Resolve MCP):**
  Cuando se requiera edicion manual fina, Color Grading (LUTs/Halation) o mezcla Fairlight en DaVinci Resolve, exportar las capas por separado (fondo, graficos RGBA en ProRes 4444 / WebM Alpha, pista de voz y pista SFX) acompañadas de un archivo de linea de tiempo `.fcpxml` o inyectarlas via `DaVinciResolveScript` / MCP.
