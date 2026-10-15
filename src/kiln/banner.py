"""Bannière d'accueil des commandes longues (`new`, `install`, `update`, `status`).

Un four en pixel art, dessiné en demi-blocs (deux pixels par caractère), à côté de la version
de kiln, de la commande lancée, du projet et de son dossier. Hors terminal, ou avec `NO_COLOR`,
une seule ligne sans dessin : les journaux et les sorties capturées restent lisibles.
"""

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from kiln.shell import KilnError
from kiln.stack import NO_FRAMEWORK, answers_if_any, load_stack

# Un caractère = deux pixels superposés : B brique, F flamme, Y cœur de la flamme, . vide.
LOGO = (
    "..........BB..",
    "...BBBBBB.BB..",
    "..BBBBBBBBBB..",
    ".BBBBBBBBBBBB.",
    ".BBBB.F..BBBB.",
    ".BBB..FF..BBB.",
    ".BBB.FYYF.BBB.",
    "BBBBBBBBBBBBBB",
)
# Couleur de chaque pixel : 24 bits, et repli sur la palette de 256 couleurs.
TRUE_COLORS = {"B": "217;98;43", "F": "247;179;43", "Y": "255;230;140"}
PALETTE_COLORS = {"B": "166", "F": "214", "Y": "222"}
EMPTY = "."
UPPER_HALF, LOWER_HALF, FULL_BLOCK = "▀", "▄", "█"
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
LOGO_MARGIN, TEXT_GAP = "  ", "   "


def show_banner(action: str, root: Path | None = None) -> None:
    """Affiche la bannière ; `root` : le repo concerné, sinon le dossier courant sans projet."""
    title = f"kiln v{_kiln_version()}"
    details = [action, *([_project_summary(root)] if root is not None else [])]
    location = _home_relative(root or Path.cwd())
    if not _supports_drawing():
        print(" · ".join([title, *details, location]), flush=True)
        return
    text_lines = ["", f"{BOLD}{title}{RESET}", f"{DIM}{' · '.join(details)}{RESET}", location]
    drawing = _render_logo(*_color_scheme())
    print()
    for logo_line, text_line in zip(drawing, text_lines, strict=True):
        print(f"{LOGO_MARGIN}{logo_line}{TEXT_GAP}{text_line}".rstrip())
    print(flush=True)


def _render_logo(mode: str, colors: dict[str, str]) -> list[str]:
    """`mode` : 2 pour les couleurs 24 bits, 5 pour la palette de 256 couleurs."""

    def foreground(pixel: str) -> str:
        return f"\033[38;{mode};{colors[pixel]}m"

    def background(pixel: str) -> str:
        return f"\033[48;{mode};{colors[pixel]}m"

    lines = []
    for top_row, bottom_row in zip(LOGO[0::2], LOGO[1::2], strict=True):
        cells = []
        for top, bottom in zip(top_row, bottom_row, strict=True):
            if top == EMPTY and bottom == EMPTY:
                cells.append(" ")
            elif bottom == EMPTY:
                cells.append(f"{foreground(top)}{UPPER_HALF}{RESET}")
            elif top == EMPTY:
                cells.append(f"{foreground(bottom)}{LOWER_HALF}{RESET}")
            elif top == bottom:
                cells.append(f"{foreground(top)}{FULL_BLOCK}{RESET}")
            else:
                cells.append(f"{foreground(top)}{background(bottom)}{UPPER_HALF}{RESET}")
        lines.append("".join(cells))
    return lines


def _color_scheme() -> tuple[str, dict[str, str]]:
    if os.environ.get("COLORTERM", "") in ("truecolor", "24bit"):
        return "2", TRUE_COLORS
    return "5", PALETTE_COLORS


def _project_summary(root: Path) -> str:
    """Nom du projet, envergure et frameworks : `annski · flame · django + nuxt, podman`."""
    try:
        answers = answers_if_any(root)
        stack = load_stack(root)
    except KilnError, OSError, ValueError:
        return root.name
    frameworks = [name for name in (stack.backend, stack.frontend) if name != NO_FRAMEWORK]
    pile = " + ".join(frameworks) + (", podman" if stack.has_podman else "")
    parts = [str(answers.get("nom", root.name)), str(answers.get("envergure", "")), pile]
    return " · ".join(part for part in parts if part)


def _kiln_version() -> str:
    try:
        return version("kiln")
    except PackageNotFoundError:
        return "?"


def _home_relative(path: Path) -> str:
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)


def _supports_drawing() -> bool:
    return (
        sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM", "") != "dumb"
    )
