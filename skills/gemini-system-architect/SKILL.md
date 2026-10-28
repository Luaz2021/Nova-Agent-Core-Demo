---
name: gemini-system-architect
description: "Arquitectura modular y multirepo (DDD, C4 Model, Seam Mapping, Bounded Contexts y control de radio de impacto)."
trigger: model_decision
---

# Scalable System Architecture, Domain Modeling & Multi-Repo Seam Engineering

Esta habilidad guia las decisiones de arquitectura de alto nivel para asegurar que cualquier proyecto nuevo, monolito o ecosistema multirepo pueda escalar sin colapsar ni generar puntos ciegos entre servicios.

---

## 1. Principios de Escalabilidad y Diseno

1. **Modelado de Dominio (Domain-Driven Design - DDD):**
   - **Entidades:** Objetos con identidad unica a lo largo del tiempo.
   - **Value Objects:** Objetos inmutables definidos unicamente por sus atributos (ej. `Money`, `EmailAddress`).
   - **Agregados y Raices de Agregado:** Delimitar limites transaccionales claros para evitar bloqueos masivos en la base de datos.
2. **Desacoplamiento Estricto:**
   - La logica de negocio no debe saber si la peticion vino de una API REST, de un WebSocket, de gRPC o de un comando CLI.
   - Inversion de Dependencias (DIP): Los modulos de alto nivel definen interfaces (puertos) y la infraestructura concreta los implementa (adaptadores).
3. **Resiliencia y Concurrencia:**
   - **Circuit Breaker:** Evitar saturar servicios caidos de terceros (APIs de pago, emails).
   - **Reintentos con Backoff Exponencial:** En operaciones de red o colas de mensajes.
   - **Idempotencia:** Endpoints criticos de cobro o creacion deben soportar reintentos con `Idempotency-Key` sin duplicar transacciones.

---

## 2. Documentacion de Decisiones Arquitectonicas (ADRs)

Cada cambio estructural mayor se documenta en 3 viñetas:
- **Contexto:** Que problema enfrentamos.
- **Decision:** Que patron o tecnologia elegimos y que alternativas descartamos.
- **Consecuencias:** Que ventajas ganamos y que compromisos (trade-offs) asumimos.

---

## 3. Arquitectura Multi-Repo, Mapa Topologico y Costuras (Seam Mapping)

En ecosistemas con multiples repositorios (ej. Frontend Web, App Movil, Backend API, Base de Datos/Auth):

### A. Estandar de Mapa Topologico (`TOPOLOGY.md`)
Todo proyecto multirepo o distribuido debe contar con un mapa ligero de 1 pagina en la raiz del espacio de trabajo documentando:
- **Nodos del Sistema:** Lista de repositorios/servicios, lenguajes, frameworks y puertos locales asignados.
- **Costuras e Interfaces (Seams):** Endpoints REST/GraphQL que conectan cada servicio, metodos de comunicacion (HTTP sincrono, WebSockets o eventos asincronos) y esquemas de payload compartidos (DTOs).
- **Puente de Entorno:** Variables `.env` o tokens de autenticacion que deben mantenerse alineados entre servicios.

### B. Protocolo de Trazabilidad de Costuras en 4 Saltos (`Trace Seam Protocol`)
Ante la aparicion de cualquier bug, fallo 4xx/5xx o comportamiento inesperado en sistemas multicapa, queda terminantemente prohibido modificar codigo a ciegas. Se debe auditar la cadena de ejecucion en 4 saltos estrictos:
1. **Salto 1 (Emisor / Cliente):** Inspeccionar el payload exacto enviado desde el componente UI o cliente HTTP (campos, tipos y cabeceras).
2. **Salto 2 (La Aduana / Contrato de Red):** Validar la coincidencia exacta de la ruta, el metodo HTTP, la configuracion de CORS, los tokens de autenticacion y la validacion de esquema del DTO.
3. **Salto 3 (El Motor / Dominio):** Aislar el Controller que recibe la peticion y el Service que ejecuta la logica de negocio.
4. **Salto 4 (El Suelo / Persistencia):** Verificar la consulta a la base de datos, las politicas RLS (Row Level Security), restricciones de integridad o respuestas de servicios externos.

### C. Puerta del Radio de Impacto (`Blast Radius Gate`)
Antes de modificar cualquier contrato compartido (DTO, firma de endpoint, columna de base de datos o variable de configuracion), el agente debe declarar el inventario de impacto:
- Que archivos y repositorios dependen directamente de ese contrato.
- Que pruebas unitarias o de integracion quedarian afectadas.
- Si requiere migracion hacia adelante sin tiempo de inactividad (expand-contract).
