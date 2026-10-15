#!/usr/bin/env python3
"""SessionStart : propose de mettre kiln à jour, puis le repo, avec des relances espacées.

Au lancement d'une session (pas à la reprise ni après /clear) dans un repo généré par kiln :
1. Outil : si l'outil `kiln` installé est en retard sur GitHub, Claude demande (oui/non) s'il faut
   le mettre à jour, avec les plugins de la marketplace kiln.
2. Repo : une fois l'outil à jour, si le modèle a évolué depuis le commit du repo
   (`.copier-answers.yml`), Claude demande s'il faut lancer `kiln update`.

Un « non » repousse la question de 5 sessions, puis 10, 30 et 50 ; au-delà, la question propose
aussi de désinstaller kiln (outil) ou de délier le repo de kiln (repo). Les réponses sont
enregistrées par ce même script (`refus` ou `accord`), dans `~/.local/state/kiln/rappels.json`.

Jamais bloquant : trois secondes au plus par appel réseau, silence sans réseau ou hors d'un repo
kiln. Un repo s'en exempte par `git config kiln-a-jour.desactive true`.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path

ANSWERS_FILE = ".copier-answers.yml"
KILN_SOURCE_MARKERS = ("antoine-tena/kiln", "antoine-tena/init-repo")
KILN_GIT_URL = "https://github.com/antoine-tena/kiln"
COMPARE_URL = "https://api.github.com/repos/antoine-tena/kiln/compare/{commit}...HEAD"
TEMPLATE_PATHS = ("template/", "copier.yml", "macros.jinja")
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
STATE_PATH = STATE_DIR / "kiln" / "rappels.json"
# Sessions à attendre avant de reposer la question, selon le nombre de « non » déjà reçus.
DELAYS = (5, 10, 30, 50)
TIMEOUT_SECONDS = 3
STARTUP_SOURCE = "startup"
TOOL_KEY = "outil"
SCRIPT = f'python3 "{Path(__file__).resolve()}"'


def answer(text: str, key: str) -> str:
    """Valeur d'une clé de premier niveau des réponses Copier (sans dépendre de PyYAML)."""
    match = re.search(rf"^{re.escape(key)}:\s*['\"]?([^'\"\n]*)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def is_template_change(changed_paths: list[str]) -> bool:
    return any(path.startswith(TEMPLATE_PATHS) for path in changed_paths)


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)


# --- Relances : un compteur de sessions et une échéance par question ---


def load_state() -> dict[str, dict[str, int]]:
    try:
        loaded = json.loads(STATE_PATH.read_text())
        return loaded if isinstance(loaded, dict) else {}
    except OSError, ValueError:
        return {}


