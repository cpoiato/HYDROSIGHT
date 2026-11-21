# 05 — Données réelles et protocole expérimental MLOps

# Données expérimentales, validation et MLOps — Calgary

Ce document sépare les **constats mesurés** des **tests à réaliser**. Il n’existe actuellement aucune preuve qu’un modèle ML bat les baselines.

## 1. Jeux réels disponibles

- Ruptures d’eau Calgary : 37 555 enregistrements au total; 2 153 événements de 2016 à 2025 et 338 en 2024–2025; source [dpcu-jr23](https://data.calgary.ca/resource/dpcu-jr23.json).
- Inventaire public actuel : 60 740 tronçons; source [w6h9-w33i](https://data.calgary.ca/resource/w6h9-w33i.json).
- Climat historique : 6 209 observations récupérées, avec au moins 300 jours de température chaque année entre 2016 et 2025. La présence et la qualité de la neige et des précipitations restent à contrôler individuellement.
- Services actuels : 5 hôpitaux et 506 écoles, géométries valides; hors variables ML.

## 2. Benchmarks déjà obtenus — capture top 10 %

| Maille | Année | Exposition actuelle approximative | Récence | Total historique |
| --- | --- | --- | --- | --- |
| 500 m | 2024 | 26,40 % | 42,13 % | 41,57 % |
| 500 m | 2025 | 20,00 % | 35,63 % | 43,75 % |
| 1 km | 2024 | 26,97 % | 40,45 % | 44,94 % |
| 1 km | 2025 | 34,38 % | 41,25 % | 40,62 % |

Ces chiffres décrivent des méthodes statistiques, et non une performance ML. Le nombre de secteurs évalués est de 2 398 à 500 m et 697 à 1 km; l’inventaire actuel a servi à filtrer les cellules et ne constitue pas une exposition historiquement valide.

## 3. Protocole de validation prévu

1. Figer la grille, les règles d’inclusion des secteurs, la définition de la cible et les dates de coupure sans consulter le résultat de l’année future.
2. Contrôler les doublons potentiels (21 correspondances jour/position/type; 30 paires très proches le même jour) sans les supprimer automatiquement.
3. Créer les variables d’antériorité des ruptures (1, 3, 5 ans), voisinage et météo historique avec décalage de disponibilité documenté.
4. Utiliser une validation chronologique glissante sur années antérieures; conserver 2024–2025 comme test final, à ne pas réutiliser pour le choix d’hyperparamètres.
5. Comparer plusieurs modèles simples et supervisés selon capture top 10 %, précision/rappel, PR-AUC si classification, et MAE si prédiction de comptages.
6. Tester l’apport marginal du climat par ablation, en comparaison exacte avec le modèle sans climat.
7. Inspecter la calibration, la stabilité interannuelle, les secteurs jamais accidentés et la robustesse au filtrage de cellules basé sur le réseau actuel.

## 4. Validation de l’absence de fuite temporelle

Pour une année cible Y, les observations de rupture et météorologiques retenues comme caractéristiques doivent être antérieures à la date de référence au début de Y et réellement disponibles à cette date. Les encodages, normalisations, imputations et calibrages sont ajustés sur l’entraînement uniquement. Des tests automatiques doivent échouer lorsqu’une variable utilise une date future; la présence d’un rapport d’audit ne suffit pas à prouver l’absence de fuite.

## 5. Actualisation, supervision et réentraînement

Comparer au moins deux captures datées de dpcu-jr23 au moyen d’identifiants stables ou d’empreintes documentées. Distinguer variation de métadonnées, corrections historiques et nouveaux événements. Archiver les lots et versions; évaluer le drift des variables, puis la performance lorsque les nouvelles étiquettes de rupture sont connues. Réentraîner uniquement en cas de dérive confirmée et de performance démontrée du candidat; conserver la possibilité de retour à la version précédente.

## 6. Critères de décision

| Critère | État |
| --- | --- |
| Données réelles historiques et points spatiaux | Acquis |
| Climat, hôpitaux, écoles téléchargés | Acquis |
| Anti-fuite validée automatiquement | À démontrer |
| ML supérieur aux références de manière robuste | À démontrer |
| Nouvelles observations réelles entre captures | À démontrer |
| Microservice, dashboard, CI/CD et surveillance | Non réalisés |

**Décision actuelle :** poursuivre le benchmark expérimental sectoriel; ne pas certifier encore la faisabilité complète du système MLOps.
