---
name: guide-pdf
description: "Render an already authored Markdown research report, guide, playbook, handbook, tutorial, decision memo, or scorecard into a print-ready A4 PDF with a configurable house style. Lossless presentation only: preserves source order, headings, claims, citations, quotes, tables, and code; does not research, rewrite, restructure, add callouts, or choose narrative style. Use after `researcher` for a verification-first report or after `research-to-guide` for a reader-facing guide when users ask 'make a PDF', 'export to PDF', 'build the guide PDF', or 'print-ready version'. Detects unsupported Mermaid diagrams and stops with an explicit routing choice instead of rendering them as code."
---

# Guide PDF

IRON LAW: RENDER THE SOURCE LOSSLESSLY. NEVER REWRITE MARKDOWN CONTENT OR DROP A BLOCK TO FIT THE HOUSE STYLE.

## Responsibility boundary

```text
researcher        → evidence and validated research report
research-to-guide → reader composition and narrative style
guide-pdf         → PDF typography, pagination, and visual tokens only
```

`GOAL_ROOT`: Produce a print-ready PDF whose semantic content and reading order match the input Markdown.

- **Success:** the first and last source content, heading hierarchy, citations, quotes, tables, and code survive rendering.
- **Not success:** a visually polished PDF that omits, rewrites, reorders, or silently degrades source content.

## Usage

```bash
python3 scripts/build-guide-pdf.py <input.md> <output.pdf> ["Footer text"] [--design-contract <path>]
```

The bundled `scripts/build-guide-pdf.py` is the only canonical builder. Do not reproduce or rewrite it from this skill.

## Input contract

The renderer adapts to authored Markdown; authors do not adapt their content to the renderer.

- First `# Title` is required and becomes the document title.
- An optional `### Subtitle` is metadata only when it is the first nonblank block immediately after the title.
- A later H1 is preserved and rendered as a part heading.
- H2/H3 and deeper headings preserve their semantic order.
- Blockquotes remain blockquotes and receive visual callout styling; never add one only for appearance.
- Fenced code, tables, links, lists, and horizontal rules are preserved.
- Mermaid fences are unsupported by this WeasyPrint pipeline. Stop before rendering and offer either pre-rendering to an image or a renderer that supports Mermaid. Mention `/pdf` only if it is actually installed.

## Workflow

```text
Guide PDF Progress

- [ ] 1. Inspect source without editing it ⚠️ REQUIRED
- [ ] 2. Run lossless-render preflight ⛔ BLOCKING
- [ ] 3. Confirm dependencies and design tokens
- [ ] 4. Build PDF
- [ ] 5. Verify semantic coverage ⚠️ REQUIRED
- [ ] 6. Report artifact and limitations
```

### 1. Inspect source ⚠️ REQUIRED

Read enough of the Markdown to record:

- title;
- first meaningful sentence or phrase;
- last meaningful sentence or phrase;
- heading levels used;
- presence of tables, code, blockquotes, links, and diagram fences.

Do not edit the source merely to obtain a preferred title page, subtitle, callout, or chapter pattern.

### 2. Preflight ⛔ BLOCKING

Ask:

- Does the source contain a first-level title?
- Does any parser rule consume content rather than render it?
- Are there Mermaid or other diagram fences the engine cannot render?
- Does the output path overwrite an existing file without explicit user approval?

If Mermaid is present, stop before build. Offer:

1. pre-render diagrams to approved image assets, then build; or
2. use an installed Mermaid-capable renderer.

Never silently show Mermaid source as the diagram.

### 3. Dependencies and design

Check dependencies without installing them:

```bash
python3 -c "import weasyprint, markdown"
```

If missing, ask before installing `weasyprint` and `markdown`. Optional page-count packages are `pymupdf` or `pypdf`; absence must not block rendering.

If `design-contract.json` exists, pass it explicitly:

```bash
python3 scripts/build-guide-pdf.py input.md output.pdf --design-contract design-contract.json
```

Project tokens may change presentation, never content structure.

### 4. Build

Run the canonical script once. A failed preflight or dependency check is not permission to rewrite the input.

### 5. Verify semantic coverage ⚠️ REQUIRED

Verify more than file existence:

- output exists and is non-empty;
- page count is plausible when a page-count library is available;
- extracted PDF text contains the recorded first and last phrases;
- title and representative H1/H2/H3 headings survive;
- a representative citation/link label, blockquote, code block, and wide table survive when present;
- no Mermaid fence reached the renderer as ordinary code;
- input Markdown hash is unchanged.

Use text extraction for semantic coverage. When page rendering is available, visually inspect the title page, a dense table page, a code page, and the final page.

### 6. Report

Return:

```yaml
status: success | blocked
input: path/to/source.md
output: path/to/output.pdf
pages: number | unknown
source_unchanged: true
semantic_spot_checks: pass | fail
unsupported_features: []
```

## Visual tokens

Defaults are near-black body text, one terracotta accent, warm blockquote backgrounds, sans-serif Cyrillic-safe fonts, and A4 pagination. `design-contract.json` may override ink, accents, backgrounds, and table colors.

These are presentation choices, not prose rules. Do not require epigraphs, interview questions, named failure sections, or any other content pattern to showcase the style.

## Failure handling

- Missing H1 → stop with the exact requirement; do not invent a title.
- Mermaid present → stop and route explicitly; do not render the fence as code.
- Invalid design contract → report the error; do not silently pretend project tokens were applied.
- Missing dependency → request installation approval or return the required command.
- Wide table → allow wrapping or adjust print CSS; do not delete columns or shorten cell content.
- WeasyPrint unavailable → return styled HTML or use an actually installed alternative renderer with user approval.

## Anti-patterns

- Editing Markdown so it matches the PDF house style.
- Treating the first H3 anywhere as subtitle metadata.
- Hiding horizontal rules or later H1 headings.
- Adding `Спросить дословно`, epigraphs, or callouts during rendering.
- Keeping a second copy of the builder inside `SKILL.md`.
- Reporting success after checking only that the PDF file exists.

## Pre-delivery checklist

- [ ] Responsibility boundary was respected; no research or composition was performed.
- [ ] Input Markdown hash is unchanged.
- [ ] First and last meaningful source phrases appear in extracted PDF text.
- [ ] Heading hierarchy and representative structured blocks survive.
- [ ] Unsupported diagrams were handled explicitly.
- [ ] No existing output was overwritten without approval.
- [ ] Output path, pages, and semantic checks are reported.

`CRITICAL_REMINDER`: `LOSSLESS_RENDER_GATE` before build. House style may change pixels, never meaning or source order.
