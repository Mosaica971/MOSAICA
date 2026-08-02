# Calibration et validation : comparer la situation observée à la situation simulée

_2026-07-21 — d'après Chopin, P., Blazy, J-M., Guindé, L., Doré, T., 2015. « MOSAICA: A
multi-scale bioeconomic model for the design and ex ante assessment of cropping system
mosaics », Agricultural Systems 140, 26-39 (`context/Chopin et al 2015 pour Hal.pdf`, racine du
dépôt), §2.5, §2.6 et §3.1._

## Contexte

Rien dans le dépôt ne dit aujourd'hui si le modèle **reproduit la Guadeloupe**. Le reporting
compare une entrée à une sortie et en donne les écarts, mais ne pose jamais la question de la
justesse : l'allocation simulée ressemble-t-elle à l'assolement réellement observé ?

L'article y répond par une procédure explicite, en deux temps distincts qu'il ne faut pas
confondre :

- **§2.5 Calibration** — le choix des coefficients d'aversion au risque Ø, un par type
  d'exploitation. C'est le seul degré de liberté calé sur les données ; tout le reste
  (rendements, prix, coûts, contraintes) vient de la base d'activités.
- **§2.6 Évaluation** — la mesure de l'écart entre l'assolement observé et l'assolement
  simulé sous la politique courante, à quatre échelles emboîtées, avec des seuils publiés.

Cette spec implémente **§2.6 seulement**. Les Ø de la Table 2 sont déjà portés dans le dépôt
(voir plus bas), et la recherche itérative de §2.5 supposerait une centaine de solves à
30-55 minutes pièce. Le périmètre est donc : **reporting seul**, aucune modification du
modèle, aucun solve déclenché.

## Ce que mesure l'évaluation

### La métrique : le PAD

L'article, Eq. 7 :

```
PAD = 100 × Σ_a |X_init(a) − X(a)| / Σ_a X_init(a)
```

`X_init(a)` est la surface **observée** de la culture *a* dans la base géographique de l'année
de base ; `X(a)` la surface **simulée** sur le même jeu de parcelles sous la politique
courante. Le PAD est nul quand la simulation reproduit exactement l'observé.

Deux lectures coexistent dans l'article et ne sont **pas** interchangeables :

| | Formule | Usage dans l'article |
|---|---|---|
| PAD par culture | `100 × \|X_init(a) − X(a)\| / X_init(a)` | « PAD de 100 % pour le melon », « 5 % pour la canne au centre Grande-Terre » |
| PAD global | `100 × Σ\|X_init(a) − X(a)\| / ΣX_init(a)` | le verdict d'ensemble à une échelle |

Les deux sont produits. Un groupe observé à 0 hectare rend le PAD par culture indéfini
(division par zéro) : la valeur est `NaN`, la surface apparue est reportée à part.

### Les quatre échelles et leurs seuils

| Échelle | Article | Ce qui est comparé | Seuil | Résultat obtenu par l'article |
|---|---|---|---|---|
| Régionale | §3.1.1, Fig. 4 | surface par culture, tout le territoire | PAD < 15 % | 8 usages sur 10 conformes |
| Sous-régionale | §3.1.2, Fig. 5 | surface par culture × 7 zones sol/climat | PAD < 20 % | conforme sauf pâture SO Basse-Terre (28 %) |
| Exploitation | §3.1.3, Table 4 | matrice de confusion 8×8 des types, observé × simulé | 80 % sur la diagonale | 81 % |
| Parcelle | §3.1.4, Table 5 | part des parcelles et part de la surface où la culture simulée égale l'observée | — | 66 % des parcelles, 77 % de la surface |

L'article énonce en outre un seuil de PAD < 20 % « in the sub-regions **and farms** » sans en
publier le tableau. Un cinquième bloc le calcule : PAD par exploitation, et part des
exploitations sous le seuil.

### Les seuils sont conventionnels, pas physiques

15 % et 20 % viennent de Kanellopoulos et al. (2010), Hazell et Norton (1986) et Janssen et van
Ittersum (2007), cités par l'article. Ils sont donc placés en configuration, pas en dur, avec
les valeurs de l'article par défaut.

