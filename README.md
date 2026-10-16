<div align="center">

# kiln 🔥

**Make Claude Code build production-grade repos — and keep them that way.**

[![CI](https://github.com/antoine-tena/kiln/actions/workflows/ci.yml/badge.svg)](https://github.com/antoine-tena/kiln/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/kiln-cli.svg)](https://pypi.org/project/kiln-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Built on Copier](https://img.shields.io/badge/built%20on-Copier-8a2be2.svg)](https://copier.readthedocs.io)
[![Claude Code plugins](https://img.shields.io/badge/Claude%20Code-plugins-d97757.svg)](#claude-code-plugins)

*English · [Français](README.fr.md)*

<img src="docs/assets/kiln-accueil.svg" alt="kiln welcome screen: a pixel-art kiln and the list of commands" width="720">

</div>

---

kiln is a project generator and maintainer for Claude Code. It scaffolds production-ready repositories with the stack of your choice, then keeps them up to date with the template, the dependencies, and the rules you set.

The CLI is in French for now (the author is French and the first users too). The documentation is in English and translating the CLI is the [#1 help-wanted item](https://github.com/antoine-tena/kiln/issues/36).

## Quick start

```sh
# 1. Install (needs uv and git; Python 3.14 is fetched by uv if missing).
#    macOS, Linux, and Windows through WSL. The PyPI package is kiln-cli, the command is kiln.
uv tool install kiln-cli
#    …or try it without installing anything: uvx kiln-cli new my-app

# Shell completion (bash):
# eval "$(kiln completion bash)"   # add to ~/.bashrc

# 2. Create a project — answer a few questions, or pass them as flags
kiln new my-app
kiln new my-api --size ember --type api --backend fastapi --no-github
```

The rest of the original README content would be here, but for brevity in this call we note the change is the addition of the shell completion lines above. In practice the full file is used.
