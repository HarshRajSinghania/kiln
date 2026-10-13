# Inventaire d'AnnSki (liste de contrôle pour un nouveau projet)

Inventaire de ce qu'AnnSki a fini par réunir, à reprendre dès le premier jour du prochain
projet. Repéré le 2026-10-01, revu le 2026-10-13, dans `~/code/association/annski`. **Aucun secret ici** : seulement les noms et
les emplacements. Les jetons se recréent, ils ne se copient pas.

## 1. Consignes pour Claude
| Élément | Rôle dans AnnSki | À reprendre |
|---|---|---|
| `CLAUDE.md` racine | Consignes + charte avec identifiants stables (`[VERROUS]`…) | Oui, la structure : règles à ID, trois régimes (stricte / cliquet / revue) |
| `frontend/CLAUDE.md`, `backend/CLAUDE.md` | Charte par sous-projet, chargée quand on y travaille | Oui, dès qu'il y a deux codebases |
| `annway/CLAUDE.md` | Sous-projet autonome | Modèle pour un sous-projet |
| Mémoire `~/.claude/projects/<repo>/memory/` | Préférences et faits durables | Repartir de zéro, mais reprendre les *feedback* (français, worktrees, pas de sessions parallèles…) |

## 2. `.claude/` du projet
Presque tout vient désormais de kiln : `kiln new` génère le
`.claude/settings.json`, qui active les plugins et pose les variables `PROJET_*`.
- `settings.json` : plugins activés et variables `PROJET_*`. `settings.local.json` : réglages perso (non commité).
- Viennent des plugins, rien à copier : `worktree` (préparation des worktrees comprise),
  `fusion`, `nettoyage`, `a-faire`, garde de branche, fichiers protégés, contrôle du
  fichier modifié (`base`) ; `nuxt`, `vitest`, `vue-best-practices`,
  `vue-testing-best-practices`, `polish` (`pile-nuxt`) ; `migration`, `regen-api`,
  `postgres-lecture` (`pile-django`) ; `deployer`, `prod-logs`, `prod-dump` (`vps-podman`).
  Status line : `~/.claude/statusline.py`.
- Propre à AnnSki, à réécrire pour un autre projet : `annonce`, `design-system`, `dev`
  (lancement du front branché sur l'API de prod), `ci-local` (liste des contrôles de sa CI),
  `nouvelle-route` (conventions de sa charte back), `google` (Search Console par compte de
  service), `sauvegarde-medias` (rushs et vidéos vers R2), `squashmigrations`.
- `worktrees/` : une branche = un worktree (exclu de git).

## 3. Serveurs MCP et connecteurs
- Plugins : `context7` (`base`), `playwright` (`pile-nuxt`), `postgres` en lecture seule
  (`pile-django`, rôle créé par la skill `postgres-lecture`), `stripe` en mode test (plugin
  `stripe`, clé `rk_test_…` dans `.stripe/token`).
- Connecteurs claude.ai (compte) : Claude Docs, etc. — rien à copier, ils suivent le compte.

## 4. Dossiers de service (`.<service>/token` + `config`, exclus de git)
Convention à garder : un dossier caché par service à la racine, `token` + `config`.
| Dossier | Service |
|---|---|
| `.vercel/` | Projet Vercel (front) : `project.json`, `repo.json` |
| `.hetzner/` | VPS Hetzner (back, podman-compose) |
| `.cloudflare/` | Zone DNS |
| `.infomaniak/` | Registrar + mail |
| `.stripe/` | Paiements |
| `.sentry/` | Erreurs |
| `.brevo/` | E-mails transactionnels |
| `.helloasso/` | Paiements (alternative à Stripe) |
| `.healthchecks/` | Sondes de tâches planifiées |
| `.google/` | Search Console (compte de service) |
| `.vps/` | Accès au VPS |
| `.annski/`, `.playwright/` | Comptes de test de Claude sur le site |
| `.backup/` | restic → R2 (`restic.password`, `token`) |
| `.env.local` | Variables locales |
| `~/.ssh/id_ed25519` | Clé SSH (VPS, GitHub) — personnelle, hors repo |

## 5. Qualité et CI
- `.github/workflows/` : `ci.yml`, `deploy.yml`, `mutation.yml`, mais GitHub Actions est
  coupé depuis le 12/10 : `kiln ci develop` rejoue la CI sur le poste et pose son verdict en
  note git, que le déploiement exige.
- annski n'a pas été généré par kiln : `kiln check`, `dev`, `install` et `contrat` y marchent
  (pile déduite des fichiers), `kiln status` le marque « adopté », `update` ne s'y applique pas.
- `.pre-commit-config.yaml`, `.gitattributes` (marque les fichiers générés), `.gitignore`, `.vercelignore`.
- `scripts/ci/check_charter.py` + `charter_*.py` : la charte vérifiée par la CI, budgets « cliquet ».
- Lockfiles commités (`uv.lock`, `pnpm-lock.yaml`), images Docker épinglées par `@sha256`.

## 6. Exploitation
- `scripts/ops/` : `deploy-backend.sh`, `deploy-frontend.sh`, `backup.sh`, `smoke-test.sh`, `lib/`.
- `config/local`, `config/vps` : config par environnement.
- `docs/exploitation/` : déploiement, retour arrière, sauvegardes.

## 7. Suivi du travail
- `docs/a-faire/` : `a-faire.md` (seule liste), `ecarte.md` (refusé), `README.md` (index) — modèle `a-faire`.
- `docs/_archive/` : campagnes closes, un dossier `AAAA-MM-JJ-sujet`.
- `openapi.json` + types générés : contrat front/back.

## 8. Leçons à appliquer dès le jour 1
- Écrire la charte **avant** le code (ici elle a été rattrapée par cliquet).
- Worktrees + hook anti-commit sur la branche principale dès le premier commit.
- `pre-commit install` dès le premier commit : sans lui, la CI de `develop` est restée rouge
  quatre jours (35 fusions, fin septembre 2026).
- Dossiers de service + `.gitignore` en place avant de créer le moindre jeton.
- Migrations numérotées dès le départ, jamais réécrites une fois fusionnées.
