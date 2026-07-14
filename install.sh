#!/usr/bin/env bash
# START_MODULE_CONTRACT
# PURPOSE: Install setup skills and shared pipeline scripts into supported local agent runtimes.
# SCOPE: Create fail-closed symlinks, then report optional runtime credentials and integrations.
# DEPENDS: Bash, coreutils, the repository skills/ and scripts/ trees, optional Claude/OpenCode CLIs.
# END_MODULE_CONTRACT
# Setup v2 — one-command install
# Run from anywhere: bash ~/setup/install.sh
#
# Install is fail-closed on skill collisions. A skill that exists in ~/.claude/skills/ as a real
# directory SHADOWS this repo: you edit setup/skills/X, and the CLI keeps loading the stale copy.
# That failure is silent and expensive — so this script HALTS on it instead of skipping.

set -euo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SKILLS_SRC="$SETUP_DIR/skills"
SKILLS_DST="$CLAUDE_DIR/skills"
SCRIPTS_DST="$CLAUDE_DIR/scripts"
BIN_DST="${WORKCTL_BIN_DIR:-$HOME/.local/bin}"

echo "=== Setup v2 install ==="
echo "Source: $SETUP_DIR"
echo "Claude: $CLAUDE_DIR"
echo ""

# 1. Symlink skills into ~/.claude/skills/ — every skill, or none.
echo "→ Registering skills..."
mkdir -p "$SKILLS_DST"
COLLISIONS=()

for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_DST/$skill_name"

  if [ -L "$target" ]; then
    if [ "$(readlink -f "$target")" = "$(readlink -f "$skill_dir")" ]; then
      echo "  ✓ $skill_name"
    else
      COLLISIONS+=("$skill_name|symlink points at $(readlink -f "$target"), not at this repo")
    fi
  elif [ -e "$target" ]; then
    COLLISIONS+=("$skill_name|real directory — a stale copy that shadows $skill_dir")
  else
    ln -s "$skill_dir" "$target"
    echo "  + $skill_name"
  fi
done

if [ ${#COLLISIONS[@]} -gt 0 ]; then
  echo ""
  echo "✗ HALT — ${#COLLISIONS[@]} skill(s) in $SKILLS_DST do not come from this repo:"
  for c in "${COLLISIONS[@]}"; do
    printf '    %-24s %s\n' "${c%%|*}" "${c#*|}"
  done
  cat <<EOF

  Why this is fatal, not a warning: the CLI loads whatever is at $SKILLS_DST.
  While a stale copy sits there, every edit you make in $SKILLS_SRC is dead code —
  it is committed, reviewed, and never executed.

  Resolve each one (after saving anything you still want from the stale copy):

      rm -rf $SKILLS_DST/<skill>          # or: mv it aside
      bash $SETUP_DIR/install.sh          # re-run — it will link it

  Nothing else was installed.
EOF
  exit 1
fi

# 2. Expose scripts at a stable path, so skills can call them from any project directory.
#    Skills reference ~/.claude/scripts/<name>.sh — independent of where this repo is cloned.
echo ""
echo "→ Exposing scripts at $SCRIPTS_DST..."
mkdir -p "$SCRIPTS_DST"
for script in "$SETUP_DIR"/scripts/*.sh; do
  ln -sfn "$script" "$SCRIPTS_DST/$(basename "$script")"
  echo "  ✓ $(basename "$script")"
done

# Expose the cross-runtime task controller as a normal CLI. Refuse to overwrite a real file or a
# symlink owned by another installation: a shadowed controller is as dangerous as a shadowed skill.
echo ""
echo "→ Installing workctl at $BIN_DST/workctl..."
mkdir -p "$BIN_DST"
WORKCTL_SRC="$SETUP_DIR/scripts/workctl.py"
WORKCTL_DST="$BIN_DST/workctl"
if [ -L "$WORKCTL_DST" ]; then
  if [ "$(readlink -f "$WORKCTL_DST")" != "$(readlink -f "$WORKCTL_SRC")" ]; then
    echo "✗ HALT — $WORKCTL_DST points at $(readlink -f "$WORKCTL_DST"), not this setup"
    exit 1
  fi
elif [ -e "$WORKCTL_DST" ]; then
  echo "✗ HALT — $WORKCTL_DST is a real file; move it aside before installing workctl"
  exit 1
else
  ln -s "$WORKCTL_SRC" "$WORKCTL_DST"
fi
echo "  ✓ workctl"

# 3. Check GH_TOKEN
echo ""
echo "→ Checking GH_TOKEN..."
if grep -q "GH_TOKEN" "$CLAUDE_DIR/.env" 2>/dev/null; then
  echo "  ✓ GH_TOKEN found in ~/.claude/.env"
else
  echo "  ⚠ GH_TOKEN not found. Set it in ~/.claude/.env:"
  echo "    echo 'GH_TOKEN=ghp_...' >> ~/.claude/.env"
fi

# 4. Check Playwright MCP
echo ""
echo "→ Checking Playwright MCP..."
if claude mcp list 2>/dev/null | grep -q "playwright"; then
  echo "  ✓ Playwright MCP installed"
else
  echo "  ⚠ Playwright MCP not found (needed for /build-loop)"
  echo "    Run: claude mcp add playwright -- npx -y @playwright/mcp@latest --headless"
fi

# 5. Check OpenCode + DeepSeek (parity path — skips cleanly if you only use Claude Code)
echo ""
echo "→ Checking OpenCode + DeepSeek..."
OC_CFG="$HOME/.config/opencode/opencode.json"
if command -v opencode >/dev/null 2>&1; then
  echo "  ✓ opencode found ($(opencode --version 2>/dev/null | head -1))"
else
  echo "  ⚠ opencode not on PATH (ignore if you only use Claude Code)"
fi
# Skills need nothing extra — OpenCode discovers ~/.claude/skills/ natively (verified: opencode.ai/docs/skills)
echo "  ✓ Skills: OpenCode reads ~/.claude/skills/ natively — same symlinks as above"
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

echo ""
echo "=== Done ==="
echo ""
echo "Every skill in $SKILLS_SRC is now linked — what you edit is what runs."
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
echo "  workctl continue <task-id> --runtime claude|codex|opencode"
