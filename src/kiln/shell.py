"""Lancement des commandes externes (git, uv, pnpm, gh) et messages à l'utilisateur."""

import os
import shutil
import subprocess
from pathlib import Path

from kiln import ui


class KilnError(Exception):
    """Erreur attendue, affichée sans trace à l'utilisateur."""


def step(title: str) -> None:
    ui.step(title)


# Sortie complète des commandes, sans roue animée (diagnostic).
VERBOSE_VARIABLE = "KILN_VERBOSE"


def run(
    command: list[str], cwd: Path, env: dict[str, str] | None = None, *, live: bool = False
) -> None:
    """Lance une commande ; échoue si elle échoue. `live` : sortie affichée telle quelle, pour
    une commande interactive ou dont la sortie est le résultat."""
    returncode = run_status(command, cwd, env, live=live)
    if returncode != 0:
        raise KilnError(f"échec de `{' '.join(command)}` (code {returncode})")


def run_status(
    command: list[str], cwd: Path, env: dict[str, str] | None = None, *, live: bool = False
) -> int:
    """Lance une commande et renvoie son code. Dans un terminal, une roue animée remplace sa
    sortie, affichée en entier seulement si elle échoue."""
    if live or not ui.is_styled() or os.environ.get(VERBOSE_VARIABLE):
        return subprocess.run(command, cwd=cwd, env=env, check=False).returncode
    spinner = ui.Spinner(" ".join(command))
    output: list[str] = []
    spinner.start()
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        for line in process.stdout or ():
            output.append(line)
            spinner.show(line)
        returncode = process.wait()
    finally:
        spinner.stop()
    spinner.finish(succeeded=returncode == 0, output="".join(output))
    return returncode


def capture(command: list[str], cwd: Path) -> str:
    """Lance une commande et renvoie sa sortie standard, sans espaces autour."""
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise KilnError(f"échec de `{' '.join(command)}` : {completed.stderr.strip()}")
    return completed.stdout.strip()


INSTALL_HINTS = {
    "git": "https://git-scm.com/downloads",
    "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
    "pnpm": "npm install -g pnpm (Node 24 requis)",
    "gh": "https://cli.github.com, puis gh auth login",
}


def require_tools(*tool_names: str) -> None:
    missing_tools = [name for name in tool_names if shutil.which(name) is None]
    if missing_tools:
        hints = "\n".join(f"  {name} : {INSTALL_HINTS.get(name, '')}" for name in missing_tools)
        raise KilnError(f"outils manquants :\n{hints}")


def repo_root(start: Path) -> Path:
    try:
        return Path(capture(["git", "rev-parse", "--show-toplevel"], start))
    except KilnError:
        raise KilnError(
            f"{start} n'est pas dans un dépôt git : se placer dans un repo, ou kiln new"
        ) from None
