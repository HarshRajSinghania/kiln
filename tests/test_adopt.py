import subprocess
import tomllib
from pathlib import Path

import pytest

from kiln import adopt
from kiln.shell import KilnError

TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un repo existant, à soi, sur une branche de travail ; la commande `charte` ne tourne pas."""
    monkeypatch.setattr(adopt, "run_status", lambda *args, **kwargs: 0)
    root = tmp_path / "Mon_Outil"
    subprocess.run(["git", "init", "-q", "-b", "chore/kiln-adopt", str(root)], check=True)
    (root / "outil.py").write_text("print('ok')\n")
    git = ["git", "-C", str(root), "-c", "user.name=N", "-c", "user.email=n@example.com"]
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "a"], check=True)
    return root


def test_adoption_adds_the_charter_and_the_backlog_without_touching_the_code(repo: Path) -> None:
    adopt.adopt_project(repo, size="flame", template=TEMPLATE_DIR)

    charter = tomllib.loads((repo / "charte.toml").read_text())
    assert charter["envergure"] == "flame"
    assert charter["interdictions"]["outils-interdits"]["id"] == "UV-PODMAN"
    assert "Mon Outil" in (repo / "docs/backlog/backlog.md").read_text()
    assert (repo / "outil.py").read_text() == "print('ok')\n"
    assert not (repo / "backend").exists()


def test_adoption_keeps_an_existing_backlog(repo: Path) -> None:
    (repo / "docs/backlog").mkdir(parents=True)
    (repo / "docs/backlog/backlog.md").write_text("à moi\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    git = ["git", "-C", str(repo), "-c", "user.name=N", "-c", "user.email=n@example.com"]
    subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "b"], check=True)

    adopt.adopt_project(repo, template=TEMPLATE_DIR)

    assert (repo / "docs/backlog/backlog.md").read_text() == "à moi\n"


def test_adoption_refuses_kiln_repos_and_dirty_trees(repo: Path) -> None:
    (repo / "brouillon.txt").write_text("")
    with pytest.raises(KilnError, match="arbre non propre"):
        adopt.check_adoptable(repo)
    (repo / "charte.toml").write_text("")
    with pytest.raises(KilnError, match="déjà adopté"):
        adopt.check_adoptable(repo)
    (repo / ".copier-answers.yml").write_text("")
    with pytest.raises(KilnError, match="généré par kiln"):
        adopt.check_adoptable(repo)


def test_project_name_follows_the_template_format() -> None:
    assert adopt.project_name(Path("Mon_Outil")) == "mon-outil"
    assert adopt.project_name(Path("2048")) == "projet-2048"
