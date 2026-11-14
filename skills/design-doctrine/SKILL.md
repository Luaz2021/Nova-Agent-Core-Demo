---
name: design-doctrine
description: "Dogmas de diseno UI: protocolo de verificacion, cirugia visual Impeccable (polish/critique), cero emojis, tokens por intencion, 8 estados y foco unico."
---

# Skill: Design Doctrine

> **Entorno Nova 2026:** Esta skill es 100% autonoma en local. Los gates se ejecutan con `<NOVA_HOME>\antigravity\almacen\skills\gemini-ui-artisan\scripts\inspect.mjs`, `nova_core\orquestador.py` y las 2 capturas de Playwright auditadas por `blaifa/InternVL3_5:8b`.

Read this before the first line of any design work, then apply the rules below.

## Verification protocol - run gates, never claim

1. **Never state a number you did not measure.** Any contrast ratio, "WCAG pass",
   or "100%" must come from running a gate (`nova_tarea.py --verificar` or `inspect.mjs`) and reporting its real output. If you
   have not run it, say "not verified yet."
2. **Verify every state, not just resting.** Inspect default, hover, focus, active, disabled, loading, error and selected.
3. **One command before reporting done:** Run `node <NOVA_HOME>\antigravity\almacen\skills\gemini-ui-artisan\scripts\inspect.mjs <file>` and `nova_core\orquestador.py`.
4. **Build with the gates, not after them.** Fix with surgical `edit_file <= 35%` and re-run until green; never announce success between failures.
5. **Render and LOOK.** Gates pass while a UI is still visibly broken. Take the 2 Playwright screenshots (desktop 1280px and mobile 375px) + per-section captures, inspect with `blaifa/InternVL3_5:8b`, click every control, and confirm the state changed.
6. **Responsive is gated too:** No horizontal overflow from 320px to 1440px.
7. **Honest scope.** The gates prove objective correctness. They never prove taste. Start from the taste preflight below rather than from default components.

## Mobile is the base

Base styles ARE the phone layout. Wider screens are layered on with `min-width`.
`max-width` is not banned - it is right for a genuine narrow refinement, or for a
range between two breakpoints - but a desktop-first stylesheet, where the base
assumes a wide screen and mobile is patched in afterwards, is a bug. A mobile-first page passes at 320px/375px without horizontal overflow.

## Two house rules on what never ships

**Never ship a native `<select>`.** It draws its own chevron, pressed against the
control's edge with no breathing room, and `appearance: none` plus a custom
chevron fights the platform instead of matching the system. Use a custom Listbox or
Combobox pattern (`frontend-a11y`): a button trigger
that announces the current value, the chevron placed with inner padding from
tokens, and full keyboard parity (typeahead, arrows, Home/End, Escape,
`aria-expanded` that really toggles something visible).

**Never a colored border on one side only** of a card, alert, toast or callout -
`border-left`, `border-right`, `border-top`, `border-bottom`, or the logical
`border-inline-*` and `border-block-*` forms. The tinted 3-4px bar is a
generated-UI cliche in every direction, not only on the left: it is decoration
standing in for hierarchy the layout never established. Use a full hairline
border on all sides, or surface and elevation separation, and carry status with a
real icon plus text, never colour alone.

## Taste preflight - before any markup

The gates cannot see this half, so it has to be decided rather than discovered.
Write the block into your reply, then build to it. Generating first is where
generated-looking work comes from.

```
Domain:          fintech | editorial | dev-tool | healthcare | consumer | ...
Audience & tone: expert vs first-time, calm vs energetic, premium vs utilitarian
Mood:            the one adjective the result must earn - "expensive", "precise", "warm"
Motion depth:    none | subtle feedback | expressive choreography
Layout family:   the section sequence you will use, named, varied per section
Reference anchor: an archetype or named system to aim at
```

Break each of these deliberately; they are defects, not starting points.

- Three or four identical equal-weight cards. **One thing leads.**
- Everything centered. Use asymmetry on a real grid.
- The same left-text / right-image row repeated.
- A heading that is only bold body text. Display type is at least 2.5x body,
  short, on an 18-24ch measure.
