---
name: fusion
description: Terminer un chantier - fusionner la branche dans la branche d'intégration (develop), pousser, supprimer la branche (et son worktree). Sans CI : elle ne tourne qu'à la mise en version (base:version).
argument-hint: "[branche]"
---

Branche : `$ARGUMENTS`, sinon la branche courante. Branche d'intégration : celle que nomme le
`CLAUDE.md` du projet, sinon `develop` si elle existe, sinon la branche par défaut d'`origin`.

1. Sur la branche : tout est commité (`git status --porcelain` vide), sinon s'arrêter et le dire.
   Si le `CLAUDE.md` du projet exige une pull request avant la fusion (annway [PAS-SUR-MAIN],
   par exemple), ne pas fusionner en local : `git push -u origin <branche>`, puis
   `gh pr create --base <intégration> --fill`, donner le lien de la PR et s'arrêter là ; la
   fusion se fait sur GitHub une fois la CI verte, `base:nettoyage` supprime ensuite le worktree.
2. Mettre à jour l'intégration (`git pull --ff-only origin <intégration>`) puis
   `git merge --no-ff <branche> -m "Merge branch '<branche>' into <intégration>"`, depuis
   l'arbre principal s'il est sur l'intégration, sinon `git -C` sur un worktree qui l'est ;
   ne jamais changer la branche de l'arbre principal sous une autre session.
3. En cas de conflit : s'arrêter, montrer les fichiers en conflit, proposer une résolution.
4. `git push origin <intégration>`.
5. Si la branche avait un worktree : `git worktree remove .claude/worktrees/<nom>` ; puis
   `git branch -d <branche>`.
6. Pas de CI après la fusion : `kiln ci` ne tourne qu'au passage d'une version dans `main`
   (`base:version`), seul état qui se déploie. Sur un repo sans `main` de production (la
   branche d'intégration se déploie elle-même), la CI de GitHub suit le push. Le typage a
   tourné avant le push (crochet pre-push) : s'il échoue, corriger sur la branche.
7. Résumer : commit de fusion, fichiers touchés.
