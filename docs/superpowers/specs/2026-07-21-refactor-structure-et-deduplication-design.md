# Refactor transverse : arborescence, déduplication, abstraction de `core/`

_2026-07-21 — chantier de qualité de code, sans changement de comportement._

## Contexte

Le code a grossi par ajouts successifs de fonctionnalités (parité GAMS phase 1 et 2, batch de
scénarios, indicateurs d'impact) sans passe de consolidation. Trois symptômes :

1. **De la duplication mécanique** s'est accumulée, en particulier dans `indicators.py` (575
   lignes, le plus gros fichier du dépôt) et entre les modules `domain/` qui partagent tous la
   même structure de calcul ITK.
2. **`core/` laisse fuir du vocabulaire guadeloupéen** (`data_parc`, `island`, `gfa`), ce qui
   contredit sa raison d'être : être la couche réutilisable par un autre case study.
3. **`case_studies/guadeloupe/` a 11 modules à plat**, sans regroupement par rôle.

Le périmètre est **exclusivement qualitatif** : aucune formule, aucune contrainte, aucun
indicateur ne change de valeur. C'est la propriété centrale à garantir, et la section
« Vérification » ci-dessous décrit comment on la prouve.

## Non-goals

- **Aucun renommage dans `case_studies/guadeloupe/`.** Les noms `rdt_cult`, `prix_cult`,
  `MB_Ha_Cult`, `Matrice_OTK_Cult` sont la clé de traçabilité vers `context/gams/`,
  que `CLAUDE.md` désigne comme source de vérité pour la parité. Les abstraire couperait le lien
  entre une ligne de Python et la ligne de `OPTIMISATION.txt` qu'elle porte — précisément ce qui
  permet aujourd'hui de vérifier une formule. Et ça n'aide pas à généraliser : un futur case
  study réutilisera `core/`, pas les noms de colonnes guadeloupéennes.
- **Aucun changement des clés de `recap.json`**, ni des noms de fonctions publiques
  d'`indicators.py`, ni des noms de contraintes/objectifs du registre. Le dashboard lit les
  `outputs/output_N/` **passés** : renommer une clé casserait la comparaison avec l'historique.
- **Aucun solve réel n'est lancé** pour ce chantier (voir « Vérification »).
- Pas de nouvelle fonctionnalité, pas de correction de bug de fond, pas de traitement des points
  ouverts de `docs/04-vigilance.md`.

## Vérification : le snapshot déterministe

C'est la partie la plus importante de la spec. Un refactor transverse ne vaut que par la preuve
qu'il n'a rien changé, et la suite pytest seule ne suffit pas : elle est majoritairement
unitaire sur données synthétiques (choix délibéré, cf. `CLAUDE.md`), donc une dérive sur les
vraies données pourrait passer.

### Pourquoi pas un run de référence avec solve

L'idée naturelle — figer un run complet avant/après et comparer les `recap.json` — est à la fois
**trop lente et non fiable** :

- le solve réel coûte 30 à 55 min avec une variance ×2,1 (`docs/04-vigilance.md`) ;
- surtout, il n'est **pas déterministe au sens qui nous intéresse** : sur un MILP dégénéré, deux
  optima de valeur identique peuvent être retournés indifféremment. Un écart d'allocation entre
  deux runs ne prouverait rien, et masquerait les vrais écarts.

### Ce qu'on vérifie à la place

Le refactor ne touche **ni le solveur, ni la formulation mathématique**. Ce qu'il faut prouver
se réduit donc à : les *entrées* du solveur et les *sorties* du reporting sont inchangées. Ça se
mesure sans jamais résoudre le MILP.

Mesures relevées sur le vrai jeu de données pendant le cadrage :

| Étage | Contenu | Coût |
|---|---|---|
| **G1** | `build_dataset` complet (33 paramètres, 5 sets, 1 271 780 paires éligibles) **+** tous les indicateurs sur les 22 197 parcelles réelles de la baseline | **7 s** _(mesuré)_ |
| **G2** | `build_model` sur zone réduite → nb variables/contraintes + coefficients d'objectif | ~10 s _(estimé ; 188 s mesurés sur le territoire complet)_ |
| **G3** | Suite pytest complète | ~29 min _(documenté dans `CLAUDE.md`)_ |

