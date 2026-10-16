---
name: prod-logs
description: Diagnostiquer la prod sur le VPS - état des conteneurs, logs ciblés, santé de l'API, système. Lecture seule. À utiliser quand le site ou l'API se comporte mal.
argument-hint: "[symptôme ou service]"
---

Symptôme : `$ARGUMENTS`.
Paramètres du repo : !`env | grep -E '^PROJET_(NOM|VPS|SITE|API_SANTE)' | sort`

**Lecture seule** : aucun `restart`, `rm`, `up`, aucune écriture sur le serveur ; ne jamais
afficher de secret (`.env`, `printenv`). Proposer les actions correctives sans les faire.

1. Santé publique : `curl -s -o /dev/null -w '%{http_code}' $PROJET_API_SANTE` et
   `curl -sI $PROJET_SITE | head -5` (503 `DEPLOYMENT_PAUSED` → Vercel en pause).
2. Conteneurs : `ssh $PROJET_VPS "podman ps -a --format '{{.Names}} {{.Status}}'"`. Un conteneur
   absent ou `Exited` après un redémarrage du serveur : vérifier
   `systemctl is-enabled podman-restart` et la politique `always`.
3. Logs ciblés des conteneurs `$PROJET_NOM-*` concernés par le symptôme :
   `ssh $PROJET_VPS 'podman logs --since 2h <conteneur> 2>&1 | grep -iE "error|exception|traceback|5[0-9]{2}" | tail -50'`.
   Proxy : `ssh $PROJET_VPS 'journalctl -u caddy --since "2 hours ago" | tail -50'`.
4. Système : `ssh $PROJET_VPS 'df -h / ; free -m ; uptime ; systemctl --failed'`.
5. Conclure : cause probable, preuve (lignes de log sans donnée personnelle), correction
   proposée ; `scripts/ops/smoke-test.sh` pour confirmer après correction.
