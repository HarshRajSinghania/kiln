# kiln

*[English](README.md) · Français*

L'atelier de Claude Code : kiln lui donne de quoi construire des repos de qualité production et
les garder ainsi. Le savoir (stacks à jour, consignes par repo, documentation des bibliothèques),
les garde-fous (règles vérifiées par la machine, hooks, branches protégées), les façons de
travailler (branche, fusion, version, suivi) et la fraîcheur : un projet complet en une
commande, des paramètres réglables à tout moment, tenu à jour (architecture et dépendances). Jamais pip ni docker : uv pour Python,
pnpm pour JavaScript, podman pour les conteneurs.

Un projet généré contient :

- la stack choisie, conseillée selon le type de projet (voir ci-dessous) ;
- sa charte de code (`CLAUDE.md` à la racine, dans `backend/` et `frontend/`), dont les règles
  contrôlables sont décrites dans `charte.toml` et vérifiées par la commande `charte` ;
- l'outillage partagé : `.claude/` (plugins et variables `PROJET_*`), `.vscode/`, `.editorconfig`,
  `.gitattributes`, `.gitignore`, modèle de PR, `CODEOWNERS`, pre-commit (ruff, ESLint, charte,
  refus de commiter sur `main` et `develop`) ;
- la CI GitHub (`.github/workflows/ci.yml`), qui appelle les workflows réutilisables de kiln ;
- le suivi du travail, d'office : `docs/a-faire/` (`a-faire.md`, `ecarte.md`, `urgent.md`,
  skill `base:a-faire`), que la status line de Claude Code compte ;
- les réglages de la status line propres au repo (`statusline_ci`, `url_sante_prod`), posés en
  `git config statusline.*` par `kiln install`, `kiln new` et `kiln set` ;
- d'office (`--no-github` pour s'en passer) : le dépôt GitHub privé, avec `main` verrouillée (seul le commit initial)
  et `develop` protégée (ni suppression ni réécriture), et les correctifs de sécurité Dependabot ;
- en option : les conteneurs podman.

