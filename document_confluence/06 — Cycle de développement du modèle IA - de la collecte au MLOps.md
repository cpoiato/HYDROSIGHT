# 06 — Cycle de développement du modèle IA : de la collecte au MLOps

# Cycle de développement du modèle IA — Calgary

**Portée :** guide d’exécution et de validation du projet académique, fondé exclusivement sur des données réelles hors tests automatisés. Ce document complète « 05 — Données réelles et protocole expérimental MLOps » sans affirmer que les étapes non exécutées sont terminées.

**État au 24 octobre 2026 :** collecte initiale et premières analyses descriptives/baselines réalisées; EDA exhaustive, prétraitement final, ingénierie des variables, entraînement IA, tests anti-fuite, validation de nouvelles observations, API et CI/CD restent à exécuter ou démontrer.

## Vue d’ensemble du cycle

Cadrage → Collecte → EDA → Prétraitement → Construction des variables → Découpage chronologique et baselines → Entraînement → Évaluation → Validation anti-fuite → Industrialisation → Monitoring et réentraînement → Rapport. Les résultats de qualité peuvent faire revenir aux étapes précédentes; il ne s’agit pas d’une séquence irréversible.

## Étapes, livrables et points de contrôle

| Étape | Travaux à réaliser | Livrable / preuve | Précaution scientifique |
| --- | --- | --- | --- |
| **01 — Cadrage et formulation du problème** | Préciser unité de prédiction (secteur fixe 500 m ou 1 km), date de référence, horizon de 12 mois, cible binaire (≥1 rupture) ou nombre de ruptures. Définir métriques, baselines, contraintes et règle d’approbation. | Fiche de problème, contrat cible/grille/horizon, critères de succès. | Ne pas confondre localisation à risque et conduite exacte. |
| **02 — Collecte, provenance et stockage brut** | Charger ruptures Calgary (dpcu-jr23), réseau actuel (w6h9-w33i), historique météo et positions actuelles de 5 hôpitaux / 506 écoles. Conserver les 37 555 ruptures, 60 740 tronçons et 6 209 observations climatiques comme totaux de la capture auditée (à revalider sur toute nouvelle extraction). Capturer horodatages, URLs, schémas, empreintes et snapshots. | Manifeste d’ingestion, fichiers bruts immuables, contrôles de couverture. | Un instantané unique ne prouve pas des mises à jour réelles; comparer les captures. |
| **03 — EDA / analyse exploratoire** | Évaluer répartition annuelle/spatiale des 2 153 ruptures de 2016–2025, 338 cas en 2024–2025, saisonnalité, extrêmes de froid, valeurs manquantes, distribution par secteur, catégories et concentrations; examiner 21 doublons possibles mêmes jour/coordonnées/type et 30 cas à moins de 0,1 m. Vérifier température, neige et précipitations séparément. | Rapport EDA reproductible avec graphiques, comptages et biais potentiels. | Ne jamais retirer automatiquement les événements rapprochés sans preuve de doublon. |
| **04 — Prétraitement et nettoyage** | Valider dates, fuseaux, types, projection métrique, géométries, unités météo, station et couverture; normaliser noms/unités et dédoublonner de manière documentée. Construire une grille fixe indépendamment du test futur et comparer scénarios d’inclusion des secteurs. | Jeu normalisé traçable, tests qualité, journal des exclusions. | Aucune donnée simulée en production. L’inventaire de conduites actuel n’est pas une photographie historique. |
| **05 — Feature engineering et cible** | Pour chaque secteur/année, calculer cumul historique, ruptures sur 1/3/5 ans, récence, voisinage, statistiques climatiques antérieures (jours sous 0 °C, gel–dégel, minima, précipitations si vérifiées). Garder services essentiels contemporains hors variables ML : seulement couche de priorisation après prédiction. | Table de caractéristiques horodatée, dictionnaire et lineage des variables. | Chaque caractéristique doit déclarer observation\_max\_date et être disponible avant la date de prédiction; météo du futur interdite. |
| **06 — Partition temporelle et baselines** | Construire entraînement et validation glissants sur années antérieures à 2024; préserver 2024–2025 en holdout final. Réévaluer sur même grille et mêmes étiquettes les méthodes exposition seule, récence et historique cumulé; signaler biais d’utilisation de l’inventaire actuel pour le filtre spatial. | Protocole walk-forward, tableaux des performances des baselines par année/résolution. | Ne pas ajuster des choix sur le holdout; les baselines actuelles ne sont pas du ML. |
| **07 — Entraînement des modèles** | Former d’abord des modèles supervisés interprétables (régression logistique pour cible binaire, Poisson pour comptage selon définition) puis comparer à une méthode non linéaire telle que Random Forest ou HistGradientBoosting. Gérer déséquilibre et réutiliser une seule chaîne de préparation ajustée au train. | Expériences enregistrées, hyperparamètres, versions code/jeu, modèles sérialisés. | Aucun modèle n’a encore été entraîné ni validé dans le projet audité. |
| **08 — Évaluation, robustesse et interprétabilité** | Comparer sur périodes futures : taux de capture des ruptures parmi les 10 % de secteurs classés, PR-AUC, rappel, précision et calibration pour classification; MAE pour comptage. Effectuer ablation « avec vs sans climat », sensibilité 500 m/1 km, erreurs par année, seuils et variables influentes. | Rapport comparatif, intervalles d’incertitude si justifiés, résultats négatifs compris. | Un gain instable ou dû à une fuite temporelle ne justifie pas la mise en service. |
| **09 — Validation anti-fuite et revue scientifique** | Automatiser tests assurant que toutes les observations et transformations utilisées pour prédire l’année Y sont disponibles avant sa date de référence; vérifier fit sur train seulement, sélection de colonnes, révisions tardives des sources, grille fixe et empreintes des partitions. | Rapport anti-fuite reproductible; décision go/no-go formelle. | Les dates de publication des mesures et l’historique des actifs restent à examiner si utilisés. |
| **10 — Industrialisation API, base et dashboard** | Sous réserve du go/no-go : stocker données/snapshots/features/prédictions dans PostgreSQL/PostGIS; fournir FastAPI, carte de risque 500 m/1 km et classement. Faire une couche indépendante de priorité des services essentiels courants; préciser que proximité ≠ interruption de service. | Microservice versionné, contrat API, carte avec date du modèle et avertissements, migrations. | Pas de duplication de logique entre ingestion, service et interface. |
| **11 — CI/CD, surveillance, drift et réentraînement** | Automatiser tests, validation de données, packaging Docker et déploiement expérimental; comparer de nouveaux snapshots pour confirmer de nouvelles étiquettes; suivre qualité, drift et performance en tenant compte du délai de disponibilité des résultats; réentraîner seulement si dérive/perte de performance confirmée et nouvelle version meilleure. | Pipeline CI/CD, tableaux de surveillance, journal des décisions et rollback. | Un portail modifié ne garantit pas de nouveaux enregistrements; aucune actualisation continue n’est encore prouvée. |
| **12 — Rapport final et démonstration** | Documenter jeux sources, limitations, EDA, protocole, code, résultats, échecs, architecture exécutée et démonstration sur observations réelles. | Rapport académique, démonstration reproductible et conclusions honnêtes. | Ne pas transformer une hypothèse de risque en preuve causale. |

