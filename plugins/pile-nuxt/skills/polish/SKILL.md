---
name: polish
description: Audit visuel d'une page du site avec captures (desktop et mobile), liste des défauts de finition, puis corrections. Pour rendre une page digne d'un site haut de gamme.
disable-model-invocation: true
argument-hint: "<chemin de page, ex. /events>"
---

Page : `$ARGUMENTS`. Appliquer la skill de direction visuelle du projet s'il en a une
(`design-system` ou équivalente) et la charte du front (`$PROJET_FRONT/CLAUDE.md`).
Skills du projet : !`ls .claude/skills 2>/dev/null | tr '\n' ' '`

1. **Préparer** : travailler sur une branche dédiée `style/…`, dans son worktree (skill
   `base:worktree`). Lancer le front par la skill de lancement du projet (`dev`) si rien
   n'écoute sur son port.
2. **Capturer** avec le MCP Playwright de ce plugin (réglable par `/mcp`), sinon un script
   jetable `@playwright/test` lancé depuis le front, captures dans le scratchpad : la page à
   1440 px et à 375 px, en haut puis en défilant, plus les états accessibles (survol d'un
   bouton, menu ouvert, formulaire vide, erreur de validation, chargement si on peut le provoquer).
3. **Critiquer comme un directeur artistique** : tableau des défauts, du plus visible au moins
   visible, dans ces familles : hiérarchie et typographie, alignements et espacements,
   couleurs et contrastes, cohérence avec le reste du site, images, états manquants (vide,
   chargement, erreur), mouvement et micro-interactions, mobile, accessibilité.
   Pour chacun : ce qui ne va pas, pourquoi ça fait « bon marché », la correction.
4. **Proposer** 1 à 3 idées « effet waouh » adaptées à la page (révélation au défilement,
   chiffres animés, parallaxe légère, en-tête vidéo…), sans rien casser de la performance.
5. **Corriger** directement : Tailwind dans les composants, en suivant les règles de style de
   la charte du front, en réutilisant les composants d'interface existants.
6. **Recapturer** les mêmes vues et montrer avant/après. Commiter dans la branche du chantier.
