#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Compute the weighted build-loop score and select its next verdict.
# SCOPE: Combine one critique with contract thresholds and prior iteration history; emit JSON only.
# DEPENDS: Bash, Python 3, contract.json, and initialized .build-loop iteration files.
# END_MODULE_CONTRACT
# Compute weighted score from critique.json and determine verdict against contract.json thresholds.
# Usage: verdict.sh <iteration-number>
#
# Outputs JSON to stdout:
#   { "iteration": N, "weighted_score": X, "must_pass_failures": [...], "verdict": "pass|fail|restart|abort" }

set -euo pipefail

N=$1
CRITIQUE=".build-loop/iterations/$N/critique.json"
CONTRACT="contract.json"

if [ ! -f "$CRITIQUE" ]; then
  echo "[verdict] $CRITIQUE not found" >&2
  exit 1
fi

python3 - "$N" "$CRITIQUE" "$CONTRACT" <<'PY'
import json, sys, pathlib
n = int(sys.argv[1])
critique = json.loads(pathlib.Path(sys.argv[2]).read_text())
contract = json.loads(pathlib.Path(sys.argv[3]).read_text())

scores = critique.get("scores", {})
criteria_by_id = {c["id"]: c for c in contract["criteria"]}

total_weight = 0
weighted_sum = 0
must_pass_failures = []

for cid, score in scores.items():
    c = criteria_by_id.get(cid)
    if not c:
        continue
    w = c.get("weight", 1)
    total_weight += w
    weighted_sum += score * w
    if c.get("must_pass") and score < 0.99:
        must_pass_failures.append(cid)

weighted_score = weighted_sum / total_weight if total_weight else 0.0

threshold = contract.get("restart_threshold", {})
max_iter = threshold.get("max_iterations", 5)
no_prog = threshold.get("no_progress_iterations", 3)
floor = threshold.get("criteria_floor", 0.6)

# Load iteration log to check progress
log_path = pathlib.Path(".build-loop/iteration-log.json")
log = json.loads(log_path.read_text())
prior_scores = [it.get("weighted_score", 0) for it in log["iterations"]]
restart_count = log.get("restart_count", 0)

# Verdict logic
verdict = "continue"

if must_pass_failures:
    verdict = "fail"  # must_pass blocked → cannot pass yet
elif weighted_score >= 0.99:
    verdict = "pass"
elif n >= max_iter:
    if restart_count >= 2:
        verdict = "abort"
    else:
        verdict = "restart"
elif len(prior_scores) >= no_prog:
    recent = prior_scores[-no_prog:] + [weighted_score]
    if max(recent) - min(recent) < 0.05:
        verdict = "restart" if restart_count < 2 else "abort"
elif weighted_score < floor and n >= 2:
    verdict = "restart" if restart_count < 2 else "abort"

out = {
    "iteration": n,
    "weighted_score": round(weighted_score, 3),
    "must_pass_failures": must_pass_failures,
    "verdict": verdict,
    "restart_count": restart_count
}
print(json.dumps(out, indent=2))
PY
