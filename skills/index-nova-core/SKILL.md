---
name: index-nova-core
description: "Indice Macro Nova Core: memoria local, sincronizacion v4, napkin y aprendizaje de errores, enrutado de modelos, ahorro de tokens y creacion de skills. Usar cuando la tarea trate sobre la propia Nova."
---

# Index 08 · Nova Core: Memoria, Aprendizaje, Sync & Skills (1-Hop Router)

## 1. Reglas Operativas Directas (80/20 - Aplicar sin lecturas extra)
- **Todo es local:** memoria en `<NOVA_HOME>\antigravity\memory\`, indices en `<NOVA_HOME>\config\skills\`, almacen en `<NOVA_HOME>\antigravity\almacen\skills\`. Nunca leer ni escribir archivos de Nova en `G:`; Drive es solo respaldo que mueve `sync_antigravity.ps1`.
- **Napkin vs Aprendizaje:**
  - *Napkin* = un error concreto y su arreglo. Global en `memory\napkin-global.md`; de un proyecto en `<proyecto>\.agents\napkin.md`. Formato: `[Contexto] -> [Causa raiz] -> [Hacer en su lugar]`.
  - *Aprendizaje* = como pensar o verificar. Vive en la seccion "Trampas de Flash" / "Definicion de hecho" del `index-*` de su dominio.
- **Capturar una leccion (barato, 1 llamada):** solo si Alexander corrige, un test falla o se repite un error. Anadir UNA linea al final de `memory\inbox_lecciones.md`:
  `- [AAAA-MM-DD] [dominio] situacion -> hacer en su lugar`
  Prohibido leer el inbox durante una tarea normal, prohibido volcar logs, diffs o salida de Qwen en el (asi se inflo learnings.md a 1.9 MB).
- **Destilar (`/destilar`, semanal):** lo ejecuta un modelo fuerte (Claude o Argon, nunca Flash ni Qwen 9B). Lee `inbox_lecciones.md` + `mis_quejas.md`, fusiona cada leccion en el `index-*` o napkin que toque, elimina duplicadas y vacia el inbox. Tope: si un `index-*` pasa de 60 lineas, fusionar reglas antes de anadir.
- **Dos puentes (Drive es el original):** "Nova, sube los cambios" = `sync_antigravity.ps1 -Modo Subir` (entrada a Drive); "Nova, sincroniza" = `sync_antigravity.ps1` (salida desde Drive, tambien al encender). La memoria sube sola al cerrar Antigravity. Leer el resultado solo en `memory\sync_status.json`: `BLOQUEADOS` -> pedir "sincroniza" y volver a subir; `CONFLICTOS` -> nombrar los `*.local-*` guardados; `ALERTA_REVISAR` -> no repetir, avisar en 1 linea.
- **Ahorro de tokens:** una sola lectura por archivo, nunca recorrer `memory\` entera, nunca abrir `bitacora_claude_ollama.txt` ni `memory\archivo\` salvo orden directa.
- **Nueva skill:** va al almacen `almacen\skills\<nombre>\SKILL.md` con frontmatter (`name`, `description`) y se enlaza en UN solo `index-*`. Una skill que ningun indice nombra no existe para Nova.
- **Proyectos Reales = GitHub First (PC <-> Laptop):** En todo proyecto nuevo desde 0 (no prueba/scratch) o cuando Alexander diga *"mira este proyecto"* y no tenga `git remote -v` hacia GitHub, recordarle en el acto subirlo a GitHub y usar `git clone` / `git pull` entre PC y Laptop para que ningun proyecto quede atrapado en local.
- **Orden de Escritorio (PecoFence Rust ~15MB RAM):** Si Alexander pide ordenar el escritorio en PC o Laptop, ejecutar `<NOVA_HOME>\antigravity\scripts\nova_pecofence_setup.ps1` (instala `DayuanJiang.PecoFence` y arma las 5 cajas Acrylic Dark sin overflow: `Programacion & IA`, `Juegos, DJ & Web`, `Carpetas & Documentos`, `Temporal (Borrar al final)` y `Sistema`).

## Trampas de Flash (errores reales ya cometidos)
- Arranque: si el puente no existe, parar en 1 llamada (se llegaron a lanzar 19 lecturas a ciegas).
- No leer `.ipynb` / `.jsonl` completos (20k tokens de golpe); usar micro-scripts.
- No diagnosticar costes de tokens sin medir: comprobar el prompt real antes de culpar a MCPs o skills.

## Definicion de hecho
- Sync: `sync_status.json` con `Errores = []`; si hay `Bloqueados` o `CopiasLocalesGuardadas`, nombrarlos.
- Skills: toda skill nueva enlazada en un solo `index-*` y subida con "Nova, sube los cambios".
- `/destilar`: inbox vacio despues, ningun `index-*` por encima de 60 lineas.

## 2. Catalogo Profundo Bajo Demanda (`<NOVA_HOME>\antigravity\almacen\` + la ruta `skills\...` de cada entrada; copia local, nunca leer de G:)
Leer con `read_file` **unicamente** si la tarea exige el protocolo completo:
- **Memoria & Aprendizaje:** `skills\gemini-runbook-napkin\SKILL.md` | `skills\gemini-continuous-learner\SKILL.md` | `skills\gemini-mem\SKILL.md` | `skills\gemini-daily-briefing\SKILL.md`
- **Tokens, Prompts & Modelos:** `skills\gemini-prompt-distiller\SKILL.md` | `skills\gemini-multiagent-router\SKILL.md` | `skills\gemini-omniroute-manager\SKILL.md` | `skills\council-multi-model\SKILL.md`
- **Estilo de Respuesta:** `skills\gemini-concise-voice\SKILL.md` | `skills\gemini-concise-clean-code\SKILL.md` | `skills\user-intent-reader\SKILL.md`
- **Crear & Buscar Skills:** `skills\gemini-skill-architect\SKILL.md` | `skills\find-skills\SKILL.md`
- **Herramientas oficiales (08/11):** indice `<NOVA_HOME>ntigravity\herramientas\LEEME.md` (trello, voz, video, seguridad, nube, pruebas, radar). Antes de crear un script, mirar ahi.
