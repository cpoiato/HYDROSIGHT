# 02 — Analyse fonctionnelle : User Stories et spécifications

# Analyse fonctionnelle — Calgary

Cette page décrit les besoins et critères d’acceptation. L’architecture et les expériences scientifiques sont documentées séparément. Toutes les fonctions utilisent des données observées réellement, sauf les fixtures de tests.

## Périmètre de l'interface HYDROSIGHT — clarification du 16 novembre 2026

La référence UX approuvée comprend deux vues complémentaires : **(1) Tableau de bord du risque**, avec carte et classement des secteurs; **(2) Analyse détaillée d'un secteur**, avec observations, prévision, facteurs explicatifs et actions possibles. La navigation et l'identité visuelle suivent la charte graphique approuvée. Les textes de l'application sont en anglais; les spécifications restent en français.

La prédiction prévue est **sectorielle, sur un horizon de 12 mois**; elle ne constitue ni une probabilité individuelle de rupture d'une conduite, ni une série de prédictions hebdomadaires. La grille géographique du projet utilise exclusivement une maille de 500 m × 500 m, dans un référentiel métrique approprié. Les cellules en limite municipale peuvent être découpées par le périmètre officiel de Calgary.

**Distinction obligatoire :** les observations historiques sont consultables dès qu'elles sont intégrées et validées; les scores, classements prédictifs, contributions explicatives et recommandations fondées sur le ML ne sont publiés qu'après disponibilité et validation du modèle et des données correspondantes. Les valeurs, seuils et tendances de la maquette sont illustratifs et ne doivent jamais être intégrés comme résultats réels.

## Catalogue des User Stories

| Réf. | Besoin | Priorité |
| --- | --- | --- |
| US-01 | Importer et actualiser les sources officielles | Haute |
| US-02 | Contrôler et historiser la qualité et la provenance | Haute |
| US-03 | Construire les secteurs et l’historique des ruptures | Haute |
| US-04 | Préparer et contrôler les données climatiques | Haute |
| US-05 | Entraîner et comparer les modèles | Haute |
| US-06 | Afficher une carte et le classement des risques | Haute |
| US-07 | Prioriser les services essentiels actuels | Haute |
| US-08 | Surveiller les nouvelles observations et le drift | Haute |
| US-09 | Consulter les résultats et versions passées | Haute |
| US-10 | Sélectionner un secteur et demander une prévision | Haute |
| US-11 | Consulter l'analyse détaillée d'un secteur | Haute |
| US-12 | Exporter un rapport sectoriel vérifiable | Moyenne |
| US-13 | Construire et valider les variables du modèle (feature engineering) | Haute |

## Spécifications et critères d’acceptation

### US-01 — Sources

En tant que responsable du projet, je veux charger les enregistrements officiels des ruptures, du climat, des conduites et des services essentiels pour disposer d’observations vérifiables.

- Les téléchargements conservent l’URL, la date d’extraction, le nombre de lignes, un identifiant ou une empreinte stable et les erreurs.
- Une extraction identique ne produit pas de doublons; une nouvelle observation est détectable en comparant deux captures.

### US-02 — Qualité et persistance

Contrôler les dates, coordonnées, doublons potentiels, valeurs manquantes et unités au moyen de règles de nettoyage explicites et testées. Préserver les fichiers sources, les versions des jeux de données et un bilan agrégé indiquant les volumes de données traitées, les nombres d’enregistrements exclus ou corrigés et les motifs correspondants. La reproductibilité du traitement et la validation des règles suffisent : aucun registre d’audit individuel des enregistrements exclus n’est requis.

### US-03 — Grille géographique et historique des ruptures

Construire, identifier et versionner une grille géographique fixe de 500 m × 500 m dans un référentiel métrique approprié et la découper au périmètre municipal lorsque nécessaire. Associer les ruptures observées aux secteurs de cette grille et produire un historique vérifiable par secteur et période, sans utiliser d’informations futures. La définition, le calcul et la validation de la variable cible des 12 mois suivants relèvent exclusivement de la US-13 (feature engineering).

