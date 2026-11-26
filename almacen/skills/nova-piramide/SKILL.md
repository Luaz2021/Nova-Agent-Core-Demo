---
name: nova-piramide
description: "Piramide de modelos de Nova (20/11/2026, al dia 24/11 con Antigravity 2.35): cuando y como escalar una duda o un fallo (asesor Hydrogen xhigh -> ventana Carbon -> Neon -> Opus -> Claude), el orquestador casero (PLAN.md) y cuando usar el Orchestrator de Google. Usar cuando algo no sale, cuando la tarea es gorda o cuando el usuario habla de modelos, cupo u orquestador."
---

# Piramide de Nova (medida con el usuario el 20/11; modelos al dia el 24/11)

**24/11:** Gemini 3.8 Flash, Gemini 4 Argon y GPT-OSS 120B se retiran el 30/11/2026. La ventana base pasa a
**Gemini 4 Hydrogen** y la escalera pesada a **Carbon -> Neon**.

**Idea:** la ventana base (Hydrogen) NUNCA cambia de modelo: asi conserva su cache y gasta poco. Los modelos pesados
entran con UNA pregunta concreta en texto plano, resuelven y se van (no engordan con la conversacion).

## Las dos bolsas de cupo (visor View Usage)
- **Gemini Models**: TODOS los Gemini (Hydrogen, Neon, Carbon, el Orchestrator) gastan de la MISMA bolsa, segun el
  precio de cada modelo. Un pesado vacia la bolsa de Hydrogen mucho mas rapido.
- **Claude and GPT models**: Opus 5.5 y Sonnet 5.5 van aparte. Para una segunda opinion de OTRA familia sin tocar la
  bolsa Gemini, Claude es la opcion.
- Cada bolsa tiene limite semanal y de 5 horas.

## La escalera
| Nivel | Quien | Cuando | Como | Bolsa |
|---|---|---|---|---|
| 0 | **Hydrogen** (tu) | Siempre | Trabajo normal + carriles por tema | Gemini |
| 1 | **Asesor** (sub-agente `asesor`, nivel pro = Hydrogen xhigh, solo lectura) | el usuario lo pide o 2 fallos seguidos (el hook te avisa y te frena) | `invoke_subagent` TypeName `asesor` con pregunta concreta; la 2a vez `send_message` al MISMO. Max 2 por conversacion | Gemini |
| 2 | **Carbon** (High) | El asesor no lo saca | Consulta de ventana | Gemini (pesado x4) |
| 3 | **Neon** (High/Extra) | Carbon no lo saca | Consulta de ventana | Gemini (pesado x4) |
| 4 | **Claude Opus 5.5** | Salvavidas | UNA consulta de ventana | Claude/GPT (x10) |
| 5 | **Claude Code** (fuera de Antigravity) | Ultimo recurso | el usuario le lleva la carpeta de la consulta | Suscripcion de Claude |

**Ojo con los sub-agentes:** solo aceptan `inherit`, `flash` o `pro`, y los dos acaban en Hydrogen (high / xhigh).
Un sub-agente NO puede ser Neon, Carbon ni Claude: para eso es la consulta de ventana. Ademas el sub-agente NO ve la
conversacion: pasale solo la pregunta y las rutas.

**Atajo:** si el usuario dice "esto va directo a Neon/Opus" o es algo GORDO o urgente (SaaS, bug en sistema grande, REA,
video largo), salta directo al nivel que diga. Lo decide el.

## Consulta de ventana (niveles 2-5)
```
<PYTHON> "<NOVA_HOME>/antigravity/herramientas/consultas/nova_consulta.py" nueva --titulo "<tema>" --pregunta "<que necesitas decidir>" --intentado "<que probaste y el error exacto>" --archivos "<ruta1>,<ruta2>"
```
- El script elige el siguiente nivel que NO haya fallado en ese tema y te da la frase exacta para el usuario.
- Cuando vuelva: lee `respuesta.md` de la consulta, aplicalo y cierra:
  `nova_consulta.py cerrar <id> --resultado resuelto|no_resuelto [--nota "..."]` (apunta la leccion sola).
- `nova_consulta.py estado` = consultas abiertas.
- Si TE abren a ti en una ventana nueva con "responde la consulta <ruta>": lee SOLO esa consulta y sus archivos, escribe la respuesta donde dice y no toques nada mas.

## Orquestador casero (tareas medianas-gordas)
`nova_consulta.py nueva --tipo plan --titulo "..." --pregunta "<objetivo>" --archivos "..."` -> Carbon/Neon escribe
`PLAN.md` (pasos pequenos con archivos y comprobacion) -> tu ejecutas paso a paso en TU ventana. Si te atascas,
escribe `ESTADO.md` en esa carpeta (hecho / falla / duda) y pide revisar SOLO eso.

## Orchestrator de Google (selector "Orchestrator", planificador Neon por defecto)
- Planificador: Neon, Carbon (u Opus). Ejecutor: SOLO Hydrogen o Claude Sonnet 5.5. Desde 2.35 los dos arrancan en
  esfuerzo High (gasta mas).
- Medido el 20/11: cada relevo reenviaba la conversacion ENTERA sin cache (hasta 183k de golpe). Para lo
  pequeno/mediano es mas caro que la ventana base.
- Solo para lo ENORME y en ventana nueva arrancando con un dosier corto (la consulta tipo plan sirve de dosier).
- Con orquestador el hook NO frena gasto ni seguidas: solo avisa (Marina cada 3 % de la bolsa Gemini) y escribe un
  informe en `memory/registros/orquestador/`.

## Coste (nova_core\nova_cupo.py)
Hydrogen x1 · Neon/Carbon/orquestador x4 (bolsa Gemini) · Sonnet x4 · Opus x10 (bolsa Claude/GPT). ~175k ponderados
= 1 % semanal de la bolsa Gemini (ESTIMACION heredada de Flash: se recalibra con el visor).
