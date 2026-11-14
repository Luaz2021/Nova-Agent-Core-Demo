---
name: ux-writing
description: "Redaccion y revision de microcopy UI (botones, estados vacios y errores con formula que/por que/como resolver)."
---

# Skill: UX Writing

Produce or critique interface copy in the project's voice (100% standalone in Nova 2026).

## Steps
1. Define voice principles, tone spectrum, formulas, microcopy patterns, and inclusive language for the target archetype (A-F).
2. Match tone to the user's emotional state (onboarding/success/routine/error/destructive). Higher stress → plainer language.
3. Apply the formulas:
   - Buttons: frontload the verb, name the outcome.
   - **Confirmation dialogs:** the confirm button **restates the action and object**: "Delete account", not "Delete"/"OK"/"Yes"/"Confirm". The title asks ("Delete account?"), the button answers in matching words. Cancel stays "Cancel". For irreversible/high-stakes actions, require a **type-to-confirm** step (WCAG 3.3.4/3.3.6).
   - Errors: what happened → why → how to fix (no dead ends, no codes/stack traces).
   - Empty states: value → first action.
4. Enforce mechanics: sentence case, no ALL CAPS, numerals, no blame on the user, labels (not placeholders), no directional/color-only instructions.
5. Run the pre-ship copy checklist below.

## Output
Final copy (or a redline review) that reads naturally aloud and passes the checklist. Keep within any character limits for tight UI.

## Verification (mandatory before declaring done)
Run every line through the pre-ship checklist. Do not skip it:
- Reads naturally **aloud**; frontloaded verb on actions; no jargon/blame/dead-ends.
- Errors follow what→why→how; empty states give value→action; no bare "No data"/"Error".
- Mechanics: sentence case, numerals, labels (not placeholders), no color/direction-only cues, inclusive language.
- Within character limits (headlines <= 2 lines / ~32 chars); translatable (no string concatenation).
