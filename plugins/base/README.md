# Plugin `base` de kiln

Vu depuis un repo par le lien `.claude/kiln`, créé à l'ouverture de chaque session (ignoré par
git) : c'est le plugin tel qu'il tourne sur ce poste.

- `skills/` : les skills `/base:…` (`worktree`, `fusion`, `version`, `nettoyage`, `backlog`,
  `maj-kiln`, `report-to-kiln`, `token`).
- `hooks/` : les hooks (`hooks.json` dit quand chacun se déclenche).
- `scripts/` : la status line.

**Ne pas modifier ces fichiers ici** : hors du repo kiln, ce dossier est le cache des plugins de
Claude Code, écrasé à chaque mise à jour. Une modification se fait dans
https://github.com/antoine-tena/kiln (`plugins/base/`) : sur une branche pour son mainteneur,
par le skill `base:report-to-kiln` (issue ou pull request) pour les autres.
