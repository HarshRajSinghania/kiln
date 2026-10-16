# kiln — consignes de travail

L'atelier de Claude Code : savoir, garde-fous, façons de travailler et mise à jour des repos
(modèle Copier, commande `kiln`, moteur `charte`, plugins Claude Code, workflows
réutilisables). Tout ce qui est générique aux repos vit ici : un défaut d'un fichier
généré se corrige dans `template/`, puis `kiln update` dans le repo. Présentation complète et
commandes dans [`README.fr.md`](README.fr.md) (vitrine en anglais :
[`README.md`](README.md)).

## Carte du repo

Où chercher, pour ne pas explorer ; à tenir à jour dans le commit qui ajoute, déplace ou retire
un dossier ou un module.

- `src/kiln/` : la commande. `cli.py` (arguments) ; une commande par module : `new.py`,
  `install.py`, `dev.py`, `check.py`, `settings.py` (`kiln set`, clés réglables), `update.py`,
  `contract.py`, `release.py` (`kiln version`), `doctor.py` (diagnostic du poste et du repo), `fleet.py` (`status`, `update --all`) ; socle : `stack.py` (stack lue dans
  `.copier-answers.yml`), `template.py`, `deps.py`, `github.py`, `rules.py` (règles non
  vérifiées), `statusline.py`, `versions.py` (tags, journal des versions), `banner.py` (bannière, écran d'accueil), `ui.py` (palette pierre et feu, étapes,
  roue animée, bilan, succès, erreurs), `shell.py`, `config.py` (`~/.config/kiln/config.toml`).
- `src/kiln/ci/` : `kiln ci` (CI rejouée sur le poste, verdict en note git) ;
  `src/kiln/charte/` : moteur de `charte` (`interdictions.py`, `cliquets.py`,
  `outils_python.py`, `waivers.py` : dérogations de `kiln-waivers.toml`).
- `copier.yml` : questions du modèle ; `template/` : le modèle (`CLAUDE.md.jinja`, chartes de
  `backend/` et `frontend/` par stack, `.claude/settings.json.jinja`, CI…) ; `macros.jinja`.
- `plugins/` : plugins Claude Code, catalogue `.claude-plugin/marketplace.json` ; `base/`
  (skills `worktree`, `fusion`, `version`, `nettoyage`, `backlog`, `maj-kiln`,
  `report-to-kiln` (défaut de kiln remonté en issue ou PR), `token` (jeton d'un service dans
  `.<service>/`) ; `hooks/` ; `scripts/statusline.py`),
  `pile-django/`, `pile-nuxt/`, `vps-podman/`, `stripe/`, `serena/`.
- `.github/workflows/` : workflows réutilisables appelés par les repos générés, plus ceux de
  kiln (`kiln.yml` contrôles, `pypi.yml` publication du paquet `kiln-cli` au tag promu) ;
  `actions/` : actions composites (`charte`, `services`).
- Vitrine publique, en anglais : `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`
  (MIT), `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` ; capture de l'écran
  d'accueil `docs/assets/kiln-accueil.svg`. Référence complète en français : `README.fr.md`.
- `docs/backlog/` : suivi du travail, en anglais (skill `base:backlog`), dont la prochaine
  promotion de version ; `docs/assets/` : images de la vitrine.
- `tests/` : `test_modele.py` (rendu du modèle pour chaque stack), `test_cli.py` (la commande :
  accueil, erreurs, bilan, sorties hors terminal), `test_unites.py`,
  `test_ci.py`, `test_flotte.py`, `test_waivers.py` (dérogations), `test_deploiement.py`, `test_statusline.py` (choix du
  poste et rendu du script), `test_plugins.py` (skills cités présents, nommés comme leur dossier).

## Versions

