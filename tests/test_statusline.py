"""Status line : le choix du poste (`kiln set statusline=…`) et le script du plugin `base`."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from kiln.config import UserConfig
from kiln.poste import apply_poste
from kiln.shell import KilnError
from kiln.statusline import apply_statusline_choice, is_kiln_statusline

SCRIPT = Path(__file__).parent.parent / "plugins" / "base" / "scripts" / "statusline.py"
OWN = {"type": "command", "command": "~/bin/ma-ligne.sh"}
X = "\u00d7"  # signe de multiplication des compteurs


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("statusline_script", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un poste avec le catalogue kiln déclaré là où Claude Code le range."""
    monkeypatch.setenv("HOME", str(tmp_path))
    kiln = tmp_path / "kiln"
    (kiln / "plugins" / "base" / "scripts").mkdir(parents=True)
    (kiln / "plugins" / "base" / "scripts" / "statusline.py").write_text("")
    plugins = tmp_path / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "known_marketplaces.json").write_text(
        json.dumps({"kiln": {"installLocation": str(kiln)}})
    )
    return tmp_path


def settings(home: Path) -> dict:
    return json.loads((home / ".claude" / "settings.json").read_text())


def test_statusline_choice_is_checked() -> None:
    assert apply_poste(UserConfig(), ["statusline=bandeau"]).statusline == "bandeau"
    with pytest.raises(KilnError, match="statusline"):
        apply_poste(UserConfig(), ["statusline=arc-en-ciel"])


def test_a_kiln_style_installs_the_script_and_keeps_other_settings(home: Path) -> None:
    (home / ".claude" / "settings.json").write_text(json.dumps({"model": "opus"}))

    apply_statusline_choice("sobre")

    assert settings(home)["model"] == "opus"
    assert is_kiln_statusline(settings(home)["statusLine"])


def test_perso_never_touches_the_users_own_statusline(home: Path) -> None:
    (home / ".claude" / "settings.json").write_text(json.dumps({"statusLine": OWN}))

    apply_statusline_choice("perso")

    assert settings(home)["statusLine"] == OWN


def test_aucune_removes_the_statusline(home: Path) -> None:
    apply_statusline_choice("classique")
    apply_statusline_choice("aucune")

    assert "statusLine" not in settings(home)


def test_switching_styles_keeps_the_kiln_command(home: Path) -> None:
    (home / ".claude" / "settings.json").write_text(
        json.dumps(
            {"statusLine": {"command": 'python3 "$HOME/kiln/plugins/base/scripts/statusline.py"'}}
        )
    )

    apply_statusline_choice("bandeau")

    assert "$HOME" in settings(home)["statusLine"]["command"]  # écrite à la main, gardée


def test_secret_scan_ignores_rendered_examples(tmp_path: Path) -> None:
    script = load_script()
    for name in ("template/.env.example.jinja", ".env.sample", "backend/.env", ".stripe/token"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-f", "."], cwd=tmp_path, check=True)

    assert sorted(script.tracked_secrets(str(tmp_path))) == [".stripe/token", "backend/.env"]


def test_integration_branch_is_not_counted_as_unmerged(tmp_path: Path) -> None:
    script = load_script()
    remote, clone = tmp_path / "remote", tmp_path / "clone"
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", "-b", "develop", str(remote)], check=True)
    subprocess.run(
        [*git, "-C", str(remote), "commit", "-q", "--allow-empty", "-m", "a"], check=True
    )
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True)
    subprocess.run([*git, "-C", str(clone), "commit", "-q", "--allow-empty", "-m", "b"], check=True)
    subprocess.run(["git", "-C", str(clone), "branch", "feat/x"], check=True)

    assert script.unmerged_branches(str(clone), "develop") == 1  # feat/x, pas develop


def sample(script: ModuleType) -> object:
    item, status = script.Item, script.Status()
    status.repo = [[item("annski", role="title"), item("⎇ develop")], [item("~2", 1)]]
    status.session = [[item("Opus", role="strong")], [item("ctx", 0, gauge=34.0)]]
    status.tasks = [[item("65 tasks"), item(f"urgent{X}10", 3), item(f"blocked{X}14", short="")]]
    status.env = [
        [item(f"uv{X}8")],
        [item("prod"), item("django ↓153", 2, "↓153")],
        [item(":3000 :8000")],
    ]
    return status


@pytest.mark.parametrize("style", ["sobre", "bandeau", "classique", "classique-fond"])
@pytest.mark.parametrize("columns", [60, 90, 140])
def test_no_line_overflows(style: str, columns: int) -> None:
    script = load_script()

    lines = script.render(sample(script), style, columns)

    assert all(script.visible_width(line) <= columns for line in lines)


def test_signals_put_tasks_first_and_drop_grey_before_compacting_colour() -> None:
    script = load_script()

    signals = script.render(sample(script), "sobre", 40)[2]
    plain = script.re.sub(r"\033\[[0-9;]*m", "", signals)

    assert plain.startswith(f"65 tasks urgent{X}10")  # le total reste devant ses sous-comptes
    assert "django ↓153" in plain or "↓153" in plain
    assert f"uv{X}8" not in plain  # le gris tombe en premier
