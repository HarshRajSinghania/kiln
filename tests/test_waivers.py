"""Dérogations de `kiln-waivers.toml` : paliers, échéance, cibles, effet sur la charte, fichiers
figés laissés tels quels par `kiln update`."""

import datetime
import json
import subprocess
import tomllib
from pathlib import Path

import copier
import pytest

from kiln.charte.charte import verifier
from kiln.charte.moteur import Depot
from kiln.charte.waivers import load
from kiln.frozen import report_frozen_drift
from kiln.update import apply_template, template_commit

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


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def template_version(template: Path, tag: str, ci: str) -> None:
    (template / "ci.yml").write_text(ci)
    (template / "autre.txt").write_text(f"{tag}\n")
    git(template, "add", "-A")
    git(template, "commit", "-qm", tag)
    git(template, "tag", tag)


@pytest.fixture
def generated(tmp_path: Path) -> Path:
    """Un repo généré à la v1 d'un petit modèle, `ci.yml` modifié et figé ; le modèle est en v2."""
    template, project = tmp_path / "modele", tmp_path / "projet"
    template.mkdir()
    git(template, "init", "-q")
    (template / "copier.yml").write_text("_answers_file: .copier-answers.yml\n")
    (template / "{{_copier_conf.answers_file}}.jinja").write_text(
        "{{ _copier_answers | to_nice_yaml }}"
    )
    template_version(template, "v1", "a\nb\n")
    copier.run_copy(str(template), project, vcs_ref="v1", defaults=True, quiet=True)
    (project / "ci.yml").write_text("a\nlocal\n")
    today = datetime.date.today()
    write(project, waiver(rule=None, file="ci.yml", since=today, until=today))
    git(project, "init", "-q")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "init")
    template_version(template, "v2", "a\nb2\n")
    return project


def test_update_leaves_frozen_files_alone(generated: Path) -> None:
    apply_template(generated)

    assert (generated / "ci.yml").read_text() == "a\nlocal\n"
    assert (generated / "autre.txt").read_text() == "v2\n"


def test_update_reports_what_kiln_changed_in_frozen_files(
    generated: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    template = str(generated.parent / "modele")
    apply_template(generated)

    report_frozen_drift(generated, template, "v1", template_commit(generated))

    out = capsys.readouterr().out
    assert "ci.yml" in out and "-b\n+b2" in out
