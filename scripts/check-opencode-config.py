#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Validate OpenCode's global instruction contract without substring-based false positives.
# SCOPE: Parse opencode.json and require exact resolved PIPELINE.md and COMPAT.md paths in an array.
# DEPENDS: Python standard library only.
# END_MODULE_CONTRACT
"""Check OpenCode instruction paths and print one status per invariant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def check(config: Path, setup_dir: Path) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    errors: list[str] = []
    try:
        document = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"FAIL valid JSON: {error}"], ["invalid JSON"]
    lines.append("PASS valid JSON")
    instructions = document.get("instructions") if isinstance(document, dict) else None
    if not isinstance(instructions, list) or not all(isinstance(item, str) for item in instructions):
        lines.append("FAIL instructions array")
        return lines, ["instructions must be an array of paths"]
    lines.append("PASS instructions array")
    resolved = {str(Path(item).expanduser().resolve(strict=False)) for item in instructions}
    for label, relative in (("PIPELINE", "docs/human/PIPELINE.md"), ("COMPAT", "docs/agent/COMPAT.md")):
        expected = str((setup_dir / relative).resolve())
        if expected in resolved:
            lines.append(f"PASS {label} present: {expected}")
        else:
            lines.append(f"FAIL {label} present: expected {expected}")
            errors.append(f"missing exact {label} instruction path")
    return lines, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--setup-dir", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lines, errors = check(args.config.expanduser(), args.setup_dir.resolve())
    print("\n".join(lines))
    if errors:
        print("OpenCode instructions are not ready: " + "; ".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# END_MODULE_CONTRACT
