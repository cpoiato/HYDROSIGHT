# 03 — Architecture technique et intelligence artificielle

# Architecture technique et IA — Calgary

**État :** proposition technique à confirmer après benchmark. Cette architecture s’applique à une prévision par secteur, non par conduite.

## 1. Chaîne fonctionnelle

1. Ingestion périodique des sources municipales et météorologiques avec horodatage de collecte.
2. Validation de schémas, coordonnées, dates, doublons et complétude.
3. Persistance immuable des observations originales et production de tables normalisées dans PostgreSQL/PostGIS.
4. Définition de la grille fixe, cibles et variables disponibles au moment de la prédiction.
5. Entraînement supervisé et comparaison chronologique aux références statistiques.
6. Publication conditionnelle des prévisions via API FastAPI.
7. Dashboard sectoriel; surcouche de proximité actuelle des services essentiels.
8. Surveillance des données, dérive et performance; réentraînement contrôlé.

## 2. Services et responsabilités

| Composant | Rôle exclusif |
| --- | --- |
| Collecte/qualité Python | Sources, instantanés, provenance et validations |
| PostgreSQL/PostGIS | Observations, secteurs, expériences, prévisions et audit |
| Pipeline ML scikit-learn | Construction temporelle des variables, entraînement, backtesting et version du modèle |
| Microservice FastAPI | Exposer prévisions et métadonnées, sans recalcul ad hoc ni seconde logique métier |
| Dashboard Streamlit/Plotly | Cartographie et explication des résultats issus de l’API |
| CI/CD GitHub Actions et Docker | Tests, analyse statique, versionnement, construction et déploiement expérimental |

## 3. Séparation prédiction / impact

Le **score prédictif** est construit avec les ruptures historiques et des variables connues à la date de référence. La **priorité opérationnelle** exploite ensuite les localisations actuelles des hôpitaux et écoles, indépendamment de la formation du modèle. On ne déduit pas d’une distance géographique l’appartenance à une même zone hydraulique.

## 4. Barrières anti-fuite

- Pour une prévision à la fin de l’année T−1, aucune observation de T ne contribue aux variables.
- Transformation, imputation, encodage, sélection de variables et calibrage s’ajustent uniquement aux partitions d’entraînement.
- Test final sur 2024–2025, sélection des hyperparamètres exclusivement sur des années antérieures; ne pas réutiliser le holdout comme validation itérative.
- Inventaire actuel de 60 740 tronçons conservé en référence contemporaine, sans attribuer son matériau/longueur historique aux années anciennes.
- Vérifier les règles de disponibilité des données météorologiques avant de considérer un décalage temporel comme suffisant.

## 5. Exploitabilité et sécurité

Traçabilité des sources, journalisation, contrôles de schéma, migration des tables et tests unitaires/intégration/régression. Le système ne dépend pas de données simulées en fonctionnement. L’exécution locale est prioritaire et les coûts des services cloud restent à valider.

## 6. Condition de passage à l’implémentation

Le déploiement de cette architecture est conditionné à un gain reproductible du ML sur les baselines et à l’établissement d’une politique crédible d’actualisation des étiquettes.
