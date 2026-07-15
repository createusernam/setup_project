#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Resolve provider-neutral phase capability profiles through project-local model bindings.
# SCOPE: Read model-routing.json and model-bindings.json; print agent-verifiable runtime/model selections and role independence.
# DEPENDS: Bash, Python 3, model-routing.json, and project model-bindings.json.
# END_MODULE_CONTRACT
set -euo pipefail

SELF="$(readlink -f "${BASH_SOURCE[0]}")"
ROOT="$(cd "$(dirname "$SELF")/.." && pwd)"
PHASE="${1:-}"
PROJECT="${2:-.}"
MR="$ROOT/model-routing.json"
BINDINGS="$PROJECT/model-bindings.json"

[ -n "$PHASE" ] || { echo "usage: model-check.sh <phase> [project_dir]"; exit 2; }
[ -f "$MR" ] || { echo "model-check: routing not found at $MR"; exit 2; }
[ -f "$BINDINGS" ] || { echo "model-check: bindings not found at $BINDINGS (copy templates/project/model-bindings.json and configure it)"; exit 2; }

python3 - "$MR" "$BINDINGS" "$PHASE" <<'PY'
import json, sys
routing_path, bindings_path, phase = sys.argv[1:]
routing = json.load(open(routing_path, encoding="utf-8"))
document = json.load(open(bindings_path, encoding="utf-8"))
configured = document.get("bindings", {})
route = routing.get("phases", {}).get(phase)
if not route:
    print(f"model-check: phase {phase!r} unknown; known: {', '.join(routing.get('phases', {}))}")
    raise SystemExit(2)

failures = []
resolved = {}
known_profiles = set(routing.get("profiles", {}))
known_runtimes = {"claude", "codex", "opencode", "api", "manual", "self-hosted"}

if document.get("version") != "1":
    failures.append("bindings version must be '1'")
if not isinstance(configured, dict):
    failures.append("bindings must be an object")
    configured = {}
for profile in configured:
    if profile not in known_profiles:
        failures.append(f"unknown capability profile {profile!r}")

def valid_runtime(value):
    if value in known_runtimes:
        return True
    if not isinstance(value, str) or not value.startswith("custom:"):
        return False
    slug = value[7:]
    return bool(slug) and all(char.islower() or char.isdigit() or char in "._-" for char in slug) and slug[0].isalnum()

def bind(label, profile):
    entry = configured.get(profile, {})
    model_id = entry.get("model_id", "") if isinstance(entry, dict) else ""
    runtime = entry.get("runtime", "") if isinstance(entry, dict) else ""
    enabled = entry.get("enabled", True) if isinstance(entry, dict) else False
    if not isinstance(enabled, bool):
        failures.append(f"{label}: profile {profile!r} enabled must be true or false")
        return
    if not enabled:
        failures.append(f"{label}: profile {profile!r} is unbound or disabled")
        return
    if not valid_runtime(runtime):
        failures.append(f"{label}: profile {profile!r} runtime must be claude|codex|opencode|api|manual|self-hosted|custom:<slug>")
        return
    if not isinstance(model_id, str) or not model_id or any(char.isspace() for char in model_id):
        failures.append(f"{label}: profile {profile!r} model_id must be the exact non-empty runtime identifier without whitespace")
        return
    resolved[label] = model_id
    print(f"{label}: profile={profile} → runtime={runtime} model={model_id}")

print(f"=== Phase {phase} · {route.get('skill', '?')} ===")
if route.get("profile"):
    bind("primary", route["profile"])
for role, profile in route.get("roles", {}).items():
    bind(role, profile)

for group in route.get("distinct_roles", []):
    values = [resolved.get(role) for role in group]
    if None not in values and len(set(values)) != len(values):
        failures.append(f"roles {group} must resolve to different model IDs, got {values}")

if route.get("note"):
    print(f"note: {route['note']}")
if failures:
    print("HALT — model binding failed:")
    for failure in failures:
        print(f"  - {failure}")
    raise SystemExit(1)

print("AGENT VERIFY: confirm the running runtime/model matches the resolved binding for your role.")
print("On mismatch, stop, switch the user-configured binding/runtime, and re-run this check.")
PY
