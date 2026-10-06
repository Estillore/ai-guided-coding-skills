#!/usr/bin/env bash
# Install AI Guided Coding Skills (macOS / Linux)
# Usage:
#   ./install.sh              # all tools (kiro + grok + opencode + zed)
#   ./install.sh all
#   ./install.sh kiro
#   ./install.sh grok
#   ./install.sh opencode
#   ./install.sh zed
#   ./install.sh both         # kiro + grok only (legacy)

set -euo pipefail

TARGET="${1:-all}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS="$ROOT/skills"
AGENTS_DIR="$ROOT/agents"
STEERING="$ROOT/steering/ponytail.md"
ZED_PROFILES="$ROOT/agents/zed/profiles.snippet.jsonc"

if [[ ! -d "$SKILLS" ]]; then
  echo "Error: skills/ not found. Run this script from the ai-guided-coding-skills repo." >&2
  exit 1
fi

copy_skills() {
  local dest="$1"
  mkdir -p "$dest"
  cp -R "$SKILLS"/* "$dest/"
}

install_kiro() {
  mkdir -p "$HOME/.kiro/skills" "$HOME/.kiro/agents" "$HOME/.kiro/steering"
  copy_skills "$HOME/.kiro/skills"
  [[ -d "$AGENTS_DIR" ]] && cp "$AGENTS_DIR"/*.json "$HOME/.kiro/agents/"
  [[ -f "$STEERING" ]] && cp "$STEERING" "$HOME/.kiro/steering/"
  echo "OK  Kiro     -> $HOME/.kiro/skills"
  echo "    agents   -> $HOME/.kiro/agents/guided*.json"
  echo "    steering -> $HOME/.kiro/steering/ponytail.md"
}

install_grok() {
  copy_skills "$HOME/.grok/skills"
  echo "OK  Grok     -> $HOME/.grok/skills"
}

install_opencode() {
  # Native OpenCode global path
  copy_skills "$HOME/.config/opencode/skills"
  if [[ -d "$AGENTS_DIR/opencode" ]]; then
    mkdir -p "$HOME/.config/opencode/agent"
    cp "$AGENTS_DIR"/opencode/*.md "$HOME/.config/opencode/agent/"
    rm -f "$HOME/.config/opencode/agent/guided-tdd.md"
  fi
  echo "OK  OpenCode -> $HOME/.config/opencode/skills"
  echo "    agents   -> $HOME/.config/opencode/agent/guided-*.md"
}

install_zed() {
  # Agent Skills open standard (Zed + also read by OpenCode)
  copy_skills "$HOME/.agents/skills"
  echo "OK  Zed      -> $HOME/.agents/skills  (Agent Skills standard)"
  if [[ -f "$ZED_PROFILES" ]]; then
    echo "    profiles -> $ZED_PROFILES"
    echo "               paste into Zed settings (agent.profiles), then restart Zed"
  fi
}

echo "Installing guided skills (target: $TARGET)..."
echo ""

if [[ -d "$ROOT/scripts" ]]; then
  mkdir -p "$HOME/.guided/scripts"
  cp -R "$ROOT/scripts"/* "$HOME/.guided/scripts/"
  echo "OK  Harness  -> $HOME/.guided/scripts (guided_run.py)"
  echo ""
fi

if [[ -d "$ROOT/mcp" ]]; then
  mkdir -p "$HOME/.guided/mcp"
  cp -R "$ROOT/mcp"/* "$HOME/.guided/mcp/"
  echo "OK  MCP refs -> $HOME/.guided/mcp (snippets disabled-by-default; paste to enable)"
  echo ""
fi

case "$TARGET" in
  kiro) install_kiro ;;
  grok) install_grok ;;
  opencode) install_opencode ;;
  zed) install_zed ;;
  both)
    install_kiro
    install_grok
    ;;
  all)
    install_kiro
    install_grok
    install_opencode
    install_zed
    ;;
  *)
    echo "Usage: $0 [all|kiro|grok|opencode|zed|both]" >&2
    exit 1
    ;;
esac

DRIFT=0
VERIFY="$HOME/.guided/scripts/guided_run.py"
if [[ ! -f "$VERIFY" ]]; then
  echo ""
  echo "SKIP  harness missing at $VERIFY. Run: python3 ~/.guided/scripts/guided_run.py sync --check"
elif ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo ""
  echo "SKIP  python3 not on PATH. Run: python3 ~/.guided/scripts/guided_run.py sync --check"
else
  PY=python3
  command -v python3 >/dev/null 2>&1 || PY=python
  echo ""
  echo "Verifying installed skills against skills/ ..."
  "$PY" "$VERIFY" record-install --repo "$ROOT" || DRIFT=1
  "$PY" "$VERIFY" sync --check --repo "$ROOT" || DRIFT=1
fi

echo ""
if [[ "$DRIFT" -ne 0 ]]; then
  echo "Done, but the sync check FAILED. Fix the cause above (stale skills, or a broken python3) and re-run." >&2
  exit 1
fi
echo "Done. Restart your tool (or open a new chat), then run: /guided-coding"
