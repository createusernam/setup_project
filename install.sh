#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Install setup skills and shared pipeline scripts into supported local agent runtimes.
# SCOPE: Create fail-closed cross-CLI skill and command symlinks, then report optional runtime integrations.
# DEPENDS: Bash, Python 3, coreutils, repository skills/docs/scripts, and any installed supported CLI.
# END_MODULE_CONTRACT
# Setup v2 — one-command install
# Run from anywhere: bash ~/setup/install.sh
#
# Install is fail-closed on skill collisions in both discovery roots. Pass
# --migrate-skill-collisions to move every collision into a timestamped backup before linking.

set -euo pipefail

# START_BLOCK_INSTALL
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SKILLS_SRC="$SETUP_DIR/skills"
CLAUDE_SKILLS_DST="$CLAUDE_DIR/skills"
AGENT_SKILLS_DST="$HOME/.agents/skills"
SCRIPTS_DST="$CLAUDE_DIR/scripts"
BIN_DST="${WORKCTL_BIN_DIR:-$HOME/.local/bin}"
ROUTING_SRC="$SETUP_DIR/docs/agent/SKILL-ROUTING.md"
MIGRATE_COLLISIONS=0

if [ "${1:-}" = "--migrate-skill-collisions" ] && [ "$#" -eq 1 ]; then
  MIGRATE_COLLISIONS=1
elif [ "$#" -ne 0 ]; then
  echo "Usage: bash $0 [--migrate-skill-collisions]" >&2
  exit 2
fi

echo "=== Setup v2 install ==="
echo "Source: $SETUP_DIR"
echo "Claude: $CLAUDE_DIR"
echo ""

# 1. Preflight every destination before mutating anything.
echo "→ Preflighting skill discovery and commands..."
COLLISIONS=()

