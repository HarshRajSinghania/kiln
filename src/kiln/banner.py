"""Bannière d'accueil des commandes longues (`new`, `install`, `update`, `status`).

Un four rieur en pixel art (pierre et feu), dessiné en demi-blocs (deux pixels par caractère),
à côté de la version de kiln, de la commande lancée, du projet et de son dossier.
Hors terminal, ou avec `NO_COLOR`, une seule ligne sans dessin : les journaux et les sorties
capturées restent lisibles.
"""

import os
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from kiln.shell import KilnError
from kiln.stack import NO_FRAMEWORK, answers_if_any, load_stack

# Un caractère = deux pixels superposés. Four rieur, pierre et feu : L pierre éclairée, B pierre,
# b pierre dans l'ombre, d socle et chapeau de brique, W/K yeux, P joues, R/F/Y flamme (bord rouge,
# orange, cœur jaune), . vide.
LOGO = (
    "..........dd..",
    "...LLLBBB.bb..",
    "..LWKBBWKBbb..",
    ".LLWKBBWKBBbb.",
    ".LBP.RR..PBbb.",
    ".LBB.RFR..Bbb.",
    ".BBB.FYYF.bbb.",
    "dddddddddddddd",
)
# Couleur de chaque pixel : 24 bits, et repli sur la palette de 256 couleurs.
TRUE_COLORS = {
    "L": "185;185;180",
    "B": "140;140;135",
    "b": "95;95;92",
    "d": "180;75;35",
    "W": "255;255;255",
    "K": "25;25;25",
    "P": "230;130;120",
    "R": "205;50;35",
    "F": "247;150;40",
    "Y": "255;225;120",
}
PALETTE_COLORS = {
    "L": "250",
    "B": "245",
    "b": "240",
    "d": "130",
    "W": "231",
    "K": "234",
    "P": "174",
    "R": "160",
    "F": "208",
    "Y": "222",
}
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
