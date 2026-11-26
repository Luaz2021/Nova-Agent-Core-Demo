# NOVA DIRECTOR (v3.3 · Windows, macOS y Linux)

Orquestador casero para **proyectos grandes** (app completa, full stack, varios módulos). Nace de 5 pruebas medidas el
26/11/2026 con la misma API. Principio: **"el arquitecto no vive en la
obra"**: los modelos caros entran con un sobre cerrado, deciden y se van; el barato construye con caché; la máquina comprueba.

**Necesita la CLI oficial de Antigravity (`agy`)**: instálala desde la documentación oficial de Antigravity para tu
sistema, abre una terminal, escribe `agy` e inicia sesión una vez con tu cuenta. Luego comprueba los modelos con
`<PYTHON> "<NOVA_HOME>/antigravity/herramientas/director/nova_director.py" modelos`. Gasta de tu misma bolsa de Gemini.
En Windows los criterios de cada fase se ejecutan en PowerShell; en macOS/Linux, en bash (el arquitecto lo sabe).
El aviso en el chat usa el puerto de depuración de Antigravity (si no está, solo suena el aviso).

## Cómo entra Nova (carril `proyecto`)
El hook detecta "app completa", "full stack", "sistema de gestión", "desde cero", "front y back", `/director`... y manda
leer `herramientas\carriles\carril_proyecto.md`. Nova escribe `TAREA.md`, avisa en una línea y lanza:
```
<PYTHON> "<NOVA_HOME>/antigravity/herramientas/director/nova_director.py" lanzar "<carpeta>" --idea "<carpeta>\TAREA.md"
```
Después no hace nada. **Marina avisa** al acabar, al pausar o si se para (clips `voice_cache\marina\aviso_director_*`).
`resumen` le da a Nova todo para explicártelo. Tras una pausa: `lanzar "<carpeta>" --continuar`.

## Flujo
| Paso | Quién | Qué |
|---|---|---|
| 1. Especificar + planos | Neon Medium | Lee el **catálogo** (`catalogo.md`: rutas sin_ui / con_ui / web_negocio / clon / legacy + tarjetas de herramientas). Escribe `spec.md` (R1..Rn "CUANDO..., EL SISTEMA DEBE..."), `preguntas.json` (si falta algo que cambia el diseño → PAUSA y pregunta), `arquitectura.md` (+ contrato API), `fases.json` (3-5 fases; `obra` o `pausa`) |
| 2. Obra | Hydrogen High | Fases seguidas en la MISMA conversación (caché); paralelo solo sin archivos compartidos. Criterios = comandos que ejecuta el director (0 tokens). Falla → 2.º intento → Neon High → Carbon → para y avisa |
| Pausas | Nova + el usuario | Diseño con el estudio web + **vale del usuario**, preguntas... Se dan por hechas cuando sus criterios pasan |
| 3. Inspección | Neon Medium → Neon XHigh | Paso 1: TODO (escáneres + diff + spec + revisión visual si hay UI). Paso 2: XHigh solo en zonas críticas (si las hay). Arreglo crítico/alto por Hydrogen → reinspección Medium. Lo que **contradice el enunciado** no se toca: decide el usuario |

Modos de inspección (`--inspeccion` o `inspeccion_modo` en `director.json`): `completa` · `ligera` (solo paso 1) · `ninguna` (solo máquinas).
Tope de gasto: `presupuesto_ponderado` (2,5 M). Todo queda en `<proyecto>\.director\` (`director.log`, `estado.json`,
`spec.md`, `INSPECCION.md`, `PAUSA.md`...).

## Lo medido (misma API, 26/11)
| | Construir | Inspección | Calidad |
|---|---|---|---|
| Orchestrator Antigravity | 961k (≈4 % 5h) | — | buena, sin revisar |
| Director v3 | **573k (≈2,6 %)** | 1,78 M (ya recortado en v5: paso 1 y reinspección con Medium, paso 2 solo si hay algo crítico) | 0 altos tras inspección |

## El hook de Nova con el director (26/11 noche)
Las llamadas del director pasan por los MISMOS hooks que Nova. Sin ventana, "preguntar" = "no". El hook reconoce que
la llamada es del director (transcript en `.gemini\antigravity-cli\brain` + `<proyecto>\.director\en_marcha.json`, que
el director crea al trabajar y borra al acabar) y entonces:
- Borrar DENTRO del proyecto o de `%TEMP%` no pregunta (fuera, la carpeta entera, `.director`, `..`, git reset/clean/push
  siguen frenados).
- Sus frenos no hacen hablar a Marina (avisa el director al acabar / pausar / parar).
- `<proyecto>\.director\permisos.json` = el "dale, sigue" del usuario SOLO para ese proyecto
  (`{"permitir": [{"patron": "<regex>", "motivo": "..."}]}`; nunca claves, cofre, zona blindada ni núcleo).
- Si una fase falla 2 veces con Hydrogen y el hook le frenó algo, el director NO escala a Neon/Carbon: PAUSA explicando
  qué se frenó (Nova se lo cuenta al usuario; si dice que sí, regla en permisos.json y --continuar).
Siempre (también Nova normal): añadir lecciones al inbox (`Add-Content ... inbox_lecciones.md`) y leer la salida de SUS
comandos (`brain\<su conv>\.system_generated\steps|tasks`). Baterías: D2 16/16, hook 0 fallos, regresión 6.652
llamadas reales = solo cambian 70 "añadir lección" (de preguntar a permitir).

Revisión visual (ruta con_ui): si el proyecto es una app FastAPI (`app/main.py`), el director la ARRANCA en un puerto
libre con una BD temporal y revisa la URL (antes salían "0 páginas").

Git (ramas del trabajo): `.director/` va a `.git\info\exclude` (local) y la ficha prohíbe commit/push/reset/clean.
⚠ Antes de usarlo con código de una empresa: su política de IA (el código va a Google/Gemini).

## Requisitos (una vez por equipo)
CLI `agy` en `~/agy/bin` con sesión iniciada (`agy`), `nova_director.py modelos` en OK. La CLI usa tu cupo
Gemini, tus hooks y tus reglas deny. Sin ventana solo confía en System32: el director pasa `--settings trustedWorkspaces`
en cada llamada. `--mode auto` no está disponible en la cuenta (no hace falta). Ojo: al continuar una conversación agy
devuelve el uso ACUMULADO (el director resta lo ya contado).

## Probar sin gastar
`DIRECTOR_AGY=<simulador.py>` + `DIRECTOR_SIN_ESCANERES=1` (simulador de Claude en su scratchpad del 26/11: paralelo,
reintentos, escalera hasta parar, preguntas → respuestas → continuar, pausa de diseño, 3 modos de inspección).
