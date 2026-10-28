---
name: gemini-superpowers-engine
description: "Ingenieria metodica: planificacion previa (Grill-Me), subagentes paralelos, TDD estricto y revision de codigo."
trigger: model_decision
---

# Superpowers Engineering Methodology (obra/superpowers)

Esta habilidad integra la metodologÃ­a completa de **Superpowers** (`obra/superpowers`). En lugar de saltar a escribir cÃ³digo de forma caÃ³tica, obliga al agente a comportarse como un ingeniero senior metÃ³dico que sigue un ciclo de vida de desarrollo de software estructurado.

---

## 1. Los 5 Pilares de la MetodologÃ­a Superpowers

### Pilar 1: PlanificaciÃ³n Antes de EjecuciÃ³n (`writing-plans`)
- Ante cualquier tarea medianamente compleja o refactorizaciÃ³n, el agente **NUNCA** empieza a modificar cÃ³digo directamente.
- Primero genera un **Plan de ImplementaciÃ³n** con pasos numerados, dependencias claras, verificaciÃ³n esperada y anÃ¡lisis de riesgos (KISS & YAGNI estricto).

### Pilar 2: OrquestaciÃ³n de Subagentes (`subagent-driven-development`)
- En tareas grandes o investigaciones profundas, el agente principal actÃºa como lÃ­der tÃ©cnico y delega subtareas aisladas a subagentes paralelos (mediante `invoke_subagent`).
- El agente principal inspecciona y valida el trabajo de cada subagente antes de fusionar o continuar.

### Pilar 3: Desarrollo Guiado por Pruebas (TDD Riguroso)
- Ciclo Rojo $\rightarrow$ Verde $\rightarrow$ RefactorizaciÃ³n.
- Escribir primero el test que falla $\rightarrow$ Escribir el cÃ³digo mÃ­nimo para pasarlo $\rightarrow$ Limpiar y refactorizar.

### Pilar 4: DepuraciÃ³n SistemÃ¡tica (`systematic-debugging`)
- Prohibido adivinar. Cuatro pasos: ReproducciÃ³n confiable, aislamiento de la causa raÃ­z, parche quirÃºrgico y verificaciÃ³n.

### Pilar 5: VerificaciÃ³n y Cierre Limpio de Rama (`finishing-development`)
- Antes de dar por finalizada la tarea:
  1. Ejecutar la suite de tests y linters del proyecto.
  2. Verificar que no se hayan dejado archivos temporales o `console.log` sueltos.
  3. Redactar un mensaje de commit claro y estructurado.

---

## 2. CuÃ¡ndo se Activa

El agente activarÃ¡ esta metodologÃ­a cuando:
- El usuario diga: *"superpowers"*, *"aplica la metodologÃ­a superpowers"*, *"haz un plan estructurado"*, *"trabajemos con subagentes"*, *"aplica TDD estricto"*.
- Al enfrentarse a tareas complejas que abarquen mÃºltiples archivos o arquitectura de negocio completa.

