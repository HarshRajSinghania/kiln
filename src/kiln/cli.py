"""kiln : l'atelier de Claude Code. Génère un projet, règle ses paramètres et le tient à jour."""

import argparse
import re
import sys
import time
from pathlib import Path

from kiln import (
    banner,
    check,
    ci,
    contract,
    dev,
    doctor,
    fleet,
    install,
    new,
    poste,
    release,
    settings,
    ui,
    update,
    waive,
)
from kiln.config import load_config
from kiln.shell import KilnError, repo_root
from kiln.stack import load_stack

EXIT_FAILURE = 1
PROJECT_NAME = re.compile(r"[a-z][a-z0-9-]*")
SIZES = ("spark", "ember", "flame", "blaze")
PROJECT_TYPES = ("app", "api", "site", "tableau", "analyse", "outil")
BACKENDS = ("django", "fastapi", "data", "cli", "java", "aucun")
FRONTENDS = ("nuxt", "next", "astro", "streamlit", "dash", "aucun")


# Écran d'accueil : commandes par section ; le rôle de chacune vient de son aide argparse.
COMMAND_GROUPS = (
    ("Projet", ("new", "install", "update", "set", "waive")),
    ("Au quotidien", ("dev", "check", "ci", "contrat", "doctor")),
    ("Tous les repos", ("status", "update --all", "version")),
)
FLEET_UPDATE_ROLE = "mettre à jour chaque repo kiln, fusion directe"
EXAMPLES = (
    "kiln new atelier --size ember --backend fastapi",
    "kiln update --major",
    "kiln set podman=true",
    "kiln set equipe=alice,bob     # hors d'un repo : réglages du poste",
)
NO_RECAP_COMMANDS = frozenset({"dev", "ci", "status", "doctor", "version", "waive"})
HELP_FLAGS: tuple[list[str], ...] = ([], ["-h"], ["--help"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kiln", description=__doc__)
    commands = parser.add_subparsers(dest="command")
    _add_new_command(commands)
    commands.add_parser("install", help="préparer le poste après un clone")
    _add_update_command(commands)
    dev_parser = commands.add_parser("dev", help="lancer le projet en local")
    dev_parser.add_argument("--containers", action="store_true", help="toute la pile dans podman")
    commands.add_parser("check", help="lancer les contrôles du projet")
    _add_ci_command(commands)
    commands.add_parser("contrat", help="régénérer openapi.json et les types du front")
    version_parser = commands.add_parser(
        "version", help="versions de kiln : publique, candidates, prochaine"
    )
    version_parser.add_argument(
        "--minor", action="store_true", help="la prochaine est une étape : monter la mineure"
    )
    commands.add_parser("doctor", help="diagnostiquer le poste et le repo, avec les corrections")
    status_parser = commands.add_parser("status", help="état des repos kiln du dossier de code")
    status_parser.add_argument("--all", action="store_true", help="(par défaut) tous les repos")
    set_parser = commands.add_parser(
        "set", help="afficher ou changer les paramètres du repo (hors d'un repo : du poste)"
    )
    set_parser.add_argument("assignments", nargs="*", metavar="clé=valeur")
    set_parser.add_argument(
        "--poste", action="store_true", help="réglages du poste, même depuis un repo"
    )
    _add_waive_command(commands)
    return parser


def _add_waive_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    waive_parser = commands.add_parser(
        "waive", help="déroger à une règle de kiln, ou figer un fichier (sans argument : lister)"
    )
    waive_parser.add_argument(
        "target", nargs="?", metavar="RÈGLE|fichier", help="identifiant de règle, ou fichier généré"
    )
    waive_parser.add_argument("--reason", default="", help="pourquoi (obligatoire)")
    waive_parser.add_argument("--paths", nargs="+", default=[], help="motifs git couverts")
    waive_parser.add_argument(
        "--renew", action="store_true", help="renouveler : palier suivant, raison redemandée"
    )
    waive_parser.add_argument("--permanent", action="store_true", help="écart sans échéance")
    waive_parser.add_argument("--upstream", default="", help="issue ou PR ouverte chez kiln")


def _add_new_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    new_parser = commands.add_parser("new", help="générer un nouveau projet complet")
    new_parser.add_argument(
        "directory", type=Path, nargs="?", help="dossier du projet (sinon demandé : nom du projet)"
    )
    new_parser.add_argument("--name", help="nom court (par défaut : nom du dossier)")
    new_parser.add_argument("--title", help="titre affiché")
    new_parser.add_argument("--description", help="une phrase sur le projet")
    new_parser.add_argument("--owner", help="compte GitHub propriétaire")
    new_parser.add_argument("--team", help="logins GitHub séparés par des virgules")
    new_parser.add_argument("--size", choices=SIZES, help="envergure du projet")
    new_parser.add_argument("--type", dest="project_type", choices=PROJECT_TYPES, help="conseil")
    new_parser.add_argument("--backend", choices=BACKENDS, help="backend (sinon conseillé)")
    new_parser.add_argument("--frontend", choices=FRONTENDS, help="frontend (sinon conseillé)")
    new_parser.add_argument("--podman", action="store_true", help="conteneurs podman")
    new_parser.add_argument(
        "--vps", metavar="UTILISATEUR@ADRESSE", help="déploiement sur ce serveur (Django + podman)"
    )
    new_parser.add_argument("--goal", help="boussole (north star) du suivi docs/backlog/")
    new_parser.add_argument("--prod-url", help="sonde de santé de la production (status line)")
    new_parser.add_argument(
        "--no-github", action="store_true", help="ne pas créer le dépôt GitHub (créé par défaut)"
    )
    new_parser.add_argument("--no-install", action="store_true", help="ne rien installer")
    new_parser.add_argument("--template", help="source du modèle (chemin ou URL git)")


def _add_ci_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ci_parser = commands.add_parser("ci", help="rejouer la CI d'un commit sur le poste")
    ci_parser.add_argument("revision", nargs="?", default="HEAD", help="commit (défaut : HEAD)")
    ci_parser.add_argument(
        "--sauter", action="append", default=[], metavar="JOB", help="job du ci.yml à écarter"
    )
    ci_parser.add_argument("--sans-pousser", action="store_true", help="note gardée en local")
    ci_parser.add_argument("--garder", action="store_true", help="garder le worktree du commit")
    ci_parser.add_argument("--statut", action="store_true", help="verdict seul, sans rejouer")


def _add_update_command(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    update_parser = commands.add_parser("update", help="mettre à jour modèle et dépendances")
    update_parser.add_argument("--no-template", action="store_true", help="garder l'architecture")
    update_parser.add_argument("--no-deps", action="store_true", help="garder les dépendances")
    update_parser.add_argument("--major", action="store_true", help="versions majeures comprises")
    update_parser.add_argument(
        "--all", action="store_true", help="tous les repos kiln, fusion directe"
    )


def _new_project_request(arguments: argparse.Namespace) -> new.NewProjectRequest:
    directory = arguments.directory or Path(arguments.name or _ask_project_name())
    answers: dict[str, object] = {"nom": arguments.name or directory.name}
    if arguments.title:
        answers["titre"] = arguments.title
    if arguments.description:
        answers["description"] = arguments.description
    for key, value in (
        ("envergure", arguments.size),
        ("type_projet", arguments.project_type),
        ("backend", arguments.backend),
        ("frontend", arguments.frontend),
    ):
        if value:
            answers[key] = value
    if arguments.podman:
        answers["podman"] = True
    if arguments.vps:
        answers.update(deploiement="vps", vps_hote=arguments.vps)
    if arguments.goal:
        answers["boussole"] = arguments.goal
    if arguments.prod_url:
        answers["url_sante_prod"] = arguments.prod_url
    if arguments.owner:
        answers["proprietaire"] = arguments.owner
    if arguments.team:
        answers["equipe"] = [login.strip() for login in arguments.team.split(",")]
    return new.NewProjectRequest(
        destination=directory,
        answers=answers,
        template=arguments.template,
        should_install=not arguments.no_install,
        should_publish=not arguments.no_github,
    )


def _ask_project_name() -> str:
    """`kiln new` sans dossier : le nom est demandé, le projet est créé dans le dossier courant."""
    if not sys.stdin.isatty():
        raise KilnError("kiln new <dossier> : le dossier du projet est requis hors terminal")
    while True:
        name = input("Nom du projet (minuscules, chiffres, tirets) : ").strip()
        if PROJECT_NAME.fullmatch(name):
            return name
        print("Minuscules, chiffres et tirets seulement, en commençant par une lettre.")


BANNER_ACTIONS = {
    "new": "nouveau projet",
    "install": "installation",
    "update": "mise à jour",
    "status": "état des repos",
    "doctor": "diagnostic",
}


def dispatch(arguments: argparse.Namespace) -> None:
    _show_banner(arguments)
    if arguments.command == "new":
        new.create_project(_new_project_request(arguments))
        return
    if arguments.command == "doctor":
        doctor.run_doctor(Path.cwd())
        return
    if arguments.command == "version":
        release.show_release_status(repo_root(Path.cwd()), milestone=arguments.minor)
        return
    if arguments.command == "status" or (arguments.command == "update" and arguments.all):
        _dispatch_fleet(arguments)
        return
    if arguments.command == "set" and (arguments.poste or not _is_in_repo()):
        poste.run_poste(arguments.assignments)
        return
    root = _repo_root_or_hint()
    if arguments.command == "install":
        install.install_project(root)
    elif arguments.command == "update":
        update.update_project(
            root,
            should_update_template=not arguments.no_template,
            should_update_deps=not arguments.no_deps,
            allow_major=arguments.major,
        )
    elif arguments.command == "dev":
        dev.run_dev_servers(root, in_containers=arguments.containers)
    elif arguments.command == "check":
        check.check_project(root)
    elif arguments.command == "ci":
        _dispatch_ci(root, arguments)
    elif arguments.command == "contrat":
        contract.generate_api_contract(root, load_stack(root))
    elif arguments.command == "waive":
        _dispatch_waive(root, arguments)
    elif arguments.command == "set":
        if arguments.assignments:
            settings.apply_settings(root, arguments.assignments)
        else:
            settings.show_settings(root)


def _is_in_repo() -> bool:
    try:
        repo_root(Path.cwd())
    except KilnError:
        return False
    return True


def _repo_root_or_hint() -> Path:
    """Racine du repo courant ; hors d'un repo, l'erreur dit où aller et quoi lancer d'ici."""
    try:
        return repo_root(Path.cwd())
    except KilnError:
        code_dir = load_config().code_dir
        names = (
            [str(repo.root.relative_to(code_dir)) for repo in fleet.find_repos(code_dir)]
            if code_dir.is_dir()
            else []
        )
        repos_line = f" Repos kiln de {code_dir} : {', '.join(names)}." if names else ""
        raise KilnError(
            f"{Path.cwd()} n'est pas dans un repo : s'y placer d'abord (cd <repo>).{repos_line} "
            "D'ici : kiln status, kiln update --all, kiln set (réglages du poste), kiln new."
        ) from None


def _show_banner(arguments: argparse.Namespace) -> None:
    """Bannière des commandes longues ; les repos de la flotte sont dans le dossier de code."""
    action = BANNER_ACTIONS.get(arguments.command)
    if action is None:
        return
    if arguments.command in ("new", "status", "doctor") or getattr(arguments, "all", False):
        banner.show_banner(action if arguments.command != "update" else "mise à jour des repos")
        return
    banner.show_banner(action, _repo_root_or_hint())


def _dispatch_ci(root: Path, arguments: argparse.Namespace) -> None:
    if arguments.statut:
        if not ci.show_verdict(root, arguments.revision):
            sys.exit(EXIT_FAILURE)
        return
    skipped_jobs = frozenset(arguments.sauter)
    ci.require_known_jobs(root, skipped_jobs)
    verdict = ci.run_local_ci(
        root,
        arguments.revision,
        skipped_jobs,
        should_push=not arguments.sans_pousser,
        should_keep=arguments.garder,
    )
    print("\n" + verdict.render(), end="")
    if not verdict.is_success:
        sys.exit(EXIT_FAILURE)


def _dispatch_waive(root: Path, arguments: argparse.Namespace) -> None:
    if arguments.target is None:
        waive.show_waivers(root)
        return
    waive.waive(
        root,
        waive.WaiveRequest(
            target=arguments.target,
            reason=arguments.reason,
            paths=tuple(arguments.paths),
            renew=arguments.renew,
            permanent=arguments.permanent,
            upstream=arguments.upstream,
        ),
    )


def _dispatch_fleet(arguments: argparse.Namespace) -> None:
    code_dir = load_config().code_dir
    fleet.require_code_dir(code_dir)
    if arguments.command == "status":
        fleet.show_status(code_dir)
    else:
        fleet.update_all(code_dir, allow_major=arguments.major)


def show_home(parser: argparse.ArgumentParser) -> None:
    roles = {"update --all": FLEET_UPDATE_ROLE}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            roles |= {choice.dest: choice.help or "" for choice in action._choices_actions}
    banner.show_home(
        [
            (title, [(name, roles[name][:1].upper() + roles[name][1:]) for name in names])
            for title, names in COMMAND_GROUPS
        ],
        EXAMPLES,
    )


def main() -> None:
    try:
        parser = build_parser()
        if sys.argv[1:] in HELP_FLAGS:
            show_home(parser)
            return
        arguments = parser.parse_args()
        started = time.monotonic()
        try:
            dispatch(arguments)
        except KilnError:
            _recap(arguments, started, succeeded=False)
            raise
        _recap(arguments, started, succeeded=True)
    except KilnError as error:
        ui.error(str(error))
        sys.exit(EXIT_FAILURE)


def _recap(arguments: argparse.Namespace, started: float, *, succeeded: bool) -> None:
    """Bilan des commandes à étapes ; `dev` tourne jusqu'à l'arrêt, `ci` a son verdict."""
    if arguments.command not in NO_RECAP_COMMANDS:
        ui.recap(arguments.command, started, succeeded=succeeded)
