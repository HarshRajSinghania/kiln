"""Styles du terminal : palette pierre et feu (celle du four de la bannière) et messages.

Les couleurs ne sortent que vers un terminal, sans `NO_COLOR` ni `TERM=dumb` : hors terminal,
le texte reste nu, pour les journaux et les sorties capturées. 24 bits quand le terminal
l'annonce (`COLORTERM`), sinon la palette de 256 couleurs.
"""

import os
import sys
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class Color:
    true_color: str  # « r;g;b »
    palette: str  # indice dans les 256 couleurs


STONE_LIGHT = Color("185;185;180", "250")
STONE = Color("140;140;135", "245")
STONE_DARK = Color("95;95;92", "240")
BRICK = Color("180;75;35", "130")
FIRE = Color("247;150;40", "208")
EMBER = Color("205;50;35", "160")
GLOW = Color("255;225;120", "222")
MOSS = Color("130;190;110", "107")
WHITE = Color("255;255;255", "231")
SOOT = Color("25;25;25", "234")
CHEEK = Color("230;130;120", "174")

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def is_styled(stream: TextIO | None = None) -> bool:
    """`stream` : sys.stdout par défaut, lu à l'appel (pytest le remplace)."""
    return (
        (stream or sys.stdout).isatty()
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM", "") != "dumb"
    )


def foreground(color: Color) -> str:
    return _escape(38, color)


def background(color: Color) -> str:
    return _escape(48, color)


def _escape(layer: int, color: Color) -> str:
    if os.environ.get("COLORTERM", "") in ("truecolor", "24bit"):
        return f"\033[{layer};2;{color.true_color}m"
    return f"\033[{layer};5;{color.palette}m"


def paint(
    text: str,
    color: Color | None = None,
    *,
    bold: bool = False,
    dim: bool = False,
    stream: TextIO | None = None,
) -> str:
    """Le texte en couleur pour ce flux, ou tel quel s'il ne prend pas les couleurs."""
    if not is_styled(stream):
        return text
    codes = (BOLD if bold else "") + (DIM if dim else "") + (foreground(color) if color else "")
    return f"{codes}{text}{RESET}" if codes else text


def step(title: str) -> None:
    """Début d'une étape : un losange de feu et le titre en gras."""
    if is_styled():
        print(f"\n{paint('◆', FIRE)} {paint(title, bold=True)}", flush=True)
    else:
        print(f"\n==> {title}", flush=True)


def success(message: str) -> None:
    print(f"\n{paint('✓', MOSS, bold=True)} {paint(message, bold=True)}", flush=True)


def note(message: str) -> None:
    print(paint(message, dim=True), flush=True)


def error(message: str) -> None:
    mark = paint("✗", EMBER, bold=True, stream=sys.stderr)
    print(f"{mark} {paint('kiln', bold=True, stream=sys.stderr)} : {message}", file=sys.stderr)
