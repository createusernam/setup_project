#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Append immutable harness telemetry events used to calibrate pipeline gates and costs.
# SCOPE: Validate a bounded event vocabulary and append one JSON object to .pipeline-events.jsonl.
# DEPENDS: Python standard library and a writable project directory.
# END_MODULE_CONTRACT
"""Append one pipeline telemetry event without rewriting prior events."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

EVENTS = {"phase_start", "phase_end", "gate_wait", "gate_failure", "rework", "human_disagreement", "deployment", "rollback", "escaped_defect", "user_outcome"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=sorted(EVENTS))
    parser.add_argument("--phase", required=True)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--model")
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--tokens", type=int)
    parser.add_argument("--cost-usd", type=float)
    parser.add_argument("--result", required=True)
    parser.add_argument("--evidence-ref", action="append", default=[])
    args = parser.parse_args()
    payload = {
        "at": datetime.now(timezone.utc).isoformat(), "event": args.event, "phase": args.phase,
        "model": args.model, "duration_ms": args.duration_ms, "tokens": args.tokens,
        "cost_usd": args.cost_usd, "result": args.result, "evidence_refs": args.evidence_ref,
    }
    path = args.project.resolve() / ".pipeline-events.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
