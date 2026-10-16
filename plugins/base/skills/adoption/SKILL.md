---
name: adoption
description: Faire suivre kiln à un repo qu'il n'a pas généré (kiln adopt) - charte vérifiée après chaque édition, suivi docs/backlog/, repo visible dans kiln status - sur une branche fusionnée ensuite dans la branche d'intégration. À utiliser quand l'utilisateur accepte l'adoption proposée en début de session, ou demande d'adopter kiln dans un repo existant.
---

`<relances>` désigne `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/relances.py"` (réponses aux
questions de kiln).

1. Le repo ouvert ne suit pas encore kiln : ni `.copier-answers.yml` (généré : skill
   `base:maj-kiln`), ni `charte.toml` (déjà adopté) ; sinon le dire et s'arrêter. La commande
   `kiln` est installée (`kiln --version`) ; sinon donner `uv tool install kiln-cli` et s'arrêter.
2. Demander l'envergure avec l'outil AskUserQuestion : `spark` (script, outil perso), `ember`
   (petite app, peu d'enjeu, par défaut), `flame` (production, vrais utilisateurs), `blaze`
   (plusieurs équipes, gros enjeux).
3. Branche `chore/kiln-adopt` dans un worktree (skill `base:worktree`), puis
   `kiln adopt --size <envergure>` dans ce worktree. Elle pose `charte.toml` (règles valables
   partout) et `docs/backlog/` (gardé s'il existe), sans toucher au code.
4. Le passif que la charte relève (un `Dockerfile`, un `pip install`…) : le montrer et laisser
   choisir, règle par règle, entre corriger maintenant, retirer la règle de `charte.toml`, ou
   noter la correction en ticket (skill `base:backlog`). Ne rien corriger sans accord.
5. Commiter (`chore: adoption de kiln`), puis fusionner (skill `base:fusion`).
6. `<relances> oui adoption "<racine de l'arbre principal du repo>"`.

## Résumer

Fichiers ajoutés, envergure, passif relevé et ce qui en a été fait. Ce que l'adoption n'apporte
pas encore : le modèle complet (CI, pre-commit, CLAUDE.md), qui suppose l'arborescence de
`kiln new` ; `kiln update` ne touche pas un repo adopté.
