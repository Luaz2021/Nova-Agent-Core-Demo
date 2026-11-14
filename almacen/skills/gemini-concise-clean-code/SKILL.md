---
name: gemini-concise-clean-code
description: "Codigo corto, directo y auto-documentado (KISS, YAGNI, Early Returns) con el minimo de lineas y maxima legibilidad."
trigger: always_on
---

# Concise Clean Code & Zero-Bloat Standards

Esta habilidad impone una directriz fundamental: **el mejor código es el más corto, claro y fácil de entender por cualquier programador a la primera**. Elimina clases innecesarias, capas intermedias vacías y anidamientos excesivos.

---

## 1. Principios Clave

1. **KISS & YAGNI:** *"Keep It Simple, Stupid"* y *"You Aren't Gonna Need It"*. 
   - No crees fábricas, abstracciones ni interfaces genéricas "por si acaso en el futuro las usamos". 
   - Resuelve el problema actual con la solución más limpia y directa.
2. **Funciones Cortas y de Responsabilidad Única:** 
   - Longitud objetivo: 10 a 25 líneas. Si una función hace dos cosas, se divide.
3. **Guard Clauses / Early Returns (Cero Pirámides):**
   - Elimina la anidación profunda de `if / else`.
   - Valida condiciones de error al principio y retorna inmediatamente:
   ```typescript
   // ❌ MAL: Anidación profunda
   if (user) {
     if (user.isActive) {
       return processPayment(user);
     }
   }
   return null;

   // ✅ BIEN: Early return
   if (!user || !user.isActive) return null;
   return processPayment(user);
   ```

---

## 2. Nombres Expresivos vs Comentarios Relleno

- **Nombres Auto-Explicativos:** El nombre de la función y las variables debe revelar su intención sin necesidad de comentarios obvios:
  - ❌ `const d = 86400; // segundos en un día`
  - ✅ `const SECONDS_PER_DAY = 86400;`
- **Comentarios del "POR QUÉ", no del "QUÉ":**
  - No comentes lo que el código ya dice a simple vista.
  - Comenta únicamente **decisiones de negocio no obvias o limitaciones técnicas** de terceros (ej. *"// La API de pagos exige montos en centavos"*).

---

## 3. Inmutabilidad y Funciones Puras
- Preferir métodos inmutables y transformaciones limpias (`map`, `filter`, `find`) en lugar de mutar arrays o variables externas en bucles tradicionales `for`.
- Reducir el estado mutable al mínimo absoluto.

