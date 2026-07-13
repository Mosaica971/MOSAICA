# Output Persistence & Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every solve, persist a numbered `outputs/output_N/` folder with a
recap (constraints/objective/timing), the input/output allocation tables, and PNG
charts of key indicators, computed via a new `core.reporting` (generic) +
`case_studies.guadeloupe.reporting` (domain-specific) module pair.

**Architecture:** A generic `core/reporting/run_folder.py` handles output-folder
numbering. All Guadeloupe-specific indicator math and rendering lives in a new
`case_studies/guadeloupe/reporting/` package (mirrors the existing placement of
`economics.py`/`farm_typology.py`), because indicator computation depends on
Guadeloupe-specific column names (`SURF_HA`, `ILE`, `REGION`, `cult_2017`) and
`farm_typology.compute_base_crop_group`. `report.py` orchestrates: decode both
allocations, compute indicators, render PNGs, write the recap + CSVs.

**Tech Stack:** Python 3.10+, pandas, pyomo, matplotlib (new dependency), pyyaml
(already a dependency), pytest.

## Global Constraints

- `requires-python = ">=3.10"` (pyproject.toml) — no syntax newer than 3.10.
- New dependency: `matplotlib>=3.8`, added to `[project.dependencies]`.
- Follow existing test convention: flat `tests/` directory, `test_<module>.py`
  naming, `tmp_path` fixture for anything touching the filesystem — never the
  real `outputs/`/`.mosaica_solve_history.json` paths in a test.
- No inline comments beyond what's already established in touched files
  (e.g. `economics.py`'s GAMS-line-reference docstrings) — names should carry
  the meaning.
- **Known, accepted limitation (see `VIGILANCE.md` and the design doc):**
  economic indicators (production/subsidy/revenue) are computed at full
  fine-crop resolution for the **output** allocation only. The **input**
  (baseline `cult_2017`) allocation only resolves to 12 RPG groups
  (`farm_typology.compute_base_crop_group`), so it only gets
  surface/plot-count/diversity indicators. Deltas are limited to
  resolution-independent aggregates (total surface, active plot count, farm
  count). Do not attempt a per-crop input/output delta in this plan.

---

## Task 1: Split `compute_gross_product_per_ha_cult` into a sales-only component

**Files:**
- Modify: `case_studies/guadeloupe/economics.py`
- Test: `tests/test_economics.py`

**Interfaces:**
- Produces: `compute_sales_per_ha_cult(rdt_cult: pd.Series, prix_cult: pd.Series, bagasse_cult: pd.Series, duree_cycle_cult: pd.Series) -> pd.Series`
  — used by Task 2 (`data_pipeline.py`) and indirectly by
  `case_studies/guadeloupe/reporting/indicators.py` (Task 6+) via the
  `sales_per_ha_cult` dataset parameter.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_economics.py` (after the existing
`test_compute_gross_product_per_ha_cult_annualizes_price_and_subsidy_income`
test, keep that one unchanged):

```python
def test_compute_sales_per_ha_cult_excludes_subsidy():
    from case_studies.guadeloupe.economics import compute_sales_per_ha_cult

    result = compute_sales_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )

    # 10*(700+50) / 24 * 12 = 3750.0
    assert result["C1"] == pytest.approx(3750.0)


