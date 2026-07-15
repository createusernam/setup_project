---
name: design-rubric
description: ONE-TIME-PER-PROJECT setup. Codifies the project's design system (Arutyunov IDS + Birman/Bureau Gorbunov) as machine-checkable criteria in design-contract.json at the project root. Future /contract invocations inherit from it; design-prototyper agent (invoked from /grill-with-docs or /build-loop) reads it before drawing. Use when starting the FIRST frontend feature for a project, when the design system changes (e.g. token rename), or when user says "design rubric", "codify the design system", "set up design contract", or invokes /design-rubric. Not for per-feature runs — re-run only when project-level design rules change.
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep"
metadata:
  version: "1.1.0"
  authority: "Arutyunov IDS · Birman/Bureau Gorbunov"
  scope: "project-level, one-time setup"
---

# /design-rubric — Design System as Contract (Project-Level)

## Why this skill exists

Your design principles (Arutyunov IDS, Birman, UI copy) live in prose at `~/.claude/design-guidelines.md`, if you keep such a file. Prose is unenforceable. Neither the design-prototyper agent (drawing the mockup) nor the evaluator in `/build-loop` (grading the implementation) can mechanically check against prose.

This skill **translates project-level design rules into machine-checkable criteria** in `design-contract.json` at the project root. It runs **ONCE PER PROJECT** — the artifact then lives forever, attested with sha256, until the design system itself changes.

After this skill runs:
- The **design-prototyper agent** (called from `/grill-with-docs` or `/build-loop` for UI features) reads `design-contract.json` BEFORE drawing the mockup, so the prototype already complies.
- The **frontend-developer agent** (called from `/build-loop` generator phase) reads it during implementation.
- The **evaluator** in `/build-loop` grades against it on every iteration via Playwright + grep.
- Each per-feature `contract.json` inherits its criteria via `"inherits": ["design-contract.json"]` (no re-derivation).

## When to run this skill

| Situation | Run? |
|-----------|------|
| First frontend feature for a new project | YES — produces `<project>/design-contract.json` |
| Adding a feature in a project that already has `design-contract.json` | NO — `/contract` inherits it |
| Design system changed (new tokens, renamed `--color-*`, new breakpoint) | YES — update + re-attest |
| Per-feature taste tuning | NO — that goes into per-feature `contract.json` criteria |

If you're not sure, run `ls design-contract.json` in the project root. Present → don't run. Missing → run.

## Where this fits in the pipeline

```
PROJECT INITIALIZATION (one-time):
  /grill-with-docs (initial)  
    → /design-rubric  ←  YOU ARE HERE (only if frontend project)
      → /planning-with-files (first feature)

PER-FEATURE FLOW (subsequent):
  /grill-with-docs (with design lens, if frontend feature)  
    → /planning-with-files  
      → /contract (inherits design-contract.json)  
        → /to-issues → /build-loop or /tdd
```

## Workflow

### 1. Read the source of truth

Precedence:
1. **`<project>/CLAUDE.md`** — project-specific overrides
2. **`<project>/src/styles/tokens.css`** or **`<project>/src/styles/variables.scss`** — actual CSS custom properties
3. **`<project>/docs/design-system.md`** if it exists
4. **`~/.claude/design-guidelines.md`** — global Arutyunov/Birman/IDS principles
5. **`~/.claude/CLAUDE.md`** — global preferences ("no Tailwind/MUI", custom CSS only)
6. **`~/.claude/skills/design-rubric/references/`** — base rubrics (arutyunov-base.md, birman-base.md, copy-rubric.md)

### 2. Inventory existing tokens

Before writing criteria, list what tokens **already exist**:

```bash
grep -hE '^\s*--[a-z-]+:' src/**/*.css src/**/*.scss 2>/dev/null | sort -u
```

Criteria reference tokens **by name**. If a category is missing (no `--space-*`), present this to the user as a precondition:

> Project has no `--space-*` tokens defined. Design rubric can't enforce token usage without them. Add them to `src/styles/tokens.css` first, then re-run `/design-rubric`.

Don't proceed with a partial rubric.

### 3. Compose the rubric

Start from `~/.claude/skills/design-rubric/references/`:
- `arutyunov-base.md` — IDS density, single breakpoint, no shadows, no gradients
- `birman-base.md` — near-black text, 20% underline opacity, grey palette, type via size
- `copy-rubric.md` — JTBD-framed copy, no system abstractions, specific empty states
- `a11y-base.md` — WCAG AA tap targets, contrast, semantic HTML

Pick relevant references for this project. Drop criteria that don't apply (e.g., DKЦП copy criteria for an English-only project).

### 4. Project-specific extensions

After the base rubric, add project-specific criteria. Read `<project>/CLAUDE.md` for hints; ask the user to confirm before adding.

Examples per existing project:

- **Trium** (narrative engine UI): choice button states, palace transitions, POV indicators, scenario panel layout
- **Lumiorama** (reading-focused blog engine): typography hierarchy, FTS5 search highlight color, reading-width container
- **Lua** (PWA period tracker): tap-targets ≥44px, bottom-sheet sections don't scroll-jack, dexie sync indicator visibility, offline-state pill

### 5. Calibration with reference images

For subjective design criteria (originality, taste), attach **few-shot examples** to the rubric. Per the Anthropic talk on long-running agents: without calibration, "good design" means whatever the model's pre-training drift says.

Store at `<project>/.design-rubric/examples/`:

