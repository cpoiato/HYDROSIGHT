# 04 — Modèle de données et contraintes d’intégrité

# Modèle de données — Calgary

Modèle logique initial proposé pour PostgreSQL/PostGIS. Les noms de tables ci-dessous sont des références techniques, pas des libellés d’interface.

## 1. Entités

| Entité | Attributs essentiels | Responsabilité |
| --- | --- | --- |
| Source de données (data\_source) | id, nom, URL, licence, fréquence déclarée | Catalogue vérifiable des fournisseurs |
| Capture (source\_snapshot) | id, source\_id, captured\_at, empreinte, statut, nombre\_lignes | Historiser effectivement les extractions |
| Rupture (water\_break) | id\_source ou empreinte, date, type brut, statut, géométrie, snapshot\_id | Ground truth observé; doublons à investiguer |
| Observation climatique (weather\_observation) | station\_id, observation\_date, variables et unités, snapshot\_id | Mesures réelles datées |
| Secteur (grid\_cell) | id, résolution\_m, géométrie, version\_grille | Référentiel spatial stable |
| Événement sectoriel (sector\_event) | break\_id, grid\_cell\_id, règle\_affectation | Affectation reproductible des ruptures |
| Actif courant (current\_pipe) | id\_source, géométrie, matière, année\_installation, snapshot\_id | Contexte contemporain; pas de vérité historique implicite |
| Service essentiel courant (essential\_service) | id\_source, type, nom, géométrie, snapshot\_id | Priorisation actuelle hors ML |
| Jeu d’apprentissage (feature\_dataset) | id, as\_of\_date, horizon, version\_definitions, empreintes\_sources | Regrouper des variables temporellement admissibles |
| Exécution d’expérience (ml\_run) | id, model\_version, dates\_train\_validation\_test, paramètres, métriques | Traçabilité des benchmarks |
| Prévision (sector\_forecast) | run\_id, grid\_cell\_id, date\_reference, horizon, score, rang | Prévisions consultables |
| Évaluation et drift (monitoring\_result) | run\_id, date\_controle, métriques, dérive, décision | Déclenchement justifié des révisions |

## 2. Contraintes d’intégrité

- Clés étrangères entre captures et observations, expériences et prévisions, ruptures et affectations.
- Idempotence à l’import; distinguer les vrais identifiants des empreintes de rapprochement, sans fusionner aveuglément des événements proches.
- Conserver la valeur brute, l’unité et les valeurs manquantes avec leur provenance.
- Géométries avec système de coordonnées déclaré et contrôlé; cellules de 500 m et 1 km construites en coordonnées métriques.
- Une prévision unique par exécution, secteur, horizon et date de référence.
- Les variables utilisent uniquement les observations autorisées à la date de référence; enregistrer pour chacune la date maximale des données contributrices.
- Les services essentiels restent dans un jeu courant versionné et ne deviennent pas des variables d’entraînement.
- Ne jamais réécrire les captures brutes ni effacer les prévisions historiques lors d’un réentraînement.

## 3. Décisions et limites

Pas de relation « rupture → conduite exacte » sans identifiant officiellement fiable. L’association par distance ne constitue pas une preuve. L’historique du réseau n’étant pas disponible, les années d’installation et matériaux actuels ne doivent pas générer des contre-exemples historiques trompeurs. Le stockage de plusieurs captures permettra de constater ou de réfuter l’arrivée réelle de nouveaux enregistrements.

## 4. Schéma physique et migrations

Les types PostgreSQL, index spatiaux, partitions, politique de conservation et migrations seront définis au moment de l’implémentation. Cette page représente le contrat conceptuel initial, non une base déjà déployée.
