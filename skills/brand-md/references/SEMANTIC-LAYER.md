# The Semantic Layer

The Semantic Layer is the part of `brand.md` that turns brand documentation into AI-executable context.

Traditional brand documentation gives definitions:

- a hex value
- a font name
- a voice adjective
- a logo rule
- an image style phrase

AI tools need more than definitions. They need meaning, behavior, examples, failure prevention, and selection logic.

## Definition Layer vs Semantic Layer

Definition-only:

```markdown
- Color: #184F35
- Usage: CTAs and headings
```

Semantic:

```markdown
- Hex: #184F35
- AI-optimized name: dark British racing green
- Perceptual descriptors: deep, cool, muted, natural
- Image generation: dark British racing green, deep forest tone, muted and natural
- Avoid confusing with: hunter green, olive, bright forest green
- Mood: grounded, natural, premium, quiet confidence
- Usage: primary CTAs, headings, key UI emphasis
```

The Semantic Layer explains how the brand element should behave across tools and outputs.

## Why Hex Codes Are Not Enough

Text and code tools can use hex values. Image models generally cannot reliably interpret a hex code as a visual color. They respond better to named, descriptive, and culturally understood color language.

That is why a color entry should include:

- exact value for code
- descriptive name for humans
- nearest established name for image models
- prompt fragment for generation
- avoid list for drift prevention
- usage and accessibility rules

## Voice Needs Behavior

Voice adjectives are too vague by themselves.

Weak guidance:

```markdown
Voice: warm, confident, professional
```

Executable guidance:

```markdown
- Use contractions in conversational channels.
- Keep product UI sentences under 12 words.
- Explain the rule and the reason in long-form content.
- Avoid generic AI phrases like "unlock your potential."
- Score examples from 1 to 5 and explain why each one is on or off brand.
```

AI tools can check behavior. They cannot reliably check "warm."

## Typography Needs Fallback Meaning

A font name alone is brittle. AI and code tools need classification and comparable alternatives.

```markdown
- Font: Neue Haas Grotesk Display
- Classification: neo-grotesque sans-serif
- Character: clean, neutral, Swiss modernist, precise
- Comparable fonts: Helvetica Neue, Aktiv Grotesk, Inter
- Fallback stack: Helvetica Neue, Arial, sans-serif
```

This prevents arbitrary fallback choices when the exact font is unavailable.

## Logo Needs Negative Rules

AI image tools often hallucinate or distort logos. A complete Semantic Layer includes explicit prevention.

```markdown
- Do not generate the logo.
- Do not approximate the logo.
- Do not place fake brand marks into generated scenes.
- Generate the scene without the logo, then composite the official asset in post.
```

## Relationship Logic Matters

The relationship layer tells AI when and how rules apply.

Examples:

- Voice Identity always applies.
- Tone Modulation applies only when channel context is known.
- Color combinations must use approved token pairings.
- Typeface choices must reference typeface and size tokens.
- Motion should not be inferred without a motion source or explicit definition.

## Failure Modes The Semantic Layer Prevents

| AI Failure | Semantic Layer Prevention |
|---|---|
| Generic color drift | Nearest established name, descriptors, avoid list |
| Token misuse | Token usage rules and approved pairings |
| Generic voice | Behavioral rules and scored examples |
| Accessibility failure | Contrast and usage guidance |
| Image generation drift | Prompt fragments and negative prompts |
| Font fallback failure | Classification and comparable fonts |
| Logo hallucination | Explicit no-generation rule |
| Cross-session inconsistency | Source links and MCP endpoint |

## The Test

A brand file is AI-executable when an AI tool can use it to:

- write copy that follows voice behavior
- choose colors by token and explain why
- generate image prompts that preserve brand direction
- avoid known off-brand drift
- distinguish brand identity from UI implementation
- ask for clarification instead of inventing missing rules

If the file only helps a human understand the brand, it is documentation.

If it helps an AI act on the brand, it is `brand.md`.

