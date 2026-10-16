"""Déploiement sur un serveur à soi (`deploiement=vps`) : config/vps, scripts/ops et la doc."""

import json
import subprocess
from pathlib import Path

import copier
import pytest
import yaml
from test_modele import generate

VPS_ANSWERS = {
    "podman": True,
    "deploiement": "vps",
    "vps_hote": "root@203.0.113.7",
    "domaine_api": "api.demo.fr",
    "url_site": "https://www.demo.fr",
}
SERVER_SCRIPTS = ("deploy-remote", "backup", "restore-test", "heal", "setup-deploy-user")


def test_vps_brings_server_files_scripts_and_docs(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", **VPS_ANSWERS)

    descriptor = json.loads((project_dir / "config/vps/project.json").read_text())
    assert descriptor == {
        "host": "root@203.0.113.7",
        "remotePath": "/opt/demo",
        "branch": "develop",
        "apiUrl": "https://api.demo.fr",
        "siteUrl": "https://www.demo.fr",
    }
    compose = yaml.safe_load((project_dir / "config/vps/compose.yaml").read_text())
    assert set(compose["services"]) == {"db", "backend"}
    assert compose["services"]["backend"]["read_only"] is True
    assert "api.demo.fr {" in (project_dir / "config/vps/Caddyfile").read_text()
    for unit in ("backup", "restore-test", "heal"):
        assert (project_dir / f"config/vps/demo-{unit}.timer").is_file()
        service = (project_dir / f"config/vps/demo-{unit}.service").read_text()
        assert f"ExecStart=/usr/local/sbin/demo-{unit}" in service
    assert (project_dir / "docs/exploitation/production.md").is_file()


@pytest.mark.parametrize(
    "script",
    [f"config/vps/{name}.sh" for name in SERVER_SCRIPTS]
    + ["scripts/ops/deploy-backend.sh", "scripts/ops/smoke-test.sh"],
)
def test_vps_scripts_are_valid_executable_bash(tmp_path: Path, script: str) -> None:
    path = generate(tmp_path / "demo", **VPS_ANSWERS) / script

    assert path.stat().st_mode & 0o100
    # Les formats de podman ({{.Names}}) survivent au rendu du modèle.
    assert "{%" not in path.read_text()
    subprocess.run(["bash", "-n", str(path)], check=True)


def test_podman_formats_survive_rendering(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", **VPS_ANSWERS)

    assert "--format '{{.Names}}'" in (project_dir / "config/vps/heal.sh").read_text()


def test_no_vps_files_without_deployment(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", podman=True)

    assert not (project_dir / "config").exists()
    assert not (project_dir / "scripts/ops").exists()
    assert not (project_dir / "docs/exploitation").exists()


def test_vps_requires_podman(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="podman"):
        copier.run_copy(
            str(Path(__file__).resolve().parent.parent),
            tmp_path / "demo",
            data={**VPS_ANSWERS, "podman": False, "nom": "demo"},
            defaults=True,
            vcs_ref="HEAD",
            quiet=True,
        )


def test_backend_image_serves_gunicorn_without_migrating(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", podman=True)

    containerfile = (project_dir / "backend/Containerfile").read_text()
    assert '"gunicorn", "config.wsgi"' in containerfile
    assert "collectstatic" in containerfile
    command = yaml.safe_load((project_dir / "compose.yaml").read_text())["services"]["backend"]
    assert "runserver" in command["command"][-1]


def test_vercel_brings_only_the_front_deployment(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", front_deploiement="vercel")

    ops = project_dir / "scripts/ops"
    assert sorted(path.name for path in ops.rglob("*.sh")) == ["ci-verte.sh", "deploy-frontend.sh"]
    script = ops / "deploy-frontend.sh"
    assert script.stat().st_mode & 0o111
    subprocess.run(["bash", "-n", str(script)], check=True)
    assert not (project_dir / "config/vps").exists()
