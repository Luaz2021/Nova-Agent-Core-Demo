---
name: gemini-systematic-debugger
description: "Depuracion rigurosa sin parches a ciegas: aislamiento de causa raiz, lectura de logs y test reproducible."
trigger: model_decision
---

# Systematic Debugging & Root Cause Analysis

Esta habilidad proviene de la metodología oficial de **Superpowers** (`obra/superpowers`). Su objetivo es erradicar la "programación por coincidencia" o adivinar soluciones cuando algo falla, aplicando un método científico riguroso de 4 pasos.

---

## 1. Regla de Oro: Prohibido Adivinar
- Nunca cambies código al azar *"a ver si con esto funciona"*.
- Si un bug aparece, primero se demuestra y reproduce la causa raíz; luego se escribe el parche quirúrgico.

---

## 2. El Ciclo Científico de Depuración (4 Pasos)

1. **Paso 1: Reproducción Confiable:**
   - Identificar los datos de entrada exactos o la secuencia de pasos que disparan el fallo.
   - Si es posible, escribir un test unitario mínimo que reproduzca el fallo (test en rojo).
2. **Paso 2: Aislamiento de la Causa Raíz:**
   - No confundir el *síntoma* con la *causa*.
   - Rastrear el flujo de datos hacia atrás: inspeccionar el punto exacto donde la variable o el estado toma un valor incorrecto o nulo.
3. **Paso 3: Parche Quirúrgico Mínimo:**
   - Aplicar la corrección más pequeña y limpia posible que solucione la causa raíz sin alterar comportamiento colateral no relacionado.
4. **Paso 4: Verificación y Prevención de Regresiones:**
   - Ejecutar la prueba: verificar que el test ahora pasa en verde.
   - Si fue un bug complejo o recurrente, registrar la lección en `napkin` para evitar cometerlo de nuevo.