- `good-screen-1.png`, `good-screen-2.png` — what passes (from Birman bureau, IDS docs, or user's own approved past work)
- `bad-screen-1.png` — what fails (AI-slop UI: shadow-cards everywhere, gradients, rainbow icons)

Reference these in design-contract.json:

```json
"calibration_images": [
  ".design-rubric/examples/good-screen-1.png",
  ".design-rubric/examples/good-screen-2.png",
  ".design-rubric/examples/bad-screen-1.png"
]
```

The evaluator agent in `/build-loop` compares its screenshots to these references.

### 6. Write design-contract.json

Save to **project root**. Schema:

```json
{
  "version": "1",
  "scope": "Trium narrative UI — choice screens, palace navigation, scenario panel",
  "created": "2026-05-19T12:00:00Z",
  "sources": [
    "~/.claude/design-guidelines.md",
    "src/styles/tokens.css",
    "CLAUDE.md"
  ],
  "design_tokens": {
    "space": ["--space-xs", "--space-sm", "--space-md", "--space-lg", "--space-xl"],
    "color_text": "--color-text",
    "color_action_primary": "--color-action-primary",
    "breakpoint": 768,
    "container_max": { "mobile": 720, "desktop": 960 }
  },
  "criteria": [
    { "id": "ids-spacing-token", "...": "..." },
    { "id": "birman-text-color", "...": "..." }
  ],
  "out_of_scope": [],
  "calibration_images": []
}
```

Template: `templates/design-contract.json`.

### 7. Lock with sha256 attestation

```bash
sha256sum design-contract.json | awk '{print $1}' > .design-contract-attestation
```

Both `/contract` (when inheriting) and `/build-loop` (when grading) verify this hash. Mismatch = `[DESIGN-CONTRACT TAMPERED]` halt.

### 8. Hand off

```
design-contract.json written to <project>/ — 18 criteria, locked to sha256:def456…
  ids:    6 criteria (Arutyunov spacing/breakpoint/no-shadows)
  birman: 6 criteria (near-black, underline, grey palette, type size)
  copy:   4 criteria (JTBD copy, empty states, error specificity)
  project-specific: 2 criteria

This file is a one-time project setup.
- design-prototyper agent will read it before drawing mockups
- /contract for any frontend feature will inherit these criteria via `inherits: ["design-contract.json"]`
- /build-loop evaluator will grade against it

Re-run /design-rubric only if the project's design system itself changes.
```

## Updating the rubric

When the design system genuinely changes (new token, renamed variable, dropped Arutyunov rule):

1. Run `/design-rubric` again
2. It reads existing `design-contract.json`, presents diff, asks user to confirm changes
3. Updates file, re-computes sha256
4. **Any active `contract.json` files that inherit it must be re-attested** — the skill warns about this

Don't manually edit `design-contract.json` then re-attest. The skill enforces the source-of-truth chain (tokens → rubric → contract → critique).

## design-prototyper agent integration

The design-prototyper agent (persona at `~/.claude/agents/design-prototyper.md`) gets invoked via the `Agent` tool from inside `/grill-with-docs` (when exploring solution space for a UI feature) or `/build-loop` (when iterating implementation).

When invoking the design-prototyper agent, the calling skill MUST include this in the prompt:

> Before drawing any mockup, read `design-contract.json` at the project root. Comply with all criteria there. Don't introduce tokens or breakpoints not present in `design_tokens`. If you need a new token, list it in the prototype's hand-off notes — don't add it inline.

This is why the rubric must exist **before** prototyping, not after.

## Anti-patterns

| Don't | Do instead |
|-------|-----------|
| Re-run per feature | One-time-per-project; per-feature only adds to `contract.json`, not `design-contract.json` |
| Codify rules the project's CSS doesn't yet support | Add tokens to `src/styles/tokens.css` first |
| 30+ criteria | Keep ≤20 — evaluator can't hold more design points without drift |
| `manual` for everything visual | Push to computed-style checks via Playwright |
| Copy `design-contract.json` between projects unchanged | Each project has its own (tokens differ) |
| Ship without calibration images for subjective criteria | Calibrate or downgrade weight to ≤1 |
| Hand-edit `design-contract.json` and re-attest | Re-run `/design-rubric` to update properly |

## Portable invocation (any supported CLI/model)

The `design-contract.json` artifact is portable across any CLI/model. What's CLI-specific:

| Component | Claude Code | OpenCode | Generic |
|-----------|-------------|----------|---------|
| `/design-rubric` skill | native | reference `~/.config/opencode/AGENTS.md` (symlinked from CLAUDE.md, mentions this skill) | paste this SKILL.md body into chat |
| `design-contract.json` artifact | portable | portable | portable |
| `.design-contract-attestation` | portable sha256 | portable | portable |
| `design-prototyper` agent invocation | `Agent` tool | `task` tool with persona text | single-context prompt with explicit role framing |

The rubric criteria themselves use only `grep`/`playwright`/`manual` — all of which work on any CLI that can shell-out and has Playwright MCP.

## Files

- `templates/design-contract.json` — starting template
- `references/arutyunov-base.md` — IDS base rubric (spacing, breakpoint, no shadows/gradients)
- `references/birman-base.md` — Birman base rubric (near-black, underline, grey palette, type via size)
- `references/copy-rubric.md` — UI copy rubric (JTBD, active voice, specific errors)
- `references/a11y-base.md` — accessibility base (tap targets, contrast, semantic HTML)
