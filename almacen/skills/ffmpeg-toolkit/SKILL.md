---
name: ffmpeg-toolkit
description: "Comandos CLI de FFmpeg: corte rapido sin recodificar, compresion web/WhatsApp, subtitulos y extraccion de audio."
trigger: model_decision
---

# FFmpeg Video Automation & CLI Mastery

## 1. Comandos Canonicos de Rendimiento Maximo
- **Corte Instantaneo (Sin Re-encode, <1 segundo):**
  `ffmpeg -ss <inicio_hh:mm:ss> -to <fin_hh:mm:ss> -i input.mp4 -c copy output.mp4`
- **Compresion Optima Web/WhatsApp (H.264 + AAC, reduccion del 70% sin perdida visual):**
  `ffmpeg -i input.mp4 -vcodec libx264 -crf 23 -preset fast -acodec aac -b:a 128k output.mp4`
- **Quemado Duro de Subtitulos (.srt a video con estilo):**
  `ffmpeg -i input.mp4 -vf "subtitles=subs.srt:force_style='FontSize=20,PrimaryColour=&H00FFFFFF,Outline=1'" -c:a copy output.mp4`
- **Extraccion de Audio Limpio (MP3 a 192 kbps):**
  `ffmpeg -i input.mp4 -vn -acodec libmp3lame -b:a 192k audio.mp3`
- **Generacion de GIF de Alta Calidad con Paleta Optimizada:**
  `ffmpeg -i input.mp4 -vf "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" out.gif`

## 2. Reglas de Operacion del Agente
- Priorizar siempre `-c copy` cuando solo se corten fragmentos para evitar ciclos de CPU innecesarios.
- Verificar resoluciones pares (`scale=trunc(iw/2)*2:trunc(ih/2)*2`) para compatibilidad H.264.
