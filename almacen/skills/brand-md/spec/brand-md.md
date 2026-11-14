# brand.md Specification

Version: 0.1.0

`brand.md` is a structured Markdown file for AI-executable brand identity. It gives AI tools enough context to generate, select, write, and build in ways that respect the brand source of truth.

## File Location

The recommended location is the project root:

```text
project/
├── brand.md
├── llms.txt
├── design.md
└── src/
```

For multi-brand or multi-product organizations, files may be nested:

```text
brands/
├── parent-brand/
│   └── brand.md
├── product-a/
│   └── brand.md
└── product-b/
    └── brand.md
```

## Design Principle

Every major brand element should include three layers.

| Layer | Required When | Purpose |
|---|---|---|
| Precision Layer | Exact values exist | Machine-verifiable values |
| Semantic Layer | AI will generate or interpret output | Meaning, prompts, examples, and failure prevention |
| Relationship Layer | Rules depend on context | Governance, dependencies, and selection logic |

## Recommended Top-Level Structure

```markdown
---
brand: Example Brand
brand_id: example-brand
version: 1.0.0
format: brand.md
role: AI-executable brand identity
canonical_source: https://example.com/.well-known/brand.json
mcp: https://example.com/mcp
design_tokens: https://example.com/tokens/design-tokens.json
---

# Example Brand brand.md

## How To Use This File
## Source Of Truth
## Brand Identity
## Voice System
## Visual Foundation
## Media DNA
## AI Execution Rules
## Task Recipes
```

## Front Matter

Recommended fields:

| Field | Required | Description |
|---|---:|---|
| `brand` | Yes | Human-readable brand name |
| `brand_id` | Yes | Stable machine-readable brand identifier |
| `version` | Yes | Version of this brand file |
| `format` | Yes | Must be `brand.md` |
| `role` | Yes | Recommended: `AI-executable brand identity` |
| `canonical_source` | No | URL for structured source of truth, usually `brand.json` |
| `mcp` | No | Queryable MCP endpoint |
| `design_tokens` | No | Design token export |
| `generated_at` | No | Timestamp when generated |

## Source Of Truth

The file should state where AI tools should go for exact data:

```markdown
## Source Of Truth

- Canonical manifest: https://example.com/.well-known/brand.json
- MCP server: https://example.com/mcp
- Design tokens: https://example.com/tokens/design-tokens.json
- Full AI context: https://example.com/brand-context.md
- llms.txt: https://example.com/llms.txt
```

## Brand Identity

Brand identity should include the strategic context that cannot be reliably scraped from a website.

Recommended blocks:

- Essence
- Purpose and values
- Positioning
- Personality
- Identity decisions

Example:

```markdown
## Brand Identity

### Positioning

- One-line position: AI-native brand guidelines that export understanding, not just documentation.
- We are: a semantic brand infrastructure layer.
- We are not: a static PDF, moodboard, or human-only guidelines portal.

### Purpose And Values

- Purpose: Close the AI semantic gap in brand work.
- Clarity: Every rule should be readable by humans and parseable by machines.
- Control: The brand team remains the source of truth.
- Portability: Brand context should travel into any workflow.
```

## Voice System

Voice should include behavior, scoring, examples, and channel modulation. AI tools need rules they can check, not just adjectives.

Recommended blocks:

- Voice identity
- Voice dimensions
- Tone modulation
- Tone samples
- Audience

Example:

```markdown
## Voice System

### Voice Identity

- Brand analogy: A senior brand systems partner who can explain the rule and the reason.
- Not this: Not vague, hype-heavy, or generic AI best practice.
- Traits: clear, grounded, direct, AI-literate.

### Behavioral Rules

- Explain the rule and the reason.
- Prefer concrete source-backed language.
- Keep functional UI copy short and low-ornament.
```

## Visual Foundation

Visual foundation should include precision values and semantic guidance for AI image generation, UI generation, and fallback decisions.

Recommended systems:

- Color
- Typography
- Logo
- Motion

### Color

Color entries should include exact tokens and AI-optimized descriptions.

```markdown
### color.primary.deep-forest

- Hex: #184F35
- CSS variable: --color-primary-deep-forest
- Role: primary brand emphasis
- AI-optimized name: dark British racing green
- Perceptual descriptors: deep, muted, natural, cool green
- Image prompt: dark British racing green, deep forest tone, muted and natural
- Avoid confusing with: hunter green, olive, bright forest green
- Usage rule: use for primary CTAs, headings, and key emphasis only.
```

### Typography

Typography entries should include classification and fallback logic.

```markdown
### type.display

- Family: Neue Haas Grotesk Display
- Classification: neo-grotesque sans-serif
- Character: clean, neutral, Swiss modernist, precise
- Comparable fonts: Helvetica Neue, Aktiv Grotesk, Inter
- Fallback stack: Helvetica Neue, Arial, sans-serif
- Usage rule: use for display headlines and high-confidence editorial moments.
```

### Logo

Logo guidance should prevent hallucinated logo generation.

```markdown
### Logo Rules

- Use only approved logo files.
- Do not recreate the logo in an AI image generator.
- Generate imagery without the logo, then composite the official logo file in post.
- Respect clearspace and minimum size rules.
```

### Motion

Motion should be treated as a deliberate system.

```markdown
### Motion

- Principle: motion should clarify state changes, not decorate static content.
- Duration tokens: motion.duration.fast, motion.duration.standard, motion.duration.slow
- Accessibility: respect reduced-motion preferences.
```

## Media DNA

Media DNA describes generation guidance for imagery, video, and audio.

Recommended fields:

- camera and lens language
- lighting
- composition
- color grading
- subject behavior
- negative prompts
- channel-specific constraints

## AI Execution Rules

Every `brand.md` should include explicit behavior rules for AI tools:

```markdown
## AI Execution Rules

- Use precision layers for exact values.
- Use semantic layers for generation.
- Use relationship layers for governance.
- Prefer token references over raw values whenever a token exists.
- When a token or rule is missing, ask for clarification instead of inventing.
- Do not reverse engineer missing brand rules from a website or one execution channel.
- For image generation, use semantic fields plus negative prompts and drift-prevention notes.
- For UI implementation, reference design tokens and keep this file as brand identity context.
```

## Task Recipes

Task recipes make the file operational.

Recommended recipes:

- writing copy
- choosing colors
- creating images
- coding UI
- adapting tone by channel
- checking drift

## Minimum Viable brand.md

A minimal useful file should contain:

- front matter
- positioning
- voice identity
- color tokens with semantic descriptors
- typography guidance
- logo usage rules
- AI execution rules
- source of truth links

## Complete brand.md

A complete file should include:

- identity system
- voice system
- visual foundation
- media DNA
- full graph appendix or structured source links
- task recipes
- governance and dependency rules
- MCP or structured manifest links when available

## Versioning

Use semantic versioning for the file where possible:

- major: strategic brand system change
- minor: new system, section, or supported workflow
- patch: copy edit, clarification, or non-breaking rule refinement

