"""Création du dépôt GitHub, protection de main et develop, invitations de l'équipe."""

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from kiln.shell import KilnError, run, step

LOGIN_URL = "https://github.com/login/device"
MAIN_RULESET_NAME = "Protection main"
DEVELOP_RULESET_NAME = "Protection develop"
REPOSITORY_ADMIN_ROLE_ID = 5

# main garde le seul commit initial : verrouillée, personne n'y pousse, sauf l'admin qui peut la
# réécrire. develop, branche de travail et d'intégration, ne se supprime ni ne se réécrit.
DEVELOP_RULESET = {
    "name": DEVELOP_RULESET_NAME,
    "target": "branch",
    "enforcement": "active",
    "conditions": {"ref_name": {"include": ["refs/heads/develop"], "exclude": []}},
    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
}
MAIN_RULESET = {
    "name": MAIN_RULESET_NAME,
    "target": "branch",
    "enforcement": "active",
    "conditions": {
        "ref_name": {"include": ["refs/heads/main"], "exclude": []},
    },
    "bypass_actors": [
        {
            "actor_id": REPOSITORY_ADMIN_ROLE_ID,
            "actor_type": "RepositoryRole",
            "bypass_mode": "always",
        },
    ],
    "rules": [{"type": "deletion"}, {"type": "update"}],
}


def ensure_logged_in() -> None:
    """Vérifie la connexion de gh avant de générer quoi que ce soit ; au terminal, la propose."""
    if _is_logged_in():
        return
    if not sys.stdin.isatty():
        raise KilnError(
            f"gh n'est pas connecté à GitHub : lancer `gh auth login --web` ({LOGIN_URL}), "
            "ou `kiln new … --no-github`"
        )
    step(f"GitHub : connexion (ouvrir {LOGIN_URL} et saisir le code affiché)")
    run(["gh", "auth", "login", "--web", "--git-protocol", "https"], Path.cwd())
    if not _is_logged_in():
        raise KilnError(f"connexion à GitHub non aboutie : réessayer sur {LOGIN_URL}")


def _is_logged_in() -> bool:
    status = subprocess.run(["gh", "auth", "status"], capture_output=True, check=False)
    return status.returncode == 0


def publish(root: Path, repository: str, team_logins: list[str]) -> None:
    step(f"GitHub : dépôt privé {repository}")
    run(["gh", "repo", "create", repository, "--private", "--source", "."], root)
    run(["git", "push", "-q", "-u", "origin", "main", "develop"], root)
    run(["gh", "repo", "edit", repository, "--default-branch", "develop"], root)
    step("GitHub : protection de main et develop")
    _post_ruleset(root, repository, MAIN_RULESET)
    _post_ruleset(root, repository, DEVELOP_RULESET)
    step("GitHub : alertes et correctifs de sécurité (Dependabot)")
    _enable_security_updates(root, repository)
    owner = repository.split("/")[0]
    for login in team_logins:
        if login != owner:
            step(f"GitHub : invitation de {login}")
            _gh_put(root, f"repos/{repository}/collaborators/{login}", "permission=push")


def _gh_put(root: Path, endpoint: str, *fields: str) -> None:
    field_options = [option for field in fields for option in ("-f", field)]
    run(["gh", "api", "-X", "PUT", endpoint, *field_options, "--silent"], root)


def _enable_security_updates(root: Path, repository: str) -> None:
    """Dependabot ne propose que les correctifs de sécurité ; le reste passe par kiln update."""
    _gh_put(root, f"repos/{repository}/vulnerability-alerts")
    _gh_put(root, f"repos/{repository}/automated-security-fixes")


def _post_ruleset(root: Path, repository: str, ruleset: Mapping[str, object]) -> None:
    completed = subprocess.run(
        ["gh", "api", "-X", "POST", f"repos/{repository}/rulesets", "--input", "-", "--silent"],
        cwd=root,
        input=json.dumps(ruleset),
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise KilnError("création du ruleset refusée par GitHub")
