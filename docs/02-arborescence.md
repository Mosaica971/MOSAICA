# 02 — Arborescence

## Le principe d'organisation

Trois couches, et la frontière entre elles est une règle, pas une habitude :

```
core/            générique     ne parle QUE de parcelles, cultures, exploitations.
                               Aucune mention de la Guadeloupe, du RPG, des ILE/REGION, du GFA.
case_studies/    concret       les données, les règles agronomiques, le reporting d'un territoire.
apps/            lecture       ce qui ne fait que LIRE des runs finis. Ne participe pas au solve.
```

**Sens des dépendances** : `case_studies/` importe `core/`, jamais l'inverse. `apps/` importe les
deux ; **rien sous `core/` ou `case_studies/` ne peut importer `apps/`**.

Pourquoi cette discipline : c'est elle qui rend le modèle portable sur un autre territoire (voir
[05](05-nouveau-cas-etude.md)) et c'est elle qui garde le vocabulaire GAMS là où il ancre la
parité.

---

## Racine

```
main.py                     un solve complet. C'est le point d'entrée.
pyproject.toml              dépendances, config pytest (pythonpath = ["."])
CLAUDE.md                   instructions pour l'agent Claude Code
TODO.md                     ce qui reste à implémenter (le "quoi ensuite")
docs/                       cette documentation
context/                    sources externes : GAMS d'origine, article, rapport technique
core/  case_studies/  apps/  scripts/  tests/
data/                       ⚠ NON VERSIONNÉ — tables d'entrée + SIG. À copier à part.
outputs/                    ⚠ NON VERSIONNÉ — un dossier par run
.golden/                    ⚠ NON VERSIONNÉ — sommes de contrôle de non-régression
.mosaica_solve_history.json ⚠ NON VERSIONNÉ — durées des solves passés (local à la machine)
```

---

## `core/` — le solveur générique

### `core/config.py` (~700 l.) — le fichier central

Tout ce qui transforme du YAML en configuration exécutable.

| Fonction | Rôle |
|---|---|
| `load_config` | lire un YAML |
| `resolve_enabled` | filtrer une liste de config sur `enable: true` et résoudre les noms dans un registre → `(fonction, args)` |
| `load_batch_spec` | charger un spec de batch en suivant ses `include:` et en résolvant `{group: …}` |
| `expand_group_refs` / `resolve_crop_groups` | le catalogue de groupes de cultures |
| `compose_runs` | transformer un spec en liste de runs (plan / liste plate / catalogues croisés) |
| `expand_runs` | déplier un `matrix:` en produit cartésien |
| `merge_run_specs` | composer politique ⊕ forçage ⊕ balayage sans perdre l'un des deux |
| `apply_overrides` | appliquer les overrides d'un run sur la config de référence |
| `order_sweep_points` | réordonner un balayage pour que le chaînage de warm start soit valide |
| `scale_territorial_bounds` | mettre les seuils absolus à l'échelle d'un `zone_filter` |

### `core/case_study.py` — quel cas d'étude

Résout par **nom** les trois fonctions qu'un cas d'étude doit exposer. C'est ce qui fait que le
nom « guadeloupe » vit dans un drapeau et non dans une douzaine d'imports.

### `core/model/` — construire un modèle (et rien d'autre)

| Fichier | Rôle |
|---|---|
| `registry.py` | `@register_constraint(nom)` / `@register_objective(nom)` remplissent deux dictionnaires |
| `builder.py` | crée le `ConcreteModel`, la variable binaire `Y[parcelle, culture]` sur les paires éligibles, puis exécute chaque builder activé. **Exige exactement un objectif actif.** |
| `model_inputs.py` | `ModelInputs` : le seul objet que voient les builders. Trois champs obligatoires, tout le reste optionnel avec un défaut vide |
| `constraints.py` (~400 l.) | les contraintes génériques : bornes territoriales, par zone, par exploitation, parts de cultures, inertie |
| `objectives.py` | marge brute, et marge ajustée au risque (Markowitz) |

### `core/solve/` — résoudre un modèle

