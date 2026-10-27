---
name: gemini-continuous-learner
trigger: model_decision
description: "Meta-habilidad de auto-aprendizaje y mejora continua (inspirada en Task Observer / One Skill to Rule Them All). Observa patrones de trabajo, correcciones del usuario y fricciones en las sesiones para aprender preferencias, evitar repetir errores y actualizar las reglas o skills automÃ¡ticamente."
---

# Self-Learning Observer (One Skill to Rule Them All)

Esta meta-habilidad permite que el asistente **aprenda de tus correcciones, de tus preferencias habituales y de las fricciones de trabajo** a lo largo del tiempo. Su objetivo es convertir cada correcciÃ³n que hagas en una regla persistente para no cometer el mismo error dos veces y adaptarse a tu estilo de programaciÃ³n entre tu PC y tu Laptop.

---

## 1. DÃ³nde se Guardan las Observaciones de Aprendizaje

Para mantener sincronizado el aprendizaje entre ambos equipos, el registro central se ubica en:
- `G:\Mi unidad\Antigravity\observations\learnings.md`

Opcionalmente, para proyectos especÃ­ficos con repositorios compartidos, se puede registrar en:
- `.agents/learnings.md` en la raÃ­z del proyecto.

---

## 2. CuÃ¡ndo se Activa la ObservaciÃ³n (SeÃ±ales de Aprendizaje)

El agente detecta automÃ¡ticamente situaciones como:

1. **Correcciones Directas del Usuario:**
   - *"No hagas eso asÃ­, hazlo con X"*, *"Te he dicho que uses Y librerÃ­a"*, *"Nunca importes Z de esa forma"*.
2. **Preferencias Recurrentes:**
   - Estilo de cÃ³digo preferido (ej. funciones flecha vs declarativas, tipos estrictos, uso de interfaces vs types).
   - Estructura de carpetas predilecta (ej. atomic design, feature-first, Clean Architecture).
   - Idioma o tono preferido en commits, comentarios o documentaciÃ³n.
3. **Errores de EjecuciÃ³n Repetidos:**
   - Comandos que fallan en Windows PowerShell por diferencias de sintaxis respecto a bash/linux.
   - Herramientas o scripts que requieran rutas o permisos especiales.

---

## 3. Formato del Registro de Aprendizaje (`learnings.md`)

Cada aprendizaje se documenta de forma concisa y accionable:

```markdown
# Registro de Aprendizaje y Preferencias (Continuous Evolution)
*Ãšltima actualizaciÃ³n: YYYY-MM-DD*

## 1. Preferencias de CÃ³digo y Arquitectura
- **[Estilo/PatrÃ³n]:** DescripciÃ³n clara de cÃ³mo le gusta al usuario que se escriba o estructure.
- **[LibrerÃ­as/Herramientas Favoritas]:** QuÃ© tecnologÃ­as prefiere usar por defecto cuando se le da a elegir.

## 2. Restricciones y Reglas Negativas (Lo que NUNCA hacer)
- **[AntipatrÃ³n evitado]:** QuÃ© error o enfoque rechazÃ³ el usuario previamente y por quÃ©.

## 3. Atajos y Comportamiento del Sistema
- **[Entorno Windows/PowerShell]:** Particularidades del sistema operativo detectadas para evitar fallos de comandos.
- **[Flujo de Trabajo]:** CÃ³mo prefiere recibir las propuestas (directo al cÃ³digo, sin rodeos, con planes breves).
```

---

## 4. EvoluciÃ³n de Skills y Reglas (`/learn`)

Cuando una preferencia o correcciÃ³n se repita mÃ¡s de 2 veces o sea fundamental:
1. El agente propondrÃ¡ al usuario actualizar directamente la skill afectada en `G:\Mi unidad\Antigravity\skills/` o el archivo de reglas global `GEMINI.md`.
2. Si el usuario dice *"Aprende esto"* o utiliza el comando `/learn`, el agente registrarÃ¡ de inmediato el nuevo principio en su memoria permanente.

