# shellcheck shell=bash
# Refuse de déployer un commit dont la CI n'est pas verte : un commit aux tests en échec pouvait
# partir en production. Deux verdicts font foi, le premier vert suffit :
# - celui de `kiln ci <sha>`, la CI du ci.yml rejouée sur un poste (note git refs/notes/ci,
#   poussée sur origin) : seul verdict d'un repo dont la CI GitHub ne tourne pas ;
# - celui de la CI GitHub (workflow CI_WORKFLOW).
# Le commit de version de `main` (fusion --no-ff de `release/vN`, skill `base:version`) porte
# exactement les fichiers de la release : le verdict vert de celle-ci vaut pour lui.
# SAUTER_CI=1 passe outre, en cas d'urgence.
#
# Usage : . scripts/ops/lib/ci-verte.sh ; ci_verte <sha>
# Réglages : CI_WORKFLOW (défaut ci.yml), SAUTER_CI=1
ci_verte() {
  local sha="$1" note runs conclusion release
  if [ "${SAUTER_CI:-0}" = 1 ]; then
    echo "ATTENTION : vérification de la CI ignorée (SAUTER_CI=1)." >&2
    return 0
  fi
  note="$(verdict_kiln_ci "$sha")"
  if [ "${note%%$'\n'*}" != "kiln ci : succès" ] && release="$(release_identique "$sha")"; then
    note="$(verdict_kiln_ci "$release")"
    [ "${note%%$'\n'*}" = "kiln ci : succès" ] && echo "Fusion de version : mêmes fichiers que la release ${release:0:8}."
  fi
  if [ "${note%%$'\n'*}" = "kiln ci : succès" ]; then
    echo "CI rejouée par kiln ci, verte pour ${sha:0:8} :"
    sed -n '2,$s/^/  /p' <<< "$note"
    return 0
  fi
  if command -v gh > /dev/null; then
    runs="$(gh run list --commit "$sha" --workflow "${CI_WORKFLOW:-ci.yml}" --json status,conclusion --limit 1 2> /dev/null || echo '[]')"
    conclusion="$(python3 -c '
import json, sys
runs = json.load(sys.stdin)
print((runs[0]["conclusion"] or runs[0]["status"]) if runs else "aucune exécution")
' <<< "$runs")"
  else
    conclusion="gh absent"
  fi
  if [ "$conclusion" = success ]; then
    echo "CI GitHub verte pour ${sha:0:8}."
    return 0
  fi
  echo "CI de ${sha:0:8} : GitHub « $conclusion », kiln ci « ${note%%$'\n'*} »." >&2
  [ -n "$note" ] && sed -n '2,$s/^/  /p' <<< "$note" >&2
  echo "Lancer \`kiln ci ${sha:0:12}\` (la CI rejouée sur ce poste), ou SAUTER_CI=1 en cas d'urgence." >&2
  return 1
}

# Note de `kiln ci` sur le commit : celle d'origin si elle dit succès, sinon la locale, sinon
# « jamais rejoué ».
verdict_kiln_ci() {
  local sha="$1" ref note
  git fetch -q origin "+refs/notes/ci:refs/notes/ci-origin" 2> /dev/null || true
  for ref in ci-origin ci; do
    note="$(git notes --ref="$ref" show "$sha" 2> /dev/null || true)"
    if [ "${note%%$'\n'*}" = "kiln ci : succès" ]; then
      printf '%s\n' "$note"
      return 0
    fi
  done
  note="$(git notes --ref=ci show "$sha" 2> /dev/null || git notes --ref=ci-origin show "$sha" 2> /dev/null || echo "jamais rejoué")"
  printf '%s\n' "$note"
}

# Second parent d'un commit de fusion qui n'apporte rien d'autre que lui (même arbre) ; échoue
# sinon. C'est la fusion d'une release dans `main`.
release_identique() {
  local sha="$1" parent
  parent="$(git rev-parse -q --verify "$sha^2" 2> /dev/null)" || return 1
  [ "$(git rev-parse "$sha^{tree}")" = "$(git rev-parse "$parent^{tree}")" ] || return 1
  printf '%s\n' "$parent"
}
