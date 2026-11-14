---
name: gemini-superpowers-engine
description: "Ingenieria metodica: planificacion previa (Grill-Me), subagentes paralelos, TDD estricto y revision de codigo."
trigger: model_decision
---

# Superpowers Engineering Methodology (obra/superpowers)

Esta habilidad integra la metodología completa de **Superpowers** (`obra/superpowers`). En lugar de saltar a escribir código de forma caótica, obliga al agente a comportarse como un ingeniero senior metódico que sigue un ciclo de vida de desarrollo de software estructurado.

---

## 1. Los 5 Pilares de la Metodología Superpowers

### Pilar 1: Planificación Antes de Ejecución (`writing-plans`)
- Ante cualquier tarea medianamente compleja o refactorización, el agente **NUNCA** empieza a modificar código directamente.
- Primero genera un **Plan de Implementación** con pasos numerados, dependencias claras, verificación esperada y análisis de riesgos (KISS & YAGNI estricto).

### Pilar 2: Orquestación de Subagentes (`subagent-driven-development`)
- En tareas grandes o investigaciones profundas, el agente principal actúa como líder técnico y delega subtareas aisladas a subagentes paralelos (mediante `invoke_subagent`).
- El agente principal inspecciona y valida el trabajo de cada subagente antes de fusionar o continuar.

### Pilar 3: Desarrollo Guiado por Pruebas (TDD Riguroso)
- Ciclo Rojo $\rightarrow$ Verde $\rightarrow$ Refactorización.
- Escribir primero el test que falla $\rightarrow$ Escribir el código mínimo para pasarlo $\rightarrow$ Limpiar y refactorizar.

### Pilar 4: Depuración Sistemática (`systematic-debugging`)
- Prohibido adivinar. Cuatro pasos: Reproducción confiable, aislamiento de la causa raíz, parche quirúrgico y verificación.

### Pilar 5: Verificación y Cierre Limpio de Rama (`finishing-development`)
- Antes de dar por finalizada la tarea:
  1. Ejecutar la suite de tests y linters del proyecto.
  2. Verificar que no se hayan dejado archivos temporales o `console.log` sueltos.
  3. Redactar un mensaje de commit claro y estructurado.

---

## 2. Cuándo se Activa

El agente activará esta metodología cuando:
- El usuario diga: *"superpowers"*, *"aplica la metodología superpowers"*, *"haz un plan estructurado"*, *"trabajemos con subagentes"*, *"aplica TDD estricto"*.
- Al enfrentarse a tareas complejas que abarquen múltiples archivos o arquitectura de negocio completa.