### US-04 — Préparation et qualité des données climatiques

Préparer les observations météorologiques réelles nécessaires au projet : harmoniser les dates, formats et unités; contrôler la couverture, les doublons, les valeurs manquantes et la cohérence des températures; appliquer uniquement les corrections et imputations documentées et validées; préserver les indicateurs de valeurs imputées ainsi que le bilan de qualité; enregistrer et versionner le jeu de données nettoyé. La US-04 ne calcule ni les indicateurs climatiques historiques destinés au modèle, ni les fenêtres glissantes associées à une date de prévision : ces transformations appartiennent exclusivement à la US-13. Toute imputation utilisée ultérieurement comme entrée du modèle doit respecter la disponibilité temporelle des observations.

### US-13 — Construire et valider les variables du modèle (feature engineering)

**En tant que** responsable du développement du modèle IA,  
**Je veux** assembler, transformer et valider les caractéristiques historiques des secteurs et la cible de rupture,  
**Afin de** produire un jeu de données supervisé reproductible, sans fuite temporelle, utilisable par la US-05.

**Description fonctionnelle** — Après le prétraitement des sources réelles (US-01 et US-02), la construction de la grille de 500 m × 500 m et de l’historique des ruptures (US-03), ainsi que la préparation et la validation des observations climatiques (US-04), le système calcule les indicateurs climatiques historiques, définit la variable cible sur 12 mois et produit un jeu de caractéristiques par secteur et date de référence. Cette US assemble ces résultats selon un contrat unique, sans dupliquer les règles de la grille ou du climat dans une autre couche.

**Règles fonctionnelles et métier**

- Assigner les observations à des identifiants de secteurs et à une grille versionnée; agréger par secteur les ruptures observées, les caractéristiques de réseau justifiables et les indicateurs climatiques calculés ici à partir des données nettoyées en US-04. Les propriétés de réseau disponibles seulement à la date actuelle ne doivent pas être utilisées comme état historique prouvé.
- Construire les variables temporelles (historique des ruptures, récence, fenêtres glissantes et autres indicateurs retenus) exclusivement avec les événements antérieurs à la date de référence. Documenter les périodes d'observation et les règles de découpage. Calculer ici, une seule fois, les indicateurs météorologiques historiques par date de référence (notamment jours de gel, cycles gel/dégel et jours de froid extrême selon des seuils documentés). N'ajouter les indicateurs de précipitation ou de neige que si leur qualité est suffisante. Contrôler l'absence d'utilisation d'observations futures, y compris par interpolation franchissant la date de référence. Les températures observées pendant les 12 mois à prédire ne peuvent pas être des variables explicatives.
- Définir, documenter, calculer et valider la variable cible à partir des ruptures réellement observées sur les 12 mois suivant la date de référence. Le choix entre la présence d'au moins une rupture (cible binaire) et le nombre de ruptures (cible de comptage) est arrêté et documenté dans le protocole expérimental avant l'entraînement; une seule définition canonique est utilisée. Aucune autre US ne reconstruit cette cible.
- Assembler un enregistrement unique par secteur et date de référence, avec identifiants de grille et de capture des données, horizon, cible, variables et indicateurs de complétude. Les cellules sans rupture observée ne sont pas supprimées automatiquement; leur statut de couverture doit être connu.
- Valider types, unités, dates, doublons, valeurs manquantes, couverture des secteurs, cohérence géographique, complétude des horizons et absence de fuite temporelle. Toute exclusion ou valeur non disponible doit être explicitement justifiée et traçable.
- Enregistrer le jeu final versionné et ses métadonnées afin de le réutiliser à l'identique pour l'entraînement, l'évaluation et l'inférence. Conserver la provenance et la compatibilité des transformations; aucune donnée fictive hors tests automatisés.
- La définition et la production du dataset de caractéristiques restent la responsabilité de cette US. La US-05 consomme le jeu produit sans recalculer les variables ou la cible selon une logique parallèle.

