#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Summarize completion from canonical JSON planning state with legacy Markdown fallback.
# SCOPE: Resolve one plan file/directory and always report status through stdout.
# DEPENDS: Bash, Python 3, planning-state.py, and optional legacy task_plan.md.
# END_MODULE_CONTRACT
set -u

TARGET="${1:-.}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -f "$TARGET" ]; then PLAN_DIR="$(dirname -- "$TARGET")"; else PLAN_DIR="$TARGET"; fi

if [ -f "$PLAN_DIR/task_plan.json" ]; then
    RESULT="$(python3 "$SCRIPT_DIR/planning-state.py" check "$PLAN_DIR" 2>/dev/null)"
    COMPLETE="$(printf '%s' "$RESULT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["complete"])')"
    TOTAL="$(printf '%s' "$RESULT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["total"])')"
elif [ -f "$PLAN_DIR/task_plan.md" ]; then
    TOTAL="$(grep -c '### Phase' "$PLAN_DIR/task_plan.md" || true)"
    COMPLETE="$(grep -cF '**Status:** complete' "$PLAN_DIR/task_plan.md" || true)"
else
    echo "[planning-with-files] No planning state found."
    exit 0
fi

if [ "$TOTAL" -gt 0 ] && [ "$COMPLETE" -eq "$TOTAL" ]; then
    echo "[planning-with-files] ALL PHASES COMPLETE ($COMPLETE/$TOTAL)."
else
    echo "[planning-with-files] Task in progress ($COMPLETE/$TOTAL phases complete). Update canonical JSON before stopping."
fi
exit 0
