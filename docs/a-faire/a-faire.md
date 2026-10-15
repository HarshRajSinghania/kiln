# À faire

Tout ce qu'il reste à faire sur kiln, en une seule liste rangée par criticité. Créée le
**2026-10-15**. Ce qui est fait est dans la section « ✅ Fait » en bas ; ce qui a été refusé est
dans [ecarte.md](ecarte.md). **Rien d'autre n'est ouvert.**

La boussole est **kiln v0.3.0 publique, adoptée par tous les repos générés**.

---

## Mode d'emploi (humains et agents)

**Une entrée** = un titre `### AF-NN · Titre`, puis trois lignes fixes, puis le détail :

    ### AF-NN · Titre court qui dit ce qu'il faut obtenir
    - **État** : à faire
    - **Effort** : S · **Qui** : … · **Échéance** : —
    - **Origine** : d'où vient l'entrée

    Pourquoi, ce qu'il faut faire (en liste à cocher `- [ ]` s'il y a plusieurs étapes), où regarder.

- **Identifiant** `AF-NN` : stable, jamais réattribué, cité tel quel dans les commits et les
  branches. **Prochain libre : AF-13.**
- **L'état** prend une seule valeur parmi : `à faire` ; `en cours — branche <nom>, depuis le
  JJ mois` ; `bloqué — attend <qui ou quoi>` ; `à vérifier — <où>`.
- **Criticité** = la section où vit l'entrée ; en changer, c'est déplacer l'entrée.
  🔴 critique (maintenant), 🟠 important (avant la boussole), 🟡 normal, ⚪ fond (chantiers
  longs, dette).
- **Effort** : XS (moins d'une heure), S (une demi-journée), M (un à deux jours), L (plus).
- **Terminer une entrée** : la retirer de sa section et ajouter en tête du journal de la
  section « ✅ Fait » une ligne `- **AAAA-MM-JJ** · AF-NN · Titre — ce qui a été fait (branche)`.
- **Les emplacements cités sont des pistes, pas des adresses.**
- Vue d'ensemble : `grep -E '^(## |### AF-|- \*\*État)' docs/a-faire/a-faire.md`.

---

## 🔴 Critique

### AF-01 · Promouvoir v0.3.0, la première version publique
- **État** : bloqué — attend une candidate suivante et le 18 octobre (3 jours de v0.3.0-rc.1)
- **Effort** : S · **Qui** : Claude · **Échéance** : 18 octobre 2026
- **Origine** : passage au semver et aux candidates, 15 octobre 2026

`v0.3.0-rc.1` (branche `release/v0.3.0`) est adoptée par annway, sweep et vision. La règle
(CLAUDE.md, « Versions ») veut une candidate suivante prête et 3 jours sans nouvelle `-rc`.
`kiln version` dit quand c'est prêt.
- [ ] Tirer `v0.3.1-rc.1` de `develop` (gitleaks dans la CI, colonne de `status`, correctif de
  `doctor` y sont déjà), puis `kiln update --all` : annway ne doit plus avoir de conflit sur
  `ci.yml` (son job gitleaks est maintenant dans le modèle, à l'identique).
- [ ] Le 18 octobre au plus tôt : tag `v0.3.0` sur le commit de `v0.3.0-rc.1`, fusion de
  `release/v0.3.0` dans `main`, reversement dans `develop`, puis `kiln update --all`.
- [ ] Vérifier l'installation publique : `uv tool install git+https://github.com/antoine-tena/kiln@main`
  (la branche par défaut reste `develop`, donc les docs d'installation citent `@main`).

## 🟠 Important

### AF-02 · Relire la PR #39 (`kiln --version`) d'un contributeur extérieur
- **État** : à faire
- **Effort** : XS · **Qui** : Claude · **Échéance** : —
- **Origine** : https://github.com/antoine-tena/kiln/pull/39 (issue #35)

La version affichée vient maintenant de `versions.installed_version()` : la PR doit s'en servir.
Seul antoine-tena fusionne une PR (CONTRIBUTING.md) ; répondre vite et remercier.

### AF-03 · Lancer kiln publiquement, puis l'inscrire dans les annuaires Claude Code
- **État** : bloqué — attend AF-01, AF-11 et AF-06
- **Effort** : S · **Qui** : antoine · **Échéance** : —
- **Origine** : vitrine GitHub, 15 octobre 2026 ; positionnement « atelier de Claude Code »,
  16 octobre 2026

Objectif d'antoine : beaucoup de stars. Les annuaires prennent des projets qui ont déjà des
utilisateurs : le lancement vient d'abord. Publications au nom d'antoine, jamais faites sans
lui ; Claude rédige les textes.
- [ ] Une démo de `kiln new` en tête du README (GIF ou asciinema, issue #38).
- [ ] Show HN (https://news.ycombinator.com/submit), titre proposé « Show HN: Kiln – make
  Claude Code build production-grade repos, and keep them that way ».
- [ ] r/ClaudeAI (https://www.reddit.com/r/ClaudeAI/submit) et r/ClaudeCode
  (https://www.reddit.com/r/ClaudeCode/submit).
- [ ] awesome-claude-code (55 000 ★) : pas avant le **29 octobre 2026** (repo d'au moins
  14 jours, ou 100 ★), une seule proposition à la fois, **par le formulaire d'issue
  uniquement** (pas de PR) : https://github.com/hesreallyhim/awesome-claude-code/issues/new/choose
- [ ] Annuaire officiel d'Anthropic (claude-plugins-official, chargé d'office dans Claude Code) :
  https://clau.de/plugin-directory-submission — après AF-06, des plugins en français ont peu
  de chances d'y entrer.

### AF-11 · Publier kiln sur PyPI sous le nom `kiln-cli`
- **État** : à faire
- **Effort** : S · **Qui** : Claude (antoine pour le compte PyPI) · **Échéance** : —
- **Origine** : distribution, 16 octobre 2026

Le nom `kiln` est pris sur PyPI ; le paquet s'appelle `kiln-cli`, la commande reste `kiln`.
Seule la commande passe par PyPI : le modèle, les plugins et les workflows restent lus dans le
dépôt git au tag (Copier, Claude Code, GitHub Actions ne savent pas lire PyPI). Cible : macOS,
Linux et Windows via WSL ; Windows natif hors cible (choix d'antoine, 16 octobre 2026).
- [ ] Renommer la distribution `kiln-cli` dans `pyproject.toml`, et ajouter une commande
  `kiln-cli` (même point d'entrée) pour que `uvx kiln-cli new` marche.
- [ ] `installed_version()`, `kiln doctor` et `maj-kiln` : lire la version et proposer la mise
  à jour par PyPI (`uv tool upgrade kiln-cli`), en gardant l'installation depuis git.
- [ ] Workflow de publication au tag de promotion, en *trusted publishing* (sans jeton) ;
  antoine crée le projet en attente sur https://pypi.org/manage/account/publishing/
- [ ] README (anglais et français) : `uv tool install kiln-cli`, `uvx kiln-cli new`, ligne
  « macOS, Linux, Windows via WSL ».

### AF-12 · Formule Homebrew dans un tap `antoine-tena/homebrew-kiln`
- **État** : bloqué — attend AF-11
- **Effort** : S · **Qui** : Claude · **Échéance** : —
- **Origine** : distribution, 16 octobre 2026

`brew install antoine-tena/kiln/kiln` pour macOS et Linux, formule mise à jour à chaque
promotion. Le dépôt officiel homebrew-core exige un projet déjà connu : plus tard.

### AF-04 · Décider si annski cite les workflows de kiln à un tag
- **État** : à faire
- **Effort** : XS · **Qui** : antoine · **Échéance** : —
- **Origine** : passage au semver, 15 octobre 2026

annski est adopté (sans modèle) et cite les workflows en `@develop` : il reçoit tout ce qui
arrive sur `develop`, avant toute candidate. Le figer à un tag (`@v0.3.0`) le protégerait, au
prix d'une mise à jour à la main à chaque version. Condition de l'utilisateur : ne jamais
casser annski.

### AF-06 · Traduire en anglais la commande, le modèle et les plugins
- **État** : à faire
- **Effort** : L · **Qui** : Claude · **Échéance** : —
- **Origine** : issues #36 (CLI), #37 (référence du README), #38 (démo de `kiln new`) ;
  remontée en 🟠 le 16 octobre 2026 (objectif de stars)

Principal frein à l'adoption hors de France et à l'entrée dans l'écosystème Claude Code : le
README est en anglais, la commande, les skills et les fichiers générés en français.
- [ ] Messages de la commande en anglais, français en option (réglage `kiln set`).
- [ ] Skills et hooks des plugins (`plugins/`) en anglais.
- [ ] Fichiers générés (`CLAUDE.md`, chartes, `docs/a-faire/`) dans la langue choisie à
  `kiln new`.

## 🟡 Normal

### AF-05 · Vérifier le premier vrai passage des workflows sur GitHub
- **État** : bloqué — attend la facturation GitHub (CI arrêtée)
- **Effort** : XS · **Qui** : Claude · **Échéance** : —
- **Origine** : actions de kiln au commit du workflow, 15 octobre 2026

Les workflows de kiln clonent kiln à `job.workflow_sha` (propriété d'avril 2026, inconnue
d'actionlint) avec repli sur `develop`. Vérifier au premier run que la version prise est bien
celle du tag, et que `.kiln` est retiré avant les contrôles du projet.

### AF-07 · Mieux suivre les projets Java
- **État** : à faire
- **Effort** : M · **Qui** : Claude · **Échéance** : —
- **Origine** : passation de la session kiln1, 15 octobre 2026
- [ ] Audit des dépendances Maven en CI (`securite.yml`).
- [ ] `kiln update` monte les versions du `pom.xml` (aujourd'hui seul Dependabot le fait).
- [ ] `kiln ci` rejoue `maven.yml`.

## ⚪ Fond

### AF-08 · Migrations Copier pour les versions cassantes
- **État** : à faire
- **Effort** : M · **Qui** : Claude · **Échéance** : —
- **Origine** : passage au semver, 15 octobre 2026

En 0.x, une mineure peut casser. Copier sait lancer une migration au franchissement d'une
version (`_migrations` dans `copier.yml`) : chaque version cassante livre la sienne, pour que
`kiln update --all` passe sans intervention.

### AF-09 · Tests qui tournent dans l'arbre principal pendant une fusion
- **État** : à faire
- **Effort** : XS · **Qui** : Claude · **Échéance** : —
- **Origine** : passation de la session kiln1

plumbum ou Copier échoue si pytest tourne dans l'arbre principal en pleine fusion avec un
worktree présent : lancer les tests dans un worktree propre, ou rendre le test du modèle
indépendant de l'état de l'arbre.

### AF-10 · Finitions de l'interface
- **État** : à faire
- **Effort** : S · **Qui** : Claude · **Échéance** : —
- **Origine** : refonte de l'interface, 15 octobre 2026
- [ ] `kiln check` : le titre d'étape et la ligne `✓` font doublon (une commande par étape).
- [ ] Complétion bash (`kiln <Tab>`).

---

## ✅ Fait

- **2026-10-16** · Positionnement « l'atelier de Claude Code » : accroche « Make Claude Code
  build production-grade repos — and keep them that way. » (README, `pyproject.toml`,
  `CLAUDE.md`, sous-titre de l'accueil), description et mots-clés du dépôt GitHub
  (`docs/positionnement`).
- **2026-10-15** · Semver en 0.x, candidates (`-rc.N`) et promotion, canal `interne`,
  `kiln version`, workflows cités au tag exact, actions au commit du workflow (`feat/semver`) ;
  candidate `v0.3.0-rc.1` adoptée par annway, sweep et vision ; gitleaks et `workflow_call`
  remontés d'annway dans le modèle (`feat/secrets-scan`).
- **2026-10-15** · Interface (bannière, accueil, roue animée, bilan), `kiln doctor`, sorties
  préfixées de `kiln dev`, dette (status line et `charte` typées), tests de la commande et
  pytest-xdist, vitrine GitHub en anglais.