**Critères d'acceptation**

- Étant donné les données officielles prétraitées et une grille versionnée, lorsque le pipeline de feature engineering s'exécute, alors il produit un dataset par secteur et date de référence contenant les variables définies, la cible sur 12 mois et des références de provenance vérifiables.
- Étant donné une date de référence, lorsque les variables et la cible sont calculées, alors aucune variable explicative n'utilise une observation postérieure à cette date, tandis que la cible utilise seulement la fenêtre future prévue et les horizons effectivement observables.
- Étant donné des données manquantes, des secteurs non couverts, des doublons ou des incohérences, lorsque la validation est exécutée, alors les anomalies sont signalées et la production invalide est refusée ou explicitement qualifiée, sans correction silencieuse.
- Étant donné les mêmes versions des données sources, de la grille et des règles de transformation, lorsque le pipeline est exécuté à nouveau, alors il produit un résultat reproductible, sans doublons et avec la même définition de variables et de cible.
- Étant donné un dataset final validé, lorsque la US-05 démarre l'entraînement, alors elle peut consommer ce dataset directement, sans reconstruire localement ses variables ni introduire de nouvelle logique de normalisation.

**État d'avancement constaté dans le dépôt GitHub :** les associations géographiques, les agrégats de conduites et l'historique mensuel de ruptures possèdent déjà des fonctions. En revanche, les fonctions d'agrégation météo, de variables géographiques et temporelles, de cible, d'assemblage, de validation et de sauvegarde du dataset sont encore non implémentées dans `feature_engineering.py`. Cette US est donc **partiellement implémentée**, et non terminée.

### US-05 — ML vérifiable

Comparer le modèle supervisé à « exposition seule », « récence historique » et « total historique » sur les mêmes années et secteurs. Respecter l’entraînement passé → validation future; publier taux de capture des ruptures par les 10 % de secteurs prioritaires, précision/rappel et erreurs selon cible.

**Dépendance fonctionnelle US-05 :** le jeu de variables et la cible validés en US-13 constituent l'entrée canonique de l'entraînement; la US-05 n'effectue pas de reconstruction indépendante des caractéristiques.

### US-06 — Interface

Afficher une carte interactive des secteurs, les observations disponibles et, lorsqu'elles ont été validées, les prévisions et le classement des risques sur 12 mois. L'écran présente le périmètre géographique, la maille, la date de référence, l'horizon, les données disponibles, la version du modèle, les limites et la sémantique exacte de chaque score. L'interface ne présente jamais une estimation expérimentale comme une certitude.

- La carte permet de repérer et sélectionner un secteur réel, au clic ou au clavier avec une alternative de recherche ou de liste; la sélection ouvre le résumé du secteur et l'accès à l'analyse détaillée (US-11).
- Les couches de secteurs et les observations géographiques sont issues des sources réelles et de la grille versionnée. La vue globale ne classe les secteurs par risque qu'à partir de prévisions comparables produites par le même modèle et le même horizon.
- La légende et les catégories de risque utilisent uniquement des seuils validés et documentés; faute de seuils approuvés, afficher un indicateur défini et son rang sans utiliser les catégories faible/modéré/élevé. Aucun pourcentage n'est présenté comme probabilité sans calibration démontrée.
- Un secteur sans données suffisantes ou sans prévision valide possède un état explicite « données insuffisantes » ou « prévision indisponible », différent d'un risque faible. Chargement et erreurs sont traités de manière visible.
- Les filtres de secteur et de date de référence admissible ne proposent que des valeurs réellement disponibles. La résolution géographique est fixe (500 m × 500 m) et ne fait pas l’objet d’une sélection par l’utilisateur. L'action de lancement relève de l'US-10.

