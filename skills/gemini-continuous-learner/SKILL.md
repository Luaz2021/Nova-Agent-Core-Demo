---
name: gemini-continuous-learner
description: "Auto-aprendizaje de patrones de trabajo y correcciones del usuario para actualizar reglas y evitar repetir errores."
trigger: model_decision
---

# Self-Learning Observer (One Skill to Rule Them All)

Esta meta-habilidad permite que el asistente **aprenda de tus correcciones, de tus preferencias habituales y de las fricciones de trabajo** a lo largo del tiempo. Su objetivo es convertir cada corrección que hagas en una regla persistente para no cometer el mismo error dos veces y adaptarse a tu estilo de programación entre tu PC y tu Laptop.

---

## 1. Dónde se Guardan las Observaciones de Aprendizaje

Para mantener sincronizado el aprendizaje entre ambos equipos, el registro central se ubica en:
- `<NOVA_HOME>\antigravity\memory\inbox_lecciones.md`

Opcionalmente, para proyectos específicos con repositorios compartidos, se puede registrar en:
- `.agents/learnings.md` en la raíz del proyecto.

---

## 2. Cuándo se Activa la Observación (Señales de Aprendizaje)

El agente detecta automáticamente situaciones como:

1. **Correcciones Directas del Usuario:**
   - *"No hagas eso así, hazlo con X"*, *"Te he dicho que uses Y librería"*, *"Nunca importes Z de esa forma"*.
2. **Preferencias Recurrentes:**
   - Estilo de código preferido (ej. funciones flecha vs declarativas, tipos estrictos, uso de interfaces vs types).
   - Estructura de carpetas predilecta (ej. atomic design, feature-first, Clean Architecture).
   - Idioma o tono preferido en commits, comentarios o documentación.
3. **Errores de Ejecución Repetidos:**
   - Comandos que fallan en Windows PowerShell por diferencias de sintaxis respecto a bash/linux.
   - Herramientas o scripts que requieran rutas o permisos especiales.

---

## 3. Formato del Registro de Aprendizaje (`learnings.md`)

Cada aprendizaje se documenta de forma concisa y accionable:

```markdown
# Registro de Aprendizaje y Preferencias (Continuous Evolution)
*Última actualización: YYYY-MM-DD*

## 1. Preferencias de Código y Arquitectura
- **[Estilo/Patrón]:** Descripción clara de cómo le gusta al usuario que se escriba o estructure.
- **[Librerías/Herramientas Favoritas]:** Qué tecnologías prefiere usar por defecto cuando se le da a elegir.

## 2. Restricciones y Reglas Negativas (Lo que NUNCA hacer)
- **[Antipatrón evitado]:** Qué error o enfoque rechazó el usuario previamente y por qué.

## 3. Atajos y Comportamiento del Sistema
- **[Entorno Windows/PowerShell]:** Particularidades del sistema operativo detectadas para evitar fallos de comandos.
- **[Flujo de Trabajo]:** Cómo prefiere recibir las propuestas (directo al código, sin rodeos, con planes breves).
```

---

## 4. Evolución de Skills y Reglas (`/learn`)

Cuando una preferencia o corrección se repita más de 2 veces o sea fundamental:
1. El agente propondrá al usuario actualizar directamente la skill afectada en `<NOVA_HOME>ntigravitylmacen\skills\` o el archivo de reglas global `GEMINI.md`.
2. Si el usuario dice *"Aprende esto"* o utiliza el comando `/learn`, el agente registrará de inmediato el nuevo principio en su memoria permanente.

