---
name: fusion
description: Terminer un chantier - fusionner la branche dans la branche d'intégration, pousser, supprimer la branche (et son worktree).
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
6. Si le repo rejoue sa CI sur le poste (`git config statusline.ci` vaut `locale`) : lancer
   `kiln ci <intégration>` **en arrière-plan** (une vingtaine de minutes ; le verdict part en note
   git sur origin, et le script de déploiement le lit), puis donner son verdict quand il arrive.
   Ne pas attendre devant : la fusion est faite.
7. Résumer : commit de fusion, fichiers touchés, CI déclenchée (`kiln ci` lancé, ou
   `gh run list -b <intégration> -L 1` si le repo est sur GitHub).
