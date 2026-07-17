# Indicateurs environnementaux + score agrégé (chantier B)

## Contexte

Le dashboard n'expose aujourd'hui, comme critères de comparaison de scénarios, que
l'économie (marge/revenu/subvention/production/ETP) et deux indicateurs sociaux (Gini
du revenu par exploitation, diversité de Shannon). Le MOSAICA GAMS d'origine calculait
en plus une batterie d'indicateurs **environnementaux** (voir `RESULTATS.txt` bloc
`INDICATEURS.TXT` et `OPTIMISATION.txt`). Ce chantier en porte les quatre prioritaires
et ajoute un **score agrégé** paramétrable.

## Objectif

1. Calculer, pour toute allocation (sortie du solveur **et** baseline représentative,
   comme les indicateurs économiques existants), quatre indicateurs environnementaux :
   **azote**, **GES** (gaz à effet de serre), **IFT** (indice de fréquence de
   traitement phytosanitaire), **chlordécone** (surface cultivée sur sol à risque).
2. Les persister au niveau territoire (recap.json) **et** par culture×région (table
   `facts`), pour alimenter les graphes et l'axe parallèle existants.
3. Ajouter au dashboard de comparaison : le choix (cases à cocher) des indicateurs
   affichés, incluant les nouveaux, et un **score composite** par scénario avec
   **pondération interactive**.

R_PEST (indice de risque toxicologique parcellaire composite, `R_PEST_NEW.txt`) est
**hors périmètre** de ce chantier (déféré).

## Faisabilité — données déjà présentes

Aucune nouvelle donnée requise. Le pipeline charge déjà `data_otk`
(`data/tables/Data_OTK.txt`) et `matrice_otk_cult`
(`Matrice_OTK_Cult_<scenario>.txt`), et calcule des taux/ha par le motif
`matrice_otk_cult.multiply(rate, axis=0).sum() / duree_cycle * 12` avec la ventilation
AMORTI 0/1 (cf. `economics.compute_variable_cost_per_ha_cult`). Les colonnes utiles de
`Data_OTK` existent : `AZOTE`, `GES_SURF`, `GES_Q`, `IFT`, `DOSE`, `AMORTI`. La
chlordécone est dans `Data_Parc_Gwad_2017` (`RISQUE_CLD`, `CLD_KG_HA`).

## Formules (fidèles au GAMS `OPTIMISATION.txt`)

Toutes les sommes sont sur les opérations `SK`, avec le même traitement AMORTI que le
coût variable (terme amorti divisé par `Duree_Plant_Cult`), normalisées
`/ Duree_Cycle_Cult * 12` (taux annuel).

- **Azote** (kg N/ha/an) : `Σ_SK Matrice(SK,SC)·DOSE·AZOTE`.
- **GES** (t CO₂/ha/an) : `Σ_SK Matrice(SK,SC)·(GES_SURF + GES_Q·Rdt_Cult(SC))`, le tout
  divisé par `COEFF_C_CO2` (= 0.272, conversion carbone→CO₂). Note : GES_SURF et GES_Q
  ne sont **pas** multipliés par DOSE ; GES_Q est multiplié par le rendement.
- **IFT** (traitements/ha/an) : `Σ_SK Matrice(SK,SC)·IFT`. (IFT non multiplié par DOSE.)

Puis, pour une allocation (surface par parcelle × taux de la culture assignée) :
territoire = Σ parcelles ; moyenne/ha = total / SAU cultivée.

