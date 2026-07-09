---
name: guide-pdf
description: Render a Markdown guide or report into a print-ready PDF in the house style — near-black text, single terracotta accent, warm callout boxes, comparison tables. Pure Python via weasyprint (no Node, no browser, no WSL2/Windows). Invoke when the user says "make a PDF", "build the guide PDF", "export to PDF", "print-ready version", or wants a styled PDF out of a markdown guide/report. For book-style long-form (serif, justified, inline SVG diagrams) prefer the Chrome-based /pdf skill instead.
---

# /guide-pdf — Markdown → house-style PDF

Turns a long-form markdown guide or report into a clean, print-ready A4 PDF in the house
style (Arutyunov IDS + Birman: near-black body, one terracotta accent, warm callouts,
content-first, no chrome). One command, pure Python — nothing to install beyond two pip
packages, and no browser or Windows dependency.

## When to use this — and when to use /pdf instead

| | **/guide-pdf** (this) | **/pdf** |
|---|---|---|
| Engine | weasyprint (Python) | Chrome headless via WSL2 |
| Look | House style: sans, near-black, terracotta accent, warm callout boxes | Book style: Georgia serif, justified, part/chapter breaks |
| Best for | Guides, playbooks, interview prep, reports, scorecards | Long-form books, docs with inline SVG diagrams, CJK |
| Deps | `weasyprint`, `markdown` | Node `marked` + Windows Chrome |
| Portability | Any Linux (incl. bare WSL2, servers) | Needs Windows Chrome on the host |

Reach for **/guide-pdf** when you want the branded, callout-driven guide look with zero
browser setup. Reach for **/pdf** when you want a justified serif *book* or need inline SVG.

## Requirements

```bash
python3 -c "import weasyprint, markdown" 2>/dev/null || pip install weasyprint markdown
```

Optional (nicer page-count report): `pip install pymupdf` or `pip install pypdf`.

## Usage

```bash
python3 scripts/build-guide-pdf.py <input.md> <output.pdf> ["Footer text"] [--design-contract <path>]
```

The bundled `scripts/build-guide-pdf.py` is the canonical copy. If you only have this
SKILL.md (e.g. pasted into a prompt), write out the **Self-contained builder** below to a
file and run that.

## What the markdown should contain

The builder reads structure from the markdown — author the guide to this contract:

- `# Title` — first H1 becomes the document title (big, near-black).
- `### Subtitle` — first H3 becomes the grey subtitle under the title.
- `> epigraph` — a blockquote right after the subtitle is **kept** as the first warm callout.
- `## Chapter` — H2s render as terracotta section rules.
- `> **Спросить дословно:** …` — write every verbatim ask / key callout as a blockquote;
  it styles itself into a warm box. No CSS in the source.
- ` ```fenced``` ` code blocks render as styled `pre` (for prompt examples, schemas, etc.).
- Tables use auto layout — 3, 4, 5+ columns all render (comparison / scorecard matrices).
- `---` rules are hidden; the H2 styling carries the visual section breaks.

## Steps (agent workflow)

1. **Ensure deps** — run the requirements check above; `pip install` if missing.
2. **Detect design contract** — if `design-contract.json` exists in the project root,
   pass `--design-contract design-contract.json` to the build command so the guide
   inherits project-level design tokens.
3. **Check the source** — confirm the markdown has a `# Title` (required) and ideally a
   `### Subtitle`. Fix the source, don't work around it.
4. **Build** — run `scripts/build-guide-pdf.py <in.md> <out.pdf> ["Footer"] [--design-contract <path>]`.
4. **Verify** — confirm the PDF exists, is non-zero, and the reported page count is sane.
   This environment usually has no `poppler`, so verify content by **text extraction**
   (`fitz`/`pypdf`), not by rendering to an image. Spot-check that the title, a callout,
   a code block, and a wide table all appear.
5. **Report** — output path, page count, file size. Note that re-running is idempotent.

## Design tokens (house style — single source of truth)

