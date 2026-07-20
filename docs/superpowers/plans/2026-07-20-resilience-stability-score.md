# Score de stabilité — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter trois indicateurs d'exposition aux aléas — marge à risque climatique, concentration du revenu, perte sous choc de prix — calculés après le solve, alimentant le recap et le score composite du dashboard.

**Architecture:** Un module pur `resilience.py` produisant des taux par culture, agrégés sur l'allocation par une nouvelle fonction `compute_resilience_totals` dans `reporting/indicators.py`, écrits dans un bloc `resilience` du recap, et exposés au dashboard via un nouveau groupe `_RESILIENCE_INDICATORS`. Aucune fonction n'est parcellaire : tout dépend de la culture seule.

**Tech Stack:** Python 3, pandas, pytest. Venv à `.venv/`. Pas de Pyomo ni de solveur dans ce lot.

**Spec :** `docs/superpowers/specs/2026-07-20-resilience-stability-score-design.md`

## Global Constraints

- **Reporting seul.** Aucune contrainte, aucun objectif, aucune modification du modèle Pyomo. L'allocation ne change pas.
- **Ne jamais lancer `main.py` ni `scripts/run_scenarios.py`** — solves réels, ~30–55 min, réservés à une demande explicite de l'utilisateur en fin de journée.
- **Tests de logique sans `data/`** : configs minuscules montées à la main (cf. `tests/test_guadeloupe_constraints.py`). Aucun test de ce lot ne résout de MILP.
- **`Var_Rdt_Cult` est une fraction de perte de marge, pas une variance ni un coefficient de variation.** Le GAMS l'emploie ainsi (`OPTIMISATION.txt:70`, `MODELE.txt:427`). La perte est **linéaire** en surface : pas de carré, pas de covariance.
- **Le choc de prix ne touche ni les subventions, ni les coûts variables, ni la bagasse.** Seul `prix_cult` est choqué.
- **Défaut du choc : `δ = 0.20`**, sous la clé `resilience.price_shock_delta` de `config.yaml`. Un config sans cette clé doit fonctionner et retomber sur 0.20.
- **Brancher le dashboard aux DEUX endroits.** `INDICATOR_DIRECTION` (`dashboard/comparison.py`) annote le sens ; `_RESILIENCE_INDICATORS` (`dashboard/pages/2_Comparaison.py`) confère l'appartenance au sélecteur. La spec 1 n'avait fait que le premier : ses indicateurs étaient du code mort. Un test de la Task 4 garde ça.
- Commandes pytest : `.venv/Scripts/python -m pytest <chemin> -v`.

---

### Task 1: Module `resilience.py` — les trois fonctions pures

**Files:**
- Create: `case_studies/guadeloupe/resilience.py`
- Test: `tests/test_guadeloupe_resilience.py`

**Interfaces:**
- Consumes: rien (premier task).
- Produces:
  - `DEFAULT_PRICE_SHOCK_DELTA: float` (= 0.20)
  - `compute_climate_margin_at_risk_per_ha_cult(margin_per_ha_cult: pd.Series, var_rdt_cult: pd.Series) -> pd.Series` — euros/ha/an à risque, indexé par culture
  - `compute_price_shock_loss_per_ha_cult(rdt_cult: pd.Series, prix_cult: pd.Series, duree_cycle_cult: pd.Series, delta: float) -> pd.Series` — euros/ha/an perdus, indexé par culture
  - `compute_revenue_concentration_hhi(revenue_by_crop: pd.Series) -> float` — dans [0, 1]

- [ ] **Step 1: Write the failing test**

Créer `tests/test_guadeloupe_resilience.py` :

