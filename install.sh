#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Install setup skills and shared pipeline scripts into supported local agent runtimes.
# SCOPE: Create fail-closed symlinks, then report optional runtime credentials and integrations.
# DEPENDS: Bash, Python 3, coreutils, repository skills/docs/scripts, optional Claude/OpenCode CLIs.
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

for command_spec in "workctl|$SETUP_DIR/scripts/workctl.py" "setup-skill-doctor|$SETUP_DIR/scripts/check-skill-discovery.py"; do
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

# 3. Expose scripts at a stable path, so skills can call them from any project directory.
#    Skills reference ~/.claude/scripts/<name>.sh — independent of where this repo is cloned.
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
for command_spec in "workctl|$SETUP_DIR/scripts/workctl.py" "setup-skill-doctor|$SETUP_DIR/scripts/check-skill-discovery.py"; do
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
# 5. Check GH_TOKEN
echo ""
echo "→ Checking GH_TOKEN..."
if grep -q "GH_TOKEN" "$CLAUDE_DIR/.env" 2>/dev/null; then
  echo "  ✓ GH_TOKEN found in ~/.claude/.env"
else
  echo "  ⚠ GH_TOKEN not found. Set it in ~/.claude/.env:"
  echo "    echo 'GH_TOKEN=ghp_...' >> ~/.claude/.env"
fi

# 6. Check Playwright MCP
echo ""
echo "→ Checking Playwright MCP..."
if claude mcp list 2>/dev/null | grep -q "playwright"; then
  echo "  ✓ Playwright MCP installed"
else
  echo "  ⚠ Playwright MCP not found (needed for /build-loop)"
  echo "    Run: claude mcp add playwright -- npx -y @playwright/mcp@latest --headless"
fi

# 7. Check OpenCode + DeepSeek (parity path — skips cleanly if you only use Claude Code)
echo ""
echo "→ Checking OpenCode + DeepSeek..."
OC_CFG="$HOME/.config/opencode/opencode.json"
if command -v opencode >/dev/null 2>&1; then
  echo "  ✓ opencode found ($(opencode --version 2>/dev/null | head -1))"
else
  echo "  ⚠ opencode not on PATH (ignore if you only use Claude Code)"
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
  echo "      { \"instructions\": [\"$SETUP_DIR/docs/human/PIPELINE.md\", \"$SETUP_DIR/docs/agent/COMPAT.md\"],"
  echo "        \"model\": \"deepseek/deepseek-v4-pro\", \"small_model\": \"deepseek/deepseek-v4-flash\" }"
fi
# DeepSeek/OpenRouter key — OpenCode needs one to actually run DeepSeek
if [ -f "$HOME/.opencode/openrouter-key" ] || [ -n "${DEEPSEEK_API_KEY:-}" ] || [ -n "${OPENROUTER_API_KEY:-}" ]; then
  echo "  ✓ DeepSeek/OpenRouter key present"
else
  echo "  ⚠ No DeepSeek/OpenRouter key found:"
  echo "    echo 'sk-...' > ~/.opencode/openrouter-key   (or export DEEPSEEK_API_KEY / OPENROUTER_API_KEY)"
fi
# END_BLOCK_OPTIONAL_CHECKS

# START_BLOCK_SUMMARY
echo ""
echo "=== Done ==="
echo ""
"$BIN_DST/setup-skill-doctor" --setup-dir "$SETUP_DIR" --home "$HOME" --quiet
echo "Every skill in $SKILLS_SRC now has one source across Claude, Codex, and OpenCode."
echo ""
echo "Pipeline (docs/human/PIPELINE.md):"
echo "  /startup → choose /methodology OR manual 9-section brief → /judge product-brief"
echo "  → /researcher only for remaining factual gaps → /grill-with-docs → /planning-with-files → /pm-review"
echo "  → /grace-init + /grace-plan → /design-first → /contract → /judge → /to-issues"
echo "  → /scaffold → /build-loop | /tdd → /judge feature → /code-review-expert → ship"
echo ""
echo "Model routing (model-routing.json · scripts/model-check.sh <phase>):"
echo "  Orchestrator / architect / scaffold → Claude Opus"
echo "  Backend code   → DeepSeek V4        Frontend code → GLM 5.2 / DeepSeek V4"
echo "  Research work  → DeepSeek Flash     Judge         → Claude Opus (isolated)"
echo ""
echo "Gates callable from any project dir:"
echo "  bash ~/.claude/scripts/pipeline-preflight.sh <phase>   # inputs, models, human gates"
echo "  bash ~/.claude/scripts/grace-lint.sh                   # GRACE Lite markup"
echo "  bash ~/.claude/scripts/model-check.sh <phase>          # required model for a phase"
echo ""
echo "Cross-runtime task continuation:"
echo "  workctl doctor"
echo "  workctl init <task-id> --goal \"...\""
echo "  workctl handoff <task-id> --to codex --next-action \"...\""
echo "  workctl continue <task-id> --runtime claude|codex|opencode"
echo ""
echo "Skill discovery:"
echo "  setup-skill-doctor"
# END_BLOCK_SUMMARY
