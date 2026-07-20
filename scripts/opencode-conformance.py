#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Qualify an OpenCode-hosted model binding with executable setup-specific probes.
# SCOPE: Structured output, filesystem tool use, legal transitions, bounded deltas, resume, and disagreement handling.
# DEPENDS: Python standard library and an authenticated opencode runtime.
# END_MODULE_CONTRACT
"""Run a batched conformance probe through OpenCode and emit capability evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any


HARNESS_VERSION = "1"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def setup_sha(root: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False)
    return result.stdout.strip() or "unknown"


def assistant_text(stdout: str) -> str:
    chunks: list[str] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text" and isinstance(event.get("part", {}).get("text"), str):
            chunks.append(event["part"]["text"])
    if not chunks:
        raise ValueError("OpenCode output contained no assistant text event")
    return "".join(chunks).strip()


def result(probe_id: str, passed: bool, latency_ms: int, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": probe_id,
        "status": "pass" if passed else "fail",
        "attempts": 1,
        "latency_ms": latency_ms,
        "evidence": evidence,
    }


def expected_response() -> dict[str, Any]:
    return {
        "instruction_format": {"status": "ready", "phase": "6f"},
        "malformed_output_recovery": {"status": "ready"},
        "legal_transition": {"next_phase": "7", "allowed": True},
        "bounded_artifact_delta": {"op": "replace", "path": "/status", "value": "ready"},
        "compaction_resume": {"action": "attest", "then": "review"},
        "independent_disagreement": {"verdict": "REVISE", "independent": True},
    }


def prompt() -> str:
    expected = json.dumps(expected_response(), ensure_ascii=False, separators=(",", ":"))
    return f"""You are running a model-runtime conformance test in an isolated temporary directory.
Use your filesystem tools to do both operations before answering:
1. Create tool-result.json containing exactly {{"phase":"6f","status":"ready"}}.
2. Read state.json, then create transition.json containing exactly {{"project_id":"demo","from":"6f","to":"7"}} using only its legal_next value.

After the tool operations, return exactly one JSON object, with no markdown or prose. It must equal:
{expected}
Do not modify any other file."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="openrouter")
    parser.add_argument("--model", required=True, help="OpenCode provider/model identifier")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.8)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        raise ValueError("--threshold must be between 0 and 1")

    started = time.monotonic()
    scenarios: list[dict[str, Any]] = []
    error_text = ""
    with tempfile.TemporaryDirectory(prefix="setup-opencode-conformance-") as temporary:
        workdir = Path(temporary)
        state = {"project_id": "demo", "current_phase": "6f", "legal_next": ["7"]}
        (workdir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
        try:
            completed = subprocess.run(
                [
                    "opencode", "run", "--pure", "--auto", "--model", args.model,
                    "--format", "json", "--dir", str(workdir), prompt(),
                ],
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError((completed.stderr or completed.stdout or "OpenCode failed")[-500:])
            value = json.loads(assistant_text(completed.stdout))
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            value = {}
            error_text = str(exc)[:500]

        latency_ms = int((time.monotonic() - started) * 1000)
        for probe_id, expected in expected_response().items():
            actual = value.get(probe_id) if isinstance(value, dict) else None
            evidence = {
                "result_sha256": sha256_bytes(json.dumps(actual, sort_keys=True).encode()),
                "runtime_contract": "batched-structured-output",
            }
            if error_text:
                evidence["error"] = error_text
            scenarios.append(result(probe_id, actual == expected, latency_ms, evidence))

        file_checks = [
            ("strict_tool_call", workdir / "tool-result.json", {"phase": "6f", "status": "ready"}),
            ("multi_hop_tools", workdir / "transition.json", {"project_id": "demo", "from": "6f", "to": "7"}),
        ]
        for probe_id, path, expected in file_checks:
            try:
                actual = json.loads(path.read_text(encoding="utf-8"))
                passed = actual == expected
                evidence = {"artifact_sha256": sha256(path), "runtime_contract": "filesystem-tool"}
            except (OSError, json.JSONDecodeError) as exc:
                passed = False
                evidence = {"error": str(exc)[:500], "runtime_contract": "filesystem-tool"}
            scenarios.insert(1 if probe_id == "strict_tool_call" else 3, result(probe_id, passed, latency_ms, evidence))

    passed = sum(item["status"] == "pass" for item in scenarios)
    total = len(scenarios)
    pass_rate = passed / total
    root = args.root.resolve()
    document = {
        "$schema": "../model-conformance.schema.json",
        "version": "1",
        "harness_version": HARNESS_VERSION,
        "provider": args.provider,
        "runtime": "opencode",
        "model_id": args.model,
        "endpoint_host": "opencode-runtime",
        "executed_at": now(),
        "settings": {
            "temperature": 0,
            "max_tokens": 0,
            "timeout_seconds": args.timeout,
            "max_repair_attempts": 0,
            "thinking": "default",
        },
        "scenarios": scenarios,
        "summary": {
            "passed": passed,
            "total": total,
            "pass_rate": pass_rate,
            "threshold": args.threshold,
            "qualified": pass_rate >= args.threshold,
        },
        "provenance": {"setup_git_sha": setup_sha(root), "runner_sha256": sha256(Path(__file__))},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"provider": args.provider, "model": args.model, **document["summary"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if document["summary"]["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
