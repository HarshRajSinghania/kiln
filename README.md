<div align="center">

# kiln 🔥

**Make Claude Code build production-grade repos — and keep them that way.**

[![CI](https://github.com/antoine-tena/kiln/actions/workflows/kiln.yml/badge.svg?branch=develop)](https://github.com/antoine-tena/kiln/actions/workflows/kiln.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Built on Copier](https://img.shields.io/badge/built%20on-Copier-8a2be2.svg)](https://copier.readthedocs.io)
[![Claude Code plugins](https://img.shields.io/badge/Claude%20Code-plugins-d97757.svg)](#claude-code-plugins)

*English · [Français](README.fr.md)*

<img src="docs/assets/kiln-accueil.svg" alt="kiln welcome screen: a pixel-art kiln and the list of commands" width="720">

</div>

---

Claude Code writes code fast, but a real repo needs more than a prompt: an up-to-date stack,
rules the agent cannot talk its way around, a sane git workflow, and someone to stop the repo
from going stale on day ninety. **kiln** brings all four. Built on
[Copier](https://copier.readthedocs.io), it generates the repo, wires Claude Code into it, and
keeps every repo you own current:

- 🧱 **`kiln new`** — asks what you are building, recommends a stack, and generates a complete
  repo: code, tests, linters, CI, pre-commit, containers, a `CLAUDE.md` for AI agents, a GitHub
  repo with protected branches.
- 🎛️ **`kiln set`** — change your mind later. `kiln set frontend=nuxt podman=true` re-renders
  the repo; a removed framework takes its files with it.
- 🔄 **`kiln update`** — pull template improvements *and* dependency upgrades into an existing
  repo, then run the checks before anything is committed. Local edits are kept; real conflicts
  are marked inline.
- 🚚 **`kiln update --all`** — do it for **every** kiln repo in `~/code` at once: one worktree
  per repo, small commits, merge only when the checks pass.
- 📏 **`charte`** — a rule engine for things linters don't catch (no `pip`/`docker`, file-size
  ratchets, Django locks, personal-data patterns, coverage floors…), declared per repo in
  `charte.toml`. Disagree with a rule? Waive it in `kiln-waivers.toml`, with a reason and an
  expiry that grows with each renewal (a week, a month, three months, six months).
- 🤖 **Claude Code native** — every generated repo ships agent instructions and enables kiln's
  Claude Code plugins (branch guards, worktree/merge/release skills, status line).

> [!NOTE]
> kiln was born to run a real production app (a non-profit's Django + Nuxt site) and the
> repos around it. **Its CLI messages and generated docs are currently in French**; this README
> is in English and translating the CLI is the [#1 help-wanted item](https://github.com/antoine-tena/kiln/issues/36).

## Quick start

```sh
# 1. Install (needs uv and git; Python 3.14 is fetched by uv if missing).
#    macOS, Linux, and Windows through WSL. The PyPI package is kiln-cli, the command is kiln.
uv tool install kiln-cli
#    …or try it without installing anything: uvx kiln-cli new my-app

# 2. Create a project — answer a few questions, or pass them as flags
kiln new my-app
kiln new my-api --size ember --type api --backend fastapi --no-github

# 3. Work in it
cd my-app
kiln dev       # start the dev servers of the stack
kiln check     # ruff, mypy, pytest, ESLint, type checks, then charte

# 4. Months later
kiln update            # template changes + compatible dependency upgrades + checks
kiln update --major    # major versions too
```

`kiln new` creates a private GitHub repo by default (via `gh`); `--no-github` skips it.
Optional tools: [pnpm](https://pnpm.io/) for JavaScript fronts, a JDK 25 for Java,
[podman](https://podman.io/) for containers.

## What you get

| Project type | Recommended backend | Recommended frontend |
|---|---|---|
| Full app (`app`) | Django + Django Ninja | Nuxt + Vue |
| API only (`api`) | FastAPI | — |
| Content site (`site`) | — | Astro |
| Data dashboard (`tableau`) | Python data (polars, marimo, Plotly) | Streamlit |
| Data analysis (`analyse`) | Python data | — |
| CLI tool (`outil`) | Python CLI (argparse, installable) | — |

Backends: `django`, `fastapi`, `data`, `cli`, `java` (Java 25 + Maven, no framework).
Frontends: `nuxt`, `next`, `astro`, `streamlit`, `dash`. **Every combination is generated and
validated by the test suite.**

Each generated repo comes with:

- **Opinionated tooling, no `pip`, no `docker`:** uv for Python, pnpm for JavaScript, podman
  for containers; ruff, mypy (strict), pytest + coverage floor, ESLint, pre-commit (which also
  refuses commits on `main`/`develop`).
- **CI on GitHub Actions** that calls kiln's reusable workflows — so fixing CI once in kiln
  fixes it everywhere.
- **A project size** (`spark` → `ember` → `flame` → `blaze`) that tunes defaults: a weekend
  script doesn't get the same ceremony as a multi-team service.
- **Agent-ready docs:** `CLAUDE.md` at the root and per sub-project, with stable rule IDs the
  `charte` engine can check.
- **Optional production setups:** a hardened VPS deployment for Django (Caddy with automatic
  TLS, read-only containers, one image per commit, automatic rollback, daily backups with
  restore tests) and Vercel deployment for Nuxt fronts.
- **A backlog** (`docs/backlog/`: typed `T-NN` tickets by priority) that Claude Code's status line counts.

## Why not just Copier / cookiecutter?

kiln **is** Copier underneath — every project keeps its `.copier-answers.yml`, so you can
always fall back to plain Copier. What kiln adds is everything around the template:

| | cookiecutter | Copier | **kiln** |
|---|:---:|:---:|:---:|
| Generate a project | ✅ | ✅ | ✅ |
| Apply template updates to existing projects | ❌ | ✅ | ✅ |
| Stack recommendation from the project type | ❌ | ❌ | ✅ |
| Change stack/options after generation (`kiln set`) | ❌ | partial | ✅ |
| Upgrade dependencies + run checks in the same step | ❌ | ❌ | ✅ |
| Update all your repos at once (`update --all`) | ❌ | ❌ | ✅ |
| Shared, reusable CI workflows | ❌ | ❌ | ✅ |
| Repo-level rule engine (`charte`) | ❌ | ❌ | ✅ |
| Replay CI locally, verdict stored as a git note (`kiln ci`) | ❌ | ❌ | ✅ |
| Claude Code plugins and agent instructions | ❌ | ❌ | ✅ |

kiln is opinionated on purpose. If you want a neutral templating engine, use Copier directly;
if you want a batteries-included workflow that stays maintained, use kiln — or fork it and
make the opinions yours.

## Commands

| Command | What it does |
|---|---|
| `kiln new [dir]` | Questionnaire, generation, lockfiles, install, first commit on `main`, then `develop` where all work happens. |
| `kiln install` | Set up a machine after a clone: tools, dependencies, `.env`, migrations, pre-commit. Re-runnable. |
| `kiln dev` | Start the stack's dev servers, their output interleaved and prefixed by service in colour (`django │ …`); `--containers` runs everything in podman. |
| `kiln check` | Ruff, mypy, pytest for each Python project, ESLint and type checks for the front, then `charte`. |
| `kiln set [key=value…]` | Show or change the repo's settings (team, frameworks, podman…); the repo is re-rendered. |
| `kiln update` | Move to the latest kiln release (with a box listing what's new in each release crossed), compatible dependency upgrades, then checks. `--major`, `--no-template`, `--no-deps`. |
| `kiln update --all` | Update every kiln repo in your code folder, one worktree each, merged only if checks pass. |
| `kiln status` | Branch, clean tree, template release (`v0.3.2 → v0.3.5` when behind), stack — for every kiln repo. |
| `kiln version` | In kiln's own repo: latest public release, candidates (age, adopting repos, ready to promote) and the number the next release should take. |
| `kiln doctor` | Check the machine (git, uv, gh login, pnpm, podman, Java, pre-commit, kiln release, Claude plugin) and the current repo; each problem comes with the command that fixes it. Changes nothing. |
| `kiln ci [commit]` | Replay the repo's GitHub CI locally against throwaway PostgreSQL/Redis, and push the verdict as a git note. |
| `kiln contrat` | Django + Nuxt: export `openapi.json` and regenerate the front's API types. |
| `charte` | Check the repo against its `charte.toml` (`--detail`, `types`, `couverture`). |

Full reference (in French): [README.fr.md](README.fr.md#commandes).

## Reusable GitHub workflows

kiln's workflows work from any repository, kiln-generated or not:

```yaml
jobs:
  backend:
    uses: antoine-tena/kiln/.github/workflows/django.yml@v0.3.0   # a kiln release tag
```

`django.yml`, `python.yml`, `maven.yml`, `pnpm.yml`, `charte.yml`, `securite.yml` (`uv audit`,
`pnpm audit`), `contrat-api.yml`, `infra.yml` (podman build, actionlint, shellcheck),
`sbom.yml` (CycloneDX), `mutation.yml` (mutmut), `vercel.yml`. Databases for tests run in
podman. See [`.github/workflows/`](.github/workflows/).

## Claude Code plugins

kiln is also a [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace:

```sh
claude plugin marketplace add antoine-tena/kiln
claude plugin install base@kiln
```

| Plugin | What's inside |
|---|---|
| `base` | Skills for the git workflow (`worktree`, `fusion` = merge, `version` = release, `nettoyage` = cleanup, `backlog`, `maj-kiln` = self-update), `report-to-kiln` (a kiln defect met in your repo becomes an issue or a PR, posted once you approve) and `token` (a service token pasted once into a git-ignored `.<service>/` folder, never shown); hooks that guard protected branches and files, check each edited file, and offer kiln updates at session start; a shared status line in four styles (`kiln set statusline=…`, or `aucune` / `perso` to keep your own); condensed command output with [rtk](https://github.com/rtk-ai/rtk). |
| `pile-django` | Migrations, API regeneration, read-only PostgreSQL. |
| `pile-nuxt` | Nuxt / Vue / Vitest skills, UI polish, screenshots on three phones and a desktop (Playwright). |
| `vps-podman` | Deploy, production logs, production dumps. |
| `stripe` | Stripe MCP in test mode. |
| `serena` | Read-only [Serena](https://github.com/oraios/serena) MCP for symbol navigation in big repos. |

Generated repos enable the right plugins for their stack automatically.

## Status

kiln is used daily on a handful of real repos, including one in production. It is young, so it
numbers releases like Claude Code does: in `0.x`, every release bumps the patch, breaking changes
included (`0.3.4 → 0.3.5`), listed first in the release notes and migrated by `kiln update`; the
minor only moves for a milestone. Strict semver starts at 1.0. Each release is first a candidate
(`v0.3.5-rc.1`) used on the author's own repos; it is promoted to `main` (`v0.3.5`) only once
the next candidate is ready, so a release never needs an emergency fix. Projects are generated and updated from the latest release, pin kiln's workflows to
that exact tag, and `kiln update` shows what changed in each release it applies (see
[`CHANGELOG.md`](CHANGELOG.md)).
Linux, WSL and macOS are supported.

## Contributing

Issues and pull requests are very welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Small fixes can go straight to a PR; for bigger changes, open an issue first so we agree on
the approach. Good places to start: the
[`good first issue`](https://github.com/antoine-tena/kiln/labels/good%20first%20issue) label.
Using Claude Code in a kiln repo? `/base:report-to-kiln` turns a kiln defect into a
ready-to-post issue or PR: checked against the latest release and the existing issues, scrubbed
of anything private, posted only once you approve.

If kiln saves you time, a ⭐ helps other people find it.

## License

[MIT](LICENSE)
