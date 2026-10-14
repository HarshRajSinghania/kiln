---
name: apercu
description: Voir une page ou une fenêtre du front comme les utilisateurs - une capture sur trois téléphones (iPhone 16, Galaxy A55, Galaxy S24) et un ordinateur (1920 × 1080), connecté ou non, puis les regarder. À utiliser pour vérifier un rendu (nouvelle page, fenêtre, retouche visuelle, débordement sur mobile) ou quand l'utilisateur demande de « voir » quelque chose sur mobile et sur ordinateur.
argument-hint: "<chemin ou URL> [compte]"
---

Le script `apercu.mjs` est dans le dossier `scripts/` du plugin, deux niveaux au-dessus de
cette skill (`<dossier de la skill>/../../scripts/apercu.mjs`). Il prend le Chromium de
Playwright du projet : rien à installer.

1. **Le site doit répondre** : la base est `url=` de `.playwright/config` (sinon
   `http://localhost:3000`). S'il ne répond pas (`curl -s -o /dev/null -w '%{http_code}'`),
   le lancer par la skill de serveur de dev du projet s'il en a une (`dev`), sinon
   `pnpm dev` en arrière-plan, et attendre qu'il réponde.
2. **Capturer**, depuis le dossier du front (celui qui a `@playwright/test`) :
   ```bash
   node <scripts>/apercu.mjs /account/profile --compte member --attendre '[role=dialog]' --nom nouveautes
   ```
   - `--compte <nom>` : se connecter avec `login_<nom>` de `.playwright/config` (mot de passe :
     `.playwright/token`) ; `--compte defaut` prend `login=`. Sans `--compte` : visiteur.
     Chaque appareil part d'un navigateur neuf (localStorage vide) : une fenêtre « vue une
     fois » s'y rouvre.
   - `--attendre <sélecteur>` : attendre un élément (une fenêtre, un tableau chargé) avant la
     capture ; `--pleine-page` : toute la hauteur ; `--sortie` : autre dossier que
     `.playwright/captures/apercu/`.
   Le script écrit une ligne par appareil : nom, fichier, et `DÉBORDEMENT HORIZONTAL` si la page
   est plus large que l'écran.
3. **Regarder les quatre captures** (outil Read sur chaque PNG) et juger : rien de coupé ni de
   superposé, textes lisibles sans zoom, zones tactiles assez grandes, fenêtre entière à
   l'écran, pas de débordement. Le design du projet (skill `design-system` s'il y en a une)
   fait foi.
4. **Rendre compte** appareil par appareil, court : ce qui va, ce qui ne va pas avec la capture
   en cause, et la correction proposée. Corriger seulement si l'utilisateur l'a demandé.

Les comptes de `.playwright/config` peuvent agir sur la production quand le front parle à l'API
de prod : ne rien acheter, ne rien envoyer, regarder seulement.
