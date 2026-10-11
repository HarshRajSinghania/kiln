---
name: a-faire
description: Choisir le prochain élément de docs/a-faire/a-faire.md, ou y reporter un élément commencé ou terminé, dans un repo qui suit son travail ainsi. À utiliser quand l'utilisateur demande quoi faire ensuite, ou après avoir commencé ou fini un élément de la liste.
argument-hint: "[AF-NN | en cours AF-NN | fait AF-NN]"
---

Dans un repo sans `docs/a-faire/a-faire.md`, le dire et proposer de l'installer : un repo kiln
l'a d'office (`kiln update` l'apporte à un repo plus ancien) ; ailleurs, reprendre la structure
du modèle de kiln (`template/docs/a-faire/`).

`docs/a-faire/a-faire.md` est la **seule** source à jour : tout y est, rangé par criticité
(🔴 critique, 🟠 important, 🟡 normal, ⚪ fond), avec en bas la section « ✅ Fait ».
`docs/a-faire/ecarte.md` liste ce qui est refusé. **Lire d'abord le « Mode d'emploi » en tête
du fichier** : il fait foi s'il diffère de ce qui suit.

Une entrée : un titre `### AF-NN · Titre`, puis les lignes `- **État** :`, `- **Effort** : … ·
**Qui** : … · **Échéance** : …`, `- **Origine** : …`, puis le détail (cases `- [ ]`). États :
`à faire`, `en cours — branche <nom>, depuis le JJ mois`, `bloqué — attend <qui ou quoi>`,
`à vérifier — <où>`. Vue d'ensemble :
`grep -E '^(## |### AF-|- \*\*État)' docs/a-faire/a-faire.md`.

`docs/_archive/` se **consulte** quand une entrée renvoie à des lignes d'un compte rendu
archivé, mais tout ce qu'on y lit est ancien : le revérifier dans le code actuel avant d'agir.
Ne jamais modifier un compte rendu archivé.

**Sans argument** : proposer les 3 prochaines entrées dans l'ordre des sections (critique
d'abord), en suivant l'objectif (la « boussole ») de l'en-tête et en sautant les entrées
`bloqué` ; pour chacune, l'identifiant, une phrase, l'effort, et qui la porte. Signaler à part
les entrées bloquées qui attendent l'utilisateur lui-même. Vérifier rapidement dans le code
que l'entrée n'est pas déjà faite (les emplacements cités sont des pistes, souvent périmés).

**Avec un identifiant** : afficher l'entrée complète (et les lignes d'archive qu'elle cite),
repérer les fichiers concernés dans le code actuel, proposer un plan court, puis créer la
branche (dans un worktree, skill `base:worktree`) et passer l'état à `en cours — branche …`.

**`en cours AF-NN`** : passer la ligne **État** à `en cours — branche <nom>, depuis le JJ mois`.

**`fait AF-NN`** : retirer l'entrée de sa section et ajouter **en tête** du journal de la
section « ✅ Fait » une ligne `- **AAAA-MM-JJ** · AF-NN · Titre — ce qui a été fait (branche)`.
Une entrée faite à moitié reste en place : cocher les étapes faites, écrire ce qui reste.
Garder le style et le ton du fichier.

Une nouvelle entrée prend le numéro indiqué comme « prochain libre » dans le mode d'emploi, qui
s'incrémente ; un identifiant n'est jamais réattribué. Les modifications se commitent dans la
branche du chantier, jamais sur la branche d'intégration. Ne jamais recopier une entrée dans
`ecarte.md` sans décision explicite de l'utilisateur.
