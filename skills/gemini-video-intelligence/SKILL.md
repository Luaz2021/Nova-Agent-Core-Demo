---
name: gemini-video-intelligence
description: "Procesamiento, análisis semántico y comprensión multimodal de videos locales y URLs (YouTube, MP4, grabaciones). Extracción de frames clave, transcripción temporal precisa con Whisper, OCR en pantalla y síntesis de contenido para aprendizaje acelerado."
---

# 🎥 Video Intelligence & Multimodal Understanding

Protocolo de ingesta y comprensión integral de videos para Nova.

## 1. Fuentes Soportadas
- **URLs de YouTube / Redes**: Extracción de subtítulos oficiales o automáticos de alta fidelidad vía `yt-dlp` / `youtube-transcript-api`.
- **Archivos de Video Locales (`.mp4`, `.mkv`, `.mov`)**: Extracción de audio con `ffmpeg` y análisis temporal con Whisper.

## 2. Comprensión de Contexto
- Mapeo de marcas de tiempo (*Timestamps*) para responder preguntas como: *"¿En qué minuto explican los hooks de React?"*.
- Resúmenes ejecutivos, esquemas jerárquicos y código extraído de la pantalla del video mediante OCR.
- Generación de tarjetas de estudio y síntesis de clases magistrales.