## État des lieux dans le dépôt

Une bonne part des briques existe.

| Élément de l'article | Dans le dépôt |
|---|---|
| `X_init`, situation observée | `indicators.decode_baseline_allocation()` → `cult_2017` → 12 groupes RPG ; exporté en `csv/allocation_input.csv` |
| `X`, situation simulée | `indicators.decode_output_allocation()` → 84 cultures fines ; exporté en `csv/allocation_output.csv` |
| 7 sous-régions sol/climat | colonne `REGION`, codes 1-7 — correspondance exacte, noms déjà dans `dashboard/comparison.py:65` |
| 8 types d'exploitation + algorithme if-then | `domain/farm_typology.compute_type_expl()` |
| Coefficients Ø calibrés (Table 2) | `farm_typology._AVERS_BY_TYPE_EXPL` |
| Objectif Markowitz (Eq. 1) | `maximize_risk_adjusted_gross_margin`, présent mais `enable: false` |
| Plafond de main-d'œuvre par ferme (Eq. 5) | **non porté** (`docs/04-vigilance.md`, `Eq_MO_MAX_Expl`) |
| PAD, matrice de confusion, taux parcellaire | **rien** — objet de cette spec |

### Les Ø portés correspondent à la Table 2, à une exception près

| Type | Nom (article) | Ø article | `_AVERS_BY_TYPE_EXPL` |
|---|---|---|---|
| 1 | Arboriculteurs | 1.3 | 1.30 |
| 2 | Bananiers | 1.2 | 1.20 |
| 3 | Canniers spécialisés | 0.3 | 0.30 |
| 4 | Canniers diversifiés | 1.4 | **0.50 / 1.60** selon `TYPE_EXPL_Bis` (41/42) |
| 5 | Diversifiés | 0.55 | 0.55 |
| 6 | Éleveurs | 2.4 | 2.40 |
| 7 | Maraîchers | 0.0 | 0.00 |
| 8 | Canniers-éleveurs | 2.3 | 2.30 |

Le type 4 est le seul écart : le GAMS le scinde en deux sous-types là où l'article publie une
valeur unique. Le GAMS a donc continué d'évoluer après la publication. C'est une observation,
pas une action — aucune des deux valeurs n'est à corriger sans arbitrage.

## Le problème de résolution : 12 groupes contre 84 cultures

La situation observée n'existe qu'au niveau **agrégat RPG** : 12 groupes
(`farm_typology._RPG_CODE_TO_BASE_GROUP`). La variante technique de 2017 n'a jamais été
relevée — le GAMS faisait pareil, ce n'est pas un portage manquant (`docs/04-vigilance.md`, point sur
la baseline agrégée). La sortie du solveur, elle, est en 84 cultures fines.

La comparaison se fait donc en **agrégeant le simulé vers les 12 groupes observés**. C'est
exactement ce que fait la Fig. 4 de l'article, qui compare « 10 agricultural uses » et non les
36 systèmes de culture de sa base d'activités.

Deux correspondances méritent d'être écrites parce qu'elles ne sont pas déductibles du seul
préfixe :

- `CF_*` (canne fibre) → `CS`. Le RPG ne distingue pas canne à sucre et canne fibre : les deux
  tombent sur le code 6. Rattacher `CF` à `CS` est la seule lecture cohérente avec l'observé.
- `TH` (tomate) → `MA`. La tomate relève du maraîchage de plein champ dans la nomenclature RPG.

## Architecture

Un module de calcul, quatre consommateurs. Le calcul ne connaît ni Streamlit, ni matplotlib,
ni le système de fichiers.

### 1. `case_studies/guadeloupe/domain/crop_families.py` — nouveau

```python
def base_group_for(crop: str) -> str
def base_groups_for(crops: pd.Series) -> pd.Series
```

Table de préfixes explicite, miroir de `_RPG_CODE_TO_BASE_GROUP` :

```
CS_* , CF_*        -> CS        AN_*               -> AN
BA_*               -> BA        IG_*               -> IG
BC_*               -> BC        PN_*               -> PN
MA_* , TH          -> MA        VE_*               -> VE
AG , ME , JA , NC  -> eux-mêmes
```

