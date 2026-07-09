#!/usr/bin/env bash
# pipeline-preflight.sh — gate before a pipeline phase. Validates that the phase can run
# WITHOUT a human having to intervene for a preventable reason:
#   1. the models the phase routes to are declared available (env manifest in the ledger)
#   2. the phase's required input artifacts exist and match their recorded attestation
#   3. any required human-in-the-loop gate for the phase has been signed off
# Exits non-zero with a diagnostic on the first failure. Pipeline-wide generalisation of
# /build-loop's hard gate. The model MATCH itself stays agent-cooperative (a shell can't
# detect the running model) — see model-check.sh.
#
# Usage: bash scripts/pipeline-preflight.sh <phase> [project_dir]
#        project_dir defaults to $PWD; ledger is <project_dir>/.pipeline-state.json
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MR="$ROOT/model-routing.json"
PHASE="${1:-}"
PROJ="${2:-$PWD}"
LEDGER="$PROJ/.pipeline-state.json"
[ -n "$PHASE" ] || { echo "usage: pipeline-preflight.sh <phase> [project_dir]"; exit 2; }
[ -f "$MR" ] || { echo "preflight: model-routing.json not found at $MR"; exit 2; }

python3 - "$MR" "$LEDGER" "$PHASE" "$PROJ" <<'PY'
import json, sys, os, hashlib
mr_path, ledger_path, phase, proj = sys.argv[1:5]
mr = json.load(open(mr_path))
p = mr.get("phases", {}).get(phase)
if not p:
    print(f"preflight: phase '{phase}' unknown. Known: {', '.join(mr.get('phases',{}))}")
    sys.exit(2)

if not os.path.exists(ledger_path):
    print(f"preflight: no ledger at {ledger_path}.")
    print("  Expected only at the very first phase. Create it from")
    print("  templates/project/.pipeline-state.json and set models_available.")
    if phase != "-1":
        sys.exit(3)
    ledger = {"models_available": [], "artifacts": {}, "gates_passed": [], "human_gates": {}}
else:
    ledger = json.load(open(ledger_path))

fails = []
avail = set(ledger.get("models_available", []))

def any_available(spec):
    return any(tok.strip() in avail for tok in spec.split("|"))

required = p.get("required_model", "")
if required and not any_available(required):
    fails.append(f"model: phase needs one of [{required}] but models_available={sorted(avail)}. "
                 f"Add it to {ledger_path}.models_available (declared env manifest).")

roles = {k: p[k] for k in ("implementer","test_owner","acceptor") if k in p}
if roles:
    chosen = {}
    for role, spec in roles.items():
        got = [t.strip() for t in spec.split("|") if t.strip() in avail]
        if not got:
            fails.append(f"model: collegium role '{role}' needs one of [{spec}] — none available.")
        else:
            chosen[role] = got[0]
    if len(set(chosen.values())) < len(chosen):
        fails.append(f"collegium: roles must be DIFFERENT models, got {chosen}.")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

for art in p.get("requires", []):
    ap = os.path.join(proj, art)
    if not os.path.exists(ap):
        fails.append(f"input: required artifact '{art}' missing (phase {phase} consumes it).")
        continue
    rec = ledger.get("artifacts", {}).get(art, {})
    if isinstance(rec, dict) and rec.get("sha256"):
        actual = sha256(ap)
        if actual != rec["sha256"]:
            fails.append(f"input: '{art}' changed since attested "
                         f"(ledger {rec['sha256'][:12]}…, actual {actual[:12]}…). "
                         f"Re-run the phase that owns it or update the ledger.")

hg = p.get("human_gate")
if hg:
    sig = ledger.get("human_gates", {}).get(hg, {})
    if not sig.get("by"):
        fails.append(f"human_gate: '{hg}' not signed. A human decision is required before this "
                     f"phase may proceed. Record it in {ledger_path}.human_gates.{hg} "
                     f'= {{"by":"<name>","at":"<iso>"}}.')

print(f"=== preflight · phase {phase} · {p.get('skill','?')} ===")
if fails:
    print("HALT — preconditions failed:")
    for f in fails:
        print(f"  ✗ {f}")
    print("\nNo phase work should start until these pass.")
    sys.exit(1)
print("✓ models available   ✓ inputs present & attested   ✓ human gate satisfied")
print(f"required model: {required}   (AGENT: confirm your running model matches — shell can't detect it)")
sys.exit(0)
PY
