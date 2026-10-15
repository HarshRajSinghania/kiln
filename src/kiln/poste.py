"""`kiln set` hors d'un repo (ou `kiln set --poste`) : les réglages du poste.

Ils vivent dans `~/.config/kiln/config.toml` : système, propriétaire GitHub et équipe par défaut
de `kiln new`, dossier des repos de `kiln status` et `kiln update --all`.
"""

from dataclasses import replace
from pathlib import Path

from kiln import ui
from kiln.config import CHANNELS, SYSTEMS, UserConfig, config_path, load_config, save_config
from kiln.shell import KilnError

POSTE_KEYS = ("systeme", "proprietaire", "equipe", "dossier_code", "canal")


def show_poste(config: UserConfig) -> None:
    values = {
        "systeme": config.system or "(demandé au premier kiln install)",
        "proprietaire": config.owner or "(aucun)",
        "equipe": ", ".join(config.team) or "(aucune)",
        "dossier_code": str(config.code_dir),
        "canal": f"{config.channel} (public : versions promues ; interne : candidates comprises)",
    }
    width = max(len(key) for key in POSTE_KEYS)
    print(ui.paint(f"Réglages du poste ({config_path()})", bold=True))
    for key in POSTE_KEYS:
        print(f"{ui.paint(f'{key:<{width}}', ui.STONE)}  {values[key]}")
    print()
    ui.note("Changer : kiln set clé=valeur [clé=valeur…] (ex. kiln set equipe=alice,bob).")
    ui.note("Paramètres d'un repo : se placer dans le repo, puis kiln set.")


def apply_poste(config: UserConfig, assignments: list[str]) -> UserConfig:
    """Nouvelle configuration du poste, une fois chaque `clé=valeur` vérifiée."""
    updated = config
    for assignment in assignments:
        key, separator, value = assignment.partition("=")
        value = value.strip()
        if not separator or key not in POSTE_KEYS:
            raise KilnError(
                f"« {assignment} » : attendu clé=valeur, clés du poste : {', '.join(POSTE_KEYS)}"
            )
        if key == "systeme":
            if value not in SYSTEMS:
                raise KilnError(f"systeme : {', '.join(SYSTEMS)}")
            updated = replace(updated, system=value)
        elif key == "proprietaire":
            updated = replace(updated, owner=value or None)
        elif key == "equipe":
            team = tuple(login.strip() for login in value.strip("[]").split(",") if login.strip())
            updated = replace(updated, team=team)
        elif key == "canal":
            if value not in CHANNELS:
                raise KilnError(f"canal : {', '.join(CHANNELS)}")
            updated = replace(updated, channel=value)
        else:
            updated = replace(updated, code_dir=Path(value).expanduser())
    return updated


def run_poste(assignments: list[str]) -> None:
    config = load_config()
    if assignments:
        config = apply_poste(config, assignments)
        save_config(config)
    show_poste(config)
