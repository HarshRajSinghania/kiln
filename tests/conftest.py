from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def git_identity(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests à l'abri de la config git du poste, avec une identité comme sur la CI de GitHub
    qui n'en a pas : sinon un test qui passe ici échoue là-bas."""
    config = Path(tmp_path_factory.mktemp("git")) / "gitconfig"
    config.write_text("[user]\n\tname = Test\n\temail = test@example.com\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
