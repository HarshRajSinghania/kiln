# Backlog

Everything left to do on kiln, in a single list ordered by priority. Started on
**2026-10-15**. What is done is in the "✅ Done" section at the bottom; what was turned
down is in [rejected.md](rejected.md). **Nothing else is open.**

North star: **kiln v0.3.0 public, adopted by every generated repo**.

---

## How to use (humans and agents)

**A ticket** = a `### T-NN · Title` heading, then five fixed lines, then the details:

    ### T-NN · Short title that says what to achieve
    - **Type**: task
    - **Status**: todo
    - **Opened**: YYYY-MM-DD
    - **Effort**: S · **Owner**: … · **Due**: —
    - **Origin**: where it comes from

    Why, what to do (as a `- [ ]` checklist when there are several steps), where to look.

- **ID** `T-NN`: stable, never reused, quoted as is in commits and branches (tickets opened
  before 16 October 2026 were `AF-NN`, same number). **Next free: T-14.**
- **Type**, one of: `bug` (something is broken); `improvement` (it works, it could work
  better); `idea` (nothing exists yet, to be explored); `task` (work that is neither: a release,
  a decision, a check).
- **Status**, one of: `todo`; `in progress — branch <name>, since YYYY-MM-DD`;
  `blocked — waiting for <who or what>`; `to verify — <where>`.
- **Priority** = the section the ticket lives in; changing it means moving the ticket.
  🔴 critical (now), 🟠 important (before the north star), 🟡 normal, ⚪ background
  (long-running work, debt, ideas still to be explored).
- **Effort**: XS (under an hour), S (half a day), M (one or two days), L (more).
- **Closing a ticket**: remove it from its section and add a line at the top of the "✅ Done"
  log: `- **YYYY-MM-DD** · T-NN · Title — what was done (branch) · opened YYYY-MM-DD`.
- **Locations quoted are hints, not addresses.**
- Overview: `grep -E '^(## |### T-|- \*\*Status)' docs/backlog/backlog.md`.

---

## 🔴 Critical

### T-01 · Promote v0.3.0, the first public release
- **Type**: task
- **Status**: blocked — waiting for a next candidate and 18 October (3 days of v0.3.0-rc.1)
- **Opened**: 2026-10-15
- **Effort**: S · **Owner**: Claude · **Due**: 2026-10-18
- **Origin**: move to semver and release candidates, 15 October 2026

`v0.3.0-rc.1` (branch `release/v0.3.0`) is adopted by annway, sweep and vision. The rule
(CLAUDE.md, "Versions") requires a next candidate ready and 3 days without a new `-rc`.
`kiln version` says when it is ready.
- [ ] Cut `v0.3.1-rc.1` from `develop` (gitleaks in CI, the `status` column, the `doctor` fix
  are already there), then `kiln update --all`: annway must no longer conflict on `ci.yml`
  (its gitleaks job is now in the template, identical).
- [ ] On 18 October at the earliest: tag `v0.3.0` on the commit of `v0.3.0-rc.1`, merge
  `release/v0.3.0` into `main`, merge back into `develop`, then `kiln update --all`.
- [ ] Check the public install: `uv tool install git+https://github.com/antoine-tena/kiln@main`
  (the default branch stays `develop`, so install docs quote `@main`).

## 🟠 Important

### T-02 · Review PR #39 (`kiln --version`) from an outside contributor
- **Type**: task
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: XS · **Owner**: Claude · **Due**: —
- **Origin**: https://github.com/antoine-tena/kiln/pull/39 (issue #35)

The displayed version now comes from `versions.installed_version()`: the PR must use it.
Only antoine-tena merges a PR (CONTRIBUTING.md); answer quickly and say thanks.

### T-03 · Launch kiln publicly, then list it in the Claude Code directories
- **Type**: task
- **Status**: blocked — waiting for T-01, T-11 and T-06
- **Opened**: 2026-10-15
- **Effort**: S · **Owner**: antoine · **Due**: —
- **Origin**: GitHub showcase, 15 October 2026; "Claude Code's workshop" positioning,
  16 October 2026

