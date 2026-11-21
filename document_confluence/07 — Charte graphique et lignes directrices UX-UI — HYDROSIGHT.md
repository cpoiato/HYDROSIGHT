# 07 — Charte graphique et lignes directrices UX/UI — HYDROSIGHT

# HYDROSIGHT — Charte graphique et lignes directrices UX/UI

**Version :** 1.0 — **Statut :** approuvée — **Date d'approbation :**  — **Portée :** interface web de prévision du risque de rupture des conduites d'eau potable à Calgary.

Cette charte définit l'identité visuelle, les principes d'expérience utilisateur et les règles d'affichage à respecter dans l'interface HYDROSIGHT. Elle sert de référence commune pour la conception des écrans, le développement des composants et la validation de la qualité de l'expérience.

**Important :** la documentation de conception est rédigée en français; les libellés définitifs de l'application, les messages utilisateur et les textes techniques intégrés au produit seront rédigés en anglais, conformément aux conventions du projet.

## 1. Vision et positionnement

**HYDROSIGHT — Water Infrastructure Risk Prediction** est une application d'aide à la décision qui présente, par secteur géographique, des estimations de risque de rupture des conduites d'eau potable sur un horizon de 12 mois. L'expérience doit permettre aux responsables municipaux de repérer rapidement les secteurs à examiner et de comprendre les données qui étayent les résultats.

La direction artistique retenue est **GovTech premium** : sobre, professionnelle, contemporaine, lisible et centrée sur la cartographie. Il s'agit d'une identité propre à HYDROSIGHT, et non de l'identité officielle de la Ville de Calgary.

- **Clarté :** une information prioritaire par niveau de lecture, vocabulaire compréhensible et hiérarchie visuelle stable.
- **Utilité :** les écrans doivent conduire de l'observation à une décision informée.
- **Confiance :** distinguer les observations, les prévisions et les limites du modèle.
- **Cohérence :** appliquer les mêmes composants, couleurs, espacements et états dans toute l'application.

## 2. Identité de marque

| Élément | Règle adoptée |
| --- | --- |
| Nom | **HYDROSIGHT**, en majuscules pour le logotype. |
| Signature | *Water Infrastructure Risk Prediction*. |
| Symbole | Goutte d'eau associée à la silhouette urbaine et au réseau d'eau, dans un style géométrique épuré. |
| Expression visuelle | Contraste entre bleu profond, bleu technologique, fonds clairs et accents sémantiques limités. |
| Ton rédactionnel | Professionnel, accessible, orienté vers l'action et transparent quant aux incertitudes. |

## 3. Palette chromatique

Les codes suivants constituent les **valeurs de référence** de la charte approuvée. Les couleurs de risque ont un rôle sémantique, distinct de la palette de marque.

| Jeton de design | Nom | Code HEX | Usage principal |
| --- | --- | --- | --- |
| `brand.navy` | Bleu profond | `#0B2D5C` | Identité, titres, navigation structurante. |
| `brand.primary` | Bleu technologique | `#1E88E5` | Actions principales, éléments interactifs, sélection. |
| `brand.light` | Bleu clair | `#90CAF9` | Surfaces secondaires, repères cartographiques et accents. |
| `risk.low` | Vert | `#2E7D32` | Risque faible, selon une classification validée. |
| `risk.moderate` | Ambre | `#F9A825` | Risque modéré, selon une classification validée. |
| `risk.high` | Rouge | `#D32F2F` | Risque élevé, selon une classification validée. |
| `text.secondary` | Gris | `#6B7280` | Métadonnées, descriptions et informations secondaires. |

**Règle scientifique :** les intervalles 0–33 %, 34–66 % et 67–100 % présentés dans le visuel initial sont uniquement illustratifs. Aucun seuil de risque ne doit être codé en dur ou présenté comme scientifiquement validé avant l'évaluation et la calibration du modèle. Les catégories « faible », « modéré » et « élevé » seront configurées à partir de règles documentées et approuvées.

## 4. Typographie

