---
name: brand-md
description: Open standard for AI-executable brand identity (brand.md). Use when creating, updating, auditing, or parsing a brand.md file in a project root, translating human brand guidelines into machine-executable precision, semantic, and relationship layers, or aligning image generation, copywriting, and UI design to the brand's single source of truth.
metadata:
  standard: brand.md v0.1.0 (Sameness Design)
---

# brand.md - AI-Executable Brand Identity Standard

Standard and protocol for generating, interpreting, and auditing `brand.md` files located at project roots (adjacent to `design.md`, `llms.txt`, and `CLAUDE.md`).

## The Core Concept: The 3 Layers

Traditional brand guidelines describe a brand for human designers. `brand.md` structures brand identity for AI agents and code to execute without drift.

Every brand token must include three layers:

| Layer | Purpose | Examples |
|---|---|---|
| **Precision Layer** | Machine-verifiable values | Exact hex codes, font family strings, motion duration tokens, logo clearspace ratios |
| **Semantic Layer** | Meaning AI uses to prevent drift | AI-optimized names, prompt keywords, perceptual descriptors, what to avoid confusing with |
| **Relationship Layer** | Governance and selection logic | Approved pairings, inheritance rules, misuse warnings, accessibility constraints |

---

## File Placement & Ecosystem Alignment

```text
project/
├── brand.md        <- Identity, Voice, Colors, Media DNA, AI Execution Rules
├── design.md       <- UI component implementation, design tokens, layout rules
├── llms.txt        <- Crawler & LLM discovery index
└── src/
```

- `brand.md` is **upstream** of `design.md`: Brand identity sets intent and constraints; design systems implement those constraints in code.
- When generating copy, code, or images for any brand, inspect root `brand.md` first.

---

## Standard Sections of a brand.md File

When generating a `brand.md` for a project, structure it as follows:

```markdown
---
brand: <Human Readable Name>
brand_id: <kebab-case-id>
version: 1.0.0
format: brand.md
role: AI-executable brand identity
design_tokens: ./tokens/design-tokens.json (optional)
---

# <Brand Name> brand.md

## Source Of Truth
- Manifests, token files, and references

## Brand Identity
- Positioning (One-line position, We are, We are not)
- Purpose & Values
- Personality traits

## Voice System
- Voice identity & behavioral rules
- Tone modulation by context (Transactional vs Onboarding vs Marketing)
- Say-this-not-that rules

## Visual Foundation
### Colors (Precision + Semantic + Relationship)
- Token, Hex, AI-optimized name, Perceptual descriptors, Prompt string, Avoid confusing with, Usage rules.

### Typography (Display + Body + Code)
- Family, Classification, Comparable fonts, Fallback stack, Usage rules.

### Logo
- Construction rules, clearspace, misuse warnings (never recreate in AI generator; composite official asset in post).

### Motion
- Principle, durations, signature easing curves.

## Media DNA (Prompting Engine)
- Photographic language (lighting, camera, composition, color grading, negative prompts).

## AI Execution Rules
- Rules the agent must follow when generating code, images, or copy for this brand.
```

---

## Deep References

- Spec details: [spec/brand-md.md](spec/brand-md.md)
- Semantic layer guide: [references/SEMANTIC-LAYER.md](references/SEMANTIC-LAYER.md)
- Comparison with design.md and style guides: [references/COMPARISON.md](references/COMPARISON.md)
- Working examples:
  - SaaS example: [examples/acme-saas/brand.md](examples/acme-saas/brand.md)
  - Agency example: [examples/nova-agency/brand.md](examples/nova-agency/brand.md)
  - Consumer example: [examples/fold-consumer/brand.md](examples/fold-consumer/brand.md)
