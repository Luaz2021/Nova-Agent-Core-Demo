---
name: gemini-systematic-debugger
trigger: model_decision
description: "MetodologÃ­a rigurosa de depuraciÃ³n y resoluciÃ³n de errores (inspirada en Superpowers de Jesse Vincent). ProhÃ­be adivinar o aplicar parches a ciegas. Exige aislar la causa raÃ­z con hipÃ³tesis reproducibles, inspecciÃ³n de logs exactos y verificaciÃ³n con tests antes de dar por resuelto un bug."
---

# Systematic Debugging & Root Cause Analysis

Esta habilidad proviene de la metodologÃ­a oficial de **Superpowers** (`obra/superpowers`). Su objetivo es erradicar la "programaciÃ³n por coincidencia" o adivinar soluciones cuando algo falla, aplicando un mÃ©todo cientÃ­fico riguroso de 4 pasos.

---

## 1. Regla de Oro: Prohibido Adivinar
- Nunca cambies cÃ³digo al azar *"a ver si con esto funciona"*.
- Si un bug aparece, primero se demuestra y reproduce la causa raÃ­z; luego se escribe el parche quirÃºrgico.

---

## 2. El Ciclo CientÃ­fico de DepuraciÃ³n (4 Pasos)

1. **Paso 1: ReproducciÃ³n Confiable:**
   - Identificar los datos de entrada exactos o la secuencia de pasos que disparan el fallo.
   - Si es posible, escribir un test unitario mÃ­nimo que reproduzca el fallo (test en rojo).
2. **Paso 2: Aislamiento de la Causa RaÃ­z:**
   - No confundir el *sÃ­ntoma* con la *causa*.
   - Rastrear el flujo de datos hacia atrÃ¡s: inspeccionar el punto exacto donde la variable o el estado toma un valor incorrecto o nulo.
3. **Paso 3: Parche QuirÃºrgico MÃ­nimo:**
   - Aplicar la correcciÃ³n mÃ¡s pequeÃ±a y limpia posible que solucione la causa raÃ­z sin alterar comportamiento colateral no relacionado.
4. **Paso 4: VerificaciÃ³n y PrevenciÃ³n de Regresiones:**
   - Ejecutar la prueba: verificar que el test ahora pasa en verde.
   - Si fue un bug complejo o recurrente, registrar la lecciÃ³n en `napkin` para evitar cometerlo de nuevo.

