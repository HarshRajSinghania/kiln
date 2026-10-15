from pathlib import Path

import pytest
from packaging.version import Version

from kiln.deps import _major_bounds
from kiln.install import ensure_env_file
from kiln.rules import charter_rules, verified_rules
from kiln.settings import parse_assignments, remove_replaced_artifacts
from kiln.shell import KilnError
from kiln.stack import Stack, answers_if_any, load_stack, stack_from_answers
from kiln.update import replace_legacy_source


def test_legacy_answers_mean_django_and_nuxt() -> None:
    assert stack_from_answers({}) == Stack(backend="django", frontend="nuxt", has_podman=False)


def test_python_dirs_cover_backend_and_python_frontend() -> None:
    stack = Stack(backend="data", frontend="streamlit", has_podman=False)

    assert stack.python_dirs == ("backend", "frontend")
    assert stack.pnpm_dir is None


def test_checks_end_with_charter() -> None:
    commands = Stack(backend="fastapi", frontend="next", has_podman=False).check_commands()

    assert [command.label for command in commands][-3:] == [
        "frontend lint",
        "frontend typecheck",
        "charte",
    ]


def test_java_backend_is_checked_by_the_maven_wrapper() -> None:
    stack = Stack(backend="java", frontend="aucun", has_podman=False)

    assert stack.python_dirs == ()
    assert stack.maven_dir == "backend"
    assert stack.dev_commands() == []
    assert [(command.label, command.argv) for command in stack.check_commands()] == [
        ("backend maven", ("./mvnw", "-B", "-q", "verify")),
        ("charte", ("charte",)),
    ]


def test_adopted_maven_backend_is_detected(tmp_path: Path) -> None:
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend/pom.xml").write_text("<project/>")

    assert load_stack(tmp_path).backend == "java"


def test_major_bounds_keep_the_major() -> None:
    assert _major_bounds(Version("6.1.2")) == ">=6.1.2,<7.0.0"
    assert _major_bounds(Version("0.25.1")) == ">=0.25.1,<0.26.0"


def test_team_accepts_a_comma_list() -> None:
    assert parse_assignments(["equipe=a, b", "podman=true"]) == {
        "equipe": ["a", "b"],
        "podman": True,
    }


def test_unknown_key_is_refused() -> None:
    with pytest.raises(KilnError):
        parse_assignments(["couleur=bleu"])


def test_rules_checked_by_charte_are_verified(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("- **[SIGNAUX]** a\n- **[NOMS-INTERDITS]** b\n")
    (tmp_path / "charte.toml").write_text('[interdictions.signaux-django]\nid = "SIGNAUX"\n')

    stack = Stack(backend="django", frontend="aucun", has_podman=False)
    unverified = set(charter_rules(tmp_path)) - verified_rules(tmp_path, stack)

    assert unverified == {"NOMS-INTERDITS"}


def test_legacy_template_source_is_replaced(tmp_path: Path) -> None:
    answers = tmp_path / ".copier-answers.yml"
    answers.write_text("_commit: abc\n_src_path: https://github.com/antoine-tena/init-repo.git\n")

    replace_legacy_source(tmp_path)

    assert "_src_path: https://github.com/antoine-tena/kiln.git" in answers.read_text()


def test_env_file_gets_a_local_secret_and_is_kept(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("DJANGO_SECRET_KEY=\nDJANGO_DEBUG=True\n")

    ensure_env_file(tmp_path)
    first = (tmp_path / ".env").read_text()
    ensure_env_file(tmp_path)

    assert first.startswith("DJANGO_SECRET_KEY=") and len(first.splitlines()[0]) > 30
    assert "DJANGO_DEBUG=True" in first
    assert (tmp_path / ".env").read_text() == first


def test_replaced_frontend_loses_its_lockfile(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend/pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")

    remove_replaced_artifacts(
        tmp_path,
        Stack(backend="data", frontend="nuxt", has_podman=False),
        Stack(backend="data", frontend="streamlit", has_podman=False),
    )

    assert not (tmp_path / "frontend/pnpm-lock.yaml").exists()


def test_adopted_repo_stack_comes_from_its_files(tmp_path: Path) -> None:
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "manage.py").touch()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "frontend" / "nuxt.config.ts").touch()
    assert load_stack(tmp_path) == Stack(backend="django", frontend="nuxt", has_podman=False)


def test_adopted_repo_declares_its_size_in_its_charter(tmp_path: Path) -> None:
    (tmp_path / "charte.toml").write_text('envergure = "flame"\nexclus = []\n')
    assert answers_if_any(tmp_path) == {"envergure": "flame"}
