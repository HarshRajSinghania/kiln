#!/usr/bin/env python3
"""PreToolUse (Edit/Write/NotebookEdit) : protège secrets, jetons, lockfiles et archives.

Ces fichiers ne se modifient pas à la main.
"""

import json
import os
import re
import sys

path = json.load(sys.stdin).get("tool_input", {}).get("file_path") or ""
name = os.path.basename(path)
LOCKFILES = {
    "uv.lock",
    "poetry.lock",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "bun.lockb",
    "Cargo.lock",
}

if "/docs/_archive/" in path:
    reason = "docs/_archive/ est clos"
elif re.fullmatch(r"\.env(\..*)?", name) and not name.endswith((".example", ".sample")):
    reason = "fichier de secrets"
elif re.search(r"/\.[\w-]+/token$", path):
    reason = "jeton de service : l'utilisateur le colle lui-même"
elif name in LOCKFILES:
    reason = "lockfile : passer par le gestionnaire de paquets"
else:
    sys.exit(0)
print(f"Modification refusée ({reason}) : {path}", file=sys.stderr)
sys.exit(2)
