"""`kiln status --all` et `kiln update --all` : tous les repos kiln du dossier de code.

`update --all` ne change jamais la branche de l'arbre principal d'un repo : il travaille dans un
worktree (`.claude/worktrees/`) partant de la branche d'intégration, commite par lots de dix
fichiers au plus, pousse et ouvre une PR (en brouillon si les contrôles échouent), puis retire le
worktree. La branche reste, pour la PR.
"""

import datetime
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kiln import ui
from kiln.check import run_checks
from kiln.install import install_project
from kiln.shell import KilnError, capture, require_tools, run, step
from kiln.stack import ANSWERS_FILE, CHARTER_FILE, answers_if_any, load_stack, read_answers
from kiln.update import update_project

KILN_SOURCE_MARKERS = ("antoine-tena/kiln", "antoine-tena/init-repo")
KILN_GITHUB_REPO = "antoine-tena/kiln"
# Ce qui fait le modèle : un commit qui n'y touche pas ne met aucun repo en retard.
TEMPLATE_PATHS = ("template/", "copier.yml", "macros.jinja")
SEARCH_DEPTH = 3
# Un dépôt adopté (que kiln n'a pas généré) se reconnaît à sa charte : `status` le montre,
# `update --all` l'ignore, car appliquer le modèle écraserait ses fichiers écrits à la main.
ADOPTED_MARKER = CHARTER_FILE
SKIPPED_DIRS = frozenset({"node_modules", ".venv", ".git", ".claude", "_archives"})
WORKTREES_DIR = Path(".claude") / "worktrees"
UPDATE_BRANCH_PREFIX = "chore/kiln-update"
DEFAULT_INTEGRATION_BRANCH = "main"
# Préférée quand origin l'a : un clone n'a pas toujours `origin/HEAD`, et `main` y est alors
# souvent figée par une règle GitHub.
PREFERRED_INTEGRATION_BRANCH = "develop"
MAX_FILES_PER_COMMIT = 10
# pre-commit refuse de tourner tant que sa configuration modifiée n'est pas commitée.
FIRST_COMMITTED = ".pre-commit-config.yaml"
CONFLICT_MARKER = "<<<<<<< before updating"
COMMIT_ATTEMPTS = 2


@dataclass(frozen=True)
class ManagedRepo:
    root: Path
    template_commit: str


def find_repos(code_dir: Path) -> list[ManagedRepo]:
    """Repos du dossier de code générés par kiln (ou par init-repo, son ancien nom)."""
    repos = []
    for answers_path in _marker_files(code_dir, ANSWERS_FILE, SEARCH_DEPTH):
        root = answers_path.parent
        answers = read_answers(root)
        if (root / ".git").is_dir() and any(
            marker in str(answers.get("_src_path", "")) for marker in KILN_SOURCE_MARKERS
        ):
            repos.append(ManagedRepo(root, str(answers.get("_commit", ""))))
    return repos


def find_adopted(code_dir: Path) -> list[Path]:
    """Repos du dossier de code qui suivent une charte kiln sans avoir été générés par kiln."""
    return [
        marker.parent
        for marker in _marker_files(code_dir, ADOPTED_MARKER, SEARCH_DEPTH)
        if (marker.parent / ".git").is_dir() and not (marker.parent / ANSWERS_FILE).exists()
    ]


def _marker_files(directory: Path, name: str, depth: int) -> list[Path]:
    found = [directory / name] if (directory / name).is_file() else []
    if depth == 0:
        return found
    for child in sorted(directory.iterdir()):
        if child.is_dir() and child.name not in SKIPPED_DIRS:
            found += _marker_files(child, name, depth - 1)
    return found


def template_changed_since(commit: str) -> bool:
    """Le modèle a-t-il changé sur kiln depuis `commit` ? Seuls ses fichiers comptent."""
    changed = capture(
        [
            "gh",
            "api",
            f"repos/{KILN_GITHUB_REPO}/compare/{commit}...HEAD",
            "-q",
            ".files[].filename",
        ],
        Path.cwd(),
    ).split()
    return is_template_change(changed)


