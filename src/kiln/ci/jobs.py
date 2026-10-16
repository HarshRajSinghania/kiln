"""Étapes locales de chaque workflow réutilisable de kiln, pour `kiln ci`.

Chaque fonction reprend, étape par étape, le workflow de même nom de `.github/workflows/`, avec ses
valeurs par défaut (DEFAULTS, que tests/test_ci.py compare aux fichiers). Un workflow qui change
change ici dans le même commit.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from kiln.ci.workflow import INLINE_KIND, Job

GENERATED_DIFF = "git diff --exit-code -- ':(top,attr:linguist-generated=true)'"
DEFAULTS: Mapping[str, Mapping[str, str]] = {
    "django": {
        "dossier": "backend",
        "base": "app",
        "postgres": "docker.io/library/postgres:16-alpine",
        "redis": "docker.io/library/redis:7-alpine",
        "env": "",
        "mypy": "true",
        "couverture": "true",
    },
    "contrat-api": {
        "back": "backend",
        "front": "frontend",
        "export": "uv run python manage.py export_openapi --check --output ../openapi.json",
        "generation": "pnpm generate:api",
        "env": "",
    },
    "charte": {},
    # `rapports` : artefacts publiés sur GitHub ; en local, les journaux en tiennent lieu.
    "pnpm": {
        "dossier": "frontend",
        "pnpm": "",
        "scripts": "lint\ntypecheck\ntest\nbuild\n",
        "rapports": "",
    },
    "securite": {"uv": "backend", "pnpm": "frontend", "version-pnpm": "", "niveau": "high"},
}
BACK_LANE = "back"
FRONT_LANE = "front"


@dataclass(frozen=True)
class Step:
    """Une commande shell lancée depuis `directory` (relatif à la racine du worktree)."""

    label: str
    command: str
    directory: str = "."
    should_always_run: bool = False


@dataclass(frozen=True)
class Services:
    """Bases que le job attend : images podman (vide = aucune) et nom de la base."""

    base: str
    postgres: str
    redis: str


@dataclass(frozen=True)
class Plan:
    job: Job
    steps: tuple[Step, ...]
    lane: str = FRONT_LANE
    env: Mapping[str, str] = field(default_factory=dict)
    services: Services | None = None
    python_dirs: tuple[str, ...] = ()
    pnpm_dirs: tuple[str, ...] = ()


def plan_job(job: Job) -> Plan:
    if job.kind == INLINE_KIND:
        steps = tuple(Step(f"étape {index}", command) for index, command in enumerate(job.commands))
        return Plan(job, steps)
    inputs = {**DEFAULTS[job.kind], **job.inputs}
    return PLANNERS[job.kind](job, inputs)


def parse_env(lines: str) -> dict[str, str]:
    """Le paramètre `env` des workflows : une variable `CLE=valeur` par ligne."""
    pairs = (line.strip().split("=", 1) for line in lines.splitlines() if "=" in line)
    return {key.strip(): value for key, value in pairs}


def _django(job: Job, inputs: Mapping[str, str]) -> Plan:
    directory = inputs["dossier"]
    steps = [
        Step("ruff", "uv run ruff check .\nuv run ruff format --check .", directory),
        Step("typage (charte types)", "charte types") if inputs["mypy"] == "true" else None,
        Step(
            "aucune migration manquante",
            "uv run python manage.py makemigrations --check --dry-run",
            directory,
        ),
        Step(
            "pytest",
            "uv run pytest --cov --cov-branch --cov-report=xml --cov-report=term:skip-covered",
            directory,
        ),
        Step("planchers de couverture", "charte couverture")
        if inputs["couverture"] == "true"
        else None,
    ]
    services = Services(inputs["base"], inputs["postgres"], inputs["redis"])
    return Plan(
        job,
        tuple(step for step in steps if step is not None),
        lane=BACK_LANE,
        env=parse_env(inputs["env"]),
        services=services,
        python_dirs=(directory,),
    )


def _contract(job: Job, inputs: Mapping[str, str]) -> Plan:
    steps = (
        Step("openapi.json correspond au code", inputs["export"], inputs["back"]),
        Step(
            "types et règles de saisie conformes au schéma",
            f"{inputs['generation']}\n{GENERATED_DIFF}",
            inputs["front"],
        ),
    )
    return Plan(
        job,
        steps,
        env=parse_env(inputs["env"]),
        python_dirs=(inputs["back"],),
        pnpm_dirs=(inputs["front"],),
    )


def _charter(job: Job, inputs: Mapping[str, str]) -> Plan:
    return Plan(job, (Step("charte", "charte"),))


def _pnpm(job: Job, inputs: Mapping[str, str]) -> Plan:
    directory = inputs["dossier"]
    scripts = [line.strip() for line in inputs["scripts"].splitlines() if line.strip()]
    steps = tuple(Step(f"pnpm {script}", f"pnpm {script}", directory) for script in scripts)
    return Plan(job, steps, pnpm_dirs=(directory,))


def _security(job: Job, inputs: Mapping[str, str]) -> Plan:
    audit_command = "uv audit --locked --preview-features audit-command"
    steps = [
        Step(f"uv audit {directory}", audit_command, directory)
        for directory in inputs["uv"].split()
    ]
    if inputs["pnpm"]:
        audit = f"pnpm audit --prod --audit-level {inputs['niveau']}"
        steps.append(Step("pnpm audit", audit, inputs["pnpm"], should_always_run=True))
    return Plan(job, tuple(steps))


PLANNERS: Mapping[str, Callable[[Job, Mapping[str, str]], Plan]] = {
    "django": _django,
    "contrat-api": _contract,
    "charte": _charter,
    "pnpm": _pnpm,
    "securite": _security,
}
