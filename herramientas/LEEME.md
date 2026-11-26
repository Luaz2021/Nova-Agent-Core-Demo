# Herramientas de Nova

Carpeta OFICIAL de herramientas de Nova (protegida: Nova la consulta y usa, pero no escribe aqui). Antes de crear
un script, Nova mira este indice para no repetir uno que ya existe.

Reglas:
- Script NUEVO -> se crea en `antigravity\scratch\` (la sala de espera, carpeta por defecto de Antigravity), nunca aqui directamente.
- Pasa a esta carpeta solo cuando el usuario lo valida y Claude le pasa auditoria; entonces se apunta en el indice.
- Lo que una herramienta GENERE (datos, capturas, informes) va en `herramientas\datos\<nombre>\`, no junto al script.
- No se copian textos ni fotos de webs ajenas: solo medidas y estructura.

## En que sistema funciona cada una (v3.3)

- **Windows, macOS y Linux:** carriles, revision_visual, estudio_web, api_xray (lanzadores .bat / .command / .sh),
  consultas, seguridad/nova_seguridad.py (los escaneres opcionales se instalan con winget, brew o uv: el propio arnes
  dice el comando de tu sistema), codebase_memory (el programa se instala con `instalar.py`, que elige tu sistema),
  radar_web, trello, nube, video/generar_voz.py, director (necesita la CLI `agy` de Antigravity; criterios en
  PowerShell o bash segun el sistema), penpot_mcp (necesita Node.js; `lanzar.py`), video/destilador_video (entorno con
  `instalar.py`; GPU NVIDIA opcional en Windows/Linux, CPU en Mac) y voz_clon (pack de voz: GPU NVIDIA o Mac con chip
  Apple; `instalar.ps1` en Windows, `instalar.sh` en Mac/Linux).
- **Solo Windows (en macOS/Linux Nova lo dice y sigue sin ello):** voz/ (aduana de adjuntos, mascota, Nova Voz Live y
  guardian de claves: necesitan la ventana de Antigravity de Windows), horario/, pruebas/phantom_test.ps1 y
  seguridad/git_clone_sentinel.ps1.

## Indice (herramientas nuevas)

| Herramienta | Que hace | Uso |
|---|---|---|
| voz_clon/clonador.py | CLONADOR DE VOZ (15/11; 16/11 motor faster-qwen3-tts: suena en ~1,3 s y en streaming, `hablar` / POST `/hablar`): Qwen3-TTS 1.7B en local (GPU). Voces oficiales: Ayla = Nova (crudo, normal/agresiva), Marina = videos (locutora con filtro de radio, o crudo); derechos cedidos al usuario. Muestras aprobadas en Drive `Archivos Compartidos\clonar_audio\ayla_oficial` y `marina_oficial`. Sustituye a scratch\20261112_clonador_voz (no clonaba: acababa en Edge-TTS) | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\voz_clon\clonador.py" decir --voz nova --texto "Hola"` |
| estudio_web/estudio.py | ESTUDIO WEB (15/11): Nova directora de arte. ficha (concepto, referencias, paleta, tipografia, pieza principal, fotos) validada con codigo + skills por fase comprobadas en la telemetria; Qwen pica el HTML con las clases de Nova; revisor que baja por la web en PC y movil (contraste en pixeles, huecos, neones, datos inventados, InternVL en fotos). Memoria anti-repeticion en `datos\estudio_web\memoria.json`. Sustituye a gema_esqueleto (retirado) | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\estudio_web\estudio.py" ficha <carpeta> "<pedido>"` |
| horario/nova_horario.py | Widget de escritorio del usuario: HORARIO de clase (semana real con fechas, Semana A/B automatica, hoy y clase en curso marcadas, clic en un cuadro = nota de ese dia) + APUNTES de pendientes en 3 pestanas (Estudios, Personal, Proyectos). Datos en `herramientas\datos\horario\` (viajan por Drive). Sin librerias extra (tkinter). Nova no edita esos json: si el usuario quiere apuntar algo, lo apunta el en el widget | abrir: acceso "Horario Nova" del Escritorio · crearlo en otro equipo: `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\horario\nova_horario.py" --acceso` |
| trello/trello.py | Trello generico: tableros, listas, tarjetas, crear, mover, comentar, archivar. Claves del vault leidas en local, nunca impresas | `<PYTHON> <NOVA_HOME>\antigravity\herramientas\trello\trello.py tableros` (ver --help) |
| voz/nova_voz.py | Manos libres: di 'Nova' y dicta la orden al chat de Antigravity (voz neural; sin widget; lista para la voz clonada de voice_clone) | `pythonw ...\herramientas\voz\nova_voz.py` |
| codebase_memory/radiografia.py | RADIOGRAFIA DE PROYECTOS (25/11, Claude): proyecto grande, rama o codigo LEGACY -> sin leerlo entero y en local: piezas y que hace cada una (Qwen), mapa de dependencias (mermaid), ciclos, cohesion/acoplamiento (pieza INDEPENDIENTE / BASE / NUDO / AISLADA), puntos fragiles, funciones monstruo, codigo duplicado, codigo muerto y plan para trocear en piezas. `impacto` = que se rompe si tocas una funcion; `cambios` = impacto del git diff; `mapa` = visor web 9749 bajo demanda (se cierra solo). Usa el programa del MCP codebase en modo CLI: no hace falta encender el MCP | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\codebase_memory\radiografia.py" analizar "<carpeta>" --explicar` · `impacto <proyecto> <funcion>` · `cambios <proyecto>` · `mapa` / `mapa --cerrar` · salida en `documentos_generados\radiografias\` |
| director/nova_director.py | NOVA DIRECTOR (26/11, Claude; idea del usuario tras la prueba A/B del orquestador): proyecto GRANDE de cero o por fases SIN ventanas: Neon High hace los PLANOS (arquitectura + fases.json con criterios), Hydrogen High pica cada fase en una conversacion nueva (en paralelo las independientes), el director comprueba los criterios (gratis) y escala Hydrogen x2 -> Neon -> Carbon; al final INSPECCION de seguridad con Neon Extra High (escaneres + diff completo) -> arreglo -> reinspeccion. Usa la CLI `agy -p`. NO es para tareas pequenas (ahi Nova sola) | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\director\nova_director.py" todo "<proyecto>" --idea "<enunciado.md>"` · `estado <proyecto>` · `modelos` · ver `director\LEEME.md` |
| api_xray/api_xray.py | API X-RAY (20/11 Nova, auditada por Claude; en herramientas desde el 25/11): link de una API JSON -> radiografia (codigo, latencia, CORS, paginacion), tabla de datos, diagrama ER y CREATE TABLE para SQLite/MySQL/PostgreSQL; exporta .sqlite/.sql/.md/.json. Solo libreria estandar. Errores conocidos en `errores.md`; tests 10/10 + 6/6 | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\api_xray\api_xray.py" --url <url>` · solo consola: `--cli <url> --all --sql postgres` |
| seguridad/nova_seguridad.py | ARNES DE SEGURIDAD (25/11, Claude): escaneres gratis (nova_auditoria con reglas web + Java/JDBC + Android; Semgrep CE, gitleaks y OSV-Scanner si estan instalados) -> `PAQUETE.md` compacto con los candidatos y su codigo, para verificar SOLO eso (metodo security-audit-cloudflare) sin leer el proyecto entero. No escribe en el proyecto | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\seguridad\nova_seguridad.py" "<carpeta>"` · salida en `documentos_generados\seguridad\` |
| revision_visual/revisar.py | REVISION VISUAL (23/11, Claude): mira la web COMO LA VE ALEXANDER antes de decir listo: la sirve en local sin cache, capturas en 1366x768, 1920x1080 y movil 390x844, comprueba scroll horizontal, cosas que se salen, imagenes rotas y errores de consola, mide el marco de un mockup (--marco) e InternVL revisa cada captura. VEREDICTO OK / REVISAR + informe.md. El hook te frena si cambias .html/.css/.js y dices listo sin pasarla | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\revision_visual\revisar.py" "<carpeta>"` · `--paginas a.html,b.html` · `--todas` · `--marco .phone-frame` |
| video/destilador_video/destilar.py | DESTILADOR DE VIDEO (23/11, Claude): ver y entender un video EN LOCAL. Whisper transcribe (GPU), FFmpeg detecta cambios de pantalla y frases tipo "fijaos / este codigo", InternVL lee esas capturas (codigo exacto, diapositiva, consola; sin nombres de personas), Qwen resume. Modo `clase` (grabaciones de clase: resumen, conceptos, codigo con minuto y "A verificar" con busquedas que haces TU despues) y modo `referencia` (reel/TikTok/URL: gancho 0-3 s, planos, ritmo, textos, estilo, leccion). Clase de 3 min = 85 s; reel de 1 min = 137 s. Para TRANSCRIBIR audio/video tambien es este (mira `transcripcion.txt`). La grabacion nunca sale a internet. Salida: `antigravity\documentos_generados\destilados\<fecha>_<nombre>\` (resumen.md, transcripcion.txt, vista.md, capturas\) | `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\video\destilador_video\destilar.py" "<video o URL>" --modo clase` · trozo: `--desde 40:00 --hasta 55:00` · rapido: `--modelo small` · solo transcribir: `--sin-vista --sin-resumen` |
| penpot_mcp/lanzar.py | MCP de PENPOT (diseno en design.penpot.app): lo enciende el hook cuando hablas de Penpot; instala y arranca @penpot/mcp en ~/nova_penpot_mcp y conecta con mcp-remote. Necesita Node.js. Ver penpot_mcp/LEEME.md | `nova_mcp.py activar penpot` |
| video/ | Video: generar_voz.py (narracion Edge TTS), nova_intro_template.py (intro 10 s), capturar_fotogramas.py, auditar_hoja_vl.py (InternVL), nova_video_router.py (escenas local/nube) (el destilador VIEJO se retiro el 25/11: usa destilador_video) | ver cada script |
| seguridad/ | git_clone_sentinel.ps1 + nova_repo_scanner.py: escanea repos de terceros al clonarlos (activar: `. <ruta>\git_clone_sentinel.ps1` en el perfil de PowerShell) | `git-clone-guard <url>` |
| nube/ | nova_external_shield.py (IA gratis en la nube CON filtro de datos sensibles y vuelta a local), groq_zero_token_client.py (Whisper + Llama 70B gratis), gmail_api_client.py (buscar correos), youtube_api_client.py (buscar videos) | ver cada script |
| pruebas/phantom_test.ps1 | Prueba codigo en una rama temporal de git o caja aislada y la descarta si falla | `powershell -File ...\pruebas\phantom_test.ps1 -?` |
| proyecto/GEMINI_community.md | Plantilla 'Community Edition' de las reglas (para la version open source de Nova) | referencia |
| scripts\nova_puente_capturas.py (arranca solo) | Adjuntos del chat -> temporal\<mes>\: imagen descrita por InternVL (.vista.md), documento destilado (.resumen.md), indice temporal\INDICE.md | automatico; `--analizar --prompt` para preguntar por la ultima imagen |
| nova_core\conversor.py + resumir.py | Destilar (texto limpio por trozos) y resumir con Qwen local PDF, Word, Excel, PowerPoint, txt, md, csv, html | `<PYTHON> <NOVA_HOME>\nova_core\resumir.py doc.pdf [--ollama --vinetas 6]` |
| nova_core\redactar.py | Documentos por tipos (actividad, informe...) con revision final y exportacion a Word/PDF/Markdown en antigravity\documentos_generados (redactor.py, el viejo, se retiro el 25/11) | `<PYTHON> <NOVA_HOME>\nova_core\redactar.py` (ver index-nova-core / GEMINI.md) |
| radar_web.py | Mide 3-5 webs reales del sector (202 de draw.mjs o URLs del usuario) y deja `datos\referencias_web\<sector>\resumen.txt` (estructura, ritmo, densidad; sin textos ni fotos ajenas) | `<PYTHON> <NOVA_HOME>\antigravity\herramientas\radar_web.py --sector health --max 4` |
| medios.py + efectos.py (en `almacen\biblioteca_web\`) | Fotos de CDN gratis comprobadas (420 Unsplash/Picsum + Openverse) y kit de efectos de scroll (pasos, zoom, mascara, horizontal, apiladas, video, fondo vivo, titular, contador, relleno, magnetico) | Caja de herramientas del estudio web (`estudio.py herramientas`) y de nova_secciones.py |
| nova_secciones.py (en `antigravity\scripts\`) | Qwen pica una web seccion a seccion desde `secciones.json` masticado + acabados (aparicion, halo, Lenis) | `python ...\scripts\nova_secciones.py --carpeta <ruta>` · repicar: `--solo id1,id2` · solo montar: `--solo-montar` |

## Herramientas que ya existen en otras carpetas (se moveran aqui en la reorganizacion)

| Herramienta | Donde esta hoy | Que hace |
|---|---|---|
| nova_tarea.py | `antigravity\scripts\` | Comando unico: webs por categoria, referencia (clonador), verificar, contrato + Qwen |
| nova_pipeline_local.py | `antigravity\scripts\` | Pipeline Capa 0: Qwen pica, linter, Playwright + InternVL revisan |
| nova_auditoria.py | `antigravity\scripts\` | Auditoria de seguridad real (15 reglas, npm audit, pip-audit) |
| resumir.py / conversor.py | `nova_core\` | Leer documentos grandes en local sin gastar tokens |
| orquestador.py | `nova_core\` | Linter de commits (freno del 35 %) |
| biblioteca_web | `antigravity\almacen\biblioteca_web\` | Bloques de webs para 15 categorias (solo lectura para Nova) |
| draw.mjs | `antigravity\almacen\skills\gemini-ui-artisan\scripts\` | Sorteo de direccion de arte |
| clonador (clones_web) | `<NOVA_HOME>\antigravity\clonador` | Clonar una web de referencia (solo se ejecuta, via `nova_tarea.py --referencia`) |
| voz/guardian_claves.py | GUARDIAN DE CLAVES: la aduana (aduana.js v2) intercepta las claves de API que el usuario pega en el chat, las guarda en vault\google_cloud.env + variables de Windows y en el chat deja '[clave guardada en el cofre: NOMBRE]'. Enter con una clave escrita se frena. Nunca muestra valores | `<PYTHON> <NOVA_HOME>\antigravity\herramientas\voz\guardian_claves.py lista` · `renombrar VIEJO NUEVO` |
