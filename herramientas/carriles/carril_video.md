# CARRIL VÍDEO (kit corto: léelo entero, ~1k tokens)

Activo cuando el usuario pide un vídeo, una edición, un reel/TikTok, un guion o planificar un montaje.

## Ver / transcribir / resumir un vídeo que YA existe (clase o referencia)
Herramienta local (0 tokens de nube, la grabación no sale del equipo). NO subas audio a Groq/Gemini ni digas que no puedes transcribir:
`<PYTHON> "<NOVA_HOME>/antigravity/herramientas/video/destilador_video/destilar.py" "<video o URL>" --modo clase|referencia`
- `clase` = grabación de clase -> resumen, conceptos, código con minuto y "A verificar" (esas búsquedas las haces tú después, solo con los términos).
- `referencia` = reel/TikTok -> gancho 0-3 s, planos, ritmo, textos, estilo, lección para nuestros vídeos.
- Solo transcribir: `--sin-vista --sin-resumen`. Un trozo: `--desde 40:00 --hasta 55:00`. Más rápido: `--modelo small`.
- Lee `resumen.md` de la carpeta que imprime al final (y `transcripcion.txt` / `vista.md` si hace falta). Si dice FALTA el entorno: avisa al usuario (una vez, con su OK: `<PYTHON> "<NOVA_HOME>/antigravity/herramientas/video/destilador_video/instalar.py"`).

## Hacer un vídeo nuevo: flujo (no te saltes pasos)
1. **Guion y escenas** primero, aprobados por el usuario: duración, formato (16:9 / 9:16), escenas con texto y tiempo.
2. **Voz**: `<PYTHON> <NOVA_HOME>/antigravity/herramientas/voz_clon/clonador.py decir --voz videos --texto "..." --mp3` (Marina, locutora de los vídeos; `--estilo crudo`). Solo voces con permiso.
3. **Montaje en código**: `almacen/skills/canvas-video-engine/SKILL.md` (Motor 1 Canvas 2.5D + WebCodecs) y plantillas en `herramientas/video/`; Remotion/Hyperframes solo si el usuario lo pide.
4. **FFmpeg**: cortes sin pérdida `-c copy`; web `-c:v libx264 -crf 23 -preset fast -pix_fmt yuv420p -c:a aac -b:a 128k`.
5. **QA**: hoja de contacto 3x2 a 720p auditada con `auditar_hoja_vl.py` antes de entregar.

## Reglas
- Nada de URLs ni IDs de vídeo inventados: salen de la API o del DOM.
- Éxito solo con datos reales: `duration > 0`, formato y audio comprobados.
- El código grande lo pica Qwen (más de 150 líneas): tú haces el contrato.

## Definición de hecho (el verificador)
- Archivo final existe, dura lo previsto, tiene audio y la hoja de contacto está auditada.

## Escalar
- Planificar un vídeo largo o una edición compleja -> orquestador casero (Carbon/Neon escribe PLAN.md, tú ejecutas) o consulta de ventana.

## Profundizar
`almacen/skills/canvas-video-engine/SKILL.md` · `ffmpeg-toolkit` · `remotion-video-agent` · `hyperframes-director`
Índice del dominio (1 salto): `config/skills/index-ai-multimedia/SKILL.md`.

<!-- ERRORES_YA_COMETIDOS:INICIO -->
## Errores que ya cometiste (no los repitas)
_Lo genera `nova_aprendido.py kits` desde `memory/aprendido.jsonl` (tus propios errores): no lo edites a mano. Aun no hay ninguno._
<!-- ERRORES_YA_COMETIDOS:FIN -->
