---
trigger: model_decision
description: "Ejecuta un anÃ¡lisis de seguridad defensivo, validaciÃ³n de entradas y mitigaciÃ³n de vulnerabilidades OWASP Top 10 al auditar o escribir endpoints y consultas."
---

# Security & OWASP Top 10 Guardian

## 1. MitigaciÃ³n Obligatoria por Defecto
- **InyecciÃ³n SQL (A03:2021):** Prohibido concatenar strings o usar variables directas en queries. Obligatorio usar Prepared Statements, ORMs parametrizados o consultas tipadas de forma segura.
- **Control de Accesos (A01:2021):** Todo endpoint o mÃ©todo pÃºblico de controlador debe validar explÃ­citamente el token de sesiÃ³n, roles y privilegios del usuario (*Principle of Least Privilege*).
- **SanitizaciÃ³n de Entradas (A00):** Nunca confÃ­es en el cliente. Toda entrada de usuario (`DTO`, parÃ¡metros de URL, headers) debe pasar por validadores estrictos antes de procesarse.
- **GestiÃ³n de Secretos:** Cero contraseÃ±as, *tokens* o claves de API *hardcodeadas* en el cÃ³digo fuente. Todo debe leerse obligatoriamente mediante variables de entorno (`.env`).

## 2. Protocolo de AuditorÃ­a de Seguridad
Cuando el usuario pida revisar seguridad, el agente buscarÃ¡ activamente:
1. ExposiciÃ³n de datos sensibles en trazas de error (`StackTrace` impresas al usuario).
2. Uso de algoritmos criptogrÃ¡ficos dÃ©biles (ej. MD5 o SHA-1 para hashes de contraseÃ±as, exigiendo bcrypt o Argon2).

