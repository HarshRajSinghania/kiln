import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "plugins/base/hooks/garde-branche.py"


def run_hook(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    return subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "-b", "feat/x", str(tmp_path)], check=True)
    return tmp_path


@pytest.mark.parametrize(
    "message",
    ["Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", "Claude-Session: abc"],
)
def test_claude_signature_is_refused(repo: Path, message: str) -> None:
    result = run_hook(f'git commit -m "feat: x" -m "{message}"', repo)
    assert result.returncode == 2
    assert "Co-Authored-By" in result.stderr


def test_claude_signature_in_message_file_is_refused(repo: Path) -> None:
    (repo / "msg.txt").write_text("feat: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
    assert run_hook("git commit -F msg.txt", repo).returncode == 2


def test_plain_commit_on_feature_branch_passes(repo: Path) -> None:
    assert run_hook('git commit -m "feat: x"', repo).returncode == 0


def test_signature_outside_a_commit_passes(repo: Path) -> None:
    assert run_hook('echo "Co-Authored-By: Claude"', repo).returncode == 0


def test_commit_on_develop_is_refused(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "develop", str(tmp_path)], check=True)
    assert run_hook('git commit -m "feat: x"', tmp_path).returncode == 2
