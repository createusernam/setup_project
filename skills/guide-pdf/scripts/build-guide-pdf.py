#!/usr/bin/env python3
"""Markdown guide/report -> print-ready PDF in the house style.
 
House style = Arutyunov IDS + Birman: near-black body (#1c1c1c), single
terracotta accent (#9a3b2f), warm callout/table backgrounds, content-first,
no chrome. Pure Python via weasyprint — no Node, no browser, no WSL2/Windows
(unlike the /pdf skill, which is book-style Chrome-based).
 
Usage:
    python3 build-guide-pdf.py <input.md> <output.pdf> ["Footer text"]
          [--design-contract <path>]
 
    --design-contract <path>  Read design tokens from design-contract.json
                              (design_tokens.values.*). Has priority over
                              hardcoded defaults.
 
Deps: weasyprint, markdown  (pip install weasyprint markdown)
Optional page count: fitz (PyMuPDF) or pypdf.
 
Markdown contract:
    # Title            -> document title (first H1)
    ### Subtitle       -> grey subtitle (first H3)
    > epigraph         -> kept, becomes the first warm callout
    ## Chapter         -> terracotta section rules
    > **Ask:** ...     -> blockquotes double as warm callout boxes
    ```fenced```       -> code blocks (styled pre)
    | tables |         -> auto layout, any column count
    ---                -> hidden (H2 styling carries the breaks)
"""
import json
import re
import sys
import markdown
from weasyprint import HTML

if len(sys.argv) < 3:
    sys.exit("usage: build-guide-pdf.py <input.md> <output.pdf> [\"Footer text\"] [--design-contract <path>]")

SRC = sys.argv[1]
OUT = sys.argv[2]
FOOTER = sys.argv[3] if len(sys.argv) > 3 else ""
DESIGN_CONTRACT = None

i = 4
while i < len(sys.argv):
    if sys.argv[i] == "--design-contract" and i + 1 < len(sys.argv):
        DESIGN_CONTRACT = sys.argv[i + 1]
        i += 2
    elif sys.argv[i] == "--design-contract":
        i += 1
    else:
        i += 1

src = open(SRC, encoding="utf-8").read()

# --- title = first "# ", subtitle = first "### " ---
m_title = re.search(r"^# (.+)$", src, re.M)
if not m_title:
    sys.exit("error: no '# Title' H1 found in the markdown")
title = m_title.group(1).strip()
m_sub = re.search(r"^### (.+)$", src, re.M)
subtitle = m_sub.group(1).strip() if m_sub else ""

# --- body = everything AFTER the subtitle line (keeps the epigraph) ---
cut = m_sub.end() if m_sub else m_title.end()
body_md = src[cut:].lstrip("\n")

body_html = markdown.markdown(
    body_md, extensions=["tables", "sane_lists", "fenced_code"]
)

# --- print cleanups: screen emoji -> print-safe glyphs ---
body_html = (body_html
             .replace("✅", '<span class="ok">✓</span>')
             .replace("🟡", '<span class="mid">≈</span>'))

# ---------------------------------------------------------------- HOUSE STYLE
# Defaults (Arutyunov IDS + Birman). Overridable via design-contract.json.
INK      = "#1c1c1c"
ACCENT   = "#9a3b2f"
ACCENT2  = "#d98b6a"
WARM_BG  = "#f6f1ee"
CODE_BG  = "#ece7e3"
TH_BG    = "#f1e7e4"
ZEBRA    = "#faf7f6"

if DESIGN_CONTRACT:
    try:
        with open(DESIGN_CONTRACT, encoding="utf-8") as f:
            dc = json.load(f)
        vals = dc.get("design_tokens", {}).get("values", {})
        INK      = vals.get("ink",      INK)
        ACCENT   = vals.get("accent",   ACCENT)
        ACCENT2  = vals.get("accent2",  ACCENT2)
        WARM_BG  = vals.get("warm_bg",  WARM_BG)
        CODE_BG  = vals.get("code_bg",  CODE_BG)
        TH_BG    = vals.get("th_bg",    TH_BG)
        ZEBRA    = vals.get("zebra",    ZEBRA)
    except Exception:
        pass  # fall back to defaults

