#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Render authored Markdown to PDF without changing semantic content or block order.
# SCOPE: Parse title metadata, reject unsupported diagrams, apply print CSS, and emit PDF.
# DEPENDS: Python stdlib; optional runtime packages markdown, weasyprint, fitz, and pypdf.
# END_MODULE_CONTRACT

"""Lossless Markdown guide/report -> print-ready A4 PDF.

This renderer owns presentation only. It preserves authored block order and heading
hierarchy, and refuses diagram fences that WeasyPrint cannot render faithfully.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import sys
from typing import Any


TITLE_RE = re.compile(r"^#(?!#)\s+(.+?)\s*$", re.MULTILINE)
DIAGRAM_FENCE_RE = re.compile(
    r"^\s*```\s*(mermaid|plantuml|dot|graphviz)\b", re.MULTILINE | re.IGNORECASE
)

DEFAULT_TOKENS = {
    "ink": "#1c1c1c",
    "accent": "#9a3b2f",
    "accent2": "#d98b6a",
    "warm_bg": "#f6f1ee",
    "code_bg": "#ece7e3",
    "th_bg": "#f1e7e4",
    "zebra": "#faf7f6",
}


# START_BLOCK_DOCUMENT_PARSE
def parse_document(source: str) -> tuple[str, str, str]:
    """Return title, optional adjacent subtitle, and losslessly preserved body."""
    title_match = TITLE_RE.search(source)
    if not title_match:
        raise ValueError("no '# Title' H1 found in the Markdown")

    title = title_match.group(1).strip()
    remainder = source[title_match.end() :]

    # Subtitle metadata is valid only as the first nonblank block after the title.
    leading_blank = re.match(r"(?:[ \t]*\n)*", remainder)
    candidate_start = leading_blank.end() if leading_blank else 0
    subtitle_match = re.match(
        r"###[ \t]+(.+?)[ \t]*(?:\n|$)", remainder[candidate_start:]
    )

    if subtitle_match:
        subtitle = subtitle_match.group(1).strip()
        body_start = candidate_start + subtitle_match.end()
        body = remainder[body_start:].lstrip("\n")
    else:
        subtitle = ""
        body = remainder.lstrip("\n")

    return title, subtitle, body


def unsupported_diagram_fences(source: str) -> list[str]:
    """Return unsupported diagram languages in first-seen order."""
    found: list[str] = []
    for match in DIAGRAM_FENCE_RE.finditer(source):
        language = match.group(1).lower()
        if language not in found:
            found.append(language)
    return found


def load_design_tokens(path: str | None) -> dict[str, str]:
    """Load optional project tokens, failing explicitly on an invalid contract."""
    tokens = DEFAULT_TOKENS.copy()
    if not path:
        return tokens

    try:
        contract: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read design contract '{path}': {exc}") from exc

    values = contract.get("design_tokens", {}).get("values", {})
    if not isinstance(values, dict):
        raise ValueError("design contract field design_tokens.values must be an object")

    for key in tokens:
        value = values.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"design token '{key}' must be a string")
            tokens[key] = value
    return tokens
# END_BLOCK_DOCUMENT_PARSE


# START_BLOCK_PRINT_STYLE
def css_string(value: str) -> str:
    """Escape a value for a quoted CSS content string."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def build_css(tokens: dict[str, str], footer: str) -> str:
    ink = tokens["ink"]
    accent = tokens["accent"]
    accent2 = tokens["accent2"]
    warm_bg = tokens["warm_bg"]
    code_bg = tokens["code_bg"]
    th_bg = tokens["th_bg"]
    zebra = tokens["zebra"]
    footer_css = css_string(footer)

    return f"""
@page {{ size: A4; margin: 15mm 17mm 16mm 17mm;
  @bottom-left  {{ content: "{footer_css}"; font-size: 7pt; color: #a59a97; }}
  @bottom-right {{ content: "стр. " counter(page) " / " counter(pages); font-size: 7pt; color: #a59a97; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: "PT Sans", "DejaVu Sans", "Liberation Sans", sans-serif;
  font-size: 10.3pt; line-height: 1.46; color: {ink}; margin: 0; }}
.doc-head {{ margin: 0 0 2pt 0; }}
.doc-title {{ font-size: 20pt; font-weight: 700; color: #111; line-height: 1.16; margin: 0 0 4pt 0; }}
.doc-sub {{ font-size: 10pt; color: #6f6f6f; margin: 0; line-height: 1.3; }}
.doc-rule {{ height: 2.2pt; background: {accent}; margin: 8pt 0 0 0; }}
body > h1 {{ font-size: 16pt; font-weight: 700; color: #111; margin: 24pt 0 8pt 0;
  padding-top: 7pt; border-top: 2pt solid {accent}; page-break-after: avoid; }}
h2 {{ font-size: 13.5pt; font-weight: 700; color: {accent}; margin: 20pt 0 7pt 0;
  padding-bottom: 3pt; border-bottom: 1.4pt solid {accent}; page-break-after: avoid; }}
h2:first-of-type {{ margin-top: 13pt; }}
h3 {{ font-size: 10.9pt; font-weight: 700; color: #2a2a2a; margin: 12pt 0 4pt 0;
  padding-left: 7pt; border-left: 3pt solid {accent2}; page-break-after: avoid; }}
h4, h5, h6 {{ color: #2a2a2a; page-break-after: avoid; }}
p {{ margin: 5pt 0; }}
strong {{ color: #101010; font-weight: 700; }} em {{ color: #555; }}
a {{ color: {accent}; text-decoration: none; word-break: break-word; }}
ul, ol {{ margin: 5pt 0; padding-left: 17pt; }} li {{ margin: 2.6pt 0; line-height: 1.42; }}
li::marker {{ color: {accent}; }}
blockquote {{ margin: 7pt 0; padding: 6pt 11pt; background: {warm_bg};
  border-left: 3pt solid {accent}; page-break-inside: avoid; }}
blockquote p {{ margin: 3pt 0; }}
code {{ font-family: "DejaVu Sans Mono", monospace; font-size: 8.7pt;
  background: {code_bg}; padding: 0.5pt 3pt; border-radius: 2pt; }}
pre {{ background: {code_bg}; padding: 8pt 10pt; border-radius: 3pt;
  border-left: 3pt solid {accent2}; margin: 7pt 0; page-break-inside: avoid;
  white-space: pre-wrap; word-wrap: break-word; }}
pre code {{ background: none; padding: 0; font-size: 8.4pt; line-height: 1.4; }}
table {{ width: 100%; border-collapse: collapse; margin: 8pt 0;
  font-size: 8.5pt; table-layout: auto; }}
th {{ background: {th_bg}; color: {accent}; font-weight: 700; text-align: left;
  padding: 5pt 6pt; border: 0.6pt solid #d9c7c2; vertical-align: top; }}
td {{ padding: 5pt 6pt; border: 0.6pt solid #ddd6d3; vertical-align: top; word-wrap: break-word; }}
tbody tr {{ page-break-inside: avoid; }} tbody tr:nth-child(even) {{ background: {zebra}; }}
.ok {{ color: #2e7d32; font-weight: 700; }} .mid {{ color: #b9770b; font-weight: 700; }}
hr {{ border: 0; border-top: 0.7pt solid #d8cfcc; margin: 13pt 0; }}
"""
# END_BLOCK_PRINT_STYLE