| Fichier | Rôle |
|---|---|
| `solver.py` | `SolverFactory('appsi_highs')`, options depuis la config |
| `progress.py` | affiche une fourchette de durée avant, la durée réelle après ; `SolveHistory` |
| `timing.py` | chronomètre données / construction / solve séparément |
| `warm_start.py` | applique une allocation passée **et l'audite** contre les contraintes |
| `shadow_prices.py` | coût marginal de chaque contrainte nommée (duaux de la relaxation LP) |

⚠ **`progress.py` ne doit jamais lancer le solve en arrière-plan.** `appsi_highs` charge le
modèle dans `capture_output(capture_fd=True)`, qui redirige les descripteurs stdout/stderr du
processus ; toute I/O concurrente depuis un autre thread corrompt cet état et casse **tout vrai
run**. Spec : `superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md`.

### `core/data/`

| Fichier | Rôle |
|---|---|
| `readers.py` | lecture des `.set` et `.txt` GAMS |
| `dataset.py` | le conteneur `Dataset(sets, parameters, scalars)` |
| `eligibility.py` | masque booléen parcelle × culture : bornes numériques ∩ règles catégorielles |
| `zone_filter.py` | restreindre à un sous-territoire |
| `shapefile.py` | lecteur ESRI en **Python pur** — pas de GDAL, pas de geopandas |

### `core/reporting/`

| Fichier | Rôle |
|---|---|
| `run_folder.py` | crée `outputs/output_N/` (ou un dossier nommé), relit une allocation |
| `robustness.py` | pire cas (Wald), rétention, CV, regret max (Savage), viabilité (Starr) sur une grille |

---

## `case_studies/guadeloupe/`

Organisé par **rôle**, pas par type de donnée.

```
config.yaml                  ⭐ pilote tout : contraintes, objectifs, éligibilité, données
crop_groups.yaml             groupes de cultures nommés, partagés par les fichiers de scénarios
scenarios.yaml               batch de scénarios (liste plate)
plan.yaml                    ⭐ le plan prospectif — ce qui est réellement lancé
scenarios_politiques.yaml    catalogue : ce qu'une puissance publique décide (P1..P10)
scenarios_forcages.yaml      catalogue : ce que le climat et les marchés imposent (F0..F11)
scenarios_pareto.yaml        catalogue : les balayages ε-contrainte
scenarios_calibration.yaml   régénère les deux runs de calibration de référence
references.yaml              les trois runs de référence, avec la justification de chaque choix
```

### `pipeline/data_pipeline.py` (~420 l.)

Lit les tables, applique le `zone_filter`, calcule l'économie, la typologie et le masque
d'éligibilité. Retourne un `Dataset`. **C'est le seul endroit qui touche `data/`.**

### `domain/` — la science, une culture à la fois

