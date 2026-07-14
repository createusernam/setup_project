#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Restart a build-loop run from its attested start commit while archiving prior iterations.
# SCOPE: Stash current work, archive loop state, reset to the start commit, and increment restart metadata.
# DEPENDS: Bash, git, Python 3, and an initialized .build-loop directory.
# END_MODULE_CONTRACT
# Restart-from-scratch: roll back to start commit, archive iterations.
# Called when the evaluator's verdict is "restart" and the agent decides to act on it.

set -euo pipefail

cd "${1:-$(pwd)}"

if [ ! -f .build-loop/start-commit ]; then
  echo "[restart] No start_commit found. Run /build-loop first." >&2
  exit 1
fi

START_COMMIT=$(cat .build-loop/start-commit)
TIMESTAMP=$(date +%s)
RESTART_DIR=".build-loop/restart-$TIMESTAMP"

# Archive current state
mkdir -p "$RESTART_DIR"
git stash push -u -m "build-loop restart at $TIMESTAMP" 2>/dev/null || true
mv .build-loop/iterations "$RESTART_DIR/iterations" 2>/dev/null || true
mkdir -p .build-loop/iterations

# Hard reset to start commit
git reset --hard "$START_COMMIT"

# Increment restart counter in log
python3 - <<PY
import json, pathlib
p = pathlib.Path(".build-loop/iteration-log.json")
data = json.loads(p.read_text())
data["restart_count"] = data.get("restart_count", 0) + 1
data["last_restart"] = "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
data["iterations"] = []  # fresh slate for in-loop tracking
p.write_text(json.dumps(data, indent=2))
PY

echo "[restart] Reset to $START_COMMIT. Prior iterations archived to $RESTART_DIR/."
echo "[restart] Restart count now $(python3 -c 'import json; print(json.load(open(".build-loop/iteration-log.json"))["restart_count"])')"
