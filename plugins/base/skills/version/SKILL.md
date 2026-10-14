---
name: version
description: Sortir une version - branche release/vN tirée de develop, contrôle complet (CI, migrations, contrat, réglages), annonce de la version (fenêtre de nouveautés, e-mail), fusion dans main taguée vN, déploiement, reversement dans develop. À utiliser quand l'utilisateur demande de sortir, livrer ou mettre en production une version, ou un correctif urgent de la prod.
argument-hint: "[vN] [commit de develop]"
---

Une version est le seul état qui part en production : `develop` intègre sans CI complète
(`base:fusion`), la version fait tout le contrôle. Modèle Git Flow : une branche
`release/vN` tirée de `develop` ne reçoit plus que des correctifs, puis se fusionne dans `main`
(tag `vN`) et se reverse dans `develop`. Un correctif urgent de la prod suit le même chemin
depuis le dernier tag de `main`, sur `hotfix/vN.M`.

Le `CLAUDE.md` du projet (règle `[VERSIONS]` ou section « Versions ») dit ce qui lui est propre :
l'annonce de la version (fichier des nouveautés, e-mail), les commandes de déploiement, les
contrôles en plus. Le lire d'abord. S'arrêter si le repo n'a pas de `main` de production.

Ne jamais changer la branche de l'arbre principal : chaque branche dans
`.claude/worktrees/<nom>` (`release-vN`, `main`).

## 1. Choisir
- `git fetch origin --tags`. Version précédente : `git describe --tags --abbrev=0 origin/main`.
- Commit candidat : l'argument, sinon `origin/develop`. Pour un correctif urgent : le dernier
  tag, plus les seuls commits du correctif (`git cherry-pick`).
- Numéro : l'argument, sinon `vN+1` s'il y a des nouveautés (`feat`), `vN.M+1` si ce ne sont
  que des correctifs.
- Changements : `git log --first-parent --format='%h %s' <précédente>..<candidat>`. Si
  l'utilisateur écarte un chantier, prendre un candidat plus ancien plutôt que de défaire du
  code sur la release.

## 2. Tirer la release
`git worktree add .claude/worktrees/release-vN -b release/vN <candidat>`, puis
`git push -u origin release/vN`. Dès lors, rien d'autre que des correctifs n'y entre (commits
`fix:`), jamais une fonctionnalité.

## 3. Inventaire des risques (entre la version précédente et la release)
- **Migrations** ajoutées (`*/migrations/`) : schéma, données, réversibles ou non. Le
  déploiement les applique après une sauvegarde ; une migration irréversible se signale.
- **Réglages** : variables d'environnement nouvelles (`config(`, `runtimeConfig`,
  `.env.example`) ; vérifier qu'elles existent en production avant de déployer.
- **Contrat d'API** : routes ou champs retirés ou renommés dans `openapi.json` ; un front
  encore en cache appelle l'ancien contrat. Déployer l'API d'abord, le front ensuite.
- **Drapeaux** : les fonctionnalités livrées éteintes, et leur état prévu en production.
- **Dépendances** ajoutées ou montées de version majeure.

## 4. Annonce
Ce que le `CLAUDE.md` du projet demande pour annoncer une version (fenêtre de nouveautés,
e-mail aux utilisateurs…). Vérifier qu'elle existe pour `vN`, qu'elle décrit ce que l'inventaire
a trouvé, et qu'elle ne promet ni un chantier écarté ni une fonctionnalité derrière un drapeau
éteint. Sinon, la rédiger sur la release et **faire valider le texte** par l'utilisateur.

## 5. Contrôle complet
`kiln ci release/vN` (ou la CI GitHub de la branche) : tous les jobs. En cas d'échec, corriger
sur la release, commiter, relancer, jusqu'au vert. Donner aussi les jobs non rejoués.

## 6. Feu vert
Présenter à l'utilisateur, en court : numéro, changements, risques, annonce, verdict de CI,
plan de retour arrière (version précédente). Attendre son accord : c'est la production.

## 7. Fusionner et taguer
```bash
git worktree add .claude/worktrees/main main
git -C .claude/worktrees/main merge --no-ff release/vN -m "Version vN : <résumé>"
git -C .claude/worktrees/main tag -a vN -m "Version vN du site" -m "<changements, une ligne chacun>"
git push origin main vN && git worktree remove .claude/worktrees/main
```
Le commit de `main` a les fichiers de la release : le script de déploiement accepte le verdict
de `kiln ci` de celle-ci (`ci-verte.sh`), sans rejouer la CI.

## 8. Déployer
Les commandes du projet (souvent `scripts/ops/deploy-backend.sh --dry-run`, puis sans, puis
`deploy-frontend.sh`), l'API avant le front. Puis vérifier : test de fumée du script, journaux
de production quelques minutes (skill de diagnostic du projet s'il y en a), l'annonce visible.
En cas de casse : retour à la version précédente par la procédure du projet, et le dire.

## 9. Reverser et ranger
```bash
git merge --no-ff release/vN -m "Merge branch 'release/vN' into develop"   # depuis develop
git push origin develop
git worktree remove .claude/worktrees/release-vN
git branch -d release/vN && git push origin --delete release/vN
```
Résumer : tag, commit déployé, migrations appliquées, annonce, correctifs faits sur la release,
commande de retour arrière.
