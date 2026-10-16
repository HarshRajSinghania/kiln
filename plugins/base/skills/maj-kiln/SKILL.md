---
name: maj-kiln
description: Mettre kiln à jour - l'outil kiln du poste et ses plugins, puis le repo ouvert (kiln update, sur une branche fusionnée aussitôt dans develop). À utiliser quand l'utilisateur demande de mettre kiln à jour, ou quand il accepte la mise à jour proposée en début de session.
argument-hint: "[outil|depot]"
---

Portée : `$ARGUMENTS` ; `outil` seul, `depot` seul, sinon les deux, l'outil d'abord.
`<hook>` désigne `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/kiln-a-jour.py"`.

## Outil

1. `<hook> outil` affiche `à jour`, ou la commande qui met à jour l'outil installé (depuis
   PyPI ou GitHub : `uv tool install --force kiln-cli==…` ou `…git+…@<tag>`, précédé de
   `uv tool uninstall kiln` si l'outil porte encore son ancien nom, la marketplace kiln et le plugin `base` installé pour tous
   les repos du poste ; depuis un dossier : `git pull` de ce dossier et réinstallation). La lancer telle quelle ; si elle échoue (dossier kiln
   modifié, pas de réseau), s'arrêter et dire pourquoi.
2. `<hook> accord outil`, puis dire de taper `/reload-plugins` : les skills et les hooks du
   plugin ne changent qu'au rechargement.

## Dépôt

1. Le repo ouvert est généré par kiln (`.copier-answers.yml` à sa racine, `_src_path` vers
   `antoine-tena/kiln`) ; sinon le dire et s'arrêter.
2. Branche `chore/kiln-update` dans un worktree (skill `base:worktree`), puis `kiln update` dans
   ce worktree : modèle, dépendances compatibles, contrôles.
3. Des marqueurs de conflit (`<<<<<<< before updating`) : s'arrêter, montrer les fichiers, proposer
   une résolution. Des contrôles en échec : le dire, ne pas fusionner.
4. Relire le diff, commiter en lots de 10 fichiers au plus (`chore: mise à jour kiln`, titre de
   50 caractères au plus), puis fusionner dans `develop` (skill `base:fusion`), sans PR ni
   approbation à attendre.
5. `<hook> accord "<racine du repo>"`.

## Résumer

Version de l'outil avant et après, commit du modèle avant et après (`_commit` de
`.copier-answers.yml`), fichiers changés, contrôles.