**Critères d'acceptation complémentaires**

- Étant donné un jeu de secteurs et de données historiques valides, lorsque l'utilisateur consulte la carte, alors seuls les secteurs réels sont affichés avec leur identifiant et leurs observations disponibles, sans scores fictifs.
- Étant donné des prévisions validées et comparables, lorsque l'utilisateur consulte le tableau de bord, alors le classement, sa période, sa méthode et la version du modèle sont affichés de façon cohérente sur la carte et dans la liste.
- Étant donné qu'aucun modèle valide n'est publiable, lorsque le tableau de bord est affiché, alors le classement prédictif est indisponible et un message explicatif apparaît sans bloquer la consultation des observations.
- Étant donné un secteur sélectionné, lorsque l'utilisateur choisit « View sector analysis », alors la vue de l'US-11 s'ouvre sur le même secteur et la même prévision, sans calcul contradictoire.

### US-07 — Hôpitaux et écoles

En tant que gestionnaire, je souhaite identifier des services essentiels actuellement proches de secteurs à risque. Les 5 hôpitaux et 506 écoles téléchargés servent uniquement à une couche de priorité courante, pas à l’apprentissage ni à reconstituer le passé. La proximité ne démontre pas une dépendance hydraulique.

- La carte peut superposer les emplacements réels et actuels des hôpitaux et écoles, avec leur type, source et date de disponibilité. Leur proximité géographique reste une information de priorisation indépendante du score ML.
- Étant donné qu'un service essentiel est proche d'un secteur, lorsque l'utilisateur consulte sa fiche, alors la distance ou le critère de proximité documenté peut être affiché sans prétendre établir une dépendance hydraulique ni un impact causé par une rupture.

### US-08 — Surveillance et drift

Comparer les instantanés successifs de la source de ruptures; suivre complétude, dérive des variables, dérive de performance lorsque les vraies étiquettes sont connues; proposer un réentraînement uniquement sur dérive confirmée et après évaluation. Une seule capture de 2026 ne prouve aucune actualisation future.

### US-09 — Traçabilité

Conserver les prévisions, horizons, métriques, paramètres, identifiants de jeu de données et modèles. Permettre la consultation historique sans régénération implicite.

- Chaque prévision consultée comporte son identifiant, la maille et sa version, le secteur, la date de référence, la période couverte, la version du modèle, la capture de données et la date de génération. Les historiques restent consultables même lorsqu'un nouveau modèle est publié.
- Lorsqu'un résultat existant est rouvert ou exporté, il est restitué sans réentraînement ni recalcul implicite; toute nouvelle prévision devient un résultat distinct traçable.

### US-10 — Sélectionner un secteur et demander une prévision

**En tant que** gestionnaire municipal,  
**Je veux** sélectionner un secteur et une date de référence admissible puis lancer une prévision,  
**Afin de** connaître son niveau de risque estimé pour les 12 mois suivants lorsque le modèle est disponible.

**Description fonctionnelle** — La sélection principale se fait sur la carte; un formulaire permet aussi de rechercher un identifiant de secteur réel et une date de référence disponible. L'application charge les caractéristiques nécessaires auprès du service de prédiction; elle ne demande pas de saisir des valeurs techniques déjà présentes dans les sources officielles.

**Règles métier**

- Le secteur doit appartenir à la grille active ou à une grille historique explicitement disponible; les données d'entrée, leur état de complétude et le modèle doivent être compatibles avec la date et la maille sélectionnées.
- L'horizon est de 12 mois; aucune option de prévision hebdomadaire, de risque de rupture par conduite ou de date arbitraire incompatible avec les données disponibles n'est offerte.
- L'action « Run prediction » est activée uniquement si le service possède un modèle approuvé, des variables calculables sans fuite temporelle et une période d'entrée admissible. Sinon, elle est désactivée ou rejetée avec une explication explicite.
- Le résultat affiché provient exclusivement de la réponse du backend et contient l'identifiant du secteur, la date de référence, l'horizon, le score et sa signification, la version du modèle et la provenance des données. L'interface ne recalcule ni le score ni les seuils.
- Un indicateur de chargement précède le résultat; les erreurs, délais et données manquantes ne sont jamais présentés comme une prévision réussie. Une consultation d'un résultat préexistant doit être identifiable comme telle.

