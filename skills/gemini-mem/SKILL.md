---
name: gemini-mem
trigger: model_decision
description: "Sistema de persistencia y memoria continua de proyectos entre sesiones para Gemini y Antigravity. Permite consultar decisiones arquitectÃ³nicas, lecciones aprendidas, correcciones de errores pasados y registrar el progreso y contexto de trabajo continuo."
---

# Memoria Persistente de Proyectos (Gemini-Mem)

Esta habilidad proporciona continuidad y memoria histÃ³rica entre sesiones de trabajo en tus proyectos con Gemini/Antigravity. Permite recordar decisiones tÃ©cnicas tomadas, soluciones a bugs complejos, arquitectura elegida y el estado pendiente de las tareas sin perder el hilo al cambiar de sesiÃ³n o de dispositivo (PC / Laptop).

---

## 1. DÃ³nde se Almacena la Memoria

Para garantizar sincronizaciÃ³n total entre tu PC y tu Laptop, la memoria opera en dos niveles:

1. **Memoria Local del Workspace / Proyecto**:
   - Archivo: `.agents/memory.md` (o `docs/memory.md`) en la raÃ­z del proyecto activo.
   - Ideal para control de versiones en Git y compartir decisiones con el repositorio.
2. **Memoria Global de Proyectos en la Nube**:
   - Directorio: `G:\Mi unidad\Antigravity\memory\`
   - Archivo por proyecto: `G:\Mi unidad\Antigravity\memory\<nombre-proyecto>.md`
   - Permite consultar el historial de cualquier proyecto incluso antes de abrirlo o clonarlo.

---

## 2. CuÃ¡ndo Consultar la Memoria (Lectura)

El agente debe revisar activamente el archivo de memoria cuando:
- El usuario pregunte: *"Â¿Recuerdas quÃ© estÃ¡bamos haciendo?", "Â¿CÃ³mo habÃ­amos solucionado el error X?", "Â¿En quÃ© estado dejamos el proyecto?"*.
- Al iniciar una sesiÃ³n o tarea de desarrollo en un proyecto existente.
- Antes de tomar decisiones de arquitectura o refactorizaciones mayores.

### Procedimiento de Consulta:
1. Buscar si existe `.agents/memory.md` en el espacio de trabajo.
2. Si no existe en el workspace, consultar en la nube: `G:\Mi unidad\Antigravity\memory\<nombre-proyecto>.md`.
3. Extraer el contexto relevante (decisiones, bugs previos, convenciones y tareas pendientes).

---

## 3. CuÃ¡ndo y CÃ³mo Actualizar la Memoria (Escritura)

Al concluir un hito importante, corregir un bug complejo o tomar una decisiÃ³n de arquitectura, el agente debe actualizar la memoria de forma concisa.

### Estructura EstÃ¡ndar de `memory.md`:

```markdown
# Memoria de Proyecto: [Nombre del Proyecto]
*Ãšltima actualizaciÃ³n: YYYY-MM-DD*

## 1. VisiÃ³n y Stack TecnolÃ³gico
- **DescripciÃ³n:** Breve resumen de quÃ© hace el proyecto.
- **Stack:** Lenguajes, frameworks, bases de datos y herramientas clave.

## 2. Decisiones ArquitectÃ³nicas Clave (ADR)
- **[YYYY-MM-DD] [TÃ­tulo de la decisiÃ³n]:** Motivo, alternativas descartadas y soluciÃ³n adoptada.

## 3. Registro de Bugs y Soluciones CrÃ­ticas
- **[YYYY-MM-DD] [Error / Bug]:** Causa raÃ­z identificada y cÃ³mo se resolviÃ³ para evitar regresiones.

## 4. Estado Actual y Tareas Pendientes
- [x] Tareas completadas recientemente.
- [ ] Tarea pendiente inmediata 1.
- [ ] Tarea pendiente inmediata 2.

## 5. Convenciones y Notas de Aprendizaje
- Particularidades del entorno, comandos comunes o atajos especÃ­ficos del proyecto.
```

---

## 4. Directrices de Mantenimiento

- **CompresiÃ³n SemÃ¡ntica:** MantÃ©n las entradas directas y concisas. Evita volcar logs completos; resume la causa y la soluciÃ³n en 2-4 lÃ­neas.
- **DeduplicaciÃ³n:** Actualiza las tareas completadas en lugar de aÃ±adir entradas repetidas.
- **SincronizaciÃ³n:** Si se realizan modificaciones en la memoria local del proyecto, asegÃºrate de reflejarlas o advertir al usuario para que ambas mÃ¡quinas (PC y Laptop) conserven el mismo estado.

