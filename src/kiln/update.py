"""`kiln update` : rapporte les évolutions du modèle, puis met à jour les dépendances."""

from collections.abc import Mapping
from pathlib import Path

import copier
from copier.errors import UserMessageError

from kiln import ui
from kiln.backlog import migrate_legacy_backlog
from kiln.check import check_project
from kiln.contract import generate_api_contract
from kiln.deps import lock_dependencies, sync_dependencies, update_dependencies
from kiln.frozen import frozen_files, report_frozen_drift
from kiln.rules import write_unverified_rules
from kiln.shell import KilnError, capture, require_tools, run, step
from kiln.stack import ANSWERS_FILE, load_stack, read_answers
from kiln.template import DEFAULT_TEMPLATE_SOURCE, template_revision
from kiln.versions import follows_candidates, notes_between, read_changelog

PROTECTED_BRANCHES = ("main", "develop")
# Ancienne adresse du modèle (init-repo, renommé kiln) : GitHub redirige, mais on la remplace.
LEGACY_TEMPLATE_SOURCES = ("https://github.com/antoine-tena/init-repo.git",)


def update_project(
    root: Path,
    *,
    should_update_template: bool,
    should_update_deps: bool,
    allow_major: bool,
    should_check: bool = True,
) -> None:
    require_tools("git", "uv")
    check_working_branch(root)
    if should_update_template:
        step("Architecture : évolutions du modèle")
        previous = template_commit(root)
        apply_template(root)
        show_release_notes(previous, template_commit(root))
        report_frozen_drift(root, _template_source(root), previous, template_commit(root))
    stack = load_stack(root)
    if should_update_deps:
        update_dependencies(root, stack, allow_major=allow_major)
    elif should_update_template:
        lock_dependencies(root, stack)
        sync_dependencies(root, stack)
    generate_api_contract(root, stack)
    write_unverified_rules(root, stack)
    report_changes(root)
    if should_check:
        check_project(root)


def apply_template(root: Path, answers: Mapping[str, object] | None = None) -> None:
    """Modèle réappliqué (révision la plus récente, réponses éventuellement changées), sans
    écraser les modifications locales : les conflits sont marqués dans les fichiers. Les
    fichiers figés (`kiln-waivers.toml`) sont laissés tels quels."""
    try:
        copier.run_update(
            root,
            data=dict(answers or {}),
            vcs_ref=template_revision(_template_source(root)),
            use_prereleases=follows_candidates(),
            exclude=frozen_files(root),
            defaults=True,
            skip_answered=True,
            overwrite=True,
            conflict="inline",
            unsafe=False,
        )
    except UserMessageError as error:
        raise KilnError(f"mise à jour du modèle refusée : {error}") from error
    # Après Copier, qui exige un arbre propre et réécrit le fichier de réponses.
    replace_legacy_source(root)
    if migrate_legacy_backlog(root):
        ui.note("Suivi déplacé de docs/a-faire/ vers docs/backlog/ (tickets T-NN, en anglais).")


def _template_source(root: Path) -> str:
    source = str(read_answers(root).get("_src_path", ""))
    return DEFAULT_TEMPLATE_SOURCE if source in LEGACY_TEMPLATE_SOURCES else source


def template_commit(root: Path) -> str:
    """Révision du modèle dont part le repo : `v3`, ou un commit avant la première version."""
    return str(read_answers(root).get("_commit", ""))


def show_release_notes(previous: str, current: str) -> None:
    """Encadré des nouveautés de chaque version passée, d'après le journal de kiln."""
    notes = notes_between(previous, current, read_changelog())
    if not notes:
        return
    lines: list[str] = []
    for release in notes:
        lines += [f"{release.tag}  {release.date}".rstrip(), *release.lines, ""]
    ui.panel(f"Nouveautés de kiln : {previous or '?'} → {current}", lines[:-1])


def check_working_branch(root: Path) -> None:
    if not (root / ANSWERS_FILE).exists():
        raise KilnError(f"pas de {ANSWERS_FILE} : ce dépôt n'a pas été généré par kiln")
    branch = capture(["git", "branch", "--show-current"], root)
    if branch in PROTECTED_BRANCHES:
        raise KilnError(f"sur {branch} : créer d'abord une branche (ex. chore/kiln-update)")
    if capture(["git", "status", "--porcelain"], root):
        raise KilnError("arbre non propre : commiter ou mettre de côté les modifications")


def report_changes(root: Path) -> None:
    step("Fichiers modifiés")
    run(["git", "status", "--short"], root, live=True)
    print()
    ui.note(
        "Relire le diff (conflits marqués <<<<<<<), commiter, puis fusionner dans develop "
        "(skill base:fusion)."
    )


def replace_legacy_source(root: Path) -> None:
    answers_path = root / ANSWERS_FILE
    text = answers_path.read_text()
    for legacy_source in LEGACY_TEMPLATE_SOURCES:
        text = text.replace(f"_src_path: {legacy_source}", f"_src_path: {DEFAULT_TEMPLATE_SOURCE}")
    answers_path.write_text(text)
