---
name: build-loop
description: Autonomous generator-evaluator cycle that builds a feature against contract.json, with the evaluator launching the live app via Playwright MCP for grading. Generator and evaluator have separate context windows. Loops until pass, restart, or max iterations. Use after /contract is written, for new features (not bugfixes — those use /diagnose + /tdd). User triggers — /build-loop, "autonomous build", "let it cycle", "generator-evaluator", "GAN loop". Requires Playwright MCP installed and contract.json present.
user-invocable: true
allowed-tools: "Read Write Edit Bash Glob Grep Agent TaskCreate TaskUpdate TaskList"
metadata:
  version: "1.0.0"
  authority: "Anthropic Applied AI talk, May 2026 — generator-evaluator with on-disk contract"
---

# /build-loop — Autonomous Generator-Evaluator Cycle

## Why this skill exists

From the Anthropic Applied AI talk (May 2026): the load-bearing pattern for long-running coding agents is a **generator and evaluator in separate context windows**, grading against a **contract negotiated on disk before any code is written**.

Three rules from the talk that this skill enforces:

1. **Evaluator never sees generator's reasoning or traces.** Sycophancy contagion otherwise.
2. **Evaluator launches the live app**, not reads diffs. Playwright/Chrome MCP clicks, types, screenshots, measures.
3. **Restart > patch on hard failures.** Use the contract's restart threshold instead of accumulating low-progress patches.

## Where this fits

```
/planning-with-files → /design-rubric (UI only) → /contract → /build-loop → /code-review-expert → ship
                                                              ▲
                                                              you are here
```

For **bugfixes**: don't use this skill. Use `/diagnose` → `/tdd`. /build-loop is for greenfield/feature work with subjective quality dimensions (UI, design, originality).

## Prerequisites — HARD GATE

Validate before any iteration starts. Halt with a clear message if any check fails. **Do not proceed with partial setup** — the whole point of the contract is that the autonomous cycle has no humans in the loop.

```
1. contract.json exists at project root
2. .contract-attestation exists and matches sha256(contract.json)
3. contract.json has criteria.length >= 10
4. contract.json has no must_pass criteria with verify.method === "manual"
   (humans gate must_pass before autonomous runs; manual ≠ autonomous)
5. If contract.json.is_frontend === true:
     5a. user_flow.primary_path is non-empty
     5b. design-contract.json exists at project root
     5c. .design-contract-attestation exists and matches sha256(design-contract.json)
6. If contract.json.is_frontend || contract.json.is_backend:
     6a. integrations.data_flow is non-empty
     6b. at least one of integrations.frontend_calls or integrations.backend_endpoints is non-empty
7. Playwright MCP server is reachable
   (Claude Code: `claude mcp list | grep playwright`
    OpenCode:    check `~/.config/opencode/opencode.json` mcp.playwright.enabled)
8. Dev server command runs cleanly: contract.json.verify_commands.dev_server
9. Git working tree is clean (no uncommitted changes — restart-from-scratch needs a rollback point)
10. Routed models available: run `bash ~/.claude/scripts/pipeline-preflight.sh 6` — implementer/
    implementation/test/acceptance profiles are bound in `model-bindings.json` and distinct where required.
    (Closes the "cycle stalls on a missing model" gap.)
11. GRACE Lite markup is clean on the code the loop will edit:
    `bash ~/.claude/scripts/grace-lint.sh --profile autonomous` exits 0.
    Not cosmetic: the loop has no human in it. The generator navigates by MODULE_CONTRACT /
    FUNCTION_CONTRACT anchors, and the evaluator's `trace` criteria grade against the
    [Module][function][BLOCK] log anchors. Unmarked code blinds both halves of the cycle.
    If this fails on a greenfield feature, you skipped `/scaffold` — run it.
```

If any check fails, print a precise diagnostic:

```
[build-loop] HALT — preconditions failed:
  ✗ user_flow.primary_path is empty (contract.json line 23)
    Fix: re-run /contract and fill primary_path. Each step is a Playwright-executable action.
  ✗ Playwright MCP not reachable
    Fix: claude mcp add playwright -- npx -y @playwright/mcp@latest
         or for OpenCode, edit ~/.config/opencode/opencode.json

Cycle aborted. No code generated.
```

## Workflow

### 1. Setup

