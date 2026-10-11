# shellcheck shell=bash
# Briques d'un test de fumée après déploiement : chaque contrôle affiche ✓ ou ✗ sans arrêter
# les suivants, et `fumee_bilan` sort en erreur si l'un a échoué.
#
# Usage : . "$DOTFILES_OUTILS/ops/lib/fumee.sh"
#         controle "sonde en état ok" json_vrai "$API/health/" "data['status'] == 'ok'"
#         fumee_bilan
fumee_echecs=0

controle() {  # controle <intitulé> <commande…>
  local intitule="$1" sortie
  shift
  if sortie="$("$@" 2>&1)"; then
    echo "  ✓ $intitule"
  else
    echo "  ✗ $intitule : ${sortie:-échec}" >&2
    fumee_echecs=$((fumee_echecs + 1))
  fi
}

lire() {  # lire <url> [options curl…] — corps en sortie, non nul si le statut n'est pas 2xx
  curl -fsS --max-time 15 "$@"
}

json_vrai() {  # json_vrai <url> <expression python sur `data`>
  local url="$1" expression="$2" corps
  corps="$(lire "$url")" || return 1
  python3 -c "
import json, sys
data = json.loads(sys.argv[1])
value = $expression
if not value:
    raise SystemExit(f'valeur inattendue : {value!r}')
" "$corps"
}

cors_ouvert() {  # cors_ouvert <url de l'API> <origine du site>
  local entetes
  entetes="$(curl -fsS --max-time 15 -D - -o /dev/null -X OPTIONS \
    -H "Origin: $2" -H 'Access-Control-Request-Method: GET' "$1")" || return 1
  grep -qi "^access-control-allow-origin: $2" <<< "$entetes"
}

fumee_bilan() {
  if [ "$fumee_echecs" -gt 0 ]; then
    echo "Test de fumée : $fumee_echecs contrôle(s) en échec." >&2
    return 1
  fi
  echo "Test de fumée : tout répond."
}
