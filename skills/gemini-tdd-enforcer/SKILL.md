---
name: gemini-tdd-enforcer
description: "Desarrollo guiado por pruebas (Ciclo Rojo-Verde-Refactor), patron AAA y piramide Unit/Integration/E2E."
trigger: model_decision
---

# TDD & Testing Engineering Enforcer

Esta habilidad obliga al agente a seguir una disciplina inquebrantable de pruebas para garantizar que el software sea robusto, libre de regresiones y verificado matemáticamente antes de darlo por bueno.

---

## 1. El Ciclo Red-Green-Refactor Obligatorio

1. **FASE 1: ROJO (Red):**
   - Escribir primero el caso de prueba mínimo que capture el requerimiento técnico o el bug a resolver.
   - La prueba debe fallar por el motivo correcto (comprobando que el test no es una tautología vacía).
2. **FASE 2: VERDE (Green):**
   - Escribir la cantidad mínima de código de producción estrictamente necesaria para que la prueba pase.
   - Prohibido adelantarse o implementar características futuras no cubiertas por tests.
3. **FASE 3: REFACTORIZACIÓN (Refactor):**
   - Limpiar el código, eliminar duplicación y optimizar nombres manteniendo siempre todos los tests en verde.

---

## 2. Anatomía de Pruebas: Patrón AAA (Arrange-Act-Assert)

Toda prueba debe estructurarse con claridad meridiana:
```typescript
// Arrange: Preparar el escenario y datos de prueba
const user = createTestUser({ balance: 100 });
const paymentService = new PaymentService(mockPaymentGateway);

// Act: Ejecutar la acción concreta bajo prueba
const result = paymentService.charge(user, 50);

// Assert: Verificar el resultado exacto y los efectos colaterales
expect(result.isSuccess).toBe(true);
expect(user.balance).toBe(50);
```

---

## 3. Principios de Mocks y Dependencias
- **No mockear lo que no te pertenece:** Mockea tus propias interfaces de servicio o repositorios; no mockees llamadas a librerías estándar del lenguaje.
- **Evitar tests frágiles:** Los tests deben validar el **comportamiento y los resultados**, no la implementación interna o si una variable privada se llamó 3 veces.

