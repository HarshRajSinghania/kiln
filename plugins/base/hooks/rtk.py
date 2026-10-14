#!/usr/bin/env python3
"""PreToolUse (Bash) : fait passer la commande par rtk, qui condense sa sortie (tests, lint,
git, builds) avant qu'elle n'entre dans le contexte.

Sans rtk dans le PATH, le hook ne fait rien. La réécriture vient de `rtk hook claude`, dont on
retire la décision de permission (`allow`) : la commande réécrite passe par les permissions
habituelles, comme l'originale. Un repo s'en exempte par `git config rtk.desactive true`.
"""

import json
import shutil
import subprocess
import sys

raw = sys.stdin.read()
cwd = json.loads(raw).get("cwd") or "."

if not shutil.which("rtk"):
    sys.exit(0)
disabled = subprocess.run(
    ["git", "-C", cwd, "config", "--get", "--type=bool", "rtk.desactive"],
    capture_output=True, text=True,
)
if disabled.stdout.strip() == "true":
    sys.exit(0)

rewrite = subprocess.run(["rtk", "hook", "claude"], input=raw, capture_output=True, text=True)
try:
    output = json.loads(rewrite.stdout)
except json.JSONDecodeError:
    sys.exit(0)
specific = output.get("hookSpecificOutput") or {}
if "updatedInput" not in specific:
    sys.exit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "updatedInput": specific["updatedInput"],
}}))
