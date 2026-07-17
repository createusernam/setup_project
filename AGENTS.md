# Setup v2 — Development Harness

## Key files

- `README.md` — orientation and source-of-truth links; no operational command path
- `docs/human/SETUP.md` — sole install/runtime syntax and tool/model discovery guide
- `docs/human/PIPELINE.md` — sole project operator path from bootstrap through Phase 7 acceptance
- `docs/agent/COMPAT.md` — cross-runtime compatibility and provider-neutral capability bindings
- `docs/agent/PROMPT-FORMAT.md` — structured prompt standard (PCAM, Belief State, metamodel check)
- `skills/grace-ontology/SKILL.md` — GRACE annotation vocabulary (agent-facing)
- `skills/visualization/SKILL.md` — human-track views (Mermaid/HTML) at pipeline gates; concern → scale → notation
- `docs/human/ARCHITECTURE-GUIDE.md` — neutral architecture handoff: required inputs, portable outputs, quality checks, and pipeline re-entry; architecture method/tool is the user's choice

## Skills

All skills in `skills/` are symlinked by `install.sh` into both `~/.claude/skills/` (Claude) and
`~/.agents/skills/` (Codex and the shared Agent Skills convention). OpenCode scans both; the links
must resolve to the same canonical source.

| Skill | Purpose |
|-------|---------|
| `startup` | Create new project from template |
| `researcher` | Multi-agent research flow |
| `research-to-guide` | Turn validated research into an evidence-faithful user guide |
| `grill-with-docs` | Stress-test plan against domain model + docs |
| `planning-with-files` | PBS task decomposition |
| `pm-review` | PM gate (Phase 2-PM): plan vs brief before build |
| `design-first` | Wireframe → API contract for frontend |
| `risk-review` | T4 independent risk, rollout, and rollback gate (Phase 3r) |
| `contract` | Hard-gate contract before build |
| `judge` | LLM-as-Judge artifact evaluation |
| `to-issues` | Break plans into GitHub issues |
| `scaffold` | GRACE-marked module skeletons — the implementer's few-shot (Phase 5.5, strong model) |
| `build-loop` | Autonomous generator-evaluator cycle |
| `tdd` | Human-paced test-driven development |
| `code-review-expert` | Senior engineer code review |
| `diagnose` | Bug diagnosis loop |
| `triage` | Issue triage state machine |
| `guide-pdf` | Render markdown to styled PDF |
| `workctl` | Continue one explicit task safely across Claude Code, Codex, and OpenCode |
| `visualization` | Human-track Mermaid/HTML at pipeline gates |
| `grace-ontology` | GRACE annotation vocabulary for agents |
| `youtube-transcript` | Extract YouTube subtitles |
| `grace-init`, `grace-plan`, etc. | GRACE framework scaffolding |

## Templates

`templates/project/` — copied to new projects by `startup`.

## Per-project init

Use `startup` in the active runtime, then work from the created project. It creates the project
configuration and the `AGENTS.md → CLAUDE.md` link; do not replace that link manually.

## Global agent rules

Apply to every agent in every phase:

- **Model routing.** `model-routing.json` declares provider-neutral capability profiles and role independence; each project maps profiles to concrete runtime/model IDs in `model-bindings.json`. Before a phase, run `setup-model-check <phase> <project>`. Confirm the running identity matches the resolved binding and STOP on mismatch. A shell cannot detect the generating model. Collegium phases also require the configured roles to resolve to different model IDs.
- **Route skills before tools.** Apply `docs/agent/SKILL-ROUTING.md` in every CLI. A named or clearly matching skill is mandatory. In particular, load `planning-with-files` when the user asks to save and execute a plan, calls the work a large task, the task likely needs 5+ tool calls, or it must survive a CLI/provider switch.
- **Ask only at the knowledge boundary.** Inspect code and approved artifacts before asking. Ask only
  for a decision that is necessary for the next transition and owned by the respondent; give a
  recommended answer and consequences. Preserve `unknown`/`deferred` when evidence does not exist,
  and ask one blocking question per pause. Never ask a product owner to invent stack, module, test,
  logging, or mock details that a technical role can derive and review.
- **Arithmetic → calculator tool.** All arithmetic goes through the JS-sandbox calculator tool — never mental math. Token-by-token generation is unreliable for numbers.
- **Delete superseded code immediately.** Don't leave dead/orphaned code "just in case" — agents read existing code as few-shot examples, so dead code becomes a false template that propagates. `code-review-expert` flags it MUST-FIX.
- **GRACE Lite is checked, not trusted.** Every source file carries a MODULE_CONTRACT. Verify with `setup-grace-lint --changed` before you hand work on; `--profile autonomous` adds FUNCTION_CONTRACT on exports and block-anchored logs, and is a hard gate for `build-loop`. The rule used to live only in prose here — and prose is not an enforcement mechanism.
- **Validate skills against their runtime profile.** Run `python3 scripts/validate-skills.py --profile claude` for this repository. Claude fields such as `user-invocable` and `hooks` are valid here; use `--profile portable` only when packaging a runtime-neutral skill and treat its stricter rejection as a portability result, not a Claude error.
- **The handoff to a cheaper model is code, not a spec.** Writing a module spec costs roughly what writing the module costs, and a small model imitates code far more faithfully than it follows prose. Strong model → `scaffold` (contracts, blocks, log anchors, `IMPL:` directives, mocks, no logic); implementer fills the blocks and must not alter contracts, block names or log anchors.
- **Tests are feedback, not the spec.** The spec is the contract; the trace is the evidence. Grade trajectories (`verify.method: trace` against `[Module][function][BLOCK]` logs), not just return values — an LLM will otherwise write code that satisfies every assertion and breaks everywhere nobody asserted. Never hand an agent a bare `TEST FAIL`: say which anchor was missed, which branch fired, what the trace shows.

## Maintaining this file

AGENTS.md is a primary attention anchor — agents weight its CAPS/structure heavily (Top-k). That cuts both ways:

- **Stale rules anchor agents *wrongly*.** An outdated rule isn't ignored; it actively pulls output toward a dead decision (anchoring bias). Update or delete — never accumulate.
- **Opposite of positive GRACE anchoring.** `MODULE_CONTRACT` / `PBS_LEAF` are *intended* beacons on live code. A stale rule here is an *unintended* beacon on a dead decision. Keep the first, prune the second.
- Bounded ≤200 lines, curated, not append-only (global memory doctrine).

Full pipeline: `docs/human/PIPELINE.md`. Model routing: `docs/agent/COMPAT.md`.

For cross-runtime continuation, use `workctl` and name the task whenever more than one task may
exist. Durable files under `.workctl/tasks/<task-id>/` outrank runtime chat history; never guess the
active task from timestamps or recent prose. Root pipeline artifacts still own specification and
gate truth; `.workctl` owns task identity and execution continuity. Do not maintain `CONTINUITY.md`
for the same workctl-managed task. See `docs/human/WORKCTL.md`.
