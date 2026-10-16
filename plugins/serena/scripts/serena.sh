#!/usr/bin/env bash
# Lance Serena sur le worktree courant (chaque worktree est son propre projet, indexé dans son
# dossier .serena/, ignoré par git), dans le contexte en lecture seule de kiln, sans tableau de
# bord. Version figée : la monter ici après l'avoir essayée.
set -euo pipefail
VERSION=2.0.0
here="$(cd "$(dirname "$0")" && pwd)"
project="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
exec uvx --from "serena-agent==$VERSION" serena start-mcp-server \
  --project "$project" --context "$here/lecture.yml" --mode no-memories --agent-interface tools \
  --enable-web-dashboard false --open-web-dashboard false --enable-gui-log-window false
