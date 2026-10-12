---
name: deployer
description: Déployer le projet en production avec les scripts du repo (scripts/ops/), après avoir vérifié que la CI de la branche d'intégration est verte.
disable-model-invocation: true
argument-hint: "[back|front|tout] [rebuild]"
---

Déploiement demandé : `$ARGUMENTS` (par défaut : back puis front).
Paramètres du repo : !`env | grep -E '^PROJET_(NOM|VPS|SITE|API_SANTE|DOC_PROD)' | sort`
Scripts disponibles : !`ls scripts/ops/ 2>/dev/null | tr '\n' ' '`

**Particularités du projet** (options, pièges, étapes en plus) : la section « Particularités »
de `$PROJET_DOC_PROD`, à lire en entier avant de commencer ; elle prime sur ce qui suit.

1. La branche d'intégration est poussée et la CI de son dernier commit est verte : verdict de
   `kiln ci` (`kiln ci --statut <intégration>`, pour un repo dont la CI GitHub ne tourne pas) ou
   CI GitHub (`gh run list -b <intégration> -L 3`). Jamais rejoué : lancer `kiln ci <intégration>`
   (une vingtaine de minutes) et attendre son verdict. Rouge : montrer le job en échec et s'arrêter.
2. **Back** : `scripts/ops/deploy-backend.sh`. Les déploiements **migrent** et gardent les
   données ; une reconstruction de la base seulement si l'argument `rebuild` est donné.
   Ensuite `scripts/ops/smoke-test.sh` s'il existe.
3. **Front** : `scripts/ops/deploy-frontend.sh`, sans fichier non suivi dans le dossier du front.
4. Résumer : commit déployé, résultat de la sonde de santé (`curl -s -o /dev/null -w '%{http_code}' $PROJET_API_SANTE`)
   et du smoke test. En cas de problème : skill `vps-podman:prod-logs`.
