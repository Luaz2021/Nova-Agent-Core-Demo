# 🗺️ Guía Maestra: Dónde y Cómo Publicar Nova Agent

Este documento contiene los enlaces exactos, repositorios y plantillas de texto listas para enviar a los mejores directorios de la comunidad internacional de agentes de IA y código abierto.

---

## 1. Directorios de Agentes Autónomos (Máxima Relevancia)

### A. `awesome-ai-agents` (E2B)
- **Repositorio:** [https://github.com/e2b-dev/awesome-ai-agents](https://github.com/e2b-dev/awesome-ai-agents)
- **Cómo participar:** Fork del repositorio -> Editar `README.md` -> Abrir Pull Request.
- **Sección:** *Coding & Software Engineering Agents*
- **Línea a agregar en Markdown:**
  ```markdown
  - [Nova Agent](https://github.com/Luaz2021/Nova-Agent-Core-Demo) - Open-source autonomous engineering engine built natively for Google Antigravity 2.0 and Gemini models with 119 skills, continuous learning, and token cost optimization.
  ```

### B. `awesome-autonomous-agents` (Kyrolabs)
- **Repositorio:** [https://github.com/kyrolabs/awesome-autonomous-agents](https://github.com/kyrolabs/awesome-autonomous-agents)
- **Cómo participar:** Fork -> Añadir en la sección de *Autonomous Developer Agents* -> Pull Request.
- **Texto:** Mismo formato que E2B.

---

## 2. Ecosistema Nativo de Google & Gemini

### A. `awesome-gemini`
- **Repositorio:** [https://github.com/reorx/awesome-gemini](https://github.com/reorx/awesome-gemini)
- **Cómo participar:** Pull Request en la sección *Agent Frameworks & Tools*.
- **Texto de PR:**
  ```markdown
  ### Add Nova Agent: Google-Native Autonomous Engineering Engine
  Nova Agent is the first open-source software engineering agent built exclusively for Google Antigravity 2.0 and Gemini 3.8/Argon models, featuring 119 specialized engineering skills, persistent memory, and a 4-tier token cost hierarchy.
  ```

### B. Google Developer Groups (GDG) & Discord de Google AI
- **Discord Oficial de Google DeepMind / Gemini:** Canal `#projects-showcase` o `#community-tools`.
- **Pitch sugerido (en inglés para máxima repercusión):**
  > *"Hey everyone! While most agent frameworks focus on Claude or Cursor, I spent the last month building and stress-testing **Nova Agent**: the first open-source autonomous engineering agent designed 100% natively for **Google Antigravity 2.0** and the **Gemini** ecosystem. It features 119 domain skills, a 4-tier cost architecture (including local Ollama for zero-cost logs), strict TDD, and a 38% cold-start token reduction. Check it out and let me know your thoughts: https://github.com/Luaz2021/Nova-Agent-Core-Demo"*

---

## 3. Directorios de Skills & Reglas

### A. `skills.sh` (Vercel Labs)
- **Web / Repositorio:** [https://skills.sh](https://skills.sh) / [https://github.com/vercel-labs](https://github.com/vercel-labs)
- **Cómo participar:** Enviar un Pull Request indexando el repositorio para que los desarrolladores puedan instalar las skills de Nova vía su CLI.

### B. `cursor.directory`
- **Web:** [https://cursor.directory](https://cursor.directory)
- **Cómo participar:** Formulario web directo en el botón *"Submit Rule / Agent"*.
- **Campos:**
  - *Title:* Nova Agent - Google-Native Engineering Copilot
  - *Category:* Fullstack / Architecture / DevSecOps
  - *Repository:* `https://github.com/Luaz2021/Nova-Agent-Core-Demo`

### C. `awesome-cursorrules` (PatrickJS)
- **Repositorio:** [https://github.com/PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)
- **Cómo participar:** PR agregando Nova en la sección de agentes y directrices multi-rol.

---

## 4. Lanzamiento Comunitario (Show HN & Reddit)

### A. Hacker News (Show HN)
- **URL de Envío:** [https://news.ycombinator.com/submit](https://news.ycombinator.com/submit)
- **Título:** `Show HN: Nova Agent – Open-source autonomous engineering engine for Google Antigravity 2.0`
- **URL:** `https://github.com/Luaz2021/Nova-Agent-Core-Demo`
- **Texto:**
  > *"Hi HN, I built Nova Agent because almost every open-source AI agent project is focused on OpenAI or Anthropic wrappers. Google Antigravity 2.0 and Gemini models have massive context windows and great latency, but lacked a dedicated agentic framework with strict engineering discipline. Nova includes 119 specialized skills, 1-shot execution protocols, local Ollama routing for free logs, and anti-slop frontend standards. Feedback and contributions (especially for a dedicated Flutter GUI) are welcome!"*

### B. Reddit
- **Subreddits recomendados:**
  - `r/GoogleGeminiAI`
  - `r/LocalLLaMA` (enfocándote en el enrutamiento a Qwen 2.5 Coder 7B local para no pagar tokens en volcados de logs)
  - `r/ArtificialIntelligence`
  - `r/programming`

---

## 5. Próximo Paso: Product Hunt
- Cuando el instalador y la primera versión de la GUI estén montados a finales de noviembre, registrar Nova Agent en Product Hunt en la categoría *Developer Tools* & *Artificial Intelligence*.