Un code inconnu lève `KeyError` — il ne tombe pas dans un groupe « autre » silencieux. Un test
balaie l'intégralité de `CROP_LABELS` et exige que chaque code atterrisse dans un des 12
groupes : l'ajout futur d'une culture au dépôt fait échouer la suite tant que la
correspondance n'est pas déclarée.

### 2. `case_studies/guadeloupe/domain/zones.py` — relocalisation

`REGION_LABELS`, `ISLAND_LABELS`, `REGION_CODES`, `ISLAND_CODES` quittent
`dashboard/comparison.py` pour `domain/`. Motif : le reporting en a besoin pour les axes des
figures, et `reporting/` ne doit pas importer `dashboard/`. Ce vocabulaire géographique est du
vocabulaire de case-study, il a sa place dans `domain/` à côté de `crop_labels.py`.
`comparison.py` les ré-exporte sous leurs noms actuels, donc `pages/2_Comparaison.py` et
`tests/test_guadeloupe_dashboard_comparison.py` ne changent pas. Quatre symboles, deux
fichiers appelants : le déplacement est contenu.

### 3. `case_studies/guadeloupe/reporting/calibration.py` — le cœur

Signature maison, celle d'`indicators.py` : `(dataset, allocation, config)`. Testable sur un
`Dataset` synthétique de six parcelles, sans accès à `data/`, comme
`tests/test_guadeloupe_reporting_indicators.py`.

```python
@dataclass(frozen=True)
class CalibrationThresholds:
    regional_pad_max: float      # 15.0
    subregional_pad_max: float   # 20.0
    farm_pad_max: float          # 20.0
    farm_type_match_min: float   # 80.0

def thresholds_from_config(config) -> CalibrationThresholds

def pad_by_crop(dataset, output_allocation) -> pd.DataFrame
def pad_by_crop_and_region(dataset, output_allocation) -> pd.DataFrame
def pad_by_farm(dataset, output_allocation) -> pd.DataFrame
def farm_type_confusion(dataset, output_allocation) -> pd.DataFrame
def field_match_rate(dataset, output_allocation) -> pd.DataFrame

def evaluate(dataset, output_allocation, config) -> dict[str, Any]
```

Colonnes produites :

- `pad_by_crop` — index groupe ; `observed_ha`, `simulated_ha`, `abs_deviation_ha`, `pad_pct`,
  `within_threshold`. Une ligne `TOTAL` porte le PAD global, avec son propre
  `within_threshold` : le verdict d'ensemble et les verdicts par culture sont distincts et
  peuvent diverger.
- `pad_by_crop_and_region` — index `(region, groupe)`, mêmes colonnes, seuil sous-régional.
- `pad_by_farm` — index ferme ; `observed_ha`, `simulated_ha`, `pad_pct`, `within_threshold`.
- `farm_type_confusion` — matrice 8×8 en effectifs de fermes, plus les types 0 (surface
  cultivée nulle) et -1 (défaut) s'ils apparaissent ; totaux en marge, part diagonale.
  L'univers est celui d'`expl_parc`, identique des deux côtés puisque les deux typologies sont
  recalculées par le même appel à `compute_type_expl` sur la même liste de fermes.
- `field_match_rate` — index région plus `TOTAL` ; `matched_plots`, `total_plots`,
  `plot_match_pct`, `matched_ha`, `total_ha`, `area_match_pct`. Une parcelle « concorde »
  quand le groupe de base simulé égale le groupe observé — la comparaison se fait au niveau
  des 12 groupes ici comme dans tous les autres blocs, jamais au niveau de la culture fine,
  que l'observé ne connaît pas.

`evaluate` assemble les cinq blocs et les verdicts booléens dans un dictionnaire sérialisable,
destiné à `recap["calibration"]`.

Le côté observé est recalculé **dans le module** par
`compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])`, sur l'univers
complet des parcelles, `NC` compris — voir la section fidélité.

### 4. Branchement dans `reporting/report.py`

