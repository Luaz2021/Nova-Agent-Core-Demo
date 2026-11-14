---
name: gemini-security-bastion
description: "Auditor White-Hat de repositorios propios: escaneo de secretos, CORS, puertos, bypass de auth y cabeceras Helmet/CSP."
trigger: model_decision
---

# Security Bastion & Self-Pentesting Auditor (White-Hat Guardian)

> **ÁMBITO ESTRICTO:** Esta habilidad opera **única y exclusivamente sobre el código, repositorios y configuraciones locales del propio usuario** para blindar su software antes del despliegue en producción.

Su propósito es darte paz mental un fin de semana y evitar que "Pepito 123" exponga una API key en producción, deje un puerto abierto sin autenticación o permita que un usuario normal acceda a datos de administración.

---

## 1. Cuándo se Activa

El agente activará este modo cuando el usuario diga:
- *"Audita la seguridad de este proyecto antes de subirlo"*
- *"Haz un pentest a mi código para ver por dónde me pueden entrar"*
- *"Revisa si hay API keys, tokens o secretos expuestos"*
- *"Comprueba puertos abiertos, CORS o endpoints desprotegidos"*
- *"Revisa si mis variables de entorno están seguras"*

---

## 2. Los 5 Controles del Bastionado Preventivo

### Control 1: Escaneo de Secretos y Entropía de Shannon (Fugas Fatales)
- **Análisis Matemático de Entropía (H >= 4.2 bits):**
  - Ejecutar `python "<NOVA_HOME>\antigravity\scripts\security\entropy_secret_scanner.py" --path .`
  - Caza cualquier secreto o contraseña de alta aleatoriedad independientemente de su nombre o prefijo.
- **Búsqueda profunda de patrones de credenciales conocidas:**
  - Tokens de Stripe (`sk_live_...`), OpenAI (`sk-...`), AWS (`AKIA...`), GitHub Personal Access Tokens, llaves privadas RSA (`-----BEGIN RSA PRIVATE KEY-----`) o URLs de conexión a BD con contraseña embebida (`postgres://user:pass@host...`).
- **Verificación de `.gitignore`:**
  - Certificar que `.env`, `.env.local`, `*.pem`, `id_rsa` y archivos de credenciales estén estrictamente excluidos del control de versiones.
- **Frontend Leak Check:**
  - Verificar que ninguna variable secreta se esté importando en componentes cliente o empaquetando en el bundle de JavaScript público (ej. Next.js `NEXT_PUBLIC_` usado indebidamente en llaves secretas).

---

### Control 2: Auditoría de Puertos, Servicios y CORS
- **CORS Inseguro (Wildcard fatal):**
  - Prohibido `Access-Control-Allow-Origin: *` cuando se manejan credenciales (`credentials: true`) o datos autenticados.
- **Puertos de Base de Datos y Docker:**
  - Verificar que puertos sensibles (PostgreSQL `5432`, Redis `6379`, MongoDB `27017`, Elasticsearch `9200`) **no estén bindeados a `0.0.0.0`** en Docker Compose, sino a `127.0.0.1` o protegidos dentro de la red interna de Docker.

---

### Control 3: Bypass de Autenticación y Autorización (BOLA / IDOR)
- **Broken Object Level Authorization (IDOR):**
  - Buscar endpoints como `GET /api/invoices/:id` o `PUT /api/users/:id` y verificar que el código compruebe explícitamente:
    `if (invoice.userId !== currentUser.id && !currentUser.isAdmin) throw ForbiddenException();`
  - Impedir que un atacante cambie el ID en la URL y descargue las facturas de otros clientes.

---

### Control 4: Endpoints Públicos "Olvidados"
- Escaneo de rutas de depuración o testing que quedaron activas por descuido (ej. `/api/test-login`, `/debug/users`, `/swagger` expuesto en producción sin autenticación).

---

### Control 5: Cabeceras de Seguridad y Cookies (Hardening)
- **Cabeceras obligatorias (Helmet / Nginx):**
  - `Content-Security-Policy` (CSP contra XSS).
  - `X-Content-Type-Options: nosniff`.
  - `Strict-Transport-Security` (HSTS).
- **Cookies de Sesión:**
  - `HttpOnly: true` (inaccesible desde JS / XSS).
  - `Secure: true` (solo viaja por HTTPS).
  - `SameSite: 'Strict'` o `'Lax'` (protección contra CSRF).

---

### Control 6: Auditoría SCA de Dependencias a 0 Tokens
- Ejecutar `python "<NOVA_HOME>\antigravity\scripts\qa\audit_dependencies.py" --path .`
- Inspecciona vulnerabilidades y CVEs conocidos en `package.json` o `requirements.txt` con herramientas nativas del ecosistema antes de autorizar cualquier despliegue.

---

## 3. Formato del Reporte de Bastionado

```markdown
### 🛡️ Reporte de Bastionado Preventivo: [Proyecto]

| Nivel de Riesgo | Vector de Fuga | Archivo / Línea | Acción Inmediata de Blindaje |
| :--- | :--- | :--- | :--- |
| 🚨 **CRÍTICO** | API Key o Secreto en código | `.env` commiteado o variable hardcodeada | Revocar key, añadir a .gitignore y rotar credencial. |
| ⚠️ **ALTO** | IDOR / Falta de validación de dueño | `orders.controller.ts:32` | Añadir filtro `userId === session.userId`. |
| ⚠️ **ALTO** | Puerto BD expuesto en 0.0.0.0 | `docker-compose.yml:14` | Cambiar `5432:5432` por `127.0.0.1:5432:5432`. |
| ℹ️ **MEDIO** | CORS permisivo (`*`) | `server.ts:25` | Limitar a orígenes del frontend de producción. |

> *¿Quieres que apliquemos los parches de blindaje a estos puntos ahora mismo?*
```

