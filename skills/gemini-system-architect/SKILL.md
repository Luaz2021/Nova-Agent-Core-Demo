---
name: gemini-system-architect
trigger: model_decision
description: "Arquitectura de software escalable, modular y orientada a dominios (Domain-Driven Design / C4 Model). Define lÃ­mites de contexto (Bounded Contexts), desacoplamiento mediante eventos o interfaces, gestiÃ³n de estado distribuido y resiliencia para aplicaciones que crecen sin convertirse en monolitos inmanejables."
---

# Scalable System Architecture & Domain Modeling

Esta habilidad guÃ­a las decisiones de arquitectura de alto nivel para asegurar que cualquier proyecto nuevo o refactorizado pueda escalar a miles de usuarios sin colapsar ni requerir reescrituras completas.

---

## 1. Principios de Escalabilidad y DiseÃ±o

1. **Modelado de Dominio (Domain-Driven Design - DDD):**
   - **Entidades:** Objetos con identidad Ãºnica a lo largo del tiempo.
   - **Value Objects:** Objetos inmutables definidos Ãºnicamente por sus atributos (ej. `Money`, `EmailAddress`).
   - **Agregados y RaÃ­ces de Agregado:** Delimitar lÃ­mites transaccionales claros para evitar bloqueos masivos en la base de datos.
2. **Desacoplamiento Estricto:**
   - La lÃ³gica de negocio no debe saber si la peticiÃ³n vino de una API REST, de un WebSocket, de gRPC o de un comando CLI.
   - InversiÃ³n de Dependencias (DIP): Los mÃ³dulos de alto nivel definen interfaces (puertos) y la infraestructura concreta los implementa (adaptadores).
3. **Resiliencia y Concurrencia:**
   - **Circuit Breaker:** Evitar saturar servicios caÃ­dos de terceros (APIs de pago, emails).
   - **Reintentos con Backoff Exponencial:** En operaciones de red o colas de mensajes.
   - **Idempotencia:** Endpoints crÃ­ticos de cobro o creaciÃ³n deben soportar reintentos con `Idempotency-Key` sin duplicar transacciones.

---

## 2. DocumentaciÃ³n de Decisiones ArquitectÃ³nicas (ADRs)
Cada cambio estructural mayor se documenta en 3 viÃ±etas:
- **Contexto:** QuÃ© problema enfrentamos.
- **DecisiÃ³n:** QuÃ© patrÃ³n o tecnologÃ­a elegimos y quÃ© alternativas descartamos.
- **Consecuencias:** QuÃ© ventajas ganamos y quÃ© compromisos (trade-offs) asumimos.