def test_sales_plus_annualized_subsidy_equals_gross_product():
    from case_studies.guadeloupe.economics import (
        compute_gross_product_per_ha_cult,
        compute_sales_per_ha_cult,
    )

    sales = compute_sales_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )
    subsidy_annualized = pd.Series({"C1": 230.0}) / pd.Series({"C1": 24.0}) * 12
    gross_product = compute_gross_product_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        subsidy_per_ha_cult=pd.Series({"C1": 230.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )

    assert (sales + subsidy_annualized)["C1"] == pytest.approx(gross_product["C1"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_economics.py -v`
Expected: the two new tests FAIL with `ImportError: cannot import name 'compute_sales_per_ha_cult'`.

- [ ] **Step 3: Implement `compute_sales_per_ha_cult` and refactor `compute_gross_product_per_ha_cult`**

In `case_studies/guadeloupe/economics.py`, replace the existing
`compute_gross_product_per_ha_cult` function with:

```python
def compute_sales_per_ha_cult(
    rdt_cult: pd.Series,
    prix_cult: pd.Series,
    bagasse_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """Sales-only component of PB_Ha_Cult, annualized the same way (excludes subsidy)."""
    return rdt_cult * (prix_cult + bagasse_cult) / duree_cycle_cult * 12


def compute_gross_product_per_ha_cult(
    rdt_cult: pd.Series,
    prix_cult: pd.Series,
    bagasse_cult: pd.Series,
    subsidy_per_ha_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """PB_Ha_Cult: gross product per ha, annualized (OPTIMISATION.GMS lines 36-38)."""
    sales = compute_sales_per_ha_cult(rdt_cult, prix_cult, bagasse_cult, duree_cycle_cult)
    return sales + subsidy_per_ha_cult / duree_cycle_cult * 12
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_economics.py -v`
Expected: all tests PASS, including the pre-existing
`test_compute_gross_product_per_ha_cult_annualizes_price_and_subsidy_income`
(still expects `3865.0`, unchanged).

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/economics.py tests/test_economics.py
git commit -m "Split sales out of compute_gross_product_per_ha_cult"
```

---

## Task 2: Expose `sales_per_ha_cult` and annualized subsidy on the Dataset

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py`
- Test: `tests/test_guadeloupe_pipeline.py`

**Interfaces:**
- Consumes: `compute_sales_per_ha_cult` from Task 1.
- Produces: `dataset.parameters["sales_per_ha_cult"]: pd.Series` (indexed by
  crop) and `dataset.parameters["subsidy_per_ha_cult_annualized"]: pd.Series`
  (indexed by crop) — consumed by `indicators.py` starting Task 6.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_guadeloupe_pipeline.py`:

```python
def test_build_dataset_exposes_sales_and_annualized_subsidy_per_ha_cult():
    dataset = build_dataset(CONFIG)

    sales = dataset.parameters["sales_per_ha_cult"]
    subsidy_annualized = dataset.parameters["subsidy_per_ha_cult_annualized"]
    margin = dataset.parameters["margin_per_ha_cult"]

    # AG: PB=rdt*prix=20*700=14000, no subsidies/bagasse (see the existing
    # gross-margin test's comment) -- sales alone should equal the full gross
    # product, and reconciling with the already-verified margin gives the
    # same CV~8001.31 hand-verified variable cost.
    assert sales["AG"] == pytest.approx(14000.0, abs=0.01)
    assert subsidy_annualized["AG"] == pytest.approx(0.0, abs=0.01)
    assert (sales["AG"] + subsidy_annualized["AG"] - margin["AG"]) == pytest.approx(8001.31, abs=1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_guadeloupe_pipeline.py::test_build_dataset_exposes_sales_and_annualized_subsidy_per_ha_cult -v`
Expected: FAIL with `KeyError: 'sales_per_ha_cult'`.

- [ ] **Step 3: Compute and expose the two new parameters**

In `case_studies/guadeloupe/data_pipeline.py`, update the import block:

```python
from case_studies.guadeloupe.economics import (
    compute_gross_margin_per_ha_cult,
    compute_gross_product_per_ha_cult,
    compute_sales_per_ha_cult,
    compute_subsidy_per_ha_cult,
    compute_variable_cost_per_ha_cult,
)
```

Immediately after the existing `subsidy_per_ha_cult = compute_subsidy_per_ha_cult(...)`
call (right before `gross_product_per_ha_cult = compute_gross_product_per_ha_cult(...)`),
add:

```python
    sales_per_ha_cult = compute_sales_per_ha_cult(
        rdt_cult=rdt_cult,
        prix_cult=prix_cult,
        bagasse_cult=bagasse_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    subsidy_per_ha_cult_annualized = subsidy_per_ha_cult / duree_cycle_cult * 12
```

And add both to the `parameters` dict (next to the existing
`"margin_per_ha_cult": margin_per_ha_cult,` line):

```python
        "sales_per_ha_cult": sales_per_ha_cult,
        "subsidy_per_ha_cult_annualized": subsidy_per_ha_cult_annualized,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_guadeloupe_pipeline.py -v`
Expected: all tests PASS (this rebuilds the real dataset, so it's slower —
matches the existing tests in this file).

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py tests/test_guadeloupe_pipeline.py
git commit -m "Expose sales_per_ha_cult and annualized subsidy on the Dataset"
```

---

## Task 3: `solve_with_progress` returns `(results, duration)`

**Files:**
- Modify: `core/model/progress.py`
- Modify: `main.py:14-17` (unpack the new return value; report wiring comes in Task 11)
- Test: `tests/test_model_progress.py`

**Interfaces:**
- Produces: `solve_with_progress(...) -> tuple[Any, float]` (was `-> Any`) —
  consumed by `main.py` (this task) and `report.py`'s `duration` parameter
  (Task 10/11).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_model_progress.py` (near the other `solve_with_progress` tests):

```python
def test_solve_with_progress_returns_results_and_duration(tmp_path):
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=_SOLVE_CONFIG,
    )
    history = SolveHistory(path=tmp_path / "history.json")

    results, duration = solve_with_progress(
        model, _SOLVE_CONFIG, case_study="test_case", history=history
    )

    assert results is not None
    assert duration >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model_progress.py::test_solve_with_progress_returns_results_and_duration -v`
Expected: FAIL with `TypeError: cannot unpack non-sequence ...Results object` (or similar) since `solve_with_progress` currently returns a single value.

- [ ] **Step 3: Change the return type**

In `core/model/progress.py`, change the last two lines of `solve_with_progress`:

```python
    history.record(case_study, problem_size, duration)
    return results, duration
```

(was `return results`.)

- [ ] **Step 4: Update `main.py`'s call site**

In `main.py`, change:

```python
    solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)
```

to:

```python
    results, duration = solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)
```

(`duration` is unused until Task 11 — that's fine, it's about to be consumed.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_model_progress.py tests/test_main.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add core/model/progress.py main.py tests/test_model_progress.py
git commit -m "solve_with_progress returns (results, duration)"
```

---

## Task 4: Generic output-folder numbering (`core/reporting/run_folder.py`)

**Files:**
- Create: `core/reporting/__init__.py` (empty)
- Create: `core/reporting/run_folder.py`
- Test: `tests/test_run_folder.py`

**Interfaces:**
- Produces: `create_output_folder(outputs_root: Path = Path("outputs")) -> Path`
  — consumed by `report.py` (Task 10).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_run_folder.py`:

```python
from core.reporting.run_folder import create_output_folder


def test_create_output_folder_starts_at_1_for_empty_directory(tmp_path):
    result = create_output_folder(tmp_path)

    assert result == tmp_path / "output_1"
    assert result.is_dir()


def test_create_output_folder_increments_past_existing_runs(tmp_path):
    (tmp_path / "output_1").mkdir()
    (tmp_path / "output_3").mkdir()

    result = create_output_folder(tmp_path)

    assert result == tmp_path / "output_4"


def test_create_output_folder_ignores_non_matching_entries(tmp_path):
    (tmp_path / "output_1").mkdir()
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "output_backup").mkdir()

    result = create_output_folder(tmp_path)

    assert result == tmp_path / "output_2"


def test_create_output_folder_creates_missing_root(tmp_path):
    root = tmp_path / "outputs"

    result = create_output_folder(root)

    assert result == root / "output_1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_run_folder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.reporting'`.

- [ ] **Step 3: Implement**

Create `core/reporting/__init__.py` (empty file).

Create `core/reporting/run_folder.py`:

```python
from pathlib import Path

_PREFIX = "output_"


def create_output_folder(outputs_root: Path = Path("outputs")) -> Path:
    outputs_root.mkdir(parents=True, exist_ok=True)
    existing = [
        int(child.name[len(_PREFIX):])
        for child in outputs_root.iterdir()
        if child.is_dir()
        and child.name.startswith(_PREFIX)
        and child.name[len(_PREFIX):].isdigit()
    ]
    next_index = max(existing, default=0) + 1
    output_dir = outputs_root / f"{_PREFIX}{next_index}"
    output_dir.mkdir()
    return output_dir
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_run_folder.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add core/reporting/__init__.py core/reporting/run_folder.py tests/test_run_folder.py
git commit -m "Add generic output-folder numbering (core.reporting.run_folder)"
```

---

## Task 5: Indicator foundations — allocation decoding, surface, plot counts, aggregates

**Files:**
- Create: `case_studies/guadeloupe/reporting/__init__.py` (empty)
- Create: `case_studies/guadeloupe/reporting/indicators.py`
- Test: `tests/test_guadeloupe_reporting_indicators.py`

**Interfaces:**
- Consumes: `case_studies.guadeloupe.farm_typology.compute_base_crop_group`
  (existing), `core.data.dataset.Dataset` (existing).
- Produces: `decode_output_allocation(model) -> pd.Series`,
  `decode_baseline_allocation(dataset) -> pd.Series`,
  `plot_to_farm(dataset) -> pd.Series`, `plot_to_region(dataset) -> pd.Series`,
  `plot_to_island(dataset) -> pd.Series`,
  `compute_surface_by_key(dataset, allocation) -> pd.Series`,
  `compute_plot_count_by_key(allocation) -> pd.Series`,
  `compute_aggregate_summary(dataset, allocation) -> dict` — all consumed by
  later tasks in this file and by `report.py` (Task 10).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_guadeloupe_reporting_indicators.py`:

```python
import pandas as pd
import pytest

from case_studies.guadeloupe.reporting import indicators
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model

_MINIMAL_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def _small_dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0, 1.0, 4.0, 3.0, 1.0],
            "REGION": ["R1", "R1", "R2", "R2", "R1", "R2"],
            "ILE": [1, 1, 2, 2, 1, 2],
            "cult_2016": [6, 6, 13, 14, 6, 13],
            "cult_2017": [6, 6, 13, 14, 6, 13],
        },
        index=["P1", "P2", "P3", "P4", "P5", "P6"],
    )
    expl_parc = pd.DataFrame(
        {
            "farm": ["E1", "E1", "E2", "E2", "E3", "E3"],
            "plot": ["P1", "P2", "P3", "P4", "P5", "P6"],
        }
    )
    rdt_cult = pd.Series({"CS": 80.0, "ME": 20.0})
    sales_per_ha_cult = pd.Series({"CS": 3000.0, "ME": 5000.0})
    subsidy_per_ha_cult_annualized = pd.Series({"CS": 500.0, "ME": 200.0})
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "rdt_cult": rdt_cult,
            "sales_per_ha_cult": sales_per_ha_cult,
            "subsidy_per_ha_cult_annualized": subsidy_per_ha_cult_annualized,
        },
        scalars={},
    )


def test_decode_baseline_allocation_maps_rpg_codes_to_groups_and_drops_non_cultivated():
    dataset = _small_dataset()

    allocation = indicators.decode_baseline_allocation(dataset)

    assert allocation.to_dict() == {
        "P1": "CS", "P2": "CS", "P3": "ME", "P5": "CS", "P6": "ME",
    }


def test_decode_output_allocation_reads_selected_pairs_from_solved_model():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"C1": 10.0, "C2": 20.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2"), ("P2", "C1")],
        config=_MINIMAL_CONFIG,
    )
    model.Y["P1", "C1"].set_value(0)
    model.Y["P1", "C2"].set_value(1)
    model.Y["P2", "C1"].set_value(1)

    allocation = indicators.decode_output_allocation(model)

    assert allocation.to_dict() == {"P1": "C2", "P2": "C1"}


