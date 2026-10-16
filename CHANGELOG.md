# Nouveautés de kiln

Une entrée par version, la plus récente en tête : `## vX.Y.Z — date`, puis une ligne par
changement visible (`- …`), cassants en tête. `kiln update` montre les entrées des versions
qu'un projet passe ; la skill `base:version` rédige celle de la version qu'elle sort, sur la
branche `release/vX.Y.Z`, avant sa première candidate.

## v0.3.0 — 2026-10-15
- Première version publiée. Semver en 0.x : une version sort d'abord en candidate (`-rc.N`) pour les postes au canal `interne`, puis est promue quand la suivante est prête et qu'elle a tenu trois jours ; `kiln version` dit où en sont les candidates.
- Les projets citent les workflows de kiln au tag exact dont ils partent ; `kiln update` le fait avancer et montre les nouveautés de chaque version passée. Le hook de début de session propose l'outil puis le repo à chaque version.
- `kiln status` dit de quelle version part chaque repo (`f611f82 → v0.3.0`) ; `kiln set canal=interne` (réglage du poste) fait suivre les candidates.
- Nouvelle interface : four rieur en bannière, écran d'accueil par sections, roue animée et durée pour chaque commande externe, bilan encadré des étapes ; aucune couleur hors terminal, `KILN_VERBOSE=1` pour la sortie complète.
- `kiln doctor` : diagnostic du poste et du repo, chaque problème avec la commande qui le corrige.
- `kiln dev` : sorties des serveurs entrelacées, préfixées par service en couleur.
- `kiln update --all` fusionne directement chaque repo dont les contrôles passent, sans PR.
- Backend Java (Maven), skill `maj-kiln`, lien `.claude/kiln` vers le plugin, réglages du poste par `kiln set`.
