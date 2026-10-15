"""Status line de Claude Code : le style choisi pour le poste et les réglages propres au repo.

Le style (`kiln set statusline=…`, clé du poste) est lu par le script du plugin `base` à chaque
affichage ; kiln ne touche à la `statusLine` de `~/.claude/settings.json` que pour y poser son
script ou l'en retirer, jamais avec `perso`. Les réglages du repo vivent dans les réponses de
kiln (`statusline_ci`, `url_sante_prod`), donc partagés par l'équipe, et sont posés en
`git config statusline.*` à chaque `kiln install`, `kiln new` et `kiln set`.
"""

import json
from dataclasses import replace
from pathlib import Path

from kiln.config import (
    DEFAULT_STATUSLINE,
    STATUSLINE_STYLES,
    UserConfig,
    config_path,
    save_config,
)
from kiln.shell import KilnError, run
from kiln.stack import answers_if_any

SCRIPT = Path("plugins") / "base" / "scripts" / "statusline.py"


def apply_statusline_settings(root: Path) -> None:
    answers = answers_if_any(root)
    show_ci = answers.get("statusline_ci", True) is not False
    run(["git", "config", "statusline.ci", "true" if show_ci else "false"], root)
    prod_url = str(answers.get("url_sante_prod") or "")
    if prod_url:
        run(["git", "config", "statusline.prod-url", prod_url], root)


def claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def kiln_script() -> Path:
    """Le script du plugin `base`, là où Claude Code a posé le catalogue kiln."""
    known = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
    try:
        location = json.loads(known.read_text())["kiln"]["installLocation"]
    except (OSError, ValueError, KeyError) as error:
        raise KilnError(
            "catalogue de plugins kiln absent : claude plugin marketplace add antoine-tena/kiln"
        ) from error
    script = Path(location) / SCRIPT
    if not script.exists():
        raise KilnError(f"script de status line introuvable : {script}")
    return script


def is_kiln_statusline(entry: object) -> bool:
    return isinstance(entry, dict) and SCRIPT.as_posix() in str(entry.get("command", ""))


def apply_statusline_choice(choice: str, settings_path: Path | None = None) -> str:
    """Accorde la `statusLine` de Claude Code au choix ; renvoie ce qui a été fait."""
    path = settings_path or claude_settings_path()
    if choice == "perso":
        return "statusLine de Claude Code laissée telle quelle (perso)."
    settings = json.loads(path.read_text()) if path.exists() else {}
    current = settings.get("statusLine")
    previous = "" if current is None or is_kiln_statusline(current) else f" (remplace : {current})"
    if choice == "aucune":
        if current is None:
            return "Aucune status line."
        del settings["statusLine"]
        message = f"statusLine retirée de {path}{previous}."
    elif choice in STATUSLINE_STYLES:
        if is_kiln_statusline(current):
            return f"Status line kiln, style {choice}."
        settings["statusLine"] = {"type": "command", "command": f'python3 "{kiln_script()}"'}
        message = f"Status line kiln, style {choice}, posée dans {path}{previous}."
    else:
        raise KilnError(f"statusline inconnue : {choice}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    return message


def ensure_statusline(config: UserConfig) -> UserConfig:
    """Au premier `kiln install` : le style par défaut, ou `perso` si l'utilisateur a déjà sa
    propre status line ; le choix est gardé dans la configuration du poste."""
    if config.statusline is not None:
        return config
    path = claude_settings_path()
    settings = json.loads(path.read_text()) if path.exists() else {}
    current = settings.get("statusLine")
    own = current is not None and not is_kiln_statusline(current)
    updated = replace(config, statusline="perso" if own else DEFAULT_STATUSLINE)
    print(apply_statusline_choice(str(updated.statusline)))
    save_config(updated)
    print(f"Choix enregistré dans {config_path()} (changer : kiln set statusline=…).")
    return updated