| Token | Value | Used for |
|---|---|---|
| Ink (body) | `#1c1c1c` | Body text (near-black, not pure black) |
| Accent primary | `#9a3b2f` | H2 rules, links, list markers, callout border, table headers |
| Accent secondary | `#d98b6a` | H3 left rule, code-block left rule |
| Warm background | `#f6f1ee` | Blockquote / callout boxes |
| Code background | `#ece7e3` | Inline code + code blocks |
| Table header / zebra | `#f1e7e4` / `#faf7f6` | `th` / even rows |
| Body / mono font | `PT Sans → DejaVu Sans` / `DejaVu Sans Mono` | DejaVu is the live Cyrillic fallback |
| Page | A4, margins `15/17/16/17 mm` | Footer: text left, `стр. N / M` right |

To **restyle every guide at once**, edit the `INK / ACCENT / …` constants and the font
stack in the builder — no per-guide CSS anywhere.

The builder also accepts `--design-contract <path>` to read tokens from a project's
`design-contract.json` (`design_tokens.values.ink / accent / accent2 / warm_bg / code_bg
/ th_bg / zebra`). When present, these override the hardcoded defaults, so project-level
design tokens (set by `/design-rubric`) propagate into printed documentation.

## Self-contained builder

Canonical copy lives at `scripts/build-guide-pdf.py`. Reproduced here so the skill works
when only SKILL.md is available (write it to a file and run `python3 <file> in.md out.pdf`):

