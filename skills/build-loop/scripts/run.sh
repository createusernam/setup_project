#!/usr/bin/env bash
# /build-loop orchestrator. Intended to be invoked from inside the SKILL.md workflow,
# not directly by the user. Sets up state directories, snapshots the start commit,
# validates contract attestation. Iteration spawning happens in the host agent via
# the Agent tool — this script just prepares the workspace.

set -euo pipefail

PROJECT_DIR=${1:-$(pwd)}
cd "$PROJECT_DIR"

# Contract present?
if [ ! -f contract.json ]; then
  echo "[build-loop] contract.json missing. Run /contract first." >&2
  exit 1
fi

# Attestation matches?
if [ ! -f .contract-attestation ]; then
  echo "[build-loop] .contract-attestation missing. Re-run /contract to lock the contract." >&2
  exit 1
fi

EXPECTED=$(tr -d '[:space:]' < .contract-attestation)
ACTUAL=$(sha256sum contract.json | awk '{print $1}')
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "[build-loop] Contract tampered. Expected sha256:$EXPECTED, got sha256:$ACTUAL." >&2
  echo "[build-loop] Re-run /contract to re-attest, then retry /build-loop." >&2
  exit 2
fi

# Git clean?
if ! git diff --quiet HEAD 2>/dev/null; then
  echo "[build-loop] Working tree dirty. Commit or stash before /build-loop — restart-from-scratch needs a clean rollback point." >&2
  exit 3
fi

# Init state directory
mkdir -p .build-loop/iterations
git rev-parse HEAD > .build-loop/start-commit
START_COMMIT=$(cat .build-loop/start-commit)

# Bootstrap iteration-log.json if absent
if [ ! -f .build-loop/iteration-log.json ]; then
  cat > .build-loop/iteration-log.json <<EOF
{
  "version": "1",
  "contract_sha": "$ACTUAL",
  "contract_path": "contract.json",
  "design_contract_path": $([ -f design-contract.json ] && echo '"design-contract.json"' || echo 'null'),
  "start_commit": "$START_COMMIT",
  "started": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "iterations": [],
  "final_verdict": null,
  "restart_count": 0
}
EOF
fi

echo "[build-loop] State initialized at .build-loop/"
echo "[build-loop] start_commit=$START_COMMIT"
echo "[build-loop] contract_sha=$ACTUAL"
echo "[build-loop] Ready for generator-evaluator cycle."