## Portes de validation (gates)

- **Gate A — Données :** sources vérifiées, métadonnées, couverture météo détaillée et stratégie de doublons approuvées.
- **Gate B — Temporalité :** cibles, dates de référence, variables et partitions validées sans accès au futur; tests automatisés réussis.
- **Gate C — Valeur du ML :** gain mesuré et suffisamment robuste par rapport aux baselines sous protocole chronologique honnête. Les résultats négatifs conduisent à une reconsidération de la portée.
- **Gate D — MLOps :** nouveaux enregistrements réellement constatés entre captures, surveillance démontrable et réentraînement seulement sur critères confirmés.
- **Gate E — Livraison :** API et interface montrent les dates, limites et versions; tests CI/CD, traçabilité et restitution validés.

## Règles incontournables du projet

- Prédiction par **secteur** sur 12 mois, pas identification causale d’une conduite individuelle.
- Seules les variables observées avant la date de prédiction alimentent le modèle.
- Hôpitaux et écoles actuels : couche de priorisation indépendante, sans reconstruction historique.
- Un seul calcul canonique pour les variables et les scores; backend, frontend et stockage utilisent des contrats explicites.
- Persistance des données historiques et nouvelles observations réelles afin de tester la dérive et la possibilité de réentraînement.
- Les données simulées sont réservées aux tests automatisés.

## Travail immédiatement prioritaire

Finaliser EDA et audit des mesures météo (notamment précipitations/neige), puis construire un benchmark ML supervisé sans fuite temporelle, sur les mêmes années et secteurs que les références statistiques. Le déploiement MLOps complet dépend des résultats et de la preuve de mises à jour réelles.
