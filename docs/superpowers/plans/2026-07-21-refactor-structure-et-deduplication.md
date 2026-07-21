# Refactor transverse : arborescence, déduplication, abstraction de `core/` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolider le code (fusion des duplications, abstraction de `core/`, arborescence par rôle, commentaires resserrés) sans changer **aucune** valeur produite par le modèle ou le reporting.

**Architecture :** Quatre lots séquentiels sur la branche `refactor/structure-et-deduplication`, un commit par lot. La garantie d'invariance repose sur `scripts/golden_snapshot.py` (tâche 1) : un instantané déterministe du dataset complet et de tous les indicateurs sur les vraies données, sans solve MILP, à rejouer après chaque modification.

**Tech Stack :** Python 3.x, pandas, Pyomo, pytest. Venv à `.venv/`.

Spec : `docs/superpowers/specs/2026-07-21-refactor-structure-et-deduplication-design.md`

## Global Constraints

- **Aucun changement de valeur.** G1 (`golden_snapshot.py --check`) doit rester vert après chaque modification. Toute dérive numérique est un échec, pas un ajustement.
- **Aucun solve MILP n'est lancé** pendant tout le chantier. Ni `main.py`, ni `run_scenarios.py`.
- **Ne pas renommer** dans `case_studies/guadeloupe/` : `rdt_cult`, `prix_cult`, `MB_Ha_Cult`, `Matrice_OTK_Cult` etc. sont les ancres de parité GAMS.
- **Ne pas renommer** les clés de `recap.json`, les fonctions publiques d'`indicators.py`, ni les noms de contraintes/objectifs du registre.
- Commentaires et docstrings **en anglais** ; docs projet (`VIGILANCE.md`, `TODO.md`, `PRISE_EN_MAIN.md`) **en français**.
- Conserver **intégralement** les ancres de parité (`OPTIMISATION.txt:118-127`, `MODELE.txt:305-307`, …) et les mises en garde méthodologiques.
- Python : `.venv/Scripts/python`. Tests : `.venv/Scripts/python -m pytest`.

---

## File Structure

**Créés :**
- `scripts/golden_snapshot.py` — outil de vérification d'invariance (reste après le chantier)
- `scripts/_common.py` — `CONFIG_PATH`, `ROOT`, bootstrap `sys.path` partagés par les scripts
- `case_studies/guadeloupe/domain/itk.py` — helper ITK partagé (lot 2)
- `case_studies/guadeloupe/{pipeline,domain,model}/__init__.py`

**Déplacés (lot 1, contenu inchangé) :**
- `data_pipeline.py` → `pipeline/data_pipeline.py`
- `economics.py`, `environment.py`, `water.py`, `soil_carbon.py`, `resilience.py`, `farm_typology.py`, `crop_labels.py` → `domain/`
- `model.py`, `constraints.py` → `model/`

**Modifiés en profondeur :** `reporting/indicators.py` (lot 2), `domain/economics.py` + `domain/environment.py` (lot 2), `core/model/builder.py` (lot 2), `core/data/eligibility.py` + `core/model/model_inputs.py` + `config.yaml` (lot 3).

---

## Task 1 : Outil golden_snapshot

**Files:**
- Create: `scripts/golden_snapshot.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `scripts/golden_snapshot.py`, CLI `--write` / `--check`, référence dans `.golden/snapshot.json`.

- [ ] **Step 1 : Ajouter `.golden/` au `.gitignore`**

Le snapshot est dérivé de `data/` (gitignoré) : il ne doit pas entrer dans l'historique.

- [ ] **Step 2 : Écrire `scripts/golden_snapshot.py`**

Le script construit le dataset complet, décode l'allocation baseline représentative (aucun solve), calcule tous les blocs d'indicateurs, et sérialise des sommes de contrôle numériques arrondies à 6 décimales.

Couverture attendue : chaque `pd.Series`/`DataFrame` de `dataset.parameters` (somme, min, max, nb d'éléments non nuls), la taille de chaque set, `eligible_pairs` (cardinalité + hash de la liste triée), puis `compute_economic_totals`, `compute_environmental_totals`, `compute_resilience_totals`, `compute_food_autonomy_totals`, et `compute_facts_table` (somme par colonne numérique + nb de lignes).

- [ ] **Step 3 : Générer la référence depuis l'état actuel**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --write`
Expected: écrit `.golden/snapshot.json`, affiche le nombre d'entrées, termine en ~7 s.

