---
name: design-qa
description: "Gates de control de calidad de diseno: lint de tokens, axe a11y, contraste y regresion visual en variantes/temas."
---

# Skill: Design QA

Stand up the automated + visual gates that stop quality from regressing in Nova 2026.

## Steps
1. Follow the QA pyramid: token/lint gates → automated a11y → Playwright 2-viewport captures + `blaifa/InternVL3_5:8b` visual audit → surgical `edit_file <= 35%`.
2. Run the **fast gates** first: `python <NOVA_HOME>\nova_core\orquestador.py revisar <dir>`, `node <NOVA_HOME>\antigravity\almacen\skills\gemini-ui-artisan\scripts\lint.mjs <src>`, and `nova_tarea.py --verificar --carpeta <dir>` (measures real WCAG contrast in the rendered page; `nova_color_oracle.py` is retired since 09/11: it called a cloud model).
3. Run the **real-render browser gate**: `node <NOVA_HOME>\antigravity\almacen\skills\gemini-ui-artisan\scripts\inspect.mjs <file.html>` at 1440px, 768px, and 390px. Zero `FAIL` allowed.
4. Run **Playwright dual captures** (Desktop 1280px + Mobile 375px and per-section snapshots) and audit with `blaifa/InternVL3_5:8b` (`nova_puente_capturas.py`). Note exact failing lines and patch only those lines (`edit_file <= 35%`).
5. Verify keyboard navigation, visible focus, 8 interactive states, and `prefers-reduced-motion` fallback.

## Verification (definition of done)
- An unreviewed PR cannot introduce an unresolved token alias, a contrast failure, a raw hex/px, or an axe violation: a gate blocks each.
- Snapshots cover dark mode + RTL + the semantic-changing states, not just the happy path.
- Manual a11y checklist signed off for the release.