**Police de référence :** Inter, avec une police de remplacement sans empattement disponible sur le système. Éviter de multiplier les familles typographiques.

| Style | Police / graisse | Taille de référence | Utilisation |
| --- | --- | --- | --- |
| H1 | Inter Bold | 32 px | Titre principal de page. |
| H2 | Inter SemiBold | 24 px | Titre de section. |
| H3 | Inter SemiBold | 20 px | Sous-section et titre de panneau. |
| Sous-titre | Inter Medium | 16 px | Contexte ou explication d'une mesure. |
| Corps | Inter Regular | 14 px | Champs, tableaux et contenu courant. |
| Légende | Inter Regular | 12 px | Métadonnées et annotations complémentaires. |

Les tailles ci-dessus constituent une base de conception desktop, adaptable selon les besoins d'accessibilité et la taille de l'écran. Les textes essentiels ne doivent pas dépendre d'une taille fixe empêchant leur agrandissement.

## 5. Composition et structure des écrans

L'interface privilégie une **carte centrale** et une navigation simple. La composition recommandée sur ordinateur comprend une barre supérieure avec la marque et le contexte, une navigation latérale compacte, une zone cartographique principale et un panneau latéral présentant les détails du secteur sélectionné.

- **Dashboard :** vue générale des secteurs, indicateurs de synthèse et accès aux analyses.
- **Map :** carte interactive, recherche ou sélection de secteur, légende, filtres et zoom.
- **Predictions :** paramètres, horizon de 12 mois, résultats disponibles et interprétation.
- **Data & Model :** sources, dates de mise à jour effectives, qualité des données, version du modèle et limites connues.

Les panneaux et cartes de contenu utilisent des surfaces claires, des séparations discrètes, un arrondi modéré et des espacements réguliers. Privilégier la lisibilité à la décoration, limiter les ombres et conserver un langage de composants uniforme.

## 6. Parcours de prédiction et entrées utilisateur

Le mode principal est la **sélection d'un secteur sur la carte**. L'utilisateur ne devrait pas avoir à saisir manuellement les propriétés techniques des conduites quand celles-ci sont présentes dans les sources réelles disponibles.

| Mode | Entrée de l'utilisateur | Comportement attendu |
| --- | --- | --- |
| **A — Sélection cartographique** (principal) | Clic sur un secteur. | Identifier le secteur, charger les caractéristiques historiques disponibles et lancer une estimation. |
| **B — Formulaire** | Identifiant du secteur et date de référence. | Rechercher une région existante, vérifier l'éligibilité de ses données et exécuter la prédiction. |
| **C — Ensemble des secteurs** | Commande d'analyse globale. | Produire une vue comparative des secteurs disposant de données suffisantes. |

**Horizon cible :** 12 mois. Les caractéristiques des conduites, l'historique des ruptures et les données météorologiques utilisées doivent provenir de sources réelles, être disponibles à la date de référence et être compatibles avec le modèle effectivement entraîné. Ne pas inventer de données ou de résultats en production.

## 7. Composants d'interface

| Composant | Règle UX/UI |
| --- | --- |
| Bouton primaire | Bleu technologique, verbe d'action explicite (ex. *Run prediction*), état actif, désactivé et en traitement clairement reconnaissable. |
| Bouton secondaire | Traitement plus discret; actions complémentaires (ex. *Export* si la fonction est disponible). |
| Sélecteur et filtre | Libellé visible, valeur sélectionnée explicite, navigation clavier, validation et erreurs contextualisées. |
| Carte d'indicateur | Mesure, unité, période, secteur, provenance et statut de calcul visibles. |
| Étiquette de risque | Couleur + texte et, au besoin, pictogramme; jamais une distinction par couleur seule. |
| Panneau de détail | Résumé du secteur, historique, estimation, facteurs pertinents et accès aux informations de méthode. |
| Graphique | Titre explicite, axes et unités, légende, période, infobulles accessibles et distinction entre observé et prédit. |
| Notifications | Messages d'erreur ou de confirmation compréhensibles; ne jamais annoncer une prédiction réussie avant un résultat confirmé. |

