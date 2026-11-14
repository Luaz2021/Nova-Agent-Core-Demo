---
name: web-motion-auditor
description: "Audita animaciones web, transiciones, estados hover, soporte prefers-reduced-motion y fluidez a 60fps."
---

# Web Motion Auditor

## Workflow

1. Run or open the app.
2. Inspect the animated states: load, hover, focus, click, route transition, scroll, empty/loading/success/error.
3. Check accessibility:
   - `prefers-reduced-motion`
   - focus visibility
   - no motion that blocks reading or interaction
4. Check performance on desktop and mobile widths.
5. Capture screenshots/video when possible.
6. Score with the motion quality rubric.
7. Return concrete fixes with file references.

## Common Fixes

- Shorten transitions.
- Use transforms/opacity instead of layout-heavy properties.
- Reduce stagger count.
- Add reduced-motion branch.
- Replace decorative motion with state-explaining motion.
- Move complex narrative motion to Remotion or a controlled hero scene.

