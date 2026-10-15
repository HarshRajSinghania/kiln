#!/usr/bin/env python3
"""SessionStart : signale qu'un repo généré par kiln part d'un modèle qui a évolué depuis.

Lit le commit du modèle dans `.copier-answers.yml`, demande à l'API publique de GitHub ce qui a
changé sur kiln depuis (seuls `template/`, `copier.yml` et `macros.jinja` comptent, comme pour
`kiln status`) et, si le modèle a bougé, ajoute au contexte de la session de proposer
`kiln update`. Ne lance rien : la mise à jour se fait sur une branche, à la demande.

Jamais bloquant : résultat gardé un jour par repo et par commit, trois secondes au plus pour
GitHub, silence sans réseau ou hors d'un repo kiln. Un repo s'en exempte par
`git config kiln-a-jour.desactive true`.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

ANSWERS_FILE = ".copier-answers.yml"
KILN_SOURCE_MARKERS = ("antoine-tena/kiln", "antoine-tena/init-repo")
COMPARE_URL = "https://api.github.com/repos/antoine-tena/kiln/compare/{commit}...HEAD"
TEMPLATE_PATHS = ("template/", "copier.yml", "macros.jinja")
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kiln" / "a-jour"
CACHE_SECONDS = 24 * 60 * 60
TIMEOUT_SECONDS = 3


def answer(text: str, key: str) -> str:
    """Valeur d'une clé de premier niveau des réponses Copier (sans dépendre de PyYAML)."""
    match = re.search(rf"^{re.escape(key)}:\s*['\"]?([^'\"\n]*)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def is_template_change(changed_paths: list[str]) -> bool:
    return any(path.startswith(TEMPLATE_PATHS) for path in changed_paths)


def fetch_changed_paths(commit: str) -> list[str]:
    request = urllib.request.Request(
        COMPARE_URL.format(commit=commit), headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        comparison = json.load(response)
    return [entry["filename"] for entry in comparison.get("files", [])]


def is_late(
    root: Path,
    commit: str,
    fetch: Callable[[str], list[str]] = fetch_changed_paths,
    now: Callable[[], float] = time.time,
) -> bool:
    """Le modèle a-t-il changé depuis `commit` ? Réponse gardée un jour par repo et commit."""
    cache_path = CACHE_DIR / (hashlib.sha1(f"{root}:{commit}".encode()).hexdigest()[:16] + ".json")
    try:
        cached = json.loads(cache_path.read_text())
        if now() - cached["checked_at"] < CACHE_SECONDS:
            return bool(cached["is_late"])
    except OSError, ValueError, KeyError:
        pass
    late = is_template_change(fetch(commit))
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"checked_at": now(), "is_late": late}))
    except OSError:
        pass
    return late


def git(cwd: str, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", cwd, *args], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
    )
    return completed.stdout.strip()


def message_for(cwd: str) -> str:
    root = git(cwd, "rev-parse", "--show-toplevel")
    if not root or git(root, "config", "--get", "kiln-a-jour.desactive") == "true":
        return ""
    answers_path = Path(root) / ANSWERS_FILE
    if not answers_path.is_file():
        return ""
    answers = answers_path.read_text(encoding="utf-8")
    commit = answer(answers, "_commit")
    if not commit or not any(m in answer(answers, "_src_path") for m in KILN_SOURCE_MARKERS):
        return ""
    if not is_late(Path(root), commit):
        return ""
    return (
        f"Le modèle kiln a évolué depuis le commit {commit} dont part ce repo : proposer à "
        "l'utilisateur `kiln update`, sur une branche dédiée (`chore/kiln-update`). Ne pas le "
        "lancer sans son accord."
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        message = message_for(payload.get("cwd") or ".")
    except Exception:
        # Réseau absent, GitHub qui limite, repo illisible : la session démarre sans rien dire.
        return
    if message:
        print(
            json.dumps(
                {
                    "systemMessage": "kiln : le modèle a évolué, `kiln update` disponible.",
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": message,
                    },
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
