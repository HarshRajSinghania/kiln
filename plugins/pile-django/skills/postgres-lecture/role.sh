#!/usr/bin/env bash
# Crée (ou répare) le rôle <PROJET_NOM>_mcp_lecture du MCP postgres dans le conteneur de test.
# Lecture seule garantie par la base, pas par l'outil : pg_read_all_data, aucun droit
# d'écriture, transactions en lecture seule par défaut.
set -euo pipefail
: "${PROJET_NOM:?PROJET_NOM manque dans .claude/settings.json (env)}"
container="${PROJET_PG_CONTENEUR:-$PROJET_NOM-test-pg}"
role="${PROJET_NOM}_mcp_lecture"
podman exec -i "$container" psql -v ON_ERROR_STOP=1 -U "${PROJET_PG_UTILISATEUR:-$PROJET_NOM}" -d postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$role') THEN
    CREATE ROLE $role LOGIN PASSWORD '$role';
  END IF;
END
\$\$;
ALTER ROLE $role NOSUPERUSER NOCREATEDB NOCREATEROLE;
ALTER ROLE $role SET default_transaction_read_only = on;
GRANT pg_read_all_data, pg_monitor TO $role;
SQL
echo "postgres_mcp_role_ready container=$container role=$role"
