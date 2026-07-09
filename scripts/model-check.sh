#!/usr/bin/env bash
# model-check.sh — surface the required model for a pipeline phase from model-routing.json.
#
# Usage:  bash scripts/model-check.sh <phase>      # e.g. -1, 0, 2, 2-PM, 4, 6
#
# HONEST LIMITATION: a shell script cannot detect which model is currently running. This SURFACES
# the requirement; the agent (which does know its own model from the system prompt) must confirm the
# match and switch if wrong. Enforcement is agent-cooperative, not OS-level. This is why there is no
# blocking hook — a hook that "enforces model per phase" without model detection would be theatre.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MR="$ROOT/model-routing.json"
PHASE="${1:-}"
[ -f "$MR" ] || { echo "model-check: model-routing.json not found at $MR"; exit 2; }
[ -n "$PHASE" ] || { echo "usage: model-check.sh <phase>   (e.g. -1, 0, 2, 2-PM, 4, 6)"; exit 2; }

python3 - "$MR" "$PHASE" <<'PY'
import json, sys
mr, phase = sys.argv[1], sys.argv[2]
d = json.load(open(mr))
p = d.get("phases", {}).get(phase)
if not p:
    print(f"model-check: phase '{phase}' not in model-routing.json. Known: {', '.join(d.get('phases', {}))}")
    sys.exit(2)
print(f"=== Phase {phase} · {p.get('skill','?')} ===")
print(f"required model: {p.get('required_model','?')}")
for k in ("workers", "implementer", "test_owner", "acceptor", "fallback"):
    if k in p:
        print(f"{k}: {p[k]}")
if p.get("note"):
    print(f"note: {p['note']}")
print()
print("AGENT VERIFY: confirm your current model matches 'required model' above.")
print(f"On mismatch, output: MODEL MISMATCH: phase {phase} requires {p.get('required_model')}, current is <detected> — switch and re-run. Then STOP.")
if any(k in p for k in ("implementer", "test_owner", "acceptor")):
    print("Collegium phase: also confirm implementer / test-owner / acceptor are DIFFERENT models.")
PY
