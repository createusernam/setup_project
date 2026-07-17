# Cross-CLI Skill Routing Contract

Apply these rules before the first tool call in Claude Code, Codex, and OpenCode:

1. Inspect the available skill names and descriptions for the current runtime.
2. If the user names a skill, load and follow it for that turn.
3. If the request clearly matches a skill description, load and follow it even when the user did not
   name it. Announce the skill and the reason briefly.
4. Use the smallest set of matching skills. When several apply, state their execution order.
5. Treat a missing skill as an installation/discovery problem; do not silently substitute a similarly
   named workflow.

`planning-with-files` is mandatory before substantive work when any of these is true:

- the user asks to save, write, or persist a plan and then execute it;
- the user says “сохрани план и выполни”, “сначала запиши план”, or describes a “большая задача”;
- the task is a research/build/migration/audit expected to require at least five tool calls;
- the work must survive compaction, `/clear`, a provider limit, or a CLI switch.

Explicit runtime invocation syntax differs (`/skill` in Claude, `$skill` or a named request in
Codex, the native `skill` tool in OpenCode). The routing decision does not: `name` and `description`
are the portable trigger contract. Runtime-specific frontmatter, hooks, permissions, and UI metadata
are optional extensions; the workflow in `SKILL.md` must remain usable without them.

For cross-CLI continuation, `workctl` and `.workctl/tasks/<task-id>/` own task identity and handoff
state. A legacy `CONTINUITY.md` is fallback-only and must not be maintained for the same task.

When the user asks in ordinary language where a project is, what comes next, where work stopped, or
to resume the project, invoke `pipeline-status`. Read `.pipeline-state.json` and current preflight;
never infer a phase from chat history. The answer must give the stage, readiness or blockers, and one
next action without requiring the user to know a command. If named task continuation across a
session or CLI is also relevant, use `workctl` after project status and keep task progress separate
from pipeline phase. A status question alone must not create a workctl task.
