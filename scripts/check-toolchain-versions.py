#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Keep executable tool references reproducible and synchronized with the version manifest.
# SCOPE: Validate Playwright MCP references in setup documentation and skills.
# DEPENDS: Python standard library and toolchain-versions.json.
# END_MODULE_CONTRACT
"""Fail when committed Playwright MCP commands drift from the pinned manifest."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads((ROOT / "toolchain-versions.json").read_text(encoding="utf-8"))
    expected = f"@playwright/mcp@{manifest['playwright_mcp']}"
    failures: list[str] = []
    references = 0
    for base in (ROOT / "docs", ROOT / "skills"):
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".json", ".py", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "@playwright/mcp@" not in text:
                continue
            references += text.count("@playwright/mcp@")
            versions = re.findall(r"@playwright/mcp@([0-9A-Za-z._-]+)", text)
            if any(f"@playwright/mcp@{version}" != expected for version in versions):
                failures.append(str(path.relative_to(ROOT)))
    if references == 0:
        failures.append("no pinned Playwright MCP references found")
    if failures:
        print("FAIL toolchain version drift: " + ", ".join(sorted(set(failures))))
        return 1
    print(f"PASS {references} Playwright MCP reference(s) pinned to {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_MODULE_CONTRACT
