"""`kiln ci` : lecture du ci.yml, plans des jobs, exécution et verdict en note git."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from kiln.ci import execution
from kiln.ci.execution import Workspace, run_job
from kiln.ci.jobs import BACK_LANE, DEFAULTS, plan_job
from kiln.ci.verdict import (
    FAILURE_LINE,
    SUCCESS_LINE,
    JobOutcome,
    Verdict,
    read_verdict,
    record_verdict,
)
from kiln.ci.workflow import INLINE_KIND, Job, load_jobs

WORKFLOWS = Path(__file__).parent.parent / ".github" / "workflows"
PROJECT_CI = """
on: push
jobs:
  backend-quality:
    uses: antoine-tena/kiln/.github/workflows/django.yml@main
    with:
      base: annski
      postgres: docker.io/library/postgres:18-alpine
      mypy: false
      env: |
        DEBUG=True
        IDEMPOTENCY_REQUIRED=True
  infra:
    uses: antoine-tena/kiln/.github/workflows/infra.yml@main
  end-to-end:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres
    steps:
      - run: pnpm test:e2e
  versions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: python3 scripts/ci/check_versions.py
"""


@pytest.fixture(autouse=True)
def git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """`git notes` exige une identité, absente des runners de CI."""
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "kiln")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "kiln@example.invalid")


def _git(directory: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments], cwd=directory, capture_output=True, text=True, check=True
    ).stdout.strip()


def _project(tmp_path: Path) -> Path:
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(PROJECT_CI)
    return tmp_path


@pytest.mark.parametrize("kind", sorted(DEFAULTS))
def test_defaults_match_the_reusable_workflow(kind: str) -> None:
    workflow = yaml.safe_load((WORKFLOWS / f"{kind}.yml").read_text())
    trigger = workflow.get("on", workflow.get(True))  # PyYAML lit la clé `on` comme un booléen
    declared = (trigger["workflow_call"] or {}).get("inputs") or {}
    defaults = {name: str(spec.get("default", "")) for name, spec in declared.items()}
    defaults = {name: value.lower() if value in {"True", "False"} else value
                for name, value in defaults.items()}  # fmt: skip
    assert DEFAULTS[kind] == defaults


def test_jobs_are_sorted_into_replayed_and_skipped(tmp_path: Path) -> None:
    jobs = {job.name: job for job in load_jobs(_project(tmp_path))}
    assert jobs["backend-quality"].is_replayable
    assert jobs["backend-quality"].inputs["mypy"] == "false"
    assert "infra" in jobs["infra"].reason
    assert jobs["end-to-end"].reason == "services propres au job"
    assert jobs["versions"].kind == INLINE_KIND
    assert jobs["versions"].commands == ("python3 scripts/ci/check_versions.py",)


def test_django_plan_keeps_the_project_inputs(tmp_path: Path) -> None:
    job = next(job for job in load_jobs(_project(tmp_path)) if job.name == "backend-quality")
    plan = plan_job(job)
    labels = [step.label for step in plan.steps]
    assert labels == ["ruff", "aucune migration manquante", "pytest", "planchers de couverture"]
    assert plan.lane == BACK_LANE
    assert plan.env == {"DEBUG": "True", "IDEMPOTENCY_REQUIRED": "True"}
    assert plan.services is not None
    assert plan.services.postgres == "docker.io/library/postgres:18-alpine"
    assert plan.services.redis == DEFAULTS["django"]["redis"]


def test_a_job_stops_at_its_first_failed_step(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path, tmp_path, "kiln-ci-test")
    job = Job("demo", INLINE_KIND, commands=("true", "false", "touch reached"))
    outcome = run_job(plan_job(job), workspace)
    assert outcome == JobOutcome("demo", is_success=False, failed_step="étape 1")
    assert not (tmp_path / "reached").exists()
    assert "$ false" in (tmp_path / "demo.log").read_text()


def test_verdict_goes_to_origin_and_comes_back(tmp_path: Path) -> None:
    origin, clone, other = tmp_path / "origin.git", tmp_path / "clone", tmp_path / "other"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    _git(clone, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
         "-m", "init")  # fmt: skip
    _git(clone, "push", "-q", "origin", "HEAD")
    sha = _git(clone, "rev-parse", "HEAD")
    outcomes = (JobOutcome("charter", is_success=True),)
    verdict = Verdict(sha, outcomes, (("infra", "pas rejoué"),), datetime.now().astimezone(), 75)
    record_verdict(clone, verdict, should_push=True)
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    note = read_verdict(other, sha)
    assert note is not None
    assert note.splitlines()[0] == SUCCESS_LINE
    assert "durée : 1 min 15 s" in note
    assert "non rejoués : infra (pas rejoué)" in note


def test_a_failed_job_makes_the_verdict_fail() -> None:
    outcomes = (JobOutcome("a", is_success=True), JobOutcome("b", False, "pytest"))
    verdict = Verdict("0" * 40, outcomes, (), datetime.now().astimezone(), 1)
    assert verdict.render().splitlines()[0] == FAILURE_LINE
    assert "b ÉCHEC (pytest)" in verdict.render()


def _ci_green(repo: Path, fake_bin: Path, sha: str) -> subprocess.CompletedProcess[str]:
    script = next(Path(__file__).parent.parent.glob("template/*/ops/lib/ci-verte.sh"))
    return subprocess.run(
        ["bash", "-c", '. "$1"; ci_verte "$2"', "ci-verte", str(script), sha],
        cwd=repo,
        env={"PATH": f"{fake_bin}:/usr/bin:/bin", "HOME": str(repo)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_deploy_gate_accepts_a_kiln_ci_success_only(tmp_path: Path) -> None:
    origin, clone = tmp_path / "origin.git", tmp_path / "clone"
    _git(tmp_path, "init", "-q", "--bare", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    _git(clone, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
         "-m", "init")  # fmt: skip
    sha = _git(clone, "rev-parse", "HEAD")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "gh").write_text("#!/bin/sh\necho '[]'\n")
    (fake_bin / "gh").chmod(0o755)
    refused = _ci_green(clone, fake_bin, sha)
    assert refused.returncode == 1
    assert "kiln ci « jamais rejoué »" in refused.stderr
    failed = Verdict(sha, (JobOutcome("a", False, "pytest"),), (), datetime.now().astimezone(), 1)
    record_verdict(clone, failed, should_push=False)
    assert _ci_green(clone, fake_bin, sha).returncode == 1
    passed = Verdict(sha, (JobOutcome("a", is_success=True),), (), datetime.now().astimezone(), 1)
    record_verdict(clone, passed, should_push=True)
    accepted = _ci_green(clone, fake_bin, sha)
    assert accepted.returncode == 0, accepted.stderr
    assert "CI rejouée par kiln ci, verte" in accepted.stdout


@pytest.mark.skipif(shutil.which("wslpath") is None, reason="WSL seulement")
def test_wsl_chrome_launcher_translates_the_windows_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_chrome = tmp_path / "chrome"
    fake_chrome.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@"\n')
    fake_chrome.chmod(0o755)
    monkeypatch.setattr(execution, "WSL_CHROME", tmp_path / "chrome-wsl")

    launcher = execution.wsl_chrome_launcher(str(fake_chrome))
    printed = subprocess.run(
        [launcher, "--headless", "--user-data-dir=C:\\Users\\a\\AppData\\Local\\lighthouse.1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    assert printed[0] == "--headless"
    assert printed[1].startswith("--user-data-dir=/")