# START_BLOCK_PDF_RENDER
def render_pdf(
    source: str,
    output_path: str,
    footer: str = "",
    design_contract: str | None = None,
) -> None:
    """Render validated Markdown source to PDF."""
    diagrams = unsupported_diagram_fences(source)
    if diagrams:
        joined = ", ".join(diagrams)
        raise ValueError(
            f"unsupported diagram fence(s): {joined}; pre-render diagrams or use an installed diagram-capable renderer"
        )

    title, subtitle, body_markdown = parse_document(source)
    tokens = load_design_tokens(design_contract)

    try:
        import markdown  # type: ignore
        from weasyprint import HTML  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "missing dependencies: install 'weasyprint' and 'markdown' after user approval"
        ) from exc

    body_html = markdown.markdown(
        body_markdown, extensions=["tables", "sane_lists", "fenced_code"]
    )
    body_html = body_html.replace("✅", '<span class="ok">✓</span>').replace(
        "🟡", '<span class="mid">≈</span>'
    )

    header_html = (
        '<div class="doc-head">'
        f'<div class="doc-title">{html.escape(title)}</div>'
        + (f'<div class="doc-sub">{html.escape(subtitle)}</div>' if subtitle else "")
        + '</div><div class="doc-rule"></div>'
    )
    css = build_css(tokens, footer)
    document = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{header_html}{body_html}</body></html>"
    )
    HTML(string=document).write_pdf(output_path)


def page_count(path: str) -> int | None:
    """Best-effort page count without making optional packages mandatory."""
    try:
        import fitz  # type: ignore

        document = fitz.open(path)
        count = len(document)
        document.close()
        return count
    except Exception:
        try:
            from pypdf import PdfReader  # type: ignore

            return len(PdfReader(path).pages)
        except Exception:
            return None
# END_BLOCK_PDF_RENDER


# START_BLOCK_CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="source Markdown path")
    parser.add_argument("output", help="target PDF path")
    parser.add_argument("footer", nargs="?", default="", help="optional footer text")
    parser.add_argument("--design-contract", help="optional design-contract.json path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = Path(args.input).read_text(encoding="utf-8")
        render_pdf(source, args.output, args.footer, args.design_contract)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    pages = page_count(args.output)
    print(f"Saved: {args.output}")
    print(f"Pages: {pages if pages is not None else '?'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_BLOCK_CLI
