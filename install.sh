#!/usr/bin/env bash
# Setup v2 — one-command install
# Run from anywhere: bash ~/.setup/install.sh

set -e

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SKILLS_SRC="$SETUP_DIR/skills"
SKILLS_DST="$CLAUDE_DIR/skills"

echo "=== Setup v2 install ==="
echo "Source: $SETUP_DIR"
echo "Claude: $CLAUDE_DIR"
echo ""

# 1. Symlink skills into ~/.claude/skills/
echo "→ Registering skills..."
mkdir -p "$SKILLS_DST"

for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name="$(basename "$skill_dir")"
  target="$SKILLS_DST/$skill_name"

  if [ -L "$target" ]; then
    echo "  ✓ $skill_name (already linked)"
  elif [ -d "$target" ]; then
    echo "  ⚠ $skill_name — directory already exists at $target (skipped)"
  else
    ln -s "$skill_dir" "$target"
    echo "  + $skill_name"
  fi
done

# 2. Check GH_TOKEN
echo ""
echo "→ Checking GH_TOKEN..."
if grep -q "GH_TOKEN" "$CLAUDE_DIR/.env" 2>/dev/null; then
  echo "  ✓ GH_TOKEN found in ~/.claude/.env"
else
  echo "  ⚠ GH_TOKEN not found. Set it in ~/.claude/.env:"
  echo "    echo 'GH_TOKEN=ghp_...' >> ~/.claude/.env"
fi

# 3. Check Playwright MCP
echo ""
echo "→ Checking Playwright MCP..."
if claude mcp list 2>/dev/null | grep -q "playwright"; then
  echo "  ✓ Playwright MCP installed"
else
  echo "  ⚠ Playwright MCP not found (needed for /build-loop)"
  echo "    Run: claude mcp add playwright -- npx -y @playwright/mcp@latest --headless"
fi

# 4. Check OpenCode + DeepSeek (parity path — skips cleanly if you only use Claude Code)
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
if [ -f "$HOME/.opencode/openrouter-key" ] || [ -n "$DEEPSEEK_API_KEY" ] || [ -n "$OPENROUTER_API_KEY" ]; then
  echo "  ✓ DeepSeek/OpenRouter key present"
else
  echo "  ⚠ No DeepSeek/OpenRouter key found:"
  echo "    echo 'sk-...' > ~/.opencode/openrouter-key   (or export DEEPSEEK_API_KEY / OPENROUTER_API_KEY)"
fi

echo ""
echo "=== Done ==="
echo ""
echo "Available skills (Claude Code: /startup | OpenCode: mention by name):"
echo "  startup       — create new project from template"
echo "  researcher    — multi-agent research flow"
echo "  judge         — LLM-as-judge artifact evaluation"
echo "  design-first  — wireframe → API contract"
echo ""
echo "OpenCode: skills discovered from ~/.claude/skills/ — same path, both CLI."
echo "See docs/agent/COMPAT.md for OpenCode model routing and collegium protocol."
echo ""
echo "Model routing:"
echo "  Orchestrator  → Claude Opus / DeepSeek V4 Pro"
echo "  Backend code  → DeepSeek V4"
echo "  Frontend code → GLM 5.2 / DeepSeek V4"
echo "  Research work → DeepSeek Flash"
echo "  Judge         → Claude Opus (isolated context)"
echo ""
echo "Next: open Claude Code or OpenCode and create a new project."