- [ ] **Step 4 : Vérifier que `--check` est vert et détecte réellement une dérive**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check`
Expected: `OK` et code de sortie 0.

Puis test négatif obligatoire — modifier temporairement une constante (p. ex. `DEFAULT_PRICE_SHOCK_DELTA` 0.20 → 0.21), relancer `--check`, vérifier code de sortie **non nul** et diff lisible, puis annuler la modification et re-vérifier que c'est vert. **Un golden qui ne sait pas échouer ne protège rien** — ne pas sauter cette étape.

- [ ] **Step 5 : Commit**

```bash
git add scripts/golden_snapshot.py .gitignore
git commit -m "test(refactor): snapshot deterministe pour garantir l'invariance"
```

---

## Task 2 : Lot 1 — Réorganisation de `case_studies/guadeloupe/`

**Files:**
- Move: 10 modules vers `pipeline/`, `domain/`, `model/`
- Create: 3 × `__init__.py`
- Modify: tous les importeurs (voir liste ci-dessous), `CLAUDE.md`

**Interfaces:**
- Consumes: `scripts/golden_snapshot.py` (Task 1)
- Produces: nouveaux chemins d'import `case_studies.guadeloupe.{pipeline.data_pipeline, domain.*, model.model, model.constraints}`

- [ ] **Step 1 : `git mv` des 10 modules + création des `__init__.py`**

```bash
mkdir -p case_studies/guadeloupe/{pipeline,domain,model}
git mv case_studies/guadeloupe/data_pipeline.py case_studies/guadeloupe/pipeline/
git mv case_studies/guadeloupe/{economics,environment,water,soil_carbon,resilience,farm_typology,crop_labels}.py case_studies/guadeloupe/domain/
git mv case_studies/guadeloupe/{model,constraints}.py case_studies/guadeloupe/model/
touch case_studies/guadeloupe/{pipeline,domain,model}/__init__.py
```

Attention : `model.py` va dans un paquet `model/` → le module devient `case_studies.guadeloupe.model.model`.

- [ ] **Step 2 : Corriger les chemins calculés dans `pipeline/data_pipeline.py`**

Le module descend d'un niveau. `DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"` devient `.parents[3] / "data"`, et `CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"` devient `.parents[1] / "config.yaml"` (le YAML **ne bouge pas**, il reste à la racine de `guadeloupe/`).

C'est le piège n°1 du lot : sans ça, `build_dataset` lève un `FileNotFoundError`.

- [ ] **Step 3 : Mettre à jour tous les imports**

Fichiers concernés (relevé exhaustif) : `main.py` ; `scripts/{run_scenarios,profile_solver,display_datasets}.py` ; `case_studies/guadeloupe/pipeline/data_pipeline.py` ; `case_studies/guadeloupe/model/model.py` ; `case_studies/guadeloupe/reporting/{indicators,plots,report}.py` ; `case_studies/guadeloupe/dashboard/comparison.py` ; `case_studies/guadeloupe/dashboard/pages/2_Comparaison.py` ; et les tests `test_{crop_labels,economics,farm_typology,guadeloupe_config,guadeloupe_constraints,guadeloupe_environment,guadeloupe_model,guadeloupe_pipeline,guadeloupe_resilience,guadeloupe_soil_carbon,guadeloupe_water,zone_filter,scenario_overrides,profile_solver,display_datasets}.py`.

Piège n°2, **le plus dangereux du lot** : l'import pour effet de bord dans `model/model.py`,
`from case_studies.guadeloupe import constraints as _guadeloupe_constraints  # noqa: F401`,
devient `from case_studies.guadeloupe.model import constraints as _guadeloupe_constraints  # noqa: F401`. S'il est perdu, `CONSTRAINT_REGISTRY` ne contient plus les contraintes du case study et `resolve_enabled` lève un `KeyError` au premier build. Même chose dans `tests/test_guadeloupe_constraints.py`.

