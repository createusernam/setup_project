#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Enforce GRACE Lite or autonomous markup contracts on repository source files.
# SCOPE: Select source files, validate module/block/function/log annotations, and report a verdict.
# DEPENDS: Bash, Python 3, git for --changed mode, and the GRACE rules in docs/human/PIPELINE.md.
# END_MODULE_CONTRACT
# grace-lint.sh — enforce GRACE Lite markup (docs/human/PIPELINE.md §"GRACE Lite — обязательные правила").
#
# GRACE Lite is declared mandatory in every project. Until this script existed, nothing checked it:
# the rule lived in prose, and the model asked to honour it in Phase 6 is the weakest one in the
# chain. Prose is not an enforcement mechanism — this is.
#
# Usage:
#   bash ~/.claude/scripts/grace-lint.sh [path ...]        # default: whole repo
#   bash ~/.claude/scripts/grace-lint.sh --changed         # only files changed vs HEAD (pre-commit / review)
#   bash ~/.claude/scripts/grace-lint.sh --profile autonomous   # stricter: function contracts + log anchors
#   bash ~/.claude/scripts/grace-lint.sh --json            # machine-readable (build-loop gate)
#
# Profiles:
#   lite (default) — MODULE_CONTRACT in every source file; balanced START_BLOCK/END_BLOCK.
#   autonomous     — lite + FUNCTION_CONTRACT on every exported function + at least one block-anchored
#                    log per module. Required before an unattended /build-loop run: an autonomous agent
#                    navigates by these anchors and has no human to ask.
#
# Exit: 0 clean · 1 violations found · 2 usage error
set -euo pipefail
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SELF")/.." && pwd)"

PROFILE="lite"
CHANGED=0
JSON=0
PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --changed) CHANGED=1; shift ;;
    --json)    JSON=1; shift ;;
    -h|--help) sed -n '2,20p' "$SELF"; exit 0 ;;
    -*)        echo "grace-lint: unknown flag $1"; exit 2 ;;
    *)         PATHS+=("$1"); shift ;;
  esac
done
case "$PROFILE" in lite|autonomous) ;; *) echo "grace-lint: profile must be 'lite' or 'autonomous'"; exit 2 ;; esac

python3 - "$PROFILE" "$CHANGED" "$JSON" "${PATHS[@]:-}" <<'PY'
import json, os, re, subprocess, sys

profile, changed, as_json = sys.argv[1], sys.argv[2] == "1", sys.argv[3] == "1"
paths = [p for p in sys.argv[4:] if p]

# Extensions we lint, mapped to their line-comment token. A file type absent here is not linted:
# we would rather skip a language than emit noise the agent learns to ignore.
COMMENT = {
    ".ts": "//", ".tsx": "//", ".js": "//", ".jsx": "//", ".mjs": "//", ".cjs": "//",
    ".go": "//", ".rs": "//", ".java": "//", ".kt": "//", ".swift": "//", ".c": "//",
    ".h": "//", ".cpp": "//", ".cs": "//", ".php": "//", ".scala": "//",
    ".py": "#", ".rb": "#", ".sh": "#", ".bash": "#",
    ".sql": "--", ".lua": "--",
}
SKIP_DIRS = {"node_modules", "dist", "build", ".git", "vendor", "coverage", ".next",
             "__pycache__", ".venv", "venv", "target", "out", ".build-loop", "docs"}
SKIP_FILE = re.compile(r"(\.d\.ts|\.test\.|\.spec\.|\.min\.|\.config\.|\.stories\.)")

def source_files():
    if changed:
        try:
            out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
                                 capture_output=True, text=True, check=True).stdout
            cand = [f for f in out.splitlines() if f.strip()]
        except subprocess.CalledProcessError:
            print("grace-lint: --changed needs a git repo with at least one commit", file=sys.stderr)
            sys.exit(2)
    else:
        roots = paths or ["."]
        cand = []
        for r in roots:
            if os.path.isfile(r):
                cand.append(r)
                continue
            for dirpath, dirnames, filenames in os.walk(r):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
                cand += [os.path.join(dirpath, f) for f in filenames]
    out = []
    for f in cand:
        if not os.path.isfile(f):
            continue
        if any(part in SKIP_DIRS for part in f.split(os.sep)):
            continue
        if SKIP_FILE.search(os.path.basename(f)):
            continue
        if os.path.splitext(f)[1] in COMMENT:
            out.append(f)
    return sorted(set(out))

# Exported-symbol detection is deliberately shallow: it catches the common declaration forms and
# nothing else. A false negative costs one unchecked function; a false positive trains the agent to
# ignore the linter, which costs the whole mechanism.
EXPORTED = re.compile(
    r"^\s*(?:export\s+(?:async\s+)?function\s+(\w+)"          # export function foo
    r"|export\s+const\s+(\w+)\s*[:=]\s*(?:async\s*)?\("        # export const foo = (…)
    r"|def\s+(?!_)(\w+)\s*\("                                   # python def foo (not _private)
    r"|func\s+(?!\w*\btest\b)([A-Z]\w*)\s*\()"                  # go exported func
)

