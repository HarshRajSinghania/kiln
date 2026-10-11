---
name: postgres-lecture
description: Préparer ou réparer l'accès du MCP postgres (lecture seule) à la base de test locale. À utiliser quand le serveur MCP postgres échoue à se connecter, ou après la recréation du conteneur de test.
---

Le MCP `postgres` de ce plugin vise `127.0.0.1:$PROJET_PG_PORT`, base `$PROJET_PG_BASE`, avec le
rôle `<PROJET_NOM>_mcp_lecture`. Paramètres du repo : !`env | grep -E '^PROJET_(NOM|PG_)' | sort`

1. Le conteneur `$PROJET_PG_CONTENEUR` tourne-t-il ? (`podman ps`) Sinon `podman start` dessus.
2. Créer ou réparer le rôle : `bash "${CLAUDE_SKILL_DIR}/role.sh"`. Il n'a que
   `pg_read_all_data` et `pg_monitor` : la lecture seule tient aux droits, pas à l'outil.
3. Recharger le serveur MCP (`/mcp`) et vérifier par une requête simple.
