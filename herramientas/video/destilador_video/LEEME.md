# Destilador de video (Claude, 23/11/2026) - en herramientas desde el 23/11 (probado en el PC)

Un motor, dos modos. Todo en LOCAL: **Whisper oye, InternVL ve, Qwen redacta** (uno detras de otro: cabe en 8 GB).

| Modo | Para | Saca |
|---|---|---|
| `clase` | grabaciones de clase (Teams, pantalla compartida) | transcripcion con minutos, capturas cuando cambia la pantalla o el profe dice "fijaos / este codigo / el error", lo que hay en cada captura (codigo exacto, diapositiva, consola), resumen y lista **A verificar** con busquedas cortas |
| `referencia` | reels, TikTok, videos de referencia (archivo o URL) | gancho 0-3 s, estructura por planos, ritmo (cortes/min), textos en pantalla, estilo y leccion para nuestros videos |

## Uso
```
& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\video\destilador_video\destilar.py" "<video o URL>" --modo clase
```
(destilar.py salta solo a su entorno `~/nova_destilador/env`; si falta, dice como instalarlo.)
Opciones: `--out DIR`, `--modelo small|medium|large-v3-turbo` (clase: medium; referencia: small),
`--desde 40:00 --hasta 55:00` (solo un trozo), `--sin-vista`, `--sin-resumen`, `--cpu`.
Salida por defecto: `antigravity\documentos_generados\destilados\<fecha>_<nombre>\`
(`resumen.md`, `transcripcion.txt`, `vista.md`, `capturas\`, `datos.json`).

## Medido en el PC (RTX 3060 12 GB)
- Clase de 3 min: **85 s** (Whisper medium 21 s, pantallas 1 s, InternVL 3 capturas 19 s, Qwen 44 s).
- Reel de 1 min (Instagram): **137 s** (46 cortes, 16 capturas vistas).
- Clase de 2 h (estimado): ~25-35 min. Con `--modelo small` o `--desde/--hasta`, menos.

## Se adapta al equipo (23/11) y hace cola
Antes de empezar mira la GPU (nvidia-smi) y la RAM (API de Windows) y reparte:
| GPU | Whisper | Capturas a InternVL | Contexto Qwen |
|---|---|---|---|
| 11+ GB (PC 3060 12 GB) | large-v3-turbo | todas, 1280 px | 16k, tramos 10 min |
| 7-10 GB (laptop 5060 8 GB) | medium | 70 % | 12k |
| 6 GB | medium | 40 %, 960 px | 8k, tramos 7 min |
| 3-5 GB | small | sin InternVL | 8k |
| sin GPU | small/base en CPU (deja 2 hilos libres) | sin InternVL | avisa si hay poca RAM |
Ademas descarga de la GPU los modelos de Ollama que haya dejado otra tarea antes de transcribir.
**Cola:** un destilado cada vez por equipo (`~/nova_destilador/en_marcha.json`); si Nova lanza otro,
ese escribe "EN COLA" y espera. Un destilado muerto no bloquea (se mira si su PID vive).
Probar otro equipo sin tenerlo: `$env:DESTILADOR_SIMULAR="vram=8,ram=8"`.
Medido 23/11: clase 40 min = 7:52; clase 58 min = 9:17 (PC). Dos a la vez: el 2o espero 90 s en cola y siguio solo.

## Reglas
- La grabacion NUNCA sale a internet. La investigacion la hace Nova despues con las busquedas de "A verificar".
- InternVL tiene orden de no escribir nombres de personas (en Teams salen los de los companeros).
- El entorno pesado vive fuera de la carpeta de Nova: `~/nova_destilador/env` -> en cada equipo, una vez: `<PYTHON> instalar.py` (Windows, macOS y Linux; GPU NVIDIA opcional).
- Audio por FFmpeg (no PyAV: faster-whisper 1.2.1 + av nuevo rompe con `metadata_errors`).
- GPU sin instalar CUDA: DLLs de los paquetes `nvidia-cublas-cu12` / `nvidia-cudnn-cu12`. Si fallan, pasa solo a CPU.
- Sustituye al `herramientas\video\destilador` viejo (ese NO oia ni miraba: Qwen se imaginaba el video por el titulo).
