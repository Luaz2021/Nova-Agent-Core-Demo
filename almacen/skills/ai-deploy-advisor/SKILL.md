---
name: ai-deploy-advisor
description: "Auditor y generador de despliegue a 0 EUR (Vercel, Cloudflare, Render, Fly.io, Supabase, Docker, GitHub Actions)."
trigger: model_decision
---

# AI Deploy Advisor (Arquitecto de Despliegue Coste 0€)

Esta habilidad analiza el stack completo de tu proyecto para determinar la forma más rápida, segura y económica (priorizando tiers 100% gratuitos) de desplegarlo en la nube, entregando los archivos de configuración necesarios sin tener que investigar documentación.

---

## 1. Cuándo se Activa
Se activa automáticamente cuando el usuario dice:
- *"¿Dónde puedo desplegar este proyecto?"*, *"Recomiéndame un hosting o servidor para esto"*, *"¿Cómo lo subo a internet gratis?"*, *"Prepara este proyecto para producción / deploy"*, *"Genera los archivos de despliegue para Vercel/Render/Fly.io/Docker"*.

---

## 2. Los 4 Pasos del Triaje de Despliegue

### Paso 1: Radiografía del Stack Local
1. **Frontend:** Next.js, React SPA (Vite), Astro, HTML/CSS o Vue.
2. **Backend:** FastAPI (Python), Spring Boot (Java), Node/Express, NestJS o Go.
3. **Persistencia y Base de Datos:** SQLite local, PostgreSQL, Supabase, Redis o MongoDB.
4. **Secretos y Variables de Entorno:** Auditar `.env.example` para detectar qué variables exige la app para no romperse al arrancar.

### Paso 2: Matriz de Decisión de Infraestructura (Prioridad Coste 0€)

| Componente | Opción Recomendada (0€) | Segunda Opción / Escalado |
| :--- | :--- | :--- |
| **Frontend Estático / SPA** | **Cloudflare Pages** (ancho de banda ilimitado gratis) | **Vercel** / **Netlify** |
| **Frontend Next.js SSR** | **Vercel** (optimización nativa Vercel Edge) | **Cloudflare Workers** |
| **Backend Python / Node** | **Render.com** (Free Web Service) | **Railway** / **Fly.io** |
| **Backend Java (Spring Boot)** | **Render Docker / Fly.io** (512MB RAM) | **Hetzner Cloud VPS** (3.5€/mes para alto rendimiento) |
| **Base de Datos SQL** | **Supabase** (Postgres 500MB gratis) / **Neon.tech** | **Turso** (SQLite distribuido) |

### Paso 3: Generación de Artefactos de Despliegue
Según la plataforma elegida, generar de inmediato:
- `Dockerfile` multi-stage ligero (Alpine/Distroless para arranques rápidos y bundle menor a 100MB).
- `docker-compose.yml` para pruebas locales idénticas a producción.
- Archivo específico del proveedor (`render.yaml`, `vercel.json` o `fly.toml`).
- Workflow de CI/CD para GitHub Actions (`.github/workflows/deploy.yml`) que corra linter y tests antes de disparar el despliegue.

### Paso 4: Hoja de Ruta de 3 Pasos para Alexander
Nova entrega una guía de 3 pasos directos:
1. Qué comando ejecutar localmente para validar que el build compila (`npm run build`, `mvn clean package` o `docker build`).
2. Qué variables de entorno cargar en el panel web del proveedor.
3. El enlace directo al dashboard para activar el despliegue automático con Git.
