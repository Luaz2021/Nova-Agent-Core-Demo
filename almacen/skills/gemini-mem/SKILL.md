---
name: gemini-mem
description: "Memoria persistente entre sesiones para consultar decisiones arquitectonicas, errores resueltos y progreso en curso."
trigger: model_decision
---

# Memoria Persistente de Proyectos (Gemini-Mem)

Esta habilidad proporciona continuidad y memoria histórica entre sesiones de trabajo en tus proyectos con Gemini/Antigravity. Permite recordar decisiones técnicas tomadas, soluciones a bugs complejos, arquitectura elegida y el estado pendiente de las tareas sin perder el hilo al cambiar de sesión o de dispositivo (PC / Laptop).

---

## 1. Dónde se Almacena la Memoria

Para garantizar sincronización total entre tu PC y tu Laptop, la memoria opera en dos niveles:

1. **Memoria Local del Workspace / Proyecto**:
   - Archivo: `.agents/memory.md` (o `docs/memory.md`) en la raíz del proyecto activo.
   - Ideal para control de versiones en Git y compartir decisiones con el repositorio.
2. **Memoria Global de Proyectos en la Nube**:
   - Directorio: `<NOVA_HOME>\antigravity\memory\`
   - Archivo por proyecto: `<NOVA_HOME>\antigravity\memory\<nombre-proyecto>.md`
   - Permite consultar el historial de cualquier proyecto incluso antes de abrirlo o clonarlo.

---

## 2. Cuándo Consultar la Memoria (Lectura)

El agente debe revisar activamente el archivo de memoria cuando:
- El usuario pregunte: *"¿Recuerdas qué estábamos haciendo?", "¿Cómo habíamos solucionado el error X?", "¿En qué estado dejamos el proyecto?"*.
- Al iniciar una sesión o tarea de desarrollo en un proyecto existente.
- Antes de tomar decisiones de arquitectura o refactorizaciones mayores.

### Procedimiento de Consulta:
1. Buscar si existe `.agents/memory.md` en el espacio de trabajo.
2. Si no existe en el workspace, consultar en la nube: `<NOVA_HOME>\antigravity\memory\<nombre-proyecto>.md`.
3. Extraer el contexto relevante (decisiones, bugs previos, convenciones y tareas pendientes).

---

## 3. Cuándo y Cómo Actualizar la Memoria (Escritura)

Al concluir un hito importante, corregir un bug complejo o tomar una decisión de arquitectura, el agente debe actualizar la memoria de forma concisa.

### Estructura Estándar de `memory.md`:

```markdown
# Memoria de Proyecto: [Nombre del Proyecto]
*Última actualización: YYYY-MM-DD*

## 1. Visión y Stack Tecnológico
- **Descripción:** Breve resumen de qué hace el proyecto.
- **Stack:** Lenguajes, frameworks, bases de datos y herramientas clave.

## 2. Decisiones Arquitectónicas Clave (ADR)
- **[YYYY-MM-DD] [Título de la decisión]:** Motivo, alternativas descartadas y solución adoptada.

## 3. Registro de Bugs y Soluciones Críticas
- **[YYYY-MM-DD] [Error / Bug]:** Causa raíz identificada y cómo se resolvió para evitar regresiones.

## 4. Estado Actual y Tareas Pendientes
- [x] Tareas completadas recientemente.
- [ ] Tarea pendiente inmediata 1.
- [ ] Tarea pendiente inmediata 2.

## 5. Convenciones y Notas de Aprendizaje
- Particularidades del entorno, comandos comunes o atajos específicos del proyecto.
```

---

## 4. Directrices de Mantenimiento

- **Compresión Semántica:** Mantén las entradas directas y concisas. Evita volcar logs completos; resume la causa y la solución en 2-4 líneas.
- **Deduplicación:** Actualiza las tareas completadas en lugar de añadir entradas repetidas.
- **Sincronización:** Si se realizan modificaciones en la memoria local del proyecto, asegúrate de reflejarlas o advertir al usuario para que ambas máquinas (PC y Laptop) conserven el mismo estado.

