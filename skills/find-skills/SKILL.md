---
name: find-skills
description: "Buscador e instalador de skills para agentes desde repositorios de Vercel Labs y skills.sh por tecnologia."
---

# Find Skills (Motor de Descubrimiento de Habilidades)

Esta skill permite a Nova buscar, evaluar e incorporar habilidades de los directorios mundiales de IA (`skills.sh`, GitHub y `vercel-labs/skills`).

## 1. Procedimiento de Búsqueda
Cuando el usuario pida:
- *"Busca una skill para X"*
- *"¿Hay alguna habilidad que haga Y?"*
- *"Encuentra cómo mejorar el rendimiento de Z"*

### Paso 1: Explorar el Catálogo Global
1. Consultar el índice de `skills.sh` o repositorios verificados de GitHub (`vercel-labs/agent-skills`, `affaan-m/ecc`, etc.).
2. Identificar si la skill resuelve un problema real del stack actual (React, Next.js, Node, PostgreSQL, Tailwind).

### Paso 2: Análisis de Calidad y Cero Ruido
- Descartar skills redundantes o con dependencias rotas.
- Extraer las directrices esenciales en formato estandarizado `SKILL.md`.

### Paso 3: Almacenamiento en Google Drive
- Guardar la nueva habilidad en `G:\Mi unidad\Antigravity\skills\<nombre-de-la-skill>\SKILL.md`.
- Conectar la habilidad al `gemini-multiagent-router` para activación por contexto.
