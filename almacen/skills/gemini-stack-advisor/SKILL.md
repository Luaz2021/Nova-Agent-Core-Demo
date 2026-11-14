---
name: gemini-stack-advisor
description: "Analiza el stack de un proyecto y recomienda servidores MCP, reglas locales, hooks y mejoras de librerias."
trigger: model_decision
---

# Project Stack Advisor & Automations Recommender

Esta habilidad analiza en profundidad la base de código de cualquier proyecto activo y recomienda integraciones, servidores MCP, reglas de desarrollo y herramientas complementarias a la medida del stack detectado.

---

## 1. Cuándo Ejecutar Esta Habilidad

El agente activará esta habilidad cuando:
- El usuario abra un nuevo proyecto o pregunte: *"¿Qué me recomiendas para este proyecto?", "¿Qué integraciones o MCP debería usar?", "¿Cómo configuro este repositorio para Antigravity?"*.
- El usuario pregunte si su arquitectura o librerías actuales son las más recomendadas o si conviene complementarlas con otras soluciones.

---

## 2. Fase de Análisis del Proyecto (Read-Only)

El agente inspecciona de forma no invasiva:

1. **Gestores de paquetes y archivos de configuración:**
   - `package.json`, `pnpm-lock.yaml`, `bun.lockb` (Node / JS / TS)
   - `pyproject.toml`, `requirements.txt`, `Pipfile` (Python)
   - `pom.xml`, `build.gradle` (Java / Kotlin)
   - `Cargo.toml` (Rust)
   - `go.mod` (Go)
   - `docker-compose.yml`, `Dockerfile` (Contenedores y servicios)
2. **Estructura del proyecto:**
   - Carpetas de código fuente (`src/`, `app/`, `pages/`, `components/`, `lib/`).
   - Configuración de testing (`tests/`, `__tests__/`, `playwright.config.ts`, `vitest.config.ts`, `pytest.ini`).
3. **Configuraciones existentes de IA:**
   - Presencia de `GEMINI.md`, `AGENTS.md` o `.agents/`.

---

## 3. Matriz de Recomendaciones Inteligentes

Basándose en las tecnologías detectadas, el agente selecciona las mejores recomendaciones organizadas en 4 categorías:

### A. Servidores MCP Recomendados
| Señal en el Código | Servidor MCP Sugerido | Propósito |
| :--- | :--- | :--- |
| React, Vue, Svelte, Next.js | **Playwright MCP** / Browser | Pruebas de interfaz, navegación y validación visual. |
| PostgreSQL, MySQL, SQLite | **Database MCP** | Inspección de esquemas, consultas directas y optimización SQL. |
| Supabase | **Supabase MCP** | Gestión de migraciones, autenticación y storage. |
| GitHub Actions / `.git` | **GitHub MCP** | Gestión de issues, pull requests y estados de CI/CD. |
| APIs complejas / Stripe / AWS | **Context / Docs MCP** | Consulta de documentación en tiempo real sin alucinaciones. |

### B. Reglas de Workspace (`GEMINI.md` / `AGENTS.md`)
- Generación de un archivo de reglas a la medida del framework (ej. principios de Server Actions en Next.js, inyección de dependencias en Spring Boot, tipado estricto en TypeScript o buenas prácticas en FastAPI).

### C. Automatizaciones y Hooks Sugeridos
- Formateo y linting automático en guardado (`Prettier`, `Biome`, `Black`, `Ruff`, `ESLint`).
- Protección de variables de entorno (bloqueo de commits si `.env` no está en `.gitignore`).

### D. Skills Complementarias de Antigravity
- Si maneja código backend modular $\rightarrow$ Recomendar la skill `clean-architecture`.
- Si maneja autenticación o pagos $\rightarrow$ Recomendar la skill `security-audit`.
- Si maneja interfaces complejas $\rightarrow$ Recomendar la skill `ui-design-system`.

---

## 4. Formato de Salida al Usuario

El reporte debe ser claro, estructurado y listo para actuar:

```markdown
### 🔍 Diagnóstico del Proyecto: [Nombre del Proyecto]
- **Stack Detectado:** [Ej. Next.js 15, TypeScript, TailwindCSS, Supabase, Vitest]

#### 🚀 Recomendaciones Clave:
1. **Servidores MCP Sugeridos:**
   - *[Nombre MCP]*: Motivo por el cual beneficiará a este proyecto.
2. **Reglas de Desarrollo (`GEMINI.md`):**
   - Directrices específicas para este stack que evitarán errores comunes.
3. **Skills & Automatizaciones:**
   - Skills recomendadas para este caso de uso.
4. **Mejoras del Stack (Opcional):**
   - Librerías modernas o alternativas que mejorarían el rendimiento o la DX del proyecto.

> *¿Quieres que activemos o configuremos alguna de estas integraciones ahora mismo?*
```

---

## 5. Auto-Precalentamiento (.agents/stack-lock.json)
Para no quemar tokens re-analizando el arbol de dependencias cada vez que se abre el repositorio:
1. Una vez realizado el diagnostico inicial, guardar el resultado en un micro-archivo ultraligero:
   `.agents/stack-lock.json`
2. El archivo contiene el stack principal y las 5 skills clave recomendadas.
3. En sesiones futuras en esa carpeta, `gemini-multiagent-router` lee directamente `stack-lock.json` en 0 segundos a coste de ~10 tokens, precalentando las herramientas necesarias sin escanear carpetas completas.