for root_spec in "claude|$CLAUDE_SKILLS_DST" "agents|$AGENT_SKILLS_DST"; do
  root_name="${root_spec%%|*}"
  root_path="${root_spec#*|}"
  for skill_dir in "$SKILLS_SRC"/*/; do
    skill_name="$(basename "$skill_dir")"
    target="$root_path/$skill_name"
    if [ -L "$target" ]; then
      if [ "$(readlink -f "$target")" != "$(readlink -f "$skill_dir")" ]; then
        COLLISIONS+=("skill|$root_name|$target|$skill_name|symlink points at $(readlink -f "$target"), not at this repo")
      fi
    elif [ -e "$target" ]; then
      COLLISIONS+=("skill|$root_name|$target|$skill_name|real path shadows setup")
    fi
  done
done

for command_spec in \
  "workctl|$SETUP_DIR/scripts/workctl.py" \
  "setup-skill-doctor|$SETUP_DIR/scripts/check-skill-discovery.py" \
  "setup-pipeline|$SETUP_DIR/scripts/pipeline-state.py" \
  "setup-preflight|$SETUP_DIR/scripts/pipeline-preflight.sh" \
  "setup-model-check|$SETUP_DIR/scripts/model-check.sh" \
  "setup-grace-lint|$SETUP_DIR/scripts/grace-lint.sh"; do
  command_name="${command_spec%%|*}"
  command_src="${command_spec#*|}"
  command_dst="$BIN_DST/$command_name"
  if [ -L "$command_dst" ]; then
    if [ "$(readlink -f "$command_dst")" != "$(readlink -f "$command_src")" ]; then
      COLLISIONS+=("command|bin|$command_dst|$command_name|symlink points at $(readlink -f "$command_dst"), not at this repo")
    fi
  elif [ -e "$command_dst" ]; then
    COLLISIONS+=("command|bin|$command_dst|$command_name|real file shadows setup")
  fi
done

if [ ${#COLLISIONS[@]} -gt 0 ]; then
  if [ "$MIGRATE_COLLISIONS" -ne 1 ]; then
    echo ""
    echo "✗ HALT — ${#COLLISIONS[@]} collision(s) do not come from this repo:"
    for collision in "${COLLISIONS[@]}"; do
      IFS='|' read -r kind root target name reason <<< "$collision"
      printf '    %-8s %-8s %-24s %s\n' "$kind" "$root" "$name" "$reason"
    done
    cat <<EOF

  Nothing was installed. Preserve and migrate all collisions explicitly with:

      bash $SETUP_DIR/install.sh --migrate-skill-collisions

  The migration moves each conflicting path into ~/.setup-skill-backups/<timestamp>/;
  it never deletes the old copy.
EOF
    exit 1
  fi

  BACKUP_ROOT="$HOME/.setup-skill-backups/$(date +%Y%m%d-%H%M%S)"
  echo "  Migrating ${#COLLISIONS[@]} collision(s) to $BACKUP_ROOT"
  for c in "${COLLISIONS[@]}"; do
    IFS='|' read -r kind root target name reason <<< "$c"
    backup="$BACKUP_ROOT/$root/$name"
    mkdir -p "$(dirname "$backup")"
    mv "$target" "$backup"
    echo "  ↪ $target → $backup"
  done
fi

# 2. Link one canonical skill tree into every supported discovery root.
echo ""
echo "→ Registering skills in ~/.claude/skills and ~/.agents/skills..."
mkdir -p "$CLAUDE_SKILLS_DST" "$AGENT_SKILLS_DST"
for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name="$(basename "$skill_dir")"
  for target in "$CLAUDE_SKILLS_DST/$skill_name" "$AGENT_SKILLS_DST/$skill_name"; do
    if [ ! -L "$target" ]; then
      ln -s "$skill_dir" "$target"
    fi
  done
  echo "  ✓ $skill_name"
done

# 3. Retain legacy script links for older projects; current docs use runtime-neutral bin commands.
echo ""
echo "→ Exposing scripts at $SCRIPTS_DST..."
mkdir -p "$SCRIPTS_DST"
for script in "$SETUP_DIR"/scripts/*.sh; do
  ln -sfn "$script" "$SCRIPTS_DST/$(basename "$script")"
  echo "  ✓ $(basename "$script")"
done

# Expose cross-runtime diagnostics and task continuation as normal commands.
echo ""
echo "→ Installing workctl and setup-skill-doctor in $BIN_DST..."
mkdir -p "$BIN_DST"
for command_spec in \
  "workctl|$SETUP_DIR/scripts/workctl.py" \
  "setup-skill-doctor|$SETUP_DIR/scripts/check-skill-discovery.py" \
  "setup-pipeline|$SETUP_DIR/scripts/pipeline-state.py" \
  "setup-preflight|$SETUP_DIR/scripts/pipeline-preflight.sh" \
  "setup-model-check|$SETUP_DIR/scripts/model-check.sh" \
  "setup-grace-lint|$SETUP_DIR/scripts/grace-lint.sh"; do
  command_name="${command_spec%%|*}"
  command_src="${command_spec#*|}"
  command_dst="$BIN_DST/$command_name"
  if [ ! -L "$command_dst" ]; then
    ln -s "$command_src" "$command_dst"
  fi
  echo "  ✓ $command_name"
done

# 4. Put the same mandatory routing contract into each runtime's always-on instructions.
echo ""
echo "→ Installing managed cross-CLI skill-routing policy..."
python3 "$SETUP_DIR/scripts/install-skill-routing.py" --install --source "$ROUTING_SRC" --home "$HOME"
# END_BLOCK_INSTALL

# START_BLOCK_OPTIONAL_CHECKS
# 5. Report optional Playwright MCP availability without making one CLI mandatory.
echo ""
echo "→ Checking optional Playwright MCP (needed only for build-loop)..."
if command -v claude >/dev/null 2>&1; then
  claude mcp list 2>/dev/null | grep -q "playwright" \
    && echo "  ✓ Claude: playwright" \
    || echo "  · Claude: not configured; see docs/human/SETUP.md"
fi
if command -v codex >/dev/null 2>&1; then
  codex mcp list 2>/dev/null | grep -q "playwright" \
    && echo "  ✓ Codex: playwright" \
    || echo "  · Codex: not configured; see docs/human/SETUP.md"
fi
if command -v opencode >/dev/null 2>&1; then
  opencode mcp list 2>/dev/null | grep -q "playwright" \
    && echo "  ✓ OpenCode: playwright" \
    || echo "  · OpenCode: not configured; see docs/human/SETUP.md"
fi

# 6. Check OpenCode instructions when that runtime is installed.
echo ""
echo "→ Checking OpenCode..."
OC_CFG="$HOME/.config/opencode/opencode.json"
if command -v opencode >/dev/null 2>&1; then
  echo "  ✓ opencode found ($(opencode --version 2>/dev/null | head -1))"
else
  echo "  · opencode not on PATH; no OpenCode-specific setup needed"
fi
# OpenCode scans both roots. They intentionally resolve to the same canonical setup source.
echo "  ✓ Skills: OpenCode reads ~/.claude/skills and ~/.agents/skills; both resolve to setup/skills"
# instructions must be an ARRAY of file paths incl. the docs/ subdirs (a prose string loads nothing)
if [ -f "$OC_CFG" ]; then
  if grep -q "docs/human/PIPELINE.md" "$OC_CFG" 2>/dev/null; then
    echo "  ✓ opencode.json instructions reference PIPELINE.md"
  else
    echo "  ⚠ opencode.json instructions don't point at $SETUP_DIR/docs/ — set (array, not string):"
    echo "      \"instructions\": [\"$SETUP_DIR/docs/human/PIPELINE.md\", \"$SETUP_DIR/docs/agent/COMPAT.md\"],"
  fi
else
  echo "  ⚠ $OC_CFG not found. Minimal config:"
  echo "      { \"instructions\": [\"$SETUP_DIR/docs/human/PIPELINE.md\", \"$SETUP_DIR/docs/agent/COMPAT.md\"] }"
fi
# END_BLOCK_OPTIONAL_CHECKS

# START_BLOCK_SUMMARY
echo ""
echo "=== Done ==="
echo ""
"$BIN_DST/setup-skill-doctor" --setup-dir "$SETUP_DIR" --home "$HOME" --quiet
echo "Every skill in $SKILLS_SRC now has one source across Claude, Codex, and OpenCode."
echo ""
echo "Next step: open any supported agent in a project and ask:"
echo "  What stage are we at, and what should we do next?"
echo "The pipeline-status skill reads durable state and gives one next action."
echo "Use $SETUP_DIR/docs/human/PIPELINE.md for first-time decisions or troubleshooting."
echo ""
echo "Model routing:"
echo "  model-routing.json defines capability profiles and role independence"
echo "  each project/model-bindings.json selects concrete runtime/model IDs"
echo ""
echo "Deterministic diagnostics used by agents (and available for troubleshooting):"
echo "  setup-pipeline values                                  # phases, tiers, conditions, gates, profiles, runtimes, schemas"
echo "  setup-pipeline status                                  # inspect project ledger"
echo "  setup-pipeline attest <artifact...>                   # hash/register changed artifacts"
echo "  setup-pipeline sign <gate> --by <identity>            # record an explicit human gate"
echo "  setup-preflight <phase> [project]                     # inputs, models, human gates"
echo "  setup-grace-lint --changed                            # GRACE Lite markup"
echo "  setup-model-check <phase> [project]                   # optional binding diagnostic"
echo ""
echo "Optional cross-runtime continuation for one named task (not project status):"
echo "  workctl doctor"
echo "  workctl init <task-id> --goal \"...\""
echo "  workctl handoff <task-id> --to codex --next-action \"...\""
echo "  workctl continue <task-id> --runtime claude|codex|opencode"
echo ""
echo "Skill discovery:"
echo "  setup-skill-doctor"
# END_BLOCK_SUMMARY