**Critères d'acceptation**

- Étant donné un secteur valide et un modèle approuvé, lorsque l'utilisateur lance la prévision, alors la réponse réelle est présentée pour l'horizon de 12 mois avec identifiants de version et date de référence.
- Étant donné un secteur inconnu ou une date non prise en charge, lorsque la demande est soumise, alors le système la refuse clairement sans résultat fabriqué.
- Étant donné un modèle non disponible ou non validé, lorsque l'utilisateur consulte le formulaire, alors il peut inspecter les observations mais ne peut pas obtenir un faux score.

### US-11 — Consulter l'analyse détaillée d'un secteur

**En tant que** gestionnaire municipal,  
**Je veux** ouvrir la fiche détaillée d'un secteur sélectionné,  
**Afin de** comprendre les observations, le risque estimé, les limites du modèle et les actions éventuellement justifiées.

**Description fonctionnelle** — La fiche comporte un en-tête avec secteur, période et statut; des observations historiques de ruptures; une prévision sectorielle si disponible; des facteurs explicatifs s'ils sont validés; un bloc « actions possibles » fondé sur les données réellement accessibles; et un bloc « fiabilité et limites ». L'export relève de l'US-12.

**Règles métier**

- Le graphique « Évolution du risque sur 12 semaines » de la maquette est remplacé par l'historique réel des ruptures par année ou mois, selon la qualité et la granularité des observations, et par une représentation distincte de la prévision sur 12 mois. Une succession de probabilités hebdomadaires n'est pas inférée d'un modèle annuel.
- Les courbes observées et les résultats prédits sont distingués par leur libellé, unité, période et provenance. Une prévision ne devient un pourcentage de probabilité qu'après validation et calibration appropriées; sinon afficher sa mesure réelle et sa définition.
- La rubrique « Ce qui explique le score » affiche uniquement des facteurs réellement utilisés par le modèle et des contributions calculées par une méthode documentée, sans les assimiler à des causes. Elle est masquée ou remplacée par un état informatif si l'explicabilité n'est pas disponible.
- Les champs « pression du réseau », « nature du sol » ou tout autre indicateur absent des données vérifiées ne sont ni supposés ni présentés en score. Les propriétés actuelles des conduites ne sont pas attribuées rétroactivement au réseau historique sans preuve.
- Les actions proposées sont présentées comme pistes de vérification, issues de règles métier traçables et des observations disponibles, non comme prescriptions automatiques ou décisions d'ingénierie. Les hôpitaux et écoles proches sont une couche de contexte actuel, sans inférence de dépendance hydraulique.
- Le bloc « Fiabilité et limites » expose les métriques effectivement mesurées, la dernière version du modèle, la date des sources, les limites méthodologiques et un avertissement d'aide à la décision. Ne jamais afficher une date de calibration ou un niveau de confiance inventé.

**Critères d'acceptation**

- Étant donné un secteur disposant de ruptures observées mais sans modèle validé, lorsque l'utilisateur ouvre la fiche, alors il voit son historique réel et un message d'indisponibilité du risque prédictif.
- Étant donné une prévision validée, lorsque l'utilisateur ouvre la fiche, alors le score, son horizon, son sens, la version et ses limites correspondent exactement à la prévision de l'US-10.
- Étant donné qu'aucune explication de modèle n'a été produite, lorsque l'utilisateur ouvre la rubrique explicative, alors aucune barre d'influence arbitraire n'est affichée.
- Étant donné un service essentiel recensé à proximité, lorsque la fiche mentionne ce service, alors l'interface signale explicitement qu'il s'agit de proximité géographique et non d'une relation hydraulique démontrée.

