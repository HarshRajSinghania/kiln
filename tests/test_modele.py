import json
import tomllib
from pathlib import Path

import copier
import pytest
import yaml

TEMPLATE_DIR = Path(__file__).resolve().parent.parent
ANSWERS = {
    "nom": "demo",
    "titre": "Démo",
    "description": "Projet de démonstration.",
    "proprietaire": "antoine-tena",
    "equipe": ["antoine-tena", "NathanBarrachin"],
}
BACKENDS = ("django", "fastapi", "data", "cli", "java", "aucun")
FRONTENDS = ("nuxt", "next", "astro", "streamlit", "dash", "aucun")
STACKS = [
    (back, front) for back in BACKENDS for front in FRONTENDS if (back, front) != ("aucun",) * 2
]
# Un outil en ligne de commande ou un backend Java seuls n'ont rien à conteneuriser : copier
# refuse podman.
PODMAN_STACKS = [stack for stack in STACKS if stack not in {("cli", "aucun"), ("java", "aucun")}]
JSON_FILES = (".vscode/settings.json", ".vscode/extensions.json", ".claude/settings.json")


def generate(destination: Path, **extra_answers: object) -> Path:
    copier.run_copy(
        str(TEMPLATE_DIR),
        destination,
        data={**ANSWERS, **extra_answers},
        defaults=True,
        vcs_ref="HEAD",
        quiet=True,
    )
    return destination