```bash
# Verify contract attestation matches
ACTUAL=$(sha256sum contract.json | awk '{print $1}')
EXPECTED=$(cat .contract-attestation 2>/dev/null)
[ "$ACTUAL" = "$EXPECTED" ] || { echo "Contract tampered or unattested. Run /contract again."; exit 1; }

# Snapshot current commit for restart point
git rev-parse HEAD > .build-loop/start-commit
mkdir -p .build-loop/iterations
```

Initialize `iteration-log.json`:

```json
{
  "version": "1",
  "contract_sha": "abc123...",
  "contract_path": "contract.json",
  "design_contract_path": "design-contract.json",
  "start_commit": "deadbeef",
  "started": "2026-05-19T12:00:00Z",
  "iterations": [],
  "final_verdict": null
}
```

### 2. The cycle

For each iteration `n = 1, 2, ...`:

#### 2a. Generator phase

Spawn a **generator sub-agent** (`Agent` tool, `subagent_type=general-purpose`, isolated context):

Inputs the generator receives:
- `contract.json` (full)
- `design-contract.json` (if present)
- `task_plan.md`, `findings.md`, `progress.md` (planning artifacts)
- Previous iteration's `critique.json` if `n > 1` (the evaluator's verdict — **not** the evaluator's reasoning trace)
- File diffs from previous iterations (cumulative)

Inputs the generator does NOT receive:
- Evaluator's internal reasoning, scratch notes, or tool traces
- Other iterations' generator contexts

Generator's task:
- Implement against the contract, using critique.json to target what failed last time
- Make minimal, focused diff
- Write `iterations/<n>/generator-summary.md` — a short (≤500 word) report of what was changed and why
- Update `progress.md` with what was done
- Write `iterations/<n>/handoff.json` in the COMPAT schema (`handoff.md`): `agent_role` = generator
  persona (frontend/backend-implementer), `model_used`, `done`, `files_touched`, `uncertain_about`,
  `collegium_verdict: "needs-review"`, `next_agent: "evaluator"`. This is an **audit record for the
  orchestrator** — it is NOT handed to the evaluator (the isolation in 2b is deliberate).

Generator's persona — pick by domain:
- **Frontend** (`design-contract.json` present) → frontend-developer
- **Backend** → backend-developer
- **Full-stack feature** → frontend-developer + backend-developer in sequence (two sub-agents)

#### 2b. Evaluator phase

Spawn an **evaluator sub-agent** (separate Agent invocation, independent context):

