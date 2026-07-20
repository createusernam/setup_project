---
name: tdd
description: Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development.
---

# Test-Driven Development

## Philosophy

**Core principle**: Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests** are integration-style: they exercise real code paths through public APIs. They describe _what_ the system does, not _how_ it does it. A good test reads like a specification - "user can checkout with valid cart" tells you exactly what capability exists. These tests survive refactors because they don't care about internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or verify through external means (like querying a database directly instead of using the interface). The warning sign: your test breaks when you refactor, but behavior hasn't changed. If you rename an internal function and tests fail, those tests were testing implementation, not behavior.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This is "horizontal slicing" - treating RED as "write all tests" and GREEN as "write all code."

This produces **crap tests**:

- Tests written in bulk test _imagined_ behavior, not _actual_ behavior
- You end up testing the _shape_ of things (data structures, function signatures) rather than user-facing behavior
- Tests become insensitive to real changes - they pass when behavior breaks, fail when behavior is fine
- You outrun your headlights, committing to test structure before understanding the implementation

**Correct approach**: Vertical slices via tracer bullets. One test → one implementation → repeat. Each test responds to what you learned from the previous cycle. Because you just wrote the code, you know exactly what behavior matters and how to verify it.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
  ...
```

## Workflow

### 1. Planning

When exploring the codebase, use the project's domain glossary so that test names and interface vocabulary match the project's language, and respect ADRs in the area you're touching.

Before writing any code, derive the test surface from the attested contract. For a standalone bugfix,
derive the public interface from existing code and the regression behavior from the reproduction.

- [ ] Confirm the interface against contract/existing public behavior
- [ ] Derive behavior priority from must-pass criteria, critical paths, and the reproduced symptom
- [ ] Identify opportunities for [deep modules](deep-modules.md) (small interface, deep implementation)
- [ ] Design interfaces for [testability](interface-design.md)
- [ ] List the behaviors to test (not implementation steps)
- [ ] Escalate only an unresolved product-owned behavior or contract change

Do not ask an open-ended interface/test-priority question when approved artifacts or existing public
behavior answer it. If two materially different behaviors remain valid, present both, recommend one,
name the contract impact, and ask the owner of that behavior one blocking question.

**You can't test everything.** Prioritize must-pass outcomes, critical paths, complex logic, and the
regression symptom. A changed priority that alters acceptance returns to `/contract`.

### 2. Tracer Bullet

Write ONE test that confirms ONE thing about the system:

```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

This is your tracer bullet - proves the path works end-to-end.

### 3. Incremental Loop

For each remaining behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:

- One test at a time
- Only enough code to pass current test
- Don't anticipate future tests
- Keep tests focused on observable behavior

### 4. Refactor

After all tests pass, look for [refactor candidates](refactoring.md):

- [ ] Extract duplication
- [ ] Deepen modules (move complexity behind simple interfaces)
- [ ] Apply SOLID principles where natural
- [ ] Consider what new code reveals about existing code
- [ ] Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

## Contract awareness (v2.0+)

If `contract.json` exists at project root and is attested (`.contract-attestation` matches sha256):

- Use `contract.json.criteria` to derive the **test list** for this feature. Each criterion with `verify.method === "test"` becomes a test in the tracer-bullet sequence.
- Use `contract.json.user_flow.primary_path` and `error_paths` as integration-test scenarios (one test per path, executing through public interfaces).
- Use `contract.json.integrations.backend_endpoints` to drive API tests — request/response shapes are already specified.
- At the end of the red-green-refactor cycle, **run all `verify` commands from criteria** as a final gate before commit. Any failure = not done.

This makes /tdd contract-aware without surrendering its hand-on-keyboard nature. Different from `/build-loop`, which is fully autonomous — /tdd remains for **bugfix shape work** and **deliberate human-paced TDD**, with the contract as a target list rather than a rubric for an evaluator agent.

## When to choose /tdd vs /build-loop

| Situation | Use |
|-----------|-----|
| Bugfix | `/diagnose` → `/tdd` (no contract; the issue + regression test is the spec) |
| Greenfield feature, contract written, want human in the loop | `/tdd` reading contract criteria as test list |
| Greenfield feature, contract written, autonomous cycle wanted | `/build-loop` (generator+evaluator pair via Agent tool) |
| Hard-to-reach failure modes that need careful test design | `/tdd` (deliberate, slow, human judges abstractions) |
| Subjective quality dimensions (UI taste, design polish) | `/build-loop` (evaluator with Playwright + design-contract grading) |

## Separate-evaluator option (within /tdd)

For complex backend features where you want a sanity check between RED→GREEN passes without going full autonomous:

- After every 3-5 GREEN passes, spawn a one-shot evaluator sub-agent (via `Agent` tool) with the contract.json and the current diff.
- The evaluator reports gaps against criteria. You decide whether to continue or refactor.
- Cheaper than `/build-loop` (no Playwright launch, no iteration log), but catches the "I'm testing the wrong thing" failure mode.

Not the default. Default `/tdd` is single-context red-green-refactor.

## Handoff (pipeline Phase 6 mode)

When `/tdd` runs as a **Phase 6 build task** (contract present — not a standalone bugfix), close the
session by writing `handoff.json` in the COMPAT schema (`handoff.md`): `agent_role: "implementer"`
(or `"test-owner"` after a separate-evaluator checkpoint), `model_used`, `done`, `files_touched`,
`uncertain_about`, `test_status` (pass/fail/not_run + `tests_run`), `collegium_verdict`, `next_agent`
(`test-owner` / `acceptor` / `code-review-expert`), `next_agent_goal`. This is the Belief-State the
next agent reads — unlike `/build-loop`, `/tdd`'s handoff *is* passed forward (human-paced, no
adversarial isolation).

For a standalone bugfix (`/diagnose` → `/tdd`, no contract), the regression test itself is the record —
skip `handoff.json`.

For every pipeline route, including a standalone T0/T1 change in machine Phase `6f`, update root
`build-evidence.json`: choose `route` from `targeted|tdd|build-loop`, record commands and actual
`pass|fail|not_run` results, criterion evidence when a contract exists, trace references and
residual risks. Set `status` to `complete` only when the checks needed for review pass. The exact
shape and allowed values are in `build-evidence.schema.json`.