CSS = f"""
@page {{
  size: A4;
  margin: 15mm 17mm 16mm 17mm;
  @bottom-left  {{ content: "{FOOTER}"; font-size: 7pt; color: #a59a97; }}
  @bottom-right {{ content: "стр. " counter(page) " / " counter(pages);
                   font-size: 7pt; color: #a59a97; }}
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: "PT Sans", "DejaVu Sans", "Liberation Sans", sans-serif;
  font-size: 10.3pt; line-height: 1.46; color: {INK}; margin: 0;
}}
.doc-head  {{ margin: 0 0 2pt 0; }}
.doc-title {{ font-size: 20pt; font-weight: 700; color: #111;
             line-height: 1.16; margin: 0 0 4pt 0; }}
.doc-sub   {{ font-size: 10pt; color: #6f6f6f; margin: 0; line-height: 1.3; }}
.doc-rule  {{ height: 2.2pt; background: {ACCENT}; margin: 8pt 0 0 0; }}
h2 {{
  font-size: 13.5pt; font-weight: 700; color: {ACCENT};
  margin: 20pt 0 7pt 0; padding-bottom: 3pt;
  border-bottom: 1.4pt solid {ACCENT}; page-break-after: avoid;
}}
h2:first-of-type {{ margin-top: 13pt; }}
h3 {{
  font-size: 10.9pt; font-weight: 700; color: #2a2a2a;
  margin: 12pt 0 4pt 0; padding-left: 7pt;
  border-left: 3pt solid {ACCENT2}; page-break-after: avoid;
}}
p  {{ margin: 5pt 0; }}
strong {{ color: #101010; font-weight: 700; }}
em {{ color: #555; }}
a  {{ color: {ACCENT}; text-decoration: none; word-break: break-word; }}
ul, ol {{ margin: 5pt 0; padding-left: 17pt; }}
li {{ margin: 2.6pt 0; line-height: 1.42; }}
li::marker {{ color: {ACCENT}; }}
blockquote {{
  margin: 7pt 0; padding: 6pt 11pt;
  background: {WARM_BG}; border-left: 3pt solid {ACCENT};
  page-break-inside: avoid;
}}
blockquote p {{ margin: 3pt 0; }}
code {{
  font-family: "DejaVu Sans Mono", monospace;
  font-size: 8.7pt; background: {CODE_BG};
  padding: 0.5pt 3pt; border-radius: 2pt;
}}
pre {{
  background: {CODE_BG}; padding: 8pt 10pt; border-radius: 3pt;
  border-left: 3pt solid {ACCENT2}; margin: 7pt 0;
  page-break-inside: avoid; white-space: pre-wrap; word-wrap: break-word;
}}
pre code {{ background: none; padding: 0; font-size: 8.4pt; line-height: 1.4; }}
table {{
  width: 100%; border-collapse: collapse; margin: 8pt 0;
  font-size: 8.5pt; table-layout: auto;
}}
th {{
  background: {TH_BG}; color: {ACCENT}; font-weight: 700;
  text-align: left; padding: 5pt 6pt; border: 0.6pt solid #d9c7c2;
  vertical-align: top;
}}
td {{
  padding: 5pt 6pt; border: 0.6pt solid #ddd6d3;
  vertical-align: top; word-wrap: break-word;
}}
tbody tr {{ page-break-inside: avoid; }}
tbody tr:nth-child(even) {{ background: {ZEBRA}; }}
.ok  {{ color: #2e7d32; font-weight: 700; }}
.mid {{ color: #b9770b; font-weight: 700; }}
hr {{ display: none; }}
"""

header_html = (
    '<div class="doc-head">'
    f'<div class="doc-title">{title}</div>'
    + (f'<div class="doc-sub">{subtitle}</div>' if subtitle else "")
    + '</div><div class="doc-rule"></div>'
)

html = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    f"<style>{CSS}</style></head><body>"
    f"{header_html}{body_html}</body></html>"
)

HTML(string=html).write_pdf(OUT)

# --- best-effort page count ---
pages = "?"
try:
    import fitz
    d = fitz.open(OUT); pages = len(d); d.close()
except Exception:
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(OUT).pages)
    except Exception:
        pass
print(f"Saved: {OUT}")
print(f"Pages: {pages}")
