"""`kiln waive` : liste, ajoute ou renouvelle une dérogation de `kiln-waivers.toml`.

La commande remplit ce qu'on oublie à la main (auteur, dates, palier) et refuse ce que `charte`
refuserait. Elle ne touche qu'à l'entrée visée : le reste du fichier, commentaires compris,
reste tel quel.
"""

import datetime
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from kiln import ui
from kiln.charte.charte import derogations
from kiln.charte.moteur import Depot
from kiln.charte.waivers import NEVER, NOT_WAIVABLE, TIERS_DAYS, WAIVERS_FILE, max_days
from kiln.shell import KilnError, capture

RULE_ID = re.compile(r"[A-Z0-9+-]+")
TIERS = ", ".join(map(str, TIERS_DAYS[:-1])) + f" puis {TIERS_DAYS[-1]}"
HEADER = f"""\
# Dérogations de ce repo aux règles de kiln (CLAUDE.md [DEROGATIONS]), vérifiées par `charte`.
# kiln ne réécrit jamais ce fichier ; `kiln waive` y ajoute ou renouvelle une entrée.
# Durée au plus : {TIERS} jours, palier suivant à chaque renouvellement.
"""


@dataclass(frozen=True)
class WaiveRequest:
    target: str  # identifiant de règle, ou chemin d'un fichier à figer
    reason: str
    paths: tuple[str, ...] = ()
    renew: bool = False
    permanent: bool = False
    upstream: str = ""


def show_waivers(root: Path) -> None:
    waivers = derogations(_depot(root))
    if not (waivers.actives or waivers.errors):
        ui.note(f"Aucune dérogation ({WAIVERS_FILE}). Ajouter : kiln waive <RÈGLE> --reason …")
        return
    lines = [
        f"- {w.label} : {w.reason} ({w.by}, jusqu'au {w.until or 'jamais'}, "
        f"{w.renewals} renouvellement(s))"
        for w in waivers.actives
    ]
    lines += [f"! {message}" for message in waivers.warnings + waivers.errors]
    ui.panel(f"Dérogations ({WAIVERS_FILE})", lines)


def waive(root: Path, request: WaiveRequest, today: datetime.date | None = None) -> None:
    today = today or datetime.date.today()
    if not request.reason.strip():
        raise KilnError("une dérogation se justifie : --reason « pourquoi »")
    is_rule = RULE_ID.fullmatch(request.target) is not None
    if is_rule and request.target in NOT_WAIVABLE:
        raise KilnError(f"[{request.target}] ne se déroge pas")
    if not is_rule and request.paths:
        raise KilnError("--paths ne va qu'avec une règle ; un fichier se fige en entier")
    path = root / WAIVERS_FILE
    text = path.read_text("utf-8") if path.exists() else HEADER
    blocks = _split(text)
    key = "rule" if is_rule else "file"
    index = next(
        (
            i
            for i, block in enumerate(blocks[1:], start=1)
            if _matches(block, key, request.target, request.paths)
        ),
        None,
    )
    if request.renew and index is None:
        raise KilnError(f"aucune dérogation à renouveler pour {request.target}")
    if not request.renew and index is not None:
        raise KilnError(f"{request.target} est déjà dérogée : --renew pour la prolonger")
    renewals = 0 if index is None else _renewals(blocks[index]) + 1
    until = NEVER if request.permanent else today + datetime.timedelta(days=max_days(renewals))
    entry = {
        key: request.target,
        "paths": list(request.paths),
        "reason": request.reason.strip(),
        "by": capture(["git", "config", "user.name"], root) or "inconnu",
        "since": today,
        "until": until,
        "renewals": renewals,
        "upstream": request.upstream,
    }
    block = _block(entry)
    if index is None:
        blocks.append(block)
    else:
        blocks[index] = block
    previous = path.read_text("utf-8") if path.exists() else None
    path.write_text(_join(blocks), "utf-8")
    problems = [e for e in derogations(_depot(root)).errors if request.target in e]
    if problems:
        _restore(path, previous)
        raise KilnError("dérogation refusée : " + " ; ".join(problems))
    ui.note(
        f"{request.target} dérogée jusqu'au {until} ({WAIVERS_FILE}, à commiter). Si la règle "
        "est fausse pour tout le monde : skill base:report-to-kiln, puis --upstream <lien>."
    )


def _depot(root: Path) -> Depot:
    config = root / "charte.toml"
    return Depot(root, tomllib.loads(config.read_text("utf-8")) if config.exists() else {})


def _split(text: str) -> list[str]:
    """En-tête, puis un bloc par `[[waiver]]` (commentaires qui le suivent compris)."""
    parts = re.split(r"(?m)^(?=\[\[waiver\]\]\s*$)", text)
    return parts if parts else [""]


def _join(blocks: list[str]) -> str:
    return (
        "".join(b if b.endswith("\n\n") else b.rstrip("\n") + "\n\n" for b in blocks).rstrip("\n")
        + "\n"
    )


def _matches(block: str, key: str, target: str, paths: tuple[str, ...]) -> bool:
    try:
        entries = tomllib.loads(block).get("waiver", [])
    except tomllib.TOMLDecodeError:
        return False
    return any(
        e.get(key) == target and (not paths or tuple(e.get("paths", [])) == paths) for e in entries
    )


def _renewals(block: str) -> int:
    return int(tomllib.loads(block)["waiver"][0].get("renewals", 0))


def _block(entry: dict[str, object]) -> str:
    lines = ["[[waiver]]"]
    for key, value in entry.items():
        if value in ("", [], None):
            continue
        lines.append(f"{key} = {_toml(value)}")
    return "\n".join(lines) + "\n"


def _toml(value: object) -> str:
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml(v) for v in value) + "]"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _restore(path: Path, previous: str | None) -> None:
    if previous is None:
        path.unlink()
    else:
        path.write_text(previous, "utf-8")
