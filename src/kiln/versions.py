"""Versions de kiln : semver à trois chiffres, `vMAJEUR.MINEUR.CORRECTIF`.

En 0.x, chaque version monte le correctif, cassante comprise (`0.3.4 → 0.3.5`) ; la mineure ne
monte que pour une étape (CLAUDE.md, Versions). Deux canaux : une version sort d'abord en
candidate (`v0.3.5-rc.1`), suivie par les postes au canal `interne` (`kiln set canal=interne`) ;
elle est promue (`v0.3.5`, fusion
dans `main`) quand la suivante est prête et qu'elle a tenu trois jours. Le canal `public`, par
défaut, ne voit que les versions promues. Chaque version a son entrée dans `CHANGELOG.md`, que
`kiln update` montre au passage d'une version à l'autre.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from importlib import resources
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from packaging.version import InvalidVersion, Version

from kiln.config import INTERNAL_CHANNEL, load_config

KILN_GIT_URL = "https://github.com/antoine-tena/kiln"
CHANGELOG_FILE = "CHANGELOG.md"
# `v0.4.0`, `v0.4.0-rc.2`, et ce que `git describe` ajoute derrière (`v0.4.0-3-gabc1234`).
RELEASE_TAG = re.compile(r"^v(\d+\.\d+\.\d+(?:-rc\.\d+)?)(?:-(\d+)-g([0-9a-f]+))?$")
RELEASE_HEADING = re.compile(r"^## (v\d+\.\d+\.\d+)(?:\s+[-—·]\s+(.+))?$")
NETWORK_TIMEOUT = 5
# Avant la première version, les projets suivaient un commit : tout est nouveau pour eux.
BEFORE_FIRST_RELEASE = Version("0")


@dataclass(frozen=True)
class ReleaseNotes:
    tag: str
    date: str
    lines: list[str]


def release_version(ref: str) -> Version | None:
    """Version d'un tag ou d'une sortie de `git describe` ; None pour un simple commit."""
    match = RELEASE_TAG.match(ref.strip())
    if match is None:
        return None
    try:
        return Version(match.group(1))
    except InvalidVersion:
        return None


def follows_candidates() -> bool:
    """Le poste suit-il les candidates (canal `interne`) ?"""
    return load_config().channel == INTERNAL_CHANNEL


def latest_release(source: str = KILN_GIT_URL, *, candidates: bool | None = None) -> str | None:
    """Tag de la version la plus récente du dépôt, candidates comprises au canal `interne` ;
    None sans réseau ou sans version."""
    if candidates is None:
        candidates = follows_candidates()
    try:
        listing = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", source],
            capture_output=True,
            text=True,
            timeout=NETWORK_TIMEOUT,
            check=False,
        ).stdout
    except subprocess.TimeoutExpired, OSError:
        return None
    tags = [line.rsplit("refs/tags/", 1)[-1] for line in listing.splitlines()]
    releases = [
        (version, tag)
        for tag in tags
        if (version := release_version(tag)) is not None
        and (candidates or not version.is_prerelease)
    ]
    return max(releases)[1] if releases else None


def installed_version() -> str:
    """Version de l'outil : `v3`, et pour un outil installé depuis un dossier, ce que dit git
    (`v3 +4 · abc1234` : quatre commits après v3)."""
    try:
        dist = distribution("kiln")
    except PackageNotFoundError:
        return "v?"
    package_version = f"v{dist.version}"
    source = _source_dir(dist.read_text("direct_url.json") or "")
    if source is None:
        return package_version
    try:
        described = subprocess.run(
            ["git", "-C", str(source), "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            timeout=NETWORK_TIMEOUT,
            check=False,
        ).stdout.strip()
    except subprocess.TimeoutExpired, OSError:
        return package_version
    match = RELEASE_TAG.match(described)
    if match is None:
        return f"{package_version} · {described}" if described else package_version
    tag, distance, commit = f"v{match.group(1)}", match.group(2), match.group(3)
    return f"{tag} +{distance} · {commit}" if distance else tag


def _source_dir(direct_url: str) -> Path | None:
    """Dossier d'où l'outil a été installé (`uv tool install <dossier>`), s'il y en a un."""
    try:
        origin = json.loads(direct_url) if direct_url else {}
    except ValueError:
        return None
    url = str(origin.get("url", ""))
    if "dir_info" not in origin or not url.startswith("file://"):
        return None
    return Path(url.removeprefix("file://"))


def read_changelog() -> str:
    """`CHANGELOG.md` livré avec l'outil ; à défaut, celui du dépôt (outil en développement)."""
    packaged = resources.files("kiln") / CHANGELOG_FILE
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    in_repo = Path(__file__).resolve().parents[2] / CHANGELOG_FILE
    return in_repo.read_text(encoding="utf-8") if in_repo.is_file() else ""


def parse_changelog(text: str) -> list[ReleaseNotes]:
    """Entrées `## vN — date` du journal, dans l'ordre du fichier (la plus récente en tête)."""
    notes: list[ReleaseNotes] = []
    for line in text.splitlines():
        heading = RELEASE_HEADING.match(line)
        if heading:
            notes.append(ReleaseNotes(heading.group(1), heading.group(2) or "", []))
        elif notes and line.strip():
            notes[-1].lines.append(line.rstrip())
    return notes


def notes_between(old_ref: str, new_ref: str, changelog: str) -> list[ReleaseNotes]:
    """Versions passées entre deux révisions du modèle : après `old_ref`, jusqu'à `new_ref`."""
    new = release_version(new_ref)
    if new is None:
        return []
    # Une candidate porte déjà les nouveautés de sa version : on compare les versions finales.
    old = Version((release_version(old_ref) or BEFORE_FIRST_RELEASE).base_version)
    target = Version(new.base_version)
    return [
        notes
        for notes in parse_changelog(changelog)
        if (version := release_version(notes.tag)) is not None and old < version <= target
    ]
