# shellcheck shell=bash
# Refuse de déployer un commit dont la CI n'est pas verte : un commit aux tests en échec pouvait
# partir en production. SAUTER_CI=1 passe outre, en cas d'urgence.
#
# Usage : . "$DOTFILES_OUTILS/ops/lib/ci-verte.sh" ; ci_verte <sha>
# Réglages : CI_WORKFLOW (défaut ci.yml), SAUTER_CI=1
ci_verte() {
  local sha="$1" runs conclusion
  if [ "${SAUTER_CI:-0}" = 1 ]; then
    echo "ATTENTION : vérification de la CI ignorée (SAUTER_CI=1)." >&2
    return 0
  fi
  if ! command -v gh > /dev/null; then
    echo "gh absent : impossible de vérifier la CI de ${sha:0:8} (SAUTER_CI=1 pour passer outre)." >&2
    return 1
  fi
  runs="$(gh run list --commit "$sha" --workflow "${CI_WORKFLOW:-ci.yml}" --json status,conclusion --limit 1)"
  conclusion="$(python3 -c '
import json, sys
runs = json.load(sys.stdin)
print((runs[0]["conclusion"] or runs[0]["status"]) if runs else "aucune exécution")
' <<< "$runs")"
  if [ "$conclusion" != success ]; then
    echo "CI de ${sha:0:8} : $conclusion. Attendre une CI verte, ou SAUTER_CI=1 en cas d'urgence." >&2
    return 1
  fi
  echo "CI verte pour ${sha:0:8}."
}
