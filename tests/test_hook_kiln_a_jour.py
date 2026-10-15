import importlib.util
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
    monkeypatch.setattr(module, "remote_head", lambda: "nouveau")
    return module


def test_answers_are_read_without_yaml() -> None:
    hook = load_hook()

    assert hook.answer(KILN_ANSWERS, "_commit") == "8e6427b"
    assert hook.answer(KILN_ANSWERS, "_src_path") == "https://github.com/antoine-tena/kiln.git"
    assert hook.answer(KILN_ANSWERS, "absent") == ""


def test_only_template_files_make_a_repo_late() -> None:
    hook = load_hook()

    assert hook.is_template_change(["template/CLAUDE.md.jinja", "README.md"])
    assert not hook.is_template_change(["src/kiln/cli.py", "plugins/base/hooks/hooks.json"])


def test_refusals_push_the_question_back_5_10_30_then_50_sessions(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    asked_at = []
    for session in range(1, 120):
        if hook.instructions(".", state, fetch=lambda commit: []):
            asked_at.append(session)
            hook.record(state, hook.TOOL_KEY, refused=True)

    assert asked_at == [1, 6, 16, 46, 96]


def test_after_four_refusals_uninstalling_is_offered(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    for _ in range(4):
        hook.record(state, hook.TOOL_KEY, refused=True)
    state[hook.TOOL_KEY]["prochaine"] = 0

    assert "Désinstaller kiln" in hook.instructions(".", state, fetch=lambda commit: [])


def test_repo_question_follows_a_tool_update(hook: ModuleType) -> None:
    message = hook.instructions(".", {}, fetch=lambda commit: ["copier.yml"])

    assert "L'outil kiln installé" in message
    assert "Une fois l'outil mis à jour avec succès" in message
    assert "kiln update" in message


def test_refused_tool_update_also_silences_the_repo(hook: ModuleType) -> None:
    state: dict[str, dict[str, int]] = {}
    hook.instructions(".", state, fetch=lambda commit: ["copier.yml"])
    hook.record(state, hook.TOOL_KEY, refused=True)

    assert hook.instructions(".", state, fetch=lambda commit: ["copier.yml"]) == ""


def test_up_to_date_tool_asks_only_for_the_repo(
    hook: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hook, "installed_kiln", lambda: ("git", "nouveau"))

    message = hook.instructions(".", {}, fetch=lambda commit: ["template/README.md.jinja"])

    assert message.startswith("Le modèle kiln a évolué depuis le commit 8e6427b")
    assert hook.instructions(".", {}, fetch=lambda commit: ["src/kiln/cli.py"]) == ""


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
