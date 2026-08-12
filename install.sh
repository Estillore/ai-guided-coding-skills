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
AGENT="$ROOT/agents/guided.json"
STEERING="$ROOT/steering/ponytail.md"

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
  [[ -f "$AGENT" ]] && cp "$AGENT" "$HOME/.kiro/agents/"
  [[ -f "$STEERING" ]] && cp "$STEERING" "$HOME/.kiro/steering/"
  echo "OK  Kiro     -> $HOME/.kiro/skills"
  echo "    agent    -> $HOME/.kiro/agents/guided.json"
  echo "    steering -> $HOME/.kiro/steering/ponytail.md"
}

install_grok() {
  copy_skills "$HOME/.grok/skills"
  echo "OK  Grok     -> $HOME/.grok/skills"
}

install_opencode() {
  # Native OpenCode global path
  copy_skills "$HOME/.config/opencode/skills"
  echo "OK  OpenCode -> $HOME/.config/opencode/skills"
}

install_zed() {
  # Agent Skills open standard (Zed + also read by OpenCode)
  copy_skills "$HOME/.agents/skills"
  echo "OK  Zed      -> $HOME/.agents/skills  (Agent Skills standard)"
}

echo "Installing guided skills (target: $TARGET)..."
echo ""

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

echo ""
echo "Done. Restart your tool (or open a new chat), then run: /guided-coding"
