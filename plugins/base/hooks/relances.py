#!/usr/bin/env python3
"""Relances : quand reposer une question que kiln pose à l'utilisateur, pour toutes ses questions.

Mise à jour de l'outil ou du repo, adoption de kiln dans un autre repo : une seule politique.
- Chaque question a un genre (`maj`, `adoption`) et une clé (`outil`, la racine d'un repo). Le
  genre donne ses délais : sessions avant la première question, puis après chaque « non ».
- Une note de bienveillance du poste, de 0 à 1 (0,5 au départ), monte à chaque « oui » et baisse
  à chaque « non » du poids du genre : une adoption refusée pèse plus qu'une mise à jour remise.
  Elle étire ou raccourcit tous les délais : doublés à 0, tels quels à 0,5, moitié à 1. Qui dit
  oui se voit proposer kiln plus tôt ailleurs ; qui dit non, plus tard.
- Un genre peut aussi espacer ses questions sur tout le poste (`espacement`) : une adoption
  proposée dans un repo ne se repropose pas dans le suivant dès la session d'après.
- « jamais » clôt une question pour de bon.

Les sessions se comptent par question (une session dans le repo où elle se pose) et pour le poste.
État : `~/.local/state/kiln/rappels.json`. Réponses, données par Claude après la question :
`python3 relances.py oui|non|jamais <genre> <clé>`.
"""

import json
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
STATE_PATH = STATE_DIR / "kiln" / "rappels.json"
SCRIPT = f'python3 "{Path(__file__).resolve()}"'

NEUTRAL = 0.5
ANSWERS = ("oui", "non", "jamais")
# « jamais » pèse comme deux « non ».
NEVER_WEIGHT = 2


@dataclass(frozen=True)
class Kind:
    premier: int
    delais: tuple[int, ...]
    poids: float
    espacement: int = 0


KINDS = {
    "maj": Kind(premier=0, delais=(5, 10, 30, 50), poids=0.05),
    # Une adoption ne se propose qu'à partir de la 3e session dans un repo (on y travaille
    # vraiment), puis au plus une fois toutes les 10 sessions du poste, tous repos confondus.
    "adoption": Kind(premier=3, delais=(20, 50, 100), poids=0.15, espacement=10),
}

State = dict[str, Any]
Question = dict[str, Any]


def load() -> State:
    try:
        loaded = json.loads(STATE_PATH.read_text())
    except OSError, ValueError:
        loaded = {}
    return migrate(loaded if isinstance(loaded, dict) else {})


def migrate(state: State) -> State:
    """Avant les genres, l'état n'avait que les questions de mise à jour, à la racine."""
    if "questions" in state:
        return state
    return {
        "bienveillance": NEUTRAL,
        "sessions": 0,
        "dernieres": {},
        "questions": {
            f"maj:{key}": entry
            for key, entry in state.items()
            if isinstance(entry, dict) and {"sessions", "refus", "prochaine"} <= entry.keys()
        },
    }


def save(state: State) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def goodwill(state: State) -> float:
    return float(state.get("bienveillance", NEUTRAL))


def scaled(state: State, sessions: int) -> int:
    """Un délai étiré par la méfiance, raccourci par la bienveillance."""
    return math.ceil(sessions * 2 ** (1 - 2 * goodwill(state)))


def question(state: State, kind: str, key: str) -> Question:
    questions = state.setdefault("questions", {})
    if f"{kind}:{key}" not in questions:
        questions[f"{kind}:{key}"] = {
            "sessions": 0,
            "refus": 0,
            "prochaine": scaled(state, KINDS[kind].premier),
        }
    entry: Question = questions[f"{kind}:{key}"]
    return entry


def count_station_session(state: State) -> None:
    """Une session de plus sur le poste ; une fois par ouverture de session."""
    state["sessions"] = int(state.get("sessions", 0)) + 1


def count_session(state: State, kind: str, key: str) -> Question:
    """Une session de plus là où la question se pose ; une fois par ouverture de session."""
    entry = question(state, kind, key)
    entry["sessions"] += 1
    return entry


def is_due(state: State, kind: str, key: str) -> bool:
    entry = question(state, kind, key)
    if entry.get("jamais") or entry["sessions"] < entry["prochaine"]:
        return False
    last = state.get("dernieres", {}).get(kind)
    spacing = scaled(state, KINDS[kind].espacement)
    return last is None or int(state.get("sessions", 0)) - last >= spacing


def mark_asked(state: State, kind: str) -> None:
    """La question d'un genre vient d'être posée : point de départ de son espacement."""
    state.setdefault("dernieres", {})[kind] = int(state.get("sessions", 0))


def is_long_refusal(state: State, kind: str, key: str) -> bool:
    return int(question(state, kind, key)["refus"]) >= len(KINDS[kind].delais)


def record(state: State, kind: str, key: str, verdict: str) -> None:
    rules = KINDS[kind]
    entry = question(state, kind, key)
    if verdict == "oui":
        shift = rules.poids
        entry["refus"] = 0
        entry["prochaine"] = 0
    else:
        shift = -rules.poids * (NEVER_WEIGHT if verdict == "jamais" else 1)
        entry["refus"] += 1
        if verdict == "jamais":
            entry["jamais"] = True
    state["bienveillance"] = round(min(1.0, max(0.0, goodwill(state) + shift)), 4)
    if verdict == "non":
        # La note vient de baisser : le délai qui suit en tient déjà compte.
        delay = rules.delais[min(entry["refus"], len(rules.delais)) - 1]
        entry["prochaine"] = entry["sessions"] + scaled(state, delay)


def main(arguments: list[str]) -> None:
    if len(arguments) != 3 or arguments[0] not in ANSWERS or arguments[1] not in KINDS:
        sys.exit(f"usage : relances.py {'|'.join(ANSWERS)} {'|'.join(KINDS)} <clé>")
    verdict, kind, key = arguments
    state = load()
    record(state, kind, key, verdict)
    save(state)


if __name__ == "__main__":
    main(sys.argv[1:])
