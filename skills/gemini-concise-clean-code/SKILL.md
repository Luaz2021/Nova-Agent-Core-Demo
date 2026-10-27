---
name: gemini-concise-clean-code
trigger: always_on
description: "FilosofÃ­a estricta de cÃ³digo corto, directo, auto-documentado y libre de sobre-ingenierÃ­a (KISS, YAGNI, Early Returns). Genera la menor cantidad de lÃ­neas posibles para resolver el problema, con nombres altamente expresivos que se explican solos a la primera lectura."
---

# Concise Clean Code & Zero-Bloat Standards

Esta habilidad impone una directriz fundamental: **el mejor cÃ³digo es el mÃ¡s corto, claro y fÃ¡cil de entender por cualquier programador a la primera**. Elimina clases innecesarias, capas intermedias vacÃ­as y anidamientos excesivos.

---

## 1. Principios Clave

1. **KISS & YAGNI:** *"Keep It Simple, Stupid"* y *"You Aren't Gonna Need It"*. 
   - No crees fÃ¡bricas, abstracciones ni interfaces genÃ©ricas "por si acaso en el futuro las usamos". 
   - Resuelve el problema actual con la soluciÃ³n mÃ¡s limpia y directa.
2. **Funciones Cortas y de Responsabilidad Ãšnica:** 
   - Longitud objetivo: 10 a 25 lÃ­neas. Si una funciÃ³n hace dos cosas, se divide.
3. **Guard Clauses / Early Returns (Cero PirÃ¡mides):**
   - Elimina la anidaciÃ³n profunda de `if / else`.
   - Valida condiciones de error al principio y retorna inmediatamente:
   ```typescript
   // âŒ MAL: AnidaciÃ³n profunda
   if (user) {
     if (user.isActive) {
       return processPayment(user);
     }
   }
   return null;

   // âœ… BIEN: Early return
   if (!user || !user.isActive) return null;
   return processPayment(user);
   ```

---

## 2. Nombres Expresivos vs Comentarios Relleno

- **Nombres Auto-Explicativos:** El nombre de la funciÃ³n y las variables debe revelar su intenciÃ³n sin necesidad de comentarios obvios:
  - âŒ `const d = 86400; // segundos en un dÃ­a`
  - âœ… `const SECONDS_PER_DAY = 86400;`
- **Comentarios del "POR QUÃ‰", no del "QUÃ‰":**
  - No comentes lo que el cÃ³digo ya dice a simple vista.
  - Comenta Ãºnicamente **decisiones de negocio no obvias o limitaciones tÃ©cnicas** de terceros (ej. *"// La API de pagos exige montos en centavos"*).

---

## 3. Inmutabilidad y Funciones Puras
- Preferir mÃ©todos inmutables y transformaciones limpias (`map`, `filter`, `find`) en lugar de mutar arrays o variables externas en bucles tradicionales `for`.
- Reducir el estado mutable al mÃ­nimo absoluto.