- [ ] **Step 4 : Vérifier G1**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check`
Expected: `OK`, code 0. Prouve que le pipeline et les indicateurs sont intacts.

- [ ] **Step 5 : Vérifier G2 — le registre est bien peuplé**

Run: `.venv/Scripts/python -c "from core.config import load_config; from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset, CONFIG_PATH; from case_studies.guadeloupe.model.model import build_model; cfg=load_config(CONFIG_PATH); cfg['zone_filter']={'include':{'islands':[2]}}; cfg['constraints']=[c for c in cfg['constraints'] if c['name']!='territory_production_bound']; ds=build_dataset(cfg); m=build_model(ds,cfg); import pyomo.environ as pyo; print('vars', sum(1 for _ in m.Y), 'constraints', sum(len(c) for c in m.component_objects(pyo.Constraint)))"`
Expected: des compteurs non nuls, aucune exception. Un `KeyError` ici = import d'enregistrement perdu (Step 3).

- [ ] **Step 6 : Suite pytest complète**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe (~29 min).

- [ ] **Step 7 : Mettre à jour `CLAUDE.md`**

Section « Architecture » : refléter la nouvelle arborescence et les nouveaux chemins d'import (notamment `case_studies.guadeloupe.model.model` et l'import d'enregistrement des contraintes).

- [ ] **Step 8 : Commit**

```bash
git add -A
git commit -m "refactor(guadeloupe): organiser les modules par role en sous-dossiers"
```

---

## Task 3 : Lot 2a — Fusion des helpers d'`indicators.py`

**Files:**
- Modify: `case_studies/guadeloupe/reporting/indicators.py`
- Test: `tests/test_guadeloupe_reporting_indicators.py` (ne doit pas changer)

**Interfaces:**
- Produces: helpers privés `_plot_surface(dataset, allocation) -> pd.Series`, `_by_crop(dataset, allocation, param_name) -> pd.Series`, `_per_plot_rate(dataset, allocation, param_name) -> pd.Series`, `_surface_by_dimension_and_key(dataset, allocation, column, name) -> pd.DataFrame`.

- [ ] **Step 1 : Introduire les trois helpers privés**

```python
def _plot_surface(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Surface (ha) of each allocated plot, aligned on the allocation index."""
    return dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)


def _by_crop(dataset: Dataset, allocation: pd.Series, param_name: str) -> pd.Series:
    """Allocated surface times a per-ha, crop-indexed rate, totalled by crop."""
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    rate = dataset.parameters[param_name]
    return surface_by_crop * rate.reindex(surface_by_crop.index)


def _per_plot_rate(dataset: Dataset, allocation: pd.Series, param_name: str) -> pd.Series:
    """Broadcast a crop-indexed per-ha rate onto the plot index of an allocation."""
    rate = dataset.parameters[param_name]
    return pd.Series(rate.reindex(allocation.to_numpy()).to_numpy(), index=allocation.index)
```

- [ ] **Step 2 : Réécrire les 7 `compute_*_by_crop` en one-liners**

`compute_production_tonnes_by_crop` → `_by_crop(dataset, allocation, "rdt_cult")` ; `compute_sales_by_crop` → `"sales_per_ha_cult"` ; `compute_subsidy_by_crop` → `"subsidy_per_ha_cult_annualized"` ; `compute_gross_margin_by_crop` → `"margin_per_ha_cult"` ; `compute_azote_by_crop` → `"azote_per_ha_cult"` ; `compute_ges_by_crop` → `"ges_per_ha_cult"` ; `compute_ift_by_crop` → `"ift_per_ha_cult"`. **Docstrings conservées** (elles portent des précisions non triviales, notamment celle de `compute_gross_margin_by_crop` sur le travail non valorisé).

- [ ] **Step 3 : Remplacer les 13 occurrences de surface et les 4 broadcasts**

Substituer `_plot_surface(dataset, allocation)` et `_per_plot_rate(...)` partout. Ne pas toucher `compute_water_need_m3_by_plot` / `compute_soil_carbon_*` sur le fond : le carbone dépend de la parcelle (`TYPE_SOL`) et ne peut pas passer par un taux par culture — c'est documenté dans `CLAUDE.md`, garder ce commentaire.

- [ ] **Step 4 : Fusionner les deux pivots région/île**

```python
def _surface_by_dimension_and_key(
    dataset: Dataset, allocation: pd.Series, dimension: pd.Series, name: str
) -> pd.DataFrame:
    frame = pd.DataFrame({
        name: dimension.reindex(allocation.index),
        "crop": allocation,
        "surface": _plot_surface(dataset, allocation),
    })
    return frame.pivot_table(
        index=name, columns="crop", values="surface", aggfunc="sum", fill_value=0.0
    )
```

`compute_surface_by_region_and_key` et `compute_surface_by_island_and_key` restent des fonctions publiques (le reporting les appelle) et deviennent des enveloppes d'une ligne.

- [ ] **Step 5 : G1 + tests ciblés**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check && .venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_indicators.py tests/test_guadeloupe_reporting_resilience.py tests/test_guadeloupe_reporting_water_carbon.py tests/test_guadeloupe_reporting_report.py -q`
Expected: `OK` puis tous les tests passent. Les fichiers de test ne doivent **pas** avoir été modifiés — les noms publics sont inchangés.

---

## Task 4 : Lot 2b — Helper ITK partagé et signature du builder

**Files:**
- Create: `case_studies/guadeloupe/domain/itk.py`
- Modify: `case_studies/guadeloupe/domain/economics.py`, `case_studies/guadeloupe/domain/environment.py`, `core/model/builder.py`, `case_studies/guadeloupe/model/model.py`, `scripts/_common.py` (create), `scripts/{run_scenarios,profile_solver,display_datasets}.py`
- Test: `tests/test_economics.py`, `tests/test_guadeloupe_environment.py`, `tests/test_model_builder.py`

**Interfaces:**
- Produces: `itk.annual_rate_per_ha_cult(matrice_otk_cult, per_application, duree_plant_cult, duree_cycle_cult, amortized) -> pd.Series` ; `build_crop_allocation_model(inputs: ModelInputs, config: dict) -> pyo.ConcreteModel`

- [ ] **Step 1 : Extraire le helper ITK dans `domain/itk.py`**

Corps identique à l'actuel `_otk_annual_rate_per_ha_cult` d'`environment.py` (déplacement, pas réécriture) :

```python
def annual_rate_per_ha_cult(
    matrice_otk_cult: pd.DataFrame,
    per_application: pd.Series,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    amortized: pd.Series,
) -> pd.Series:
    """Annual per-ha rate summed over a crop's technical operations: amortized ops
    (AMORTI=1) spread over Duree_Plant_Cult, one-off ops charged upfront, then
    / Duree_Cycle_Cult * 12. `amortized` and `per_application` are OTK-indexed
    (matrice rows); the durees are crop-indexed (columns)."""
    otk = matrice_otk_cult.multiply(per_application, axis=0)
    otk_amortized = otk.mul(amortized.astype(float), axis=0).div(duree_plant_cult, axis=1)
    otk_upfront = otk.mul((~amortized).astype(float), axis=0)
    return (otk_upfront + otk_amortized).sum(axis=0) / duree_cycle_cult * 12
```

- [ ] **Step 2 : Câbler les trois appelants**

`environment.py` importe le helper et supprime sa copie privée. Dans `economics.py`, `compute_variable_cost_per_ha_cult` remplace son bloc OTK par `itk.annual_rate_per_ha_cult(matrice_otk_cult, data_otk["DOSE"] * data_otk["PRIX_UNIT"], duree_plant_cult, duree_cycle_cult, data_otk["AMORTI"] == 1)` puis ajoute `+ (cout_recolte_cult + cout_transp_cult) * rdt_cult` ; `compute_labor_hours_per_ha_cult` fait de même avec `data_otk["DOSE"] * data_otk["MO_EXPL"]` et sans terme de récolte/transport. Conserver les ancres `OPTIMISATION.GMS lines 11-19` et `ENTREES.txt:463-466`.

- [ ] **Step 3 : G1 après le lot ITK**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check`
Expected: `OK`. C'est le contrôle décisif : ce helper porte des coûts et de l'azote, toute divergence se verrait ici.

- [ ] **Step 4 : Simplifier `build_crop_allocation_model`**

Signature ramenée à `(inputs: ModelInputs, config: dict[str, Any])`. Supprimer les 6 lignes de coalescing `None` (les `field(default_factory=dict)` de `ModelInputs` s'en chargent déjà). `plots_to_crops`, `model.PAIRS`, `model.PLOTS`, `model.FARMS`, `model.Y` se construisent depuis `inputs`. Mettre à jour l'appelant `case_studies/guadeloupe/model/model.py`, qui construit désormais le `ModelInputs` lui-même.

- [ ] **Step 5 : Adapter `tests/test_model_builder.py`**

C'est le seul fichier de test à modifier dans ce lot : les appels passent d'arguments nommés à un `ModelInputs(...)`. Ne changer **que** la forme de l'appel, aucune assertion.

- [ ] **Step 6 : Factoriser `scripts/_common.py`**

Y remonter `ROOT`, `CONFIG_PATH` et le bootstrap `sys.path` (commit `8f62032`), aujourd'hui triplés. Le bootstrap doit rester **avant** tout import projet dans chaque script — donc `import scripts._common` ne suffit pas s'il est lui-même importé via le paquet ; garder dans chaque script les deux lignes minimales de `sys.path`, et ne mutualiser que `ROOT`/`CONFIG_PATH`/`OUTPUTS_ROOT`.

- [ ] **Step 7 : G2 + suite complète**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tout passe. Puis relancer la commande G2 de la Task 2 Step 5 (adaptée à la nouvelle signature).

- [ ] **Step 8 : Commit du lot 2**

```bash
git add -A
git commit -m "refactor: fusionner les helpers dupliques (indicateurs, ITK, builder, scripts)"
```

---

## Task 5 : Lot 3 — Abstraction de `core/`

**Files:**
- Modify: `core/data/eligibility.py`, `core/model/model_inputs.py`, `core/model/builder.py`, `core/model/constraints.py`, `case_studies/guadeloupe/config.yaml`, `case_studies/guadeloupe/pipeline/data_pipeline.py`, `case_studies/guadeloupe/model/{model,constraints}.py`, `CLAUDE.md`
- Test: `tests/test_eligibility.py`, `tests/test_model_builder.py`, `tests/test_guadeloupe_constraints.py`

- [ ] **Step 1 : `data_parc` → `plot_attributes` dans `core/data/eligibility.py`**

21 occurrences, toutes des paramètres de fonction et des accès locaux. C'est un renommage **interne à `core/`** : la clé `dataset.parameters["data_parc"]` côté guadeloupe **ne change pas**, seul le nom du paramètre reçu change. Mettre à jour `tests/test_eligibility.py` en conséquence.

- [ ] **Step 2 : Généraliser la règle `island_and_soil_forbidden`**

Renommer en `attribute_and_soil_forbidden` et remplacer les paramètres `island_column` / `forbidden_island` par `attribute_column` / `forbidden_value`. Mettre à jour l'entrée correspondante de `categorical_rules` dans `config.yaml` (nom de la règle **et** noms des clés d'arguments) — sinon `resolve_enabled` lève un `KeyError` au premier build.

- [ ] **Step 3 : `ModelInputs.farm_gfa_surface_ha` → `farm_restricted_surface_ha`**

Répercuter dans `core/model/builder.py`, `core/model/constraints.py`, `case_studies/guadeloupe/model/constraints.py` (la contrainte `cs_gfa_minimum_share` **garde son nom** : c'est une contrainte case-study et un repère GAMS) et `case_studies/guadeloupe/model/model.py`.

- [ ] **Step 4 : G1 + G2 + suite complète**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check && .venv/Scripts/python -m pytest -q`
Expected: `OK` puis tout passe. G1 couvre l'éligibilité (1 271 780 paires) : une règle mal recâblée changerait ce compte.

- [ ] **Step 5 : Mettre à jour `CLAUDE.md` (vocabulaire de `core/`) et commit**

```bash
git add -A
git commit -m "refactor(core): abstraire le vocabulaire case-study de la couche generique"
```

---

## Task 6 : Lot 4 — Commentaires

**Files:**
- Modify: tous les modules de `core/`, `case_studies/guadeloupe/`, `scripts/`

- [ ] **Step 1 : Passe fichier par fichier**

Critère de tri, à appliquer littéralement : un commentaire qui explique **ce que fait** le code part ; un commentaire qui explique **pourquoi** il le fait ainsi, ou **d'où vient** un coefficient, reste. Les docstrings de 8-10 lignes descendent à 3-4 en gardant la substance. Les commentaires français passent en anglais.

Ne jamais supprimer : les références `OPTIMISATION.txt:NNN` / `MODELE.txt:NNN` / `ENTREES.txt:NNN`, les renvois à `VIGILANCE.md`, les avertissements sur les pièges (« trivial Boolean » de `territory_production_bound`, conflit `capture_fd` de `progress.py`, dépendance parcelle du carbone).

- [ ] **Step 2 : Vérifier qu'aucune ancre n'a été perdue**

Run: `git diff --stat && git diff | grep -c "^-.*\(OPTIMISATION\|MODELE\|ENTREES\|SETS\|DECLAR_OPT\)\.txt"`
Expected: le compte de lignes supprimées contenant une ancre GAMS doit être **égal** au compte de lignes ajoutées les contenant (elles peuvent être reformulées, pas supprimées). Vérifier manuellement tout écart.

- [ ] **Step 3 : G1 + suite complète**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check && .venv/Scripts/python -m pytest -q`
Expected: `OK` puis tout passe. (Un lot de commentaires ne peut rien casser en théorie ; en pratique une docstring mal fermée casse l'import.)

- [ ] **Step 4 : Commit**

```bash
git add -A
git commit -m "docs: resserrer et uniformiser les commentaires en anglais"
```

---

## Task 7 : Clôture

- [ ] **Step 1 : Diff de synthèse et rapport**

Run: `git diff master --stat | tail -5`

- [ ] **Step 2 : Consigner dans `TODO.md`**

Une ligne dans la section adéquate : chantier de refactor livré le 2026-07-21, avec le renvoi vers la spec, et la mention que la validation est un snapshot déterministe sans solve — **le premier `main.py` / `run_scenarios.py` réel reste à faire** et le confirmera de bout en bout.

- [ ] **Step 3 : Proposer le merge**

Ne pas merger sans accord explicite. Présenter le bilan (lignes supprimées, fichiers déplacés, état des vérifications) et laisser l'utilisateur trancher.
