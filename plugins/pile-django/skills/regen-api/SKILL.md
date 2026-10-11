---
name: regen-api
description: Régénérer openapi.json et les types du front après une modification d'une route ou d'un schéma de l'API Django (django-ninja). À utiliser dès qu'un schéma ou une route change.
---

Paramètres du repo : !`env | grep -E '^PROJET_(BACK|FRONT|ENV_TEST)=' | sort`

Depuis la racine du dépôt (ou du worktree courant) :
1. `cd $PROJET_BACK && set -a && . ../$PROJET_ENV_TEST && set +a && uv run python manage.py export_openapi --output ../openapi.json`
2. `cd $PROJET_FRONT && pnpm generate:api` (régénère les types et les contraintes du front).
3. Montrer `git diff --stat openapi.json $PROJET_FRONT` et signaler les routes ajoutées ou
   supprimées. Commiter ces fichiers avec la modification du backend : la CI échoue sinon.
