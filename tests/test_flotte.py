import subprocess
from pathlib import Path

import pytest

from kiln import fleet
from kiln.fleet import (
    MAX_FILES_PER_COMMIT,
    commit_in_batches,
    conflicted_files,
    find_adopted,
    find_repos,
    integration_branch,
    template_state,
)
from kiln.shell import KilnError


def make_repo(root: Path, source: str) -> Path:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / ".copier-answers.yml").write_text(f"_commit: abc1234\n_src_path: {source}\n")
    return root


def test_only_kiln_repos_are_found(tmp_path: Path) -> None:
    make_repo(tmp_path / "association" / "projet", "https://github.com/antoine-tena/kiln.git")
    make_repo(tmp_path / "ancien", "https://github.com/antoine-tena/init-repo.git")
    make_repo(tmp_path / "autre", "gh:quelquun/modele")

    found = sorted(repo.root.name for repo in find_repos(tmp_path))

    assert found == ["ancien", "projet"]


def test_adopted_repo_has_a_charter_but_no_answers(tmp_path: Path) -> None:
    generated = make_repo(tmp_path / "genere", "https://github.com/antoine-tena/kiln.git")
    (generated / "charte.toml").touch()
    adopted = tmp_path / "association" / "adopte"
    (adopted / ".git").mkdir(parents=True)
    (adopted / "charte.toml").touch()

    assert find_adopted(tmp_path) == [adopted]


def test_commits_hold_at_most_ten_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "projet", "https://github.com/antoine-tena/kiln.git")
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    for index in range(MAX_FILES_PER_COMMIT + 3):
        (repo / f"fichier_{index}.txt").write_text("contenu\n")

    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    commit_in_batches(repo)

    sizes = [
        len(
            subprocess.run(
                ["git", "show", "--name-only", "--format=", revision],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.split()
        )
        for revision in ("HEAD", "HEAD~1")
    ]
    # Les treize fichiers et le fichier de réponses : dix, puis quatre.
    assert sorted(sizes) == [4, 10]


def test_conflicts_left_by_copier_are_found(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "projet", "https://github.com/antoine-tena/kiln.git")
    (repo / "README.md").write_text(
        "<<<<<<< before updating\nancien\n=======\nnouveau\n>>>>>>> after\n"
    )

    assert conflicted_files(repo) == ["README.md"]
    (repo / "README.md").write_text("nouveau\n")
    assert conflicted_files(repo) == []


def test_develop_wins_without_origin_head(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "projet", "https://github.com/antoine-tena/kiln.git")
    git = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/develop", "HEAD"], cwd=repo, check=True
    )

    assert integration_branch(repo) == "develop"


def test_template_state_compares_releases() -> None:
    assert template_state("v3", "v3") == "v3 à jour"
    assert template_state("v2.1", "v3") == "v2.1 → v3"
    assert template_state("f611f82", "v1") == "f611f82 → v1"
    assert template_state("v3", None) == "v3"


def test_missing_code_dir_is_explained(tmp_path: Path) -> None:
    with pytest.raises(KilnError, match="dossier_code"):
        fleet.require_code_dir(tmp_path / "code")


def test_update_branch_is_merged_straight_into_integration(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "develop", str(origin)], check=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    git = ["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    subprocess.run([*git, "push", "-q", "origin", "HEAD:develop"], check=True)
    subprocess.run([*git, "switch", "-q", "-c", "chore/kiln-update"], check=True)
    (clone / "f.txt").write_text("x\n")
    subprocess.run([*git, "add", "f.txt"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "chore: maj"], check=True)

    subprocess.run([*git, "config", "user.name", "t"], check=True)
    subprocess.run([*git, "config", "user.email", "t@t"], check=True)
    fleet._merge_into_integration(clone, "chore/kiln-update", "develop")

    log = subprocess.run(
        ["git", "-C", str(origin), "log", "--format=%s", "develop"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert log[0] == "Merge branch 'chore/kiln-update' into develop"
    assert "chore: maj" in log
