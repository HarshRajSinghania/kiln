# shellcheck shell=bash
# Descripteur du serveur de production : un fichier JSON versionné et sans secret (adresse,
# branche, URL publiques), lu par `cible_vps <clé>` au lieu de recopier ces valeurs en dur dans
# chaque script. Les variables d'environnement des scripts restent prioritaires.
#
# Usage : . "$DOTFILES_OUTILS/ops/lib/cible-vps.sh" ; HOTE="${DEPLOY_HOST:-$(cible_vps host)}"
# Réglage : CIBLE_VPS (défaut <racine du repo>/config/vps/project.json)
cible_vps() {  # cible_vps <clé> — valeur du descripteur ; échoue si la clé est absente
  local fichier="${CIBLE_VPS:-$(git rev-parse --show-toplevel)/config/vps/project.json}"
  python3 -c '
import json, sys

path, key = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except OSError as error:
    sys.exit(f"Descripteur du serveur illisible ({path}) : {error}")
except ValueError as error:
    sys.exit(f"Descripteur du serveur mal formé ({path}) : {error}")
if key not in data:
    sys.exit(f"Clé « {key} » absente de {path}.")
print(data[key])
' "$fichier" "$1"
}