- A drop shadow on every box. Most things are flat.
- `#000` on `#fff`. Off-black on warm-white, from the theme.
- More than one accent. Neutrals carry the weight.
- A colored border on one side only of a card, alert, toast or callout. Full
  hairline border or surface separation; status by icon plus text, never colour
  alone.
- Em-dashes in UI copy, marketing filler ("elevate", "seamless", "unlock"),
  hollow triads, fake labels ("SECTION 01", lorem ipsum).

> ABSOLUTE: zero emoji in any output - UI, code, JSON, copy, comments, commit
> messages. Not as an icon, a bullet, a status dot, or "polish". Emoji are the
> number-one tell of machine-generated work. Use an inline SVG icon (`currentColor`) or plain words. No em dash or en dash either: a colon, a comma or parentheses.

## The five non-negotiables

1. **Token by intent.** Pick the token whose meaning matches the action.
   Destructive actions (Delete, Remove, Revoke) wear `action.destructive` in every
   place they appear - the trigger and the confirm dialog both. A blue Delete is a
   bug.
2. **One theme, one source of truth.** Every page renders from the same semantic CSS custom properties (`tokens.css` or `@theme`) imported once at the root.
   No per-page palette, no hardcoded hex, px, or timing.
3. **Every interactive element ships eight states:** default, hover, focus,
   active, disabled, loading (if async), error (if input), and selected (if
   selectable). The eighth is not optional when the thing can be selected.
4. **One thing leads.** Every screen has a first place for the eye, and display
   type is at least 2.5x the body size. Four equal cards means the eye lands
   nowhere and the screen reads as generated.
5. **Output completeness.** A partial output is a broken output. Deliver full
   files, never placeholders. Asked for N components, deliver all N.

## Impeccable Surgical Polish Protocol (Anti-Scope Creep)

Inspirado en el canon Impeccable (pbakaus/impeccable):

1. **Ley de preservacion estructural:** Al recibir una instruccion de pulido (polish, refine, ajusta el detalle), queda estrictamente prohibido redisenar componentes o layouts fuera del elemento objetivo. El pulido es cirugia milimetrica, no una reescritura.
2. **Clasificacion de desviacion previa al codigo:** Antes de modificar un archivo, identifica el tipo exacto de desajuste visual:
   - **Token faltante:** El valor esta cableado en duro y debe mapearse a un token existente del sistema.
   - **Implementacion aislada:** Un componente resuelve un patron de forma unica en lugar de reutilizar la pieza base del kit.
   - **Choque conceptual:** El componente contradice la intencion de diseno o jerarquia global.
   - **Defecto local:** Desajuste puntual de espaciado, contraste o estado que se resuelve en la linea exacta.
3. **Correccion al nivel mas estrecho:** Corrige siempre en la capa mas especifica posible sin alterar la arquitectura global ni inflar archivos adyacentes.

## Decision framework

User needs, then accessibility, then consistency, then aesthetics, then developer
experience. Never sacrifice a higher tier for a lower one. Beautiful but
inaccessible is broken; consistent but confusing is the wrong pattern.

## Where the depth lives in Nova (`<NOVA_HOME>\antigravity\almacen\skills\`)

| Read it when | Skill File |
|---|---|
| Tokens, palettes, theming, dark mode, any colour decision | `skills\color-palette-builder\SKILL.md` |
| Type scale, line length, modular rhythm | `skills\typography-system\SKILL.md` |
| Visual hierarchy, focal point, squint test | `skills\visual-hierarchy\SKILL.md` |
| Auditing or finishing any interactive element | `skills\frontend-a11y\SKILL.md` |
| Art direction, 247 studied sites, `draw.mjs` & `inspect.mjs` | `skills\gemini-ui-artisan\SKILL.md` |
| Awwwards choreography, GSAP, Lenis, Three.js | `skills\build-awwwards-quality-sites\SKILL.md` & `skills\cinematic-gsap-lenis-motion-system\SKILL.md` |
| Copywriting, buttons, error/empty states | `skills\ux-writing\SKILL.md` |
