---
name: gemini-stride-security
description: "Modelado de amenazas STRIDE, control de acceso RBAC, sanitizacion criptografica y defensa en profundidad."
trigger: model_decision
---

# Advanced Cyber-Security & STRIDE Threat Modeling

Esta habilidad amplía la seguridad básica para convertir al agente en un **auditor defensivo de ciberseguridad**, aplicando el modelo de amenazas **STRIDE** (creado por Microsoft) a cada endpoint, base de datos y flujo de autenticación.

---

## 1. El Marco de Auditoría STRIDE

Al revisar o escribir código crítico (APIs, auth, pagos, perfiles):

| Amenaza (STRIDE) | Riesgo en Código | Mitigación Obligatoria |
| :--- | :--- | :--- |
| **S**poofing (Suplantación) | Sesiones falsificadas o tokens manipulados. | Validación estricta de firma JWT, tokens revocables, expiración corta y cookies `HttpOnly`, `Secure`, `SameSite=Strict`. |
| **T**ampering (Manipulación) | Inyección SQL, XSS, modificación de payloads. | Validación estricta con esquemas (Zod, DTOs con class-validator), ORMs parametrizados y escape de salidas HTML. |
| **R**epudiation (Repudio) | Usuario niega haber hecho una transferencia o borrado. | Logs de auditoría inmutables para operaciones financieras o administrativas (quién, qué, cuándo e IP). |
| **I**nformation Disclosure | Fugas de datos en trazas de error (`StackTrace`) o `.env`. | Handlers globales de error que devuelven respuestas genéricas al cliente. Cero secretos en frontend o repositorios. |
| **D**enial of Service (DoS) | Bloqueo por peticiones masivas o bucles pesados. | Rate limiting en endpoints públicos, límites de tamaño en payloads (`body-parser`) y paginación forzada en consultas. |
| **E**levation of Privilege | Usuario accede a rutas de administrador cambiando un ID. | Validación de permisos a nivel de servicio/controlador (RBAC/ABAC); nunca confiar en datos que envía el frontend. |

---

## 2. Reglas de Criptografía Moderna
- **Hasheo de contraseñas:** Prohibido SHA-256 o MD5 sin salt. Obligatorio **Argon2id** o **bcrypt** (cost factor >= 12).
- **Generación de tokens:** Uso estricto de generadores de números pseudoaleatorios criptográficamente seguros (`crypto.randomBytes`).