```python
import pandas as pd
import pytest

from case_studies.guadeloupe import resilience


def test_climate_margin_at_risk_is_margin_times_loss_fraction():
    margin = pd.Series({"SAFE": 1000.0, "RISKY": 1000.0, "ZERO": 500.0})
    var_rdt = pd.Series({"SAFE": 0.1, "RISKY": 0.7, "ZERO": 0.0})

    at_risk = resilience.compute_climate_margin_at_risk_per_ha_cult(margin, var_rdt)

    assert at_risk["SAFE"] == pytest.approx(100.0)
    assert at_risk["RISKY"] == pytest.approx(700.0)


def test_zero_variance_crop_carries_no_climate_risk():
    """Prairies et jachere portent Var_Rdt = 0 dans les vraies donnees."""
    margin = pd.Series({"PRAIRIE": 800.0})
    var_rdt = pd.Series({"PRAIRIE": 0.0})

    at_risk = resilience.compute_climate_margin_at_risk_per_ha_cult(margin, var_rdt)

    assert at_risk["PRAIRIE"] == pytest.approx(0.0)


def test_price_shock_loss_is_delta_times_annualized_market_sales():
    # rdt 50 t/ha, prix 20 EUR/t, cycle 6 mois -> ventes annualisees 50*20/6*12 = 2000.
    rdt = pd.Series({"CROP": 50.0})
    prix = pd.Series({"CROP": 20.0})
    duree = pd.Series({"CROP": 6.0})

    loss = resilience.compute_price_shock_loss_per_ha_cult(rdt, prix, duree, 0.20)

    assert loss["CROP"] == pytest.approx(400.0)  # 20% de 2000


def test_price_shock_of_zero_loses_nothing_and_of_one_loses_all_market_sales():
    rdt = pd.Series({"CROP": 50.0})
    prix = pd.Series({"CROP": 20.0})
    duree = pd.Series({"CROP": 6.0})

    assert resilience.compute_price_shock_loss_per_ha_cult(rdt, prix, duree, 0.0)["CROP"] == 0.0
    assert resilience.compute_price_shock_loss_per_ha_cult(
        rdt, prix, duree, 1.0
    )["CROP"] == pytest.approx(2000.0)


def test_hhi_of_a_monoculture_is_one():
    assert resilience.compute_revenue_concentration_hhi(pd.Series({"A": 1000.0})) == pytest.approx(1.0)


def test_hhi_of_n_equal_crops_is_one_over_n():
    revenue = pd.Series({"A": 250.0, "B": 250.0, "C": 250.0, "D": 250.0})
    assert resilience.compute_revenue_concentration_hhi(revenue) == pytest.approx(0.25)


def test_hhi_ignores_zero_revenue_crops():
    """Une culture a revenu nul ne doit pas diluer l'indice."""
    concentrated = pd.Series({"A": 1000.0})
    padded = pd.Series({"A": 1000.0, "B": 0.0, "C": 0.0})

    assert resilience.compute_revenue_concentration_hhi(
        padded
    ) == pytest.approx(resilience.compute_revenue_concentration_hhi(concentrated))


def test_hhi_of_empty_or_zero_revenue_is_zero_not_a_division_error():
    assert resilience.compute_revenue_concentration_hhi(pd.Series(dtype=float)) == 0.0
    assert resilience.compute_revenue_concentration_hhi(pd.Series({"A": 0.0})) == 0.0


def test_default_price_shock_delta_is_twenty_percent():
    assert resilience.DEFAULT_PRICE_SHOCK_DELTA == 0.20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_resilience.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'case_studies.guadeloupe.resilience'`

- [ ] **Step 3: Write minimal implementation**

Créer `case_studies/guadeloupe/resilience.py` :

```python
"""Exposure of a fixed allocation to climatic and economic shocks.

These indicators measure what is *at stake* if a shock lands after the cropping decisions
are locked in. They do NOT re-optimize, so they are not a measure of adaptive capacity --
see the design spec and VIGILANCE.md. The `price_multipliers` / `yield_multipliers` config
levers do the other thing: they shock the inputs *before* the solve, letting the optimizer
adapt.

Var_Rdt_Cult is a *fractional margin loss*, not a variance and not a coefficient of
variation. GAMS uses it that way in both places it appears: OPTIMISATION.txt:70
(`MB_Ha_Cult_Pond = MB_Ha_Cult - MB_Ha_Cult * Var_Rdt_Cult`) and MODELE.txt:427 (the
Markovitz penalty). The loss is therefore linear in area -- no squaring, no covariance.
"""

import pandas as pd

# Default relative price shock applied to prix_cult. Overridable via
# config.yaml resilience.price_shock_delta.
DEFAULT_PRICE_SHOCK_DELTA = 0.20

# Annualization factor shared with economics.py: per-cycle figures are scaled by
# 12 / Duree_Cycle_Cult (months) to get a per-year figure.
_MONTHS_PER_YEAR = 12


def compute_climate_margin_at_risk_per_ha_cult(
    margin_per_ha_cult: pd.Series, var_rdt_cult: pd.Series
) -> pd.Series:
    """Gross margin at risk (EUR/ha/year) if a bad year hits: margin times the crop's
    fractional yield loss."""
    return margin_per_ha_cult * var_rdt_cult.reindex(margin_per_ha_cult.index)


def compute_price_shock_loss_per_ha_cult(
    rdt_cult: pd.Series,
    prix_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    delta: float,
) -> pd.Series:
    """Margin lost (EUR/ha/year) under a relative price shock `delta` on prix_cult.

    Closed form: subsidies are fixed amounts (not indexed on market prices), variable costs
    scale with yield rather than price, and the bagasse by-product price is left alone -- so
    the whole loss is `delta * annualized market sales`, with no need to re-run economics.py.
    """
    annual_market_sales = rdt_cult * prix_cult / duree_cycle_cult * _MONTHS_PER_YEAR
    return delta * annual_market_sales


def compute_revenue_concentration_hhi(revenue_by_crop: pd.Series) -> float:
    """Herfindahl index of revenue concentration, in [0, 1]. 1 = a single crop earns
    everything; 1/n = n crops earn equal shares. Higher means more fragile to anything
    hitting one crop.

    Computed on revenue rather than gross margin on purpose: margin can be negative for a
    crop (notably on the baseline side, where representative crops are not picked for
    profitability), and shares that do not sum to 1 make the index meaningless. Revenue
    (sales + subsidy) is always non-negative.
    """
    total = float(revenue_by_crop.sum())
    if total <= 0:
        return 0.0
    shares = revenue_by_crop / total
    return float((shares**2).sum())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_resilience.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/resilience.py tests/test_guadeloupe_resilience.py
git commit -m "feat(resilience): marge a risque, choc de prix et concentration du revenu"
```