def test_compute_surface_by_key_sums_surface_per_crop():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_surface_by_key(dataset, allocation)

    assert result["CS"] == pytest.approx(5.0)
    assert result["ME"] == pytest.approx(1.0)


def test_compute_plot_count_by_key_counts_plots_per_crop():
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "CS", "P6": "ME"})

    result = indicators.compute_plot_count_by_key(allocation)

    assert result["CS"] == 3
    assert result["ME"] == 2


def test_compute_aggregate_summary_totals_surface_plots_and_farms():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)

    summary = indicators.compute_aggregate_summary(dataset, allocation)

    assert summary == {"total_surface_ha": 10.0, "active_plot_count": 5, "farm_count": 3}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'case_studies.guadeloupe.reporting'`.

- [ ] **Step 3: Implement**

Create `case_studies/guadeloupe/reporting/__init__.py` (empty file).

Create `case_studies/guadeloupe/reporting/indicators.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from case_studies.guadeloupe.farm_typology import compute_base_crop_group
from core.data.dataset import Dataset

_NON_CULTIVATED_GROUP = "NC"


def decode_output_allocation(model: pyo.ConcreteModel) -> pd.Series:
    """plot -> fine crop, read from the solved model's Y variable."""
    allocated = {
        plot: crop
        for plot, crop in model.PAIRS
        if pyo.value(model.Y[plot, crop]) > 0.5
    }
    return pd.Series(allocated, name="crop")


