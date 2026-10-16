"""Suivi du travail : conversion de l'ancien `docs/a-faire/` en `docs/backlog/`."""

import subprocess
from pathlib import Path

from kiln.backlog import migrate_legacy_backlog

TEMPLATE_BACKLOG = (
    Path(__file__).parent.parent / "template/docs/backlog/backlog.md.jinja"
).read_text()

LEGACY = """# À faire

Tout ce qu'il reste à faire sur Demo, en une seule liste rangée par criticité. Créée le
**2026-01-02**. Ce qui est fait est dans la section « ✅ Fait » en bas.

La boussole est **la démo en ligne**.

---

## Mode d'emploi (humains et agents)

- **Identifiant** `AF-NN` : stable. **Prochain libre : AF-04.**

---

## 🔴 Critique

### AF-01 · Livrer la démo
- **État** : en cours — branche feat/demo, depuis le 3 janvier
- **Effort** : S · **Qui** : Claude · **Échéance** : —
- **Origine** : réunion

Après AF-03.
- [ ] Une étape.

## ⚪ Fond — chantiers longs et dette

### AF-03 · Nettoyer
- **État** : bloqué — attend antoine
- **Effort** : XS · **Qui** : — · **Échéance** : —
- **Origine** : —

---

## ✅ Fait

### Journal

- **2026-01-02** · AF-02 · Démarrer — fait (feat/init)
"""


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_legacy_tracker_becomes_an_english_backlog(tmp_path: Path) -> None:
    legacy = tmp_path / "docs/a-faire"
    legacy.mkdir(parents=True)
    (legacy / "a-faire.md").write_text(LEGACY)
    (legacy / "ecarte.md").write_text("# Écarté\n\n## Sans suite\n\n- AF-09 · Abandonné\n")
    (legacy / "urgent.md").write_text("# Urgent\n\nTexte.\n\n- [ ] Payer — antoine\n  suite\n")
    (legacy / "audit-api-2026-01-03.md").write_text("# Audit\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(
        tmp_path,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-qm",
        "init",
        "--date=2026-01-02T10:00:00",
    )
    backlog = tmp_path / "docs/backlog"
    backlog.mkdir(parents=True)
    (backlog / "backlog.md").write_text(TEMPLATE_BACKLOG)
    (backlog / "urgent.md").write_text("# Urgent\n\nWhat only a human can do.\n")

    assert migrate_legacy_backlog(tmp_path)

    text = (backlog / "backlog.md").read_text()
    assert "North star: **la démo en ligne**." in text
    assert "Next free: T-04." in text
    assert "**2026-01-02**" in text
    assert "### T-01 · Livrer la démo" in text
    assert "- **Status**: in progress — branch feat/demo, since 3 janvier" in text
    assert text.count("- **Opened**: 2026-01-02") == 2
    assert "- **Effort**: S · **Owner**: Claude · **Due**: —" in text
    assert "- **Status**: blocked — waiting for antoine" in text
    assert "## ⚪ Background — long-running work, debt and ideas" in text
    assert "Après T-03." in text
    assert "- **2026-01-02** · T-02 · Démarrer" in text
    assert "AF-" not in text and "État" not in text and "Mode d'emploi" not in text
    assert "## Dropped" in (backlog / "rejected.md").read_text()
    assert "T-09" in (backlog / "rejected.md").read_text()
    urgent = (backlog / "urgent.md").read_text()
    assert urgent.startswith("# Urgent\n\nWhat only a human can do.\n")
    assert "- [ ] Payer — antoine\n  suite\n" in urgent
    assert (backlog / "audit-api-2026-01-03.md").exists()
    assert not legacy.exists()


def test_nothing_to_migrate(tmp_path: Path) -> None:
    assert not migrate_legacy_backlog(tmp_path)


def test_tracker_deleted_by_copier_is_read_back_from_the_last_commit(tmp_path: Path) -> None:
    legacy = tmp_path / "docs/a-faire"
    legacy.mkdir(parents=True)
    (legacy / "a-faire.md").write_text(LEGACY)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    (legacy / "a-faire.md").unlink()  # Copier retire un fichier que le modèle n'a plus
    legacy.rmdir()
    (tmp_path / "docs/backlog").mkdir()
    (tmp_path / "docs/backlog/backlog.md").write_text(TEMPLATE_BACKLOG)

    assert migrate_legacy_backlog(tmp_path)

    assert "### T-01 · Livrer la démo" in (tmp_path / "docs/backlog/backlog.md").read_text()
