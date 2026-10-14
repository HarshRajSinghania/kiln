# kiln — consignes de travail

Orchestrateur de repos (modèle Copier, commande `kiln`, moteur `charte`, plugins Claude Code,
workflows réutilisables). Tout ce qui est générique aux repos vit ici : un défaut d'un fichier
généré se corrige dans `template/`, puis `kiln update` dans le repo. Présentation complète et
commandes dans [`README.md`](README.md).

## Carte du repo

Où chercher, pour ne pas explorer ; à tenir à jour dans le commit qui ajoute, déplace ou retire
un dossier ou un module.

- `src/kiln/` : la commande. `cli.py` (arguments) ; une commande par module : `new.py`,
  `install.py`, `dev.py`, `check.py`, `settings.py` (`kiln set`, clés réglables), `update.py`,
  `contract.py`, `fleet.py` (`status`, `update --all`) ; socle : `stack.py` (stack lue dans
  `.copier-answers.yml`), `template.py`, `deps.py`, `github.py`, `rules.py` (règles non
  vérifiées), `statusline.py`, `shell.py`, `config.py` (`~/.config/kiln/config.toml`).
- `src/kiln/ci/` : `kiln ci` (CI rejouée sur le poste, verdict en note git) ;
  `src/kiln/charte/` : moteur de `charte` (`interdictions.py`, `cliquets.py`,
  `outils_python.py`).
- `copier.yml` : questions du modèle ; `template/` : le modèle (`CLAUDE.md.jinja`, chartes de
  `backend/` et `frontend/` par stack, `.claude/settings.json.jinja`, CI…) ; `macros.jinja`.
- `plugins/` : plugins Claude Code, catalogue `.claude-plugin/marketplace.json` ; `base/`
  (skills `worktree`, `fusion`, `version`, `nettoyage`, `a-faire` ; `hooks/` ; `scripts/statusline.py`),
  `pile-django/`, `pile-nuxt/`, `vps-podman/`, `stripe/`, `serena/`.
- `.github/workflows/` : workflows réutilisables appelés par les repos générés ; `actions/` :
  actions composites (`charte`, `services`).
- `tests/` : `test_modele.py` (rendu du modèle pour chaque stack), `test_unites.py`,
  `test_ci.py`, `test_flotte.py`, `test_deploiement.py`.

## Contrôles

`uv run pytest -q` (le rendu du modèle prend environ une minute et demie), `uv run ruff check`
et `uv run ruff format --check`. Un hook ou un script de plugin est lu en direct par Claude Code
(catalogue déclaré en dossier local) : il agit dès la fusion dans `develop`.
