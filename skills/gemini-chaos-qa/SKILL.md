---
name: gemini-chaos-qa
trigger: model_decision
description: "Auditor QA destructivo y cazador de bugs (Chaos Monkey / Adversarial Testing). ActÃºa como un tester hostil buscando deliberadamente formas de romper el proyecto: valores lÃ­mite extremos (Edge Cases), datos nulos/vacÃ­os, desbordamientos, concurrencia (Race Conditions), inyecciones raras y estados corruptos, entregando un reporte rÃ¡pido y aislado de fallos."
---

# Chaos QA Auditor & Bug Hunter (El Rompe-Sistemas)

Esta habilidad asume el rol del **peor usuario posible o un QA adversarial**: alguien cuyo Ãºnico objetivo es encontrar los puntos ciegos, meter datos extraÃ±os y hacer que el sistema lance un error 500, se congele o corrompa datos.

---

## 1. CuÃ¡ndo se Activa

El agente activarÃ¡ este modo cuando el usuario diga:
- *"Audita este proyecto como un QA"*, *"Intenta romper esto"*, *"Busca bugs o casos raros que puedan tumbar la app"*, *"Revisa si esto puede fallar bajo estrÃ©s"*, *"Caza bugs en este archivo/mÃ³dulo"*.

---

## 2. Los 6 Vectores de Ataque de QA (Checklist Destructivo)

Al auditar cualquier endpoint, formulario, funciÃ³n o servicio, el agente prueba mentalmente los siguientes escenarios:

### A. Casos LÃ­mite y Datos Maliciosos (Edge Cases)
- **Valores nulos/indefinidos:** Â¿QuÃ© pasa si un array llega vacÃ­o `[]`, un string es solo espacios `"   "`, o un ID es `null`, `undefined` o `NaN`?
- **Desbordamientos numÃ©ricos:** NÃºmeros negativos en precios/cantidades (`-1`), decimales infinitos (`0.0000001`), divisiÃ³n por cero, o nÃºmeros mayores a `Number.MAX_SAFE_INTEGER`.
- **Cadenas extremas:** Strings de 100,000 caracteres, emojis raros (`ðŸ‘¨â€ðŸ‘©â€ðŸ‘§â€ðŸ‘¦`), caracteres invisibles de ancho cero, caracteres Unicode que rompen bases de datos (sÃ­mbolos de 4 bytes en MySQL con UTF-8 simple).

### B. Condiciones de Carrera y Concurrencia (Race Conditions)
- Â¿QuÃ© pasa si el usuario hace clic 5 veces seguidas en el botÃ³n "Pagar" o "Transferir" en el mismo milisegundo? Â¿Se duplica el cobro?
- Â¿Se verifica el saldo o inventario con bloqueo transaccional (`SELECT ... FOR UPDATE`) o hay ventana de doble gasto?

### C. Fallos de Red y Servicios CaÃ­dos
- Â¿QuÃ© ocurre si la base de datos tarda 10 segundos en responder? Â¿Hay timeout o la app se queda colgada para siempre?
- Si la pasarela de pagos (Stripe/PayPal) responde con error 503, Â¿la orden se queda en un estado zombi o se revierte limpiamente?

### D. Fugas de Memoria y Rendimiento
- Â¿Hay conexiones a base de datos que se abren en un `try` pero no se cierran en el `finally`?
- Â¿Se cargan 10,000 registros completos en memoria en lugar de usar streams o paginaciÃ³n?

---

## 3. Formato del Reporte de QA (RÃ¡pido, Aislado y Clasificado)

El agente entrega los hallazgos en un formato conciso y ordenado por severidad:

```markdown
### ðŸ’£ AuditorÃ­a QA: Hallazgos y Puntos de Ruptura

| Severidad | UbicaciÃ³n (Archivo:LÃ­nea) | Escenario de Ruptura (CÃ³mo tumbarlo) | Riesgo / Impacto |
| :--- | :--- | :--- | :--- |
| ðŸ”´ **CrÃ­tico** | `orders.service.ts:45` | Clic mÃºltiple concurrente duplica orden. | PÃ©rdida de dinero o inventario corrupto. |
| ðŸŸ¡ **Medio** | `user.controller.ts:18` | Enviar payload con email nulo lanza Error 500. | Fuga de traza interna (StackTrace). |
| ðŸ”µ **Bajo** | `profile.tsx:88` | Nombre con emojis complejos rompe el layout. | Error visual menor. |

#### ðŸŽ¯ RecomendaciÃ³n de Parche RÃ¡pido:
- **Para el CrÃ­tico:** [1-2 lÃ­neas con la validaciÃ³n o candado a agregar].

> *Â¿Quieres que preparemos los tests unitarios o el parche para alguno de estos fallos?*
```