Les plugins Claude Code vivent dans [`plugins/`](plugins/), catalogue `kiln`
([`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json)) :

- `base`, pour tous les projets, installé au niveau utilisateur : skills `worktree`, `fusion`,
  `version` (release/vN, contrôle complet, annonce, main tagué, déploiement), `nettoyage`, `a-faire`,
  `maj-kiln` (l'outil kiln et ses plugins, puis le repo ouvert), `report-to-kiln` (un défaut de kiln remonté en issue ou en PR, avec l'accord de l'utilisateur) ; hooks garde de branche, fichiers protégés, contrôle du fichier
  modifié, mise à jour proposée à l'ouverture de session (oui/non : l'outil kiln s'il est en
  retard sur GitHub, puis le repo par `kiln update` ; un « non » repousse la question de 5, 10,
  30 puis 50 sessions, après quoi désinstaller kiln ou délier le repo est proposé ;
  `git config kiln-a-jour.desactive true` pour s'en passer), sorties de commandes condensées par [rtk](https://github.com/rtk-ai/rtk) quand il
  est installé (`mise use -g github:rtk-ai/rtk`, sans `rtk init` : le hook est fourni ici) ; MCP context7 ; status line commune (`plugins/base/scripts/statusline.py`,
  en anglais, aux couleurs de kiln), posée par `kiln install` dans `~/.claude/settings.json` ; son
  style se choisit par poste : `kiln set statusline=sobre|bandeau|classique|classique-fond`,
  `aucune` (retirée) ou `perso` (kiln ne touche plus à la `statusLine` de l'utilisateur, choix
  automatique s'il en a déjà une) ;
- `pile-nuxt` (skills Nuxt, Vue, Vitest, `polish`, `apercu` — captures sur trois téléphones et un ordinateur ; MCP playwright) et `pile-django` (skills
  `migration`, `regen-api`, `postgres-lecture`), activés par le `.claude/settings.json` généré
  selon la stack ;
- `vps-podman` (skills `deployer`, `prod-logs`, `prod-dump`) et `stripe` (MCP en mode test),
  activés à la main par le repo qui en a besoin.
- `serena` (MCP [Serena](https://github.com/oraios/serena) en lecture seule : plan d'un
  fichier, définition et références d'un symbole), activé par `kiln set serena=true` sur un gros
  repo ; les éditions restent aux outils de Claude Code, où sont branchés les hooks de `base`.

Installation : `claude plugin marketplace add antoine-tena/kiln`, puis
`claude plugin install base@kiln`.

Le modèle vit dans [`template/`](template/), servi par [Copier](https://copier.readthedocs.io) :
chaque projet garde dans `.copier-answers.yml` ses réponses et la version du modèle dont il
part, ce qui permet de lui rapporter les évolutions sans écraser ses modifications locales.

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/) et git ; [pnpm](https://pnpm.io/) (Node 24) pour un
front JavaScript ; un JDK 25 et `unzip` pour un backend Java ; [podman](https://podman.io/)
pour les conteneurs ; [gh](https://cli.github.com)
pour le dépôt GitHub, que `kiln new` crée d'office (si `gh` n'est pas connecté, kiln lance la
connexion et affiche le lien https://github.com/login/device).

```sh
uv tool install git+https://github.com/antoine-tena/kiln
```

Installe deux commandes, `kiln` et `charte`, à la dernière version (branche `main`). Quand une
version sort, le hook de début de session propose de mettre à jour l'outil, puis chaque repo ;
à la main : `uv tool upgrade kiln`, puis `kiln update` dans le repo.
Python 3.14 est requis ; uv le télécharge au besoin. Au premier `kiln install`, kiln demande le
système du poste (Linux, WSL ou macOS) et le garde dans `~/.config/kiln/config.toml`, avec
`proprietaire` et `equipe` par défaut si on les y ajoute.

## Commandes

| Commande | Rôle |
|---|---|
| `kiln new [dossier]` | Questionnaire (envergure, type de projet, stack conseillée, podman…), génération, verrous, installation, premier commit sur `main`, puis `develop` où tout le travail se fait. |
| `kiln install` | Prépare un poste après un clone : outils (pre-commit avec pre-commit-uv, podman-compose), dépendances, `backend/.env`, migrations, pre-commit. Relançable. |
| `kiln dev` | Lance les serveurs de la stack, leurs sorties entrelacées et préfixées par service en couleur (`django │ …`) ; `--containers` : toute la pile dans podman. |
| `kiln check` | Ruff, mypy et pytest pour chaque projet Python, ESLint et les types côté front, puis la charte. |
| `kiln ci [commit]` | Rejoue sur le poste la CI du `ci.yml` pour ce commit (défaut `HEAD`) et pose le verdict en note git sur origin, que le script de déploiement accepte comme une CI verte. `--statut` : le verdict seul. Voir « CI rejouée sur le poste ». |
| `kiln contrat` | Django + Nuxt : exporte `openapi.json` depuis le code, puis régénère les types du front (`app/types/api.d.ts`). `kiln update` le fait aussi. |
| `kiln set` | Dans un repo : sans argument, affiche ses paramètres ; `kiln set clé=valeur…` les change (équipe, frameworks, podman, a-faire…) : le repo est régénéré, un framework retiré emporte ses fichiers. Hors d'un repo, ou avec `--poste` : les réglages du poste (`systeme`, `proprietaire`, `equipe`, `dossier_code`, dans `~/.config/kiln/config.toml`). |
| `kiln update` | Évolutions du modèle, mises à jour compatibles des dépendances, puis contrôles. `--major` : versions majeures comprises. `--no-template`, `--no-deps` pour n'en faire qu'une partie. |
| `kiln update --all` | Tous les repos kiln du dossier de code (`~/code`, réglable par `dossier_code`) : pour chacun, un worktree depuis la branche d'intégration, la mise à jour, des commits de dix fichiers au plus, puis la fusion directe dans l'intégration (commit de fusion poussé) ; contrôles en échec, la branche est poussée sans être fusionnée. L'arbre principal ne change jamais de branche. |
| `kiln doctor` | Diagnostic du poste (git, uv, gh connecté, pnpm, podman, Java, pre-commit, version de kiln, plugin Claude, configuration) et du repo courant (version du modèle, crochet pre-commit, dépendances, `backend/.env`) : ✓, ! à regarder ou ✗ bloquant, chaque fois avec la commande qui corrige. Ne modifie rien. |
| `kiln status` | État des repos kiln du dossier de code : branche, arbre propre ou non, version du modèle (`v0.3.2 → v0.4.0` en retard), stack. |
| `kiln version` | Dans le dépôt de kiln : dernière version publique, candidates (âge, repos qui les ont adoptées, prêtes à promouvoir) et numéro de la prochaine. |
| `charte` | Vérifie le repo contre son `charte.toml` (`charte --detail`, `charte types`, `charte couverture`). |

`set` et `update` travaillent sur une branche, arbre propre ; les conflits entre le modèle et une
modification locale sont marqués dans le fichier (`<<<<<<<`). Relire, commiter, fusionner dans
`develop` (skill `base:fusion`, sans PR ni approbation à attendre).

`new`, `install`, `update` et `status` s'ouvrent sur une bannière : un four en pixel art, la
version de kiln, la commande, le projet (envergure, stack) et son dossier. Hors terminal ou avec
`NO_COLOR`, une seule ligne de texte à la place. `kiln` seul (ou `kiln --help`) ouvre l'écran
d'accueil : commandes par section et exemples ; les étapes, succès, erreurs et le tableau de
`status` suivent la même palette pierre et feu, sans couleur hors terminal.
Chaque commande externe (`uv sync`, `pnpm install`, contrôles…) tourne derrière une roue animée
qui montre sa dernière ligne, puis laisse `✓ commande  durée` ; sa sortie complète n'apparaît
qu'en cas d'échec. Un bilan encadré clôt la commande : verdict, durée totale et durée de chaque
étape. `KILN_VERBOSE=1 kiln …` rend la sortie complète des commandes.

Sans dossier, `kiln new` demande le nom du projet et le crée dans le dossier courant.
Options de `new` : `--size`, `--type`, `--backend`, `--frontend`, `--podman`,
`--vps <utilisateur@adresse>`, `--name`, `--title`,
`--description`, `--owner`, `--team login1,login2`, `--goal "<boussole>"`, `--prod-url <url>`,
`--no-github` (pas de dépôt GitHub),
`--no-install`, `--template <chemin ou URL>`. Les questions sans option sont posées dans le
terminal.

## Envergure

Première question de `kiln new` : « How hot does this one burn? ». Quatre crans, nommés d'après
le feu du four :

| Cran | Projet |
|---|---|
| `spark` | un script, un outil perso, une analyse ponctuelle |
| `ember` | une petite app ou un site, une ou deux personnes, peu d'enjeu (par défaut) |
| `flame` | une app en production, de vrais utilisateurs, plusieurs contributeurs (AnnSki) |
| `blaze` | plusieurs équipes ou services, de gros enjeux |

L'envergure est écrite dans le `CLAUDE.md` du projet et règle les valeurs par défaut des
questions suivantes : à partir de `flame`, les conteneurs podman sont précochés. Elle se change
par `kiln set envergure=…` et `kiln status` l'affiche.

## Conseil de stack

Le type de projet précoche une stack, que l'on change à la question suivante ou plus tard par
`kiln set backend=… frontend=…`.

| Type de projet | Backend conseillé | Frontend conseillé |
|---|---|---|
| Application complète (`app`) | Django + Django Ninja | Nuxt + Vue |
| API seule (`api`) | FastAPI | aucun |
| Site de contenu (`site`) | aucun | Astro |
| Tableau de bord de données (`tableau`) | Données Python (polars, marimo, Plotly) | Streamlit |
| Analyse de données (`analyse`) | Données Python | aucun |
| Outil en ligne de commande (`outil`) | Outil Python (`cli` : argparse, commande installable) | aucun |

Backends : `django`, `fastapi`, `data`, `cli`, `java`, `aucun`. Frontends : `nuxt`, `next`, `astro`,
`streamlit`, `dash`, `aucun`. Toutes les combinaisons sont générées et vérifiées par les tests.

`java` n'est conseillé pour aucun type : Java 25 sans framework, construit par Maven via son
wrapper `./mvnw` (version et somme SHA-256 figées), tests JUnit 6, couverture JaCoCo, enforcer
qui refuse les versions dynamiques. `kiln update` n'en monte pas les dépendances : les versions
du `pom.xml` se changent à la main.

## Déploiement sur un serveur à soi

`deploiement=vps` (`kiln new --vps root@<adresse>`, ou `kiln set deploiement=vps` plus tard), pour
un backend Django avec podman, ajoute la production reprise d'AnnSki :

- `config/vps/` : pile de production (PostgreSQL et gunicorn, système de fichiers en lecture
  seule), Caddyfile (TLS automatique), script de bascule exécuté en root sur le serveur (une image
  par commit, migrations, retour arrière automatique si la nouvelle version ne répond pas),
  utilisateur `deploy` limité à cette commande, sauvegardes quotidiennes et d'avant bascule (copie
  restic hors du serveur en option), test de restauration hebdomadaire, relance des conteneurs
  malades (unités systemd) ;
- `scripts/ops/` : `deploy-backend.sh` (`--dry-run`, `--rollback`) et `smoke-test.sh`, depuis le
  poste ; le serveur reçoit le code en bundle git, sans accès au dépôt ;
- `docs/exploitation/production.md` : préparation du serveur, déploiement, retour arrière,
  sauvegardes.

Réglages : `vps_hote`, `domaine_api`, `url_site`, `branche_deploiement` (par `kiln set`). Quel
que soit le déploiement, l'image du backend Django sert gunicorn et ses fichiers statiques
(WhiteNoise) sans migrer au démarrage, et `/api/health` rend la version en service.

## Front sur Vercel

`front_deploiement=vercel` (front Nuxt, `kiln set front_deploiement=vercel`) ajoute
`scripts/ops/deploy-frontend.sh` : `vercel --prod` envoie les fichiers du poste, le script ne
l'autorise que depuis `develop` à jour avec `origin`, front sans modification locale et CI verte
(`SAUTER_CI=1` en cas d'urgence). Le projet Vercel se lie une fois par `vercel link`.

## Mises à jour des dépendances

`kiln update` fait des mises à jour compatibles : uv reste dans les bornes du `pyproject.toml`
(même version majeure), pnpm ne monte que les dépendances qui gardent leur majeure et annonce les
autres. `kiln update --major` relève les bornes à la dernière version, prend les dernières
versions pnpm et met à jour les crochets pre-commit. Les contrôles suivent toujours : une montée
qui casse quelque chose est signalée avant le commit. Dependabot ne propose que les correctifs de
sécurité.

## Versions

kiln suit le semver à trois chiffres (`vMAJEUR.MINEUR.CORRECTIF`). En 0.x, le développement
initial, un changement cassant monte la mineure (`0.3.4 → 0.4.0`) et tout le reste le correctif.
Le travail s'intègre dans `develop` ; `main` ne reçoit que des versions.

- **Candidate** (`v0.4.0-rc.1`) : tirée de `develop` sur une branche `release/v0.4.0`, avec son
  entrée en tête de [`CHANGELOG.md`](CHANGELOG.md). Seuls les postes au canal `interne` la
  suivent (`kiln set canal=interne`).
- **Promotion** (`v0.4.0`) : quand une candidate plus récente est prête et que celle-ci a tenu
  3 jours (7 après la 1.0) dans les repos du canal interne, le même commit est tagué et fusionné
  dans `main`. `kiln version` montre les candidates, leur âge, qui les a adoptées, lesquelles
  sont prêtes et le numéro de la prochaine.
- **Clients** : ils se mettent à jour à chaque version, correctif compris. Le hook de début de
  session propose l'outil puis le repo ; `kiln update` applique la version, montre ses
  nouveautés et fait avancer le tag auquel le `ci.yml` du repo cite les workflows de kiln.
- **Outil** : `uv tool install git+https://github.com/antoine-tena/kiln` suit `main` ;
  `kiln status` dit de quelle version part chaque repo (`v0.3.2 → v0.4.0`), la bannière celle
  de l'outil (`v0.4.0 +3 · abc1234` : trois commits après v0.4.0, installé depuis un dossier).

## Faire évoluer le modèle

Modifier `template/` sur une branche, puis la fusionner dans `develop` : les projets le
reçoivent à la version suivante, par `kiln update` (le hook de début de session le propose).
Pour essayer un modèle pas encore publié : `KILN_TEMPLATE=~/code/kiln kiln new …`.

Depuis un projet, un défaut de kiln remonte ici ([REMONTER-A-KILN] de la charte générée), par
le skill `base:report-to-kiln` :

- **pull request** vers `develop` quand la correction est claire et localisée, depuis un fork :
  kiln n'appartient qu'à antoine-tena, seul à y écrire et à fusionner ;
- **issue** quand il faut trancher entre plusieurs voies, ou qu'on ne sait pas corriger. Dans le
  doute, l'issue d'abord : une PR sur un choix pas encore fait risque d'être refaite.

Le skill vérifie d'abord que kiln est à jour et que personne ne l'a déjà signalé, rédige en
anglais sans rien de privé du projet, et ne publie qu'avec l'accord explicite de l'utilisateur :
c'est public, sous son compte GitHub.
 Seuls les fichiers en `.jinja` sont interprétés ; un dossier
`{% if … %}nom{% endif %}` n'existe que si la condition tient ; les questions sont dans
[`copier.yml`](copier.yml) et les macros partagées (chaînes Python au format de ruff) dans
[`macros.jinja`](macros.jinja).

```sh
uv run pytest            # chaque stack se génère en fichiers valides
uv run ruff check . && uv run mypy src tests
```

## Moteur de charte

`src/kiln/charte/` lit le `charte.toml` à la racine du repo. Interdictions (`signaux-django`,
`journalisation`, `migrations-django`, `temps-constant`, `donnees-perso`, `style-vue`,
`renvois-audit`, `fichiers-interdits`, `copies`, `compose-profils`, `outils-interdits` : jamais
pip ni docker, ni leurs fichiers), cliquets et planchers
(`taille-fichier`, `routes-longues`, `verrous-django`, `occurrences`, `densite-tests`),
`[types]` (mypy en cliquet) et `[couverture]` (planchers de pytest-cov) ; paramètres dans la
docstring de chaque règle. Règle propre à un repo : un module listé dans `regles_locales`,
avec `verifier(depot, params) -> list[str]`. La liste des règles non vérifiées
(`scripts/ci/charte-non-verifiee.txt`) est recalculée par kiln à chaque `set` et `update`.

## Workflows réutilisables

kiln est public : ses workflows servent à n'importe quel dépôt, quel que soit son compte
(`uses: antoine-tena/kiln/.github/workflows/<nom>.yml@main`). Jamais pip ni docker : uv pour
Python, podman pour les conteneurs (bases de test comprises), podman-compose installé par uv.

| Workflow | Rôle |
|---|---|
| `django.yml` | Backend Django : ruff, `charte types`, migrations manquantes, pytest et couverture, contre PostgreSQL et Redis lancés par podman. |
| `python.yml` | Tout projet uv (FastAPI, données, Streamlit, Dash) : ruff, mypy, pytest avec un plancher de couverture ; PostgreSQL en option. |
| `maven.yml` | Backend Java : `./mvnw verify` (compilation stricte, JUnit, plancher de couverture JaCoCo) sur un JDK Temurin. |
| `pnpm.yml` | Front pnpm (Nuxt, Next.js, Astro) : scripts de `package.json` dans l'ordre ; pnpm pris dans `packageManager`. |
| `charte.yml` | Règles de `charte.toml`. |
| `securite.yml` | `uv audit` et `pnpm audit`. |
| `contrat-api.yml` | `openapi.json` et types du front à jour du code. |
| `infra.yml` | Images (`podman build`), actionlint, shellcheck, Caddyfile, compose (podman-compose). |
| `sbom.yml` | Nomenclatures CycloneDX du back et du front. |
| `mutation.yml` | Tests par mutation (mutmut), jamais bloquants. |
| `vercel.yml` | Déploiement du front sur Vercel. |

Actions : `actions/charte` (installe kiln et `charte`), `actions/services` (PostgreSQL et Redis
par podman, `DATABASE_URL` et `REDIS_URL` posées).

## CI rejouée sur le poste

Pour un dépôt dont la CI GitHub ne tourne pas (forfait épuisé, Actions coupées), `kiln ci <commit>`
la rejoue sur le poste, depuis le même `ci.yml` :

- le commit est extrait dans un worktree détaché hors du dépôt (`~/.cache/kiln/ci/`), les
  dépendances installées depuis les verrous (`uv sync --locked`, `pnpm install --frozen-lockfile`) ;
- chaque job qui appelle un workflow de kiln (`django`, `contrat-api`, `charte`, `pnpm`,
  `securite`) est rejoué avec ses paramètres `with:`, contre un PostgreSQL et un Redis jetables
  (podman, ports libres) ; un job écrit dans le projet l'est s'il ne fait que des `run:` ;
- le back (pytest) tourne à côté du reste ; un journal par job dans `~/.cache/kiln/ci/journaux/` ;
- le verdict part en note git (`refs/notes/ci`) poussée sur origin. Sa première ligne,
  `kiln ci : succès`, est ce que `scripts/ops/lib/ci-verte.sh` accepte avant un déploiement ; la
  note liste aussi les jobs **non rejoués** (services propres au job, `infra`, `sbom`…).

`--sauter <job>` écarte un job (noté dans le verdict), `--sans-pousser` garde la note en local,
`--garder` laisse le worktree pour enquêter. Avec `git config statusline.ci locale`, la status
line affiche ce verdict pour la branche d'intégration. `kiln ci` ne tourne plus à chaque fusion
dans `develop` : seulement sur la branche `release/vN` d'une version (skill `base:version`), dont
le verdict vaut pour le commit de fusion dans `main` (mêmes fichiers). Entre deux versions, le
typage se joue avant chaque push (crochet pre-push de `.pre-commit-config.yaml`).