def decode_baseline_allocation(dataset: Dataset) -> pd.Series:
    """plot -> RPG base crop group (12 groups), from the observed 2017 land use."""
    data_parc = dataset.parameters["data_parc"]
    groups = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])
    return groups[groups != _NON_CULTIVATED_GROUP].dropna()


def plot_to_farm(dataset: Dataset) -> pd.Series:
    expl_parc = dataset.parameters["expl_parc"]
    return expl_parc.set_index("plot")["farm"]


def plot_to_region(dataset: Dataset) -> pd.Series:
    return dataset.parameters["data_parc"]["REGION"]


def plot_to_island(dataset: Dataset) -> pd.Series:
    return dataset.parameters["data_parc"]["ILE"]


def compute_surface_by_key(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    return surface.groupby(allocation).sum()


def compute_plot_count_by_key(allocation: pd.Series) -> pd.Series:
    return allocation.value_counts()


def compute_aggregate_summary(dataset: Dataset, allocation: pd.Series) -> dict:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    farms = plot_to_farm(dataset).reindex(allocation.index)
    return {
        "total_surface_ha": float(surface.sum()),
        "active_plot_count": int(len(allocation)),
        "farm_count": int(farms.nunique()),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/__init__.py case_studies/guadeloupe/reporting/indicators.py tests/test_guadeloupe_reporting_indicators.py
git commit -m "Add allocation decoding and surface/plot-count indicators"
```

---

## Task 6: Per-crop economic indicators (output resolution)

**Files:**
- Modify: `case_studies/guadeloupe/reporting/indicators.py` (append)
- Test: `tests/test_guadeloupe_reporting_indicators.py` (append)

**Interfaces:**
- Consumes: `compute_surface_by_key` from Task 5;
  `dataset.parameters["rdt_cult"]`, `["sales_per_ha_cult"]`,
  `["subsidy_per_ha_cult_annualized"]` from Task 2 / existing pipeline.
- Produces: `compute_production_tonnes_by_crop`, `compute_sales_by_crop`,
  `compute_subsidy_by_crop`, `compute_total_revenue_by_crop`,
  `compute_subsidy_per_tonne_by_crop`, `compute_subsidy_per_euro_sold_by_crop`
  (all `(dataset, allocation) -> pd.Series`) — consumed by `report.py` (Task 10)
  and `plots.py` (Task 9).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_guadeloupe_reporting_indicators.py`:

```python
def test_compute_production_tonnes_by_crop_multiplies_surface_by_yield():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_production_tonnes_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(400.0)
    assert result["ME"] == pytest.approx(20.0)


def test_compute_sales_by_crop_multiplies_surface_by_sales_rate():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_sales_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(15000.0)
    assert result["ME"] == pytest.approx(5000.0)


def test_compute_subsidy_by_crop_multiplies_surface_by_subsidy_rate():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_subsidy_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(2500.0)
    assert result["ME"] == pytest.approx(200.0)


def test_compute_total_revenue_by_crop_sums_sales_and_subsidy():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_total_revenue_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(17500.0)
    assert result["ME"] == pytest.approx(5200.0)


def test_compute_subsidy_per_tonne_by_crop_divides_subsidy_by_production():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_subsidy_per_tonne_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(6.25)
    assert result["ME"] == pytest.approx(10.0)


def test_compute_subsidy_per_euro_sold_by_crop_divides_subsidy_by_sales():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_subsidy_per_euro_sold_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(2500.0 / 15000.0)
    assert result["ME"] == pytest.approx(200.0 / 5000.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: the 6 new tests FAIL with `AttributeError: module '...indicators' has no attribute 'compute_production_tonnes_by_crop'`.

- [ ] **Step 3: Implement**

Append to `case_studies/guadeloupe/reporting/indicators.py`:

```python
def compute_production_tonnes_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    rdt_cult = dataset.parameters["rdt_cult"]
    return surface_by_crop * rdt_cult.reindex(surface_by_crop.index)


def compute_sales_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    sales_per_ha_cult = dataset.parameters["sales_per_ha_cult"]
    return surface_by_crop * sales_per_ha_cult.reindex(surface_by_crop.index)


def compute_subsidy_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    subsidy_per_ha_cult = dataset.parameters["subsidy_per_ha_cult_annualized"]
    return surface_by_crop * subsidy_per_ha_cult.reindex(surface_by_crop.index)


def compute_total_revenue_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return compute_sales_by_crop(dataset, allocation) + compute_subsidy_by_crop(dataset, allocation)


def compute_subsidy_per_tonne_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    subsidy = compute_subsidy_by_crop(dataset, allocation)
    production = compute_production_tonnes_by_crop(dataset, allocation)
    return (subsidy / production).replace([np.inf, -np.inf], np.nan)


def compute_subsidy_per_euro_sold_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    subsidy = compute_subsidy_by_crop(dataset, allocation)
    sales = compute_sales_by_crop(dataset, allocation)
    return (subsidy / sales).replace([np.inf, -np.inf], np.nan)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/indicators.py tests/test_guadeloupe_reporting_indicators.py
git commit -m "Add per-crop production/sales/subsidy/revenue indicators"
```

---

## Task 7: Farm revenue and Gini coefficient

**Files:**
- Modify: `case_studies/guadeloupe/reporting/indicators.py` (append)
- Test: `tests/test_guadeloupe_reporting_indicators.py` (append)

**Interfaces:**
- Produces: `compute_revenue_by_farm(dataset, allocation) -> pd.Series`,
  `compute_gini(values: pd.Series) -> float` — consumed by `report.py` (Task 10).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_guadeloupe_reporting_indicators.py`:

```python
def test_compute_revenue_by_farm_sums_sales_plus_subsidy_weighted_by_surface():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_revenue_by_farm(dataset, allocation)

    assert result["E1"] == pytest.approx(17500.0)
    assert result["E2"] == pytest.approx(5200.0)


def test_compute_gini_matches_hand_computed_value_for_two_farms():
    values = pd.Series({"E1": 17500.0, "E2": 5200.0})

    result = indicators.compute_gini(values)

    assert result == pytest.approx(0.270925, abs=1e-4)


def test_compute_gini_is_zero_for_equal_distribution():
    values = pd.Series({"E1": 50.0, "E2": 50.0})

    assert indicators.compute_gini(values) == pytest.approx(0.0)


def test_compute_gini_is_zero_for_empty_series():
    assert indicators.compute_gini(pd.Series(dtype=float)) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: the 4 new tests FAIL with `AttributeError: ... has no attribute 'compute_revenue_by_farm'`.

- [ ] **Step 3: Implement**

Append to `case_studies/guadeloupe/reporting/indicators.py`:

```python
def compute_revenue_by_farm(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    sales_per_ha = dataset.parameters["sales_per_ha_cult"].reindex(allocation.values)
    subsidy_per_ha = dataset.parameters["subsidy_per_ha_cult_annualized"].reindex(allocation.values)
    revenue_per_plot = pd.Series(
        surface.to_numpy() * (sales_per_ha.to_numpy() + subsidy_per_ha.to_numpy()),
        index=allocation.index,
    )
    farms = plot_to_farm(dataset).reindex(allocation.index)
    return revenue_per_plot.groupby(farms).sum()


def compute_gini(values: pd.Series) -> float:
    x = np.sort(values.to_numpy(dtype=float))
    n = len(x)
    total = x.sum()
    if n == 0 or total == 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * x)) / (n * total) - (n + 1) / n)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/indicators.py tests/test_guadeloupe_reporting_indicators.py
