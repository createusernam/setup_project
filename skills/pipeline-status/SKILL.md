---
name: pipeline-status
description: Explain a setup-managed project's current pipeline stage, readiness, blockers, and one next action from durable on-disk state. Use when the user asks in any wording “на какой мы стадии?”, “что дальше?”, “где мы остановились?”, “продолжим проект”, “what stage are we at?”, “project status”, or returns to a project and wants orientation. Also use before resuming work when the current phase is uncertain. Do not use for the progress of one explicitly named cross-CLI task; that is workctl.
---

# Pipeline Status

Treat conversation as the primary interface. The user does not need to know or run pipeline
commands. Inspect the deterministic state behind the scenes and answer in human language.

## Inspect

1. Resolve the project root with `git rev-parse --show-toplevel`; otherwise use the current directory.
2. If `.pipeline-state.json` is absent, report that the repository is not yet connected to the setup
   pipeline. Do not create or modify anything during a status request. State one next action:
   invoke `startup` for a new project, or ask the agent to adopt the existing repository.
3. Run `setup-pipeline status` from the project root. It executes the read-only validator bound to
   the current phase in `.pipeline-state.json`; a phase-process failure overrides global READY. If the command is missing, report a setup
   installation/discovery problem and point to `~/setup/docs/human/SETUP.md`; do not guess.
4. Read the phase from `.pipeline-state.json` and run `setup-preflight <phase> <project-root>`.
   Preflight is read-only and checks the core entry contract. A nonzero result means BLOCKED, not
   that the project is broken. The specialized validator is an exit/readiness check in status, not
   an entry guard: otherwise invalid in-phase state could not be repaired.
5. At Phase 7, if entry preflight passes, also run
   `setup-preflight 7 <project-root> --completion` to distinguish “review can start” from “delivery
   accepted and complete”.
6. If `.workctl/tasks/` exists, run `workctl status` read-only and include its result under a separate
   “Tasks” heading. Never use task progress to infer the pipeline phase.

## Answer

Lead with the outcome, not raw command output. Include exactly:

- **Stage:** phase ID, its skill/process name, and a one-sentence plain-language meaning.
- **Readiness:** READY, BLOCKED, or COMPLETE. Summarize only actionable preflight failures and name
  the evidence file or human decision involved.
- **Next:** one concrete action phrased for the human. Prefer “Ask me to run `<skill>`” or ask for
  the missing decision/value; do not require the human to translate a phase into a command.
- **Tasks:** only when workctl state exists; keep task Done/Now/Next separate from project stage.

Do not paste the ledger, full route, command transcript, or long runbook unless the user asks for
diagnostic detail. Do not mutate the ledger, attest artifacts, sign gates, select a tier, or advance
the phase during a status request. Never infer state from chat history, timestamps, or apparent files.

Every phase always has the core machine preflight. A phase may additionally bind one specialized
skill through `phase_processes`; its trusted `pipeline-validator.json` supplies a read-only validator.
Agents register that binding when selecting the specialized process, not during a status request.
The machine artifact-flow contract separately requires every declared phase output to appear in a
checked downstream requirement, so a successful producer output cannot become ceremonial state.

When a blocker exposes a specification gap, ask for the missing human decision instead of filling it
with a plausible assumption. The status response is orientation, not authorization to continue.
