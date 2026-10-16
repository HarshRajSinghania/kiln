"""Verdict de `kiln ci`, gardé en note git sur le commit (`refs/notes/ci`) et poussé sur origin.

La première ligne fait foi : `kiln ci : succès` ou `kiln ci : échec`. C'est elle que lit
`scripts/ops/lib/ci-verte.sh` avant d'autoriser un déploiement. Les lignes suivantes disent quand,
où, en combien de temps, et surtout quels jobs du `ci.yml` n'ont pas été rejoués.
"""

import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from kiln.shell import KilnError

NOTES_REF = "refs/notes/ci"
REMOTE_COPY_REF = "refs/notes/ci-origin"
SUCCESS_LINE = "kiln ci : succès"
FAILURE_LINE = "kiln ci : échec"
SECONDS_PER_MINUTE = 60


@dataclass(frozen=True)
class JobOutcome:
    name: str
    is_success: bool
    failed_step: str = ""


@dataclass(frozen=True)
class Verdict:
    sha: str
    outcomes: tuple[JobOutcome, ...]
    skipped: tuple[tuple[str, str], ...]
    started_at: datetime
    duration_seconds: float

    @property
    def is_success(self) -> bool:
        return bool(self.outcomes) and all(outcome.is_success for outcome in self.outcomes)

    def render(self) -> str:
        minutes, seconds = divmod(round(self.duration_seconds), SECONDS_PER_MINUTE)
        lines = [
            SUCCESS_LINE if self.is_success else FAILURE_LINE,
            f"commit : {self.sha}",
            f"date : {self.started_at.isoformat(timespec='seconds')}",
            f"poste : {socket.gethostname()}",
            f"durée : {minutes} min {seconds:02d} s",
            "jobs rejoués : " + ", ".join(_outcome_text(outcome) for outcome in self.outcomes),
        ]
        if self.skipped:
            skipped_text = ", ".join(f"{name} ({reason})" for name, reason in self.skipped)
            lines.append(f"non rejoués : {skipped_text}")
        return "\n".join(lines) + "\n"


def _outcome_text(outcome: JobOutcome) -> str:
    if outcome.is_success:
        return f"{outcome.name} ok"
    return f"{outcome.name} ÉCHEC ({outcome.failed_step})"


def record_verdict(root: Path, verdict: Verdict, should_push: bool) -> None:
    """Pose la note sur le commit, après avoir repris celles d'origin, puis la pousse."""
    _merge_remote_notes(root)
    _git(root, "notes", f"--ref={NOTES_REF}", "add", "-f", "-m", verdict.render(), verdict.sha)
    if should_push:
        _git(root, "push", "-q", "origin", NOTES_REF)


def read_verdict(root: Path, sha: str) -> str | None:
    """La note de `kiln ci` sur ce commit, origin comprise ; None s'il n'a jamais été rejoué."""
    _merge_remote_notes(root)
    completed = subprocess.run(
        ["git", "notes", f"--ref={NOTES_REF}", "show", sha],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else None


def _merge_remote_notes(root: Path) -> None:
    """Reprend les notes d'origin ; si un commit en a des deux côtés, la locale gagne."""
    fetched = subprocess.run(
        ["git", "fetch", "-q", "origin", f"+{NOTES_REF}:{REMOTE_COPY_REF}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if fetched.returncode == 0:
        _git(root, "notes", f"--ref={NOTES_REF}", "merge", "-q", "-s", "ours", REMOTE_COPY_REF)


def _git(root: Path, *arguments: str) -> None:
    completed = subprocess.run(
        ["git", *arguments], cwd=root, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise KilnError(f"échec de `git {' '.join(arguments[:2])}` : {completed.stderr.strip()}")
