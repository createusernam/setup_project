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
# [BuildLoop][verdict][DECISION] Structured verdict output is the only loop decision record.

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
duplicate_keys = []

def preserve_and_record_duplicates(pairs):
    document = {}
    for key, value in pairs:
        if key in document:
            duplicate_keys.append(key)
        document[key] = value
    return document

critique = json.loads(
    pathlib.Path(sys.argv[2]).read_text(),
    object_pairs_hook=preserve_and_record_duplicates,
)
contract = json.loads(pathlib.Path(sys.argv[3]).read_text())

raw_scores = critique.get("scores", {})
scores_shape_invalid = not isinstance(raw_scores, dict)
scores = raw_scores if isinstance(raw_scores, dict) else {}
criteria_by_id = {}
duplicate_criterion_ids = []
for criterion in contract["criteria"]:
    criterion_id = criterion["id"]
    if criterion_id in criteria_by_id:
        duplicate_criterion_ids.append(criterion_id)
    criteria_by_id[criterion_id] = criterion
expected_ids = set(criteria_by_id)
actual_ids = set(scores)
validation_errors = [
    f"duplicate JSON key in critique: {key}" for key in sorted(set(duplicate_keys))
]
if scores_shape_invalid:
    validation_errors.append("scores must be an object")
validation_errors.extend(
    f"duplicate contract criterion id: {criterion_id}"
    for criterion_id in sorted(set(duplicate_criterion_ids))
)
missing_ids = sorted(expected_ids - actual_ids)
unknown_ids = sorted(actual_ids - expected_ids)
if missing_ids:
    validation_errors.append(f"missing criterion scores: {', '.join(missing_ids)}")
if unknown_ids:
    validation_errors.append(f"unknown criterion scores: {', '.join(unknown_ids)}")

critiques = critique.get("critique_per_criterion", {})
evidence = critique.get("evidence_per_criterion", {})
if not isinstance(critiques, dict):
    validation_errors.append("critique_per_criterion must be an object")
    critiques = {}
if not isinstance(evidence, dict):
    validation_errors.append("evidence_per_criterion must be an object")
    evidence = {}

missing_critiques = sorted(expected_ids - set(critiques))
unknown_critiques = sorted(set(critiques) - expected_ids)
missing_evidence = sorted(expected_ids - set(evidence))
unknown_evidence = sorted(set(evidence) - expected_ids)
if missing_critiques:
    validation_errors.append(f"missing criterion critiques: {', '.join(missing_critiques)}")
if unknown_critiques:
    validation_errors.append(f"unknown criterion critiques: {', '.join(unknown_critiques)}")
if missing_evidence:
    validation_errors.append(f"missing criterion evidence: {', '.join(missing_evidence)}")
if unknown_evidence:
    validation_errors.append(f"unknown criterion evidence: {', '.join(unknown_evidence)}")
for cid, explanation in critiques.items():
    if not isinstance(explanation, str) or not explanation.strip():
        validation_errors.append(f"criterion {cid} critique must be non-empty text")
for cid, references in evidence.items():
    if (
        not isinstance(references, list)
        or not references
        or any(not isinstance(reference, str) or not reference.strip() for reference in references)
    ):
        validation_errors.append(f"criterion {cid} evidence must contain at least one non-empty ref")

invalid_score_ids = set()
for cid, score in scores.items():
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
        validation_errors.append(f"criterion {cid} score must be a number from 0 to 1")
        invalid_score_ids.add(cid)

total_weight = 0
weighted_sum = 0
must_pass_failures = []

for cid, c in criteria_by_id.items():
    w = c.get("weight", 1)
    total_weight += w
    if cid not in scores or cid in invalid_score_ids:
        continue
    score = scores[cid]
    weighted_sum += score * w
    if c.get("must_pass") and score < 0.99:
        must_pass_failures.append(cid)

weighted_score = weighted_sum / total_weight if total_weight else 0.0

threshold = contract.get("restart_threshold", {})
max_iter = threshold.get("max_iterations", 5)
no_prog = threshold.get("no_progress_iterations", 3)
floor = threshold.get("criteria_floor", 0.6)
criteria_floor_failures = sorted(
    cid for cid, score in scores.items()
    if cid in expected_ids and cid not in invalid_score_ids and score < floor
)

# Load iteration log to check progress
log_path = pathlib.Path(".build-loop/iteration-log.json")
log = json.loads(log_path.read_text())
prior_scores = [it.get("weighted_score", 0) for it in log["iterations"]]
restart_count = log.get("restart_count", 0)

# Verdict logic
verdict = "continue"

if validation_errors:
    verdict = "fail"
elif must_pass_failures:
    verdict = "fail"  # must_pass blocked → cannot pass yet
elif criteria_floor_failures:
    verdict = "fail"
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
    "criteria_floor_failures": criteria_floor_failures,
    "validation_errors": validation_errors,
    "verdict": verdict,
    "restart_count": restart_count
}
print(json.dumps(out, indent=2))
PY
