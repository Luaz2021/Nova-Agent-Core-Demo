---
name: cursorrules-advisor
description: Catalog, search, and adapt project-specific rules from the 250+ awesome-cursorrules collection into .cursorrules, .cursor/rules/*.mdc, or GEMINI.md. Use when the user asks for cursor rules, project rules for a specific stack (React Native, Expo, Supabase, Spring Boot, Next.js, FastAPI), or wants to enforce coding standards on a repository.
metadata:
  total_rules: 257
  source: PatrickJS/awesome-cursorrules
---

# CursorRules Advisor & Project Rules Engine

Allows Nova and Antigravity to lookup, fetch, and adapt the best-practice rules from the 250+ `awesome-cursorrules` collection for any language, framework, or project stack.

## When to Use This Skill

- When starting a new project and configuring its `.cursorrules`, `.cursor/rules/`, or local `GEMINI.md`.
- When the user asks: "dame las cursor rules para [stack]", "configura las reglas de este proyecto", "qué buenas prácticas recomiendas para [React Native / Supabase / Spring Boot / FastAPI]".
- When setting up architectural, security, or code quality standards for a repository.

## Bundled Flagship Rules

Key rules pre-packaged locally in `bundled-rules/`:
- **React Native & Expo**: `bundled-rules/*expo*.mdc` (ideal for AutoCheck)
- **Next.js + React + Tailwind + Supabase**: `bundled-rules/*supabase*.mdc`
- **Clean Code & KISS**: `bundled-rules/clean-code.mdc`
- **Anti-Overengineering**: `bundled-rules/anti-overengineering.mdc`
- **Security & AppSec**: `bundled-rules/security-devsecops-ssdls-appsec.mdc`

## Catalog of 250+ Rules

The complete index of available rules is in `rules-catalog-index.json`.

To adapt a rule from `PatrickJS/awesome-cursorrules`:
1. Search `rules-catalog-index.json` for matching keywords (e.g., `angular`, `astro`, `flutter`, `golang`, `rust`, `vue`).
2. Fetch the raw file from `https://raw.githubusercontent.com/PatrickJS/awesome-cursorrules/main/rules/<filename>`.
3. Adapt the instructions to fit Nova's KISS guidelines and the project's local directory structure.
