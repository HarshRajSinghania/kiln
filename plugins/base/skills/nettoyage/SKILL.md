---
name: nettoyage
description: Supprimer les worktrees et branches locales déjà fusionnés dans la branche d'intégration, et les restes (worktrees d'agents, dossiers orphelins).
---

Depuis la racine du repo, sans jamais changer de branche dans l'arbre principal. Branche
d'intégration : celle que nomme le `CLAUDE.md` du projet, sinon `develop` si elle existe,
sinon la branche par défaut d'`origin`.

1. `git fetch -q --prune origin` puis `git worktree prune`.
2. Pour chaque worktree de `git worktree list --porcelain` (sauf l'arbre principal) : noter sa
   branche, s'il a des modifications (`git -C <wt> status --porcelain`) et si sa branche est
   fusionnée (`git merge-base --is-ancestor <branche> origin/<intégration>`). Un worktree
   détaché (agents) : regarder si son HEAD est dans `origin/<intégration>`.
3. Montrer un tableau : worktree, branche, fusionnée ?, modifications ?, dernier commit.
   Classer en « supprimable » (fusionné et propre) et « à garder / à décider ».
4. **Demander confirmation**, puis pour les supprimables : `git worktree remove <wt>` et
   `git branch -d <branche>` (jamais `-D`, jamais `--force` sur un worktree modifié).
5. Branches locales sans worktree fusionnées : proposer `git branch -d` de la même façon.
   Ne jamais supprimer de branche distante sans accord explicite.
6. Résumer ce qui a été supprimé et ce qui reste.