git commit -m "Add farm revenue and Gini coefficient indicators"
```

---

## Task 8: Shannon diversity and region/island surface breakdown

**Files:**
- Modify: `case_studies/guadeloupe/reporting/indicators.py` (append)
- Test: `tests/test_guadeloupe_reporting_indicators.py` (append)

**Interfaces:**
- Produces: `compute_shannon_diversity(dataset, allocation, grouping) -> pd.Series`,
  `compute_surface_by_region_and_key(dataset, allocation) -> pd.DataFrame`,
  `compute_surface_by_island_and_key(dataset, allocation) -> pd.DataFrame` —
  the region/island ones are consumed by `report.py`/`plots.py` (the map
  substitute, Tasks 9-10).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_guadeloupe_reporting_indicators.py`:

```python
def test_compute_shannon_diversity_is_zero_for_single_crop_farms_and_positive_for_mixed():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)
    farms = indicators.plot_to_farm(dataset)

    result = indicators.compute_shannon_diversity(dataset, allocation, farms)

    assert result["E1"] == pytest.approx(0.0)
    assert result["E2"] == pytest.approx(0.0)
    assert result["E3"] == pytest.approx(0.5623, abs=1e-3)


def test_compute_surface_by_region_and_key_pivots_surface_by_region_and_crop():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)

    result = indicators.compute_surface_by_region_and_key(dataset, allocation)

    assert result.loc["R1", "CS"] == pytest.approx(8.0)
    assert result.loc["R2", "ME"] == pytest.approx(2.0)
    assert result.loc["R1", "ME"] == pytest.approx(0.0)


def test_compute_surface_by_island_and_key_pivots_surface_by_island_and_crop():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)

    result = indicators.compute_surface_by_island_and_key(dataset, allocation)

    assert result.loc[1, "CS"] == pytest.approx(8.0)
    assert result.loc[2, "ME"] == pytest.approx(2.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: the 3 new tests FAIL with `AttributeError: ... has no attribute 'compute_shannon_diversity'`.

- [ ] **Step 3: Implement**

Append to `case_studies/guadeloupe/reporting/indicators.py`:

```python
def compute_shannon_diversity(
    dataset: Dataset, allocation: pd.Series, grouping: pd.Series
) -> pd.Series:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    frame = pd.DataFrame(
        {
            "group_key": grouping.reindex(allocation.index),
            "crop": allocation,
            "surface": surface,
        }
    )

    def _shannon(rows: pd.DataFrame) -> float:
        shares = rows.groupby("crop")["surface"].sum()
        shares = shares[shares > 0] / shares.sum()
        return float(-(shares * np.log(shares)).sum())

    return frame.groupby("group_key").apply(_shannon)


