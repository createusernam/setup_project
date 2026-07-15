#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Portable shell entrypoint for the semantic setup pipeline transition evaluator.
# SCOPE: Resolve symlinks and delegate one phase/project check to pipeline_preflight.py.
# DEPENDS: Bash, Python 3, scripts/pipeline_preflight.py.
# END_MODULE_CONTRACT
set -euo pipefail
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SELF")/.." && pwd)"
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || -z "${1:-}" ]]; then
  echo "usage: pipeline-preflight.sh <phase> [project_dir]"
  exit 0
fi
exec python3 "$ROOT/scripts/pipeline_preflight.py" "$@" --root "$ROOT"
