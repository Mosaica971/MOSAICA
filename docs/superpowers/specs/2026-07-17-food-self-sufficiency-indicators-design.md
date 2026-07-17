# Autonomie alimentaire — ratios d'auto-approvisionnement nutritionnel (chantier C1)

## Contexte

Objectif du chantier C : mesurer l'autonomie alimentaire de la Guadeloupe. L'exploration a
montré que le cœur du besoin est **déjà porté par le GAMS d'origine** (indicateurs n°5/6/7,
« Reaching food self-sufficiency », `OPTIMISATION.txt:1947-1975`) et repose sur des données
**déjà présentes dans le repo** : `Nutri_Cult.txt` (teneur nutritionnelle par culture, par
tonne) et `Nutri_Alim.txt` (besoins annuels par individu moyen, population, contribution
pêche). Aucune donnée externe n'est requise.

Ce chantier porte C1 (autonomie nutritionnelle). C2 (part de bio) et C3 (restauration
collective / EGalim) sont **hors périmètre** : C2 est fragile (le bio n'est inférable que du
token `BIO` dans les codes, maraîchage seulement) ; C3 exige des données externes absentes du
repo. Cohérent avec la contrainte utilisateur : ce sont des **indicateurs de reporting a
posteriori**, jamais des contraintes du modèle (le GAMS les calcule aussi comme indicateurs).

## Décisions retenues

- **Tous les nutriments** de `VAR_NUT` (Kcal, Lip, Glu, Fibres, Prot, Ca, P, Mg, K, Fe = 10),
  pas seulement les 4 de `SVAR_NUT` (Kcal/Glu/Prot/Lip) du GAMS : même formule, appliquée au
  jeu complet que les données supportent (superset fidèle).
- **Deux variantes** par nutriment : *avec pêche* (fidèle au GAMS) et *cultures seules*
  (autonomie agricole pure).
- **Intégration dashboard** : ratios ajoutés aux indicateurs cochables du profil et au
  **score composite** (bénéfice : plus haut = mieux), le nutriment limitant servant
  d'indicateur d'autonomie global.

## Données (déjà présentes)

- `data/tables/Nutri_Cult.txt` : lignes = nutriments (`Kcal`,`Lip`,…,`Fe`), colonnes =
  cultures. Teneur par **tonne** de production.
- `data/tables/Nutri_Alim.txt` : lignes = `Q_Tot` + nutriments ; colonnes = `Ind_Moy`, tranches
  démographiques, `peche`, `import`. On utilise : `Ind_Moy` (besoin annuel/individu moyen),
  `Q_Tot`×`Ind_Moy` = **population** (400 736), `peche` (teneur pêche + `Q_Tot`,`peche` =
  tonnage pêché = 10 000).

## Formules (fidèles au GAMS, par allocation et par nutriment n)

```
crop_production(n)    = Σ_crop  production_tonnes(crop) · Nutri_Cult(n, crop)
fishing_production(n) = Nutri_Alim(n, "peche") · Nutri_Alim("Q_Tot", "peche")
population            = Nutri_Alim("Q_Tot", "Ind_Moy")
need(n)               = Nutri_Alim(n, "Ind_Moy") · population
ratio_crop_only(n)    = crop_production(n) / need(n)
ratio_with_fishing(n) = (crop_production(n) + fishing_production(n)) / need(n)
limiting(variant)     = min_n ratio(n)            # nutriment contraignant
```

`production_tonnes(crop)` = `compute_production_tonnes_by_crop` existant (surface × rdt) —
donc valide pour la **sortie** (cultures fines) comme pour l'**entrée** (baseline
représentative), exactement comme l'économie/environnement. Les ratios sont sans dimension
(numérateur et dénominateur dans la même unité de nutriment), donc les unités par tonne
s'annulent.

## Architecture (cohérente avec les chantiers A/B)

### 1. Paramètres — `data_pipeline.py`

Lire `Nutri_Cult.txt` et `Nutri_Alim.txt` (`read_wide_table`) et les ajouter à
`dataset.parameters` sous `nutri_cult` et `nutri_alim`. Aucun calcul au build : les tables
brutes suffisent, les indicateurs en dérivent population/besoins/pêche.

### 2. Indicateurs — `reporting/indicators.py`

