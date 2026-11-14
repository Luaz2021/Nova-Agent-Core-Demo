# Guia de Animacion, Motion Graphics y Video con Codigo

Esta referencia documenta el patron para construir animaciones en Canvas o SVG dentro de un iframe y exportarlas como video (WebM/MP4) o secuencias de imagenes.

## 1. El Principio del Timeline Determinista

Para que una animacion en codigo se pueda exportar a video sin saltos de frames ni tartamudeos (stuttering), **nunca** debes calcular el estado de la animacion basandote en `Date.now()` o `performance.now()`.

En su lugar, estructura la animacion con una funcion pura de renderizado dependiente del fotograma o del progreso normalizado:

```javascript
// t va de 0.0 (inicio) a 1.0 (final)
function renderFrame(t, ctx, width, height) {
  // Limpiar lienzo
  ctx.clearRect(0, 0, width, height);

  // Easing (ej. cubic-in-out)
  const easeProgress = t < 0.5 
    ? 4 * t * t * t 
    : 1 - Math.pow(-2 * t + 2, 3) / 2;

  // Dibujar elementos interpolados segun easeProgress
}
```

Ventajas:
1. Permite scrub manual (pausar y mover la barra de tiempo a cualquier punto).
2. Permite exportar cada fotograma a maxima resolucion sin depender de los FPS de la pantalla.
3. Garantiza un bucle perfecto (loop).

---

## 2. Exportacion Nativa en Navegador con MediaRecorder

Para que el usuario pueda presionar un boton y descargar el video directamente sin herramientas externas:

```javascript
function recordCanvasToWebM(canvas, totalDurationMs, fps = 60) {
  return new Promise((resolve) => {
    const stream = canvas.captureStream(fps);
    const recorder = new MediaRecorder(stream, {
      mimeType: "video/webm; codecs=vp9"
    });
    const chunks = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: "video/webm" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `animacion_${Date.now()}.webm`;
      a.click();
      URL.revokeObjectURL(url);
      resolve();
    };

    recorder.start();
    
    // Iniciar bucle de animacion determinista
    let startTime = null;
    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / totalDurationMs, 1.0);

      renderFrame(progress, ctx, canvas.width, canvas.height);

      if (progress < 1.0) {
        requestAnimationFrame(step);
      } else {
        recorder.stop();
      }
    }
    requestAnimationFrame(step);
  });
}
```

---

## 3. Protocolo de Captura en Sandbox (Doctrina Open-Artifacts)

Cuando el contenido esta dentro de un iframe aislado y el padre necesita capturar frames individuales o areas seleccionadas del DOM:

1. **Inyeccion de listener en el iframe:**
```javascript
window.addEventListener("message", async (event) => {
  if (event.data?.type === "CAPTURE_FRAME") {
    const { frameIndex, totalFrames } = event.data;
    const progress = frameIndex / totalFrames;
    renderFrame(progress, ctx, canvas.width, canvas.height);
    
    // Enviar frame rasterizado de vuelta al padre
    const dataUrl = canvas.toDataURL("image/png");
    window.parent.postMessage({
      type: "FRAME_DATA",
      frameIndex,
      dataUrl
    }, "*");
  }
});
```

2. **Captura DOM con html2canvas (para layouts complejos sin Canvas directo):**
Si la animacion es HTML/CSS puro, inyectar `html2canvas` para congelar el contenedor:
```javascript
const canvasSnapshot = await html2canvas(elementToCapture, {
  useCORS: true,
  logging: false
});
const imgUri = canvasSnapshot.toDataURL("image/png");
```

---

## 4. Compilacion a MP4 con ffmpeg

Si se capturan secuencias de imagenes numeradas (`frame_0001.png`, etc.):
```bash
ffmpeg -framerate 60 -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p output.mp4
```

O para convertir el archivo `.webm` descargado a un `.mp4` compatible con cualquier reproductor o red social:
```bash
ffmpeg -i animacion.webm -c:v libx264 -pix_fmt yuv420p animacion.mp4
```