| Module | Contenu |
|---|---|
| `economics.py` | marge, ventes, subventions, coûts, heures de travail par ha et par culture |
| `environment.py` | azote, phosphore, potasse, GES, IFT |
| `water.py` | besoin en eau |
| `soil_carbon.py` | carbone organique — **seul indicateur qui dépend aussi de la parcelle** (via `TYPE_SOL`) |
| `resilience.py` | exposition : marge à risque, concentration du revenu, perte sous choc |
| `agroecology.py` | MAE (définition *sourcée* de l'agroécologie) et itinéraires bio, rapportés **séparément** |
| `rpest.py` | arbre flou de Tixier — **seul indicateur qui dépend du couple (parcelle, culture)** |
| `farm_typology.py` | groupe de culture de base → `TYPE_EXPL` → aversion au risque `AVERS` |
| `crop_families.py` | replie les 84 cultures fines sur les 12 groupes RPG observés |
| `crop_labels.py` | noms lisibles, portés de `DESCRIPTION_SETS.txt` |
| `zones.py` | normalisation des codes île/région |
| `geometry.py` | raccorde le RPG parcellaire aux identifiants synthétiques `P1..Pn` |
| `itk.py` | itinéraires techniques |

### `model/`

- `constraints.py` — les contraintes spécifiques à la Guadeloupe (GFA, jachère banane, …).
- `model.py` — assemble `ModelInputs` depuis le `Dataset` et appelle
  `build_crop_allocation_model`. **Importer le module, jamais le paquet** : `__init__.py` est
  vide, donc `import case_studies.guadeloupe.model` n'enregistre aucune contrainte.

### `reporting/`

- `indicators.py` (~600 l.) — applique les taux par culture à l'allocation résolue.
- `calibration.py` (~350 l.) — note le run contre l'observé 2017 (PAD, matrice de confusion).
- `report.py` (~460 l.) — écrit le dossier de run.
- `plots.py` — les PNG.

---

## `apps/dashboard/` — le viewer Streamlit

Vit **hors de `case_studies/`** parce qu'il ne participe pas au solve : il ouvre des dossiers
`outputs/` et ne construit jamais ni dataset, ni modèle, ni solveur.

```
app.py                    page Synthèse (accueil)
pages/1_Detail_du_run.py  2_Comparaison.py  3_Calibration.py
pages/4_Prospective.py    5_Carte.py        6_Pareto.py
loaders.py                lecture des dossiers de run
comparison.py             (~680 l.) tables de faits, directions d'indicateurs, score composite
synthesis.py              les alertes propres à un run
config_diff.py            ce que deux runs ont DEMANDÉ de différent
allocation_diff.py        ce que ça a DÉPLACÉ sur le terrain
prospective.py            la grille politique × forçage
pareto.py                 fronts, domination, coût marginal
maps.py                   rendu cartographique
references.py             chargement des runs de référence
```

---

## `scripts/`

**Génériques** (marchent sur n'importe quel cas d'étude, via `--case-study`) :

| Script | Rôle |
|---|---|
| `run_scenarios.py` | batch de scénarios |
| `profile_solver.py` | chronométrage par phase sur une sous-zone |
| `display_datasets.py` | inspecter le dataset |
| `golden_snapshot.py` | non-régression numérique (~681 sommes de contrôle) |
| `repair_allocation.py` | réparer une allocation pour en faire une graine de warm start |
| `_common.py` | chemins et formatage partagés — **sans aucun import projet**, pour que `--help` reste instantané |

**Spécifiques à la Guadeloupe** (ils importent `domain/` ou `reporting/`, par nature) :
`build_reference_state.py`, `compare_to_reference.py`, `evaluate_calibration.py`,
`pad_all_scales.py`, `check_references.py`, `check_scenario_feasibility.py`.

---

## `tests/`

~120 fichiers, **sans données par choix** : ils construisent des configs minuscules à la main
(voir `tests/test_guadeloupe_constraints.py` pour le style). Une poignée construit le vrai
dataset et résout — ce sont eux les 29 minutes de la suite complète.

Ce que ce choix implique : **les tests ne gardent pas le solve**. `golden_snapshot.py` couvre le
pipeline et les indicateurs jusqu'à l'allocation, `check_references.py` couvre les résultats des
runs de référence. Rien d'autre ne surveille la résolution.

---

## `data/` (non versionné)

```
data/sets/      les .set GAMS (CULT_2017.set, REG_PARC_2017.set, …)
data/tables/    les .txt (Data_Parc, Data_OTK, Data_Cult, Data_Sol, indice_H/…)
data/gis/       les couches SIG, dont 01_RPG 2017/ (parcellaire réel)
```

⚠ Il n'y a **aucune coordonnée** dans `data/tables/` : le reporting spatial s'agrège par
`ILE`/`REGION`/`COMMUNE`. La géométrie ne vient que de `data/gis/`, raccordée par une jointure
reconstruite (voir [04](04-vigilance.md#carte)).

---

## `context/` (sources externes)

```
context/gams/                            le GAMS d'origine — SOURCE DE VÉRITÉ pour la parité
context/Chopin et al 2015 pour Hal.pdf   l'article de référence
context/Rapport technique … .docx        dictionnaire des variables (non versionné)
```

Dans `context/gams/` : `MODELE.txt` (les équations), `OPTIMISATION.txt` (les calculs),
`ENTREES.txt` (les dérivations), `SETS.txt` (les ensembles), `DESCRIPTION_SETS.txt` (les
libellés). **En cas de doute sur une contrainte ou un coefficient, c'est là qu'on tranche.**

---

## `docs/`

```
README.md              index
01-utilisation.md … 05-nouveau-cas-etude.md
gams_port_inventory.md         état du portage, équation par équation
superpowers/specs/             une spec par chantier — le POURQUOI de chaque décision
archives/journal-vigilance.md  le log complet des enquêtes
```