- **Chlordécone** (`RCLD_Gwad`, GAMS `OPTIMISATION.txt` indicateur n°10) : ce n'est
  **pas** un simple seuil sur le sol, mais une **interaction culture × sol** — une
  parcelle produit un aliment « à risque » (`NV_CLD_parc = 1`) selon la classe
  d'absorption chlordécone de la culture assignée (`Data_Cult["CLD"]`, 1=fort … 4=nul),
  le niveau de contamination du sol (`RISQUE_CLD`, 1=très important … 5=nul) et le type
  de sol (`TYPE_SOL`). Règle fidèle (avec `c = Data_Cult["CLD"](crop)`,
  `r = RISQUE_CLD(parcelle)`, `s = TYPE_SOL(parcelle)`) :

  - `c=1 et r≤3` → à risque
  - `c=2 et r≤2` → à risque
  - `c=3 et r≤2 et s∈{2,4}` → à risque
  - `c=3 et r=1 et s∈{1,3,5}` → à risque
  - sinon (dont `c=4`) → pas à risque

  Métrique territoire = `Σ SURF_HA` des parcelles allouées où `NV_CLD_parc=1`. C'est bien
  **dépendant de l'allocation** (l'intérêt : ne pas cultiver de plante accumulatrice sur
  sol contaminé). Données : `Data_Cult["CLD"]` (à exposer dans `dataset.parameters` sous
  `cld_uptake_cult`), `RISQUE_CLD` et `TYPE_SOL` (déjà dans `data_parc`).

## Architecture

Deux couches, cohérentes avec l'existant :

### 1. Taux/ha par culture — nouveau module `case_studies/guadeloupe/environment.py`

Mirroir de `economics.py`, pour ne pas gonfler ce dernier. Trois fonctions pures :

```python
compute_azote_per_ha_cult(data_otk, matrice_otk_cult, duree_cycle_cult, duree_plant_cult) -> pd.Series
compute_ges_per_ha_cult(data_otk, matrice_otk_cult, duree_cycle_cult, duree_plant_cult, rdt_cult, coeff_c_co2) -> pd.Series
compute_ift_per_ha_cult(data_otk, matrice_otk_cult, duree_cycle_cult, duree_plant_cult) -> pd.Series
```

`build_dataset` (`data_pipeline.py`) les calcule et les ajoute à
`dataset.parameters` sous `azote_per_ha_cult`, `ges_per_ha_cult`, `ift_per_ha_cult`
(comme `margin_per_ha_cult` etc.), en réutilisant `duree_cycle_cult`,
`duree_plant_cult`, `rdt_cult` déjà présents.

### 2. Indicateurs appliqués à l'allocation — `reporting/indicators.py`

- `compute_ges_by_crop` / `compute_ift_by_crop` / `compute_azote_by_crop` : surface par
  culture × taux/ha (comme `compute_production_tonnes_by_crop`).
- `compute_cld_at_risk_surface(dataset, allocation)` : applique la règle
  culture×sol ci-dessus par parcelle allouée (`Data_Cult["CLD"]`, `RISQUE_CLD`,
  `TYPE_SOL`) et somme `SURF_HA` des parcelles à risque. Vectorisé (masque booléen), pas
  de boucle Python.
- `compute_environmental_totals(dataset, allocation, coeff)` → dict
  `total_ges`, `total_ift`, `total_azote`, `surface_cld` + moyennes/ha
  (`ges_per_ha`, `ift_per_ha`, `azote_per_ha` = total / SAU).
- **`compute_facts_table` étendu** : nouvelles colonnes additives `ges`, `ift`,
  `azote` (surface×taux) et `surface_cld` (SURF_HA de la parcelle si `NV_CLD_parc=1`
  selon la règle culture×sol, sinon 0 — calculé au niveau parcelle avant le
  `groupby(['crop','region'])`). Ajout des quatre à `_FACT_MEASURES` (toutes additives).

Les indicateurs valent pour les deux côtés (sortie fine et baseline représentative), la
baseline passant par `decode_baseline_representative_allocation` comme l'économie.

### 3. Persistance — `reporting/report.py`

Nouveau bloc `recap["environment"]` symétrique de `recap["economics"]` :
`{input: {...totaux+moyennes/ha}, output: {...}, delta: {...}}`. Les colonnes
`ges/ift/azote/surface_cld` s'ajoutent automatiquement à `facts_{side}.csv` via la table
facts étendue. Les runs antérieurs (sans ce bloc) restent lisibles : le dashboard garde
partout un `.get(...)` défensif comme pour `total_net_revenue`.

### 4. Score composite + UI — `dashboard/comparison.py` + `pages/2_Comparaison.py`

**Fonction pure** (testée) dans `comparison.py` :

