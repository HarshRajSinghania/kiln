#!/usr/bin/env bash
# MCP Stripe du repo courant, en mode test seulement : toute clé live est refusée, pour que
# l'agent ne touche jamais aux vrais paiements. Clé : STRIPE_MCP_TEST_KEY, sinon .stripe/token
# à la racine de l'arbre principal (clé restreinte rk_test_… créée sur le tableau de bord).
set -euo pipefail
key="${STRIPE_MCP_TEST_KEY:-}"
root="$(cd "$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd || pwd)"
if [[ -z "$key" && -s "$root/.stripe/token" ]]; then
  key="$(tr -d '[:space:]' < "$root/.stripe/token")"
fi
if [[ -z "$key" ]]; then
  echo "stripe_mcp: ni STRIPE_MCP_TEST_KEY ni .stripe/token (clé rk_test_… attendue)" >&2
  exit 1
fi
if [[ "$key" != rk_test_* && "$key" != sk_test_* ]]; then
  echo "stripe_mcp: clé refusée, seul le mode test est admis" >&2
  exit 1
fi
STRIPE_SECRET_KEY="$key" exec npx -y @stripe/mcp@0.3.3
