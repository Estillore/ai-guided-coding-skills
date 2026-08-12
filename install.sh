#!/usr/bin/env bash
# Install AI Guided Coding Skills (macOS / Linux)
# Usage:
#   ./install.sh              # both Kiro + Grok
#   ./install.sh kiro
#   ./install.sh grok
#   ./install.sh both

set -euo pipefail

TARGET="${1:-both}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS="$ROOT/skills"
AGENT="$ROOT/agents/guided.json"
STEERING="$ROOT/steering/ponytail.md"

if [[ ! -d "$SKILLS" ]]; then
  echo "Error: skills/ not found. Run this script from the ai-guided-coding-skills repo." >&2
  exit 1
fi

install_kiro() {
  mkdir -p "$HOME/.kiro/skills" "$HOME/.kiro/agents" "$HOME/.kiro/steering"
  cp -R "$SKILLS"/* "$HOME/.kiro/skills/"
  [[ -f "$AGENT" ]] && cp "$AGENT" "$HOME/.kiro/agents/"
  [[ -f "$STEERING" ]] && cp "$STEERING" "$HOME/.kiro/steering/"
  echo "OK  Kiro  -> $HOME/.kiro/skills"
  echo "    agent -> $HOME/.kiro/agents/guided.json"
  echo "    steer -> $HOME/.kiro/steering/ponytail.md"
}

install_grok() {
  mkdir -p "$HOME/.grok/skills"
  cp -R "$SKILLS"/* "$HOME/.grok/skills/"
  echo "OK  Grok  -> $HOME/.grok/skills"
}

echo "Installing guided skills (target: $TARGET)..."
echo ""

case "$TARGET" in
  kiro) install_kiro ;;
  grok) install_grok ;;
  both)
    install_kiro
    install_grok
    ;;
  *)
    echo "Usage: $0 [kiro|grok|both]" >&2
    exit 1
    ;;
esac

echo ""
echo "Done. Restart Kiro/Grok (or open a new chat), then run: /guided-coding"
