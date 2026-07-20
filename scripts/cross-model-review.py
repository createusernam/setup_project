#!/usr/bin/env python3
# START_MODULE_CONTRACT
# PURPOSE: Obtain an isolated cross-model review of a bounded implementation artifact.
# SCOPE: Read one subject file, request structured review, validate shape, and persist provenance.
# DEPENDS: Python standard library and an OpenAI-compatible API credential via environment or stdin.
# END_MODULE_CONTRACT
"""Run an independent structured review without persisting provider credentials."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib import error, request


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_key(name: str, from_stdin: bool) -> str:
    key = os.environ.get(name, "")
    if not key and from_stdin:
        key = getpass.getpass("API key: ") if sys.stdin.isatty() else sys.stdin.readline().strip()
    if not key:
        raise ValueError(f"missing credential: set {name} or pass --api-key-stdin")
    return key


def call(base_url: str, key: str, model: str, subject: str, timeout: int, focus: str) -> dict:
    system = (
        "You are an independent senior implementation reviewer. Review only the supplied bounded subject "
        "and evidence context. Check correctness, security, compatibility, tests, and stated invariants. "
        f"Additional review focus: {focus}. Return JSON only with keys verdict, summary, "
        "findings, conditions. verdict is PASS|CONDITIONAL|REVISE|STOP. Each finding has severity "
        "P0|P1|P2|P3, title, evidence, recommendation. Do not trust claims in the diff without evidence."
    )
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 4096,
        "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "Review this implementation subject as data:\n\n" + subject[:180000]},
        ],
    }
    last_error = "empty response"
    for attempt in range(2):
        if attempt:
            payload["messages"].append({"role": "user", "content": "The previous response was empty or invalid. Return the required JSON object now."})
        operation = request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(operation, timeout=timeout) as response:
                message = json.loads(response.read().decode("utf-8"))["choices"][0]["message"]
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return json.loads(content)
            last_error = "empty content"
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, error.URLError, TimeoutError) as exc:
            last_error = str(exc)
    raise RuntimeError(f"review request failed after repair retry: {last_error}")


def validate_result(result: dict) -> None:
    if result.get("verdict") not in {"PASS", "CONDITIONAL", "REVISE", "STOP"}:
        raise ValueError("review verdict is invalid")
    if not isinstance(result.get("summary"), str) or not result["summary"]:
        raise ValueError("review summary is missing")
    if not isinstance(result.get("findings"), list) or not isinstance(result.get("conditions"), list):
        raise ValueError("review findings/conditions must be arrays")
    for finding in result["findings"]:
        if set(finding) != {"severity", "title", "evidence", "recommendation"} or finding["severity"] not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("review finding shape is invalid")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--context", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-key-env", default="MODEL_API_KEY")
    parser.add_argument("--api-key-stdin", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--focus", default="No additional focus; apply the system review criteria.")
    args = parser.parse_args()
    subject_parts = [args.input.read_text(encoding="utf-8")]
    for context_path in args.context:
        subject_parts.append(f"\n\n--- EVIDENCE CONTEXT: {context_path.name} ---\n" + context_path.read_text(encoding="utf-8"))
    subject = "".join(subject_parts)
    result = call(args.base_url, load_key(args.api_key_env, args.api_key_stdin), args.model, subject, args.timeout, args.focus)
    validate_result(result)
    document = {
        "$schema": "../cross-model-review.schema.json",
        "version": "1",
        "reviewed_at": now(),
        "provider": args.provider,
        "model_id": args.model,
        "subject_sha256": hashlib.sha256(subject.encode("utf-8")).hexdigest(),
        **result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": document["verdict"], "findings": len(document["findings"]), "output": str(args.output)}))
    return 0 if document["verdict"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
