---
name: index-backend-db
description: "Indice Macro Backend, Base de Datos & Redes: Arquitectura Limpia, FastAPI, Node, PostgreSQL/Supabase RLS, migraciones zero-downtime, Docker y Cisco/IoT."
---

# Index 03 · Backend, Databases, BaaS, Docker & Hardware (1-Hop Router)

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **Salto Obligatorio al Almacen:** Al disenar APIs, backends desde cero, migraciones o esquemas Supabase/Postgres, abrir en paralelo las skills nucleares del apartado 2 (`gemini-clean-architecture`, `gemini-supabase-security`, `gemini-database-mastery`) antes de generar el contrato para `qwen3.5:9b`. Reparar siempre por lineas (`edit_file <= 35%`), nunca reemplazando el archivo entero.
- **Arquitectura Limpia & KISS:** Separar responsabilidades en `Controller/Router` (validacion HTTP), `Service/UseCases` (logica de negocio pura) y `Repository/DAO` (acceso a datos). Usar *early returns*, tipado estricto (Pydantic v2 / TypeScript / Java 21) y cero logica SQL dentro de controladores.
- **Supabase & PostgreSQL (Zero-Trust RLS):** Toda tabla en Supabase debe tener Row Level Security (`ENABLE ROW LEVEL SECURITY`) y politicas atomicas para `SELECT`, `INSERT`, `UPDATE`, `DELETE` usando `(select auth.uid()) = user_id` (envuelto en subconsulta para cacheo por planificador). Jamas exponer `service_role_key` en frontend.
- **SQL de Alto Rendimiento:** Prohibido el problema `N+1` (usar `JOIN` o carga por lotes), indexar toda clave foranea (`B-Tree`) y columnas JSONB consultadas (`GIN`), y usar paginacion por cursor en tablas grandes.
- **Migraciones Sin Caida (Expand-Contract):** Nunca renombrar ni borrar columnas en produccion en un solo paso; agregar columna nullable, hacer doble escritura/backfill, cambiar lectura y eliminar en fase posterior. Usar `CREATE INDEX CONCURRENTLY`.

## Trampas de Flash (errores reales ya cometidos)
- Antes de usar o sugerir una libreria, comprobar que esta en `package.json` / `requirements.txt` (`nodemailer` sin declarar rompio el runtime).
- Fechas `YYYY-MM-DD HH:mm`: `.replace(' ', 'T')` antes de `new Date()`; hora de negocio con zona (`America/Lima`) porque el servidor corre en UTC.
- La misma regla de validacion en frontend y backend (caso menores: el back exigia parentesco a todos).
- Alias SQL que no sean palabras reservadas (`mod` rompe en MySQL/MariaDB); `LEFT JOIN` si la relacion puede ser nula.
- SQLite con `path.join(__dirname, ...)`; en Render free el disco es efimero y SMTP esta bloqueado: archivos a Supabase Storage y correo por API HTTPS (Brevo/Resend).

## Definicion de hecho
- Cada endpoint tocado probado (curl o test) con un caso correcto y uno de error (validacion, 403, 404).
- Middleware de autenticacion verificado en cada ruta nueva o modificada.
- Migraciones en modo expand-contract y con vuelta atras descrita.

## 2. Mapa de Salto a las Skills (`<NOVA_HOME>/antigravity/` + la ruta `skills/...` de cada entrada)
Abrir con `read_file` en paralelo al crear arquitectura, endpoints, tablas o redes:
- **Arquitectura, APIs & Frameworks:** `skills\gemini-clean-architecture\SKILL.md` | `skills\gemini-system-architect\SKILL.md` | `skills\api-design\SKILL.md` | `skills\backend-patterns\SKILL.md` | `skills\fastapi-patterns\SKILL.md` | `skills\cursorrules-advisor\SKILL.md`
- **Bases de Datos & Supabase:** `skills\gemini-database-mastery\SKILL.md` | `skills\database-migrations\SKILL.md` | `skills\gemini-supabase-security\SKILL.md`
- **Contenedores & Servidores MCP:** `skills\docker-patterns\SKILL.md` | `skills\gemini-mcp-app\SKILL.md` | `skills\architecture-decision-records\SKILL.md`
- **Redes Cisco & Robotica Embebida:** `skills\cisco-network-architect\SKILL.md` | `skills\embedded-robotics-maker\SKILL.md`
- **Blockchain, Web3 & FinTech:** `skills\blockchain-security-foundry\SKILL.md` | `skills\fintech-web3-business\SKILL.md`
