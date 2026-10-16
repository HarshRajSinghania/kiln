import importlib.util
import subprocess
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

HOOK_PATH = Path(__file__).resolve().parent.parent / "plugins/base/hooks/kiln-a-jour.py"
KILN_ANSWERS = "_commit: 8e6427b\n_src_path: https://github.com/antoine-tena/kiln.git\n"


def load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("kiln_a_jour", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Le hook sur un repo kiln fictif, sans réseau ni outil installé réels."""
    module = load_hook()
    monkeypatch.setattr(module, "kiln_repo", lambda cwd: (tmp_path / "annway", "8e6427b"))
    monkeypatch.setattr(module, "installed_kiln", lambda: ("git", "ancien"))
    return module


def released(tag: str = "v0.4.0", commit: str = "nouveau") -> Callable[[], tuple[str, str]]:
    return lambda: (tag, commit)


def test_answers_are_read_without_yaml() -> None:
    hook = load_hook()

    assert hook.answer(KILN_ANSWERS, "_commit") == "8e6427b"
    assert hook.answer(KILN_ANSWERS, "_src_path") == "https://github.com/antoine-tena/kiln.git"
    assert hook.answer(KILN_ANSWERS, "absent") == ""


def test_releases_order_by_number_not_by_text() -> None:
    hook = load_hook()

    assert hook.release_key("v0.10.0") > hook.release_key("v0.9.3")
    assert hook.release_key("v0.4.0") > hook.release_key("v0.4.0-rc.3")
    assert hook.release_key("v0.4.0-2-gabc1234") == (0, 4, 0, hook.FINAL)
    assert hook.release_key("8e6427b") is None
    assert hook.is_repo_late("8e6427b", "v0.3.0")
    assert hook.is_repo_late("v0.4.0-rc.1", "v0.4.0")
    assert not hook.is_repo_late("v0.4.0", "v0.4.0")


def test_refusals_push_the_question_back_5_10_30_then_50_sessions(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    asked_at = []
    for session in range(1, 120):
        if hook.instructions(".", state, release=released()):
            asked_at.append(session)
            hook.record(state, hook.TOOL_KEY, refused=True)

    assert asked_at == [1, 6, 16, 46, 96]


def test_after_four_refusals_uninstalling_is_offered(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    for _ in range(4):
        hook.record(state, hook.TOOL_KEY, refused=True)
    state[hook.TOOL_KEY]["prochaine"] = 0

    assert "Désinstaller kiln" in hook.instructions(".", state, release=released())


def test_repo_question_follows_a_tool_update(hook: ModuleType) -> None:
    message = hook.instructions(".", {}, release=released())

    assert "L'outil kiln installé" in message
    assert "Une fois l'outil mis à jour avec succès" in message
    assert "`base:maj-kiln` avec l'argument `outil`" in message
    assert "`base:maj-kiln` avec l'argument `depot`" in message


def test_refused_tool_update_also_silences_the_repo(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    hook.instructions(".", state, release=released())
    hook.record(state, hook.TOOL_KEY, refused=True)

    assert hook.instructions(".", state, release=released()) == ""


def test_up_to_date_tool_asks_only_for_the_repo(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook, "installed_kiln", lambda: ("git", "nouveau"))

    message = hook.instructions(".", {}, release=released())

    assert message.startswith("kiln v0.4.0 est sortie ; annway part de 8e6427b")
    monkeypatch.setattr(hook, "kiln_repo", lambda cwd: (Path("annway"), "v0.4.0"))
    assert hook.instructions(".", {}, release=released()) == ""


def test_no_release_means_no_question(hook: ModuleType) -> None:
    assert hook.instructions(".", {}, release=lambda: None) == ""


def test_agreeing_resets_the_reminders(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    hook.record(state, hook.TOOL_KEY, refused=True)
    hook.record(state, hook.TOOL_KEY, refused=False)

    assert state[hook.TOOL_KEY]["refus"] == 0
    assert state[hook.TOOL_KEY]["prochaine"] == 0


def test_plugin_link_follows_the_installed_plugin(tmp_path: Path) -> None:
    hook = load_hook()
    old_plugin, new_plugin = tmp_path / "base-0.6.0", tmp_path / "base-0.7.0"
    old_plugin.mkdir()
    new_plugin.mkdir()
    root = tmp_path / "annway"
    root.mkdir()

    hook.link_plugin(root, old_plugin)
    hook.link_plugin(root, new_plugin)

    assert (root / ".claude/kiln").resolve() == new_plugin


def test_a_real_folder_is_never_replaced_by_the_link(tmp_path: Path) -> None:
    hook = load_hook()
    (tmp_path / "annway/.claude/kiln").mkdir(parents=True)

    hook.link_plugin(tmp_path / "annway", tmp_path)

    assert not (tmp_path / "annway/.claude/kiln").is_symlink()


def test_link_is_ignored_even_outside_kiln_repos(tmp_path: Path) -> None:
    hook = load_hook()
    root = tmp_path / "autre-repo"
    subprocess.run(["git", "init", "-q", str(root)], check=True)

    hook.link_plugin(root, tmp_path)
    hook.link_plugin(root, tmp_path)

    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True
    )
    assert (root / ".claude/kiln").is_symlink()
    assert status.stdout == ""
    assert (root / ".git/info/exclude").read_text().count(".claude/kiln") == 1


def fake_tool(tool_dir: Path, name: str, dist_info: str, direct_url: str | None) -> None:
    metadata = tool_dir / name / "lib/python3.14/site-packages" / dist_info
    metadata.mkdir(parents=True)
    (metadata / "METADATA").write_text("Metadata-Version: 2.4\nName: kiln-cli\nVersion: 0.4.0\n")
    if direct_url is not None:
        (metadata / "direct_url.json").write_text(direct_url)


def uv_tool_dir(module: ModuleType, tool_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def run(*command: str) -> subprocess.CompletedProcess[str]:
        assert command == ("uv", "tool", "dir")
        return subprocess.CompletedProcess(command, 0, stdout=f"{tool_dir}\n")

    monkeypatch.setattr(module, "run", run)


def test_a_pypi_install_is_read_from_its_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = load_hook()
    fake_tool(tmp_path, "kiln-cli", "kiln_cli-0.4.0.dist-info", None)
    uv_tool_dir(hook, tmp_path, monkeypatch)

    assert hook.installed_kiln() == ("pypi", "v0.4.0")
    assert not hook.has_legacy_tool()
    assert not hook.is_tool_outdated(("pypi", "v0.4.0"), "v0.4.0", "abc")
    assert hook.is_tool_outdated(("pypi", "v0.4.0"), "v0.4.1", "abc")


def test_the_old_kiln_tool_is_still_found_and_removed_on_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = load_hook()
    fake_tool(
        tmp_path, "kiln", "kiln-0.3.0.dist-info", '{"url": "x", "vcs_info": {"commit_id": "c0"}}'
    )
    uv_tool_dir(hook, tmp_path, monkeypatch)

    assert hook.installed_kiln() == ("git", "c0")
    command = hook.tool_update_command(("git", "c0"), "v0.4.0")
    assert command.startswith('uv tool uninstall kiln && uv tool install --force "git+')


def test_promoted_versions_come_from_pypi_and_candidates_from_github(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = load_hook()
    uv_tool_dir(hook, tmp_path, monkeypatch)

    assert hook.tool_update_command(("pypi", "v0.4.0"), "v0.4.1").startswith(
        'uv tool install --force "kiln-cli==0.4.1" && '
    )
    assert hook.tool_update_command(None, "v0.4.1").startswith('uv tool install --force "kiln-cli')
    assert '"git+https://github.com/antoine-tena/kiln@v0.5.0-rc.1"' in hook.tool_update_command(
        ("pypi", "v0.4.1"), "v0.5.0-rc.1"
    )
