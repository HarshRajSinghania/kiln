#!/usr/bin/env python3
"""SessionStart : propose kiln à jour dans un repo kiln, et kiln tout court dans un autre repo.

Au lancement d'une session (pas à la reprise ni après /clear) :
1. Outil, dans un repo généré par kiln : si l'outil `kiln` installé est en retard sur la dernière
   version (tag `vN.M.P` de `main`), Claude demande (oui/non) s'il faut le mettre à jour, avec
   les plugins de la marketplace kiln.
2. Repo, dans un repo généré par kiln : une fois l'outil à jour, si le repo part d'une version du
   modèle plus ancienne (`_commit` de `.copier-answers.yml`), Claude demande s'il faut lancer
   `kiln update`.
3. Adoption, dans un repo où l'on a déjà commité et qui ne suit pas kiln (ni généré, ni adopté) :
   Claude demande s'il faut l'adopter (`kiln adopt`, skill `base:adoption`).

Quand reposer une question après un « non », et à quel point l'utilisateur veut de kiln : module
commun `relances.py` (note de bienveillance du poste, délais par genre de question). Après 4
« non » à une mise à jour, la question propose aussi de désinstaller kiln (outil) ou de délier le
repo de kiln (repo) ; l'adoption propose « Jamais pour ce repo » dès la première fois.

Crée aussi `.claude/kiln` dans tout repo où tourne le plugin, kiln ou non : lien vers ce plugin tel
qu'il est installé sur le poste (ignoré par git, au besoin par `.git/info/exclude`), pour voir ses
skills et ses hooks dans l'éditeur. Claude Code ne charge pas les skills de
ce dossier : rien n'est chargé deux fois.

Jamais bloquant : trois secondes au plus par appel réseau, silence sans réseau. Un repo s'en
exempte par `git config kiln-a-jour.desactive true`.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relances

ANSWERS_FILE = ".copier-answers.yml"
KILN_SOURCE_MARKERS = ("antoine-tena/kiln", "antoine-tena/init-repo")
KILN_GIT_URL = "https://github.com/antoine-tena/kiln"
# `v0.4.0`, `v0.4.0-rc.2`, et ce que `git describe` ajoute derrière (`v0.4.0-3-gabc1234`).
RELEASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?(?:-\d+-g[0-9a-f]+)?$")
# Une version promue passe après toutes ses candidates.
FINAL = 10**9
CONFIG_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kiln" / "config.toml"
)
INTERNAL_CHANNEL = "interne"
CHARTER_FILE = "charte.toml"
UPDATE = "maj"
ADOPTION = "adoption"
TIMEOUT_SECONDS = 3
STARTUP_SOURCE = "startup"
TOOL_KEY = "outil"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_LINK = Path(".claude") / "kiln"


def answer(text: str, key: str) -> str:
    """Valeur d'une clé de premier niveau des réponses Copier (sans dépendre de PyYAML)."""
    match = re.search(rf"^{re.escape(key)}:\s*['\"]?([^'\"\n]*)", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def release_key(ref: str) -> tuple[int, int, int, int] | None:
    """Clé de tri d'une version (`v0.4.0-rc.2` → (0, 4, 0, 2)) ; None pour un simple commit."""
    match = RELEASE_TAG.match(ref.strip())
    if match is None:
        return None
    candidate = match.group(4)
    return (*(int(match.group(i)) for i in (1, 2, 3)), int(candidate) if candidate else FINAL)


def follows_candidates() -> bool:
    """Le poste est-il au canal `interne` (`canal = "interne"` dans la config de kiln) ?"""
    try:
        values = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return False
    return values.get("canal") == INTERNAL_CHANNEL


def run(*command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)


# --- Outil : kiln installé par uv, depuis PyPI, depuis GitHub (commit) ou un dossier (checkout) ---

# Outils uv qui portent kiln : `kiln-cli` (nom du paquet PyPI), `kiln` (avant PyPI).
TOOL_NAMES = ("kiln-cli", "kiln")
PYPI_NAME = TOOL_NAMES[0]


def installed_kiln() -> tuple[str, str] | None:
    """("pypi", version), ("git", commit) ou ("dossier", chemin) de l'outil installé ; None
    s'il est absent."""
    tool_dir = run("uv", "tool", "dir").stdout.strip()
    if not tool_dir:
        return None
    for name in TOOL_NAMES:
        for metadata in Path(tool_dir, name).glob("lib/python*/site-packages/kiln*.dist-info"):
            direct_url = metadata / "direct_url.json"
            if not direct_url.exists():
                version = next(
                    (
                        line.removeprefix("Version: ")
                        for line in (metadata / "METADATA").read_text().splitlines()
                        if line.startswith("Version: ")
                    ),
                    "",
                )
                return ("pypi", f"v{version}")
            origin = json.loads(direct_url.read_text())
            if "vcs_info" in origin:
                return ("git", str(origin["vcs_info"].get("commit_id", "")))
            return ("dossier", str(origin.get("url", "")).removeprefix("file://"))
    return None


def has_legacy_tool() -> bool:
    """L'outil uv `kiln` d'avant PyPI : à retirer avant d'installer `kiln-cli`, qui fournit la
    même commande."""
    tool_dir = run("uv", "tool", "dir").stdout.strip()
    return bool(tool_dir) and Path(tool_dir, "kiln").is_dir()


def latest_release() -> tuple[str, str] | None:
    """(tag, commit) de la dernière version, candidates comprises au canal `interne` ; None sans
    réseau ou sans version."""
    candidates = follows_candidates()
    commits: dict[str, str] = {}
    for line in run("git", "ls-remote", "--tags", f"{KILN_GIT_URL}.git").stdout.splitlines():
        commit, _, ref = line.partition("\t")
        tag = ref.removeprefix("refs/tags/")
        # Un tag annoté a deux lignes ; `^{}` donne le commit qu'il désigne.
        if tag.endswith("^{}"):
            commits[tag.removesuffix("^{}")] = commit
        else:
            commits.setdefault(tag, commit)
    releases = [
        (key, tag)
        for tag in commits
        if (key := release_key(tag)) is not None and (candidates or key[3] == FINAL)
    ]
    if not releases:
        return None
    tag = max(releases)[1]
    return tag, commits[tag]


def is_tool_outdated(install: tuple[str, str] | None, tag: str, release_commit: str) -> bool:
    if install is None:
        return True
    kind, where = install
    if kind == "pypi":
        current, latest = release_key(where), release_key(tag)
        return latest is not None and (current is None or current < latest)
    if kind == "git":
        return where != release_commit
    return (
        run("git", "-C", where, "merge-base", "--is-ancestor", release_commit, "HEAD").returncode
        != 0
    )


def is_repo_late(commit: str, tag: str) -> bool:
    current, latest = release_key(commit), release_key(tag)
    return latest is not None and (current is None or current < latest)


def tool_update_command(install: tuple[str, str] | None, tag: str) -> str:
    # Le plugin base installé pour tout le poste : ses skills, ses hooks et le lien `.claude/kiln`
    # dans tous les repos, pas seulement ceux qui le déclarent.
    plugins = (
        f"(claude plugin marketplace add {KILN_GIT_URL.removeprefix('https://github.com/')} "
        "|| true) && claude plugin marketplace update kiln && claude plugin install base@kiln "
        "--scope user"
    )
    legacy = "uv tool uninstall kiln && " if has_legacy_tool() else ""
    key = release_key(tag)
    final = key is not None and key[3] == FINAL
    # PyPI n'a que les versions promues : une candidate (canal `interne`) passe par GitHub.
    if final and (install is None or install[0] == "pypi"):
        version = tag.removeprefix("v")
        return f'{legacy}uv tool install --force "{PYPI_NAME}=={version}" && {plugins}'
    if install is None or install[0] in ("git", "pypi"):
        return f'{legacy}uv tool install --force "git+{KILN_GIT_URL}@{tag}" && {plugins}'
    return f'git -C "{install[1]}" pull --ff-only && uv tool install --reinstall "{install[1]}"'


# --- Repo : de quelle version du modèle part-il ? ---


def git_root(cwd: str) -> Path | None:
    """Racine du repo git (ou du worktree) de la session, s'il n'est pas exempté."""
    root = run("git", "-C", cwd, "rev-parse", "--show-toplevel").stdout.strip()
    if not root:
        return None
    if run("git", "-C", root, "config", "--get", "kiln-a-jour.desactive").stdout.strip() == "true":
        return None
    return Path(root)


def kiln_repo(cwd: str) -> tuple[Path, str] | None:
    """Racine et commit du modèle d'un repo généré par kiln, s'il n'en est pas exempté."""
    root = git_root(cwd)
    if root is None:
        return None
    answers_path = Path(root) / ANSWERS_FILE
    if not answers_path.is_file():
        return None
    answers = answers_path.read_text(encoding="utf-8")
    commit = answer(answers, "_commit")
    if not commit or not any(m in answer(answers, "_src_path") for m in KILN_SOURCE_MARKERS):
        return None
    return root, commit


def link_plugin(root: Path, plugin_root: Path = PLUGIN_ROOT) -> None:
    """`.claude/kiln` pointe vers le plugin installé ; un vrai dossier à ce nom reste intact."""
    link = root / PLUGIN_LINK
    if link.is_symlink():
        if link.resolve() == plugin_root:
            ignore_locally(root)
            return
        link.unlink()
    elif link.exists():
        return
    try:
        link.parent.mkdir(exist_ok=True)
        link.symlink_to(plugin_root, target_is_directory=True)
    except OSError:
        # Windows sans le mode développeur refuse les liens symboliques : on s'en passe.
        return
    ignore_locally(root)


def ignore_locally(root: Path) -> None:
    """Le lien n'apparaît jamais dans `git status`, même dans un repo que kiln n'a pas généré :
    il va dans `.git/info/exclude`, propre au poste, sans toucher aux fichiers du repo."""
    if run("git", "-C", str(root), "check-ignore", "-q", str(PLUGIN_LINK)).returncode == 0:
        return
    common_dir = run("git", "-C", str(root), "rev-parse", "--git-common-dir").stdout.strip()
    if not common_dir:
        return
    exclude = (root / common_dir) / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a", encoding="utf-8") as exclude_file:
        exclude_file.write(f"\n# Lien vers le plugin kiln (hook kiln-a-jour)\n{PLUGIN_LINK}\n")


# --- Adoption : un repo à soi qui ne suit pas encore kiln ---


def is_adoptable(root: Path) -> bool:
    """Repo ni généré ni adopté par kiln, ni modèle Copier, où l'utilisateur a déjà commité (pas
    un clone pour lire le code d'un autre), sur un poste où la commande `kiln` est installée."""
    if shutil.which("kiln") is None:
        return False
    if any((root / name).exists() for name in (ANSWERS_FILE, CHARTER_FILE, "copier.yml")):
        return False
    workflows = root / ".github" / "workflows"
    if workflows.is_dir() and any(
        marker in path.read_text(encoding="utf-8", errors="ignore")
        for path in workflows.glob("*.y*ml")
        for marker in KILN_SOURCE_MARKERS
    ):
        return False
    email = run("git", "-C", str(root), "config", "user.email").stdout.strip()
    if not email:
        return False
    mine = run("git", "-C", str(root), "log", "-1", "--format=%H", f"--author={email}")
    return bool(mine.stdout.strip())


# --- Consignes données à Claude ---


def answer_command(verdict: str, kind: str, key: Path | str) -> str:
    return f'`{relances.SCRIPT} {verdict} {kind} "{key}"`'


def tool_question(state: relances.State) -> str:
    choices = "« Oui », « Non »"
    extra = ""
    if relances.is_long_refusal(state, UPDATE, TOOL_KEY):
        choices += ", « Désinstaller kiln »"
        extra = (
            " La question commence par « Ça fait longtemps que tu dis non : tu veux désinstaller "
            "kiln ? ». Si « Désinstaller kiln » : `uv tool uninstall kiln-cli && claude plugin "
            f"uninstall base@kiln`, puis {answer_command('jamais', UPDATE, TOOL_KEY)}."
        )
    return (
        "L'outil kiln installé sur ce poste est en retard sur la dernière version. Avant toute "
        "autre chose, au début de ta première réponse, demande avec l'outil AskUserQuestion "
        f"s'il faut mettre kiln à jour ({choices}).{extra} Si « Oui » : skill "
        "`base:maj-kiln` avec l'argument `outil`. Si « Non » : "
        f"{answer_command('non', UPDATE, TOOL_KEY)}, sans rien mettre à jour. Reprends ensuite "
        "sa demande."
    )


def repo_question(root: Path, commit: str, tag: str, state: relances.State) -> str:
    choices = "« Oui », « Non »"
    extra = ""
    if relances.is_long_refusal(state, UPDATE, str(root)):
        choices += f", « Délier {root.name} de kiln »"
        extra = (
            f" La question commence par « Ça fait longtemps que tu dis non : tu veux délier "
            f"{root.name} de kiln ? ». Si « Délier » : sur une branche dédiée, supprimer "
            f"`{ANSWERS_FILE}` (kiln ne mettra plus ce repo à jour), commiter et fusionner avec "
            f"le skill `base:fusion`, puis {answer_command('jamais', UPDATE, root)}."
        )
    return (
        f"kiln {tag} est sortie ; {root.name} part de {commit}. Avant toute "
        "autre chose, au début de ta réponse, demande avec l'outil AskUserQuestion s'il faut "
        f"mettre {root.name} à jour ({choices}).{extra} Si « Oui » : skill `base:maj-kiln` "
        f"avec l'argument `depot`. Si « Non » : {answer_command('non', UPDATE, root)}. Reprends "
        "ensuite sa demande."
    )


def adoption_question(root: Path) -> str:
    return (
        f"{root.name} ne suit pas kiln. Au début de ta première réponse, en une phrase, propose "
        "avec l'outil AskUserQuestion de l'adopter : sa charte vérifiée après chaque édition, "
        "avant chaque commit et en CI, le suivi du travail dans docs/backlog/, le repo dans "
        "`kiln status` (« Oui », « Plus tard », « Jamais pour ce repo »). Si « Oui » : skill "
        f"`base:adoption`. Si « Plus tard » : {answer_command('non', ADOPTION, root)}. Si "
        f"« Jamais pour ce repo » : {answer_command('jamais', ADOPTION, root)}. Ni insistance "
        "ni rappel ensuite ; reprends sa demande."
    )


def update_instructions(
    root: Path,
    commit: str,
    state: relances.State,
    release: Callable[[], tuple[str, str] | None],
) -> str:
    relances.count_session(state, UPDATE, TOOL_KEY)
    relances.count_session(state, UPDATE, str(root))
    # Un « non » à l'outil repousse aussi la question du repo : sans réseau d'ici l'échéance.
    if not relances.is_due(state, UPDATE, TOOL_KEY):
        return ""
    latest = release()
    if latest is None:
        return ""
    tag, release_commit = latest
    repo_due = relances.is_due(state, UPDATE, str(root)) and is_repo_late(commit, tag)
    if is_tool_outdated(installed_kiln(), tag, release_commit):
        follow_up = ""
        if repo_due:
            follow_up = " Une fois l'outil mis à jour avec succès : " + repo_question(
                root, commit, tag, state
            )
        return tool_question(state) + follow_up
    return repo_question(root, commit, tag, state) if repo_due else ""


def adoption_instructions(root: Path, state: relances.State) -> str:
    if not is_adoptable(root):
        return ""
    relances.count_session(state, ADOPTION, str(root))
    if not relances.is_due(state, ADOPTION, str(root)):
        return ""
    relances.mark_asked(state, ADOPTION)
    return adoption_question(root)


def instructions(
    cwd: str,
    state: relances.State,
    release: Callable[[], tuple[str, str] | None] = latest_release,
) -> str:
    root = git_root(cwd)
    if root is None:
        return ""
    relances.count_station_session(state)
    repo = kiln_repo(cwd)
    if repo is None:
        return adoption_instructions(root, state)
    return update_instructions(*repo, state, release)


def tool_status() -> str:
    """`à jour`, ou la commande qui met à jour l'outil installé (skill `base:maj-kiln`)."""
    latest = latest_release()
    if latest is None:
        return "à jour"
    install = installed_kiln()
    if is_tool_outdated(install, *latest):
        return tool_update_command(install, latest[0])
    return "à jour"


def main() -> None:
    if sys.argv[1:] == [TOOL_KEY]:
        print(tool_status())
        return
    try:
        payload = json.load(sys.stdin)
        if payload.get("source", STARTUP_SOURCE) != STARTUP_SOURCE:
            return
        cwd = payload.get("cwd") or "."
        # Le lien vaut pour tout repo où tourne le plugin ; les mises à jour, pour les repos kiln.
        root = git_root(cwd)
        if root is not None:
            link_plugin(root)
        state = relances.load()
        message = instructions(cwd, state)
        relances.save(state)
    except Exception:
        # Réseau absent, GitHub qui limite, repo illisible : la session démarre sans rien dire.
        return
    if message:
        hook_output = {"hookEventName": "SessionStart", "additionalContext": message}
        print(json.dumps({"hookSpecificOutput": hook_output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