```python
def compute_composite_scores(raw: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """raw indexé par série (scénario), une colonne par indicateur choisi.
    Chaque colonne est min-max normalisée sur les lignes (0=pire, 1=meilleur du lot) ;
    les indicateurs 'coût' (GES/IFT/azote/chlordécone/Gini/subvention/coût MO) sont
    inversés pour que 'meilleur' = 1. Score = moyenne pondérée des colonnes normalisées.
    Colonne constante -> 0.5 (aucun écart à départager). Poids nuls ignorés."""
```

Le **sens** de chaque indicateur (bénéfice vs coût) est une constante
`INDICATOR_DIRECTION` du module. Bénéfice : production, revenu, marge, revenu net, ETP.
Coût : subvention, coût MO, GES, IFT, azote, surface chlordécone, Gini.

**Page de comparaison** :
- `_INDICATOR_LABELS` étendu avec `total_ges`, `total_ift`, `total_azote`,
  `surface_cld` (lus depuis `recap["environment"][side]`).
- Le `multiselect` « Indicateurs » existant **est** le mécanisme de cases à cocher : il
  liste désormais aussi les indicateurs environnementaux.
- Sous l'axe parallèle, nouveau bloc « Score agrégé » : un `st.slider` de poids par
  indicateur choisi (défauts = constante `DEFAULT_WEIGHTS`, poids égaux), puis un
  bar chart horizontal des scores par scénario (couleurs par scénario déjà gérées),
  via `compute_composite_scores`.

## Configuration (YAML)

Sous une nouvelle clé `reporting.environment` de `config.yaml` (le pipeline la lit au
build/report) :

```yaml
reporting:
  environment:
    coeff_c_co2: 0.272   # conversion carbone -> CO2 (constante GAMS)
```

La règle chlordécone est fidèle au GAMS et n'a **pas** de paramètre libre (pas de seuil
en config). Les **poids** du score restent dans le dashboard (sliders, défauts
constants) : le dashboard est découplé de `config.yaml` (lecture seule sur `outputs/`).
Le sens bénéfice/coût est une constante code (non pertinent à exposer à l'utilisateur).

## Détails d'implémentation confirmés à l'exploration

- `RISQUE_CLD` est catégoriel **1–5** (1 = très contaminé … 5 = nul ; distribution réelle
  1:3975, 2:14, 3:454, 4:14909, 5:5382) et `Data_Cult["CLD"]` est **1–4** (1 = forte
  absorption … 4 = nulle). La règle GAMS ci-dessus utilise ces échelles telles quelles.
- Vérifier au RED que `duree_plant_cult`, `rdt_cult`, `duree_cycle_cult` sont bien
  exposés dans `dataset.parameters` (utilisés par le coût variable — sinon les récupérer
  au même endroit du pipeline).

## Hors périmètre

- **R_PEST** (risque toxicologique composite parcellaire) et les attributs associés
  (ADI/DT50/GUS/AQUATOX/HOUDART_*) : chantier ultérieur.
- Indicateurs sociaux GAMS (emploi par type d'exploitation `EFF_TYPE`/`PART_TYPE`,
  répartition POSEI/national/PDRG) : hors périmètre ici (candidats futurs).
- Aucun de ces indicateurs ne devient une **contrainte** du modèle : reporting a
  posteriori uniquement.
- Chantier C (autonomie alimentaire / EGalim) : spec séparée, ensuite.

## Tests (TDD, data-free — style `tests/test_guadeloupe_*`)

- `environment.py` : `compute_{azote,ges,ift}_per_ha_cult` sur un mini `data_otk` +
  `matrice_otk_cult` construits à la main, avec vérification du terme AMORTI et, pour GES,
  du terme `GES_Q·Rdt` et de la division par `coeff_c_co2`.
- `indicators.py` : `compute_{ges,ift,azote}_by_crop` (surface×taux) ;
  `compute_cld_exposed_surface` (seuil, parcelles à/hors risque) ;
  `compute_environmental_totals` (totaux + moyennes/ha) ; `compute_facts_table`
  contient les nouvelles colonnes et reste additif.
- `comparison.compute_composite_scores` : min-max, inversion des indicateurs coût,
  pondération, colonne constante → 0.5, poids nuls ignorés, une seule série (dégénéré).
- Robustesse dashboard : un recap sans bloc `environment` n' empêche pas l'affichage
  (indicateurs env simplement absents de la liste).
