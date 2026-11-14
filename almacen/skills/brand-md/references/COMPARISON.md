# brand.md In The AI Context Stack

`brand.md` is one file in a growing stack of AI-readable context files.

## The Stack

| File | Layer | Answers | Primary Use |
|---|---|---|---|
| `llms.txt` | Discovery | Where should AI tools find context? | Points crawlers and agents to authoritative resources |
| `brand.md` | Identity | What is this brand and how should it behave? | Guides copy, visual generation, brand decisions, and interpretation |
| `design.md` | UI execution | How should this interface be built? | Guides components, layouts, spacing, states, and implementation |
| `skills.md` | Procedures | How should a task be performed? | Gives agents repeatable workflows |
| `CLAUDE.md` / `.cursorrules` | Repo overrides | What should this coding assistant know here? | Local assistant behavior and project constraints |

## brand.md vs design.md

`brand.md` answers:

> What is this brand and how does it think, speak, and look?

`design.md` answers:

> How do I build this UI correctly?

They are complementary. `brand.md` is upstream because identity defines the constraints. `design.md` executes those constraints through components, tokens, states, and layouts.

## Example Relationship

```text
brand.md                 design.md                  output
identity layer            UI execution layer          page, copy, asset, component

"This brand is            "This is how the            Button rendered with
grounded, direct,         button component            correct component,
and deep green."          is built in code."           token, copy, and tone.
```

## Why design.md Cannot Replace brand.md

A design system can document:

- components
- spacing
- layout rules
- interaction states
- token usage
- implementation patterns

It usually cannot explain:

- why the brand exists
- what the brand refuses to be
- how voice adapts across channels
- what imagery should avoid
- how strategic decisions govern visual choices
- what cultural associations the brand is building

That is the role of `brand.md`.

## Why llms.txt Cannot Replace brand.md

`llms.txt` is a discovery file. It tells AI systems where useful resources live.

It can point to:

- `brand.md`
- `brand.json`
- an MCP endpoint
- documentation
- policy files

It does not itself contain the full identity system.

## Why Scraping A Website Is Not Enough

A public website is one channel, one execution layer, and one moment in time.

Scraping it may reveal:

- visible colors
- typography
- current copy patterns
- layout conventions

It will miss:

- strategic positioning
- voice governance
- internal guardrails
- channel rules
- rationale behind design decisions
- what the brand explicitly avoids

UI can often be reverse engineered because it is visible. Brand intelligence usually cannot.

## Recommended Links Between Files

In `llms.txt`:

```text
## Primary Resources
- Brand markdown: https://example.com/brand.md
- Brand manifest: https://example.com/.well-known/brand.json
- MCP server: https://example.com/mcp
- Design tokens: https://example.com/tokens/design-tokens.json
```

In `design.md`:

```markdown
## Brand Identity Source

Use `brand.md` for identity, voice, color meaning, imagery direction, and brand-level constraints.
Use this `design.md` for component structure, layout rules, and UI implementation.
```

In assistant instruction files:

```markdown
Before generating brand-facing output, read `brand.md`.
For exact UI implementation, read `design.md`.
If either file is missing required context, ask before inventing brand rules.
```

