"""Styles du terminal : palette pierre et feu (celle du four de la bannière) et messages.

Les couleurs ne sortent que vers un terminal, sans `NO_COLOR` ni `TERM=dumb` : hors terminal,
le texte reste nu, pour les journaux et les sorties capturées. 24 bits quand le terminal
l'annonce (`COLORTERM`), sinon la palette de 256 couleurs.
"""

import os
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
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


@dataclass
class StepRecord:
    title: str
    started: float = field(default_factory=time.monotonic)
    ended: float | None = None
    failed: bool = False

    @property
    def duration(self) -> float:
        return (self.ended or time.monotonic()) - self.started


# Étapes de la commande en cours, pour le récapitulatif final.
_steps: list[StepRecord] = []


def step(title: str) -> None:
    """Début d'une étape : un losange de feu et le titre en gras ; l'étape précédente se clôt."""
    _close_last_step()
    _steps.append(StepRecord(title))
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


def _close_last_step() -> None:
    if _steps and _steps[-1].ended is None:
        _steps[-1].ended = time.monotonic()


def format_duration(seconds: float) -> str:
    """`0,4 s`, `12 s`, `1 min 05 s` : virgule décimale, à la française."""
    if seconds < 10:
        return f"{seconds:.1f} s".replace(".", ",")
    if seconds < 60:
        return f"{seconds:.0f} s"
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes} min {rest:02d} s"


def _columns() -> int:
    return shutil.get_terminal_size((100, 24)).columns


def _fit(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(width - 1, 0)] + "…"


SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
SPINNER_DELAY = 0.08


class Spinner:
    """Ligne animée pendant une commande externe : roue de feu, commande, dernière ligne de sa
    sortie en gris. À la fin, une ligne fixe : ✓ ou ✗, la commande et sa durée."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.detail = ""
        self.started = time.monotonic()
        self._stopped = threading.Event()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def start(self) -> None:
        sys.stdout.write("\033[?25l")  # curseur masqué pendant l'animation
        self._thread.start()

    def stop(self) -> None:
        """Efface la ligne animée et rend le curseur ; sans effet la seconde fois."""
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._thread.join()
        sys.stdout.write("\r\033[2K\033[?25h")
        sys.stdout.flush()

    def show(self, line: str) -> None:
        if line.strip():
            with self._lock:
                self.detail = line.strip()

    def finish(self, *, succeeded: bool, output: str = "") -> None:
        """Ligne finale ; en échec, l'étape est marquée et la sortie s'affiche dans une marge."""
        self.stop()
        if not succeeded and _steps:
            _steps[-1].failed = True
        mark = paint("✓", MOSS) if succeeded else paint("✗", EMBER, bold=True)
        elapsed = paint(format_duration(time.monotonic() - self.started), STONE_DARK)
        label = _fit(self.label, _columns() - 16)
        print(f"  {mark} {paint(label, STONE)}  {elapsed}", flush=True)
        if not succeeded:
            margin = paint("│", EMBER)
            for line in output.rstrip().splitlines():
                print(f"    {margin} {line}")
            sys.stdout.flush()

    def _spin(self) -> None:
        frame = 0
        while not self._stopped.wait(SPINNER_DELAY):
            with self._lock:
                detail = self.detail
            label = _fit(self.label, _columns() // 2)
            room = _columns() - len(label) - 8
            wheel = paint(SPINNER_FRAMES[frame % len(SPINNER_FRAMES)], FIRE)
            text = paint(label, STONE_LIGHT)
            if detail and room > 10:
                text += paint(f"  {_fit(detail, room)}", STONE_DARK)
            sys.stdout.write(f"\r\033[2K  {wheel} {text}")
            sys.stdout.flush()
            frame += 1


RECAP_TITLES = {
    "new": "Projet créé",
    "install": "Installation terminée",
    "update": "Mise à jour terminée",
    "check": "Contrôles terminés",
    "set": "Paramètres appliqués",
    "contrat": "Contrat régénéré",
}


def recap(command: str, started: float, *, succeeded: bool) -> None:
    """Bilan encadré de la commande : verdict, durée totale, durée de chaque étape."""
    _close_last_step()
    if not _steps:
        return
    total = format_duration(time.monotonic() - started)
    if succeeded:
        verdict = f"{RECAP_TITLES.get(command, 'Terminé')} en {total}"
    else:
        verdict = f"Interrompu après {total}"
    if not is_styled():
        print(f"\n{verdict} ({len(_steps)} étapes)", flush=True)
        return
    durations = [format_duration(record.duration) for record in _steps]
    inner = min(
        max(
            len(verdict) + 2,
            *(len(r.title) + len(d) + 6 for r, d in zip(_steps, durations, strict=True)),
        ),
        _columns() - 6,
    )
    edge = foreground(STONE_DARK)
    bar = f"{edge}│{RESET}"
    mark = paint("✓", MOSS, bold=True) if succeeded else paint("✗", EMBER, bold=True)
    print(f"\n  {edge}╭{'─' * (inner + 2)}╮{RESET}")
    head = paint(_fit(verdict, inner - 2), bold=True)
    print(f"  {bar} {mark} {head}{' ' * (inner - 2 - len(_fit(verdict, inner - 2)))} {bar}")
    print(f"  {edge}├{'─' * (inner + 2)}┤{RESET}")
    for index, (record, duration) in enumerate(zip(_steps, durations, strict=True)):
        is_failure = record.failed or (not succeeded and index == len(_steps) - 1)
        title = _fit(record.title, inner - len(duration) - 4)
        gap = " " * (inner - 2 - len(title) - len(duration))
        dot = paint("✗", EMBER) if is_failure else paint("·", STONE_DARK)
        shown = paint(title, EMBER) if is_failure else title
        print(f"  {bar} {dot} {shown}{gap}{paint(duration, STONE)} {bar}")
    print(f"  {edge}╰{'─' * (inner + 2)}╯{RESET}", flush=True)


def panel(title: str, lines: list[str]) -> None:
    """Encadré : un titre en feu, puis des lignes (une ligne `vN …` en gras, `- …` en puce)."""
    if not is_styled():
        print(f"\n{title}", *(f"  {line}" for line in lines), sep="\n", flush=True)
        return
    inner = min(max(len(title), *(len(line) for line in lines)) + 2, _columns() - 6)
    edge = foreground(STONE_DARK)
    bar = f"{edge}│{RESET}"
    print(f"\n  {edge}╭{'─' * (inner + 2)}╮{RESET}")
    shown_title = _fit(title, inner)
    print(f"  {bar} {paint(shown_title, FIRE, bold=True)}{' ' * (inner - len(shown_title))} {bar}")
    print(f"  {edge}├{'─' * (inner + 2)}┤{RESET}")
    for line in lines:
        text = _fit(line, inner)
        gap = " " * (inner - len(text))
        if text.startswith("- "):
            styled = f"{paint('·', FIRE)} {text[2:]}"
        elif text[:1] == "v" and text[1:2].isdigit():
            styled = paint(text, bold=True)
        else:
            styled = paint(text, STONE)
        print(f"  {bar} {styled}{gap} {bar}")
    print(f"  {edge}╰{'─' * (inner + 2)}╯{RESET}", flush=True)
