# Feuille de route : exemple

Index de référence de ce dépôt : une ligne par tâche (case, identifiant, balises éventuelles, titre court). Le détail, le TL;DR, le statut, l'environnement, la prochaine étape et l'historique de chaque tâche sont dans sa note `notes/<ID>.md` ; un thème dans `notes/themes/Tn.md`, un élément parqué dans `notes/parque/Pn.md`. Remplacez cet exemple par votre propre feuille de route. Dates au format AAAA-MM-JJ.
Dernière mise à jour : 2026-01-15.

## Thèmes actifs

### T1. Lancement de la version 1.0
Statut : en cours (vérifié le 2026-01-15)
Objectif : publier une première version utilisable par dix clients pilotes.
Prochaine action : A3 Relancer les deux clients le 2026-01-26, puis ajuster le parcours d'achat
Bloqueur : aucun.
- [ ] A3 Valider les écrans de paiement
- [ ] A4 [robot] [✓plan] Mettre en place la sauvegarde nocturne de la base de données
- [ ] A5 Rédiger le guide d'installation
- [x] A1 Choisir l'hébergement
- [x] A2 Déployer le prototype sur le serveur de test

### T2. Qualité et retours utilisateurs
Statut : à concevoir (vérifié le 2026-01-15)
Objectif : réduire les incidents et répondre aux clients pilotes en moins de deux jours.
Prochaine action : B1 Proposer trois indicateurs et leurs seuils à l'équipe
Bloqueur : attend la fin de A4 pour mesurer les sauvegardes.
- [ ] B1 Définir les indicateurs de qualité
- [ ] B2 Mettre en place les notifications d'incident
- [ ] B3 Automatiser le rapport hebdomadaire

## Vérifications du lendemain (2026-01-16)
- [ ] V1 Vérifier que le certificat du serveur de test se renouvelle

## Parqué
- P1 Application mobile
- P2 Second moyen de paiement
