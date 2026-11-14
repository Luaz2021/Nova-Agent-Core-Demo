---
name: gemini-owasp-sentinel
description: "Ejecuta un análisis de seguridad defensivo, validación de entradas y mitigación de vulnerabilidades OWASP Top 10 al auditar o escrib"
trigger: model_decision
---

# Security & OWASP Top 10 Guardian

## 1. Mitigación Obligatoria por Defecto
- **Inyección SQL (A03:2021):** Prohibido concatenar strings o usar variables directas en queries. Obligatorio usar Prepared Statements, ORMs parametrizados o consultas tipadas de forma segura.
- **Control de Accesos (A01:2021):** Todo endpoint o método público de controlador debe validar explícitamente el token de sesión, roles y privilegios del usuario (*Principle of Least Privilege*).
- **Sanitización de Entradas (A00):** Nunca confíes en el cliente. Toda entrada de usuario (`DTO`, parámetros de URL, headers) debe pasar por validadores estrictos antes de procesarse.
- **Gestión de Secretos:** Cero contraseñas, *tokens* o claves de API *hardcodeadas* en el código fuente. Todo debe leerse obligatoriamente mediante variables de entorno (`.env`).

## 2. Protocolo de Auditoría de Seguridad
Cuando el usuario pida revisar seguridad, el agente buscará activamente:
1. Exposición de datos sensibles en trazas de error (`StackTrace` impresas al usuario).
2. Uso de algoritmos criptográficos débiles (ej. MD5 o SHA-1 para hashes de contraseñas, exigiendo bcrypt o Argon2).