## 8. Cartographie et visualisation des données

- Représenter les secteurs géographiques sur une carte lisible et maintenir des limites de secteurs reconnaissables.
- Employer la palette vert / ambre / rouge uniquement pour des classes de risque effectivement validées; afficher systématiquement une légende textuelle.
- Conserver des couches distinctes pour le réseau d'eau, les frontières des secteurs et les infrastructures d'intérêt (hôpitaux, écoles) lorsqu'elles proviennent de sources réelles.
- En cas de données manquantes ou de prédiction impossible, utiliser un état « données insuffisantes » distinct d'un risque faible.
- Afficher la date de référence, l'horizon, la version du modèle et la date réelle des observations utilisées.
- Ne pas représenter des scores arbitraires comme des probabilités calibrées; préciser le sens exact de chaque indicateur.
- Si un intervalle d'incertitude ou un niveau de confiance est disponible et défendable méthodologiquement, le présenter de façon distincte du score principal.


## 9. Accessibilité et comportements responsifs

**Objectif de conformité :** WCAG 2.2 niveau AA. La validation de conformité devra être vérifiée sur les composants réellement développés.

- Contraste suffisant, focus clavier visible et ordre de tabulation logique.
- Texte et icônes explicites pour tous les états de risque; aucune information transmise uniquement par la couleur.
- Zones interactives faciles à viser, labels explicites et messages d'erreur associés aux champs.
- Version mobile et tablette : disposition verticale, carte conservée comme zone centrale et panneau de détail repositionné sans perte fonctionnelle.
- Graphiques et carte : alternative textuelle ou tabulaire pour les informations essentielles et interaction utilisable au clavier dans la mesure du possible.
- États obligatoires : chargement, absence de données, données insuffisantes, échec de calcul, résultat disponible.

## 10. Gouvernance, données et conventions

- La charte et les jetons de design constituent une référence unique : ne pas multiplier des variantes de couleurs, d'icônes ou de comportements dans différents écrans.
- Tout changement de palette, typographie, identité ou structure de navigation doit être explicité et validé avant développement.
- Les seuils de risque, la sémantique exacte des scores et les fonctionnalités de prédiction définitives dépendront des travaux de modélisation et d'évaluation.
- Les libellés de production, documentations techniques internes et noms de code sont en anglais.

## 11. Critères de validation UX/UI

* [ ] Identité HYDROSIGHT cohérente sur chaque écran.
* [ ] Palette et typographie appliquées à partir de jetons centralisés.
* [ ] Parcours « sélectionner un secteur → consulter les données → lancer une prédiction → analyser le résultat » compréhensible.
* [ ] États de chargement, d'erreur et de données insuffisantes pris en charge.
* [ ] Données historiques et prédictions clairement distinguées.
* [ ] Carte, tableaux et graphiques accessibles, avec informations non dépendantes uniquement de la couleur.
* [ ] Seuils de risque et niveaux de confiance documentés et fondés sur le modèle réel.
* [ ] Mise en page responsive et contrôle d'accessibilité WCAG 2.2 AA effectués.

## 12. Documents associés

- [01 — Cadrage et présentation du projet HYDROSIGHT](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/5865483/01+Cadrage+et+pr+sentation+du+projet+HYDROSIGHT)
- [02 — Analyse fonctionnelle : User Stories et spécifications](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/5931025/02+Analyse+fonctionnelle+User+Stories+et+sp+cifications)
- [03 — Architecture technique et intelligence artificielle](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/5963786/03+Architecture+technique+et+intelligence+artificielle)
- [05 — Données réelles et protocole expérimental MLOps](https://cpoiato.atlassian.net/wiki/spaces/~62f3ffc8f15eecaf50105eae/pages/5963818/05+Donn+es+r+elles+et+protocole+exp+rimental+MLOps)

*Référence visuelle approuvée : infographie « HYDROSIGHT — Charte graphique v1.0 ». Les libellés présents dans cette référence initiale sont illustratifs; les spécifications normatives sont définies dans la présente page.*
