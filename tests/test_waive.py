"""`kiln waive` : ajout et renouvellement d'une dérogation dans `kiln-waivers.toml`."""

import datetime
import subprocess
import tomllib
from pathlib import Path

import pytest

from kiln.shell import KilnError
from kiln.waive import WaiveRequest, waive

TODAY = datetime.date(2026, 10, 16)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "charte.toml").write_text('[cliquets.taille-fichier]\nid = "TAILLE-FICHIER"\n')
    (tmp_path / "ci.yml").write_text("a\n")
    return tmp_path


def entries(repo: Path) -> list[dict]:
    return tomllib.loads((repo / "kiln-waivers.toml").read_text())["waiver"]


def test_first_waiver_lasts_one_week(repo: Path) -> None:
    waive(repo, WaiveRequest("TAILLE-FICHIER", "repris tel quel"), TODAY)

    [entry] = entries(repo)
    assert entry["since"] == TODAY and entry["until"] == datetime.date(2026, 10, 23)
    assert entry["renewals"] == 0 and entry["reason"] == "repris tel quel"


def test_renewal_moves_to_the_next_tier_and_keeps_comments(repo: Path) -> None:
    waive(repo, WaiveRequest("TAILLE-FICHIER", "repris"), TODAY)
    (repo / "kiln-waivers.toml").write_text("# à moi\n" + (repo / "kiln-waivers.toml").read_text())
    later = TODAY + datetime.timedelta(days=7)

    waive(repo, WaiveRequest("TAILLE-FICHIER", "toujours repris", renew=True), later)

    [entry] = entries(repo)
    assert entry["renewals"] == 1 and entry["until"] == later + datetime.timedelta(days=30)
    assert (repo / "kiln-waivers.toml").read_text().startswith("# à moi\n")


def test_file_is_frozen(repo: Path) -> None:
    waive(repo, WaiveRequest("ci.yml", "hébergeur maison", permanent=True), TODAY)

    assert entries(repo) == [
        {
            "file": "ci.yml",
            "reason": "hébergeur maison",
            "by": entries(repo)[0]["by"],
            "since": TODAY,
            "until": "never",
            "renewals": 0,
        }
    ]


@pytest.mark.parametrize(
    ("request_", "message"),
    [
        (WaiveRequest("SECRETS", "pressé"), "ne se déroge pas"),
        (WaiveRequest("TAILLE-FICHIER", " "), "se justifie"),
        (WaiveRequest("TAILLE-FICHIER", "x", renew=True), "aucune dérogation à renouveler"),
        (WaiveRequest("INVENTEE", "x"), "règle inconnue"),
        (WaiveRequest("absent.yml", "x"), "aucun fichier"),
    ],
)
def test_refused_waiver_leaves_no_file(repo: Path, request_: WaiveRequest, message: str) -> None:
    with pytest.raises(KilnError, match=message):
        waive(repo, request_, TODAY)

    assert not (repo / "kiln-waivers.toml").exists()


def test_same_waiver_twice_is_refused(repo: Path) -> None:
    waive(repo, WaiveRequest("TAILLE-FICHIER", "x"), TODAY)

    with pytest.raises(KilnError, match="--renew"):
        waive(repo, WaiveRequest("TAILLE-FICHIER", "x"), TODAY)