def compute_surface_by_region_and_key(dataset: Dataset, allocation: pd.Series) -> pd.DataFrame:
    region = plot_to_region(dataset).reindex(allocation.index)
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    frame = pd.DataFrame({"region": region, "crop": allocation, "surface": surface})
    return frame.pivot_table(
        index="region", columns="crop", values="surface", aggfunc="sum", fill_value=0.0
    )


def compute_surface_by_island_and_key(dataset: Dataset, allocation: pd.Series) -> pd.DataFrame:
    island = plot_to_island(dataset).reindex(allocation.index)
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    frame = pd.DataFrame({"island": island, "crop": allocation, "surface": surface})
    return frame.pivot_table(
        index="island", columns="crop", values="surface", aggfunc="sum", fill_value=0.0
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: all PASS (full file, ~19 tests).

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/indicators.py tests/test_guadeloupe_reporting_indicators.py
git commit -m "Add Shannon diversity and region/island surface breakdown"
```

---

## Task 9: PNG chart rendering (`plots.py`)

**Files:**
- Modify: `pyproject.toml` (add `matplotlib` dependency)
- Create: `case_studies/guadeloupe/reporting/plots.py`
- Test: `tests/test_guadeloupe_reporting_plots.py`

**Interfaces:**
- Consumes: the `pd.Series`/`pd.DataFrame` shapes produced by `indicators.py`
  (Tasks 6-8).
- Produces: `plot_production_by_crop(series, output_path) -> Path`,
  `plot_subsidy_by_crop(series, output_path) -> Path`,
  `plot_revenue_by_crop(series, output_path) -> Path`,
  `plot_surface_by_region(frame, output_path) -> Path` — consumed by
  `report.py` (Task 10).

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add `"matplotlib>=3.8",` to the `dependencies` list
(after `"tqdm>=4.66",`).

Run: `pip install -e .`
Expected: matplotlib installs successfully.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_guadeloupe_reporting_plots.py`:

```python
import pandas as pd

from case_studies.guadeloupe.reporting import plots


def test_plot_production_by_crop_writes_a_non_empty_png(tmp_path):
    series = pd.Series({"CS": 400.0, "ME": 20.0})

    result = plots.plot_production_by_crop(series, tmp_path / "production.png")

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_subsidy_by_crop_writes_a_non_empty_png(tmp_path):
    series = pd.Series({"CS": 2500.0, "ME": 200.0})

    result = plots.plot_subsidy_by_crop(series, tmp_path / "subsidy.png")

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_revenue_by_crop_writes_a_non_empty_png(tmp_path):
    series = pd.Series({"CS": 17500.0, "ME": 5200.0})

    result = plots.plot_revenue_by_crop(series, tmp_path / "revenue.png")

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_surface_by_region_writes_a_non_empty_png(tmp_path):
    frame = pd.DataFrame({"CS": [8.0, 0.0], "ME": [0.0, 2.0]}, index=["R1", "R2"])

    result = plots.plot_surface_by_region(frame, tmp_path / "surface_by_region.png")

    assert result.exists()
    assert result.stat().st_size > 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_guadeloupe_reporting_plots.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'case_studies.guadeloupe.reporting.plots'`.

- [ ] **Step 4: Implement**

Create `case_studies/guadeloupe/reporting/plots.py`:

```python
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _save_bar_chart(series: pd.Series, *, title: str, ylabel: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    series.sort_values(ascending=False).plot.bar(ax=ax)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_production_by_crop(production_tonnes_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        production_tonnes_by_crop,
        title="Production par culture",
        ylabel="Tonnes",
        output_path=output_path,
    )


def plot_subsidy_by_crop(subsidy_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        subsidy_by_crop,
        title="Subvention par culture",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_revenue_by_crop(total_revenue_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        total_revenue_by_crop,
        title="Revenu total par culture (vente + subvention)",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_surface_by_region(surface_by_region_and_key: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    surface_by_region_and_key.plot.bar(stacked=True, ax=ax)
    ax.set_title("Surface par region et par culture")
    ax.set_ylabel("Hectares")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_guadeloupe_reporting_plots.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml case_studies/guadeloupe/reporting/plots.py tests/test_guadeloupe_reporting_plots.py
git commit -m "Add matplotlib PNG rendering for indicator charts"
```

---

## Task 10: Report orchestration (`report.py`)

**Files:**
- Create: `case_studies/guadeloupe/reporting/report.py`
- Test: `tests/test_guadeloupe_reporting_report.py`

**Interfaces:**
- Consumes: `core.reporting.run_folder.create_output_folder` (Task 4), all of
  `indicators.py` (Tasks 5-8), all of `plots.py` (Task 9).
- Produces: `generate_report(dataset, config, model, results, duration, *, outputs_root=Path("outputs")) -> Path`
  — consumed by `main.py` (Task 11).

- [ ] **Step 1: Write the failing test**

Create `tests/test_guadeloupe_reporting_report.py`:

```python
import json

import pandas as pd
import pytest

from case_studies.guadeloupe.reporting import report
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model
from core.model.solver import solve_model

_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def _tiny_dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0],
            "REGION": ["R1", "R1"],
            "ILE": [1, 1],
            "cult_2016": [6, 6],
            "cult_2017": [6, 6],
        },
        index=["P1", "P2"],
    )
    expl_parc = pd.DataFrame({"farm": ["E1", "E1"], "plot": ["P1", "P2"]})
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "rdt_cult": pd.Series({"CS": 80.0, "ME": 20.0}),
            "sales_per_ha_cult": pd.Series({"CS": 3000.0, "ME": 5000.0}),
            "subsidy_per_ha_cult_annualized": pd.Series({"CS": 500.0, "ME": 200.0}),
        },
        scalars={},
    )


def test_generate_report_writes_full_output_folder(tmp_path):
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

    assert output_dir == tmp_path / "output_1"
    assert (output_dir / "recap.json").exists()
    assert (output_dir / "recap.md").exists()
    assert (output_dir / "config_used.yaml").exists()
    assert (output_dir / "allocation_input.csv").exists()
    assert (output_dir / "allocation_output.csv").exists()
    assert (output_dir / "plots" / "production_by_crop.png").exists()
    assert (output_dir / "plots" / "subsidy_by_crop.png").exists()
    assert (output_dir / "plots" / "revenue_by_crop.png").exists()

    recap = json.loads((output_dir / "recap.json").read_text())
    assert recap["solve_duration_seconds"] == pytest.approx(1.23)
    assert recap["objective"]["name"] == "maximize_gross_margin"
    assert recap["constraints"] == [{"name": "at_most_one_crop_per_plot", "args": {}}]
    assert recap["total_plots"] == 2
    assert recap["total_farms"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_guadeloupe_reporting_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'case_studies.guadeloupe.reporting.report'`.

- [ ] **Step 3: Implement**

Create `case_studies/guadeloupe/reporting/report.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyomo.environ as pyo
import yaml

from case_studies.guadeloupe.reporting import indicators, plots
from core.data.dataset import Dataset
from core.reporting.run_folder import create_output_folder


def generate_report(
    dataset: Dataset,
    config: dict[str, Any],
    model: pyo.ConcreteModel,
    results: Any,
    duration: float,
    *,
    outputs_root: Path = Path("outputs"),
) -> Path:
    output_dir = create_output_folder(outputs_root)

    output_allocation = indicators.decode_output_allocation(model)
    input_allocation = indicators.decode_baseline_allocation(dataset)

    production_by_crop = indicators.compute_production_tonnes_by_crop(dataset, output_allocation)
    subsidy_by_crop = indicators.compute_subsidy_by_crop(dataset, output_allocation)
    total_revenue_by_crop = indicators.compute_total_revenue_by_crop(dataset, output_allocation)
    surface_by_region_output = indicators.compute_surface_by_region_and_key(dataset, output_allocation)
    surface_by_region_input = indicators.compute_surface_by_region_and_key(dataset, input_allocation)

    plots.plot_production_by_crop(production_by_crop, output_dir / "plots" / "production_by_crop.png")
    plots.plot_subsidy_by_crop(subsidy_by_crop, output_dir / "plots" / "subsidy_by_crop.png")
    plots.plot_revenue_by_crop(total_revenue_by_crop, output_dir / "plots" / "revenue_by_crop.png")
    plots.plot_surface_by_region(
        surface_by_region_output, output_dir / "plots" / "surface_by_region_output.png"
    )
    plots.plot_surface_by_region(
        surface_by_region_input, output_dir / "plots" / "surface_by_region_input.png"
    )

    _write_allocation_csv(dataset, output_allocation, output_dir / "allocation_output.csv")
    _write_allocation_csv(dataset, input_allocation, output_dir / "allocation_input.csv")

    output_summary = indicators.compute_aggregate_summary(dataset, output_allocation)
    input_summary = indicators.compute_aggregate_summary(dataset, input_allocation)
    delta_summary = {key: output_summary[key] - input_summary[key] for key in output_summary}

    recap = _build_recap(
        dataset=dataset,
        config=config,
        results=results,
        duration=duration,
        objective_value=float(pyo.value(model.objective)),
        input_summary=input_summary,
        output_summary=output_summary,
        delta_summary=delta_summary,
    )
    (output_dir / "recap.json").write_text(json.dumps(recap, indent=2))
    (output_dir / "recap.md").write_text(_render_recap_markdown(recap))
    (output_dir / "config_used.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
    )

    return output_dir


def _write_allocation_csv(dataset: Dataset, allocation: pd.Series, path: Path) -> None:
    data_parc = dataset.parameters["data_parc"]
    farm = indicators.plot_to_farm(dataset).reindex(allocation.index)
    frame = pd.DataFrame(
        {
            "plot": allocation.index,
            "crop": allocation.to_numpy(),
            "farm": farm.to_numpy(),
            "region": data_parc["REGION"].reindex(allocation.index).to_numpy(),
            "island": data_parc["ILE"].reindex(allocation.index).to_numpy(),
            "surface_ha": data_parc["SURF_HA"].reindex(allocation.index).to_numpy(),
        }
    )
    frame.to_csv(path, index=False)


def _build_recap(
    *,
    dataset: Dataset,
    config: dict[str, Any],
    results: Any,
    duration: float,
    objective_value: float,
    input_summary: dict,
    output_summary: dict,
    delta_summary: dict,
) -> dict:
    enabled_constraints = [
        {"name": entry["name"], "args": entry.get("args") or {}}
        for entry in config["constraints"]
        if entry.get("enable", False)
    ]
    enabled_objective = next(entry for entry in config["objectives"] if entry.get("enable", False))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "solve_duration_seconds": duration,
        "termination_condition": str(results.solver.termination_condition),
        "solver": config["solver"],
        "objective": {
            "name": enabled_objective["name"],
            "args": enabled_objective.get("args") or {},
            "value": objective_value,
        },
        "constraints": enabled_constraints,
        "input": input_summary,
        "output": output_summary,
        "delta": delta_summary,
        "total_plots": int(len(dataset.parameters["data_parc"])),
        "total_farms": int(dataset.parameters["expl_parc"]["farm"].nunique()),
    }


def _render_recap_markdown(recap: dict) -> str:
    lines = [
        "# Recap de simulation",
        "",
        f"- Horodatage : {recap['timestamp']}",
        f"- Duree de resolution : {recap['solve_duration_seconds']:.2f}s",
        f"- Condition de terminaison : {recap['termination_condition']}",
        f"- Solveur : {recap['solver']['name']}",
        f"- Nombre de parcelles (total) : {recap['total_plots']}",
        f"- Nombre d'exploitations (total) : {recap['total_farms']}",
        "",
        "## Objectif",
        f"- {recap['objective']['name']} = {recap['objective']['value']:,.2f}",
        "",
        "## Contraintes activees",
    ]
    for constraint in recap["constraints"]:
        lines.append(f"- {constraint['name']} {constraint['args']}")
    lines += [
        "",
        "## Entree vs sortie",
        f"- Surface cultivee (ha) : {recap['input']['total_surface_ha']:.2f} -> "
        f"{recap['output']['total_surface_ha']:.2f} "
        f"(delta {recap['delta']['total_surface_ha']:+.2f})",
        f"- Parcelles actives : {recap['input']['active_plot_count']} -> "
        f"{recap['output']['active_plot_count']} "
        f"(delta {recap['delta']['active_plot_count']:+d})",
        f"- Exploitations actives : {recap['input']['farm_count']} -> "
        f"{recap['output']['farm_count']} "
        f"(delta {recap['delta']['farm_count']:+d})",
    ]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_guadeloupe_reporting_report.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: all PASS (this is the first point where every prior task's changes
are exercised together).

- [ ] **Step 6: Commit**

```bash
git add case_studies/guadeloupe/reporting/report.py tests/test_guadeloupe_reporting_report.py
git commit -m "Add generate_report orchestration (recap, CSVs, PNGs)"
```

---

## Task 11: Wire `main.py` to `generate_report`

**Files:**
- Modify: `main.py`
- Modify: `.gitignore`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `case_studies.guadeloupe.reporting.report.generate_report` (Task 10).

- [ ] **Step 1: Write the failing test**

Replace the contents of `tests/test_main.py`:

```python
from main import main


def test_main_runs_full_pipeline_and_writes_a_report(tmp_path, capsys):
    main(outputs_root=tmp_path)

    captured = capsys.readouterr()

    assert "Total revenue" in captured.out
    assert "Plots allocated" in captured.out
    output_dir = tmp_path / "output_1"
    assert (output_dir / "recap.json").exists()
    assert (output_dir / "recap.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `TypeError: main() got an unexpected keyword argument 'outputs_root'`.

- [ ] **Step 3: Implement**

Replace `main.py` with:

```python
from pathlib import Path

import pyomo.environ as pyo

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from case_studies.guadeloupe.reporting.report import generate_report
from core.config import load_config
from core.model.progress import solve_with_progress

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"
OUTPUTS_ROOT = Path(__file__).resolve().parent / "outputs"


def main(outputs_root: Path = OUTPUTS_ROOT) -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    results, duration = solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)

    output_dir = generate_report(dataset, config, model, results, duration, outputs_root=outputs_root)

    total_revenue = pyo.value(model.objective)
    allocated_plots = sum(1 for index in model.Y if pyo.value(model.Y[index]) > 0.5)
    total_plots = len(dataset.parameters["data_parc"])

    print(f"Total revenue (gross margin, MB_Ha_Cult): {total_revenue:,.2f}")
    print(f"Plots allocated to a crop: {allocated_plots} / {total_plots}")
    print(f"Report written to: {output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ignore the real outputs directory**

In `.gitignore`, add a new line after `.mosaica_solve_history.json`:

```
/outputs/
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_main.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add main.py .gitignore tests/test_main.py
git commit -m "Wire main.py to generate_report and ignore outputs/"
```

---

## Task 12: Manual end-to-end verification

Not a TDD task — a final sanity check that the real Guadeloupe dataset produces
a sane report (the automated tests above only ever exercise tiny hand-built
fixtures for speed).

- [ ] **Step 1: Run the real pipeline**

Run: `python main.py`
Expected: solve progress bar, then three `print` lines ending with
`Report written to: <repo root>/outputs/output_1`.

- [ ] **Step 2: Inspect the generated folder**

Run: `ls outputs/output_1` (or `Get-ChildItem outputs/output_1` in PowerShell) and open
`outputs/output_1/recap.md`.
Expected: `plots/` (5 PNGs), `recap.md`, `recap.json`, `config_used.yaml`,
`allocation_input.csv`, `allocation_output.csv` all present;
`recap.md`'s "Entree vs sortie" section shows plausible, non-zero numbers for
surface/plot/farm counts on both sides.

- [ ] **Step 3: Run it again and confirm numbering increments**

Run: `python main.py`
Expected: a new `outputs/output_2/` folder appears alongside `output_1/`.

- [ ] **Step 4: Update `VIGILANCE.md`**

Mark brique A as done in the roadmap section (`docs/superpowers/plans` already
records the how; `VIGILANCE.md`'s roadmap checklist should reflect it's no
longer "in progress"). Change the line:

```
- [x] **A. Sauvegarde des résultats** (`outputs/output_N/` + récap + PNG) — en cours d'implémentation.
```

to:

```
- [x] **A. Sauvegarde des résultats** (`outputs/output_N/` + récap + PNG) — livré le 2026-07-09.
```

Commit:

```bash
git add VIGILANCE.md
git commit -m "Mark output persistence/reporting brique as delivered"
```