errors, warnings, checked = [], [], 0

for path in source_files():
    checked += 1
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        warnings.append({"file": path, "line": 0, "rule": "unreadable", "msg": str(e)})
        continue
    lines = text.splitlines()

    # Rule 1 — MODULE_CONTRACT header, with its three required fields.
    if "START_MODULE_CONTRACT" not in text:
        errors.append({"file": path, "line": 1, "rule": "module-contract-missing",
                       "msg": "no MODULE_CONTRACT header (GRACE Lite rule 1 — mandatory in every file)"})
    else:
        head = text[:text.index("END_MODULE_CONTRACT")] if "END_MODULE_CONTRACT" in text else text
        if "END_MODULE_CONTRACT" not in text:
            errors.append({"file": path, "line": 1, "rule": "module-contract-unclosed",
                           "msg": "START_MODULE_CONTRACT without END_MODULE_CONTRACT"})
        missing = [f for f in ("PURPOSE:", "SCOPE:", "DEPENDS:") if f not in head]
        if missing:
            errors.append({"file": path, "line": 1, "rule": "module-contract-incomplete",
                           "msg": f"MODULE_CONTRACT missing field(s): {', '.join(m.rstrip(':') for m in missing)}"})

    # Rule 2 — blocks must balance. An unclosed block silently swallows the rest of the file's scope.
    opened = {}
    for i, line in enumerate(lines, 1):
        for m in re.finditer(r"\bSTART_BLOCK_(\w+)", line):
            opened.setdefault(m.group(1), i)
        for m in re.finditer(r"\bEND_BLOCK_(\w+)", line):
            opened.pop(m.group(1), None)
    for name, line_no in opened.items():
        errors.append({"file": path, "line": line_no, "rule": "block-unclosed",
                       "msg": f"START_BLOCK_{name} opened here, never closed (END_BLOCK_{name} missing)"})

    # Rule 5 — BLOCK_LIMIT. A module past the limit with no internal blocks is exactly the
    # "strategic blindness past ~800 lines" case the PBS leaf size exists to prevent.
    if len(lines) > 200 and not opened and "START_BLOCK_" not in text:
        warnings.append({"file": path, "line": len(lines), "rule": "block-limit",
                         "msg": f"{len(lines)} lines and no START_BLOCK markers (BLOCK_LIMIT 200) — split into blocks"})

    if profile == "autonomous":
        # Rule 2b — every exported symbol carries a FUNCTION_CONTRACT.
        for i, line in enumerate(lines, 1):
            m = EXPORTED.match(line)
            if not m:
                continue
            name = next((g for g in m.groups() if g), None)
            if not name:
                continue
            if not re.search(rf"START_CONTRACT:\s*{re.escape(name)}\b", text):
                errors.append({"file": path, "line": i, "rule": "function-contract-missing",
                               "msg": f"exported '{name}' has no FUNCTION_CONTRACT "
                                      f"(START_CONTRACT: {name}) — required by profile 'autonomous'"})

        # Rule 4 — logs anchored to blocks: [Module][function][BLOCK] …
        # Without this an agent reading a 500-line trace cannot locate where it is. LOFT-style anchors.
        has_log = re.search(r"\b(log(?:ger)?|console)\s*\.\s*\w+\s*\(", text)
        anchored = re.search(r"\[\w+\]\[\w+\]\[\w+\]", text)
        if has_log and not anchored:
            log_line = text.count("\n", 0, has_log.start()) + 1
            errors.append({"file": path, "line": log_line, "rule": "log-anchor-missing",
                           "msg": "logs present but none use the [Module][function][BLOCK_NAME] anchor "
                                  "(GRACE Lite rule 4) — an agent cannot navigate an unanchored trace"})

if as_json:
    print(json.dumps({"profile": profile, "files_checked": checked,
                      "errors": errors, "warnings": warnings,
                      "verdict": "pass" if not errors else "fail"}, indent=2, ensure_ascii=False))
    sys.exit(1 if errors else 0)

print(f"=== grace-lint · profile: {profile} · {checked} file(s) ===")
for e in errors:
    print(f"  ✗ {e['file']}:{e['line']} — {e['msg']}")
for w in warnings:
    print(f"  ⚠ {w['file']}:{w['line']} — {w['msg']}")
if not errors and not warnings:
    print("  ✓ GRACE Lite markup present and balanced")
print()
print(f"{len(errors)} error(s), {len(warnings)} warning(s).")
if errors:
    print("GRACE Lite is mandatory in every file (docs/human/PIPELINE.md §GRACE Lite).")
    print("Fix before commit. /scaffold writes these headers for you at module creation time.")
sys.exit(1 if errors else 0)
PY