def test_default_stack_is_django_and_nuxt(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    assert (project_dir / "backend/config/api.py").is_file()
    assert (project_dir / "frontend/nuxt.config.ts").is_file()
    assert (
        (project_dir / ".github/CODEOWNERS")
        .read_text()
        .endswith("* @antoine-tena @NathanBarrachin\n")
    )


@pytest.mark.parametrize(("backend", "frontend"), STACKS)
def test_every_stack_renders_valid_files(tmp_path: Path, backend: str, frontend: str) -> None:
    project_dir = generate(tmp_path / "demo", backend=backend, frontend=frontend)

    rendered = [
        path for path in project_dir.rglob("*") if path.is_file() and ".git" not in path.parts
    ]
    assert not [path for path in rendered if path.suffix == ".jinja"]
    assert not [path for path in rendered if path.suffix != ".ico" and "{%" in path.read_text()]
    tomllib.loads((project_dir / "charte.toml").read_text())
    yaml.safe_load((project_dir / ".github/workflows/ci.yml").read_text())
    yaml.safe_load((project_dir / ".pre-commit-config.yaml").read_text())
    for name in JSON_FILES:
        json.loads((project_dir / name).read_text())
    assert (project_dir / "backend").is_dir() == (backend != "aucun")
    assert (project_dir / "frontend").is_dir() == (frontend != "aucun")


@pytest.mark.parametrize(("backend", "frontend"), PODMAN_STACKS)
def test_podman_adds_containers_for_every_stack(
    tmp_path: Path, backend: str, frontend: str
) -> None:
    project_dir = generate(tmp_path / "demo", backend=backend, frontend=frontend, podman=True)

    compose = yaml.safe_load((project_dir / "compose.yaml").read_text())
    for directory in ("backend", "frontend"):
        if (project_dir / directory / "Containerfile").is_file():
            containerfile = (project_dir / directory / "Containerfile").read_text()
            instructions = [line for line in containerfile.splitlines() if not line.startswith("#")]
            # Outil interdit : la règle [UV-PODMAN] est justement vérifiée ici.
            assert not [line for line in instructions if "pip install" in line or "docker " in line]
    assert compose["services"]


def test_stack_advice_follows_project_type(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", type_projet="tableau")

    answers = yaml.safe_load((project_dir / ".copier-answers.yml").read_text())
    assert (answers["backend"], answers["frontend"]) == ("data", "streamlit")


@pytest.mark.parametrize(("envergure", "has_podman"), [("ember", False), ("flame", True)])
def test_envergure_sets_podman_default(tmp_path: Path, envergure: str, has_podman: bool) -> None:
    project_dir = generate(tmp_path / "demo", envergure=envergure)

    answers = yaml.safe_load((project_dir / ".copier-answers.yml").read_text())
    assert (answers["envergure"], answers["podman"]) == (envergure, has_podman)
    assert f"**{envergure.capitalize()}**" in (project_dir / "CLAUDE.md").read_text()


def test_vue_templates_keep_their_mustaches(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    health_component = (project_dir / "frontend/app/components/HealthStatus.vue").read_text()
    assert "{{ health?.status }}" in health_component


def test_a_faire_is_always_there(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", boussole="la démo en ligne", backend="fastapi")

    a_faire = (project_dir / "docs/a-faire/a-faire.md").read_text()
    assert "La boussole est **la démo en ligne**." in a_faire
    assert "docs/a-faire/" in (project_dir / "CLAUDE.md").read_text()
    urgent = (project_dir / "docs/a-faire/urgent.md").read_text()
    # La status line compte les lignes qui commencent par une case ouverte : aucune au départ.
    assert not [line for line in urgent.splitlines() if line.lstrip().startswith("- [ ]")]


def test_django_and_nuxt_share_a_typed_api_contract(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    use_health = (project_dir / "frontend/app/composables/useHealth.ts").read_text()
    assert "useApi().get('/api/health'" in use_health
    assert (project_dir / "frontend/app/composables/useApi.ts").is_file()
    assert "openapi.json linguist-generated" in (project_dir / ".gitattributes").read_text()
    workflow = yaml.safe_load((project_dir / ".github/workflows/ci.yml").read_text())
    assert workflow["jobs"]["contrat"]["uses"].endswith("contrat-api.yml@develop")


def test_fastapi_front_keeps_its_plain_fetch(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", backend="fastapi")

    assert not (project_dir / "frontend/app/composables/useApi.ts").exists()
    assert "apiBase" in (project_dir / "frontend/nuxt.config.ts").read_text()


def test_data_stack_accepts_numeric_arrays_and_trained_models(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", backend="data", frontend="streamlit")

    rules = (project_dir / "backend/CLAUDE.md").read_text()
    assert "NumPy" in rules
    assert "`data/models/`" in rules
    attributes = (project_dir / ".gitattributes").read_text()
    assert "backend/data/models/** linguist-generated=true" in attributes


@pytest.mark.parametrize(("backend", "frontend"), [("django", "nuxt"), ("data", "streamlit")])
def test_readme_sections_start_on_their_own_line(
    tmp_path: Path, backend: str, frontend: str
) -> None:
    project_dir = generate(tmp_path / "demo", backend=backend, frontend=frontend)

    readme = (project_dir / "README.md").read_text()
    assert "\n\n## Suivi du travail\n" in readme
    assert all(line.startswith("## ") for line in readme.splitlines() if "## " in line)


def test_ci_runs_for_main_and_develop(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo")

    workflow = yaml.safe_load((project_dir / ".github/workflows/ci.yml").read_text())
    # PyYAML lit la clé `on` comme le booléen True.
    triggers = workflow[True]
    assert triggers["push"]["branches"] == ["main", "develop"]
    assert triggers["pull_request"]["branches"] == ["main", "develop"]


def test_tool_project_gets_a_command_line_package(tmp_path: Path) -> None:
    # Une description longue ne doit pas déborder dans le code (E501 au premier commit).
    long_description = "Un outil dont la description dépasse largement cent caractères. " * 3
    project_dir = generate(
        tmp_path / "demo", type_projet="outil", envergure="flame", description=long_description
    )

    answers = yaml.safe_load((project_dir / ".copier-answers.yml").read_text())
    assert (answers["backend"], answers["frontend"], answers["podman"]) == ("cli", "aucun", False)
    pyproject = tomllib.loads((project_dir / "backend/pyproject.toml").read_text())
    assert pyproject["project"]["scripts"] == {"demo": "demo.cli:main"}
    assert (project_dir / "backend/demo/cli.py").is_file()
    assert "[CLI-MINCE]" in (project_dir / "backend/CLAUDE.md").read_text()
    assert not (project_dir / "compose.yaml").exists()
    python_lines = [
        line
        for path in (project_dir / "backend").rglob("*.py")
        for line in path.read_text().splitlines()
    ]
    assert all(len(line) <= 100 for line in python_lines)


def test_java_backend_gets_a_maven_project(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", nom="demo-app", backend="java", frontend="aucun")

    backend_dir = project_dir / "backend"
    pom = (backend_dir / "pom.xml").read_text()
    assert "<artifactId>demo-app</artifactId>" in pom
    assert "<main.class>fr.demoapp.Main</main.class>" in pom
    assert (backend_dir / "src/main/java/fr/demoapp/Main.java").is_file()
    assert (backend_dir / "src/test/java/fr/demoapp/greeting/GreetingServiceTest.java").is_file()
    assert (backend_dir / "mvnw").stat().st_mode & 0o111
    wrapper = (backend_dir / ".mvn/wrapper/maven-wrapper.properties").read_text()
    assert "distributionSha256Sum=" in wrapper
    assert "[JAVA-MODERNE]" in (backend_dir / "CLAUDE.md").read_text()
    workflow = yaml.safe_load((project_dir / ".github/workflows/ci.yml").read_text())
    assert workflow["jobs"]["backend"]["uses"].startswith(
        "antoine-tena/kiln/.github/workflows/maven.yml@"
    )
    # Rien à auditer par uv ni pnpm : pas de job de sécurité vide.
    assert "securite" not in workflow["jobs"]
    charter = tomllib.loads((project_dir / "charte.toml").read_text())
    assert ".java" in charter["cliquets"]["taille-fichier"]["suffixes"]
    booleans_rule = next(
        line
        for line in (project_dir / "CLAUDE.md").read_text().splitlines()
        if line.startswith("- **[BOOLEENS]**")
    )
    assert "en Java" in booleans_rule
    assert "Python" not in booleans_rule


def test_team_gets_kiln_marketplace_and_base_plugin(tmp_path: Path) -> None:
    project_dir = generate(tmp_path / "demo", backend="java", frontend="aucun")

    settings = json.loads((project_dir / ".claude/settings.json").read_text())
    assert settings["extraKnownMarketplaces"]["kiln"]["source"] == {
        "source": "github",
        "repo": "antoine-tena/kiln",
    }
    assert settings["enabledPlugins"] == {"base@kiln": True}
