---
name: fusion
description: Terminer un chantier - fusionner la branche dans la branche d'intégration (develop), pousser, supprimer la branche (et son worktree). Sans CI : elle ne tourne qu'à la mise en version (base:version).
argument-hint: "[branche]"
---

Branche : `$ARGUMENTS`, sinon la branche courante. Branche d'intégration : celle que nomme le
`CLAUDE.md` du projet, sinon `develop` si elle existe, sinon la branche par défaut d'`origin`.

La fusion se fait ici, directement : ni pull request ni approbation à attendre ([PAS-SUR-MAIN]).
Une PR déjà ouverte pour la branche passe d'elle-même à « Merged » sur GitHub au push du 4.

1. Sur la branche : tout est commité (`git status --porcelain` vide), sinon s'arrêter et le dire.
2. Mettre à jour l'intégration (`git pull --ff-only origin <intégration>`) puis
   `git merge --no-ff <branche> -m "Merge branch '<branche>' into <intégration>"`, depuis
   l'arbre principal s'il est sur l'intégration, sinon `git -C` sur un worktree qui l'est ;
   ne jamais changer la branche de l'arbre principal sous une autre session.
3. En cas de conflit : s'arrêter, montrer les fichiers en conflit, proposer une résolution.
4. `git push origin <intégration>`.
5. Supprimer aussitôt le worktree et les branches : une branche fusionnée ne se garde pas de côté.
   Seulement si la fusion est réellement dans `origin/<intégration>` :
   - `git fetch -q origin` puis `git merge-base --is-ancestor <branche> origin/<intégration>`
     réussit : chaque commit de la branche, donc chacun de ses fichiers, est dans
     l'intégration publiée ;
   - le worktree est propre (`git -C <wt> status --porcelain` vide).
   Alors `git worktree remove .claude/worktrees/<nom>` (jamais `--force`),
   `git branch -d <branche>` (jamais `-D`) et, si elle existe sur GitHub
   (`git ls-remote --heads origin <branche>`), `git push origin --delete <branche>`. Si une
   vérification échoue : ne rien supprimer, dire laquelle et pourquoi.
6. Pas de CI après la fusion : `kiln ci` ne tourne qu'au passage d'une version dans `main`
   (`base:version`), seul état qui se déploie. Sur un repo sans `main` de production (la
   branche d'intégration se déploie elle-même), la CI de GitHub suit le push. Le typage a
   tourné avant le push (crochet pre-push) : s'il échoue, corriger sur la branche.
7. Résumer : commit de fusion, fichiers touchés.
