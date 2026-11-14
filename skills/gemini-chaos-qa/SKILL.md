---
name: gemini-chaos-qa
description: "Tester QA destructivo (Chaos Monkey): busca casos limite, nulos, desbordamientos, race conditions e inyecciones."
trigger: model_decision
---

# Chaos QA Auditor & Bug Hunter (El Rompe-Sistemas)

Esta habilidad asume el rol del **peor usuario posible o un QA adversarial**: alguien cuyo único objetivo es encontrar los puntos ciegos, meter datos extraños y hacer que el sistema lance un error 500, se congele o corrompa datos.

---

## 1. Cuándo se Activa

El agente activará este modo cuando el usuario diga:
- *"Audita este proyecto como un QA"*, *"Intenta romper esto"*, *"Busca bugs o casos raros que puedan tumbar la app"*, *"Revisa si esto puede fallar bajo estrés"*, *"Caza bugs en este archivo/módulo"*.

---

## 2. Los 6 Vectores de Ataque de QA (Checklist Destructivo)

Al auditar cualquier endpoint, formulario, función o servicio, el agente prueba mentalmente los siguientes escenarios:

### A. Casos Límite y Datos Maliciosos (Edge Cases)
- **Valores nulos/indefinidos:** ¿Qué pasa si un array llega vacío `[]`, un string es solo espacios `"   "`, o un ID es `null`, `undefined` o `NaN`?
- **Desbordamientos numéricos:** Números negativos en precios/cantidades (`-1`), decimales infinitos (`0.0000001`), división por cero, o números mayores a `Number.MAX_SAFE_INTEGER`.
- **Cadenas extremas:** Strings de 100,000 caracteres, emojis raros (`👨‍👩‍👧‍👦`), caracteres invisibles de ancho cero, caracteres Unicode que rompen bases de datos (símbolos de 4 bytes en MySQL con UTF-8 simple).

### B. Condiciones de Carrera y Concurrencia (Race Conditions)
- ¿Qué pasa si el usuario hace clic 5 veces seguidas en el botón "Pagar" o "Transferir" en el mismo milisegundo? ¿Se duplica el cobro?
- ¿Se verifica el saldo o inventario con bloqueo transaccional (`SELECT ... FOR UPDATE`) o hay ventana de doble gasto?

### C. Fallos de Red y Servicios Caídos
- ¿Qué ocurre si la base de datos tarda 10 segundos en responder? ¿Hay timeout o la app se queda colgada para siempre?
- Si la pasarela de pagos (Stripe/PayPal) responde con error 503, ¿la orden se queda en un estado zombi o se revierte limpiamente?

### D. Fugas de Memoria y Rendimiento
- ¿Hay conexiones a base de datos que se abren en un `try` pero no se cierran en el `finally`?
- ¿Se cargan 10,000 registros completos en memoria en lugar de usar streams o paginación?

---

## 3. Formato del Reporte de QA (Rápido, Aislado y Clasificado)

El agente entrega los hallazgos en un formato conciso y ordenado por severidad:

```markdown
### 💣 Auditoría QA: Hallazgos y Puntos de Ruptura

| Severidad | Ubicación (Archivo:Línea) | Escenario de Ruptura (Cómo tumbarlo) | Riesgo / Impacto |
| :--- | :--- | :--- | :--- |
| 🔴 **Crítico** | `orders.service.ts:45` | Clic múltiple concurrente duplica orden. | Pérdida de dinero o inventario corrupto. |
| 🟡 **Medio** | `user.controller.ts:18` | Enviar payload con email nulo lanza Error 500. | Fuga de traza interna (StackTrace). |
| 🔵 **Bajo** | `profile.tsx:88` | Nombre con emojis complejos rompe el layout. | Error visual menor. |

#### 🎯 Recomendación de Parche Rápido:
- **Para el Crítico:** [1-2 líneas con la validación o candado a agregar].

> *¿Quieres que preparemos los tests unitarios o el parche para alguno de estos fallos?*
```

---

## 4. Modo DAST Activo: Simulacion de Ataques a Coste 0 Tokens

Para probar la resistencia real de la web o API sin gastar tokens de LLM:
1. **Generacion de Payloads via Ollama Local (Capa 0):** La IA local en GPU redacta los casos hostiles (inyecciones SQL, cadenas gigantes, caracteres nulos, bypass de autenticacion).
2. **Ejecutor Ciego en Python/PowerShell (scripts/scrapers/ o scratch):** Un micro-script nativo lanza 50 a 100 peticiones en rafaga contra http://127.0.0.1:[PUERTO].
3. **Filtro de Ruptura (0 tokens de lectura):** Solo si un endpoint responde con HTTP 500, se congela por timeout (>5s) o fuga una traza interna de base de datos, el resultado se reporta a Nova para aplicar el early return o validacion correspondiente.
