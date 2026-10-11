---
name: migration
description: Modifier le schéma de la base Django - une nouvelle migration numérotée par changement, jamais de réécriture d'une migration fusionnée. À utiliser dès qu'un modèle change.
---

Paramètres du repo : !`env | grep -E '^PROJET_(BACK|ENV_TEST|CHARTE)=' | sort`
Règles propres au repo : celles de sa charte (`CLAUDE.md` du back), qui priment sur celles-ci.

Chaque changement de modèle arrive avec sa migration numérotée, appliquée au déploiement sans
vider la base. Environnement : `set -a && . ../$PROJET_ENV_TEST && set +a` depuis `$PROJET_BACK/`.

1. Modifier le modèle.
2. Dans `$PROJET_BACK/` : `uv run python manage.py makemigrations <app> --name <nom_parlant>`
   (en anglais, snake_case : `riding_profile`, `station_photo`). Le fichier prend le numéro
   suivant de l'app.
3. **Ne jamais modifier ni supprimer une migration déjà fusionnée dans la branche
   d'intégration** : la prod l'a peut-être appliquée. Une erreur se corrige par une nouvelle
   migration. Une migration encore seulement sur la branche peut être régénérée.
4. Données de départ ou reprise de données : migration de données (`RunPython`) avec sa
   fonction de retour arrière, dans un fichier séparé du changement de schéma.
5. Colonne retirée ou renommée alors que le code déployé la lit encore : deux livraisons (le
   code cesse de la lire, puis la migration la retire).
6. Vérifier : `uv run python manage.py makemigrations --check --dry-run` (rien à générer),
   `uv run python manage.py migrate` sur la base locale, puis la charte
   (`python3 $PROJET_CHARTE` depuis la racine) si le repo en a une.
7. Si un schéma d'API change aussi : skill `pile-django:regen-api`.
