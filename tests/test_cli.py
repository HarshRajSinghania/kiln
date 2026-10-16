import sys
from pathlib import Path

import pytest

from kiln import cli, fleet, ui
from kiln.shell import KilnError


def run_kiln(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> int:
    """`kiln …` dans ce processus ; renvoie le code de sortie (0 sans sys.exit)."""
    monkeypatch.setattr(sys, "argv", ["kiln", *arguments])
    try:
        cli.main()
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    return 0


@pytest.mark.parametrize("arguments", [(), ("-h",), ("--help",)])
def test_home_screen_lists_every_command_by_section(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], arguments: tuple[str, ...]
) -> None:
    assert run_kiln(monkeypatch, *arguments) == 0

    out = capsys.readouterr().out
    for title, names in cli.COMMAND_GROUPS:
        assert title.upper() in out
        assert all(name in out for name in names)
    assert "EXEMPLES" in out


def test_every_command_of_the_home_screen_exists() -> None:
    parser = cli.build_parser()
    known = {
        choice
        for action in parser._actions
        if hasattr(action, "choices") and isinstance(action.choices, dict)
        for choice in action.choices
    }
    listed = {name.split()[0] for _, names in cli.COMMAND_GROUPS for name in names}

    assert listed == known


def test_outside_a_repository_the_error_is_explained(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    assert run_kiln(monkeypatch, "install") == cli.EXIT_FAILURE
    assert "n'est pas dans un repo" in capsys.readouterr().err


def test_a_failed_command_ends_on_an_interrupted_recap(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def failing_dispatch(arguments: object) -> None:
        ui.step("backend : dépendances Python")
        raise KilnError("échec de `uv sync`")

    ui._steps.clear()
    monkeypatch.setattr(cli, "dispatch", failing_dispatch)

    assert run_kiln(monkeypatch, "check") == cli.EXIT_FAILURE
    captured = capsys.readouterr()
    assert "Interrompu après" in captured.out
    assert "kiln : échec de `uv sync`" in captured.err
    ui._steps.clear()


def test_status_outside_a_terminal_is_plain_text(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    (tmp_path / "config/kiln").mkdir(parents=True)
    (tmp_path / "config/kiln/config.toml").write_text(f'dossier_code = "{tmp_path}"\n')
    monkeypatch.setattr(fleet, "latest_release", lambda: "v0.3.0")

    assert run_kiln(monkeypatch, "status") == 0
    out = capsys.readouterr().out
    assert "\033[" not in out
    assert out.splitlines()[0].startswith("kiln v")
    assert "REPO" in out
