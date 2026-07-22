#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Provide one fail-closed integrity gate for setup development, CI, and release preparation.
# SCOPE: Run repository-owned structural, test, skill, generated-view, and handbook checks by verification profile.
# DEPENDS: Python standard library and repository validation scripts.
# END_MODULE_CONTRACT
"""Run the setup integrity matrix with fast, full, or release coverage."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def command(label: str, argv: list[str]) -> tuple[str, bool]:
    result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        print(f"FAIL {label}\n{result.stdout}", file=sys.stderr)
        return label, False
    print(f"PASS {label}")
    return label, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("fast", "full", "release"), default="fast")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    python = sys.executable
    checks: list[tuple[str, list[str]]] = [
        ("machine schema", [python, "-c", "import importlib.util,json; from pathlib import Path; r=Path('.'); s=importlib.util.spec_from_file_location('schema',r/'scripts/json_schema.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); e=m.validate(json.loads((r/'pipeline-machine.json').read_text()),json.loads((r/'schemas/pipeline-machine.schema.json').read_text())); print('\\n'.join(e)); raise SystemExit(bool(e))"]),
        ("generated pipeline view", [python, "scripts/render-pipeline-views.py", "--check"]),
        ("skill manifests", [python, "scripts/validate-skills.py", "--profile", "claude"]),
        ("core harness", [python, "-m", "unittest", "discover", "-s", "scripts/tests"]),
    ]
    if args.profile in {"full", "release"}:
        checks.append(("guide PDF tests", [python, "skills/guide-pdf/tests/test_build_guide_pdf.py"]))
        # Private extensions are deliberately discovered rather than named: public projections
        # omit them, while a private checkout still validates every installed extension contract.
        for validator in sorted((root / "skills").glob("*/scripts/validate-state.py")):
            cases = validator.parents[1] / "tests" / "cases"
            if cases.is_dir():
                checks.append((f"{validator.parents[1].name} cases", [python, str(validator), "--cases", str(cases)]))
        for validator in sorted((root / "skills").glob("*/scripts/validate-handbook.py")):
            checks.append((f"{validator.parents[1].name} handbook", [python, str(validator), "--repo", str(root)]))
    results = [command(label, argv) for label, argv in checks]
    if args.profile == "release":
        clean = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, stdout=subprocess.PIPE).stdout == ""
        results.append(("clean worktree", clean))
        print(f"{'PASS' if clean else 'FAIL'} clean worktree")
    failed = [label for label, ok in results if not ok]
    print(f"verify-setup {args.profile}: {len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
