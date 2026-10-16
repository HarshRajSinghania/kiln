"""Dérogations : écarts assumés à une règle de kiln, déclarés dans `kiln-waivers.toml` à la
racine du repo. kiln ne génère ni ne réécrit ce fichier.

Une dérogation porte sur une règle (`rule`, identifiant de la charte), dans tout le repo ou dans
`paths` (motifs git), avec une raison, un auteur et une échéance. La confiance se gagne : la
première période dure une semaine au plus, puis chaque renouvellement (`renewals`) allonge le
palier (un mois, trois mois, six mois). `until = "never"` déclare un écart permanent, toujours
affiché. Une dérogation échue ne s'applique plus ; une dérogation qui ne correspond plus à rien
échoue, comme un cliquet trop large. Certaines règles ne se dérogent pas.
"""

from __future__ import annotations

import datetime
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WAIVERS_FILE = "kiln-waivers.toml"
RULE_ID = "WAIVERS"
# Durée maximale d'une période, selon le nombre de renouvellements (le dernier palier se répète).
TIERS_DAYS = (7, 30, 90, 182)
NEVER = "never"
# Planchers de sécurité et d'hygiène : aucune dérogation.
NOT_WAIVABLE = frozenset({"DONNEES-PERSO", "PAS-SUR-MAIN", "DEPENDANCES-FIGEES", "SECRETS"})
REQUIRED = ("reason", "by", "since", "until")
KNOWN_KEYS = frozenset({"rule", "paths", "file", *REQUIRED, "renewals", "upstream"})


@dataclass(frozen=True)
class Waiver:
    rule: str
    paths: tuple[str, ...]
    file: str
    reason: str
    by: str
    since: datetime.date
    until: datetime.date | None  # None : permanente (`until = "never"`)
    renewals: int

    @property
    def label(self) -> str:
        cible = self.rule or f"fichier {self.file}"
        return f"{cible} ({', '.join(self.paths)})" if self.paths else cible


@dataclass
class Waivers:
    """Dérogations lues, et ce que leur lecture a relevé (erreurs, avertissements)."""

    actives: list[Waiver] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def for_rule(self, rule: str) -> list[Waiver]:
        return [w for w in self.actives if w.rule and w.rule == rule]

    def waived_paths(self, rule: str) -> list[str] | None:
        """Motifs exclus pour `rule` ; None si une dérogation couvre tout le repo."""
        motifs: list[str] = []
        for waiver in self.for_rule(rule):
            if not waiver.paths:
                return None
            motifs.extend(waiver.paths)
        return motifs


def max_days(renewals: int) -> int:
    return TIERS_DAYS[min(renewals, len(TIERS_DAYS) - 1)]


def load(root: Path, today: datetime.date | None = None) -> Waivers:
    path = root / WAIVERS_FILE
    result = Waivers()
    if not path.exists():
        return result
    try:
        data = tomllib.loads(path.read_text("utf-8"))
    except tomllib.TOMLDecodeError as error:
        result.errors.append(f"{WAIVERS_FILE} illisible : {error}")
        return result
    today = today or datetime.date.today()
    for index, entry in enumerate(data.get("waiver", []), start=1):
        _read(entry, f"dérogation n°{index}", today, result)
    return result


def _read(entry: dict[str, Any], where: str, today: datetime.date, result: Waivers) -> None:
    problems = _problems(entry)
    if problems:
        result.errors.append(f"{where} : {' ; '.join(problems)}")
        return
    until = entry["until"]
    waiver = Waiver(
        rule=entry.get("rule", ""),
        paths=tuple(entry.get("paths", [])),
        file=entry.get("file", ""),
        reason=entry["reason"],
        by=entry["by"],
        since=entry["since"],
        until=None if until == NEVER else until,
        renewals=entry.get("renewals", 0),
    )
    where = f"{where} [{waiver.label}]"
    if waiver.until is None:
        result.warnings.append(f"{where} : permanente — {waiver.reason}")
        result.actives.append(waiver)
        return
    allowed = max_days(waiver.renewals)
    if (waiver.until - waiver.since).days > allowed:
        result.errors.append(
            f"{where} : {(waiver.until - waiver.since).days} jours, au plus {allowed} après "
            f"{waiver.renewals} renouvellement(s) (paliers {', '.join(map(str, TIERS_DAYS))})"
        )
        return
    if today > waiver.until:
        result.errors.append(
            f"{where} : échue le {waiver.until} — corriger, ou renouveler (`renewals` + 1, "
            f"nouvelle période d'au plus {max_days(waiver.renewals + 1)} jours)"
        )
        return
    left = (waiver.until - today).days
    if left * 2 <= (waiver.until - waiver.since).days:
        result.warnings.append(f"{where} : échoit le {waiver.until} (dans {left} jour(s))")
    result.actives.append(waiver)


def _problems(entry: dict[str, Any]) -> list[str]:
    problems = [f"clé inconnue `{k}`" for k in entry if k not in KNOWN_KEYS]
    problems += [f"`{k}` manquant" for k in REQUIRED if not entry.get(k)]
    rule, file = entry.get("rule"), entry.get("file")
    if bool(rule) == bool(file):
        problems.append("une cible, et une seule : `rule` ou `file`")
    if rule in NOT_WAIVABLE:
        problems.append(f"[{rule}] ne se déroge pas")
    if file and entry.get("paths"):
        problems.append("`paths` ne va qu'avec `rule`")
    if "since" in entry and not isinstance(entry["since"], datetime.date):
        problems.append("`since` : une date (2026-10-16)")
    until = entry.get("until")
    if until is not None and until != NEVER and not isinstance(until, datetime.date):
        problems.append(f'`until` : une date, ou "{NEVER}"')
    renewals = entry.get("renewals", 0)
    if not isinstance(renewals, int) or renewals < 0:
        problems.append("`renewals` : un entier positif ou nul")
    return problems


def check_targets(
    waivers: Waivers, known_rules: Iterable[str], tracked: Callable[[list[str]], list[Path]]
) -> None:
    """Une dérogation qui ne vise plus rien (règle inconnue, motif sans fichier) est retirée et
    signalée : sinon elle couvrirait en silence le prochain fichier qui y correspondrait."""
    rules = set(known_rules)
    kept = []
    for waiver in waivers.actives:
        if waiver.rule and waiver.rule not in rules:
            waivers.errors.append(f"[{waiver.label}] : règle inconnue de la charte du repo")
            continue
        vides = [m for m in (*waiver.paths, *filter(None, [waiver.file])) if not tracked([m])]
        if vides:
            waivers.errors.append(f"[{waiver.label}] : aucun fichier pour {', '.join(vides)}")
            continue
        kept.append(waiver)
    waivers.actives = kept
