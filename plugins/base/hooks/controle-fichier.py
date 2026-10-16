#!/usr/bin/env python3
"""PostToolUse (Edit/Write) : contrôle du fichier modifié, pour voir l'infraction tout de suite.

ruff pour un .py (le `.venv/bin/ruff` le plus proche en remontant), ESLint avec cache pour un
.ts/.vue/.js (le `node_modules/.bin/eslint` le plus proche), puis la charte du repo : la
commande `charte` de kiln s'il a un `charte.toml`, sinon le script que nomme `PROJET_CHARTE`
(chemin relatif à la racine du repo) dans son `.claude/settings.json`. Une violation de la
charte n'est signalée qu'une fois, puis de nouveau
quand elle change : la dette en cours ne répète pas son rapport à chaque édition. Marche aussi
dans un worktree. Sortie 2 = le rapport est renvoyé à l'agent ; sans outil installé, on se tait.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ESLINT_SUFFIXES = (".ts", ".vue", ".js", ".mjs")
CHARTER_SUFFIXES = (".py", ".ts", ".vue", ".js", ".mjs", ".css")
# Fin du rapport utile : la suite rappelle les règles non vérifiées, du bruit à chaque édition.
CHARTER_REPORT_END = "\nRègles de CLAUDE.md non vérifiées"


def find_upward(start: Path, relative: str) -> Path | None:
    for folder in [start, *start.parents]:
        if (folder / relative).exists():
            return folder / relative
    return None


def lint_command(path: Path) -> tuple[list[str], Path] | None:
    if path.suffix == ".py":
        ruff = find_upward(path.parent, ".venv/bin/ruff")
        if ruff:
            return (
                [str(ruff), "check", "--quiet", "--output-format", "concise", str(path)],
                ruff.parents[2],
            )
    if path.suffix in ESLINT_SUFFIXES:
        eslint = find_upward(path.parent, "node_modules/.bin/eslint")
        if eslint:
            project = eslint.parents[2]
            cache = str(project / "node_modules/.cache/eslint-hook")
            return ([str(eslint), "--cache", "--cache-location", cache, str(path)], project)
    return None


def charter_command(path: Path) -> tuple[list[str], Path] | None:
    if path.suffix not in CHARTER_SUFFIXES:
        return None
    top = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not top:
        return None
    if (Path(top) / "charte.toml").exists():
        # `charte` vient de kiln (uv tool install git+https://github.com/antoine-tena/kiln).
        moteur = shutil.which("charte")
        return ([moteur], Path(top)) if moteur else None
    script = os.environ.get("PROJET_CHARTE")
    if not script or not (Path(top) / script).exists():
        return None
    return ([sys.executable, str(Path(top) / script)], Path(top))


def failure_report(command: tuple[list[str], Path] | None) -> str:
    if not command:
        return ""
    argv, cwd = command
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=60)
    if completed.returncode == 0:
        return ""
    return (completed.stdout + completed.stderr).split(CHARTER_REPORT_END)[0].strip()


def is_new_charter_report(report: str, repo_root: Path) -> bool:
    """Une violation déjà signalée (dette en cours) ne se répète pas à chaque édition.

    La signature ignore les chiffres, qui bougent à chaque ligne écrite ; un nouveau fichier en
    infraction ou une nouvelle règle enfreinte la change, et le rapport revient.
    """
    signature = "\n".join(
        sorted({"".join(c for c in line if not c.isdigit()) for line in report.splitlines()})
    )
    memo = (
        Path(tempfile.gettempdir())
        / f"charte-hook-{hashlib.sha1(str(repo_root).encode()).hexdigest()[:12]}"
    )
    previous = memo.read_text(encoding="utf-8") if memo.exists() else ""
    memo.write_text(signature, encoding="utf-8")
    return signature != previous


file_path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
if not file_path or "node_modules" in file_path or not os.path.isfile(file_path):
    sys.exit(0)
path = Path(file_path)
charter = charter_command(path)
charter_report = failure_report(charter)
if charter and not is_new_charter_report(charter_report, charter[1]):
    charter_report = ""
reports = [report for report in (failure_report(lint_command(path)), charter_report) if report]
if reports:
    print(
        f"Contrôle en échec après la modification de {file_path} :\n\n" + "\n\n".join(reports),
        file=sys.stderr,
    )
    sys.exit(2)
