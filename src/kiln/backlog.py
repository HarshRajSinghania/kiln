"""Suivi du travail : passage de l'ancien `docs/a-faire/` (en français) à `docs/backlog/`.

`kiln update` l'appelle après Copier : le modèle a posé un `docs/backlog/` vierge, que le suivi
du repo remplace, converti (titres, champs et états en anglais, `AF-NN` devenu `T-NN`) ; le
texte des tickets reste tel qu'écrit. Copier a déjà supprimé `docs/a-faire/`, même modifié :
son contenu se relit dans le dernier commit (`kiln update` part d'un arbre propre).
"""

import re
import shutil
from pathlib import Path

from kiln.shell import KilnError, capture

LEGACY_DIR = Path("docs/a-faire")
BACKLOG_DIR = Path("docs/backlog")

STATUSES = (
    ("à faire", "todo"),
    ("en cours — branche", "in progress — branch"),
    ("bloqué — attend", "blocked — waiting for"),
    ("à vérifier", "to verify"),
)
SECTIONS = (
    ("## 🔴 Critique", "## 🔴 Critical"),
    ("## 🟠 Important", "## 🟠 Important"),
    ("## 🟡 Normal", "## 🟡 Normal"),
    ("## ⚪ Fond", "## ⚪ Background — long-running work, debt and ideas"),
    ("## ✅ Fait", "## ✅ Done"),
    ("### Journal", "### Log"),
)
REJECTED_HEADINGS = (
    ("# Écarté", "# Rejected"),
    ("## Exclu pour de bon", "## Ruled out for good"),
    ("## Refusé pour cette saison", "## Declined for now"),
    ("## Sans suite", "## Dropped"),
)
LEGACY_INTROS = (
    "Trois catégories, à ne pas confondre.",
    "Décisions définitives : à ne pas reproposer, même si un audit le recommande.",
)


def migrate_legacy_backlog(root: Path) -> bool:
    """Convertit `docs/a-faire/` en `docs/backlog/` s'il existe encore ; dit s'il l'a fait."""
    old_backlog = read_legacy(root, "a-faire.md")
    if old_backlog is None:
        return False
    backlog = root / BACKLOG_DIR
    backlog.mkdir(parents=True, exist_ok=True)
    fresh = backlog / "backlog.md"
    template_text = fresh.read_text() if fresh.exists() else ""
    dates = opened(root, (LEGACY_DIR / "a-faire.md").as_posix())
    fresh.write_text(convert_backlog(old_backlog, template_text, dates))
    if (rejected := read_legacy(root, "ecarte.md")) is not None:
        (backlog / "rejected.md").write_text(convert_rejected(rejected))
    if (urgent := read_legacy(root, "urgent.md")) is not None:
        urgent_path = backlog / "urgent.md"
        intro = urgent_path.read_text() if urgent_path.exists() else "# Urgent\n"
        urgent_path.write_text(convert_urgent(urgent, intro))
    legacy = root / LEGACY_DIR
    if legacy.exists():
        for name in ("a-faire.md", "ecarte.md", "urgent.md", "README.md"):
            (legacy / name).unlink(missing_ok=True)
        # Comptes rendus d'audit en cours : ils suivent le suivi.
        for leftover in legacy.iterdir():
            shutil.move(leftover, backlog / leftover.name)
        legacy.rmdir()
    return True


def read_legacy(root: Path, name: str) -> str | None:
    """Un fichier de l'ancien suivi : sur le disque, sinon dans le dernier commit."""
    path = root / LEGACY_DIR / name
    if path.exists():
        return path.read_text()
    try:
        return capture(["git", "show", f"HEAD:{(LEGACY_DIR / name).as_posix()}"], root) + "\n"
    except KilnError:
        return None


