import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HOOK_PATH = Path(__file__).resolve().parent.parent / "plugins/base/hooks/kiln-a-jour.py"


def load_hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("kiln_a_jour", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_answers_are_read_without_yaml() -> None:
    hook = load_hook()
    answers = "_commit: 8e6427b\n_src_path: https://github.com/antoine-tena/kiln.git\n"

    assert hook.answer(answers, "_commit") == "8e6427b"
    assert hook.answer(answers, "_src_path") == "https://github.com/antoine-tena/kiln.git"
    assert hook.answer(answers, "absent") == ""


def test_only_template_files_make_a_repo_late() -> None:
    hook = load_hook()

    assert hook.is_template_change(["template/CLAUDE.md.jinja", "README.md"])
    assert not hook.is_template_change(["src/kiln/cli.py", "plugins/base/hooks/hooks.json"])


def test_answer_is_cached_for_a_day(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hook = load_hook()
    monkeypatch.setattr(hook, "CACHE_DIR", tmp_path)
    calls: list[str] = []

    def fetch(commit: str) -> list[str]:
        calls.append(commit)
        return ["copier.yml"]

    assert hook.is_late(Path("/repo"), "abc1234", fetch=fetch, now=lambda: 1000.0)
    assert hook.is_late(Path("/repo"), "abc1234", fetch=fetch, now=lambda: 2000.0)
    assert calls == ["abc1234"]
    assert hook.is_late(Path("/repo"), "abc1234", fetch=fetch, now=lambda: 1000.0 + 86400)
    assert calls == ["abc1234", "abc1234"]
