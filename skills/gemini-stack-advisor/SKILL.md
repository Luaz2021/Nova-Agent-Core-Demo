---
name: gemini-stack-advisor
description: "Analiza el stack de un proyecto y recomienda servidores MCP, reglas locales, hooks y mejoras de librerias."
trigger: model_decision
---

# Project Stack Advisor & Automations Recommender

Esta habilidad analiza en profundidad la base de cÃ³digo de cualquier proyecto activo y recomienda integraciones, servidores MCP, reglas de desarrollo y herramientas complementarias a la medida del stack detectado.

---

## 1. CuÃ¡ndo Ejecutar Esta Habilidad

El agente activarÃ¡ esta habilidad cuando:
- El usuario abra un nuevo proyecto o pregunte: *"Â¿QuÃ© me recomiendas para este proyecto?", "Â¿QuÃ© integraciones o MCP deberÃ­a usar?", "Â¿CÃ³mo configuro este repositorio para Antigravity?"*.
- El usuario pregunte si su arquitectura o librerÃ­as actuales son las mÃ¡s recomendadas o si conviene complementarlas con otras soluciones.

---

## 2. Fase de AnÃ¡lisis del Proyecto (Read-Only)

El agente inspecciona de forma no invasiva:

1. **Gestores de paquetes y archivos de configuraciÃ³n:**
   - `package.json`, `pnpm-lock.yaml`, `bun.lockb` (Node / JS / TS)
   - `pyproject.toml`, `requirements.txt`, `Pipfile` (Python)
   - `pom.xml`, `build.gradle` (Java / Kotlin)
   - `Cargo.toml` (Rust)
   - `go.mod` (Go)
   - `docker-compose.yml`, `Dockerfile` (Contenedores y servicios)
2. **Estructura del proyecto:**
   - Carpetas de cÃ³digo fuente (`src/`, `app/`, `pages/`, `components/`, `lib/`).
   - ConfiguraciÃ³n de testing (`tests/`, `__tests__/`, `playwright.config.ts`, `vitest.config.ts`, `pytest.ini`).
3. **Configuraciones existentes de IA:**
   - Presencia de `GEMINI.md`, `AGENTS.md` o `.agents/`.

---

## 3. Matriz de Recomendaciones Inteligentes

BasÃ¡ndose en las tecnologÃ­as detectadas, el agente selecciona las mejores recomendaciones organizadas en 4 categorÃ­as:

### A. Servidores MCP Recomendados
| SeÃ±al en el CÃ³digo | Servidor MCP Sugerido | PropÃ³sito |
| :--- | :--- | :--- |
| React, Vue, Svelte, Next.js | **Playwright MCP** / Browser | Pruebas de interfaz, navegaciÃ³n y validaciÃ³n visual. |
| PostgreSQL, MySQL, SQLite | **Database MCP** | InspecciÃ³n de esquemas, consultas directas y optimizaciÃ³n SQL. |
| Supabase | **Supabase MCP** | GestiÃ³n de migraciones, autenticaciÃ³n y storage. |
| GitHub Actions / `.git` | **GitHub MCP** | GestiÃ³n de issues, pull requests y estados de CI/CD. |
| APIs complejas / Stripe / AWS | **Context / Docs MCP** | Consulta de documentaciÃ³n en tiempo real sin alucinaciones. |

### B. Reglas de Workspace (`GEMINI.md` / `AGENTS.md`)
- GeneraciÃ³n de un archivo de reglas a la medida del framework (ej. principios de Server Actions en Next.js, inyecciÃ³n de dependencias en Spring Boot, tipado estricto en TypeScript o buenas prÃ¡cticas en FastAPI).

### C. Automatizaciones y Hooks Sugeridos
- Formateo y linting automÃ¡tico en guardado (`Prettier`, `Biome`, `Black`, `Ruff`, `ESLint`).
- ProtecciÃ³n de variables de entorno (bloqueo de commits si `.env` no estÃ¡ en `.gitignore`).

### D. Skills Complementarias de Antigravity
- Si maneja cÃ³digo backend modular $\rightarrow$ Recomendar la skill `clean-architecture`.
- Si maneja autenticaciÃ³n o pagos $\rightarrow$ Recomendar la skill `security-audit`.
- Si maneja interfaces complejas $\rightarrow$ Recomendar la skill `ui-design-system`.

---

## 4. Formato de Salida al Usuario

El reporte debe ser claro, estructurado y listo para actuar:

```markdown
### ðŸ” DiagnÃ³stico del Proyecto: [Nombre del Proyecto]
- **Stack Detectado:** [Ej. Next.js 15, TypeScript, TailwindCSS, Supabase, Vitest]

#### ðŸš€ Recomendaciones Clave:
1. **Servidores MCP Sugeridos:**
   - *[Nombre MCP]*: Motivo por el cual beneficiarÃ¡ a este proyecto.
2. **Reglas de Desarrollo (`GEMINI.md`):**
   - Directrices especÃ­ficas para este stack que evitarÃ¡n errores comunes.
3. **Skills & Automatizaciones:**
   - Skills recomendadas para este caso de uso.
4. **Mejoras del Stack (Opcional):**
   - LibrerÃ­as modernas o alternativas que mejorarÃ­an el rendimiento o la DX del proyecto.

> *Â¿Quieres que activemos o configuremos alguna de estas integraciones ahora mismo?*
```

---

## 5. Auto-Precalentamiento (.agents/stack-lock.json)
Para no quemar tokens re-analizando el arbol de dependencias cada vez que se abre el repositorio:
1. Una vez realizado el diagnostico inicial, guardar el resultado en un micro-archivo ultraligero:
   `.agents/stack-lock.json`
2. El archivo contiene el stack principal y las 5 skills clave recomendadas.
3. En sesiones futuras en esa carpeta, `gemini-multiagent-router` lee directamente `stack-lock.json` en 0 segundos a coste de ~10 tokens, precalentando las herramientas necesarias sin escanear carpetas completas.

