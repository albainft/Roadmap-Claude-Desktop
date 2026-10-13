---
description: Feuille de route unique : vue d'ensemble, prochaine action, ajouter, clore, parquer, vérifier
argument-hint: [vue | next | add <thème> <tâche> | done <id> | park <id> | check]
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
model: sonnet
---

# /ROADMAP

Source unique : `ROADMAP.md` (l'index) ; le détail vit dans `notes/`. Réponses courtes, en français, aucune valeur secrète dans la feuille de route. Adaptez les chemins à votre projet (voir le README du dépôt). Argument : $ARGUMENTS

## Structure
- `### Tn. Titre` : un thème actif, avec `Statut`, `Objectif`, `Prochaine action`, `Bloqueur` (`Statut` et `Prochaine action` sont recalculés par `sync`, ne pas les écrire à la main), puis les tâches : d'abord les ouvertes `- [ ] <id> [balises] titre court`, puis les faites `- [x] <id> titre court`.
- `## Parqué` : une ligne `- Pn titre court` par élément, avec sa note `notes/parque/Pn.md`.
- 3 thèmes actifs au plus ; une seule prochaine action par thème, la première tâche non cochée.
- Balises facultatives en tête de ligne, par exemple `[robot] [✓plan]` : elles s'affichent en pastilles.

## Notes
Une note par tâche (`notes/<ID>.md`), thème (`notes/themes/Tn.md`) ou parqué (`notes/parque/Pn.md`) ; en-tête : `id`, `titre`, `theme`, `statut` (`fait next cours decision wait plan todo`), `env`, `tldr`, `prochaine`, `maj`, `fait`. Toujours passer par `python3 roadmap_notes.py` :
- `new <id> --titre "…" --tldr "…" --prochaine "…" --theme Tn [--statut todo --env infra,auto --detail "…"]` crée la note et la ligne de l'index ;
- `maj <id> statut=cours tldr="…" prochaine="…" [--ajout "paragraphe"] [--journal "entrée"]` modifie une note ;
- `done <id> "ce qui a été fait"` coche la tâche, la range après les ouvertes, passe la note à `fait` et journalise ;
- `journal "<id> : texte" [--tache <id>]` ajoute une entrée datée ; `journal --depuis 7` liste les entrées récentes ;
- `sync` recalcule les lignes dérivées ; `check` compare l'index et les notes ; `index` liste les notes.
Le TL;DR tient en une ou deux phrases simples ; la prochaine étape en une phrase ; les deux se mettent à jour à chaque changement d'état.

## Sous-commandes
**vue** (par défaut) : lire `ROADMAP.md` et afficher un tableau compact (thème, statut, prochaine action, bloqueur, nombre de tâches ouvertes), puis les vérifications non cochées et le nombre d'éléments parqués.
**next** : donner la seule prochaine action du premier thème non bloqué et, en une phrase, pourquoi elle passe avant les autres.
**add <thème> <tâche>** : prochain identifiant libre du préfixe du thème, `new`, puis `sync`. Refuser un quatrième thème actif et proposer de parquer un thème existant.
**done <id>** : `done`, puis `sync` et régénérer la vue (`python3 gen_roadmap_html.py ROADMAP.md docs/index.html`).
**park <id>** : retirer la ligne du thème, ajouter `- Pn titre` sous `## Parqué`, créer la note de parqué avec ce qui la débloquerait, puis `sync`.
**check** : `python3 roadmap_notes.py check`, puis vérifier l'état réel de chaque tâche cochée sans vous fier à la note.

## Contrôle après toute modification
Relire `ROADMAP.md` : 3 thèmes actifs au plus, une prochaine action par thème, aucun identifiant en double, `roadmap_notes.py check` sans écart. Régénérer la page : `python3 gen_roadmap_html.py ROADMAP.md docs/index.html`.
