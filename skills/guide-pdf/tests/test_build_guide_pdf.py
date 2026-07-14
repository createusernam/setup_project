#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Prevent semantic loss and unsupported-diagram regressions in guide-pdf.
# SCOPE: Unit-test Markdown metadata parsing, diagram preflight, and optional PDF integration.
# DEPENDS: Python unittest; optional markdown, weasyprint, and fitz for integration coverage.
# END_MODULE_CONTRACT
"""Regression tests for lossless Markdown parsing and diagram preflight."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "build-guide-pdf.py"
SPEC = importlib.util.spec_from_file_location("build_guide_pdf", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ParseDocumentTests(unittest.TestCase):
    def test_research_report_keeps_opening_before_first_deep_h3(self) -> None:
        source = """# Evidence report

## Short conclusion

Load-bearing opening.

## Research question

Still part of the report.

### Scope

Scope details.
"""
        title, subtitle, body = MODULE.parse_document(source)

        self.assertEqual(title, "Evidence report")
        self.assertEqual(subtitle, "")
        self.assertTrue(body.startswith("## Short conclusion"))
        self.assertIn("Load-bearing opening.", body)
        self.assertIn("### Scope", body)

    def test_reader_guide_keeps_preface_and_later_part_h1(self) -> None:
        source = """# Last Train

> Practical guide.

## Preface

Why this matters.

### How to read

Read in order.

# Part I

## First mechanism
"""
        title, subtitle, body = MODULE.parse_document(source)

        self.assertEqual(title, "Last Train")
        self.assertEqual(subtitle, "")
        self.assertTrue(body.startswith("> Practical guide."))
        self.assertIn("## Preface", body)
        self.assertIn("# Part I", body)

    def test_adjacent_h3_is_optional_subtitle_metadata(self) -> None:
        source = """# Guide title

### A practical subtitle

> Opening callout.

## Chapter
"""
        title, subtitle, body = MODULE.parse_document(source)

        self.assertEqual(title, "Guide title")
        self.assertEqual(subtitle, "A practical subtitle")
        self.assertTrue(body.startswith("> Opening callout."))
        self.assertNotIn("A practical subtitle", body)

    def test_h3_after_prose_is_not_subtitle(self) -> None:
        source = """# Guide title

Opening paragraph.

### First subheading

Details.
"""
        _, subtitle, body = MODULE.parse_document(source)

        self.assertEqual(subtitle, "")
        self.assertTrue(body.startswith("Opening paragraph."))
        self.assertIn("### First subheading", body)

    def test_missing_h1_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(ValueError, "no '# Title' H1"):
            MODULE.parse_document("## Starts too deep\n")


class DiagramPreflightTests(unittest.TestCase):
    def test_mermaid_is_reported_not_silently_rendered(self) -> None:
        source = """# Guide

```mermaid
flowchart TD
  A --> B
```
"""
        self.assertEqual(MODULE.unsupported_diagram_fences(source), ["mermaid"])

    def test_ordinary_code_is_supported(self) -> None:
        source = """# Guide

```python
print('hello')
```
"""
        self.assertEqual(MODULE.unsupported_diagram_fences(source), [])


@unittest.skipUnless(
    importlib.util.find_spec("weasyprint")
    and importlib.util.find_spec("markdown")
    and importlib.util.find_spec("fitz"),
    "rendering integration dependencies are optional",
)
class RenderingIntegrationTests(unittest.TestCase):
    def test_rendered_pdf_keeps_semantic_sentinels_and_part_heading(self) -> None:
        import fitz

        source = """# Lossless Renderer Test

## Opening

FIRST_SENTINEL evidence must survive.

### Deep heading

This H3 is content, not subtitle metadata.

# Part Two

> Quoted evidence remains a blockquote.

| Claim | Status |
|---|---|
| Prefix preserved | expected |

```text
structured contract
```

---

## Closing

LAST_SENTINEL evidence must survive.
"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "guide.pdf"
            MODULE.render_pdf(source, str(output), "Integration test")
            document = fitz.open(output)
            text = "".join(page.get_text() for page in document)
            document.close()

        self.assertIn("FIRST_SENTINEL", text)
        self.assertIn("LAST_SENTINEL", text)
        self.assertIn("Part Two", text)
        self.assertIn("Deep heading", text)


if __name__ == "__main__":
    unittest.main()
