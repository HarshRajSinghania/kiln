---
name: prod-dump
description: Restaurer une copie de la base de prod dans un PostgreSQL jetable local, pour tester une migration, une requête ou un script sur de vraies données sans toucher la prod.
disable-model-invocation: true
argument-hint: "[nom de sauvegarde, par défaut la plus récente]"
---

Paramètres du repo : !`env | grep -E '^PROJET_(NOM|VPS|PG_)' | sort`
Sauvegardes : `$PROJET_VPS`, dossier `$PROJET_VPS_SAUVEGARDES`, fichiers `.dump`. Ne jamais
écrire sur le serveur.

1. Lister : `ssh $PROJET_VPS "ls -t $PROJET_VPS_SAUVEGARDES/*.dump | head -5"` ; prendre
   `$ARGUMENTS` ou la plus récente.
2. Rapatrier dans le scratchpad de session (jamais dans le dépôt : données personnelles) :
   `scp $PROJET_VPS:$PROJET_VPS_SAUVEGARDES/<fichier> <scratchpad>/`.
3. Base jetable, distincte de la base de test (port 55433, pas `$PROJET_PG_PORT`) :
   `podman run -d --rm --name $PROJET_NOM-prod-copy -e POSTGRES_USER=$PROJET_PG_UTILISATEUR -e POSTGRES_PASSWORD=copy -e POSTGRES_DB=$PROJET_PG_BASE -p 127.0.0.1:55433:5432 ${PROJET_PG_IMAGE:-postgres:18}`
   puis attendre `pg_isready`, et
   `podman exec -i $PROJET_NOM-prod-copy pg_restore -U $PROJET_PG_UTILISATEUR -d $PROJET_PG_BASE --no-owner --no-acl < <fichier>`.
4. `DATABASE_URL=postgres://$PROJET_PG_UTILISATEUR:copy@localhost:55433/$PROJET_PG_BASE` pour les
   commandes du back (migration, requêtes, `check`).
5. À la fin : `podman stop $PROJET_NOM-prod-copy` (conteneur `--rm`, il disparaît) et supprimer
   le dump du scratchpad. Ne jamais recopier de données de cette base dans un commit, un log ou
   une réponse (noms, e-mails).
