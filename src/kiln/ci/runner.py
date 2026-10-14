"""`kiln ci` : rejoue la CI d'un commit sur le poste et en garde le verdict sur le commit.

Pour un repo dont la CI GitHub ne tourne pas (forfait épuisé, dépôt sans Actions) : le commit est
extrait dans un worktree détaché, hors du repo, ses dépendances installées comme sur GitHub
(verrous figés), puis les jobs du `ci.yml` rejoués. Le verdict part en note git sur origin, où le
script de déploiement le lit.
"""

import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

from kiln.ci.execution import Workspace, base_env, run_lanes, run_step, say
from kiln.ci.jobs import Plan, Step, plan_job
from kiln.ci.services import remove_orphan_containers
from kiln.ci.verdict import JobOutcome, Verdict, read_verdict, record_verdict
from kiln.ci.workflow import load_jobs
from kiln.shell import KilnError, capture, require_tools

CACHE_DIR = Path.home() / ".cache" / "kiln" / "ci"
SHORT_SHA = 12
PREPARATION = "préparation"


def run_local_ci(
    root: Path, revision: str, skipped_jobs: frozenset[str], should_push: bool, should_keep: bool
) -> Verdict:
    require_tools("git", "uv", "podman")
    if orphan_count := remove_orphan_containers():
        say(f"{orphan_count} conteneurs d'un kiln ci interrompu retirés")
    sha = capture(["git", "rev-parse", "--verify", f"{revision}^{{commit}}"], root)
    started_at, started = datetime.now().astimezone(), time.monotonic()
    workspace = _create_workspace(root, sha)
    try:
        jobs = load_jobs(workspace.root)
        replayed = [job for job in jobs if job.is_replayable and job.name not in skipped_jobs]
        plans = [plan_job(job) for job in replayed]
        skipped = [(job.name, job.reason) for job in jobs if not job.is_replayable]
        skipped += [(name, "écarté par --sauter") for name in sorted(skipped_jobs)]
        say(f"kiln ci {sha[:SHORT_SHA]} : {len(plans)} jobs rejoués, {len(skipped)} non rejoués")
        outcomes = _prepare(plans, workspace) or run_lanes(plans, workspace)
    finally:
        if not should_keep:
            _remove_workspace(root, workspace.root)
    verdict = Verdict(sha, tuple(outcomes), tuple(skipped), started_at, time.monotonic() - started)
    record_verdict(root, verdict, should_push)
    return verdict


def show_verdict(root: Path, revision: str) -> bool:
    """Affiche la note de `kiln ci` du commit ; vrai si elle dit succès."""
    sha = capture(["git", "rev-parse", "--verify", f"{revision}^{{commit}}"], root)
    note = read_verdict(root, sha)
    if note is None:
        print(f"{sha[:SHORT_SHA]} n'a jamais été rejoué par kiln ci (kiln ci {revision}).")
        return False
    print(note, end="")
    return note.startswith("kiln ci : succès")


def _create_workspace(root: Path, sha: str) -> Workspace:
    # Nom de l'arbre principal, même lancé depuis un worktree : la status line le cherche ainsi.
    common_dir = capture(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root)
    name = f"{Path(common_dir).parent.name}-{sha[:SHORT_SHA]}"
    worktree, log_dir = CACHE_DIR / name, CACHE_DIR / "journaux" / name
    _remove_workspace(root, worktree)
    shutil.rmtree(log_dir, ignore_errors=True)
    log_dir.mkdir(parents=True)
    capture(["git", "worktree", "add", "--detach", str(worktree), sha], root)
    return Workspace(worktree, log_dir, f"kiln-ci-{name}")


def _remove_workspace(root: Path, worktree: Path) -> None:
    if worktree.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=root,
            capture_output=True,
            check=False,
        )
        shutil.rmtree(worktree, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=root, capture_output=True, check=False)


def _prepare(plans: list[Plan], workspace: Workspace) -> list[JobOutcome]:
    """Installe les dépendances une fois pour tous les jobs ; une issue en échec sinon rien."""
    python_dirs = sorted({directory for plan in plans for directory in plan.python_dirs})
    pnpm_dirs = sorted({directory for plan in plans for directory in plan.pnpm_dirs})
    steps = [Step(f"uv sync {path}", "uv sync --locked", path) for path in python_dirs]
    install = "pnpm install --frozen-lockfile"
    steps += [Step(f"pnpm install {path}", install, path) for path in pnpm_dirs]
    env = base_env({})
    log_path = workspace.log_dir / f"{PREPARATION}.log"
    for step in steps:
        if not run_step(step, workspace.root, env, log_path, PREPARATION):
            return [JobOutcome(PREPARATION, is_success=False, failed_step=step.label)]
    return []


def require_known_jobs(root: Path, names: frozenset[str]) -> None:
    known = {job.name for job in load_jobs(root)}
    unknown = sorted(names - known)
    if unknown:
        raise KilnError(f"jobs inconnus dans le ci.yml : {', '.join(unknown)}")