def opened(root: Path, path: str) -> dict[str, str]:
    """Date d'ouverture de chaque ticket : le premier commit où son titre apparaît."""
    dates: dict[str, str] = {}
    try:
        log = capture(["git", "log", "--reverse", "--format=commit %as", "-p", "--", path], root)
    except KilnError:
        return dates
    day = ""
    for line in log.splitlines():
        if line.startswith("commit "):
            day = line.removeprefix("commit ")
        elif match := re.match(r"\+### AF-(\d+) ·", line):
            dates.setdefault(match[1], day)
    return dates


def convert_backlog(text: str, template_text: str, dates: dict[str, str]) -> str:
    """`a-faire.md` en `backlog.md` : en-tête et mode d'emploi du modèle, tickets convertis."""
    next_free = re.search(r"Prochain libre : AF-(\d+)", text)
    compass = re.search(r"La boussole est \*\*(.+?)\*\*", text, re.S)
    started = re.search(r"Créée le\s+\*\*(.+?)\*\*", text)
    body = text[text.index("## 🔴") :] if "## 🔴" in text else text
    body = convert_tickets(body, dates)
    header = template_text[: template_text.index("## 🔴")] if "## 🔴" in template_text else ""
    if next_free:
        header = re.sub(r"Next free: T-\d+", f"Next free: T-{next_free[1]}", header)
    if compass:
        header = re.sub(r"North star: \*\*.*?\*\*", f"North star: **{compass[1]}**", header)
    if started:
        header = re.sub(r"Started on\s+\*\*.*?\*\*", f"Started on\n**{started[1]}**", header)
    return header + body


def convert_tickets(text: str, dates: dict[str, str]) -> str:
    lines: list[str] = []
    ticket = ""
    for line in text.splitlines():
        for old, new in SECTIONS:
            if line.startswith(old):
                line = new
        if match := re.match(r"### AF-(\d+) ·", line):
            ticket = match[1]
        elif line.startswith("- **État** : "):
            status = line.removeprefix("- **État** : ")
            for old, new in STATUSES:
                if status.startswith(old):
                    status = new + status.removeprefix(old)
            status = re.sub(r"depuis le ", "since ", status)
            lines += ["- **Type**: task", f"- **Status**: {status}"]
            lines.append(f"- **Opened**: {dates.get(ticket) or '—'}")
            continue
        line = line.replace("- **Effort** : ", "- **Effort**: ")
        line = line.replace(" · **Qui** : ", " · **Owner**: ")
        line = line.replace(" · **Échéance** : ", " · **Due**: ")
        line = line.replace("- **Origine** : ", "- **Origin**: ")
        if line.startswith("Une ligne par entrée terminée"):
            line = "One line per closed ticket, most recent first:"
        line = line.replace(
            "`- **AAAA-MM-JJ** · AF-NN · Titre — ce qui a été fait (branche)`.",
            "`- **YYYY-MM-DD** · T-NN · Title — what was done (branch) · opened YYYY-MM-DD`.",
        )
        lines.append(re.sub(r"\bAF-(\d+|NN)\b", r"T-\1", line))
    return "\n".join(lines) + "\n"


def convert_rejected(text: str) -> str:
    lines = []
    for line in text.splitlines():
        for old, new in REJECTED_HEADINGS:
            if line == old:
                line = new
        if line == LEGACY_INTROS[0]:
            line = "Three kinds, not to be confused."
        elif line == LEGACY_INTROS[1]:
            line = "Final decisions: do not propose them again, even if an audit recommends it."
        lines.append(re.sub(r"\bAF-(\d+)\b", r"T-\1", line))
    return "\n".join(lines) + "\n"


def convert_urgent(text: str, intro: str) -> str:
    """Les cases d'`urgent.md` sous l'introduction du modèle, en anglais."""
    lines = text.splitlines()
    first_box = next((i for i, line in enumerate(lines) if line.startswith("- [")), len(lines))
    boxes = "\n".join(lines[first_box:]).strip("\n")
    body = intro.rstrip("\n") + "\n"
    return body + f"\n{boxes}\n" if boxes else body