---

### Task 2: `duree_cycle_cult` dans le pipeline + `compute_resilience_totals`

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py` (une entrée dans le dict `parameters`)
- Modify: `case_studies/guadeloupe/reporting/indicators.py` (nouvelle fonction)
- Modify: `tests/test_guadeloupe_pipeline.py` (un test, ce fichier lit le vrai dataset — convention établie)
- Test: `tests/test_guadeloupe_reporting_resilience.py` (créer)

**Interfaces:**
- Consumes: Task 1 (les trois fonctions de `resilience.py`).
- Produces:
  - `Dataset.parameters["duree_cycle_cult"]` — `pd.Series` indexée par culture, durée de cycle en mois
  - `indicators.compute_resilience_totals(dataset: Dataset, allocation: pd.Series, price_shock_delta: float) -> dict[str, float]` — cinq clés : `climate_margin_at_risk`, `climate_margin_at_risk_ratio`, `revenue_concentration_hhi`, `price_shock_margin_loss`, `price_shock_margin_loss_ratio`

**Contexte.** `duree_cycle_cult` est déjà **lu** par `data_pipeline.py` (il sert à `economics.py`) mais n'est pas exposé dans `Dataset.parameters`. Le choc de prix en a besoin. Les autres paramètres nécessaires y sont déjà : `margin_per_ha_cult`, `rdt_cult`, `prix_cult`, `crop_variance_per_ha`.

**Note de nommage.** Le paramètre `crop_variance_per_ha` porte `Var_Rdt_Cult`. Le nom est trompeur — ce n'est pas une variance mais une fraction de perte. **Ne pas renommer dans ce lot** : il est consommé par l'objectif Markovitz et ses tests de la phase 2. Signaler dans `VIGILANCE.md` en Task 5.

- [ ] **Step 1: Write the failing tests**

Ajouter à la fin de `tests/test_guadeloupe_pipeline.py` (qui construit déjà le vrai dataset via `build_dataset(CONFIG)`) :

```python
def test_build_dataset_registers_duree_cycle_cult():
    dataset = build_dataset(CONFIG)
    duree = dataset.parameters["duree_cycle_cult"]

    assert set(duree.index) == set(dataset.sets["crops"])
    # Une duree de cycle nulle ferait exploser l'annualisation du choc de prix.
    assert (duree > 0).all()
```

Créer `tests/test_guadeloupe_reporting_resilience.py` :

```python
import pandas as pd
import pytest

from core.data.dataset import Dataset
from case_studies.guadeloupe.reporting import indicators


