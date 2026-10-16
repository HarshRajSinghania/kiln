---
name: worktree
description: Créer une branche de travail dans un git worktree prêt à l'emploi. Façon normale de démarrer une branche, pour ne pas croiser une autre session dans l'arbre principal.
argument-hint: "<type/nom-de-branche>"
---

Branche demandée : `$ARGUMENTS` (format `feat/…`, `fix/…`, `chore/…`, comme l'historique du
repo). Sans argument, en proposer une d'après la tâche.

1. Trouver la racine du repo (`git rev-parse --show-toplevel` de l'arbre principal) et sa
   branche d'intégration : celle que nomme le `CLAUDE.md` du projet, sinon `develop` si elle
   existe sur `origin`, sinon la branche par défaut (`git symbolic-ref refs/remotes/origin/HEAD`).
2. Depuis la racine, sans jamais changer de branche dans l'arbre principal :
   `git fetch -q origin <intégration>` puis
   `git worktree add --no-track .claude/worktrees/<nom> -b <branche> origin/<intégration>`
   (`<nom>` = la branche avec `/` remplacé par `-`). Sans `--no-track`, la branche suivrait
   `origin/<intégration>` : `git push` sans argument refusé, `git pull` qui tire l'intégration.
   Si la branche existe déjà, l'attacher sans `-b`.
   Vérifier que `.claude/worktrees/` est ignoré par git ; sinon l'ajouter à `.git/info/exclude`.
3. Préparer le worktree : `bash "${CLAUDE_PLUGIN_ROOT}/scripts/preparer-worktree.sh" <chemin du worktree>`
   (copie les `.env*` ignorés de l'arbre principal, installe les dépendances de chaque
   `pnpm-lock.yaml` / `package-lock.json`). Si le repo fournit en plus
   `.claude/worktree-setup.sh`, le lancer ensuite avec le même argument.
4. Travailler ensuite exclusivement dans ce worktree (chemins absolus) et donner son chemin.