def is_template_change(changed_paths: list[str]) -> bool:
    return any(path.startswith(TEMPLATE_PATHS) for path in changed_paths)


def require_code_dir(code_dir: Path) -> None:
    """Le dossier de code existe : sinon, dire où le régler plutôt que de planter."""
    if not code_dir.is_dir():
        raise KilnError(
            f"dossier de code introuvable : {code_dir}. Le régler dans ~/.config/kiln/config.toml "
            '(dossier_code = "<dossier qui contient vos repos>")'
        )


STATUS_COLUMNS = (("repo", 30), ("branche", 22), ("arbre", 8), ("modèle", 17), ("taille", 6))
# Couleur de chaque état : vert ce qui va, feu ce qui demande une action.
STATE_COLORS = {
    "propre": ui.MOSS,
    "modifié": ui.FIRE,
    "modèle à jour": ui.MOSS,
    "modèle en retard": ui.FIRE,
    "adopté": ui.STONE,
}


def show_status(code_dir: Path) -> None:
    header = " ".join(f"{title:<{width}}" for title, width in STATUS_COLUMNS) + " stack"
    print(" ", ui.paint(header.upper(), ui.STONE, bold=True))
    for repo in find_repos(code_dir):
        is_current = bool(repo.template_commit) and not template_changed_since(repo.template_commit)
        _print_status(code_dir, repo.root, "modèle à jour" if is_current else "modèle en retard")
    for root in find_adopted(code_dir):
        _print_status(code_dir, root, "adopté")


def _print_status(code_dir: Path, root: Path, template_state: str) -> None:
    branch = capture(["git", "branch", "--show-current"], root)
    is_dirty = bool(capture(["git", "status", "--porcelain"], root))
    stack = load_stack(root)
    size = answers_if_any(root).get("envergure", "?")
    tree_state = "modifié" if is_dirty else "propre"
    print(
        " ",
        ui.paint(f"{root.relative_to(code_dir)!s:<30}", bold=True),
        ui.paint(f"{branch:<22}", ui.STONE_LIGHT),
        ui.paint(f"{tree_state:<8}", STATE_COLORS[tree_state]),
        ui.paint(f"{template_state:<17}", STATE_COLORS[template_state]),
        ui.paint(f"{size!s:<6}", ui.STONE),
        f"{stack.backend} + {stack.frontend}{' + podman' if stack.has_podman else ''}",
    )


def update_all(code_dir: Path, *, allow_major: bool) -> None:
    require_tools("git", "uv")
    results = [
        (repo, update_one(repo.root, allow_major=allow_major)) for repo in find_repos(code_dir)
    ]
    step("Bilan")
    for repo, outcome in results:
        print(f"{repo.root.relative_to(code_dir)!s:<30} {outcome}")


def update_one(root: Path, *, allow_major: bool) -> str:
    """Met un repo à jour dans un worktree puis le fusionne directement dans l'intégration
    ([PAS-SUR-MAIN]) ; contrôles en échec, la branche est poussée sans fusion. Renvoie le bilan
    en une ligne."""
    step(f"Repo {root.name}")
    integration = integration_branch(root)
    branch = f"{UPDATE_BRANCH_PREFIX}-{datetime.date.today().isoformat()}"
    worktree = root / WORKTREES_DIR / branch.replace("/", "-")
    try:
        _create_worktree(root, worktree, branch, integration)
        failed_checks = _update_worktree(worktree, allow_major=allow_major)
        conflicted = conflicted_files(worktree)
        if conflicted:
            return f"conflits à résoudre ({', '.join(conflicted)}) dans {worktree}"
        if not capture(["git", "status", "--porcelain"], worktree):
            _remove_worktree(root, worktree, branch=branch)
            return "déjà à jour"
        commit_in_batches(worktree)
        if failed_checks:
            run(["git", "push", "-q", "-u", "origin", branch], worktree)
            return (
                f"contrôles en échec ({', '.join(failed_checks)}) : branche {branch} poussée, "
                f"non fusionnée, worktree {worktree}"
            )
        _merge_into_integration(worktree, branch, integration)
    except KilnError as error:
        return f"échec : {error} (worktree laissé dans {worktree})"
    _remove_worktree(root, worktree, branch=branch)
    return f"fusionné dans {integration}"


