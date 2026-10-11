#!/usr/bin/env python3
"""PreToolUse (Bash) : refuse un `git commit` sur une branche principale (main, master, develop).

Un repo où l'on commite directement sur la branche principale (dotfiles…) s'en exempte par
`git config garde-branche.desactive true`.
"""

import json
import os
import re
import subprocess
import sys

PROTECTED_BRANCHES = {"main", "master", "develop"}

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")
cwd = data.get("cwd") or "."

# Chaque sous-commande (séparée par ; && || | ou un saut de ligne) est lue dans l'ordre :
# un `cd` change le dossier courant, un `git [-C dir] commit` en tête de sous-commande est
# vérifié dans son dossier. Le texte « git commit » dans un echo ou un message ne compte pas.
targets = []
for part in re.split(r"&&|\|\||[;|\n]", cmd):
    part = part.strip().lstrip("(").strip()
    m = re.match(r"cd\s+(\S+)", part)
    if m:
        cwd = os.path.join(cwd, os.path.expanduser(m.group(1).strip("'\"")))
        continue
    m = re.match(r"git((?:\s+-[cC]\s+\S+)*)\s+commit\b", part)
    if m:
        c = re.findall(r"-C\s+(\S+)", m.group(1))
        targets.append(os.path.join(cwd, *(p.strip("'\"") for p in c)) if c else cwd)

for target in targets:
    try:
        branch = subprocess.run(
            ["git", "-C", target, "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:
        continue
    is_disabled = (
        subprocess.run(
            ["git", "-C", target, "config", "--get", "garde-branche.desactive"],
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        == "true"
    )
    if branch in PROTECTED_BRANCHES and not is_disabled:
        print(
            f"Commit refusé : on ne commite jamais sur {branch}. "
            "Créer une branche (worktree) d'abord.",
            file=sys.stderr,
        )
        sys.exit(2)
