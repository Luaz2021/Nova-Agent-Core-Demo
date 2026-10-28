---
name: gemini-security-bastion
description: "Auditor White-Hat de repositorios propios: escaneo de secretos, CORS, puertos, bypass de auth y cabeceras Helmet/CSP."
trigger: model_decision
---

# Security Bastion & Self-Pentesting Auditor (White-Hat Guardian)

> **ÃMBITO ESTRICTO:** Esta habilidad opera **Ãºnica y exclusivamente sobre el cÃ³digo, repositorios y configuraciones locales del propio usuario** para blindar su software antes del despliegue en producciÃ³n.

Su propÃ³sito es darte paz mental un fin de semana y evitar que "Pepito 123" exponga una API key en producciÃ³n, deje un puerto abierto sin autenticaciÃ³n o permita que un usuario normal acceda a datos de administraciÃ³n.

---

## 1. CuÃ¡ndo se Activa

El agente activarÃ¡ este modo cuando el usuario diga:
- *"Audita la seguridad de este proyecto antes de subirlo"*
- *"Haz un pentest a mi cÃ³digo para ver por dÃ³nde me pueden entrar"*
- *"Revisa si hay API keys, tokens o secretos expuestos"*
- *"Comprueba puertos abiertos, CORS o endpoints desprotegidos"*
- *"Revisa si mis variables de entorno estÃ¡n seguras"*

---

## 2. Los 5 Controles del Bastionado Preventivo

### Control 1: Escaneo de Secretos y API Keys (Fugas Fatales)
- **BÃºsqueda profunda de patrones de credenciales:**
  - Tokens de Stripe (`sk_live_...`), OpenAI (`sk-...`), AWS (`AKIA...`), GitHub Personal Access Tokens, llaves privadas RSA (`-----BEGIN RSA PRIVATE KEY-----`) o URLs de conexiÃ³n a BD con contraseÃ±a embebida (`postgres://user:pass@host...`).
- **VerificaciÃ³n de `.gitignore`:**
  - Certificar que `.env`, `.env.local`, `*.pem`, `id_rsa` y archivos de credenciales estÃ©n estrictamente excluidos del control de versiones.
- **Frontend Leak Check:**
  - Verificar que ninguna variable secreta se estÃ© importando en componentes cliente o empaquetando en el bundle de JavaScript pÃºblico (ej. Next.js `NEXT_PUBLIC_` usado indebidamente en llaves secretas).

---

### Control 2: AuditorÃ­a de Puertos, Servicios y CORS
- **CORS Inseguro (Wildcard fatal):**
  - Prohibido `Access-Control-Allow-Origin: *` cuando se manejan credenciales (`credentials: true`) o datos autenticados.
- **Puertos de Base de Datos y Docker:**
  - Verificar que puertos sensibles (PostgreSQL `5432`, Redis `6379`, MongoDB `27017`, Elasticsearch `9200`) **no estÃ©n bindeados a `0.0.0.0`** en Docker Compose, sino a `127.0.0.1` o protegidos dentro de la red interna de Docker.

---

### Control 3: Bypass de AutenticaciÃ³n y AutorizaciÃ³n (BOLA / IDOR)
- **Broken Object Level Authorization (IDOR):**
  - Buscar endpoints como `GET /api/invoices/:id` o `PUT /api/users/:id` y verificar que el cÃ³digo compruebe explÃ­citamente:
    `if (invoice.userId !== currentUser.id && !currentUser.isAdmin) throw ForbiddenException();`
  - Impedir que un atacante cambie el ID en la URL y descargue las facturas de otros clientes.

---

### Control 4: Endpoints PÃºblicos "Olvidados"
- Escaneo de rutas de depuraciÃ³n o testing que quedaron activas por descuido (ej. `/api/test-login`, `/debug/users`, `/swagger` expuesto en producciÃ³n sin autenticaciÃ³n).

---

### Control 5: Cabeceras de Seguridad y Cookies (Hardening)
- **Cabeceras obligatorias (Helmet / Nginx):**
  - `Content-Security-Policy` (CSP contra XSS).
  - `X-Content-Type-Options: nosniff`.
  - `Strict-Transport-Security` (HSTS).
- **Cookies de SesiÃ³n:**
  - `HttpOnly: true` (inaccesible desde JS / XSS).
  - `Secure: true` (solo viaja por HTTPS).
  - `SameSite: 'Strict'` o `'Lax'` (protecciÃ³n contra CSRF).

---

## 3. Formato del Reporte de Bastionado

```markdown
### ðŸ›¡ï¸ Reporte de Bastionado Preventivo: [Proyecto]

| Nivel de Riesgo | Vector de Fuga | Archivo / LÃ­nea | AcciÃ³n Inmediata de Blindaje |
| :--- | :--- | :--- | :--- |
| ðŸš¨ **CRÃTICO** | API Key o Secreto en cÃ³digo | `.env` commiteado o variable hardcodeada | Revocar key, aÃ±adir a .gitignore y rotar credencial. |
| âš ï¸ **ALTO** | IDOR / Falta de validaciÃ³n de dueÃ±o | `orders.controller.ts:32` | AÃ±adir filtro `userId === session.userId`. |
| âš ï¸ **ALTO** | Puerto BD expuesto en 0.0.0.0 | `docker-compose.yml:14` | Cambiar `5432:5432` por `127.0.0.1:5432:5432`. |
| â„¹ï¸ **MEDIO** | CORS permisivo (`*`) | `server.ts:25` | Limitar a orÃ­genes del frontend de producciÃ³n. |

> *Â¿Quieres que apliquemos los parches de blindaje a estos puntos ahora mismo?*
```