`generate_report` construit déjà les deux allocations. Un `_write_calibration(...)` écrit
`csv/calibration_pad_by_crop.csv`, `..._by_crop_and_region.csv`, `..._by_farm.csv`,
`calibration_farm_type_confusion.csv`, `calibration_field_match.csv`, les deux figures, et
retourne le bloc `recap["calibration"]` repris dans `recap.json` et dans une section
« Calibration » de `recap.md` (verdicts et chiffres clés, dans le style des sections
existantes).

`scripts/golden_snapshot.py` est étendu des sommes de contrôle des cinq blocs : sans ça, le
nouveau calcul échappe à la vérification d'invariance. Un `--write` de rebaseline est
nécessaire à la livraison.

### 5. `scripts/evaluate_calibration.py`

```
.venv/Scripts/python scripts/evaluate_calibration.py outputs/output_12
.venv/Scripts/python scripts/evaluate_calibration.py --all
```

Le script lit `config_used.yaml` du dossier de run, reconstruit le `Dataset` (~7 s, aucun
solve — même coût que `golden_snapshot.py`), lit la colonne `crop` d'`allocation_output.csv`
comme allocation simulée, appelle `calibration.evaluate`, écrit les mêmes fichiers dans le
dossier du run et affiche les verdicts en console. Le `zone_filter` du run est repris avec le
reste de la configuration, donc l'univers de parcelles reconstruit est celui du run.

Il échoue explicitement si `data/` est absent : le module a besoin du `Dataset`, et une
approximation silencieuse depuis les seuls CSV fausserait la matrice de confusion.

### 6. Figures — `reporting/plots.py`

- `plot_calibration_regional(pad_by_crop, path)` — barres groupées observé / simulé par
  groupe, dans le style de `_save_bar_chart`. C'est la Fig. 4 de l'article.
- `plot_calibration_pad_heatmap(pad_by_crop_and_region, path)` — heatmap PAD région ×
  culture, avec la ligne de seuil marquée par la palette. Remplace les 7 sous-graphes de la
  Fig. 5 : le dépassement de seuil se lit d'un coup d'œil, ce qui est l'usage réel de la
  figure. Axes libellés via `domain/zones.REGION_LABELS` et `crop_labels.label_for`.

### 7. Page dashboard — `dashboard/pages/3_Calibration.py`

Sélecteur de run via `loaders.list_output_runs`, puis les cinq blocs lus par
`loaders.load_csv`, avec code couleur sur les seuils : tableau PAD régional, heatmap
région × culture, matrice de confusion 8×8, taux parcellaires, distribution du PAD par
exploitation. Lecture seule, structure calquée sur `2_Comparaison.py`. Un run antérieur à ce
chantier n'a pas les CSV : la page affiche alors la commande à lancer plutôt qu'une erreur.

## Fidélité : les pièges identifiés

### Les parcelles `NC` ne peuvent pas être ignorées

`compute_type_expl` calcule `denom = surf_cultiv − surf_non`, où `surf_cultiv` exclut `NC` et
`surf_non` agrège `JA` et `NC`. Une parcelle `NC` **diminue** donc le dénominateur et remonte
toutes les parts `PART_*`. Or `decode_baseline_allocation` écarte les `NC`, et
`allocation_input.csv` avec elles : reconstruire la typologie depuis ce fichier traiterait ces
parcelles comme inexistantes et non comme non cultivées, ce qui décale les parts et peut faire
basculer un type.

C'est la raison pour laquelle le module prend le `Dataset` et recalcule les groupes de base
sur l'univers complet. Côté simulé, une parcelle sans culture affectée — le modèle autorise
`at_most_one_crop_per_plot`, donc l'absence d'affectation est possible — compte comme `NC`,
ce qui est sa signification agronomique.

### Les deux allocations ne couvrent pas le même jeu de parcelles

Sur `outputs/output_12` : 22 197 lignes observées non `NC` contre 22 779 simulées. Une parcelle
`NC` en 2017 qui reçoit une culture est un changement réel, pas une anomalie de données. Le PAD
et le taux de correspondance travaillent donc sur l'**union** des parcelles, l'absence d'un
côté valant surface nulle pour la culture concernée.

### `VE_PLUIE` n'apparaîtra jamais

