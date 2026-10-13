"""La stack d'un projet (backend, frontend, podman), lue dans ses réponses Copier.

Un dépôt adopté, que kiln n'a pas généré, n'a pas de réponses : sa stack se déduit alors de
fichiers marqueurs (`detect_stack`), pour que `check`, `dev`, `install` et `contrat` y servent.
`update` et `set`, qui appliquent le modèle, restent réservés aux dépôts générés.

Tout ce qui dépend des frameworks choisis passe par ici : dossiers Python et pnpm, serveurs de
développement, contrôles. Les commandes (`install`, `dev`, `check`, `update`, `set`) ne
connaissent pas les frameworks, seulement une `Stack`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml  # fourni par copier

from kiln.shell import KilnError

ANSWERS_FILE = ".copier-answers.yml"
BACKEND_DIR = "backend"
FRONTEND_DIR = "frontend"

PYTHON_BACKENDS = frozenset({"django", "fastapi", "data", "cli"})
API_BACKENDS = frozenset({"django", "fastapi"})
PYTHON_FRONTENDS = frozenset({"streamlit", "dash"})
PNPM_FRONTENDS = frozenset({"nuxt", "next", "astro"})
NO_FRAMEWORK = "aucun"

# Projets générés avant le choix des frameworks : Django et Nuxt, seule stack d'alors.
LEGACY_BACKEND = "django"
LEGACY_FRONTEND = "nuxt"

# Fichier dont la présence désigne un framework, dans l'ordre de recherche.
BACKEND_MARKERS: tuple[tuple[str, str], ...] = (
    ("manage.py", "django"),
    ("app/main.py", "fastapi"),
    ("notebooks", "data"),
)
FRONTEND_MARKERS: tuple[tuple[str, str], ...] = (
    ("nuxt.config.ts", "nuxt"),
    ("next.config.ts", "next"),
    ("next.config.mjs", "next"),
    ("astro.config.mjs", "astro"),
)
PODMAN_MARKERS = ("compose.yml", "docker-compose.yml", "config/local/compose.yml")

BACKEND_DEV_COMMANDS: Mapping[str, tuple[str, ...]] = {
    "django": ("uv", "run", "python", "manage.py", "runserver"),
    "fastapi": ("uv", "run", "uvicorn", "app.main:app", "--reload", "--port", "8000"),
    "data": ("uv", "run", "marimo", "edit", "notebooks", "--port", "2718", "--headless"),
}
FRONTEND_DEV_COMMANDS: Mapping[str, tuple[str, ...]] = {
    "nuxt": ("pnpm", "dev"),
    "next": ("pnpm", "dev"),
    "astro": ("pnpm", "dev"),
    "streamlit": ("uv", "run", "streamlit", "run", "app.py"),
    "dash": ("uv", "run", "python", "app.py"),
}
PNPM_CHECK_SCRIPTS: Mapping[str, tuple[str, ...]] = {
    "nuxt": ("lint", "typecheck"),
    "next": ("lint", "typecheck"),
    "astro": ("typecheck",),
}
# Produits de build et d'installation d'un framework, retirés quand on en change (`kiln set`).
# Jamais de données ni de .env : seulement ce que l'outil régénère. Le verrou en fait partie : il
# n'est pas dans le modèle, Copier ne le retirerait pas, et kiln le recrée pour le nouveau.
PYTHON_ARTIFACTS = (
    "uv.lock",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".coverage",
)
BUILD_ARTIFACTS: Mapping[str, tuple[str, ...]] = {
    "django": PYTHON_ARTIFACTS,
    "fastapi": PYTHON_ARTIFACTS,
    "data": (*PYTHON_ARTIFACTS, "__marimo__"),
    "cli": PYTHON_ARTIFACTS,
    "streamlit": PYTHON_ARTIFACTS,
    "dash": PYTHON_ARTIFACTS,
    "nuxt": ("pnpm-lock.yaml", "node_modules", ".nuxt", ".output", ".data"),
    "next": ("pnpm-lock.yaml", "node_modules", ".next", "next-env.d.ts", "tsconfig.tsbuildinfo"),
    "astro": ("pnpm-lock.yaml", "node_modules", ".astro", "dist"),
}
PYTHON_CHECKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff", ("uv", "run", "ruff", "check", ".")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("mypy", ("uv", "run", "mypy", ".")),
    ("pytest", ("uv", "run", "pytest", "-q")),
)


@dataclass(frozen=True)
class Command:
    """Une commande à lancer dans un dossier du projet, avec son libellé."""

    label: str
    directory: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class Stack:
    backend: str
    frontend: str
    has_podman: bool

    @property
    def has_api(self) -> bool:
        return self.backend in API_BACKENDS

    @property
    def python_dirs(self) -> tuple[str, ...]:
        backend_dirs = (BACKEND_DIR,) if self.backend in PYTHON_BACKENDS else ()
        frontend_dirs = (FRONTEND_DIR,) if self.frontend in PYTHON_FRONTENDS else ()
        return backend_dirs + frontend_dirs

    @property
    def pnpm_dir(self) -> str | None:
        return FRONTEND_DIR if self.frontend in PNPM_FRONTENDS else None

    def dev_commands(self) -> list[Command]:
        commands = []
        if self.backend in BACKEND_DEV_COMMANDS:
            commands.append(Command(self.backend, BACKEND_DIR, BACKEND_DEV_COMMANDS[self.backend]))
        if self.frontend in FRONTEND_DEV_COMMANDS:
            argv = FRONTEND_DEV_COMMANDS[self.frontend]
            commands.append(Command(self.frontend, FRONTEND_DIR, argv))
        return commands

    def check_commands(self) -> list[Command]:
        commands = [
            Command(f"{directory} {label}", directory, argv)
            for directory in self.python_dirs
            for label, argv in PYTHON_CHECKS
        ]
        if self.pnpm_dir is not None:
            commands += [
                Command(f"{self.pnpm_dir} {script}", self.pnpm_dir, ("pnpm", script))
                for script in PNPM_CHECK_SCRIPTS[self.frontend]
            ]
        return [*commands, Command("charte", ".", ("charte",))]


def read_answers(root: Path) -> dict[str, object]:
    answers_path = root / ANSWERS_FILE
    if not answers_path.exists():
        raise KilnError(
            f"pas de {ANSWERS_FILE} : ce dépôt n'a pas été généré par kiln "
            "(check, dev, install et contrat marchent quand même, pile déduite des fichiers)"
        )
    loaded = yaml.safe_load(answers_path.read_text())
    return dict(loaded) if isinstance(loaded, dict) else {}


def answers_if_any(root: Path) -> dict[str, object]:
    """Réponses Copier, vides pour un dépôt adopté."""
    return read_answers(root) if (root / ANSWERS_FILE).exists() else {}


def stack_from_answers(answers: Mapping[str, object]) -> Stack:
    return Stack(
        backend=str(answers.get("backend", LEGACY_BACKEND)),
        frontend=str(answers.get("frontend", LEGACY_FRONTEND)),
        has_podman=answers.get("podman") is True,
    )


def _first_marker(directory: Path, markers: tuple[tuple[str, str], ...]) -> str:
    return next((name for marker, name in markers if (directory / marker).exists()), NO_FRAMEWORK)


def detect_stack(root: Path) -> Stack:
    """Stack d'un dépôt adopté, déduite de ses fichiers marqueurs."""
    return Stack(
        backend=_first_marker(root / BACKEND_DIR, BACKEND_MARKERS),
        frontend=_first_marker(root / FRONTEND_DIR, FRONTEND_MARKERS),
        has_podman=any((root / marker).exists() for marker in PODMAN_MARKERS),
    )


def load_stack(root: Path) -> Stack:
    if not (root / ANSWERS_FILE).exists():
        return detect_stack(root)
    return stack_from_answers(read_answers(root))