antoine's goal: lots of stars. Directories take projects that already have users: the launch
comes first. Posts are made by antoine, never without them; Claude drafts the texts.
- [ ] A demo of `kiln new` at the top of the README (GIF or asciinema, issue #38).
- [ ] Show HN (https://news.ycombinator.com/submit), suggested title "Show HN: Kiln – make
  Claude Code build production-grade repos, and keep them that way".
- [ ] r/ClaudeAI (https://www.reddit.com/r/ClaudeAI/submit) and r/ClaudeCode
  (https://www.reddit.com/r/ClaudeCode/submit).
- [ ] awesome-claude-code (55,000 ★): not before **29 October 2026** (repo at least 14 days
  old, or 100 ★), one recommendation at a time, **through the issue form only** (no PR):
  https://github.com/hesreallyhim/awesome-claude-code/issues/new/choose
- [ ] Anthropic's official directory (claude-plugins-official, loaded by default in Claude
  Code): https://clau.de/plugin-directory-submission — after T-06, French plugins are
  unlikely to get in.

### T-11 · Publish kiln on PyPI as `kiln-cli`
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-16
- **Effort**: S · **Owner**: Claude (antoine for the PyPI account) · **Due**: —
- **Origin**: distribution, 16 October 2026

The name `kiln` is taken on PyPI; the package is `kiln-cli`, the command stays `kiln`. Only
the command goes through PyPI: the template, plugins and workflows are still read from the git
repo at the tag (Copier, Claude Code and GitHub Actions cannot read PyPI). Targets: macOS,
Linux and Windows through WSL; native Windows is out of scope (antoine's call, 16 October
2026).
- [ ] Rename the distribution to `kiln-cli` in `pyproject.toml`, and add a `kiln-cli` command
  (same entry point) so that `uvx kiln-cli new` works.
- [ ] `installed_version()`, `kiln doctor` and `maj-kiln`: read the version and offer the
  update through PyPI (`uv tool upgrade kiln-cli`), keeping the install from git.
- [ ] Publishing workflow on the promotion tag, with trusted publishing (no token); antoine
  creates the pending project on https://pypi.org/manage/account/publishing/
- [ ] README (English and French): `uv tool install kiln-cli`, `uvx kiln-cli new`, and the line
  "macOS, Linux, Windows via WSL".

### T-12 · Homebrew formula in an `antoine-tena/homebrew-kiln` tap
- **Type**: improvement
- **Status**: blocked — waiting for T-11
- **Opened**: 2026-10-16
- **Effort**: S · **Owner**: Claude · **Due**: —
- **Origin**: distribution, 16 October 2026

`brew install antoine-tena/kiln/kiln` for macOS and Linux, formula updated on each
promotion. The official homebrew-core requires an already known project: later.

### T-04 · Decide whether annski quotes kiln's workflows at a tag
- **Type**: task
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: XS · **Owner**: antoine · **Due**: —
- **Origin**: move to semver, 15 October 2026

annski is adopted (no template) and quotes the workflows at `@develop`: it gets everything that
lands on `develop`, before any candidate. Pinning it to a tag (`@v0.3.0`) would protect it, at
the cost of a manual update on each release. The user's condition: never break annski.

### T-06 · Translate the command, the template and the plugins into English
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: L · **Owner**: Claude · **Due**: —
- **Origin**: issues #36 (CLI), #37 (README reference), #38 (`kiln new` demo); moved up to 🟠
  on 16 October 2026 (stars goal)

Main obstacle to adoption outside France and to entering the Claude Code ecosystem: the README
is in English, the command, the skills and the generated files are in French. The backlog
(`docs/backlog/`, skill `base:backlog`) is already in English.
- [ ] Command messages in English, French as an option (a `kiln set` setting).
- [ ] Skills and hooks of the plugins (`plugins/`) in English, with English names (`fusion`,
  `nettoyage`, `maj-kiln`…): breaking, in the same minor release as the backlog rename.
- [ ] Generated files (`CLAUDE.md`, charters) in the language chosen at `kiln new` (T-13).

### T-13 · Ask the project's language at `kiln new`, with a per-use option
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-16
- **Effort**: M · **Owner**: Claude · **Due**: —
- **Origin**: language of generated repos, 16 October 2026 (with T-06)

kiln itself is all English; a generated repo is written in its team's language. Code
(identifiers) stays English whatever the answer. Today the generated `CLAUDE.md` imposes French
("Échanges, documentation et messages de commit en français").
- [ ] `copier.yml`: `langue` (English / Français, default English), then `langue_detaillee`
  ("set the language per use?", default no); when yes, `langue_commentaires`, `langue_commits`,
  `langue_docs`, `langue_tickets`, each defaulting to `langue` (`when:` on `langue_detaillee`).
- [ ] The generated `CLAUDE.md` states one rule per use ("comments in French, commits in
  English…") and the language Claude answers in (`langue`).
- [ ] The text of the generated backlog follows `langue_tickets`; its keywords (`Type`,
  `Status`, `todo`, section names) stay English in every language, a single format for the
  status line and the skill.
- [ ] `kiln set langue=…` (and the per-use keys), `kiln new --language`.
- [ ] Ship in the same minor release as T-06 and the backlog rename.

## 🟡 Normal

### T-05 · Check the first real run of the workflows on GitHub
- **Type**: task
- **Status**: blocked — waiting for GitHub billing (CI stopped)
- **Opened**: 2026-10-15
- **Effort**: XS · **Owner**: Claude · **Due**: —
- **Origin**: actions at the workflow's commit, 15 October 2026

kiln's workflows clone kiln at `job.workflow_sha` (an April 2026 property, unknown to
actionlint) with a fallback to `develop`. On the first run, check that the version taken is the
tag's, and that `.kiln` is removed before the project's checks.

### T-07 · Better support for Java projects
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: M · **Owner**: Claude · **Due**: —
- **Origin**: handover of the kiln1 session, 15 October 2026
- [ ] Maven dependency audit in CI (`securite.yml`).
- [ ] `kiln update` bumps the versions in `pom.xml` (today only Dependabot does).
- [ ] `kiln ci` replays `maven.yml`.

## ⚪ Background — long-running work, debt and ideas

### T-08 · Copier migrations for breaking releases
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: M · **Owner**: Claude · **Due**: —
- **Origin**: move to semver, 15 October 2026

In 0.x, a minor release can break. Copier can run a migration when a version is crossed
(`_migrations` in `copier.yml`), but `kiln update` runs Copier with `unsafe=False`, so they do
not run: today a migration lives in kiln's Python code, after Copier (see `src/kiln/backlog.py`
for `docs/a-faire/` → `docs/backlog/`). Watch out: Copier deletes a file the template no longer
has even when the repo edited it; its content is still in the last commit.

### T-09 · Tests running in the main tree during a merge
- **Type**: bug
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: XS · **Owner**: Claude · **Due**: —
- **Origin**: handover of the kiln1 session

plumbum or Copier fails if pytest runs in the main tree in the middle of a merge while a
worktree exists: run the tests in a clean worktree, or make the template test independent of
the tree's state.

### T-10 · Interface polish
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-15
- **Effort**: S · **Owner**: Claude · **Due**: —
- **Origin**: interface redesign, 15 October 2026
- [ ] `kiln check`: the step title and the `✓` line say the same thing (one command per step).
- [ ] Bash completion (`kiln <Tab>`).

---

## ✅ Done

- **2026-10-16** · Backlog in English: `docs/a-faire/` becomes `docs/backlog/` (`backlog.md`,
  `rejected.md`, `urgent.md`), `T-NN` tickets with a type and an opening date, skill
  `base:backlog`, status line reading both formats, old trackers converted by `kiln update`
  (`feat/backlog`).
- **2026-10-16** · "Claude Code's workshop" positioning: tagline "Make Claude Code build
  production-grade repos — and keep them that way." (README, `pyproject.toml`, `CLAUDE.md`,
  welcome subtitle), GitHub repo description and topics (`docs/positionnement`).
- **2026-10-15** · Semver in 0.x, candidates (`-rc.N`) and promotion, `interne` channel,
  `kiln version`, workflows quoted at the exact tag, actions at the workflow's commit
  (`feat/semver`); candidate `v0.3.0-rc.1` adopted by annway, sweep and vision; gitleaks and
  `workflow_call` brought up from annway into the template (`feat/secrets-scan`).
- **2026-10-15** · Interface (banner, welcome screen, spinner, summary), `kiln doctor`, prefixed
  output of `kiln dev`, debt (typed status line and `charte`), command tests and pytest-xdist,
  English GitHub showcase.
