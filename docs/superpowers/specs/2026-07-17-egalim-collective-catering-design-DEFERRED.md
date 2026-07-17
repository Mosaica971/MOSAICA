# Restauration collective, aide alimentaire & conformité EGalim — cadrage (chantier C3, DIFFÉRÉ)

> **Statut : différé, bloqué sur données externes.** Spec de cadrage écrite le 2026-07-17
> pour reprise ultérieure sans re-exploration. Chantiers A, B, C1 faits et mergés ; C2 (part
> de bio) cadré à part (`2026-07-17-bio-share-indicator-design-DEFERRED.md`) et lié à ce
> chantier (EGalim raisonne en part de bio + qualité).

## Objectif visé

Trois scores de reporting (a posteriori, jamais des contraintes du modèle) à l'échelle de la
Guadeloupe entière :

1. **Approvisionnement local de la restauration collective** (cantines scolaires, hôpitaux,
   EHPAD…) : part de la demande couvrable par la production locale du scénario.
2. **Aide alimentaire** : part des besoins de l'aide alimentaire couvrable localement.
3. **Conformité EGalim** : la loi impose en restauration collective **≥ 50 % de produits
   « durables et de qualité » dont ≥ 20 % de bio, en valeur d'achat HT**. Score = où en est
   le scénario vs ces seuils.

## Ce qui existe déjà (réutilisable)

- **Production locale par culture** : `indicators.compute_production_tonnes_by_crop` /
  `compute_sales_by_crop` (chantier C1/B) — tonnes et € par culture, pour toute allocation.
- **Nutrition** (`Nutri_Cult` / `Nutri_Alim`, chantier C1) : population = 400 736, besoins/hab,
  contribution pêche. Réutilisable pour convertir demande cantines ↔ tonnages/nutriments.
- **Part de bio** : dépend de C2 (voir verrou : pas de vraie classification bio aujourd'hui).

## Verrou : données externes absentes du repo

Aucune de ces données n'est présente (`/data/` ne contient que production/agronomie) :

- **Demande restauration collective** : nb de repas/an (scolaire, santé, social), grammages
  par composante, ou tonnages par groupe alimentaire. Sources possibles : Rectorat / conseil
  régional (cantines scolaires), ARS (santé), DAAF Guadeloupe, observatoire EGalim (« ma
  cantine »).
- **Aide alimentaire** : tonnages distribués (Banques alimentaires, Croix-Rouge, DRAJES /
  DEETS), ou nb de bénéficiaires × rations.
- **EGalim** : définition opérationnelle de « durables et de qualité » (bio, Label Rouge,
  AOP/IGP/STG, HVE, « fermier », mention « produit de montagne », projets alimentaires
  territoriaux, externalités环…) et **valeurs d'achat** par catégorie. Nécessite une liste de
  labels par culture et un prix d'achat de référence.

## Décisions requises avant implémentation (à poser à l'utilisateur)

1. **Granularité de la demande** : par **groupe alimentaire** agrégé (féculents, légumes,
   fruits, protéines animales/végétales…) avec une table de correspondance culture→groupe, ou
   par culture MOSAICA directement ? (Recommandé : groupes alimentaires — la demande cantine
   se raisonne ainsi, et les cultures MOSAICA ne couvrent pas tout l'assiette.)
2. **Périmètre restauration collective** : scolaire seul, ou + santé + social ?
3. **Estimation vs donnée** : à défaut de volumes réels, accepte-t-on une **estimation
   paramétrée en YAML** (nb d'élèves × repas/an × grammages) comme point de départ, marquée
   « hypothèse » ? (Recommandé pour débloquer, comme `baseline_representative_crops`.)
4. **Définition EGalim « durable/qualité »** : quelle liste de labels retenir, et sous quelle
   forme (colonne(s) par culture dans une nouvelle table, ou config) ? En **valeur d'achat**
   (fidèle à la loi) ou, à défaut de prix d'achat, en **tonnage** comme proxy documenté ?
5. **Que compte comme « local »** : toute la production Guadeloupe du scénario, ou seulement
   certaines filières ? (Défaut : toute la production locale.)

## Architecture proposée (structure « data-pluggable », à activer quand les données arrivent)

Conçue pour être **inerte tant qu'aucune donnée n'est fournie** (comme un stub configurable) :

- **Nouvelles tables de données** (à fournir, chargées si présentes) :
  - `food_groups.csv` : culture → groupe alimentaire (+ éventuel prix d'achat de référence,
    labels qualité/bio par culture pour EGalim).
  - `collective_demand.yaml`/`.csv` (ou bloc `config.yaml reporting.egalim`) : demande par
    groupe alimentaire (repas × grammages ou tonnages) pour restauration collective et aide
    alimentaire.
- **Indicateurs** (`reporting/indicators.py`, nouveau module possible `food_policy.py`) :
  - `compute_local_supply_coverage(dataset, allocation, demand)` : par groupe, min(1,
    production_locale / demande) ; score agrégé = couverture pondérée.
  - `compute_egalim_shares(dataset, allocation, labels, prices)` : part « durable/qualité » et
    part « bio » en valeur d'achat ; comparaison aux seuils 50 % / 20 % → score de conformité
    (ex. distance aux seuils, ou booléen + marge).
- **Persistance** (`report.py`) : `recap["food_policy"]` = `{input, output, delta}` avec
  couverture restauration collective, couverture aide alimentaire, parts EGalim (durable/bio)
  et statut vs seuils. Bloc **absent** si aucune donnée fournie (dashboard défensif).
- **Dashboard** : indicateurs `coverage_*`, `egalim_durable_share`, `egalim_bio_share`
  (bénéfice) dans le profil + score composite ; panneau dédié EGalim (jauges 50 %/20 % avec
  seuils tracés).

## Séquencement recommandé

1. D'abord **C2** (une vraie classification bio) — prérequis du volet bio d'EGalim.
2. Puis obtenir/estimer la **demande restauration collective** (au moins scolaire) et la table
   **culture→groupe alimentaire**.
3. Implémenter couverture locale (le plus simple, ne dépend que de la demande + production).
4. Enfin la conformité EGalim complète (nécessite labels qualité + valeurs d'achat).

## Tests (TDD, data-free) — à l'implémentation

- Couverture par groupe = min(1, prod/demande) ; agrégat pondéré ; demande nulle → neutre.
- Parts EGalim (durable/bio) en valeur ; comparaison aux seuils 50 %/20 %.
- `recap["food_policy"]` absent si pas de données ; présent et cohérent sinon.

## Hors périmètre (rappel)

Aucun de ces scores ne devient une contrainte du modèle (reporting a posteriori, cf. décision
utilisateur). L'intégration au **score composite** suit exactement le mécanisme des chantiers
B/C1 (`comparison.compute_composite_scores`, indicateurs bénéfice, poids réglables).
