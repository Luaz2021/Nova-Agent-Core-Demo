---
name: gemini-military-cybersec
description: "Ciberseguridad defensiva y ofensiva etica (OWASP Top 10, PCI-DSS, ISO 27001, AES-256-GCM, bastionado de servidores)."
---

# 🛡️ Bank & Military-Grade Cybersecurity Sentinel

Estándares estrictos de seguridad bancaria, criptografía aplicada y auditoría ofensiva ética.

## 1. Criptografía y Gestión de Secretos (Grado Bancario)
- Prohibición estricta de algoritmos obsoletos (MD5, SHA1, DES, 3DES, RSA < 2048).
- Uso obligatorio de cifrado autenticado: **AES-256-GCM** o **ChaCha20-Poly1305**.
- Derivación de claves y contraseñas: **Argon2id** o **PBKDF2** con alto factor de coste.
- Rotación de claves, variables de entorno inyectadas en runtime y cero persistencia de secretos en disco o Git.

## 2. Protección Contra Ataques Financieros y de Negocio
- **Race Conditions**: Bloqueos transaccionales en bases de datos (`SELECT ... FOR UPDATE`) para evitar doble gasto o manipulación de balances.
- **IDOR (Insecure Direct Object Reference)**: Verificación estricta de propiedad de recursos en cada capa de servicio (Tenant Isolation).
- **Prevención de Inyección**: Consultas 100% parametrizadas (Prepared Statements), validación de esquemas Zod/Pydantic en cada entrada externa.

## 3. Bastionado de Red e Infraestructura
- Cabeceras HTTP endurecidas: Strict-Transport-Security (HSTS), Content-Security-Policy (CSP) estricto, X-Frame-Options DENY.
- Rate limiting adaptativo y mitigación de fuerza bruta / DoS con Redis Token Bucket.