`docs/04-vigilance.md` documente un bug GAMS porté fidèlement : `Eq_VE_PLUIE` interdit la culture sur
**toute** parcelle. Si le PAD des vergers ressort mauvais, c'est le premier suspect, et ce
n'est pas un défaut du module d'évaluation.

## Le diagnostic attendu

Sur `outputs/output_12`, l'observé compte 10 955 parcelles en canne, 5 524 en prairie, 1 947 en
banane. Le simulé est **intégralement en maraîchage** (`MA_ROTA`, `MA_PAI_NON_NI`, `TH`…) :
zéro canne, zéro prairie, zéro banane. Le PAD régional sortira proche de 100 % sur toutes les
cultures majeures.

Deux causes probables, toutes deux cohérentes avec l'article :

1. **L'objectif actif est la marge brute pure.** L'article optimise une utilité de
   Markowitz-Freund où Ø freine chaque type d'exploitation. Sans Ø, rien ne retient un cannier
   spécialisé sur la canne. Le dépôt a l'objectif, désactivé par choix documenté.
2. **Eq. 5 n'est pas portée.** Le plafond de main-d'œuvre par exploitation est calé sur le plan
   de culture initial. Le maraîchage est de loin la culture la plus intensive en travail —
   990 à 1 560 h/ha contre 15 h/ha pour la canne mécanisée (Table 1 de l'article). Sans ce
   plafond, aucune ressource ne limite la bascule générale vers le maraîchage.

**Ces métriques évaluent donc un modèle non calibré.** Un PAD proche de 100 % est le
diagnostic attendu, pas un bug du module. C'est précisément la valeur du chantier : donner le
chiffre qui manque pour arbitrer la suite.

## Tests

`tests/test_guadeloupe_calibration.py`, style maison : `Dataset` synthétique, aucun accès à
`data/`.

- correspondance fine → groupe exhaustive sur `CROP_LABELS`, et `KeyError` sur code inconnu ;
- PAD nul quand simulé et observé coïncident ;
- PAD de 100 % quand une culture observée disparaît de la sortie ;
- PAD `NaN` et surface apparue reportée quand une culture absente de l'observé apparaît ;
- PAD par région, sur un jeu à deux régions aux verdicts opposés ;
- univers de parcelles disjoints : parcelle `NC` devenue cultivée, parcelle non affectée ;
- matrice de confusion sur une ferme qui change de type, diagonale et marges vérifiées ;
- part des fermes sous seuil ;
- `thresholds_from_config` : valeurs par défaut de l'article quand la section est absente.

`tests/test_guadeloupe_reporting_report.py` est étendu de la présence des nouveaux fichiers et
du bloc `recap["calibration"]`. `tests/test_guadeloupe_reporting_plots.py` couvre les deux
figures comme les autres. Un test de `zones.py` vérifie la ré-export depuis `comparison.py`.

## Hors périmètre

- La boucle de calibration §2.5 sur les Ø. Les coefficients de la Table 2 sont déjà portés, et
  100 itérations à 30-55 minutes de solve sont hors d'atteinte sans réduction du problème.
- Toute modification du modèle : objectif, contraintes, éligibilité, économie. En particulier
  l'activation de `maximize_risk_adjusted_gross_margin` et le portage d'`Eq_MO_MAX_Expl`
  relèvent d'un chantier suivant, que le diagnostic de celui-ci sert à motiver.
- Tout solve réel. Le chantier se valide par tests unitaires et par
  `scripts/evaluate_calibration.py` sur les runs déjà présents dans `outputs/`.

## Documentation à mettre à jour

- `docs/04-vigilance.md` — entrée « ces métriques évaluent un modèle non calibré », avec les deux
  causes probables et le renvoi à cette spec ; note sur le traitement des `NC` dans la
  reconstruction typologique.
- `TODO.md` — le chantier suivant : activer l'objectif Markowitz et porter `Eq_MO_MAX_Expl`,
  puis relancer l'évaluation pour mesurer le gain.
- `docs/01-utilisation.md` — la commande `scripts/evaluate_calibration.py`.
- `CLAUDE.md` — une ligne sur le nouveau module dans la description de `reporting/`.