def _update_worktree(worktree: Path, *, allow_major: bool) -> list[str]:
    """Installe, met à jour modèle et dépendances, puis renvoie les contrôles en échec."""
    install_project(worktree)
    update_project(
        worktree,
        should_update_template=True,
        should_update_deps=True,
        allow_major=allow_major,
        should_check=False,
    )
    return run_checks(worktree)


def conflicted_files(worktree: Path) -> list[str]:
    """Fichiers où Copier a laissé un conflit à résoudre à la main."""
    found = subprocess.run(
        ["git", "grep", "-l", "--untracked", CONFLICT_MARKER],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    return found.stdout.split()


def integration_branch(root: Path) -> str:
    preferred = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "-q",
            f"refs/remotes/origin/{PREFERRED_INTEGRATION_BRANCH}",
        ],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if preferred.returncode == 0:
        return PREFERRED_INTEGRATION_BRANCH
    completed = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    head = completed.stdout.strip()
    return head.removeprefix("origin/") if completed.returncode == 0 else DEFAULT_INTEGRATION_BRANCH


def _create_worktree(root: Path, worktree: Path, branch: str, integration: str) -> None:
    run(["git", "fetch", "-q", "origin", integration], root)
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(WORKTREES_DIR / "x")], cwd=root, check=False
    )
    if ignored.returncode != 0:
        with (root / ".git" / "info" / "exclude").open("a") as exclude:
            exclude.write(f"\n{WORKTREES_DIR.as_posix()}/\n")
    run(
        [
            "git",
            "worktree",
            "add",
            "-q",
            "--no-track",
            str(worktree),
            "-b",
            branch,
            f"origin/{integration}",
        ],
        root,
    )


def _remove_worktree(root: Path, worktree: Path, *, branch: str | None = None) -> None:
    run(["git", "worktree", "remove", "--force", str(worktree)], root)
    if branch is not None:
        run(["git", "branch", "-q", "-D", branch], root)


def commit_in_batches(worktree: Path) -> None:
    """Commits de dix fichiers au plus ([COMMITS]), regroupés par dossier de premier niveau."""
    run(["git", "add", "-A"], worktree)
    changed = capture(["git", "diff", "--cached", "--name-only"], worktree).splitlines()
    run(["git", "reset", "-q"], worktree)
    groups: dict[str, list[str]] = {}
    if FIRST_COMMITTED in changed:
        groups["pre-commit"] = [FIRST_COMMITTED]
        changed.remove(FIRST_COMMITTED)
    for path in changed:
        groups.setdefault(path.split("/")[0] if "/" in path else "racine", []).append(path)
    for group, paths in groups.items():
        for start in range(0, len(paths), MAX_FILES_PER_COMMIT):
            batch = paths[start : start + MAX_FILES_PER_COMMIT]
            _commit(worktree, batch, f"chore: mise à jour kiln, {group}"[:50])


def _commit(worktree: Path, paths: list[str], message: str) -> None:
    """Commit avec les crochets pre-commit ; un crochet qui corrige (ruff) a droit à un retour."""
    for _ in range(COMMIT_ATTEMPTS):
        run(["git", "add", "-A", "--", *paths], worktree)
        committed = subprocess.run(
            ["git", "commit", "-q", "-m", message], cwd=worktree, check=False
        )
        if committed.returncode == 0:
            return
    raise KilnError(f"commit refusé par les crochets : {message}")


def _merge_into_integration(worktree: Path, branch: str, integration: str) -> None:
    """Commit de fusion au-dessus de l'intégration publiée, poussé tel quel ([FUSION])."""
    run(["git", "fetch", "-q", "origin", integration], worktree)
    run(["git", "switch", "-q", "--detach", f"origin/{integration}"], worktree)
    run(
        [
            "git",
            "merge",
            "-q",
            "--no-ff",
            branch,
            "-m",
            f"Merge branch '{branch}' into {integration}",
        ],
        worktree,
    )
    run(["git", "push", "-q", "origin", f"HEAD:{integration}"], worktree)
