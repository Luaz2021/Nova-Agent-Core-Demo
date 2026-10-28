---
name: gemini-stride-security
description: "Modelado de amenazas STRIDE, control de acceso RBAC, sanitizacion criptografica y defensa en profundidad."
trigger: model_decision
---

# Advanced Cyber-Security & STRIDE Threat Modeling

Esta habilidad amplÃ­a la seguridad bÃ¡sica para convertir al agente en un **auditor defensivo de ciberseguridad**, aplicando el modelo de amenazas **STRIDE** (creado por Microsoft) a cada endpoint, base de datos y flujo de autenticaciÃ³n.

---

## 1. El Marco de AuditorÃ­a STRIDE

Al revisar o escribir cÃ³digo crÃ­tico (APIs, auth, pagos, perfiles):

| Amenaza (STRIDE) | Riesgo en CÃ³digo | MitigaciÃ³n Obligatoria |
| :--- | :--- | :--- |
| **S**poofing (SuplantaciÃ³n) | Sesiones falsificadas o tokens manipulados. | ValidaciÃ³n estricta de firma JWT, tokens revocables, expiraciÃ³n corta y cookies `HttpOnly`, `Secure`, `SameSite=Strict`. |
| **T**ampering (ManipulaciÃ³n) | InyecciÃ³n SQL, XSS, modificaciÃ³n de payloads. | ValidaciÃ³n estricta con esquemas (Zod, DTOs con class-validator), ORMs parametrizados y escape de salidas HTML. |
| **R**epudiation (Repudio) | Usuario niega haber hecho una transferencia o borrado. | Logs de auditorÃ­a inmutables para operaciones financieras o administrativas (quiÃ©n, quÃ©, cuÃ¡ndo e IP). |
| **I**nformation Disclosure | Fugas de datos en trazas de error (`StackTrace`) o `.env`. | Handlers globales de error que devuelven respuestas genÃ©ricas al cliente. Cero secretos en frontend o repositorios. |
| **D**enial of Service (DoS) | Bloqueo por peticiones masivas o bucles pesados. | Rate limiting en endpoints pÃºblicos, lÃ­mites de tamaÃ±o en payloads (`body-parser`) y paginaciÃ³n forzada en consultas. |
| **E**levation of Privilege | Usuario accede a rutas de administrador cambiando un ID. | ValidaciÃ³n de permisos a nivel de servicio/controlador (RBAC/ABAC); nunca confiar en datos que envÃ­a el frontend. |

---

## 2. Reglas de CriptografÃ­a Moderna
- **Hasheo de contraseÃ±as:** Prohibido SHA-256 o MD5 sin salt. Obligatorio **Argon2id** o **bcrypt** (cost factor >= 12).
- **GeneraciÃ³n de tokens:** Uso estricto de generadores de nÃºmeros pseudoaleatorios criptogrÃ¡ficamente seguros (`crypto.randomBytes`).

