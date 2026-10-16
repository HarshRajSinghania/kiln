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
  before 16 October 2026 were `AF-NN`, same number). **Next free: T-20.**
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

### T-14 · Promote v0.3.1, the first release on PyPI
- **Type**: task
- **Status**: blocked — waiting for antoine (delete the old token)
- **Opened**: 2026-10-16
- **Effort**: XS · **Owner**: antoine, then Claude · **Due**: —
- **Origin**: promotion of v0.3.0, 16 October 2026

`v0.3.1` is promoted and `kiln-cli 0.3.1` is on PyPI (16 October 2026); `v0.3.2-rc.2` is the
candidate followed by annway, sweep and vision.
- [x] Cut `v0.3.2-rc.1`, then `-rc.2` (tests independent of the machine's git config); the
  `CHANGELOG.md` entry credits #39 (@SakarPaisen). `kiln update --all` done.
- [x] Promote `v0.3.1`, `pypi` run green, `uvx --from kiln-cli==0.3.1 kiln` works on an empty
  uv cache.
- [x] README (English and French): `uv tool install kiln-cli` as the main install.
- [x] Token scoped to `kiln-cli` in `.pypi/token`, `PYPI_TOKEN` secret updated (16 October
  2026); it is first used by the promotion of `v0.3.2`.
- [ ] antoine deletes the old account-wide token on https://pypi.org/manage/account/token/

## 🟠 Important

### T-03 · Launch kiln publicly, then list it in the Claude Code directories
- **Type**: task
- **Status**: blocked — waiting for T-14 and T-06
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

### T-12 · Homebrew formula in an `antoine-tena/homebrew-kiln` tap
- **Type**: improvement
- **Status**: blocked — waiting for demand (an issue asking for it) or homebrew-core notability
- **Opened**: 2026-10-16
- **Effort**: S · **Owner**: Claude · **Due**: —
- **Origin**: distribution, 16 October 2026

`brew install antoine-tena/kiln/kiln` for macOS and Linux, formula updated on each
promotion. Not now (antoine, 16 October 2026): kiln needs uv anyway, so
`uv tool install kiln-cli` covers its users, and a formula lists ~30 dependencies to keep up
to date. The tap https://github.com/antoine-tena/homebrew-kiln is created to keep the name
(README only, issues off). The official homebrew-core requires an already known project.

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
  `nettoyage`, `maj-kiln`…): breaking, in the same release as the backlog rename.
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
- [ ] Ship in the same release as T-06 and the backlog rename.

## 🟡 Normal

### T-18 · Promoting a release makes `kiln update` conflict on `ci.yml`
- **Type**: bug
- **Status**: todo
- **Opened**: 2026-10-16
- **Effort**: S · **Owner**: Claude · **Due**: —
- **Origin**: `kiln update --all` to `v0.3.2-rc.2`, right after the promotion of `v0.3.1`

annway, sweep and vision stopped on conflicts in `.github/workflows/ci.yml`, only on the
`@<tag>` of kiln's workflows (`v0.3.1-rc.1` before, `v0.3.2-rc.2` after); resolved by hand by
taking the new side. Lead: `v0.3.1` now sits on the same commit as `v0.3.1-rc.1`, so Copier's
render of the old version may describe it as `v0.3.1` and no longer match the project's file
(`kiln_ref` in `template/.github/workflows/ci.yml.jinja`, from `_commit`). It will come back at
every promotion.
- [ ] Reproduce in a test (template tagged `-rc.1`, then the release on the same commit).
- [ ] Fix the cause, or let `kiln update` resolve by itself a conflict that only moves the
  `@<tag>` of kiln's workflows.

### T-19 · kiln has no pre-push hook: mypy errors reach `develop`
- **Type**: improvement
- **Status**: todo
- **Opened**: 2026-10-16
- **Effort**: XS · **Owner**: Claude · **Due**: —
- **Origin**: CI of `develop` red after `feat/waivers`, 16 October 2026

`base:fusion` says typing runs before the push (pre-push hook), but kiln's own checkout has
none (`.git/hooks/` only has samples): 4 mypy errors in the waiver tests reached `develop` and
made its CI red. Give kiln the same pre-push hook as the generated repos (`uv run mypy src
tests`), installed by `kiln install`.

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

In 0.x, any release can break (patch-first numbering, CLAUDE.md "Versions"). Copier can run a migration when a version is crossed
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
the tree's state. Seen again on 16 October 2026 (merge of `feat/relecture`, briefly filed as
T-17): 97 tests fail with `fatal: No url found for submodule path
'.claude/worktrees/chore-versions' in .gitmodules`; the same commit passes in a clean
worktree. Lead to check: with a dirty template, Copier copies it and runs `git add -A`, which
takes the nested worktrees as gitlinks; `.claude/worktrees/` is only ignored in
`.git/info/exclude`, which the copy does not carry.
- [ ] Reproduce, confirm the cause.
- [ ] Fix: `.claude/worktrees/` in kiln's `.gitignore`, or tests that render from a clean
  source (`vcs_ref="HEAD"` as in `test_deploiement.py`).

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

- **2026-10-16** · T-16 · A failed `kiln update --all` leaves a worktree that blocks the next
  run — a worktree with no change and no commit of its own is removed after the failure and
  before the next run; one with work in it is kept and named (`fix/update-reseau`) · opened 2026-10-16
- **2026-10-16** · T-15 · `kiln update --all` crashes with a Python traceback when GitHub is
  unreachable — Copier's git failure becomes one line in the summary, "GitHub injoignable"
  when the network is down (`fix/update-reseau`) · opened 2026-10-16
- **2026-10-16** · T-11 · Publish kiln on PyPI as `kiln-cli` — distribution and `kiln-cli`
  command, install source and update through PyPI, `pypi.yml` on the promotion tag, README;
  the first upload is checked by T-14 · opened 2026-10-16

- **2026-10-16** · T-01 · Promote v0.3.0, the first public release — `v0.3.1-rc.1` cut, then
  `v0.3.0` tagged on the commit of `v0.3.0-rc.1`, merged into `main`, back into `develop`;
  annway, sweep and vision moved to `v0.3.1-rc.1` (`kiln update --all`) · opened 2026-10-15
- **2026-10-16** · T-02 · Review PR #39 (`kiln --version`) from an outside contributor —
  reviewed with the new skill `base:contribution`, version computed only on demand (commit
  pushed on top of the contributor's), merged (`b71f91a`), issue #35 closed; credit to add to
  the next changelog entry (T-01) · opened 2026-10-15
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
