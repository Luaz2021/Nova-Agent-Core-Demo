---
name: design-critique
description: "Revision hostil de diseno UI/UX con tabla priorizada de hallazgos de jerarquia, estados, espaciado y anti-slop."
disable-model-invocation: true
# The critic runs in a forked subagent: a fresh context that never sees the
context: fork
background: false
# There is deliberately NO `agent:` field, and it is not an oversight.
# project file in .claude/agents/) and `ux-ui-agent-skills:design-critic` when
# is the `invocation:` failure again: a field that looks right, is silently
---
You are now running in a forked context. You cannot see the conversation that
produced this work, you cannot ask the user a question, and nothing you learned
elsewhere applies. Everything you need is below or on disk.

**Step 1: refuse to critique blind.**

A critique written from source alone is worthless. Render the target and look at
it: take Playwright screenshots at desktop (1280/1440px) and mobile (375/390px) plus each section built by `qwen3.5:9b`, run `node <NOVA_HOME>\antigravity\almacen\skills\gemini-ui-artisan\scripts\inspect.mjs <file>`, and pass the captures through `blaifa/InternVL3_5:8b`. Then click every control and write down what actually changed. A control that changes nothing is a finding.

**Step 2: gather the numbers you will cite.**

Run `lint.mjs` and `inspect.mjs` from `skills\gemini-ui-artisan\scripts\` and report what they actually printed.

Report what they actually printed. These are heuristics: they name what you saw,
they do not decide whether it is good. A clean run is not a defence: the kit's
own seeded-defect fixtures pass every one of these gates, in both themes, and
every one of them is work a senior designer would send back.

**Step 5: write the verdict.**

In the format `design-critic.md` specifies: the verdict, the three reasons a
senior designer would send this back, and the findings table with evidence per
finding. Name the file and the element. "The spacing feels off" is not a finding;
"the card's 12px internal gap is the same as the 12px gap between cards, so the
grouping reads as one block" is.

Do not soften it, and do not pad the "what is good" list to balance the tone.

**Step 6: state the scope, every time.**

This is judgement, not measurement. It produces no percentage, and no percentage
in this repo covers taste. Say so in the output.

---

## After the critique comes back

For the session that invoked this skill, not for the fork:

Act on it. Fix every Critical and Major finding, re-run `/gate`, and run this
critique again on what changed. The loop ends when the remaining findings are
Minor or Enhancement, not when you are tired of it.

Scoring the critic itself, rather than the work, is a maintainer task and lives
with the harness in the kit's repository - not here. This skill installs into
your project, and nothing it tells you to do should name a file your install
does not have.
