"""Fichiers figés : les dérogations `file = "…"` de `kiln-waivers.toml`. `kiln update` et
`kiln set` n'y touchent plus ; mais un fichier figé ne doit pas dériver en silence, d'où le
rapport de ce que kiln y a changé entre deux versions."""

import difflib
import tempfile
from pathlib import Path

import copier
from copier.errors import CopierError

from kiln import ui
from kiln.charte.waivers import WAIVERS_FILE, load
from kiln.stack import read_answers

DIFF_LINES = 40


def frozen_files(root: Path) -> list[str]:
    """Fichiers figés par une dérogation active (une dérogation échue ne fige plus rien)."""
    return [waiver.file for waiver in load(root).actives if waiver.file]


def report_frozen_drift(root: Path, source: str, previous: str, current: str) -> None:
    """Ce que kiln a changé, de `previous` à `current`, dans les fichiers que le repo a figés."""
    frozen = frozen_files(root)
    if not frozen or not previous or previous == current:
        return
    answers = {k: v for k, v in read_answers(root).items() if not k.startswith("_")}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            before = _render(source, previous, answers, Path(tmp) / "avant")
            after = _render(source, current, answers, Path(tmp) / "apres")
            diffs = {f: _diff(before / f, after / f, f) for f in frozen}
    except (CopierError, OSError) as error:  # OSError : révision introuvable (git)
        ui.note(f"Fichiers figés : comparaison des versions de kiln impossible ({error}).")
        return
    changed = {f: d for f, d in diffs.items() if d}
    if not changed:
        return
    ui.panel(
        f"kiln a changé des fichiers figés ({WAIVERS_FILE}) : {previous} → {current}",
        [f"- {f}" for f in changed]
        + ["Reporter ce qui convient, ou lever la dérogation pour reprendre le modèle."],
    )
    for diff in changed.values():
        print("\n".join(diff[:DIFF_LINES]))
        if len(diff) > DIFF_LINES:
            print(f"… et {len(diff) - DIFF_LINES} ligne(s) de plus")


def _render(source: str, ref: str, answers: dict[str, object], destination: Path) -> Path:
    copier.run_copy(
        source,
        destination,
        data=answers,
        vcs_ref=ref,
        defaults=True,
        quiet=True,
        unsafe=False,
    )
    return destination


def _diff(before: Path, after: Path, name: str) -> list[str]:
    lines = [p.read_text().splitlines() if p.exists() else [] for p in (before, after)]
    return list(
        difflib.unified_diff(*lines, f"kiln {name} (avant)", f"kiln {name} (après)", lineterm="")
    )