def _dataset() -> Dataset:
    """Deux parcelles, deux cultures. SAFE ne risque rien, RISKY perd 50%."""
    data_parc = pd.DataFrame({"SURF_HA": [2.0, 3.0]}, index=["P1", "P2"])
    parameters = {
        "data_parc": data_parc,
        "margin_per_ha_cult": pd.Series({"SAFE": 100.0, "RISKY": 200.0}),
        "crop_variance_per_ha": pd.Series({"SAFE": 0.0, "RISKY": 0.5}),
        "rdt_cult": pd.Series({"SAFE": 10.0, "RISKY": 20.0}),
        "prix_cult": pd.Series({"SAFE": 6.0, "RISKY": 6.0}),
        "duree_cycle_cult": pd.Series({"SAFE": 12.0, "RISKY": 12.0}),
        "sales_per_ha_cult": pd.Series({"SAFE": 60.0, "RISKY": 120.0}),
        "subsidy_per_ha_cult_annualized": pd.Series({"SAFE": 40.0, "RISKY": 80.0}),
    }
    return Dataset(sets={}, parameters=parameters, scalars={})


def _allocation() -> pd.Series:
    return pd.Series(["SAFE", "RISKY"], index=["P1", "P2"])


def test_climate_margin_at_risk_weights_by_surface():
    totals = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    # P1: 2 ha x 100 EUR x 0.0 = 0. P2: 3 ha x 200 EUR x 0.5 = 300.
    assert totals["climate_margin_at_risk"] == pytest.approx(300.0)


def test_climate_ratio_is_relative_to_total_margin():
    totals = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    # Marge totale: 2 x 100 + 3 x 200 = 800. Ratio 300 / 800.
    assert totals["climate_margin_at_risk_ratio"] == pytest.approx(0.375)


def test_price_shock_loss_scales_with_delta():
    # Ventes marche annualisees: SAFE 10*6/12*12 = 60/ha, RISKY 20*6/12*12 = 120/ha.
    # Surface: 2 x 60 + 3 x 120 = 480. A delta 0.20 -> 96.
    at_20 = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    at_40 = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.40)

    assert at_20["price_shock_margin_loss"] == pytest.approx(96.0)
    assert at_40["price_shock_margin_loss"] == pytest.approx(192.0)
    assert at_20["price_shock_margin_loss_ratio"] == pytest.approx(96.0 / 800.0)


def test_revenue_concentration_uses_revenue_not_margin():
    totals = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    # Revenu = ventes + subvention. P1: 2 x (60+40) = 200. P2: 3 x (120+80) = 600.
    # Total 800, parts 0.25 et 0.75 -> HHI = 0.0625 + 0.5625 = 0.625.
    assert totals["revenue_concentration_hhi"] == pytest.approx(0.625)


def test_empty_allocation_yields_zeros_not_errors():
    totals = indicators.compute_resilience_totals(_dataset(), pd.Series(dtype=object), 0.20)
    for key, value in totals.items():
        assert value == 0.0, f"{key} devrait etre 0 sur une allocation vide"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_resilience.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'compute_resilience_totals'`

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline.py::test_build_dataset_registers_duree_cycle_cult -v`
Expected: FAIL — `KeyError: 'duree_cycle_cult'`

- [ ] **Step 3: Write the implementation**

Dans `case_studies/guadeloupe/data_pipeline.py`, ajouter au dict `parameters`, juste après `"rdt_cult": rdt_cult,` :

```python
        "duree_cycle_cult": duree_cycle_cult,
```

