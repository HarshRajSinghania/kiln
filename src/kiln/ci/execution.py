"""Exécution des jobs de `kiln ci` : étapes en série, un journal par job, couloirs en parallèle.

Comme sur GitHub, un job s'arrête à sa première étape en échec (sauf une étape `should_always_run`),
et l'échec d'un job n'empêche pas les suivants. Le couloir `back` (pytest, le plus long) tourne à
côté du couloir `front` ; dans un couloir, les jobs se suivent, pour ne pas écrire à deux dans les
mêmes fichiers (types générés, build du front).
"""

import os
import shutil
import subprocess
import threading
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from kiln.ci.jobs import Plan, Step
from kiln.ci.services import running_services
from kiln.ci.verdict import JobOutcome

LOG_TAIL_LINES = 40
# Variables du poste qui feraient lancer les outils du worktree avec l'environnement d'un autre.
INHERITED_TO_DROP = ("VIRTUAL_ENV", "DATABASE_URL", "REDIS_URL", "PYTHONPATH")
# Chrome pour Lighthouse (CHROME_PATH) : celui du poste, sinon le Chromium de Playwright. Sur
# GitHub, l'image du runner en fournit un ; sur le poste, lhci échoue sans lui.
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
PLAYWRIGHT_BROWSERS = Path.home() / ".cache" / "ms-playwright"
_print_lock = threading.Lock()


@dataclass(frozen=True)
class Workspace:
    """Le worktree du commit rejoué, le dossier des journaux et le préfixe des conteneurs."""

    root: Path
    log_dir: Path
    container_prefix: str


def say(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def base_env(extra: Mapping[str, str]) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in INHERITED_TO_DROP}
    if "CHROME_PATH" not in env and (chrome := find_chrome()):
        env["CHROME_PATH"] = chrome
    return {**env, "CI": "true", **extra}


def find_chrome() -> str | None:
    """Chrome du poste, sinon le Chromium de Playwright le plus récent ; None s'il n'y en a pas."""
    for name in CHROME_NAMES:
        if path := shutil.which(name):
            return path
    builds = sorted(
        PLAYWRIGHT_BROWSERS.glob("chromium-*/chrome-linux*/chrome"),
        key=lambda chrome: int(chrome.parts[-3].removeprefix("chromium-")),
    )
    return str(builds[-1]) if builds else None


def run_lanes(plans: list[Plan], workspace: Workspace) -> list[JobOutcome]:
    """Lance chaque couloir dans son fil ; renvoie les issues dans l'ordre des plans."""
    lanes: dict[str, list[Plan]] = {}
    for plan in plans:
        lanes.setdefault(plan.lane, []).append(plan)
    with ThreadPoolExecutor(max_workers=len(lanes) or 1) as executor:
        futures = [executor.submit(_run_lane, lane, workspace) for lane in lanes.values()]
        outcomes = {outcome.name: outcome for future in futures for outcome in future.result()}
    return [outcomes[plan.job.name] for plan in plans]


def _run_lane(plans: list[Plan], workspace: Workspace) -> list[JobOutcome]:
    return [run_job(plan, workspace) for plan in plans]


def run_job(plan: Plan, workspace: Workspace) -> JobOutcome:
    name = plan.job.name
    log_path = workspace.log_dir / f"{name}.log"
    say(f"[{name}] démarré (journal : {log_path})")
    failed_step = ""
    try:
        with running_services(plan.services, f"{workspace.container_prefix}-{name}") as urls:
            env = base_env({**plan.env, **urls})
            for step in plan.steps:
                if failed_step and not step.should_always_run:
                    continue
                if not run_step(step, workspace.root, env, log_path, name):
                    failed_step = failed_step or step.label
    except Exception as error:  # un service qui ne démarre pas fait échouer le job, pas la CI
        _append(log_path, f"\n!! {error}\n")
        failed_step = failed_step or f"services : {error}"
    say(f"[{name}] {'ÉCHEC à « ' + failed_step + ' »' if failed_step else 'ok'}")
    if failed_step:
        say(_tail(log_path))
    return JobOutcome(name, not failed_step, failed_step)


def run_step(step: Step, root: Path, env: Mapping[str, str], log_path: Path, job: str) -> bool:
    started = time.monotonic()
    _append(log_path, f"\n==> {step.label} ({step.directory})\n$ {step.command}\n")
    with log_path.open("a") as log_file:
        completed = subprocess.run(
            ["bash", "-e", "-c", step.command],
            cwd=root / step.directory,
            env=dict(env),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    elapsed = round(time.monotonic() - started)
    status = "ok" if completed.returncode == 0 else f"échec (code {completed.returncode})"
    say(f"[{job}] {step.label} : {status}, {elapsed} s")
    return completed.returncode == 0


def _append(log_path: Path, text: str) -> None:
    with log_path.open("a") as log_file:
        log_file.write(text)


def _tail(log_path: Path) -> str:
    lines = log_path.read_text(errors="replace").splitlines()[-LOG_TAIL_LINES:]
    return "\n".join(f"    {line}" for line in lines)