G1 est **exhaustif sur les vraies données** et **parfaitement déterministe** (aucun MILP), pour
250× moins cher qu'un run avec solve. Il couvre `data_pipeline`, `economics`, `environment`,
`water`, `soil_carbon`, `resilience`, `farm_typology`, `eligibility`, `indicators` et la table
de faits.

L'allocation utilisée par G1 est celle de `decode_baseline_representative_allocation` : une
allocation **réelle sur données réelles**, obtenue sans solve. Le fait qu'elle ne soit pas
l'optimum est sans importance — on compare deux versions du code sur la *même* allocation.

Le build complet du modèle coûte 188 s (mesuré), trop lent pour boucler dessus : G2 le fait sur
un `zone_filter` réduit, avec `territory_production_bound` désactivé (les quotas territoriaux ne
s'appliquent pas à un sous-ensemble — `docs/04-vigilance.md`, et `profile_solver.disable_territory_bounds`
fait déjà exactement ça).

### Outillage

`scripts/golden_snapshot.py` (nouveau, ~60 lignes) :

- sans argument : écrit `.golden/snapshot.json`, un dict de sommes de contrôle numériques
  (totaux et hachages par paramètre, tous les dicts d'indicateurs, la table de faits agrégée) ;
- `--check` : recalcule et compare au fichier de référence, sortie non nulle et diff lisible à
  la moindre dérive.

**Le snapshot lui-même n'est pas commité** — il est dérivé de `data/`, qui est gitignoré et
reste local. `.golden/` est ajouté à `.gitignore`, au même titre que `outputs/` et
`.mosaica_solve_history.json`. La référence est donc régénérée depuis `master` au début du
chantier et vit le temps du chantier.

Le *script*, lui, reste dans le dépôt : c'est un filet de sécurité réutilisable pour tout travail
futur touchant le pipeline ou les indicateurs, et il est utilisable par quiconque dispose des
données en local.

### Cadence

G1 après **chaque** modification. G2 après les lots touchant `core/model`. G3 en fin de chaque
lot, avant le commit.

## Les quatre lots

Un commit par lot, sur la branche `refactor/structure-et-deduplication`.

### Lot 1 — Réorganisation de `case_studies/guadeloupe/`

Déplacements purs (`git mv`, contenu inchangé, donc renommages détectés à 100 % et
`git log --follow` préservé), plus la mise à jour des imports (~40 fichiers, tests compris) :

```
case_studies/guadeloupe/
├── config.yaml, scenarios.yaml
├── pipeline/    data_pipeline.py
├── domain/      economics.py, environment.py, water.py, soil_carbon.py,
│                resilience.py, farm_typology.py, crop_labels.py
├── model/       model.py, constraints.py
├── reporting/   indicators.py, plots.py, report.py      (inchangé)
└── dashboard/   app.py, comparison.py, loaders.py, pages/   (inchangé)
```

Fait **en premier** pour que tous les lots suivants travaillent aux chemins définitifs.

Point d'attention : `data_pipeline.py` calcule ses chemins de données par
`Path(__file__).resolve().parent.parent.parent`. Descendre d'un niveau casse `DATA_DIR` —
à corriger dans le même commit. Idem pour `CONFIG_PATH`. Les imports « pour l'effet de bord
d'enregistrement » (`from case_studies.guadeloupe import constraints as _constraints`) doivent
suivre le déplacement, faute de quoi le registre se vide et la config lève un `KeyError` — c'est
le mode d'échec le plus probable de ce lot, et il est couvert par G2.

### Lot 2 — Fusion du code dupliqué

**`reporting/indicators.py` (≈ 575 → 420 lignes).** Trois motifs y sont copiés-collés :

| Motif | Occurrences | Remplacement |
|---|---|---|
| `parameters["data_parc"]["SURF_HA"].reindex(allocation.index)` | 13 | `_plot_surface(dataset, allocation)` |
| `surface_by_crop * rate.reindex(surface_by_crop.index)` | 7 | `_by_crop(dataset, allocation, param_name)` |
| broadcast d'un taux par culture vers l'index parcelle | 4 | `_per_plot_rate(dataset, allocation, param_name)` |

Les sept fonctions `compute_{production_tonnes,sales,subsidy,gross_margin,azote,ges,ift}_by_crop`
sont strictement identiques au nom du paramètre près et deviennent des one-liners.
`compute_surface_by_region_and_key` et `compute_surface_by_island_and_key` sont le même code à la
colonne près et fusionnent en une fonction paramétrée par la dimension — les deux noms publics
sont conservés comme fines enveloppes, puisque le reporting les appelle.

**`domain/`.** Le bloc « opérations ITK amorties (`AMORTI=1`, étalées sur `Duree_Plant_Cult`) vs
one-off, puis annualisation par `/ Duree_Cycle_Cult * 12` » existe en **trois exemplaires** :
`_otk_annual_rate_per_ha_cult` dans `environment.py`, et recopié à la main dans
`compute_variable_cost_per_ha_cult` et `compute_labor_hours_per_ha_cult` d'`economics.py`. Un seul
helper partagé, dans `domain/itk.py`, remplace les trois. C'est la fusion la plus utile du lot :
ce bloc porte une règle de parité GAMS non triviale qu'on ne veut pas voir diverger entre copies.

**`core/model/builder.py`.** `build_crop_allocation_model` prend 11 arguments qui redupliquent
champ pour champ le dataclass `ModelInputs`, suivis de 6 lignes de `x = {} if x is None else x`.
Signature ramenée à `build_crop_allocation_model(inputs: ModelInputs, config)` ; les valeurs par
défaut vivent déjà dans les `field(default_factory=dict)` du dataclass.

**`scripts/`.** `CONFIG_PATH` et le bootstrap `sys.path` (commit `8f62032`) sont triplés :
ils remontent dans `scripts/_common.py`.

### Lot 3 — Abstraction de `core/`

| Avant | Après | Motif |
|---|---|---|
| `data_parc` (21 occ. dans `core/data/eligibility.py`) | `plot_attributes` | « parcelle » est du vocabulaire de données guadeloupéen ; `core` raisonne sur des *plots* |
| règle `island_and_soil_forbidden` | `attribute_and_soil_forbidden`, colonne paramétrée | un autre territoire n'a pas d'îles |
| `ModelInputs.farm_gfa_surface_ha` | `farm_restricted_surface_ha` | le GFA est un dispositif franco-français ; le concept générique est « sous-surface soumise à quota » |

Les noms de règles apparaissent dans `config.yaml` : le YAML est mis à jour dans le même commit,
sinon `resolve_enabled` lève un `KeyError` au premier build. `cs_gfa_minimum_share` reste tel
quel — c'est une contrainte *case study*, pas du `core`, et son nom est un point de repère GAMS.

### Lot 4 — Commentaires

Uniformisation en anglais (les docs projet — `docs/04-vigilance.md`, `TODO.md`, `docs/01-utilisation.md` —
restent en français), docstrings verbeuses resserrées de 8-10 lignes à 3-4, suppression des
commentaires qui paraphrasent le code.

**Conservées intégralement** : toutes les ancres de parité (`OPTIMISATION.txt:118-127`,
`MODELE.txt:305-307`, …) et toutes les mises en garde méthodologiques. Ce sont les commentaires
qui portent l'information non déductible du code — les raccourcir serait le seul vrai risque de
ce lot. Le critère de tri est simple : un commentaire qui explique *ce que fait* le code part ;
un commentaire qui explique *pourquoi* il le fait ainsi, ou d'où vient un coefficient, reste.

## Risques

| Risque | Parade |
|---|---|
| Un import d'enregistrement du registre perdu au lot 1 → registre vide, `KeyError` en config | G2 construit un vrai modèle depuis la config : échoue immédiatement |
| Une dérive numérique silencieuse dans la fusion des helpers | G1 sur les vraies données après chaque modification |
| `DATA_DIR` cassé par le changement de profondeur des chemins | G1 échoue au premier appel (`build_dataset`) |
| Un commentaire de parité perdu au lot 4 | Le lot 4 est un commit séparé, relisible seul ; critère de tri explicite ci-dessus |
| Perte de l'historique git sur les fichiers déplacés | `git mv` à contenu inchangé, lot 1 isolé |

## Ce qui reste après

`TODO.md` et `docs/04-vigilance.md` ne changent pas de contenu de fond ; `CLAUDE.md` est mis à jour au
lot 1 (arborescence) et au lot 3 (vocabulaire de `core/`), puisqu'il documente les deux.