(La variable `duree_cycle_cult` existe déjà plus haut dans la fonction — elle est lue mais n'était pas exposée.)

Dans `case_studies/guadeloupe/reporting/indicators.py`, ajouter l'import en tête :

```python
from case_studies.guadeloupe import resilience
```

Puis ajouter cette fonction après `compute_environmental_totals` :

```python
def compute_resilience_totals(
    dataset: Dataset, allocation: pd.Series, price_shock_delta: float
) -> dict[str, float]:
    """Exposure of one allocation to climatic and economic shocks: gross margin at risk in a
    bad year, revenue concentration, and margin lost under a relative price shock.

    These measure a *fixed* allocation's exposure -- nothing is re-optimized, so this is not
    adaptive capacity. See the design spec and VIGILANCE.md.
    """
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    total_margin = float(compute_gross_margin_by_crop(dataset, allocation).sum())

    at_risk_rate = resilience.compute_climate_margin_at_risk_per_ha_cult(
        dataset.parameters["margin_per_ha_cult"], dataset.parameters["crop_variance_per_ha"]
    )
    shock_rate = resilience.compute_price_shock_loss_per_ha_cult(
        dataset.parameters["rdt_cult"],
        dataset.parameters["prix_cult"],
        dataset.parameters["duree_cycle_cult"],
        price_shock_delta,
    )

    at_risk = float((surface_by_crop * at_risk_rate.reindex(surface_by_crop.index)).sum())
    shock_loss = float((surface_by_crop * shock_rate.reindex(surface_by_crop.index)).sum())
    hhi = resilience.compute_revenue_concentration_hhi(
        compute_total_revenue_by_crop(dataset, allocation)
    )

    def ratio(value: float) -> float:
        return value / total_margin if total_margin else 0.0

    return {
        "climate_margin_at_risk": at_risk,
        "climate_margin_at_risk_ratio": ratio(at_risk),
        "revenue_concentration_hhi": hhi,
        "price_shock_margin_loss": shock_loss,
        "price_shock_margin_loss_ratio": ratio(shock_loss),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_resilience.py tests/test_guadeloupe_resilience.py -v`
Expected: PASS — 14 passed

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline.py -v`
Expected: PASS (33 tests, dont le nouveau)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py case_studies/guadeloupe/reporting/indicators.py tests/test_guadeloupe_reporting_resilience.py tests/test_guadeloupe_pipeline.py
git commit -m "feat(resilience): agregation des indicateurs d'exposition par allocation"
```

---

### Task 3: Config `price_shock_delta` et bloc `resilience` du recap

**Files:**
- Modify: `case_studies/guadeloupe/config.yaml` (nouvelle section)
- Modify: `case_studies/guadeloupe/reporting/report.py` (calcul + passage à `_build_recap`)
- Test: `tests/test_guadeloupe_reporting_report.py` (étendre)

**Interfaces:**
- Consumes: Task 2 (`indicators.compute_resilience_totals`).
- Produces: `recap["resilience"]` = `{"input": {...}, "output": {...}, "delta": {...}}`, même forme que `recap["environment"]`.

**Attention régression.** `report.py` est appelé par des tests dont les `Dataset` sont montés à la main. En spec 1, étendre une fonction partagée a cassé 4 tests préexistants dont les fixtures manquaient les nouveaux paramètres. Ici `compute_resilience_totals` a besoin de `crop_variance_per_ha`, `rdt_cult`, `prix_cult`, `duree_cycle_cult` : les fixtures de `tests/test_guadeloupe_reporting_report.py` et `tests/test_guadeloupe_dashboard_comparison.py` devront probablement être complétées **additivement**.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_reporting_report.py` :

Ce fichier n'a pas de helper d'exécution : ses tests appellent `report.generate_report`
directement, avec le motif reproduit ci-dessous (identique à
`test_generate_report_writes_full_output_folder`, lignes 98-110).

```python
def test_recap_carries_resilience_block_for_both_sides(tmp_path):
    """Le recap expose les indicateurs d'exposition, cote entree comme sortie."""
    import json

    dataset = _tiny_dataset()
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0, "P2": 3.0},
        crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
        eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        config=_CONFIG,
    )
    results = solve_model(model, _CONFIG)
    output_dir = report.generate_report(
        dataset, _CONFIG, model, results, duration=1.23, outputs_root=tmp_path
    )
    recap = json.loads((output_dir / "recap.json").read_text())

    assert "resilience" in recap
    for side in ("input", "output", "delta"):
        assert side in recap["resilience"]
    for key in (
        "climate_margin_at_risk",
        "climate_margin_at_risk_ratio",
        "revenue_concentration_hhi",
        "price_shock_margin_loss",
        "price_shock_margin_loss_ratio",
    ):
        assert key in recap["resilience"]["output"]
```

`_tiny_dataset()`, `_CONFIG`, `build_crop_allocation_model` et `solve_model` sont déjà importés
en tête de ce fichier. `_tiny_dataset()` devra être complété additivement avec
`crop_variance_per_ha`, `rdt_cult`, `prix_cult` et `duree_cycle_cult` pour les cultures `CS` et
`ME` — c'est la régression annoncée plus haut.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_report.py::test_recap_carries_resilience_block_for_both_sides -v`
Expected: FAIL — `KeyError: 'resilience'` ou `AssertionError: assert 'resilience' in recap`

- [ ] **Step 3: Write the implementation**

Dans `case_studies/guadeloupe/config.yaml`, ajouter une section au niveau racine (à côté de `labor:`) :

```yaml
# Exposure indicators (reporting only -- no effect on the allocation). The price shock is
# applied *after* the solve to a fixed allocation, which is NOT what the scenario levers
# economics.price_multipliers / yield_multipliers do: those shock the inputs before the
# solve, so the optimizer adapts to them. Both are useful; they answer different questions.
resilience:
  # Relative shock on prix_cult, e.g. 0.20 = a 20% market price drop. Subsidies, variable
  # costs and the bagasse by-product are deliberately left untouched.
  price_shock_delta: 0.20
```

