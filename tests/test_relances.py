import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

MODULE_PATH = Path(__file__).resolve().parent.parent / "plugins/base/hooks/relances.py"


@pytest.fixture
def relances() -> ModuleType:
    spec = importlib.util.spec_from_file_location("relances", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sessions_until_asked(relances: ModuleType, state: dict[str, Any], key: str) -> int:
    """Sessions dans un nouveau repo avant que l'adoption y soit proposée."""
    for session in range(1, 1000):
        relances.count_station_session(state)
        relances.count_session(state, "adoption", key)
        if relances.is_due(state, "adoption", key):
            relances.mark_asked(state, "adoption")
            return session
    raise AssertionError("jamais proposée")


def test_saying_yes_brings_the_next_proposal_sooner(relances: ModuleType) -> None:
    neutral: dict[str, Any] = {}
    sessions_until_asked(relances, neutral, "/a")
    relances.record(neutral, "adoption", "/a", "non")
    willing: dict[str, Any] = {}
    sessions_until_asked(relances, willing, "/a")
    relances.record(willing, "adoption", "/a", "oui")

    assert sessions_until_asked(relances, willing, "/b") < sessions_until_asked(
        relances, neutral, "/b"
    )


def test_adoption_is_spaced_across_repos(relances: ModuleType) -> None:
    state: dict[str, Any] = {}
    assert sessions_until_asked(relances, state, "/a") == 3

    # Déjà au-delà de ses 3 sessions, /b attend la fin de l'espacement du poste.
    for _ in range(3):
        relances.count_session(state, "adoption", "/b")
    assert not relances.is_due(state, "adoption", "/b")


def test_never_closes_the_question_and_weighs_twice(relances: ModuleType) -> None:
    state: dict[str, Any] = {}
    relances.record(state, "adoption", "/a", "jamais")
    for _ in range(10_000):
        relances.count_station_session(state)
        relances.count_session(state, "adoption", "/a")

    assert not relances.is_due(state, "adoption", "/a")
    assert state["bienveillance"] == pytest.approx(0.5 - 2 * 0.15)


def test_goodwill_stays_between_zero_and_one(relances: ModuleType) -> None:
    state: dict[str, Any] = {}
    for _ in range(20):
        relances.record(state, "adoption", "/a", "oui")
    assert state["bienveillance"] == 1.0
    for _ in range(40):
        relances.record(state, "adoption", "/a", "non")
    assert state["bienveillance"] == 0.0


def test_agreeing_resets_the_reminders(relances: ModuleType) -> None:
    state: dict[str, Any] = {}
    relances.record(state, "maj", "outil", "non")
    relances.record(state, "maj", "outil", "oui")

    assert state["questions"]["maj:outil"]["refus"] == 0
    assert state["questions"]["maj:outil"]["prochaine"] == 0


def test_the_former_state_keeps_its_reminders(relances: ModuleType) -> None:
    former = {"outil": {"sessions": 12, "refus": 2, "prochaine": 20}}

    state = relances.migrate(former)

    assert state["questions"]["maj:outil"] == former["outil"]
    assert state["bienveillance"] == 0.5


def test_answers_are_recorded_from_the_command_line(
    relances: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(relances, "STATE_PATH", tmp_path / "rappels.json")

    relances.main(["non", "maj", "/home/n/repo"])

    assert relances.load()["questions"]["maj:/home/n/repo"]["refus"] == 1
    with pytest.raises(SystemExit):
        relances.main(["peut-être", "maj", "outil"])
