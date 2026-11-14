---
name: index-ai-multimedia
description: "Indice Macro IA, Video & Automatizacion: Qwen/Unsloth, enrutamiento multi-agente, Remotion, Hyperframes, FFmpeg, transcripcion de clases y scrapers 0-token."
---

# Index 04 · AI Engineering, Video Programatico & Scrapers (1-Hop Router)

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **Salto Obligatorio al Almacen:** En tareas de video en codigo, scrapers o automatizacion agentica, abrir primero la skill correspondiente del apartado 2 (`canvas-video-engine`, `zero-token-scraper-forge`, etc.) antes de armar el contrato para `qwen3.5:9b`.
- **Cuadernos Colab (`.ipynb`) y Datasets (`.jsonl`):** Prohibido leer o escribir archivos `.ipynb` completos con herramientas directas del chat (inyectan >15.000 tokens JSON al contexto). Inspeccionar o construir notebooks siempre mediante un micro-script generador en Python (`nbformat` o `json.dump`).
- **Fine-Tuning Unsloth (Coder y Vision VL):** En Google Colab instalar siempre `unsloth` junto con `unsloth_zoo` (`pip install --upgrade --no-cache-dir --no-deps unsloth unsloth_zoo`). Para modelos de vision (`Qwen2.5-VL` / `InternVL`) usar `FastVisionModel` y `UnslothVisionDataCollator`.
- **Principio API/CLI First (Cero Navegador Inutil):** Prohibido levantar Playwright para extraer datos si existe API REST, JSON oculto, `yt-dlp`, `curl`, `gh` o `ffmpeg`. Construir extractores reutilizables en `scripts\scrapers\` a 0 tokens.
- **FFmpeg & Video Programatico (Arquitectura 5 Capas):** Para cortes sin perdida usar `-c copy`; para compresion web usar `-c:v libx264 -crf 23 -preset fast -pix_fmt yuv420p -c:a aac -b:a 128k`. En generacion de video en codigo (`skills\canvas-video-engine\SKILL.md` y plantillas en `herramientas\video\`): usar **Motor 1 (HTML5 Canvas 2.5D + WebCodecs `Mp4Mux` + WSOLA + `edge-tts` Base64)** para explicadores largos/IT-OT (16:9, 4:5, 9:16), **Motor 2 (Python NumPy Shaders + Audio Synth BPM + pipe `rawvideo` FFmpeg)** para intros cyberpunk/logos/particulas, **Motor 3 (`hyperframes-director`)** para Reels 3D/B-Roll, y validar siempre antes de entregar generando una **Hoja de Contacto 3x2 a 720p (`auditar_hoja_vl.py`)** auditada por `blaifa/InternVL3_5:8b` local a 0 tokens.

## Trampas de Flash (errores reales ya cometidos)
- Flujo con `qwen3.5:9b` (2026): Nova planifica y genera el contrato/diff estructurado, `qwen3.5:9b` pica los bloques, Playwright/script saca las capturas, `blaifa/InternVL3_5:8b` las compara y Nova corrige **solo las lineas necesarias (`edit_file <= 35%`)**, jamas reemplazando todo el archivo.
- Prohibido dejar que Qwen "complete" listas: nombres, productos e imagenes vienen en el JSON de entrada.
- Clones: pipeline local primero (`analizar.py` -> `interacciones.py` -> `crear.py` -> `verificar.py`); Nova solo audita al final.
- Nunca inventar URLs o IDs de contenido (video de YouTube inexistente): sacarlos del DOM o de la API.
- Exito en medios solo con telemetria real (`duration > 0` y titulo correcto).
- Salida de OpenRouter: pintar solo lo esencial y sin mensajes de estado intermedios ("Consultando a la cantera...").
- Modelos Qwen 2026 en un equipo nuevo: `G:\Mi unidad\IA_LocalMejorada\modelos_completos\desplegar_modelos_v1.ps1` (instalador pesado; se queda en Drive).

## Definicion de hecho
- Video: hoja de contacto 3x2 a 720p auditada (`auditar_hoja_vl.py`) antes de entregar.
- Scraper o extractor: ejecutado una vez mostrando la salida real (filas, archivos o bytes obtenidos).

## 2. Mapa de Salto al Almacen (`<NOVA_HOME>\antigravity\almacen\` + la ruta `skills\...` de cada entrada; copia local, nunca leer de G:)
Abrir con `read_file` al ejecutar pipelines de video, scrapers o ingenieria agentica:
- **Video en Codigo & Multimedia:** `skills\canvas-video-engine\SKILL.md` (Doble Motor Zero-NPM: Canvas 2.5D WebCodecs + Python NumPy Shaders/Synth + QA Local VL) | `skills\remotion-video-agent\SKILL.md` | `skills\hyperframes-director\SKILL.md` | `skills\ffmpeg-toolkit\SKILL.md` | `skills\gemini-video-intelligence\SKILL.md` | `skills\gemini-lecture-transcriber\SKILL.md` | `skills\generative-media-director\SKILL.md` | `skills\video-script-storyteller\SKILL.md` | `skills\video-to-superprompt\SKILL.md`
- **Scrapers, Excel & Automatizacion:** `skills\zero-token-scraper-forge\SKILL.md` | `skills\gemini-xlsx-mastery\SKILL.md` | `skills\gemini-brave-sentinel\SKILL.md`
- **Ingenieria Agentica & Optimizacion:** `skills\agentic-engineering\SKILL.md` | `skills\autonomous-loops\SKILL.md` | `skills\benchmark-optimization-loop\SKILL.md` | `skills\agent-introspection-debugging\SKILL.md` | `skills\gemini-superpowers-engine\SKILL.md` | `skills\council\SKILL.md`
- **Presentaciones (alta 08/11):** `skills\frontend-slides\SKILL.md` (deck web en un solo HTML 16:9) | `skills\guizang-ppt\SKILL.md` (estilo suizo y editorial) | `skills\ppt-master\SKILL.md` (PPTX nativo con plantillas) | `skills\mcp-server-ppt\SKILL.md` (controlar PowerPoint en Windows)
- **Voz y video en herramientas (08/11):** `herramientasoz
ova_voz.py` (manos libres) | `herramientasideo\` (narracion, intro, destilador de reels, router de escenas)