Dans `case_studies/guadeloupe/reporting/report.py`, à côté du bloc qui calcule `output_env` / `input_env` / `delta_env` :

```python
    price_shock_delta = (config.get("resilience") or {}).get(
        "price_shock_delta", resilience.DEFAULT_PRICE_SHOCK_DELTA
    )
    output_res = indicators.compute_resilience_totals(
        dataset, output_allocation, price_shock_delta
    )
    input_res = indicators.compute_resilience_totals(
        dataset, input_representative, price_shock_delta
    )
    delta_res = {key: output_res[key] - input_res[key] for key in output_res}
```

Ajouter l'import en tête du fichier :

```python
from case_studies.guadeloupe import resilience
```

Puis passer le bloc à `_build_recap`, à côté de `environment=` :

```python
        resilience={"input": input_res, "output": output_res, "delta": delta_res},
```

et ajouter le paramètre `resilience` à la signature de `_build_recap` ainsi qu'au dict qu'elle construit, en suivant exactement la façon dont `environment` y est traité (lire `_build_recap` avant d'éditer).

- [ ] **Step 4: Run tests and the broad regression check**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_report.py -v`
Expected: PASS

Puis, obligatoire, la suite complète hors solve réel et hors dataset réel :
Run: `.venv/Scripts/python -m pytest tests/ --deselect tests/test_main.py --ignore=tests/test_guadeloupe_pipeline.py -q`
Expected: PASS. La baseline avant ce lot est **239 passed**. Toute fixture cassée par les nouveaux paramètres requis doit être complétée **additivement** — ne modifier aucune assertion existante.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/config.yaml case_studies/guadeloupe/reporting/report.py tests/
git commit -m "feat(resilience): bloc resilience du recap et delta de choc configurable"
```

---

### Task 4: Branchement au dashboard — les deux endroits

**Files:**
- Modify: `case_studies/guadeloupe/dashboard/comparison.py` (`INDICATOR_DIRECTION`)
- Modify: `case_studies/guadeloupe/dashboard/pages/2_Comparaison.py` (`_RESILIENCE_INDICATORS`, `_INDICATOR_LABELS`, `_indicator_value`)
- Test: `tests/test_guadeloupe_dashboard_comparison.py` (étendre)

**Interfaces:**
- Consumes: Task 3 (`recap["resilience"][side]`).
- Produces: les cinq indicateurs sélectionnables dans le dashboard et atteignables par `compute_composite_scores`.

**Le piège que ce task existe pour éviter.** `INDICATOR_DIRECTION` ne fait qu'annoter le sens d'un indicateur. C'est l'appartenance à un groupe de `_INDICATOR_LABELS` qui le rend sélectionnable, donc présent dans `raw`, donc pris en compte par `compute_composite_scores`. En spec 1, quatre indicateurs n'ont été ajoutés qu'à `INDICATOR_DIRECTION` : ils étaient **invisibles du picker**, du code mort, et aucun test ne l'a vu parce que les tests du composite appellent la fonction directement avec des frames montées à la main. Le premier test ci-dessous est précisément le garde-fou qui manquait.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_dashboard_comparison.py` :

```python
_RESILIENCE_KEYS = (
    "climate_margin_at_risk",
    "climate_margin_at_risk_ratio",
    "revenue_concentration_hhi",
    "price_shock_margin_loss",
    "price_shock_margin_loss_ratio",
)


def test_resilience_indicators_are_selectable_in_the_dashboard_picker():
    """Garde-fou: etre dans INDICATOR_DIRECTION ne suffit PAS a atteindre le score
    composite -- c'est l'appartenance a _INDICATOR_LABELS qui rend un indicateur
    selectionnable. La spec 1 a livre 4 indicateurs en code mort faute de ce test."""
    import importlib

    page = importlib.import_module(
        "case_studies.guadeloupe.dashboard.pages.2_Comparaison"
    )
    for key in _RESILIENCE_KEYS:
        assert key in page._INDICATOR_LABELS, f"{key} absent du selecteur"


def test_resilience_indicators_have_a_composite_direction():
    from case_studies.guadeloupe.dashboard import comparison

    for key in _RESILIENCE_KEYS:
        assert comparison.INDICATOR_DIRECTION.get(key) == "cost", (
            f"{key} devrait etre 'cost': plus haut = plus fragile"
        )
```

Si le nom de module `2_Comparaison` ne s'importe pas directement (il commence par un chiffre), utiliser `importlib.import_module` comme ci-dessus — c'est pour cela qu'il est écrit ainsi plutôt qu'avec un `import` classique.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_dashboard_comparison.py::test_resilience_indicators_are_selectable_in_the_dashboard_picker -v`
Expected: FAIL — `AssertionError: climate_margin_at_risk absent du selecteur`

- [ ] **Step 3: Write the implementation**

Dans `case_studies/guadeloupe/dashboard/comparison.py`, ajouter à `INDICATOR_DIRECTION` :

```python
    # Exposure indicators: for each, higher = more fragile.
    "climate_margin_at_risk": "cost",
    "climate_margin_at_risk_ratio": "cost",
    "revenue_concentration_hhi": "cost",
    "price_shock_margin_loss": "cost",
    "price_shock_margin_loss_ratio": "cost",
```

Dans `case_studies/guadeloupe/dashboard/pages/2_Comparaison.py`, ajouter le groupe après `_ENV_INDICATORS` :

```python
# Exposure of a fixed allocation to shocks -- nothing is re-optimized, so this is exposure,
# not adaptive capacity. Note: each absolute value and its ratio are near-collinear
# (same numerator), so selecting both roughly doubles that axis's weight in the composite
# score. Same trap that got the water peak-month indicator dropped in spec 1.
_RESILIENCE_INDICATORS = {
    "climate_margin_at_risk": "Marge à risque climatique (€)",
    "climate_margin_at_risk_ratio": "Marge à risque climatique (part)",
    "revenue_concentration_hhi": "Concentration du revenu (HHI)",
    "price_shock_margin_loss": "Perte sous choc de prix (€)",
    "price_shock_margin_loss_ratio": "Perte sous choc de prix (part)",
}
```

Étendre `_INDICATOR_LABELS` :

```python
_INDICATOR_LABELS = {
    **_ECON_INDICATORS, **_ENV_INDICATORS, **_AUTONOMY_INDICATORS,
    **_RESILIENCE_INDICATORS,
    _GINI_KEY: "Gini (revenu/exploit.)",
}
```

Et ajouter la branche de lecture dans `_indicator_value`, juste après la branche `_ENV_INDICATORS` :

```python
    if indicator in _RESILIENCE_INDICATORS:
        return (recap.get("resilience") or {}).get(side, {}).get(indicator)
```

Mettre à jour la docstring de `_indicator_value` pour mentionner le bloc `resilience`. Les runs antérieurs sans ce bloc renvoient `None`, ce qui est le comportement voulu.

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_dashboard_comparison.py -v`
Expected: PASS

Run: `.venv/Scripts/python -m pytest tests/ --deselect tests/test_main.py --ignore=tests/test_guadeloupe_pipeline.py -q`
Expected: PASS, aucune régression.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/dashboard/ tests/test_guadeloupe_dashboard_comparison.py
git commit -m "feat(resilience): exposer les indicateurs d'exposition au score composite"
```

---

### Task 5: Documentation des limites

**Files:**
- Modify: `VIGILANCE.md`
- Modify: `TODO.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Ajouter les limites à `VIGILANCE.md`**

Dans « Points ouverts », en respectant le format du fichier (marqueur de sévérité, date `_2026-07-20._`) :

```markdown
### Majeur — Le score de stabilité mesure l'exposition, pas l'adaptation
Les indicateurs de `resilience.py` (marge à risque, HHI, choc de prix) portent sur une
allocation **figée** : rien n'est ré-optimisé. Ils répondent à « si l'aléa tombe une fois les
assolements décidés, qu'est-ce qui est exposé ? », pas à « de combien l'optimum se dégrade-t-il
sous contrainte choquée ». À ne pas lire comme de la résilience. Une vraie mesure d'adaptation
demanderait de ré-optimiser sous choc — autre projet. À ne pas confondre non plus avec les
leviers `price_multipliers` / `yield_multipliers` de `config.yaml`, qui eux choquent les
entrées **avant** le solve et laissent l'optimiseur s'adapter. _2026-07-20._

### Mineur — `crop_variance_per_ha` porte un nom trompeur
Le paramètre contient `Var_Rdt_Cult`, qui est une **fraction de perte de marge**, pas une
variance ni un coefficient de variation (`OPTIMISATION.txt:70`, `MODELE.txt:427`). Non renommé
parce qu'il est consommé par l'objectif Markovitz et ses tests de la phase 2. Piège classique
pour qui voudrait bâtir un calcul de variance dessus : la perte est **linéaire** en surface,
sans carré ni covariance. _2026-07-20._

### Mineur — `NC` porte `Var_Rdt = 1,0`
« Non cultivé » affecté d'une perte de 100 % est un artefact du tableau source. Sans effet sur
le choc de prix (`Prix_Cult = 0` et `Rdt_Cult = 0`, vérifié), mais sa contribution à la marge à
risque vaut `marge_NC × 1,0`, et sa marge n'est pas mécaniquement nulle (`subventions − coûts`).
À mesurer sur un vrai run : si la contribution est significative, l'exclure explicitement. Le
GAMS maintient d'ailleurs un set dédié `CULT_NON_NC_2017`. _2026-07-20._
```

- [ ] **Step 2: Marquer le lot livré dans `TODO.md`**

Dans la section « Chantier "indicateurs d'impact" », remplacer la ligne 2 par :

```markdown
2. **Score de stabilité / résilience** — **livré le 2026-07-20**. Spec :
   `docs/superpowers/specs/2026-07-20-resilience-stability-score-design.md`.
   Marge à risque climatique, concentration du revenu (HHI), perte sous choc de prix
   (δ configurable). Validation unitaire seulement (aucun solve réel lancé).
```

- [ ] **Step 3: Ajouter une ligne à `CLAUDE.md`**

Dans la section « Architecture », à la suite du paragraphe sur les modules d'indicateurs
environnementaux ajouté par la spec 1 :

```markdown
`resilience.py` ajoute trois indicateurs d'**exposition** (marge à risque climatique via
`Var_Rdt_Cult`, concentration du revenu, perte sous choc de prix), agrégés par
`compute_resilience_totals` et stockés dans `recap["resilience"]`. Attention : exposer un
indicateur au score composite demande **deux** ajouts — `INDICATOR_DIRECTION`
(`dashboard/comparison.py`) pour le sens, et un groupe de `_INDICATOR_LABELS`
(`dashboard/pages/2_Comparaison.py`) pour l'appartenance au sélecteur. Le premier seul ne
branche rien.
```

- [ ] **Step 4: Vérification finale**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_resilience.py tests/test_guadeloupe_reporting_resilience.py tests/test_guadeloupe_dashboard_comparison.py tests/test_guadeloupe_reporting_report.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add VIGILANCE.md TODO.md CLAUDE.md
git commit -m "docs(resilience): consigner les limites du score d'exposition"
```

---

## Vérification finale

Le lot est terminé quand :

1. `.venv/Scripts/python -m pytest tests/ --deselect tests/test_main.py --ignore=tests/test_guadeloupe_pipeline.py -q` passe, sans régression sur la baseline de 239.
2. `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline.py -q` passe.
3. Le test « les indicateurs sont sélectionnables dans le picker » passe — c'est celui qui garantit qu'ils ne sont pas du code mort.

**Ne pas lancer `main.py`.** Les indicateurs sont du post-traitement et ne peuvent pas rendre le modèle infaisable.

**Ordres de grandeur attendus** sur un vrai run, pour repérer une erreur de facteur (marge brute totale de référence : ~325 M€, cf. `.superpowers/sdd/progress.md`) :
- `climate_margin_at_risk_ratio` autour de **0,2–0,4** — c'est la moyenne de `Var_Rdt` pondérée par la marge, et les valeurs de la table vont de 0 à 0,7. Un ratio > 0,7 ou proche de 0 signale une erreur d'alignement d'index.
- `price_shock_margin_loss_ratio` autour de **0,1–0,3** à δ=0,20 : la marge est nette de coûts alors que la perte porte sur les ventes brutes, donc le ratio peut dépasser δ.
- `revenue_concentration_hhi` bien au-dessus de 1/84 ≈ 0,012 : le run de référence ne retient qu'~9 cultures, donc attendre plutôt **0,15–0,5**. Une valeur proche de 1/84 voudrait dire que le revenu est réparti sur toutes les cultures, ce qui contredirait l'allocation observée.

Une vérification sans solve est possible et recommandée avant de conclure, comme l'a fait la revue finale de la spec 1 : `build_dataset(CONFIG)` puis `indicators.decode_baseline_allocation(dataset)` donne une allocation réelle de ~22 200 parcelles sur laquelle appeler `compute_resilience_totals`.