Inputs the evaluator receives:
- `contract.json` (full)
- `design-contract.json` (if present)
- The **diff** of changes in this iteration (not the generator's summary, not its reasoning)
- Playwright MCP access
- `iterations/<n>/screenshots/` — empty directory to write into

Inputs the evaluator does NOT receive:
- `generator-summary.md` (would muddy critical thinking per Anthropic talk)
- Any previous critique.json (each evaluation is independent — sycophancy resistance)
- Generator's internal scratch

Evaluator's task:
- Start the dev server (`verify_commands.dev_server`)
- For each criterion in `contract.json`:
  - If `verify.method` is `grep`/`test`/`typecheck`/`build`/`lint` — run the command, exit code 0 = pass
  - If `verify.method` is `playwright` — execute the steps via Playwright MCP, screenshot key states to `iterations/<n>/screenshots/`, score 0–1
  - If `verify.method` is `trace` — run `verify.command`, capture stdout+stderr to
    `iterations/<n>/traces/<criterion-id>.log`, then grade the **trajectory**:
      1. every anchor in `expect_sequence` appears, **in that order** (interleaving lines are fine) — a
         missing or reordered anchor scores 0;
      2. no anchor in `forbid` appears — any match scores 0;
      3. **semantic verdict on the captured trace**: read it and state whether the trajectory is coherent
         for `verify.flow` — a retry that "succeeded", a fallback that swallowed a failure, a path that
         passed by accident. Put the reasoning in `critique_per_criterion`, not just a number.
    A trace criterion grades *how the system got there*; an assertion only grades where it landed. The
    generator can satisfy assertions with code that is wrong everywhere they don't look — the trajectory
    is far harder to fake. (Contract-side schema: `/contract` §Verify methods.)
  - If `verify.method` is `manual` — make a judgment call, write reasoning into critique
- Compute weighted score: `Σ(score_i × weight_i) / Σ(weight_i)`
- Check must_pass criteria — any failure with `must_pass: true` → verdict `fail` regardless of weighted score
- Write `iterations/<n>/critique.json`:

```json
{
  "iteration": 3,
  "evaluator_started": "2026-05-19T13:42:00Z",
  "scores": {
    "c1": 1.0,
    "c2": 0.4,
    "c3": 1.0
  },
  "weighted_score": 0.78,
  "must_pass_failures": [],
  "verdict": "fail",
  "blocking_criteria": ["c2"],
  "critique_per_criterion": {
    "c2": "Submit button uses hardcoded #007aff at src/components/Form.tsx:42. Expected: var(--color-action-primary). Screenshot: iterations/3/screenshots/form-submit.png."
  },
  "summary": "Functionality passes (c1, c3). Design token violation in c2 — single grep hit. Targeted fix should resolve in next iteration."
}
```

Then write `iterations/<n>/handoff.json` (COMPAT schema): `agent_role: "test-owner"`, `model_used`,
`collegium_verdict` (`agreed` if verdict pass, else `disagreed`), `test_status`, `blocking_criteria`
→ `uncertain_about`, `next_agent: "orchestrator"`. Also an audit record — the evaluator stays blind
to the generator's handoff.

#### 2c. Decision

Verdict rules (in order):

1. **pass** — `weighted_score ≥ 1.0 - epsilon` AND no `must_pass` failures AND no `criteria_floor` violations → cycle ends successfully
2. **restart** — `n > restart_threshold.no_progress_iterations` AND weighted score has not improved in that window → roll back to `start_commit`, increment restart counter, reset to iteration 1.
3. **abort** — total restart count ≥ 2, or `n ≥ max_iterations` even after restart — halt and hand back to user
4. **continue** — otherwise, loop to step 2a with `n+1`

Append iteration record to `iteration-log.json`.

#### 2d. Restart-from-scratch

When verdict is `restart`:

```bash
git stash push -m "build-loop restart $(date -Iseconds)"  # preserve in case user wants forensics
git reset --hard $(cat .build-loop/start-commit)
echo "Restarting from clean state. Critiques from prior attempts archived under .build-loop/restart-<n>/"
mv iterations/ .build-loop/restart-$(date +%s)/iterations/
```

**Important**: per the Anthropic talk, restart is most effective when the *evaluator* triggers it — not the generator. The evaluator says "criterion X has not progressed across 3 iterations; the approach is wrong, not the polish." Then a fresh generator starts with all prior critiques in its context (so it doesn't repeat the same approach).

### 3. Handoff

On `pass`:

- Print a summary table to the user.
- Run `/code-review-expert` automatically (already contract-aware) for the final sanity check.
- Recommend manual visual polish for any criterion with `manual` verify.

On `abort`:

- Print all critiques from the last 3 iterations.
- Suggest the user revisit `contract.json` — may have specified the impossible, may have missed a key constraint.

## Tools and infrastructure

### Playwright MCP

Microsoft's official `@playwright/mcp` — works with any MCP-compatible CLI. The evaluator needs it.

**Claude Code:**
```bash
claude mcp add playwright -- npx -y @playwright/mcp@latest
```

**OpenCode** — add to `~/.config/opencode/opencode.json` (or project `.opencode/opencode.json`):
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "@playwright/mcp@latest", "--headless"],
      "enabled": true
    }
  }
}
```

**Generic MCP client (Cursor, etc.):**
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless"]
    }
  }
}
```

WSL2 / no display → always pass `--headless`. Playwright ships its own browsers (chromium/firefox/webkit), no system Chrome required. Node 18+ needed.

If MCP not present when /build-loop is invoked, halt and tell the user to install. **Do not** try to install it autonomously — MCP changes touch user config.

### Trace capture

Every iteration's transcripts are dumped to `.build-loop/iterations/<n>/traces/` via the user's `PostToolUse` trace-capture hook. The user can grep them post-hoc to find prompt-tuning opportunities.

This is the "trace-reading is the primary debug loop" pattern from the Anthropic talk. Don't skip the post-mortem read.

## State files — JSON, and where JSON stops

Per the Anthropic empirical finding: **models overwrite markdown more aggressively than JSON**. So
the loop's *control* state is JSON — small, schema'd, parsed by scripts, read whole:

