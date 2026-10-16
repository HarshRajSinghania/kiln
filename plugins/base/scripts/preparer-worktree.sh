#!/usr/bin/env bash
# Prépare un worktree neuf : y recopie les fichiers locaux ignorés par git (.env, .env.local…)
# de l'arbre principal, puis installe les dépendances JavaScript de chaque lockfile.
# Les dépendances Python ne sont pas installées : `uv run` crée le venv à la demande.
# Un repo qui a besoin de plus ajoute .claude/worktree-setup.sh, lancé ensuite par base:worktree.
set -euo pipefail
worktree="$(cd "$1" && pwd)"
main_tree="$(dirname "$(git -C "$worktree" rev-parse --path-format=absolute --git-common-dir)")"

# Fichiers .env* ignorés de l'arbre principal (hors exemples et node_modules), même chemin relatif.
git -C "$main_tree" ls-files --others --ignored --exclude-standard -- '*.env' '*.env.*' '.env' '.env.*' \
  | grep -vE '(^|/)node_modules/|\.(example|sample)$|^\.claude/worktrees/' \
  | while read -r f; do
      mkdir -p "$worktree/$(dirname "$f")"
      cp -p "$main_tree/$f" "$worktree/$f"
      echo "copié : $f"
    done

# Jamais de node_modules en lien symbolique : il casse les outils qui résolvent leur racine.
git -C "$worktree" ls-files -- '*pnpm-lock.yaml' '*package-lock.json' | while read -r lock; do
  dir="$worktree/$(dirname "$lock")"
  case "$lock" in
    *pnpm-lock.yaml) (cd "$dir" && pnpm install --frozen-lockfile --prefer-offline) ;;
    *package-lock.json) (cd "$dir" && npm ci --prefer-offline) ;;
  esac
done
echo "worktree prêt : $worktree"
