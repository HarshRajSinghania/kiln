"""Lecture du `ci.yml` d'un projet : ses jobs, et ce que `kiln ci` sait en rejouer.

Le `ci.yml` reste la seule description de la CI. Un job qui appelle un workflow réutilisable de
kiln est rejoué avec les mêmes paramètres (`with:`) ; un job écrit dans le projet l'est s'il ne
fait que des `run:` après le checkout. Les autres sont listés comme non rejoués : le verdict le dit.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from kiln.shell import KilnError

CI_WORKFLOW = Path(".github/workflows/ci.yml")
KILN_WORKFLOW = re.compile(r"antoine-tena/kiln/\.github/workflows/(?P<name>[\w-]+)\.yml@")
CHECKOUT_ACTION = "actions/checkout@"
# Workflows réutilisables de kiln que `kiln ci` sait rejouer (voir jobs.py).
REPLAYABLE_WORKFLOWS = frozenset({"django", "contrat-api", "charte", "pnpm", "securite"})
INLINE_KIND = "inline"


@dataclass(frozen=True)
class Job:
    """Un job du `ci.yml` : son type (workflow de kiln, `inline`, ou vide) et ses paramètres."""

    name: str
    kind: str
    inputs: dict[str, str] = field(default_factory=dict)
    commands: tuple[str, ...] = ()
    reason: str = ""

    @property
    def is_replayable(self) -> bool:
        return not self.reason


def load_jobs(root: Path) -> list[Job]:
    """Les jobs du `ci.yml` du projet, dans l'ordre du fichier."""
    workflow_path = root / CI_WORKFLOW
    if not workflow_path.exists():
        raise KilnError(f"pas de {CI_WORKFLOW} : rien à rejouer")
    workflow = yaml.safe_load(workflow_path.read_text())
    jobs = workflow.get("jobs") if isinstance(workflow, dict) else None
    if not isinstance(jobs, dict):
        raise KilnError(f"{CI_WORKFLOW} ne déclare aucun job")
    return [parse_job(str(name), definition) for name, definition in jobs.items()]


def parse_job(name: str, definition: object) -> Job:
    if not isinstance(definition, dict):
        return Job(name, "", reason="définition illisible")
    uses = definition.get("uses")
    if isinstance(uses, str):
        return _reusable_job(name, uses, definition.get("with"))
    return _inline_job(name, definition)


def _reusable_job(name: str, uses: str, raw_inputs: object) -> Job:
    match = KILN_WORKFLOW.search(uses)
    if match is None:
        return Job(name, "", reason=f"workflow hors kiln ({uses})")
    kind = match["name"]
    if kind not in REPLAYABLE_WORKFLOWS:
        return Job(name, kind, reason=f"workflow {kind} pas encore rejoué en local")
    pairs = raw_inputs.items() if isinstance(raw_inputs, dict) else ()
    inputs = {str(key): _input_text(value) for key, value in pairs}
    return Job(name, kind, inputs)


def _input_text(value: object) -> str:
    """Un paramètre `with:` tel que GitHub le passe : booléens en minuscules, le reste en texte."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _inline_job(name: str, definition: dict[str, object]) -> Job:
    if definition.get("services"):
        return Job(name, INLINE_KIND, reason="services propres au job")
    steps = definition.get("steps")
    if not isinstance(steps, list):
        return Job(name, INLINE_KIND, reason="aucune étape")
    commands: list[str] = []
    for step in steps:
        uses = step.get("uses") if isinstance(step, dict) else None
        if isinstance(uses, str) and uses.startswith(CHECKOUT_ACTION):
            continue
        command = step.get("run") if isinstance(step, dict) else None
        if not isinstance(command, str) or set(step) - {"name", "run", "working-directory"}:
            return Job(name, INLINE_KIND, reason="étapes autres que des commandes")
        directory = str(step.get("working-directory", "."))
        commands.append(f"cd {directory}\n{command}" if directory != "." else command)
    return Job(name, INLINE_KIND, commands=tuple(commands))