**Pourquoi** (choix d'antoine, 15 octobre 2026) : kiln doit rester stable pour les repos qui en
dépendent, alors qu'il change beaucoup ; d'où une version qui ne sort que quand la suivante est
prête ici, en candidate sur ses propres repos (`-rc`, comme Python ou Linux) : pas de délai
fixe, c'est la suivante prête qui évite le correctif d'urgence (précisé par antoine le
16 octobre 2026), et le 0.x du semver, prévu pour un début où tout peut casser (comme uv ou ruff), plutôt
qu'un quatrième chiffre. Les clients se mettent à jour à chaque version, correctif compris.
Suivi de ce qui reste : `docs/backlog/backlog.md`.

**Numérotation** (choix d'antoine, 16 octobre 2026) : comme Claude Code (2.1.301 en octobre
2026), pas comme Vercel CLI (64 majeures, un numéro qui ne dit plus rien). Personne ne dépend de
kiln par une plage de versions (`^0.3`) : les repos citent ses workflows au tag exact et
n'avancent que par `kiln update`, qui convertit ce qui casse. Le numéro date une version ; c'est
la note de version qui dit ce qui change. De Next.js, on prend la discipline (candidates,
changements cassants en tête des notes, migration automatique), pas la numérotation.

`vMAJEUR.MINEUR.CORRECTIF`. En 0.x (aujourd'hui) :
- **chaque version monte le correctif**, nouveautés et changements cassants compris (`v0.3.1`,
  `v0.3.2`… `v0.3.192` s'il le faut) ;
- **la mineure ne monte que pour une étape** décidée par antoine (par exemple kiln tout en
  anglais) : `kiln version --minor` ; ne jamais la proposer d'office ;
- **un changement cassant** reste marqué au commit (`feat!:` ou `BREAKING CHANGE`), ouvre la
  note de version dans `CHANGELOG.md`, et livre sa conversion dans `kiln update`. Est cassant
  ce qui touche l'API publique de kiln : commandes et options de la CLI, questions de
  `copier.yml`, arborescence générée, entrées des workflows et actions réutilisables, noms des
  skills et hooks, identifiants de règles de la charte.

À partir de 1.0 (l'engagement de stabilité public, plus tard), semver strict comme Next.js :
cassant → majeure (rare et planifiée), `feat` → mineure, le reste → correctif. `kiln version`
(module `release.py`) propose le numéro et dit quelles candidates sont prêtes.

Deux temps, par la skill `base:version` (pas de déploiement : le tag publie, et le tag promu
publie sur PyPI le paquet `kiln-cli` par `pypi.yml`) :
1. **Candidate** : branche `release/vX.Y.Z` tirée de `develop`, entrée `## vX.Y.Z — date` en tête
   de `CHANGELOG.md`, `version = "X.Y.Z"` dans `pyproject.toml`, contrôle complet (les trois
   commandes ci-dessous), tag `vX.Y.Z-rc.1` poussé. Les postes au canal `interne` (`kiln set
   canal=interne`, celui d'antoine) la suivent : `kiln update --all` y fait passer tous les repos
   générés. Un correctif de la candidate : commit `fix:` sur sa branche, tag `-rc.N+1`.
2. **Promotion**, quand `kiln version` la dit prête (une candidate plus récente existe, sans
   délai d'attente) : tag `vX.Y.Z` sur le commit exact de sa
   dernière candidate, fusion dans `main`, reversement dans `develop`, puis `kiln update --all`.
   Le canal `public` (par défaut) ne voit que ces versions.

Chaque version, correctif compris, finit par `kiln update --all` : les repos générés citent leurs
workflows au tag exact dont ils partent (`ci.yml`), et `kiln update` le fait avancer. Les
workflows de kiln prennent leurs actions et la commande `charte` à leur propre commit
(`job.workflow_sha`). Les dépôts adoptés (annski) citent les workflows en `@develop` et ne
reçoivent pas de `kiln update`. Modules : `versions.py` (tags, canaux, journal, version de
l'outil), `release.py` (`kiln version`).

## Contrôles

`uv run pytest -q` (réparti sur tous les cœurs par pytest-xdist : une vingtaine de secondes ;
`-n 0` pour un seul processus, au débogage), `uv run ruff check`
et `uv run ruff format --check`. Un hook ou un script de plugin est lu en direct par Claude Code
(catalogue déclaré en dossier local) : il agit dès la fusion dans `develop`.
