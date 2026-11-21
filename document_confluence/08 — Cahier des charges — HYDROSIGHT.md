# 08 — Cahier des charges — HYDROSIGHT

# Cahier des charges

HYDROSIGHT — Prévision du risque de rupture des conduites d’eau potable à Calgary

## 1. Contexte et problème à résoudre

La Ville de Calgary gère un vaste réseau de distribution d’eau potable. Les ruptures de conduites provoquent des interruptions et des interventions coûteuses. Les données publiques montrent que les ruptures n’affectent pas tous les secteurs de la même manière.

Problème : les responsables de la planification ont besoin d’une information géographique et historique claire pour repérer les secteurs qui pourraient nécessiter une inspection prioritaire au cours des 12 prochains mois.

Objectif du projet : HYDROSIGHT vise à anticiper les risques de rupture des conduites d’eau potable de Calgary en identifiant les secteurs géographiques les plus à risque au cours des 12 prochains mois. Grâce à l’intelligence artificielle et à l’analyse des données historiques, le système aidera les gestionnaires municipaux à mieux cibler les inspections préventives, à planifier des interventions de mitigation et à optimiser l’utilisation des ressources disponibles.

## 2. Parties prenantes et utilisateurs

| **Acteur** | **Rôle dans le projet** |
| --- | --- |
| Gestionnaires municipaux des infrastructures | Utilisateurs cibles : comparer les secteurs et éclairer la planification des inspections. |
| Ingénieurs et équipes d’entretien | Utilisateurs secondaires : consulter les observations et analyses sectorielles. |
| Hôtel de ville de Calgary (administration municipale) | Partie prenante institutionnelle potentielle : représente les besoins de planification des infrastructures. Aucun mandat ni validation officielle de la Ville n'est présumé. |

Précision : les profils municipaux sont des utilisateurs cibles, et non des participants ayant déjà validé les besoins. Aucun mandat officiel de la Ville n’est présumé.

## 3. Processus actuel et processus cible

| **Situation actuelle (avant le projet)** | **Situation visée (avec HYDROSIGHT)** |
| --- | --- |
| Des données publiques existent sur les ruptures, le réseau et la météo, mais elles demandent d’être rapprochées et analysées. Le processus interne de la Ville n’a pas été observé directement. | 1. Importer et contrôler les données publiques réelles.2. Regrouper les événements dans une grille géographique fixe.3. Produire et valider des estimations sectorielles si le modèle est fiable.4. Visualiser les secteurs, leur historique et les résultats disponibles.5. Laisser la décision d’inspection aux responsables humains. |

## 4. Objectifs et indicateurs de réussite du projet

| **Objectif concret** | **Indicateur et cible proposés** |
| --- | --- |
| O1 — Identifier les secteurs à surveiller | Retrouver au moins 55 % des ruptures observées dans les 10 % des secteurs classés les plus à risque, pour chacune des années de test. |
| O2 — Vérifier la valeur ajoutée de l’IA | Faire mieux que la meilleure méthode de référence d’au moins 5 points de pourcentage pour le taux de capture des ruptures dans les 10 % de secteurs prioritaires. |
| O3 — Fournir une information utilisable | Permettre de sélectionner un secteur et de consulter son historique réel; ne montrer une prévision que si le modèle et ses résultats ont été validés |
| O4 — Assurer des résultats vérifiables | Reproduire les résultats avec les mêmes données, la même grille et les mêmes règles; |

### Métriques du modèle d’IA et seuils à atteindre

| **Métrique** | **Ce qu’elle mesure** | **Seuil visé** |
| --- | --- | --- |
| Précision — Top 10 % | Parmi les secteurs prioritaires, proportion où au moins une rupture est réellement observée. | ≥ 20 % (au moins 1 secteur sur 5 correctement signalé). |
| Rappel — Top 10 % | Parmi les secteurs qui subissent au moins une rupture, proportion retrouvée dans les secteurs prioritaires. | ≥ 40 % (au moins 4 secteurs sur 10 concernés repérés). |
| F1-score — Top 10 % | Équilibre entre précision et rappel, pour le groupe des 10 % de secteurs prioritaires. | ≥ 0,25. |

