---
name: index-nova-core
description: "Indice Macro Nova Core: memoria local, sincronizacion v4, napkin y aprendizaje de errores, enrutado de modelos, ahorro de tokens y creacion de skills. Usar cuando la tarea trate sobre la propia Nova."
---

# Index 08 · Nova Core: Memoria, Aprendizaje, Sync & Skills (1-Hop Router)

## 1. Reglas Operativas Directas (80/20 - Aplicar sin lecturas extra)
- **Todo es local:** memoria en `<NOVA_HOME>/antigravity/memory/`, indices en `<NOVA_HOME>/config/skills/`, almacen en `<NOVA_HOME>/antigravity/almacen/skills/`. Nunca leer ni escribir archivos de Nova en `G:`; Drive es solo respaldo que mueve `sync_antigravity.ps1`.
- **Napkin vs Aprendizaje:**
  - *Napkin* = un error concreto y su arreglo. Global en `memory/napkin-global.md`; de un proyecto en `<proyecto>/.agents/napkin.md`. Formato: `[Contexto] -> [Causa raiz] -> [Hacer en su lugar]`.
  - *Aprendizaje* (23/11) = `memory/aprendido.jsonl`: una regla por error con `veces`. Lo lees en el bloque "Errores que ya cometiste" de cada kit de carril (y abajo, el de Nova). Buscar mas: `nova_core\nova_aprendido.py buscar <tema> <palabra>`.
- **Capturar (barato, 1 llamada), UNA sola entrada:** si el usuario corrige o se queja, un test falla o se repite un error, anadir UNA linea al final de `memory/inbox_lecciones.md`:
  `- [AAAA-MM-DD] [tema] (de: usuario|nova) cuando ... -> hacer en su lugar` (tema: web, backend, consola, redaccion, investigacion, video, rea, nova). `mis_quejas.md` ya no se usa.
  Prohibido leer el inbox durante una tarea normal y volcar logs, diffs o salida de Qwen en el.
- **Destilar (`/destilar`, cuando el hook avise: 15+ lineas):** lo hace Claude. Pasa cada linea a `aprendido.jsonl` (regla nueva o `veces`+1, nunca reescribir todo), regenera los kits con `nova_aprendido.py kits`, archiva el inbox en `memory/archivo/` y propone a codigo lo que llegue a 3 veces.
- **Dos puentes (Drive es el original):** "Nova, sube los cambios" = `sync_antigravity.ps1 -Modo Subir` (entrada a Drive); "Nova, sincroniza" = `sync_antigravity.ps1` (salida desde Drive, tambien al encender). La memoria sube sola al cerrar Antigravity. Leer el resultado solo en `memory/sync_status.json`: `BLOQUEADOS` -> pedir "sincroniza" y volver a subir; `CONFLICTOS` -> nombrar los `*.local-*` guardados; `ALERTA_REVISAR` -> no repetir, avisar en 1 linea.
- **Ahorro de tokens:** una sola lectura por archivo, nunca recorrer `memory/` entera, nunca abrir `bitacora_claude_ollama.txt` ni `memory/archivo/` salvo orden directa.
- **Nueva skill:** va al almacen `almacen/skills/<nombre>/SKILL.md` con frontmatter (`name`, `description`) y se enlaza en UN solo `index-*`. Una skill que ningun indice nombra no existe para Nova.
- **Proyectos Reales = GitHub First (PC <-> Laptop):** En todo proyecto nuevo desde 0 (no prueba/scratch) o cuando el usuario diga *"mira este proyecto"* y no tenga `git remote -v` hacia GitHub, recordarle en el acto subirlo a GitHub y usar `git clone` / `git pull` entre PC y Laptop para que ningun proyecto quede atrapado en local.
- **Orden de Escritorio (SOLO WINDOWS, PecoFence Rust ~15MB RAM):** Si el usuario pide ordenar el escritorio (en macOS/Linux: dile que no esta disponible), ejecutar `<NOVA_HOME>/antigravity/scripts/nova_pecofence_setup.ps1` (instala `DayuanJiang.PecoFence` y arma las 5 cajas Acrylic Dark sin overflow: `Programacion & IA`, `Juegos, DJ & Web`, `Carpetas & Documentos`, `Temporal (Borrar al final)` y `Sistema`).

## Trampas de Nova (errores reales ya cometidos)
- Arranque: si el puente no existe, parar en 1 llamada (se llegaron a lanzar 19 lecturas a ciegas).
- No leer `.ipynb` / `.jsonl` completos (20k tokens de golpe); usar micro-scripts.
- No diagnosticar costes de tokens sin medir: comprobar el prompt real antes de culpar a MCPs o skills.

## Definicion de hecho
- Sync: `sync_status.json` con `Errores = []`; si hay `Bloqueados` o `CopiasLocalesGuardadas`, nombrarlos.
- Skills: toda skill nueva enlazada en un solo `index-*` y subida con "Nova, sube los cambios".
- `/destilar`: inbox vacio despues, ningun `index-*` por encima de 60 lineas.

## 2. Catalogo Profundo Bajo Demanda (`<NOVA_HOME>/antigravity/almacen/` + la ruta `skills/...` de cada entrada; copia local, nunca leer de la carpeta de Drive)
Leer con `read_file` **unicamente** si la tarea exige el protocolo completo:
- **Memoria & Aprendizaje:** `skills/gemini-runbook-napkin/SKILL.md` | `skills/gemini-continuous-learner/SKILL.md` | `skills/gemini-mem/SKILL.md` | `skills/gemini-daily-briefing/SKILL.md`
- **Piramide de modelos (20/11):** `skills/nova-piramide/SKILL.md` (asesor, consultas de ventana Carbon -> Neon -> Opus -> Claude, orquestador casero, cuando NO usar el Orchestrator de Google). Leer cuando algo no sale tras 2 intentos o la tarea es gorda.
- **Tokens, Prompts & Modelos:** `skills/gemini-prompt-distiller/SKILL.md` | `skills/gemini-multiagent-router/SKILL.md` | `skills/gemini-omniroute-manager/SKILL.md` | `skills/council-multi-model/SKILL.md`
- **Estilo de Respuesta:** `skills/gemini-concise-voice/SKILL.md` | `skills/gemini-concise-clean-code/SKILL.md` | `skills/user-intent-reader/SKILL.md`
- **Crear & Buscar Skills:** `skills/gemini-skill-architect/SKILL.md` | `skills/find-skills/SKILL.md`
- **Herramientas oficiales (08/11):** indice `<NOVA_HOME>/antigravity/herramientas/LEEME.md` (trello, voz, video, seguridad, nube, pruebas, radar). Antes de crear un script, mirar ahi.

<!-- ERRORES_YA_COMETIDOS:INICIO -->
## Errores que ya cometiste (no los repitas)
_Lo genera `nova_aprendido.py kits` desde `memory/aprendido.jsonl` (tus propios errores): no lo edites a mano. Aun no hay ninguno._
<!-- ERRORES_YA_COMETIDOS:FIN -->
