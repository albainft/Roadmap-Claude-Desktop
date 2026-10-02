# Feuille de route : exemple

Format de référence de ce dépôt. Remplacez ce contenu par votre propre feuille de route. Dates au format AAAA-MM-JJ.
Dernière mise à jour : 2026-01-15.

## Thèmes actifs

### T1. Lancement de la version 1.0
Statut : en cours, vérifié le 2026-01-15.
Objectif : publier une première version utilisable par dix clients pilotes.
Prochaine action : A3, valider les écrans de paiement avec deux clients.
Bloqueur : aucun.
- [ ] A3 Valider les écrans de paiement : maquettes envoyées à deux clients, retours attendus avant la fin du mois, puis ajustement du parcours d'achat. Fait le 2026-01-12 pour l'envoi des maquettes.
- [ ] A4 Mettre en place la sauvegarde nocturne de la base de données : planifier le dump, le chiffrer, tester une restauration complète. Dépend de A2.
- [ ] A5 Rédiger le guide d'installation : une page par système, captures d'écran, liste des erreurs fréquentes. À partir du 2026-02-01.
- [x] A1 Choisir l'hébergement : comparaison de trois offres, choix du serveur et du nom de domaine. Fait le 2026-01-05.
- [x] A2 Déployer le prototype sur le serveur de test : conteneur, certificat, déploiement par pipeline. Fait le 2026-01-10.

### T2. Qualité et retours utilisateurs
Statut : à concevoir, ajouté le 2026-01-08.
Objectif : réduire les incidents et répondre aux clients pilotes en moins de deux jours.
Prochaine action : B1, définir les indicateurs de qualité.
Bloqueur : attend la fin de A4 pour mesurer les sauvegardes.
- [ ] B1 Définir les indicateurs de qualité : taux d'erreur, délai de réponse, satisfaction ; choisir un seuil d'alerte pour chacun.
- [ ] B2 Mettre en place les notifications d'incident : message au responsable en cas de panne, une alerte par type d'erreur et par heure au plus. Après B1.
- [ ] B3 Automatiser le rapport hebdomadaire : script de synthèse des retours, envoi par e-mail le lundi matin.

## Vérifications du lendemain (2026-01-16)
- [ ] V1 Vérifier que le certificat du serveur de test se renouvelle bien : renouvellement prévu cette nuit, contrôler la date d'expiration.

## Parqué
- Application mobile : parquée le 2026-01-08 faute de ressources ; à reprendre après la version 1.0.
- Intégration d'un second moyen de paiement : en attente du retour des clients pilotes.

## Journal
- 2026-01-12 : A3 maquettes des écrans de paiement envoyées à deux clients pilotes.
- 2026-01-10 : A2 prototype déployé sur le serveur de test, certificat valide.
- 2026-01-08 : thème T2 ajouté après la réunion avec les clients pilotes.
- 2026-01-05 : A1 hébergement choisi, nom de domaine réservé.
