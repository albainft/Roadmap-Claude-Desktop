# Roadmap

Une feuille de route en deux couches : un index Markdown court (`ROADMAP.md`, une ligne par tâche) et une note par tâche (`notes/`), avec son TL;DR, son statut, sa prochaine étape et son historique. Un script écrit les notes sans les casser, un autre affiche le tout comme une liste de tâches interactive : thèmes, statut et environnement de chaque tâche, recherche, filtres, tri, détail et historique. Aucune dépendance : Python 3 seulement.

![Aperçu large](images/apercu.png)

![Aperçu étroit](images/apercu-etroit.png)

## Pourquoi deux couches
L'index reste assez court pour être lu en entier par une personne ou par un assistant (environ 5 Ko pour 50 tâches). Le détail, le TL;DR et l'historique vivent dans les notes et ne se lisent que quand on en a besoin. Le journal n'est plus un fichier à part : c'est la somme des historiques des notes.

## Contenu du dépôt
- `ROADMAP.md` : l'index d'exemple (thèmes, tâches, parqué).
- `notes/` : les notes d'exemple (`A1.md`, `themes/T1.md`, `parque/P1.md`, `journal/2026-01.md`).
- `roadmap_notes.py` : crée et modifie les notes, recalcule les lignes dérivées de l'index, contrôle la cohérence.
- `gen_roadmap_html.py` : écrit `docs/index.html` (page complète, GitHub Pages) et `docs/index.artifact.html` (contenu seul, pour un artefact Claude Desktop).
- `claude-skill/ROADMAP/SKILL.md` : un skill Claude Code prêt à copier dans `.claude/skills/ROADMAP/`.

## Utilisation
```bash
python3 roadmap_notes.py new A6 --theme T1 --titre "Préparer la démonstration" --tldr "Scénario de dix minutes pour les clients pilotes." --prochaine "Écrire le scénario" --env prod
python3 roadmap_notes.py maj A6 statut=cours --journal "scénario écrit, répétition lundi"
python3 roadmap_notes.py done A6 "démonstration faite devant deux clients"
python3 roadmap_notes.py sync        # recalcule « Prochaine action », « Statut », la date de mise à jour
python3 roadmap_notes.py check       # index et notes cohérents ?
python3 roadmap_notes.py journal --depuis 7
python3 gen_roadmap_html.py ROADMAP.md docs/index.html
```
Il n'y a pas de commande `park` : parquer une tâche, c'est retirer sa ligne du thème, ajouter `- Pn titre` sous `## Parqué` (`new Pn --titre … --tldr … --prochaine …` crée la note et la ligne) puis lancer `sync`.

`--roadmap FICHIER` et `--notes DOSSIER` (ou les variables `ROADMAP` et `ROADMAP_NOTES`) changent les emplacements : les notes peuvent être la copie locale d'un dossier Nextcloud ou d'un coffre Obsidian.

Options de la page : `--notes=DOSSIER`, `--notes-url=URL/` (ajoute un bouton « Ouvrir la note » vers `URL/<ID>.md`) et `--launch="/commande {id}"` : chaque tâche ouverte reçoit un bouton « Lancer » qui envoie la commande à Claude, avec l'identifiant de la tâche (l'artefact doit alors déclarer la capacité `comments`).

## Format de l'index
- `# Titre`, puis `Dernière mise à jour : AAAA-MM-JJ.`
- `## Thèmes actifs`, avec un `### T1. Titre` par thème : lignes `Statut :`, `Objectif :`, `Prochaine action :`, `Bloqueur :`, puis les tâches. `Statut` et `Prochaine action` sont écrits par `sync`.
- Tâche ouverte : `- [ ] A3 Titre court`. Tâche faite : `- [x] A1 Titre court`. Les tâches ouvertes se placent avant les faites.
- Balises facultatives en tête de ligne : `- [ ] A4 [robot] [✓plan] Titre court`. Elles s'affichent en pastilles (`[✓plan]` en vert, `[plan:⏳]` en gris, les autres en violet) : à vous d'en choisir le vocabulaire, par exemple pour marquer ce qu'un robot peut traiter.
- `## Vérifications du lendemain (date)` : même format de tâche. `## Parqué` : `- P1 Titre court`, avec sa note `notes/parque/P1.md`.

## Format d'une note
```
---
id: "A3"
titre: "Valider les écrans de paiement"
theme: "T1"
statut: "cours"
env: [prod]
tldr: "Maquettes envoyées à deux clients pilotes ; retours attendus avant la fin du mois."
prochaine: "Relancer les deux clients le 2026-01-26"
maj: "2026-01-12"
---

# A3. Valider les écrans de paiement

## Détail
Texte complet.

## Historique
- 2026-01-12 17:05 : A3 maquettes envoyées.
```
Statuts : `fait`, `next` (prochaine action), `cours`, `decision` (attente de décision), `wait` (en attente), `plan` (planifié), `todo`. La première tâche ouverte d'un thème s'affiche toujours « Prochaine action ». Les notes de thème (`themes/Tn.md`) portent `tldr` et `verifie` (date de la dernière vérification).

## Sans notes
Si le dossier `notes/` n'existe pas, la page fonctionne comme avant : tout est dans `ROADMAP.md`, les statuts sont déduits du texte (« à valider », « dépend de », « à partir du AAAA-MM-JJ », « fait le AAAA-MM-JJ »), les environnements de mots-clés (liste `ENVS` en haut du script) et le journal d'une section `## Journal`.

## Environnements
Chaque tâche reçoit jusqu'à trois étiquettes de couleur : sécurité, infra, code, automatisation, communication, données, produit, exploitation. Avec des notes, elles viennent du champ `env` (`secu`, `infra`, `code`, `auto`, `comm`, `data`, `prod`, `ops`). Adaptez la liste `ENVS` à votre projet.

## Publier la page
Réglages GitHub : Pages, branche `main`, dossier `/docs`. Pour l'artefact Claude Desktop, publiez `docs/index.artifact.html`.

## Réalisation
L'intégralité de ce projet (scripts, page, exemple, README) a été réalisée avec Claude Code, et la page est publiée comme artefact dans Claude Desktop.

## Licence
MIT, voir `LICENSE`.