### US-12 — Exporter un rapport sectoriel vérifiable

**En tant que** gestionnaire municipal,  
**Je veux** exporter le résultat consulté pour un secteur,  
**Afin de** partager une analyse traçable et de préparer une décision d'inspection.

**Description fonctionnelle** — Le bouton « Export report » produit un PDF lisible à partir des données et, si elles existent, de la prévision et de l'explication effectivement affichées. Le rapport distingue les observations d'une estimation prédictive et contient des références aux sources.

**Règles métier**

- Le rapport contient l'identifiant du secteur, la maille et la version de la grille, les périodes observées, la date de référence, l'horizon, le statut du résultat, les métriques et limites disponibles et, le cas échéant, la version du modèle et la capture des données utilisées.
- Si la prévision est indisponible, le rapport ne doit pas présenter de score fictif; un rapport purement descriptif peut être exporté avec mention explicite de cette absence.
- L'export reproduit les résultats persistés et la provenance sans relancer automatiquement l'entraînement ou modifier le score. Les champs non disponibles sont omis ou explicitement signalés, jamais remplis avec des valeurs de maquette.
- Les erreurs de génération sont expliquées; aucun bouton ne signale un succès avant l'existence effective du fichier.

**Critères d'acceptation**

- Étant donné une analyse valide consultable, lorsque l'utilisateur lance l'export, alors un PDF est généré avec les mêmes valeurs, périodes et métadonnées que la fiche, sans données inventées.
- Étant donné une analyse descriptive sans prévision validée, lorsque l'utilisateur exporte, alors le rapport indique explicitement qu'aucun risque prédictif n'est disponible.
- Étant donné une erreur d'export, lorsque la génération échoue, alors aucun téléchargement présenté comme réussi n'est proposé.

## Règles transversales

- Source de vérité unique pour chaque transformation et contrat explicite API / ML / interface.
- Pas de données fictives hors tests automatisés.
- Pas d’utilisation de l’inventaire actuel des conduites comme photographie d’un exercice passé sans preuves historiques.
- Aucun résultat de modèle ou effet causal ne doit être présenté sans validation.

## Conditions de mise en œuvre du frontend

- Construire d'abord la structure des deux vues, le parcours utilisateur et la carte/les observations fondées sur les sources réelles. Les modules de prévision, de contribution des facteurs et de priorisation prédictive ne s'activent qu'après validation des sorties du pipeline ML.
- Conserver un contrat unique entre pipeline ML, service API et frontend. L'API expose les scores, unités, dates, identifiants, états de disponibilité et versions; aucun calcul parallèle ou transformation scientifique indépendante n'est autorisé dans l'interface.
- Les sorties visuelles respectent les jetons de la charte HYDROSIGHT approuvée; les libellés et messages réels de l'application sont en anglais. Les états accessibles et adaptatifs (chargement, erreur, données manquantes, prévision indisponible et résultat disponible) sont obligatoires.
- L'implémentation doit garder distinctes la qualité des observations, la performance validée d'un modèle et les informations opérationnelles de proximité. Les données simulées sont interdites en fonctionnement, sauf comme fixtures de tests automatisés.
- Les pages et API doivent être testées sur des données réelles disponibles, les cas d'absence de modèle, l'absence de fuite temporelle, la cohérence carte/détail/export, la traçabilité des versions et les erreurs réseau.

**Documents de référence :** [Charte graphique approuvée](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/8716291/07+Charte+graphique+et+lignes+directrices+UX+UI+HYDROSIGHT); [Architecture technique](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/5963786/03+Architecture+technique+et+intelligence+artificielle); [Protocole de validation des données et du modèle](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/5963818/05+Donn+es+r+elles+et+protocole+exp+rimental+MLOps).
