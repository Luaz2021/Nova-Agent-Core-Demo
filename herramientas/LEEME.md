# Herramientas de Nova

Carpeta OFICIAL de herramientas de Nova (protegida: Nova la consulta y usa, pero no escribe aqui). Antes de crear
un script, Nova mira este indice para no repetir uno que ya existe.

Reglas:
- Script NUEVO -> se crea en `antigravity\scratch\` (la sala de espera, carpeta por defecto de Antigravity), nunca aqui directamente.
- Pasa a esta carpeta solo cuando Alexander lo valida y Claude le pasa auditoria; entonces se apunta en el indice.
- Lo que una herramienta GENERE (datos, capturas, informes) va en `herramientas\datos\<nombre>\`, no junto al script.
- No se copian textos ni fotos de webs ajenas: solo medidas y estructura.

## Indice (herramientas nuevas)

| Herramienta | Que hace | Uso |
|---|---|---|
| horario/nova_horario.py | Widget de escritorio de Luaz: HORARIO de clase (semana real con fechas, Semana A/B automatica, hoy y clase en curso marcadas, clic en un cuadro = nota de ese dia) + APUNTES de pendientes en 3 pestanas (Estudios, Personal, Proyectos). Datos en `herramientas\datos\horario\` (viajan por Drive). Sin librerias extra (tkinter). Nova no edita esos json: si Luaz quiere apuntar algo, lo apunta el en el widget | abrir: acceso "Horario Nova" del Escritorio · crearlo en otro equipo: `& $env:NOVA_PYTHON "<NOVA_HOME>\antigravity\herramientas\horario\nova_horario.py" --acceso` |
| trello/trello.py | Trello generico: tableros, listas, tarjetas, crear, mover, comentar, archivar. Claves del vault leidas en local, nunca impresas | `<PYTHON> <NOVA_HOME>\antigravity\herramientas	rello	rello.py tableros` (ver --help) |
| voz/nova_voz.py | Manos libres: di 'Nova' y dicta la orden al chat de Antigravity (voz neural; sin widget; lista para la voz clonada de voice_clone) | `pythonw ...\herramientasoz
ova_voz.py` |
| video/ | Video: generar_voz.py (narracion Edge TTS), nova_intro_template.py (intro 10 s), capturar_fotogramas.py, auditar_hoja_vl.py (InternVL), nova_video_router.py (escenas local/nube), destilador/ (analiza reels y TikTok en local) | ver cada script |
| seguridad/ | git_clone_sentinel.ps1 + nova_repo_scanner.py: escanea repos de terceros al clonarlos (activar: `. <ruta>\git_clone_sentinel.ps1` en el perfil de PowerShell) | `git-clone-guard <url>` |
| nube/ | nova_external_shield.py (IA gratis en la nube CON filtro de datos sensibles y vuelta a local), groq_zero_token_client.py (Whisper + Llama 70B gratis), gmail_api_client.py (buscar correos), youtube_api_client.py (buscar videos) | ver cada script |
| pruebas/phantom_test.ps1 | Prueba codigo en una rama temporal de git o caja aislada y la descarta si falla | `powershell -File ...\pruebas\phantom_test.ps1 -?` |
| proyecto/GEMINI_community.md | Plantilla 'Community Edition' de las reglas (para la version open source de Nova) | referencia |
| scripts\nova_puente_capturas.py (arranca solo) | Adjuntos del chat -> temporal\<mes>\: imagen descrita por InternVL (.vista.md), documento destilado (.resumen.md), indice temporal\INDICE.md | automatico; `--analizar --prompt` para preguntar por la ultima imagen |
| nova_core\conversor.py + resumir.py | Destilar (texto limpio por trozos) y resumir con Qwen local PDF, Word, Excel, PowerPoint, txt, md, csv, html | `<PYTHON> <NOVA_HOME>\nova_core\resumir.py doc.pdf [--ollama --vinetas 6]` |
| nova_core\redactor.py | Redacta documentos con Qwen y los exporta a Word, PDF o Markdown (temas apa, ejecutivo, moderno, clasico) en antigravity\documentos_generados | `<PYTHON> <NOVA_HOME>\nova_core\redactor.py --prompt "..." --salida informe.pdf --tema ejecutivo` |
| radar_web.py | Mide 3-5 webs reales del sector (202 de draw.mjs o URLs de Alexander) y deja `datos\referencias_web\<sector>\resumen.txt` (estructura, ritmo, densidad; sin textos ni fotos ajenas) | `<PYTHON> <NOVA_HOME>\antigravity\herramientas\radar_web.py --sector health --max 4` |
| medios.py + efectos.py (en `almacen\biblioteca_web\`) | Fotos de CDN gratis comprobadas (420 Unsplash/Picsum + Openverse) y kit de efectos de scroll (pasos, zoom, mascara, horizontal, apiladas, video, fondo vivo, titular, contador, relleno, magnetico) | Se piden desde `secciones.json` (ver skill index-ui-frontend, modo C paso 6) |
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
| voz/guardian_claves.py | GUARDIAN DE CLAVES: la aduana (aduana.js v2) intercepta las claves de API que Luaz pega en el chat, las guarda en vault\google_cloud.env + variables de Windows y en el chat deja '[clave guardada en el cofre: NOMBRE]'. Enter con una clave escrita se frena. Nunca muestra valores | `<PYTHON> <NOVA_HOME>\antigravity\herramientas\voz\guardian_claves.py lista` · `renombrar VIEJO NUEVO` |
