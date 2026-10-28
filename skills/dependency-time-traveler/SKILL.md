---
name: dependency-time-traveler
description: "Inspecciona .d.ts y package.json en node_modules antes de picar codigo para evitar metodos deprecados o inventados."
---

# Dependency Time Traveler (Source-Driven Truth)

## Propósito
Los modelos de lenguaje tienden a mezclar versiones de APIs por su entrenamiento (ej. mezclar Next.js 13 con 15, o Tailwind v3 con v4). Esta habilidad impone la lectura directa del código fuente y tipos locales antes de implementar componentes o lógica crítica.

## Flujo de Inspección Obligatorio
1. **Detección de Versión:**
   - Consultar `package.json` en la raíz del proyecto para conocer la versión exacta instalada.
2. **Inspección de Tipos (.d.ts):**
   - Si se desconoce una firma de método, props de componente o configuración, inspeccionar la definición de tipos dentro de `node_modules/<libreria>/.../*.d.ts`.
   - Prohibido adivinar props o flags que no figuren en los tipos locales.
3. **Validación de Deprecaciones:**
   - Si un método arroja advertencia de deprecado en TypeScript o consola, buscar la alternativa exportada en el mismo módulo (`[Do Instead]`).
