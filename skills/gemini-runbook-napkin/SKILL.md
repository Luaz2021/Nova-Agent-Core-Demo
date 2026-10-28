---
name: gemini-runbook-napkin
description: "Servilleta activa de errores pasados y su accion correctiva (Do instead) para no tropezar dos veces."
trigger: always_on
---

# Napkin (Error Trap & Fast Execution Runbook)

La filosofÃ­a de **Napkin** (la "servilleta") no es ser un diario aburrido de historial, sino un **runbook de supervivencia tÃ©cnica**: una lista priorizada de errores y tropiezos cometidos, donde cada problema tiene una soluciÃ³n obligatoria: **"Hacer en su lugar" (Do instead)**.

---

## 1. DÃ³nde se Guarda el Napkin

Para que funcione tanto en tu proyecto actual como sincronizado en tu nube:
1. **En el repositorio/proyecto activo:** `.agents/napkin.md` (o `napkin.md`).
2. **En tu nube global:** `G:\Mi unidad\Antigravity\memory\napkin-global.md` (para tropiezos que aplican a todos tus proyectos en Windows/PC/Laptop).

---

## 2. Al Iniciar Cualquier SesiÃ³n (Lectura Silenciosa)

Al comenzar una tarea o abrir un proyecto, el agente lee silenciosamente el archivo de napkin:
- Interioriza los tropiezos previos y las directivas del usuario.
- **Aplica las lecciones sin hacer ruido:** No dice *"He leÃ­do el napkin"*; simplemente ejecuta el cÃ³digo evitando esos errores.

---

## 3. Formato Obligatorio del Napkin (Estructura "Hacer en su lugar")

El napkin prohÃ­be quejas sin soluciÃ³n. Cada entrada debe tener el formato exacto:

```markdown
# Napkin Runbook

## 1. EjecuciÃ³n y ValidaciÃ³n (Prioridad Alta)
1. **[YYYY-MM-DD] Error al migrar base de datos con campos nulos**
   - **Hacer en su lugar:** Asignar siempre un valor default o ejecutar script de backfill antes del NOT NULL.

## 2. Comandos y Entorno (Windows / PowerShell)
1. **[YYYY-MM-DD] Comandos bash con && fallan en ciertas versiones de PowerShell**
   - **Hacer en su lugar:** Usar `;` o comandos encadenados nativos de PowerShell.

## 3. Directivas y ManÃ­as del Usuario
1. **[YYYY-MM-DD] El usuario prefiere siempre tipado estricto en TypeScript sin usar `any`**
   - **Hacer en su lugar:** Definir interfaces explÃ­citas o usar `unknown` con type guards.
```

---

## 4. Regla de CuraciÃ³n Continua (MÃ¡ximo 10 por categorÃ­a)

- Para que el archivo no crezca infinitamente ni consuma tokens innecesarios, se mantiene un **mÃ¡ximo de 10 notas por categorÃ­a** (las 10 mÃ¡s crÃ­ticas y recientes).
- Las notas viejas o que ya no aplican se fusionan o se limpian automÃ¡ticamente.