```python
#!/usr/bin/env python3
"""Markdown guide/report -> print-ready PDF in the house style (weasyprint)."""
import json
import re, sys, markdown
from weasyprint import HTML

if len(sys.argv) < 3:
    sys.exit('usage: build-guide-pdf.py <input.md> <output.pdf> ["Footer text"] [--design-contract <path>]')
SRC, OUT = sys.argv[1], sys.argv[2]
FOOTER = sys.argv[3] if len(sys.argv) > 3 else ""
DESIGN_CONTRACT = None
i = 4
while i < len(sys.argv):
    if sys.argv[i] == "--design-contract" and i + 1 < len(sys.argv):
        DESIGN_CONTRACT = sys.argv[i + 1]; i += 2
    elif sys.argv[i] == "--design-contract": i += 1
    else: i += 1

src = open(SRC, encoding="utf-8").read()
m_title = re.search(r"^# (.+)$", src, re.M)
if not m_title:
    sys.exit("error: no '# Title' H1 found")
title = m_title.group(1).strip()
m_sub = re.search(r"^### (.+)$", src, re.M)
subtitle = m_sub.group(1).strip() if m_sub else ""
body_md = src[(m_sub.end() if m_sub else m_title.end()):].lstrip("\n")
body_html = markdown.markdown(body_md, extensions=["tables", "sane_lists", "fenced_code"])
body_html = (body_html.replace("✅", '<span class="ok">✓</span>')
                      .replace("🟡", '<span class="mid">≈</span>'))

INK, ACCENT, ACCENT2 = "#1c1c1c", "#9a3b2f", "#d98b6a"
WARM_BG, CODE_BG, TH_BG, ZEBRA = "#f6f1ee", "#ece7e3", "#f1e7e4", "#faf7f6"

if DESIGN_CONTRACT:
    try:
        with open(DESIGN_CONTRACT, encoding="utf-8") as f:
            vals = json.load(f).get("design_tokens", {}).get("values", {})
        INK      = vals.get("ink",      INK)
        ACCENT   = vals.get("accent",   ACCENT)
        ACCENT2  = vals.get("accent2",  ACCENT2)
        WARM_BG  = vals.get("warm_bg",  WARM_BG)
        CODE_BG  = vals.get("code_bg",  CODE_BG)
        TH_BG    = vals.get("th_bg",    TH_BG)
        ZEBRA    = vals.get("zebra",    ZEBRA)
    except Exception: pass
CSS = f"""
@page {{ size: A4; margin: 15mm 17mm 16mm 17mm;
  @bottom-left  {{ content: "{FOOTER}"; font-size: 7pt; color: #a59a97; }}
  @bottom-right {{ content: "стр. " counter(page) " / " counter(pages); font-size: 7pt; color: #a59a97; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: "PT Sans","DejaVu Sans","Liberation Sans",sans-serif;
  font-size: 10.3pt; line-height: 1.46; color: {INK}; margin: 0; }}
.doc-title {{ font-size: 20pt; font-weight: 700; color: #111; line-height: 1.16; margin: 0 0 4pt 0; }}
.doc-sub {{ font-size: 10pt; color: #6f6f6f; margin: 0; line-height: 1.3; }}
.doc-rule {{ height: 2.2pt; background: {ACCENT}; margin: 8pt 0 0 0; }}
h2 {{ font-size: 13.5pt; font-weight: 700; color: {ACCENT}; margin: 20pt 0 7pt 0;
  padding-bottom: 3pt; border-bottom: 1.4pt solid {ACCENT}; page-break-after: avoid; }}
h2:first-of-type {{ margin-top: 13pt; }}
h3 {{ font-size: 10.9pt; font-weight: 700; color: #2a2a2a; margin: 12pt 0 4pt 0;
  padding-left: 7pt; border-left: 3pt solid {ACCENT2}; page-break-after: avoid; }}
p {{ margin: 5pt 0; }}
strong {{ color: #101010; font-weight: 700; }} em {{ color: #555; }}
a {{ color: {ACCENT}; text-decoration: none; word-break: break-word; }}
ul, ol {{ margin: 5pt 0; padding-left: 17pt; }} li {{ margin: 2.6pt 0; line-height: 1.42; }}
li::marker {{ color: {ACCENT}; }}
blockquote {{ margin: 7pt 0; padding: 6pt 11pt; background: {WARM_BG};
  border-left: 3pt solid {ACCENT}; page-break-inside: avoid; }}
blockquote p {{ margin: 3pt 0; }}
code {{ font-family: "DejaVu Sans Mono",monospace; font-size: 8.7pt; background: {CODE_BG}; padding: 0.5pt 3pt; border-radius: 2pt; }}
pre {{ background: {CODE_BG}; padding: 8pt 10pt; border-radius: 3pt; border-left: 3pt solid {ACCENT2};
  margin: 7pt 0; page-break-inside: avoid; white-space: pre-wrap; word-wrap: break-word; }}
pre code {{ background: none; padding: 0; font-size: 8.4pt; line-height: 1.4; }}
table {{ width: 100%; border-collapse: collapse; margin: 8pt 0; font-size: 8.5pt; table-layout: auto; }}
th {{ background: {TH_BG}; color: {ACCENT}; font-weight: 700; text-align: left;
  padding: 5pt 6pt; border: 0.6pt solid #d9c7c2; vertical-align: top; }}
td {{ padding: 5pt 6pt; border: 0.6pt solid #ddd6d3; vertical-align: top; word-wrap: break-word; }}
tbody tr {{ page-break-inside: avoid; }} tbody tr:nth-child(even) {{ background: {ZEBRA}; }}
.ok {{ color: #2e7d32; font-weight: 700; }} .mid {{ color: #b9770b; font-weight: 700; }}
hr {{ display: none; }}
"""
header = ('<div class="doc-head">'
          f'<div class="doc-title">{title}</div>'
          + (f'<div class="doc-sub">{subtitle}</div>' if subtitle else "")
          + '</div><div class="doc-rule"></div>')
HTML(string=f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
            f"<body>{header}{body_html}</body></html>").write_pdf(OUT)

pages = "?"
try:
    import fitz; d = fitz.open(OUT); pages = len(d); d.close()
except Exception:
    try:
        from pypdf import PdfReader; pages = len(PdfReader(OUT).pages)
    except Exception:
        pass
print(f"Saved: {OUT}\nPages: {pages}")
```

## Fallback

- **weasyprint won't install** (rare on locked-down hosts) → fall back to the `/pdf` skill
  (Chrome), accepting the book style, or emit the styled HTML and let the user print it.
- **No `# Title` in the source** → the build stops with a clear error; add the H1 rather
  than patching the script.
- **Wide tables overflow** → they auto-wrap; if still tight, drop the table body font a
  point in the token block.
