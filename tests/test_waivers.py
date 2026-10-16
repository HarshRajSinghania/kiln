"""Dérogations de `kiln-waivers.toml` : paliers, échéance, cibles, effet sur la charte."""

import datetime
import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from kiln.charte.charte import verifier
from kiln.charte.moteur import Depot
from kiln.charte.waivers import load

TODAY = datetime.date(2026, 10, 16)
CHARTE = """
[cliquets.taille-fichier]
id = "TAILLE-FICHIER"
fichiers = ["src/*.py"]
suffixes = [".py"]
max_lignes = 3
budget = 0
"""


def waiver(**fields: object) -> str:
    """Une entrée `[[waiver]]` ; un champ à None est omis."""
    entry = {
        "rule": "TAILLE-FICHIER",
        "reason": "repris tel quel",
        "by": "antoine",
        "since": datetime.date(2026, 10, 14),
        "until": datetime.date(2026, 10, 20),
    } | fields
    lines = [f"{k} = {_toml(v)}" for k, v in entry.items() if v is not None]
    return "[[waiver]]\n" + "\n".join(lines) + "\n"


def _toml(value: object) -> str:
    return value.isoformat() if isinstance(value, datetime.date) else json.dumps(value)


def write(root: Path, *waivers: str) -> None:
    (root / "kiln-waivers.toml").write_text("\n".join(waivers))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "charte.toml").write_text(CHARTE)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "long.py").write_text("a = 1\n" * 5)
    (tmp_path / "src" / "court.py").write_text("a = 1\n")
    return tmp_path


def test_first_period_is_one_week(tmp_path: Path) -> None:
    write(tmp_path, waiver(until=datetime.date(2026, 10, 30)))

    waivers = load(tmp_path, TODAY)

    assert not waivers.actives and "au plus 7" in waivers.errors[0]


def test_each_renewal_lengthens_the_period(tmp_path: Path) -> None:
    write(
        tmp_path,
        waiver(since=datetime.date(2026, 10, 16), until=datetime.date(2026, 11, 15), renewals=1),
        waiver(since=datetime.date(2026, 10, 16), until=datetime.date(2027, 1, 14), renewals=2),
        waiver(since=datetime.date(2026, 10, 16), until=datetime.date(2027, 4, 16), renewals=7),
    )

    assert len(load(tmp_path, TODAY).actives) == 3


def test_expired_waiver_no_longer_applies(tmp_path: Path) -> None:
    write(tmp_path, waiver(since=datetime.date(2026, 10, 1), until=datetime.date(2026, 10, 8)))

    waivers = load(tmp_path, TODAY)

    assert not waivers.actives and "échue" in waivers.errors[0]


def test_warns_in_the_second_half_of_the_period(tmp_path: Path) -> None:
    write(tmp_path, waiver(since=datetime.date(2026, 10, 12), until=datetime.date(2026, 10, 18)))

    waivers = load(tmp_path, TODAY)

    assert waivers.actives and "dans 2 jour(s)" in waivers.warnings[0]


def test_permanent_waiver_is_always_shown(tmp_path: Path) -> None:
    write(tmp_path, waiver(until="never"))

    waivers = load(tmp_path, TODAY)

    assert waivers.actives[0].until is None and "permanente" in waivers.warnings[0]


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"rule": "DONNEES-PERSO"}, "ne se déroge pas"),
        ({"reason": None}, "`reason` manquant"),
        ({"file": "ci.yml"}, "une seule"),
        ({"motif": "x"}, "clé inconnue"),
    ],
)
def test_malformed_waiver_is_refused(tmp_path: Path, fields: dict, message: str) -> None:
    write(tmp_path, waiver(**fields))

    assert message in load(tmp_path, TODAY).errors[0]


def test_waiver_excludes_its_paths_from_the_rule(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    today = datetime.date.today()
    write(repo, waiver(paths=["src/long.py"], since=today, until=today))

    assert verifier(Depot(repo, _config(repo))) == 0
    assert "TAILLE-FICHIER (src/long.py)" in capsys.readouterr().out


def test_without_waiver_the_rule_fails(repo: Path) -> None:
    assert verifier(Depot(repo, _config(repo))) == 1


def test_waiver_matching_nothing_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    today = datetime.date.today()
    write(repo, waiver(paths=["src/disparu.py"], since=today, until=today))

    assert verifier(Depot(repo, _config(repo))) == 1
    assert "aucun fichier pour src/disparu.py" in capsys.readouterr().out


def test_waiver_of_an_unknown_rule_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    today = datetime.date.today()
    write(repo, waiver(rule="INVENTEE", since=today, until=today))

    assert verifier(Depot(repo, _config(repo))) == 1
    assert "règle inconnue" in capsys.readouterr().out


def _config(repo: Path) -> dict:
    return tomllib.loads((repo / "charte.toml").read_text())
