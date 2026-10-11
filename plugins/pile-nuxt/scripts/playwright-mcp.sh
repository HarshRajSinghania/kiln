#!/bin/sh
# Lance le serveur MCP playwright sur le Chromium de Playwright, sans fenêtre (WSL n'a pas
# d'affichage) et avec un profil en mémoire : deux worktrees ou deux sessions ne se disputent
# pas le même profil. Le canal « chrome » par défaut exigeait Google Chrome dans /opt.
# Le Chromium attendu par cette version du MCP s'installe au premier lancement (quelques
# secondes ensuite, quand il est déjà là) : un worktree neuf ou un poste neuf n'a rien à faire.
VERSION=0.0.83
npx -y -p "@playwright/mcp@$VERSION" playwright-core install chromium >/dev/null 2>&1
exec npx -y "@playwright/mcp@$VERSION" --browser chromium --headless --isolated "$@"