def save_state(state: dict[str, dict[str, int]]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def count_session(state: dict[str, dict[str, int]], key: str) -> dict[str, int]:
    entry = state.setdefault(key, {"sessions": 0, "refus": 0, "prochaine": 0})
    entry["sessions"] += 1
    return entry


def is_due(entry: dict[str, int]) -> bool:
    return entry["sessions"] >= entry["prochaine"]


def is_long_refusal(entry: dict[str, int]) -> bool:
    return entry["refus"] >= len(DELAYS)


def record(state: dict[str, dict[str, int]], key: str, *, refused: bool) -> None:
    entry = state.setdefault(key, {"sessions": 0, "refus": 0, "prochaine": 0})
    if refused:
        entry["refus"] += 1
        entry["prochaine"] = entry["sessions"] + DELAYS[min(entry["refus"], len(DELAYS)) - 1]
    else:
        entry["refus"] = 0
        entry["prochaine"] = 0


# --- Outil : kiln installé par uv, depuis GitHub (commit) ou depuis un dossier (checkout) ---


def installed_kiln() -> tuple[str, str] | None:
    """("git", commit) ou ("dossier", chemin) de l'outil installé ; None s'il est absent."""
    tool_dir = run("uv", "tool", "dir").stdout.strip()
    if not tool_dir:
        return None
    pattern = "lib/python*/site-packages/kiln-*/direct_url.json"
    for direct_url in Path(tool_dir, "kiln").glob(pattern):
        origin = json.loads(direct_url.read_text())
        if "vcs_info" in origin:
            return ("git", str(origin["vcs_info"].get("commit_id", "")))
        return ("dossier", str(origin.get("url", "")).removeprefix("file://"))
    return None


def remote_head() -> str:
    output = run("git", "ls-remote", f"{KILN_GIT_URL}.git", "HEAD").stdout.split()
    return output[0] if output else ""


def is_tool_outdated(install: tuple[str, str] | None, head: str) -> bool:
    if install is None:
        return True
    kind, where = install
    if kind == "git":
        return where != head
    return run("git", "-C", where, "merge-base", "--is-ancestor", head, "HEAD").returncode != 0


def tool_update_command(install: tuple[str, str] | None) -> str:
    plugins = "claude plugin marketplace update kiln"
    if install is None:
        return f"uv tool install git+{KILN_GIT_URL} && {plugins}"
    if install[0] == "git":
        return f"uv tool upgrade kiln && {plugins}"
    return f'git -C "{install[1]}" pull --ff-only && uv tool install --reinstall "{install[1]}"'


# --- Repo : le modèle a-t-il changé depuis le commit dont part le repo ? ---


def fetch_changed_paths(commit: str) -> list[str]:
    request = urllib.request.Request(
        COMPARE_URL.format(commit=commit), headers={"Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        comparison = json.load(response)
    return [entry["filename"] for entry in comparison.get("files", [])]


def kiln_repo(cwd: str) -> tuple[Path, str] | None:
    """Racine et commit du modèle d'un repo généré par kiln, s'il n'en est pas exempté."""
    root = run("git", "-C", cwd, "rev-parse", "--show-toplevel").stdout.strip()
    if not root:
        return None
    if run("git", "-C", root, "config", "--get", "kiln-a-jour.desactive").stdout.strip() == "true":
        return None
    answers_path = Path(root) / ANSWERS_FILE
    if not answers_path.is_file():
        return None
    answers = answers_path.read_text(encoding="utf-8")
    commit = answer(answers, "_commit")
    if not commit or not any(m in answer(answers, "_src_path") for m in KILN_SOURCE_MARKERS):
        return None
    return Path(root), commit


# --- Consignes données à Claude ---


def tool_question(install: tuple[str, str] | None, entry: dict[str, int]) -> str:
    choices = "« Oui », « Non »"
    extra = ""
    if is_long_refusal(entry):
        choices += ", « Désinstaller kiln »"
        extra = (
            " La question commence par « Ça fait longtemps que tu dis non : tu veux désinstaller "
            "kiln ? ». Si « Désinstaller kiln » : `uv tool uninstall kiln && claude plugin "
            f"uninstall base@kiln`, puis `{SCRIPT} accord {TOOL_KEY}`."
        )
    return (
        "L'outil kiln installé sur ce poste est en retard sur GitHub. Avant toute autre chose, au "
        "début de ta première réponse, demande avec l'outil AskUserQuestion s'il faut mettre kiln "
        f"à jour ({choices}).{extra} Si « Oui » : `{tool_update_command(install)}`, puis "
        f"`{SCRIPT} accord {TOOL_KEY}`, puis dis de taper /reload-plugins. Si « Non » : "
        f"`{SCRIPT} refus {TOOL_KEY}`, sans rien mettre à jour. Reprends ensuite sa demande."
    )


def repo_question(root: Path, commit: str, entry: dict[str, int]) -> str:
    choices = "« Oui », « Non »"
    extra = ""
    if is_long_refusal(entry):
        choices += f", « Délier {root.name} de kiln »"
        extra = (
            f" La question commence par « Ça fait longtemps que tu dis non : tu veux délier "
            f"{root.name} de kiln ? ». Si « Délier » : sur une branche dédiée, supprimer "
            f"`{ANSWERS_FILE}` (kiln ne mettra plus ce repo à jour), commiter et ouvrir la PR "
            f'comme le veut le CLAUDE.md du repo, puis `{SCRIPT} accord "{root}"`.'
        )
    return (
        f"Le modèle kiln a évolué depuis le commit {commit} dont part {root.name}. Avant toute "
        "autre chose, au début de ta réponse, demande avec l'outil AskUserQuestion s'il faut "
        f"mettre {root.name} à jour ({choices}).{extra} Si « Oui » : "
        "`kiln update` sur une branche dédiée `chore/kiln-update` (worktree), relire le diff, "
        f"commiter et ouvrir la PR comme le veut le CLAUDE.md du repo, puis `{SCRIPT} accord "
        f'"{root}"`. Si « Non » : `{SCRIPT} refus "{root}"`. Reprends ensuite sa demande.'
    )


def instructions(
    cwd: str,
    state: dict[str, dict[str, int]],
    fetch: Callable[[str], list[str]] = fetch_changed_paths,
) -> str:
    repo = kiln_repo(cwd)
    if repo is None:
        return ""
    root, commit = repo
    tool_entry = count_session(state, TOOL_KEY)
    repo_entry = count_session(state, str(root))
    # Un « non » à l'outil repousse aussi la question du repo : sans réseau d'ici l'échéance.
    if not is_due(tool_entry):
        return ""
    install = installed_kiln()
    if is_tool_outdated(install, remote_head()):
        follow_up = ""
        if is_due(repo_entry) and is_template_change(fetch(commit)):
            follow_up = " Une fois l'outil mis à jour avec succès : " + repo_question(
                root, commit, repo_entry
            )
        return tool_question(install, tool_entry) + follow_up
    if is_due(repo_entry) and is_template_change(fetch(commit)):
        return repo_question(root, commit, repo_entry)
    return ""


def answer_cli(arguments: list[str]) -> None:
    """`refus outil`, `accord outil`, `refus <racine du repo>`, `accord <racine du repo>`."""
    verdict, key = arguments
    state = load_state()
    record(state, key, refused=verdict == "refus")
    save_state(state)


def main() -> None:
    if len(sys.argv) == 3:
        answer_cli(sys.argv[1:])
        return
    try:
        payload = json.load(sys.stdin)
        if payload.get("source", STARTUP_SOURCE) != STARTUP_SOURCE:
            return
        state = load_state()
        message = instructions(payload.get("cwd") or ".", state)
        save_state(state)
    except Exception:
        # Réseau absent, GitHub qui limite, repo illisible : la session démarre sans rien dire.
        return
    if message:
        hook_output = {"hookEventName": "SessionStart", "additionalContext": message}
        print(json.dumps({"hookSpecificOutput": hook_output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
