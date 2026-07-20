# Indicateurs besoin en eau et carbone organique du sol

_2026-07-20 — spec 1 sur 3 du chantier « indicateurs d'impact »._

## Contexte

Le modèle ne produit aujourd'hui que trois indicateurs environnementaux : azote, GES et IFT
(`case_studies/guadeloupe/environment.py`), plus la surface CLD à risque. Le GAMS d'origine
en calculait davantage, à partir de données déjà présentes dans `data/` mais jamais lues par
le pipeline Python.

Cette spec porte deux d'entre eux : le **besoin en eau des cultures** et le **bilan de carbone
organique du sol**. Deux autres suivront dans leurs propres specs : le score de stabilité
(nouveau) et Rpest / Tixier (risque de pollution de l'eau par les pesticides, le plus lourd).

Périmètre décidé : **reporting seul**. Les indicateurs sont calculés après le solve, alimentent
la table de faits et le score composite du dashboard, et n'influencent ni l'allocation ni la
faisabilité. Aucun solve réel n'est nécessaire pour valider ce lot.

## Ce que chaque indicateur dit

**Besoin en eau** — la pression exercée sur la ressource en eau par l'assolement retenu.
Permet de comparer des scénarios sur un axe absent aujourd'hui : un scénario peut gagner en
marge tout en tendant fortement la ressource.

**Bilan carbone organique** — le système enrichit-il ou appauvrit-il les sols ? C'est le seul
indicateur *cumulatif* du lot : les autres décrivent un flux annuel sans mémoire, celui-ci
porte sur un stock qui se dégrade ou se reconstitue. C'est aussi la réponse à la demande
« teneur organique et minérale des sols ».

## Architecture

Deux modules purs, sans I/O, testables sans `data/`, calqués sur le pattern de
`environment.py` (taux par hectare et par culture, appliqués ensuite à l'allocation).

### `case_studies/guadeloupe/water.py`

```
compute_monthly_water_need_per_ha_cult(data_cult) -> DataFrame  # 12 x cultures, mm/mois
compute_water_need_per_ha_cult(data_cult)         -> Series     # total annuel, mm/an
```

Source : lignes `BESOIN_EAU_01`..`BESOIN_EAU_12` de `Data_Cult.txt`.
Référence GAMS : `OPTIMISATION.txt:2489-2560`.

L'agrégation parcellaire respecte le filtre GAMS : une parcelle avec `IRRIG_PARC = 0`
contribue 0 (pas d'irrigation possible, donc pas de prélèvement sur la ressource).

**Conversion d'unité.** 1 mm d'eau sur 1 ha = 10 m³. Le besoin en m³ est donc
`mm × surface_ha × 10`. Le GAMS omet ce facteur 10 et divise par 1e6 (`OPTIMISATION.txt:2559`),
produisant une unité incohérente — l'auteur avait lui-même laissé le commentaire
« pourquoi x 10 ? » dans `DECLAR_OPT.txt:2114`. On expose des m³ corrects, avec le facteur
en constante nommée et documentée. Sans effet sur le classement des scénarios de toute façon,
le score composite normalisant en min-max.

### `case_studies/guadeloupe/soil_carbon.py`

Trois mécanismes distincts, donc trois fonctions séparées — on veut pouvoir lire et tester
chacun indépendamment, et seul le troisième est parcellaire.

```
compute_residue_carbon_per_ha_cult(data_cult)   -> Series  # entrées par les résidus
compute_amendment_carbon_per_ha_cult(...)       -> Series  # entrées par les amendements
compute_initial_soil_carbon_per_ha_plot(...)    -> Series  # stock initial, parcellaire
compute_mineralization_per_ha_plot(...)         -> Series  # sorties, parcellaire
compute_carbon_balance_per_ha_plot(...)         -> Series  # entrées - sorties
```

Formules, fidèles à `OPTIMISATION.txt:2880-2947` :

| Terme | Formule | Sources |
|---|---|---|
| Résidus | `BIOM_AER × (1 + RAC) × CARB × HRES` | `Data_Cult` |
| Amendements | `Σ_OTK DOSE × HUM × CARB × FHUM × Matrice_OTK_Cult` | `Data_OTK`, matrice ITK |
| Stock initial | `PART_C_INIT/100 × DENS[sol] × PROF[sol] × 10000` | `Data_Parc`, `Data_Sol` |
| Minéralisation | `C_ORG × KAER[sol] × KCROP[culture]` | `Data_Sol`, `Data_Cult` |

Nouveau lecteur : `Data_Sol.txt` (`KAER`, `DENS`, `PROF`, `KOC`). `KOC` n'est pas utilisé ici
mais le sera par Rpest — le lecteur charge la table entière.

### Piège : le mapping des types de sol

`SOL.set` et les colonnes de `Data_Sol.txt` sont ordonnés :

```
NITISOL, ANDOSOL, FERRALSOL, AUTRES, VERTISOL
```

Le code GAMS mappe la colonne numérique `TYPE_SOL` de `Data_Parc` dans un **ordre différent** :

```
1 -> VERTISOL   2 -> FERRALSOL   3 -> ANDOSOL   4 -> NITISOL   5 -> AUTRES
```

Indexer `Data_Sol` par position donnerait des coefficients faux mais plausibles — donc une
erreur silencieuse, qui ne ferait échouer aucun test générique. Le mapping vit dans une
constante nommée explicite, `_TYPE_SOL_TO_SOIL_NAME`, avec un test dédié qui vérifie chacune
des cinq entrées contre les lignes GAMS correspondantes.

### Intégration au reporting

Quatre scalaires ajoutés à `compute_environmental_totals` (`reporting/indicators.py`) puis à
`INDICATOR_DIRECTION` (`dashboard/comparison.py`), qui les intègre alors automatiquement au
score composite :

| Indicateur | Direction |
|---|---|
| `total_water_need_m3` | `cost` |
| `water_need_peak_month_m3` | `cost` |
| `soil_carbon_balance` | `benefit` |
| `soil_carbon_mineralization` | `cost` |

Le **mois de pointe** est retenu en plus du total annuel parce que c'est lui qui dimensionne
la ressource et l'infrastructure : deux scénarios de même total annuel n'ont pas la même
tension si l'un concentre son besoin sur deux mois. Le détail des 12 mois part dans
`output_N/csv/water_need_monthly_<side>.csv` pour le dashboard, sans entrer dans le score.

Comme pour les indicateurs existants, tout est décliné **entrée** (baseline via
`baseline_representative_crops`) et **sortie** (allocation optimisée).

## Écarts au GAMS, assumés et documentés

Chacun sera reporté dans `VIGILANCE.md`.

**1. Carbone : flux annuel, pas trajectoire de stock.** Le GAMS itère
`C_ORG = C_ORG + (entrées − sorties)` sur plusieurs années (`NB_BOUCLE`,
`OPTIMISATION.txt:2946`). Le modèle Python est mono-année et mono-solve : on porte le flux
d'une année, qui répond à la question posée (le système appauvrit-il les sols, et de combien)
sans prétendre projeter une trajectoire. Une projection pluriannuelle demanderait de
ré-allouer année après année — c'est un autre projet, pas un indicateur.

**2. Eau : besoin brut, la pluie n'est jamais déduite.** La formule GAMS soustrait
`PLUVIO_01_PARC`..`PLUVIO_12_PARC`, colonnes **absentes** de `Data_Parc_Gwad_2017.txt` (qui
n'a qu'un `PLUVIO_PARC` annuel). GAMS renvoie 0 sur colonne manquante — même mécanique que le
bug `Eq_VE_PLUIE` déjà documenté. L'indicateur est donc un besoin en eau **brut des cultures**,
pas un besoin net d'irrigation, et doit être nommé et présenté comme tel. Débloquable par une
série pluviométrique mensuelle par parcelle, qui n'existe pas aujourd'hui.

**3. Bug `max(0, besoin − pluie)`, porté tel quel.** Le `$` GAMS ne conditionne que le terme
pluie, pas la soustraction : quand le besoin est inférieur à la pluie, l'expression vaut
`BESOIN − 0 = BESOIN` au lieu de `0`. L'intention était clairement `max(0, ·)`. Décision :
porter le comportement réel (mandat de parité, cohérent avec la décision du 2026-07-20 sur
`Eq_VE_*`), avec la variante corrigée disponible en `enable: false` juste à côté dans
`config.yaml`. À noter : tant que la pluie mensuelle est absente, les deux variantes donnent
le **même** résultat — le choix ne devient visible que si les données mensuelles arrivent.

**4. Les amendements ne sont pas annualisés.** `C_ENTREE_AMDT` n'est divisé ni par
`Duree_Cycle_Cult` ni par `Duree_Plant_Cult`, contrairement à azote, GES et aux coûts, qui
passent tous par `_otk_annual_rate_per_ha_cult`. C'est ce que fait le GAMS
(`OPTIMISATION.txt:2919`). On le reproduit, mais ça ressemble à un oubli côté source : à
signaler si une comparaison à des données observées est un jour menée.

## Tests

Convention du repo : configs minuscules montées à la main, pas de lecture de `data/`
(cf. `tests/test_guadeloupe_constraints.py`).

- `tests/test_water.py` — besoin mensuel et annuel sur 2 cultures × 3 parcelles ; parcelle
  `IRRIG_PARC = 0` exclue ; conversion mm → m³ ; identification du mois de pointe quand deux
  mois sont à égalité.
- `tests/test_soil_carbon.py` — chacune des quatre formules isolément sur des valeurs
  calculées à la main ; **le mapping des cinq types de sol** ; le bilan change de signe quand
  on bascule d'une culture à forts résidus vers une culture à faibles résidus (le test qui
  attrape une inversion entrées/sorties) ; parcelle sans culture allouée → bilan nul.
- `tests/test_indicators.py` (existant, à étendre) — les trois nouveaux scalaires apparaissent
  dans `compute_environmental_totals` et dans la table de faits, côté entrée comme sortie.

Aucun test ne résout de MILP ; le lot reste dans la fourchette rapide de la suite.

## Hors périmètre

- Toute contrainte ou tout objectif s'appuyant sur ces indicateurs (décision : reporting seul).
- La trajectoire pluriannuelle de carbone.
- La déduction de la pluie (bloquée par les données).
- Rpest et le score de stabilité, qui ont leurs propres specs.
- Les graphes statiques : conformément à la décision du 2026-07-13, les visualisations riches
  vivent dans le dashboard, pas dans les PNG de `output_N/`.