- `compute_nutrient_production(dataset, allocation, include_fishing: bool) -> pd.Series`
  (index = nutriment) : `nutri_cult · production_tonnes` (produit matriciel) + terme pêche
  optionnel.
- `compute_self_sufficiency_ratios(dataset, allocation, include_fishing) -> pd.Series` :
  production / need par nutriment.
- `compute_food_autonomy_totals(dataset, allocation) -> dict` : les deux variantes complètes
  + le nutriment limitant de chacune + la population. Forme :
  ```python
  {
    "population": 400736.0,
    "crop_only": {"kcal": r, "lip": r, ..., "fe": r},
    "with_fishing": {...},
    "limiting_crop_only": min_ratio,
    "limiting_with_fishing": min_ratio,
  }
  ```
  Les clés nutriments sont normalisées en minuscules (`kcal`, `lip`, …) pour des clés de recap
  stables, indépendamment de la casse du fichier.

### 3. Persistance — `reporting/report.py`

Nouveau bloc `recap["food_autonomy"]` avec `input` / `output` / `delta`, chaque côté étant le
dict de `compute_food_autonomy_totals`. Le `delta` se calcule clé à clé sur les scalaires
(récursif d'un niveau pour les sous-dicts `crop_only`/`with_fishing`). Runs antérieurs sans le
bloc : dashboard défensif (`.get`). La ventilation par nutriment n'entre **pas** dans la table
`facts` (les ratios ne sont pas additifs par culture×région) — c'est un indicateur territoire.

### 4. Dashboard — `dashboard/pages/2_Comparaison.py`

- **Indicateurs sélectionnables + score composite** : ajouter au catalogue des clés plates,
  toutes **bénéfice** (plus haut = mieux) :
  - `autonomy_limiting` (limitant, cultures seules) — l'indicateur d'autonomie global,
  - `autonomy_<nutriment>` pour les 10 nutriments (variante cultures seules).
  `_indicator_value` route ces clés vers `recap["food_autonomy"][side]` (limitant →
  `limiting_crop_only` ; par nutriment → `crop_only[nutriment]`). La variante *avec pêche*
  reste dans le recap et s'affiche dans le panneau dédié (ci-dessous), sans surcharger la
  liste du score.
- **Panneau dédié « Autonomie alimentaire »** : barres groupées par nutriment, deux variantes
  (cultures seules vs avec pêche) par scénario sélectionné, avec une ligne de référence à
  100 % (auto-suffisance). Réutilise les couleurs par scénario. La logique de mise en forme
  (construction du DataFrame nutriment×variante depuis les recaps) passe par un helper pur
  testé de `comparison.py` ; la page ne fait que le tracé.

## Configuration

Rien de nouveau : population, besoins, teneurs et pêche viennent des tables de données. (Pas
de clé YAML — contrairement au `coeff_c_co2` du chantier B, il n'y a pas de constante libre.)

## Hors périmètre

- **C2 (part de bio)** : inférence fragile depuis les codes, maraîchage seulement — spec
  ultérieure si souhaité (idéalement après ajout d'une vraie classification bio en donnée).
- **C3 (restauration collective, aide alimentaire, conformité EGalim 50 %/20 %)** : nécessite
  des données externes (volumes cantines, tonnages aide alimentaire, liste de labels
  « durable/qualité ») absentes du repo. À cadrer quand les données seront disponibles.
- Aucun de ces ratios ne devient une contrainte du modèle.

## Tests (TDD, data-free — style `tests/test_guadeloupe_*`)

- `compute_nutrient_production` : mini `nutri_cult` + allocation ; vérifier
  `Σ tonnes·teneur` et l'ajout du terme pêche quand `include_fishing=True`.
- `compute_self_sufficiency_ratios` : ratio = production / (besoin/hab × population), les deux
  variantes, avec des chiffres calculés à la main ; nutriment à ratio < 1 et > 1.
- `compute_food_autonomy_totals` : les deux variantes, le limitant = min, la population.
- `report.generate_report` : présence et cohérence du bloc `recap["food_autonomy"]`
  (input/output/delta), sur le `_tiny_dataset` étendu avec `nutri_cult`/`nutri_alim`.
- `comparison` : helper pur de mise en forme du panneau (DataFrame nutriment×variante) et
  routage des clés `autonomy_*` dans le profil/score composite.
