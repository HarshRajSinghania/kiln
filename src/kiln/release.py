"""`kiln version` : où en sont les versions de kiln, et quoi sortir ensuite (dépôt de kiln).

- **Numéro** (CLAUDE.md, Versions) : en 0.x, chaque version monte le correctif, cassante
  comprise, comme Claude Code ; la mineure ne monte que pour une étape décidée
  (`kiln version --minor`). À partir de 1.0, semver strict, comme Next.js : cassant → majeure,
  `feat` → mineure, le reste → correctif.
- **Promotion** : une candidate (`vX.Y.Z-rc.N`, la dernière de sa version) devient publique quand
  une candidate d'une version plus récente existe : la suivante prête, pas un délai, évite le
  correctif d'urgence. Les repos du dossier de code disent qui l'a déjà adoptée.

Lecture seule : les tags et les fusions se font par la skill `base:version` (CLAUDE.md, Versions).
"""

import datetime
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from kiln import ui
from kiln.config import load_config
from kiln.fleet import find_repos
from kiln.shell import KilnError, capture
from kiln.versions import release_version

# Jours d'usage d'une candidate avant promotion : plus court en 0.x, où tout bouge vite.
BREAKING_SUBJECT = re.compile(r"^\w+(\([^)]*\))?!:")
FEATURE_SUBJECT = re.compile(r"^feat(\([^)]*\))?:")
INTEGRATION_REF = "origin/develop"
VERSION_MODULE = Path("src") / "kiln" / "versions.py"


@dataclass(frozen=True)
class Tag:
    name: str
    version: Version
    created: datetime.datetime


def show_release_status(root: Path, *, milestone: bool = False) -> None:
    if not (root / VERSION_MODULE).is_file():
        raise KilnError("kiln version se lance dans le dépôt de kiln")
    capture(["git", "fetch", "-q", "--tags", "origin"], root)
    tags = read_tags(root)
    public = [tag for tag in tags if not tag.version.is_prerelease]
    candidates = latest_candidates(tags)
    now = datetime.datetime.now(datetime.UTC)
    print(f"\n  {ui.paint('PUBLIQUE', ui.FIRE, bold=True)}")
    print(f"    {public[-1].name if public else ui.paint('aucune encore', ui.STONE)}")
    print(f"\n  {ui.paint('CANDIDATES', ui.FIRE, bold=True)}")
    if not candidates:
        print(f"    {ui.paint('aucune', ui.STONE)}")
    adopted = _adoption()
    for candidate in candidates:
        verdict, ready = promotion_verdict(candidate, candidates)
        mark = ui.paint("✓", ui.MOSS) if ready else ui.paint("·", ui.STONE)
        age = (now - candidate.created).days
        users = adopted.get(candidate.name, [])
        print(
            f"    {mark} {ui.paint(f'{candidate.name:<16}', bold=True)} {age} j  {verdict}"
            + (ui.paint(f"  · {', '.join(users)}", ui.STONE) if users else "")
        )
    last = tags[-1] if tags else None
    subjects = _subjects_since(root, last.name if last else None)
    baseline = last.version if last else _package_version(root)
    proposed = next_version(baseline, subjects, milestone=milestone)
    print(f"\n  {ui.paint('PROCHAINE', ui.FIRE, bold=True)}")
    if subjects:
        detail = f"{len(subjects)} commits depuis {last.name}" if last else "première version"
        print(f"    v{proposed}-rc.1  {ui.paint(f'({detail})', ui.STONE)}")
        if Version(proposed).major == 0 and not milestone:
            print(f"    {ui.paint('une étape ? kiln version --minor', ui.STONE)}")
    else:
        print(f"    {ui.paint('rien de neuf sur develop', ui.STONE)}")
    print()


def read_tags(root: Path) -> list[Tag]:
    """Tags de version du dépôt, du plus ancien au plus récent."""
    listing = capture(
        ["git", "tag", "-l", "v*", "--format=%(refname:short) %(creatordate:iso-strict)"], root
    )
    tags = []
    for line in listing.splitlines():
        name, _, created = line.partition(" ")
        version = release_version(name)
        if version is not None and created:
            tags.append(Tag(name, version, datetime.datetime.fromisoformat(created)))
    return sorted(tags, key=lambda tag: tag.version)


def latest_candidates(tags: list[Tag]) -> list[Tag]:
    """Dernière candidate de chaque version pas encore promue."""
    promoted = {tag.version for tag in tags if not tag.version.is_prerelease}
    latest: dict[Version, Tag] = {}
    for tag in tags:
        if tag.version.is_prerelease:
            final = Version(tag.version.base_version)
            if final not in promoted:
                latest[final] = tag
    return [latest[final] for final in sorted(latest)]


def promotion_verdict(candidate: Tag, candidates: list[Tag]) -> tuple[str, bool]:
    if not any(other.version > candidate.version for other in candidates):
        return "attend une version suivante prête", False
    return f"prête : promouvoir en v{candidate.version.base_version}", True


def next_version(last: Version, subjects: list[str], *, milestone: bool = False) -> str:
    """Numéro de la prochaine version, d'après les commits depuis `last` (la dernière version,
    ou celle de `pyproject.toml` avant la première). En 0.x, le correctif suivant, sauf pour une
    étape (`milestone`) ; à partir de 1.0, le semver strict."""
    # Une candidate compte comme sa version : ses correctifs à elle vont en `-rc.N+1` sur sa
    # branche, ce qui vient de develop prépare la version d'après.
    major, minor, patch = Version(last.base_version).release[:3]
    is_breaking = any(BREAKING_SUBJECT.match(s) or "BREAKING CHANGE" in s for s in subjects)
    has_feature = any(FEATURE_SUBJECT.match(s) for s in subjects)
    if major == 0:
        return f"0.{minor + 1}.0" if milestone else f"0.{minor}.{patch + 1}"
    if is_breaking:
        return f"{major + 1}.0.0"
    return f"{major}.{minor + 1}.0" if has_feature else f"{major}.{minor}.{patch + 1}"


def _package_version(root: Path) -> Version:
    """Version de `pyproject.toml`, point de départ tant qu'aucune version n'est taguée ; la
    première est cassante par principe (rien ne la précède publiquement)."""
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    return Version(str(project["version"]))


def _subjects_since(root: Path, tag: str | None) -> list[str]:
    if tag is None:
        # Avant la première version, tout est nouveau : elle compte comme cassante.
        return ["feat!: première version"]
    log = capture(
        ["git", "log", "--no-merges", "--format=%s%n%b%x00", f"{tag}..{INTEGRATION_REF}"], root
    )
    return [entry.strip() for entry in log.split("\x00") if entry.strip()]


def _adoption() -> dict[str, list[str]]:
    """Version du modèle de chaque repo du dossier de code : qui a adopté quelle candidate."""
    code_dir = load_config().code_dir
    adopted: dict[str, list[str]] = {}
    if not code_dir.is_dir():
        return adopted
    for repo in find_repos(code_dir):
        adopted.setdefault(repo.template_commit, []).append(repo.root.name)
    return adopted