- `contract.json` (the rubric — also parsed by `verdict.sh`, `pipeline-preflight.sh`)
- `iteration-log.json` (append-only audit; the orchestrator reads it, agents don't)
- `iterations/<n>/critique.json`
- `iterations/<n>/handoff.json` (COMPAT audit record per role — orchestrator reads it; never passed between the isolated roles)
- `.build-loop/start-commit` (file, single sha)

**Where JSON stops:** the *evidence* the agents read in bulk — traces, graphs, plans — is XML-like,
never JSON. Long JSON degrades as read-context (the model ends up counting braces; OpenAI's GPT-4.1
guide says the same, and it is why GRACE artifacts are `.xml`). The two findings don't conflict —
they're about different operations, write-resistance vs read-navigability. The rule and the size
threshold: `docs/agent/COMPAT.md` §State format.

Concretely, in this loop: `iterations/<n>/traces/*.log` carry `[Module][function][BLOCK]` anchors and
are read by the evaluator for `trace` criteria; `docs/*.xml` carry the graph the generator navigates.
Neither is ever converted to JSON to "keep the state uniform".

`progress.md` is still updated for human readability — but its content is mirrored to `progress.json` by the modified `/planning-with-files`.

## Restart vs patch — concrete heuristic

Restart when:
- The same criterion has scored < 0.5 for 3 consecutive iterations
- Weighted score has decreased between iterations (regression)
- A `must_pass` criterion was passing in iteration N-1 but fails now
- Generator's critique reading produces "I'll try X again but harder" — the approach is wrong, not the execution

Patch when:
- Score moving up monotonically, even slowly
- Specific localized criterion failure (e.g., one CSS token swap)
- No regressions, just incomplete coverage

The evaluator makes this call, not the generator. Encoded in critique.json's `recommend_restart` boolean field (added by evaluator).

## Anti-patterns

| Don't | Do instead |
|-------|-----------|
| Generator and evaluator in same context window | Two separate `Agent` invocations |
| Evaluator reads generator-summary.md | Evaluator reads only the diff + screenshots |
| Pass critique-history into evaluator | Each evaluation independent |
| Patch through 8 iterations of slow progress | Restart at iteration 4 if no progress in window |
| Run without dev server | The whole point is live grading |
| Run without contract.json | The whole point is grading against a fixed rubric |
| Modify contract.json mid-loop | Re-attest, document the change, restart |
| Use for bugfixes | Use `/diagnose` + `/tdd` instead |
| Skip the integration/user_flow check "to save time" | The whole purpose of the gate is to prevent silent hallucination of API contracts during autonomous runs |

## Portable invocation

The artifacts (`contract.json`, `design-contract.json`, `iteration-log.json`, `critique.json`) are portable across any CLI/model. Playwright MCP is portable (MCP standard via stdio). What's CLI-specific:

| Component | Agent-native runtime | General coding runtime | Fallback |
|-----------|----------------------|------------------------|----------|
| Skill invocation | native | installed skill/reference | load SKILL.md explicitly |
| Separate generator/evaluator contexts | agent primitive | runtime subagent primitive | sequential roles with explicit context reset |
| Playwright MCP | MCP client | MCP client | run equivalent browser checks manually |
| Git restart and iteration state | shell/files | shell/files | portable |

**Single-runtime fallback without a separate-agent primitive:**

Instead of two `Agent` invocations, the cycle becomes one session that you manually role-frame:

```
Turn 1 (role: generator): Read contract.json + critique.json (if iteration > 1).
                          Implement. Write diff. Save generator-summary.md.
Turn 2: /clear
Turn 3 (role: evaluator): Read contract.json + git diff (NOT generator-summary.md).
                          Launch dev server. Replay user_flow via Playwright MCP.
                          Grade. Write critique.json.
Turn 4: /clear
Turn 5 (role: orchestrator): Read critique.json. Compute verdict via scripts/verdict.sh.
                              Decide continue/restart/pass/abort.
Loop or stop.
```

This is weaker than Claude Code's true separate contexts (the model may "remember" being the generator), but the `/clear` between turns blunts contagion. Use this only when separate-agent primitive isn't available.

## Files

- `scripts/run.sh` — orchestrator (sets up dirs, runs git snapshot, dispatches to Agent invocations)
- `scripts/restart.sh` — rollback to start commit, archive iterations
- `scripts/verdict.sh` — compute weighted score from critique.json
- `templates/critique.json` — example evaluator output
- `templates/iteration-log.json` — example state file
