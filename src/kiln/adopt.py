"""`kiln adopt` : fait suivre kiln à un repo qu'il n'a pas généré.

Le modèle complet suppose son arborescence (`backend/`, `frontend/`) : il ne s'applique pas sur
un repo qui a la sienne. L'adoption pose seulement ce qui n'en dépend pas, sans toucher à un
fichier existant :
- `charte.toml` : l'envergure et les règles valables partout (uv et podman, pas de renvoi
  d'audit), que la commande `charte` vérifie après chaque édition (hook du plugin `base`) ;
- `docs/backlog/` : le suivi du travail (skill `base:backlog`), tiré du modèle.

Le repo devient « adopté » (charte sans réponses Copier) : `kiln status`, `check`, `dev`,
`install` et `doctor` le servent ; `kiln update` le laisse, faute de réponses à réappliquer.
Le passif que la charte relève dès l'adoption s'affiche : à résorber, ou sa règle à retirer.
"""

import re
import shutil
import tempfile
from pathlib import Path

import copier

from kiln import ui
from kiln.rules import write_unverified_rules
from kiln.shell import KilnError, capture, require_tools, run_status, step
from kiln.stack import ANSWERS_FILE, CHARTER_FILE, detect_stack
from kiln.template import template_revision, template_source
from kiln.update import PROTECTED_BRANCHES
from kiln.versions import follows_candidates

BACKLOG_DIR = Path("docs") / "backlog"
DEFAULT_SIZE = "ember"
# Stack la plus légère du modèle : seuls ses fichiers communs (le suivi) sont repris.
RENDER_STACK = {"backend": "cli", "frontend": "aucun"}

CHARTER = """\
# Règles impératives vérifiées par la commande `charte` de kiln (`charte --detail`) : après chaque
# édition (hook du plugin base de kiln), et en CI ou avant chaque commit si on l'y ajoute.
# Repo adopté par `kiln adopt` : seules les règles valables partout. Interdictions : respectées
# partout. D'autres (journalisation, données personnelles, cliquets…) s'ajoutent à la main, sur
# le modèle du charte.toml qu'écrit `kiln new`.

envergure = "{size}"
exclus = ["/migrations/", "/node_modules/", "/vendor/"]
regles_non_verifiees = "scripts/ci/charte-non-verifiee.txt"

[interdictions.outils-interdits]
id = "UV-PODMAN"

# Les renvois à un rapport d'audit (« audit H36 », « (CART-06) ») pourrissent avec lui. Ajouter
# à `prefixes` les préfixes des constats des audits du projet, à mesure qu'ils arrivent.
[interdictions.renvois-audit]
id = "RENVOIS-AUDIT"
prefixes = "AUDIT"
exclus = '(^docs/|^charte\\.toml$|/migrations/|-lock\\.yaml$|\\.lock$)'
"""


def adopt_project(root: Path, *, size: str = DEFAULT_SIZE, template: str | None = None) -> None:
    require_tools("git", "uv")
    check_adoptable(root)
    step("Charte")
    (root / CHARTER_FILE).write_text(CHARTER.format(size=size))
    write_unverified_rules(root, detect_stack(root))
    if (root / BACKLOG_DIR).exists():
        ui.note(f"{BACKLOG_DIR}/ existe déjà : gardé tel quel.")
    else:
        step("Suivi du travail")
        copy_backlog(root, template)
    step("Passif relevé par la charte")
    if shutil.which("charte") is None or run_status(["charte"], root, live=True) == 0:
        ui.note("Aucun écart.")
    else:
        ui.note(
            "Écarts ci-dessus : les corriger, ou retirer leur règle de charte.toml (choix du repo)."
        )
    ui.note("Relire, commiter, puis fusionner (skill base:fusion).")


def check_adoptable(root: Path) -> None:
    if (root / ANSWERS_FILE).exists():
        raise KilnError("repo généré par kiln : rien à adopter (kiln update pour le suivre)")
    if (root / CHARTER_FILE).exists():
        raise KilnError(f"{CHARTER_FILE} existe déjà : repo déjà adopté")
    branch = capture(["git", "branch", "--show-current"], root)
    if branch in (*PROTECTED_BRANCHES, "master"):
        raise KilnError(f"sur {branch} : créer d'abord une branche (ex. chore/kiln-adopt)")
    if capture(["git", "status", "--porcelain"], root):
        raise KilnError("arbre non propre : commiter ou mettre de côté les modifications")


def project_name(root: Path) -> str:
    """Nom court au format du modèle (minuscules, chiffres, tirets), tiré du dossier."""
    name = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-")
    return name if re.match(r"[a-z]", name) else f"projet-{name}".rstrip("-")


def copy_backlog(root: Path, template: str | None) -> None:
    source = template_source(template)
    with tempfile.TemporaryDirectory() as rendered:
        copier.run_copy(
            source,
            rendered,
            data={"nom": project_name(root), **RENDER_STACK},
            vcs_ref=template_revision(source),
            use_prereleases=follows_candidates(),
            defaults=True,
            quiet=True,
            unsafe=False,
        )
        shutil.copytree(Path(rendered) / BACKLOG_DIR, root / BACKLOG_DIR)