Lecture des résultats : « précision » et « rappel » concernent ici les secteurs ayant au moins une rupture (cible binaire)

Condition préalable : la couverture des observations et la validité des secteurs sans rupture doivent être établies. Tant que les étiquettes négatives ne sont pas fiables, précision, rappel et F1-score ne peuvent pas être présentés comme validés. Si les cibles ne sont pas atteintes, les résultats seront documentés sans annoncer de réussite.

## 5. Périmètre et exclusions

Périmètre du prototype : données réelles publiques de Calgary; grille fixe de 500 m × 500 m; historique des ruptures; cible binaire (au moins une rupture observée au cours des 12 mois suivants); carte interactive et consultation d’un secteur; documentation et test.

Hors périmètre : prédiction de la conduite exacte qui cassera, prévision hebdomadaire, décision automatique d’inspection, preuve de l’impact hydraulique sur un hôpital ou une école.

## 6. Exigences priorisées

| **ID** | **Exigence fonctionnelle** | **Priorité** | **Test / preuve** |
| --- | --- | --- | --- |
| EF-01 | Importer et conserver la provenance des observations officielles. | Must | Source, date de collecte et nombre de lignes disponibles. |
| EF-02 | Nettoyer les données et produire l’historique des ruptures par cellule de 500 m. | Must | Contrôles qualité et affectations géographiques vérifiables. |
| EF-03 | Construire des variables et une cible binaire sans utiliser de données futures. | Must | Tests temporels réussis; jeu de données reproductible. |
| EF-04 | Entraîner, évaluer et comparer un modèle aux références simples. | Must | Résultats sur validation chronologique et test séparé. |
| EF-05 | Afficher la carte, les observations et les prévisions uniquement si validées. | Must | Sélection du secteur et affichage cohérent; absence de score fictif. |
| EF-06 | Exporter une fiche sectorielle avec provenance et limites. | Should | PDF conforme aux données consultées. |
| EF-07 | Suivre les nouvelles captures et détecter une dérive des données. | Could | Comparaison entre captures réelles et bilan des changements. |

## 7. Données disponibles et contraintes

| **Jeu de données** | **Utilisation et contrainte** |
| --- | --- |
| Ruptures d’eau — Calgary Open Data | Événements historiques et étiquettes; vérifier les dates, doublons et la couverture temporelle. |
| Inventaire actuel des conduites | Contexte du réseau; ne pas supposer qu’il décrit le réseau tel qu’il était dans le passé. |
| Observations météorologiques | Variables historiques (p. ex. gel/dégel), uniquement si disponibles à la date de référence. |
| Hôpitaux et écoles | Localisation actuelle en contexte opérationnel; hors variables d’apprentissage. |

Contraintes principales : sources publiques autorisées, qualité et complétude variables, géolocalisation fiable, horizon fixe de 12 mois et utilisation de données non fictives. La structure du modèle et du service web reste soumise aux validations expérimentales.

## 8. Risques, hypothèses et plan de validation

| **Risque / question ouverte** | **Action de validation** |
| --- | --- |
| Les mois sans rupture enregistrée représentent-ils réellement des mois couverts, avec zéro rupture? | Examiner la continuité temporelle, la couverture des secteurs et les conditions de construction des exemples négatifs; ne pas assimiler automatiquement absence de ligne et zéro rupture. |
| Le climat contient-il des lacunes ou des valeurs interpolées à partir du futur? | Contrôler les dates des données utilisées |
| Les sources reçoivent-elles réellement de nouveaux événements? | Comparer au moins deux extractions datées et leurs enregistrements. |
