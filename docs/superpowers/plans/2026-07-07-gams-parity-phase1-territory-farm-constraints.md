# GAMS parity Phase 1: territory/farm constraints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the GAMS `SCENARIO` model's remaining farm-level and territory-wide
constraints (pineapple/yam area caps, GFA sugarcane share, quota ceilings, production
floors, nutrition floors, banana fallow/rotation, 3-year fallow lock) into the Python
crop-allocation model, so `main.py`'s solve mirrors GAMS parity for everything that
doesn't require the Markovitz/ITK-classification pipeline (that's Phase 2, a separate
plan).

**Architecture:** Extend `ModelInputs`/`build_crop_allocation_model` with a `FARMS` Pyomo
set and farm-level data (mirroring the existing plot/pair pattern). Add three generic,
reusable constraint builders to `core/model/constraints.py` that cover 21 of the 22 new
GAMS equations via config parameterization, plus one case-study-specific builder in a new
`case_studies/guadeloupe/constraints.py`. Add one new categorical eligibility rule
(`friche_lock`) reusing the existing eligibility-masking mechanism instead of a Pyomo
constraint. Wire everything through `config.yaml`.

**Tech Stack:** Python 3.10+, Pyomo 6.7+, pandas 2.0+, HiGHS (`appsi_highs`) via
`highspy`, pytest.

## Global Constraints

- No new dependencies — everything is implementable with pandas/Pyomo already in
  `pyproject.toml`.
- `core/` stays case-study-agnostic: no Guadeloupe-specific column names, crop codes, or
  table names in `core/model/*.py` or `core/data/eligibility.py`. Case-study-specific
  logic (the GFA rule) lives in `case_studies/guadeloupe/`.
- All scalar constants (quotas, shares, ratios) and crop-family membership lists must
  match `old_code_gms_format_now_txt/DONNEES.txt` / `SETS.txt` **exactly** — these are
  copied verbatim in this plan, verified directly against source (see the design doc,
  `docs/superpowers/specs/2026-07-07-gams-parity-territory-farm-constraints-design.md`,
  for the full formula-by-formula derivation and line-number citations).
- Every new Pyomo constraint builder must be invocable multiple times per config (a
  `label: str` kwarg is the Pyomo component attribute name, via
  `setattr(model, label, ...)`), since several GAMS equations share the same shape.
- Follow existing test conventions exactly: synthetic tiny-fixture unit tests per
  function, plus real-data regression assertions with a `# Eq_<GAMS name>` comment.
- `git commit` after every task (this plan's steps say when).

---

### Task 1: `FARMS` set and farm-level fields on `ModelInputs`

**Files:**
- Modify: `core/model/model_inputs.py`
- Modify: `core/model/builder.py`
- Test: `tests/test_model_builder.py`

**Interfaces:**
- Produces: `ModelInputs.farm_plots: Mapping[str, Sequence[str]]`,
  `ModelInputs.farm_surface_ha: Mapping[str, float]`,
  `ModelInputs.farm_gfa_surface_ha: Mapping[str, float]`,
  `ModelInputs.crop_yield_per_ha: Mapping[str, float]` (all default to `{}`).
  `build_crop_allocation_model(..., farm_plots=None, farm_surface_ha=None,
  farm_gfa_surface_ha=None, crop_yield_per_ha=None)` — new optional kwargs, all default
  `None` and are normalized to `{}`. `model.FARMS` — new Pyomo `Set`, built from
  `farm_plots.keys()`.
- Consumed by: Tasks 4, 5, 6, 8 (constraint builders), Task 3 (case-study wiring).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_model_builder.py` (after the existing
`test_build_model_creates_binary_variable_only_for_eligible_pairs` test):

```python
def test_build_model_creates_farms_set_from_farm_plots():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1"), ("P2", "C1")],
        config=CONFIG,
        farm_plots={"E1": ["P1", "P2"]},
    )

    assert set(model.FARMS) == {"E1"}


def test_build_model_defaults_to_empty_farms_set_when_farm_plots_omitted():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1")],
        config=CONFIG,
    )

    assert list(model.FARMS) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -k farms_set -v`
Expected: FAIL with `TypeError: build_crop_allocation_model() got an unexpected keyword
argument 'farm_plots'`

- [ ] **Step 3: Update `ModelInputs`**

Replace the full contents of `core/model/model_inputs.py`:

```python
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass
class ModelInputs:
    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
    farm_plots: Mapping[str, Sequence[str]] = field(default_factory=dict)
    farm_surface_ha: Mapping[str, float] = field(default_factory=dict)
    farm_gfa_surface_ha: Mapping[str, float] = field(default_factory=dict)
    crop_yield_per_ha: Mapping[str, float] = field(default_factory=dict)
```

- [ ] **Step 4: Update `build_crop_allocation_model`**

Replace the full contents of `core/model/builder.py`:

```python
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import pyomo.environ as pyo

from core.config import resolve_enabled
from core.model import constraints as _constraints  # noqa: F401 (registers builders)
from core.model import objectives as _objectives  # noqa: F401 (registers builders)
from core.model.model_inputs import ModelInputs
from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY


def build_crop_allocation_model(
    plot_surface_ha: Mapping[str, float],
    crop_margin_per_ha: Mapping[str, float],
    eligible_pairs: Sequence[tuple[str, str]],
    config: dict[str, Any],
    farm_plots: Mapping[str, Sequence[str]] | None = None,
    farm_surface_ha: Mapping[str, float] | None = None,
    farm_gfa_surface_ha: Mapping[str, float] | None = None,
    crop_yield_per_ha: Mapping[str, float] | None = None,
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()
    farm_plots = farm_plots or {}
    farm_surface_ha = farm_surface_ha or {}
    farm_gfa_surface_ha = farm_gfa_surface_ha or {}
    crop_yield_per_ha = crop_yield_per_ha or {}

    plots_to_crops = defaultdict(list)
    for plot, crop in eligible_pairs:
        plots_to_crops[plot].append(crop)

    model.PAIRS = pyo.Set(initialize=list(eligible_pairs), dimen=2)
    model.PLOTS = pyo.Set(initialize=list(plots_to_crops.keys()))
    model.FARMS = pyo.Set(initialize=list(farm_plots.keys()))
    model.Y = pyo.Var(model.PAIRS, within=pyo.Binary)

    inputs = ModelInputs(
        plot_surface_ha=plot_surface_ha,
        crop_margin_per_ha=crop_margin_per_ha,
        eligible_pairs=eligible_pairs,
        farm_plots=farm_plots,
        farm_surface_ha=farm_surface_ha,
        farm_gfa_surface_ha=farm_gfa_surface_ha,
        crop_yield_per_ha=crop_yield_per_ha,
    )

    for build_constraint, args in resolve_enabled(config["constraints"], CONSTRAINT_REGISTRY):
        build_constraint(model, inputs, **args)

    enabled_objectives = resolve_enabled(config["objectives"], OBJECTIVE_REGISTRY)
    if len(enabled_objectives) != 1:
        raise ValueError(
            f"Expected exactly one enabled objective, got {len(enabled_objectives)}"
        )
    build_objective, args = enabled_objectives[0]
    build_objective(model, inputs, **args)

    return model
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: all PASS (7 existing + 2 new = 9 passed)

- [ ] **Step 6: Commit**

```bash
git add core/model/model_inputs.py core/model/builder.py tests/test_model_builder.py
git commit -m "Add FARMS set and farm-level fields to ModelInputs/build_crop_allocation_model"
```

---

### Task 2: Data pipeline — farm plots, GFA surface, land-use history

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py`
- Test: `tests/test_guadeloupe_pipeline.py`

**Interfaces:**
- Produces: `dataset.parameters["farm_plots"]: dict[str, list[str]]`,
  `dataset.parameters["farm_gfa_surface_ha"]: pd.Series`, and `data_parc` gains
  `cult_2015`, `cult_2016`, `cult_2017` columns (already-loaded `rdt_cult` and
  `farm_surface_ha` parameters are unchanged and reused by Task 3).
- Consumes: `compute_farm_surface_ha` (already defined in this file, reused unmodified —
  it just sums a per-plot `pd.Series` by farm, which works for any per-plot quantity, not
  only surface).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_guadeloupe_pipeline.py`:

```python
def test_build_dataset_computes_farm_plots_grouping():
    dataset = build_dataset(CONFIG)

    farm_plots = dataset.parameters["farm_plots"]

    assert farm_plots["E1"] == ["P1", "P2", "P3"]


def test_build_dataset_computes_farm_gfa_surface_ha():
    dataset = build_dataset(CONFIG)

    farm_gfa_surface_ha = dataset.parameters["farm_gfa_surface_ha"]

    # E5: 7 plots (P12..P18), all GFA_PARC=1, total surface 8.1ha -- entirely GFA-tenure
    assert farm_gfa_surface_ha["E5"] == pytest.approx(8.1)
    # E1002: 26 plots, only P7119 (1.67ha) has GFA_PARC=1
    assert farm_gfa_surface_ha["E1002"] == pytest.approx(1.67)


def test_build_dataset_merges_land_use_history_columns_into_data_parc():
    dataset = build_dataset(CONFIG)

    data_parc = dataset.parameters["data_parc"]

    # P9: fallow/non-cultivated (code 14) in 2015, 2016, and 2017 -- a friche-lock case
    assert data_parc.loc["P9", "cult_2015"] == 14
    assert data_parc.loc["P9", "cult_2016"] == 14
    assert data_parc.loc["P9", "cult_2017"] == 14
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py -k "farm_plots_grouping or farm_gfa_surface_ha or land_use_history" -v`
Expected: FAIL with `KeyError: 'farm_plots'` (and similar for the other two)

- [ ] **Step 3: Implement the pipeline additions**

In `case_studies/guadeloupe/data_pipeline.py`, add a new read call right after the
existing `data_parc = read_wide_table(TABLES_DIR / "Data_Parc_Gwad_2017.txt")` line:

```python
    data_rpg = read_wide_table(TABLES_DIR / "Data_RPG_Gwad_2017.txt")
```

Replace this block:

```python
    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)

    data_parc = data_parc.assign(
        REGION_CODE=data_parc.index.map(reg_parc.set_index("plot")["region"])
    )
```

with:

```python
    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)
    farm_plots = expl_parc.groupby("farm")["plot"].apply(list).to_dict()
    farm_gfa_surface_ha = compute_farm_surface_ha(
        plot_surface * data_parc["GFA_PARC"], expl_parc
    )

    data_parc = data_parc.assign(
        REGION_CODE=data_parc.index.map(reg_parc.set_index("plot")["region"])
    )
    data_parc = data_parc.join(data_rpg[["cult_2015", "cult_2016", "cult_2017"]])
```

In the `parameters = {...}` dict near the end of `build_dataset`, add two entries
(anywhere in the dict, e.g. right after `"farm_surface_ha": farm_surface_ha,`):

```python
        "farm_plots": farm_plots,
        "farm_gfa_surface_ha": farm_gfa_surface_ha,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py -v`
Expected: all PASS (existing + 3 new)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py tests/test_guadeloupe_pipeline.py
git commit -m "Add farm_plots, farm_gfa_surface_ha, and land-use history to the Guadeloupe dataset"
```

---

### Task 3: Wire farm-level dataset parameters into `build_model`

**Files:**
- Modify: `case_studies/guadeloupe/model.py`
- Test: `tests/test_guadeloupe_model.py`

**Interfaces:**
- Consumes: `dataset.parameters["farm_plots"]`, `["farm_surface_ha"]`,
  `["farm_gfa_surface_ha"]`, `["rdt_cult"]` (all from Task 2 / existing pipeline; accessed
  via `.get(..., {})` so datasets that omit them — like the existing fake-dataset test —
  still work).
- Produces: `build_model(dataset, config)` now threads farm-level data through to
  `build_crop_allocation_model` (Task 1's new kwargs).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_guadeloupe_model.py`:

```python
def test_build_model_wires_farm_level_parameters_into_farms_set():
    dataset = _fake_dataset()
    dataset.parameters["farm_plots"] = {"E1": ["P1", "P2"]}
    dataset.parameters["farm_surface_ha"] = pd.Series({"E1": 3.0})

    model = build_model(dataset, CONFIG)

    assert set(model.FARMS) == {"E1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_model.py -k farm_level -v`
Expected: FAIL with `AssertionError` (`model.FARMS` is empty since `build_model` doesn't
pass `farm_plots` through yet)

- [ ] **Step 3: Update `build_model`**

Replace the full contents of `case_studies/guadeloupe/model.py`:

```python
from typing import Any

import pyomo.environ as pyo

from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model


def build_model(dataset: Dataset, config: dict[str, Any]) -> pyo.ConcreteModel:
    return build_crop_allocation_model(
        plot_surface_ha=dataset.parameters["data_parc"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["margin_per_ha_cult"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        config=config,
        farm_plots=dataset.parameters.get("farm_plots", {}),
        farm_surface_ha=dataset.parameters.get("farm_surface_ha", {}),
        farm_gfa_surface_ha=dataset.parameters.get("farm_gfa_surface_ha", {}),
        crop_yield_per_ha=dataset.parameters.get("rdt_cult", {}),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_model.py -v`
Expected: all PASS (existing test + new test)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/model.py tests/test_guadeloupe_model.py
git commit -m "Thread farm-level dataset parameters through build_model"
```

---

### Task 4: `territory_production_bound` generic constraint

**Files:**
- Modify: `core/model/constraints.py`
- Test: `tests/test_model_builder.py`

**Interfaces:**
- Produces: registers `"territory_production_bound"` in `CONSTRAINT_REGISTRY`. Config
  args: `label: str`, `groups: list[{"crops": list[str], "use_yield": bool,
  "rate_multiplier": float}]`, `sense: "le" | "ge"`, `threshold: float`.
- Consumes: `inputs.eligible_pairs`, `inputs.plot_surface_ha`, `inputs.crop_yield_per_ha`
  (Task 1).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_model_builder.py`:

```python
def test_territory_production_bound_constraint_limits_total_yield_le_threshold():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "quota_c1",
                    "groups": [{"crops": ["C1"], "use_yield": True, "rate_multiplier": 1.0}],
                    "sense": "le",
                    "threshold": 5.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1"), ("P2", "C1")],
        config=config,
        crop_yield_per_ha={"C1": 2.0},
    )
    model.Y["P1", "C1"].fix(1)
    model.Y["P2", "C1"].fix(1)

    # 2.0ha*2.0yield + 2.0ha*2.0yield = 8.0
    assert pyo.value(model.quota_c1.body) == pytest.approx(8.0)
    assert model.quota_c1.upper() == pytest.approx(5.0)


def test_territory_production_bound_constraint_supports_area_only_groups():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "min_pasture",
                    "groups": [
                        {"crops": ["PN_PIQ"], "use_yield": False, "rate_multiplier": 1.0}
                    ],
                    "sense": "ge",
                    "threshold": 1.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 3.0},
        crop_margin_per_ha={"PN_PIQ": 10.0},
        eligible_pairs=[("P1", "PN_PIQ")],
        config=config,
    )
    model.Y["P1", "PN_PIQ"].fix(1)

    assert pyo.value(model.min_pasture.body) == pytest.approx(3.0)
    assert model.min_pasture.lower() == pytest.approx(1.0)


def test_territory_production_bound_constraint_sums_multiple_groups():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "combined",
                    "groups": [
                        {"crops": ["C1"], "use_yield": True, "rate_multiplier": 1.0},
                        {"crops": ["C2"], "use_yield": True, "rate_multiplier": 0.5},
                    ],
                    "sense": "ge",
                    "threshold": 0.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"C1": 10.0, "C2": 10.0},
        eligible_pairs=[("P1", "C1"), ("P2", "C2")],
        config=config,
        crop_yield_per_ha={"C1": 4.0, "C2": 4.0},
    )
    model.Y["P1", "C1"].fix(1)
    model.Y["P2", "C2"].fix(1)

    # group1: 1.0ha*4.0*1.0=4.0, group2: 1.0ha*4.0*0.5=2.0, total=6.0
    assert pyo.value(model.combined.body) == pytest.approx(6.0)


def test_territory_production_bound_constraint_raises_for_unknown_sense():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "bad",
                    "groups": [{"crops": ["C1"], "use_yield": False, "rate_multiplier": 1.0}],
                    "sense": "eq",
                    "threshold": 1.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    with pytest.raises(ValueError, match="Unknown sense"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 10.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_territory_production_bound_constraint_handles_no_matching_eligible_pairs():
    # Regression: sum() over zero matching pairs is a plain Python 0, not a Pyomo
    # expression. Comparing two plain numbers produces a bare bool, which Pyomo
    # rejects unless the rule explicitly returns Constraint.Feasible/.Infeasible.
    # This must not raise.
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "empty_group",
                    "groups": [{"crops": ["NOT_ELIGIBLE_ANYWHERE"], "use_yield": False, "rate_multiplier": 1.0}],
                    "sense": "ge",
                    "threshold": 0.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 10.0},
        eligible_pairs=[("P1", "C1")],
        config=config,
    )

    assert model.empty_group.expr()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -k territory_production_bound -v`
Expected: FAIL with `KeyError: "Unknown component 'territory_production_bound'..."`

- [ ] **Step 3: Implement the constraint**

Append to `core/model/constraints.py`:

```python
@register_constraint("territory_production_bound")
def build_territory_production_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    groups: list[dict],
    sense: str,
    threshold: float,
    **_args,
) -> None:
    if sense not in ("le", "ge"):
        raise ValueError(f"Unknown sense {sense!r}, expected 'le' or 'ge'")

    total = 0
    for group in groups:
        crops = set(group["crops"])
        use_yield = group.get("use_yield", True)
        rate_multiplier = group.get("rate_multiplier", 1.0)
        for plot, crop in inputs.eligible_pairs:
            if crop not in crops:
                continue
            rate = inputs.crop_yield_per_ha[crop] if use_yield else 1.0
            total += model.Y[plot, crop] * inputs.plot_surface_ha[plot] * rate * rate_multiplier

    # sum() over zero matching (plot, crop) pairs returns a plain Python 0, not a
    # Pyomo expression -- comparing two plain numbers below would produce a bare
    # Python bool, which Pyomo's Constraint rejects ("trivial Boolean") instead of
    # treating as an always-true/always-false constraint. Guard for it explicitly.
    if isinstance(total, (int, float)):
        satisfied = total <= threshold if sense == "le" else total >= threshold
        setattr(
            model,
            label,
            pyo.Constraint(expr=pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible),
        )
        return

    expr = total <= threshold if sense == "le" else total >= threshold
    setattr(model, label, pyo.Constraint(expr=expr))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/model/constraints.py tests/test_model_builder.py
git commit -m "Add territory_production_bound generic constraint"
```

---

### Task 5: `farm_area_share_max` generic constraint

**Files:**
- Modify: `core/model/constraints.py`
- Test: `tests/test_model_builder.py`

**Interfaces:**
- Produces: registers `"farm_area_share_max"`. Config args: `label: str`,
  `crops: list[str]`, `max_share: float`.
- Consumes: `inputs.eligible_pairs`, `inputs.plot_surface_ha`, `inputs.farm_plots`,
  `inputs.farm_surface_ha`, `model.FARMS` (all from Task 1).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_model_builder.py`:

```python
def test_farm_area_share_max_constraint_limits_crop_family_area_per_farm():
    config = {
        "constraints": [
            {
                "name": "farm_area_share_max",
                "enable": True,
                "args": {"label": "an_cap", "crops": ["AN"], "max_share": 0.5},
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 4.0, "P2": 6.0},
        crop_margin_per_ha={"AN": 100.0, "OTHER": 50.0},
        eligible_pairs=[("P1", "AN"), ("P2", "OTHER")],
        config=config,
        farm_plots={"E1": ["P1", "P2"]},
        farm_surface_ha={"E1": 10.0},
    )
    model.Y["P1", "AN"].fix(1)
    model.Y["P2", "OTHER"].fix(1)

    # AN area = 4.0ha, cap = 0.5 * 10.0ha farm surface = 5.0ha
    assert pyo.value(model.an_cap["E1"].body) == pytest.approx(4.0)
    assert model.an_cap["E1"].upper() == pytest.approx(5.0)


def test_farm_area_share_max_constraint_handles_farm_with_no_eligible_crop_family_plots():
    # Regression: a farm with zero eligible plots for `crops` sums to a plain 0, not
    # a Pyomo expression -- must not raise (see territory_production_bound's note).
    config = {
        "constraints": [
            {
                "name": "farm_area_share_max",
                "enable": True,
                "args": {"label": "an_cap", "crops": ["AN"], "max_share": 0.5},
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 4.0},
        crop_margin_per_ha={"OTHER": 50.0},
        eligible_pairs=[("P1", "OTHER")],
        config=config,
        farm_plots={"E1": ["P1"]},
        farm_surface_ha={"E1": 4.0},
    )

    assert model.an_cap["E1"].expr()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -k farm_area_share_max -v`
Expected: FAIL with `KeyError: "Unknown component 'farm_area_share_max'..."`

- [ ] **Step 3: Implement the constraint**

Append to `core/model/constraints.py`:

```python
@register_constraint("farm_area_share_max")
def build_farm_area_share_max_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    crops: list[str],
    max_share: float,
    **_args,
) -> None:
    crop_set = set(crops)
    plot_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in crop_set:
            plot_crops[plot].append(crop)

    def _rule(model, farm):
        area = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_crops.get(plot, [])
        )
        limit = max_share * inputs.farm_surface_ha[farm]
        # A farm with zero eligible plots for these crops sums to a plain 0, not a
        # Pyomo expression -- see the note in territory_production_bound above.
        if isinstance(area, (int, float)):
            return pyo.Constraint.Feasible if area <= limit else pyo.Constraint.Infeasible
        return area <= limit

    setattr(model, label, pyo.Constraint(model.FARMS, rule=_rule))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/model/constraints.py tests/test_model_builder.py
git commit -m "Add farm_area_share_max generic constraint"
```

---

### Task 6: `farm_area_ratio_min` generic constraint

**Files:**
- Modify: `core/model/constraints.py`
- Test: `tests/test_model_builder.py`

**Interfaces:**
- Produces: registers `"farm_area_ratio_min"`. Config args: `label: str`,
  `numerator_crops: list[str]`, `denominator_crops: list[str]`, `ratio: float`. Builds one
  constraint per `(farm, denominator_crop)` pair — matches GAMS's
  `Eq_BA_JA(SE,SC_BA_JA)`/`Eq_BA_ROTA(SE,SC_BA_JA)` domain binding (see design doc
  correction: NOT one constraint per farm).
- Consumes: same `ModelInputs` fields as Task 5.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_model_builder.py`. This test avoids inspecting `.body`/`.upper()`
because both sides of this constraint are Pyomo variable expressions (not a constant
bound) — Pyomo's internal normalization for that shape is not straightforward to assert
against directly, so we verify behavior through an actual solve instead:

```python
def test_farm_area_ratio_min_constraint_forces_fallow_proportional_to_target_crop():
    config = {
        "constraints": [
            {
                "name": "farm_area_ratio_min",
                "enable": True,
                "args": {
                    "label": "fallow_ratio",
                    "numerator_crops": ["JA"],
                    "denominator_crops": ["BA_INT"],
                    "ratio": 0.2,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 5.0, "P2": 1.0},
        crop_margin_per_ha={"BA_INT": 100.0, "JA": 1.0},
        eligible_pairs=[("P1", "BA_INT"), ("P1", "JA"), ("P2", "BA_INT"), ("P2", "JA")],
        config=config,
        farm_plots={"E1": ["P1", "P2"]},
    )

    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    # Unconstrained profit-max would pick BA_INT on both plots (margin 100 > 1),
    # giving BA_INT area 6.0ha and JA area 0 -- violating JA >= 0.2*BA_INT (0 >= 1.2).
    # The constraint forces the cheaper plot (P2, 1.0ha) to JA instead: BA_INT area
    # becomes 5.0ha (P1 only), JA area 1.0ha, and 1.0 >= 0.2*5.0 = 1.0 exactly.
    assert pyo.value(model.Y["P1", "BA_INT"]) == pytest.approx(1)
    assert pyo.value(model.Y["P2", "JA"]) == pytest.approx(1)


def test_farm_area_ratio_min_constraint_builds_one_instance_per_denominator_crop():
    config = {
        "constraints": [
            {
                "name": "farm_area_ratio_min",
                "enable": True,
                "args": {
                    "label": "fallow_ratio",
                    "numerator_crops": ["JA"],
                    "denominator_crops": ["BA_INT", "BA_IRR"],
                    "ratio": 0.2,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"BA_INT": 10.0},
        eligible_pairs=[("P1", "BA_INT")],
        config=config,
        farm_plots={"E1": ["P1"]},
    )

    assert set(model.fallow_ratio.keys()) == {("E1", "BA_INT"), ("E1", "BA_IRR")}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -k farm_area_ratio_min -v`
Expected: FAIL with `KeyError: "Unknown component 'farm_area_ratio_min'..."`

- [ ] **Step 3: Implement the constraint**

Append to `core/model/constraints.py`:

```python
@register_constraint("farm_area_ratio_min")
def build_farm_area_ratio_min_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    numerator_crops: list[str],
    denominator_crops: list[str],
    ratio: float,
    **_args,
) -> None:
    numerator_set = set(numerator_crops)
    denominator_set = set(denominator_crops)
    plot_numerator_crops = defaultdict(list)
    plot_denominator_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in numerator_set:
            plot_numerator_crops[plot].append(crop)
        if crop in denominator_set:
            plot_denominator_crops[plot].append(crop)

    def _rule(model, farm, denom_crop):
        numerator_area = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_numerator_crops.get(plot, [])
        )
        denominator_area = sum(
            model.Y[plot, denom_crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            if denom_crop in plot_denominator_crops.get(plot, [])
        )
        # Both sides trivially 0 (no eligible plots for either side, on this farm)
        # -- see the note in territory_production_bound above.
        if isinstance(numerator_area, (int, float)) and isinstance(denominator_area, (int, float)):
            satisfied = numerator_area >= ratio * denominator_area
            return pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible
        return numerator_area >= ratio * denominator_area

    setattr(model, label, pyo.Constraint(model.FARMS, denominator_crops, rule=_rule))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/model/constraints.py tests/test_model_builder.py
git commit -m "Add farm_area_ratio_min generic constraint"
```

---

### Task 7: `friche_lock` categorical eligibility rule

**Files:**
- Modify: `core/data/eligibility.py`
- Test: `tests/test_eligibility.py`

**Interfaces:**
- Produces: registers `"friche_lock"` in `CATEGORICAL_RULE_REGISTRY`. Signature:
  `rule_friche_lock(data_parc, *, crops, history_columns, fallow_codes) -> (crops,
  condition)`, matching every other rule in this file.
- Consumes: nothing new — same `data_parc: pd.DataFrame` shape as existing rules.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_eligibility.py`:

```python
def test_rule_friche_lock_matches_plots_fallow_for_every_listed_year():
    data_parc = pd.DataFrame(
        {
            "cult_2015": [14, 14, 5],
            "cult_2016": [14, 5, 14],
            "cult_2017": [10, 14, 14],
        },
        index=["P1", "P2", "P3"],
    )

    crops, condition = rule_friche_lock(
        data_parc,
        crops=["AG", "CS"],
        history_columns=["cult_2015", "cult_2016", "cult_2017"],
        fallow_codes=[0, 10, 14],
    )

    assert crops == ["AG", "CS"]
    # P1: 14,14,10 -- all fallow codes, locked. P2/P3: one year has a real crop (5).
    assert condition.tolist() == [True, False, False]
```

Add `rule_friche_lock` to the import block at the top of `tests/test_eligibility.py`
(alongside the other `rule_*` imports, alphabetically:
`rule_exact_risk_value, rule_friche_lock, rule_irrigation_required, ...`).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_eligibility.py -k friche_lock -v`
Expected: FAIL with `ImportError: cannot import name 'rule_friche_lock'`

- [ ] **Step 3: Implement the rule**

Append to `core/data/eligibility.py`:

```python
@register_categorical_rule("friche_lock")
def rule_friche_lock(
    data_parc: pd.DataFrame,
    *,
    crops: list[str],
    history_columns: list[str],
    fallow_codes: list[int],
) -> tuple[list[str], pd.Series]:
    condition = pd.Series(True, index=data_parc.index)
    for column in history_columns:
        condition &= data_parc[column].isin(fallow_codes)
    return crops, condition
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_eligibility.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add core/data/eligibility.py tests/test_eligibility.py
git commit -m "Add friche_lock categorical eligibility rule"
```

---

### Task 8: `cs_gfa_minimum_share` case-study constraint

**Files:**
- Create: `case_studies/guadeloupe/constraints.py`
- Modify: `case_studies/guadeloupe/model.py`
- Test: `tests/test_guadeloupe_constraints.py` (new file)

**Interfaces:**
- Produces: registers `"cs_gfa_minimum_share"`. Config args: `label: str`,
  `crops: list[str]`, `min_share: float`. Only builds a constraint instance for farms
  where `inputs.farm_gfa_surface_ha.get(farm, 0.0) > 0` (mirrors GAMS's `$` conditional
  equation — the equation is absent, not trivially true, for other farms).
- Consumes: `inputs.farm_gfa_surface_ha` (Task 1/2).

- [ ] **Step 1: Write the failing test**

Create `tests/test_guadeloupe_constraints.py`:

```python
import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe import constraints as _guadeloupe_constraints  # noqa: F401
from core.model.builder import build_crop_allocation_model


def test_cs_gfa_minimum_share_constraint_only_applies_to_farms_with_gfa_surface():
    config = {
        "constraints": [
            {
                "name": "cs_gfa_minimum_share",
                "enable": True,
                "args": {"label": "cs_gfa", "crops": ["CS"], "min_share": 0.6},
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 10.0, "P2": 4.0},
        crop_margin_per_ha={"CS": 50.0, "OTHER": 100.0},
        eligible_pairs=[("P1", "CS"), ("P1", "OTHER"), ("P2", "CS")],
        config=config,
        farm_plots={"E1": ["P1"], "E2": ["P2"]},
        farm_gfa_surface_ha={"E1": 10.0},
    )
    model.Y["P1", "CS"].fix(1)

    assert pyo.value(model.cs_gfa["E1"].body) == pytest.approx(10.0)
    assert model.cs_gfa["E1"].lower() == pytest.approx(6.0)
    assert "E2" not in model.cs_gfa


def test_cs_gfa_minimum_share_constraint_handles_gfa_farm_with_no_eligible_cs_plots():
    # Regression: a GFA farm with zero CS-eligible plots sums to a plain 0, not a
    # Pyomo expression -- must resolve via Constraint.Infeasible, not crash (see
    # territory_production_bound's note in core/model/constraints.py).
    config = {
        "constraints": [
            {
                "name": "cs_gfa_minimum_share",
                "enable": True,
                "args": {"label": "cs_gfa", "crops": ["CS"], "min_share": 0.6},
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 4.0},
        crop_margin_per_ha={"OTHER": 50.0},
        eligible_pairs=[("P1", "OTHER")],
        config=config,
        farm_plots={"E1": ["P1"]},
        farm_gfa_surface_ha={"E1": 4.0},
    )

    # 0.6 * 4.0ha = 2.4ha required, but 0ha CS-eligible -- genuinely infeasible,
    # matching GAMS's algebraic infeasibility for the same equation.
    assert not model.cs_gfa["E1"].expr()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_constraints.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'case_studies.guadeloupe.constraints'`

- [ ] **Step 3: Implement the constraint**

Create `case_studies/guadeloupe/constraints.py`:

```python
from collections import defaultdict

import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_constraint


@register_constraint("cs_gfa_minimum_share")
def build_cs_gfa_minimum_share_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    crops: list[str],
    min_share: float,
    **_args,
) -> None:
    crop_set = set(crops)
    plot_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in crop_set:
            plot_crops[plot].append(crop)

    eligible_farms = [
        farm for farm in inputs.farm_plots if inputs.farm_gfa_surface_ha.get(farm, 0.0) > 0
    ]

    def _rule(model, farm):
        area = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_crops.get(plot, [])
        )
        requirement = min_share * inputs.farm_gfa_surface_ha[farm]
        # A GFA farm with zero eligible SC crop plots sums to a plain 0 -- see the
        # note in territory_production_bound above. Note this can legitimately
        # resolve to Constraint.Infeasible (not just Feasible): a farm required to
        # keep 60% of its GFA land in sugarcane but with zero sugarcane-eligible
        # plots really is infeasible under this rule, matching GAMS's algebraic
        # infeasibility for the same equation -- that should surface as a solver
        # infeasibility, not a Python crash, which is exactly what this achieves.
        if isinstance(area, (int, float)):
            return pyo.Constraint.Feasible if area >= requirement else pyo.Constraint.Infeasible
        return area >= requirement

    setattr(model, label, pyo.Constraint(eligible_farms, rule=_rule))
```

- [ ] **Step 4: Wire the registration import into `build_model`**

In `case_studies/guadeloupe/model.py`, add the import so the decorator registers before
`build_crop_allocation_model` resolves `config["constraints"]`:

```python
from typing import Any

import pyomo.environ as pyo

from case_studies.guadeloupe import constraints as _guadeloupe_constraints  # noqa: F401
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model
```

(Only the import block changes — the `build_model` function body is unchanged from
Task 3.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_constraints.py tests/test_guadeloupe_model.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add case_studies/guadeloupe/constraints.py case_studies/guadeloupe/model.py tests/test_guadeloupe_constraints.py
git commit -m "Add cs_gfa_minimum_share case-study constraint"
```

---

### Task 9: Wire everything into `config.yaml`

**Files:**
- Modify: `case_studies/guadeloupe/config.yaml`
- Test: `tests/test_guadeloupe_pipeline.py`, `tests/test_guadeloupe_model.py`

**Interfaces:**
- Consumes: every constraint/rule registered in Tasks 4-8.
- Produces: the real Guadeloupe model now builds all Phase 1 constraints from
  `config.yaml` when `main()` runs.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_guadeloupe_pipeline.py`:

```python
def test_build_dataset_applies_friche_lock_categorical_rule():
    dataset = build_dataset(CONFIG)

    mask = dataset.parameters["eligibility_mask"]

    # P9: fallow (code 14) in 2015, 2016, and 2017 -- friche-locked (Eq_FRICHE)
    assert mask.loc["P9", "AG"] == False  # noqa: E712


def test_friche_lock_config_crops_match_cult_non_nc_set_file_exactly():
    from core.data.readers import read_flat_set

    friche_entry = next(
        entry for entry in CONFIG["categorical_rules"] if entry["name"] == "friche_lock"
    )
    expected = read_flat_set(
        Path(__file__).resolve().parent.parent / "data" / "sets" / "CULT_NON_NC_2017.set"
    )

    assert set(friche_entry["args"]["crops"]) == set(expected)
    assert len(friche_entry["args"]["crops"]) == len(expected)
```

Add to `tests/test_guadeloupe_model.py`:

```python
def test_build_model_from_real_dataset_creates_every_labeled_phase1_constraint():
    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    config = load_config(
        Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
    )
    dataset = build_dataset(config)

    model = build_model(dataset, config)

    for label in [
        "an_agro_max_expl", "ig_agro_max_expl", "cs_gfa",
        "ba_ja", "ba_rota",
        "ba_quota_max", "cs_quota_max",
        "bc_prod_min", "ig_prod_min", "ma_prod_min", "an_prod_min",
        "plu_prod_min", "me_prod_min", "pn_prod_min",
        "leg_prod_obj", "fru_prod_obj", "pat_surf_obj",
    ]:
        assert hasattr(model, label), f"expected constraint '{label}' to be built"

    for disabled_label in [
        "me_quota_max", "an_quota_max", "ig_quota_max", "bc_quota_max", "tub_prod_obj",
    ]:
        assert not hasattr(model, disabled_label)
```

Add `from pathlib import Path` and `import pandas as pd` to the top of
`tests/test_guadeloupe_model.py` if not already present (`pandas` already is; add
`Path`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py tests/test_guadeloupe_model.py -v`
Expected: FAIL (`friche_lock` rule not in config yet; new labels not built)

- [ ] **Step 3: Update `config.yaml`**

Insert a new `crop_families` block immediately after the `solver:` section (before
`objectives:`), purely to hold YAML anchors referenced below:

```yaml
crop_families:
  an: &SC_AN [AN, AN_NU, AN_PA]
  ig: &SC_IG [IG, IG_PLA, IG_TUT]
  cs: &SC_CS
    [CS, CS_BT_NISM, CS_BT_NIM, CS_BT_IM, CS_SBT_NISM, CS_SBT_NIM, CS_SBT_IM,
     CS_NGT_NISM, CS_NGT_NIM, CS_NGT_IM, CS_CGT_NISM, CS_CGT_NIM, CS_CGT_IM,
     CS_EGT_NISM, CS_EGT_NIM, CS_EGT_IM, CS_MG_NISM, CS_MG_NIM, CS_MG_IM]
  ban_ex: &SC_BAN_EX [BA, BA_INT, BA_IRR, BA_PER, BA_SINT]
  bc: &SC_BC [BC, BC_BT, BC_GTMG]
  ma: &SC_MA
    [MA, MA_PLBIO, MA_MOBIO, MA_ROTA, MA_TO_CHOU_JA, MA_TO_CO_JA,
     MA_BAG_BIO_I, MA_BAG_BIO_NI, MA_BAG_VEG_I, MA_BAG_VEG_NI, MA_BAG_FER_I, MA_BAG_FER_NI,
     MA_BAG_NON_I, MA_BAG_NON_NI, MA_BRF_BIO_I, MA_BRF_BIO_NI, MA_BRF_VEG_I, MA_BRF_VEG_NI,
     MA_BRF_FER_I, MA_BRF_FER_NI, MA_BRF_NON_I, MA_BRF_NON_NI, MA_PAI_BIO_I, MA_PAI_BIO_NI,
     MA_PAI_VEG_I, MA_PAI_VEG_NI, MA_PAI_FER_I, MA_PAI_FER_NI, MA_PAI_NON_I, MA_PAI_NON_NI]
  plu: &SC_PLU [AG, VE, VE_BTGT, VE_PLUIE]
  ba_ja: &SC_BA_JA [BA_INT, BA_IRR, BA_SINT]
```

Append to the `constraints:` list (after the existing `at_most_one_crop_per_plot`
entry):

```yaml
  - name: farm_area_share_max
    enable: true
    args: {label: an_agro_max_expl, crops: *SC_AN, max_share: 0.75}
  - name: farm_area_share_max
    enable: true
    args: {label: ig_agro_max_expl, crops: *SC_IG, max_share: 0.66}

  - name: farm_area_ratio_min
    enable: true
    args: {label: ba_ja, numerator_crops: [JA], denominator_crops: *SC_BA_JA, ratio: 0.2}
  - name: farm_area_ratio_min
    enable: true
    args:
      label: ba_rota
      numerator_crops:
        [JA,
         CS, CS_BT_NISM, CS_BT_NIM, CS_BT_IM, CS_SBT_NISM, CS_SBT_NIM, CS_SBT_IM,
         CS_NGT_NISM, CS_NGT_NIM, CS_NGT_IM, CS_CGT_NISM, CS_CGT_NIM, CS_CGT_IM,
         CS_EGT_NISM, CS_EGT_NIM, CS_EGT_IM, CS_MG_NISM, CS_MG_NIM, CS_MG_IM,
         CF_NBT_NISM, CF_NBT_NIM, CF_SBT_NISM, CF_SBT_NIM, CF_NGT_NISM, CF_NGT_NIM,
         CF_CGT_NISM, CF_CGT_NIM, CF_EGT_NISM, CF_EGT_NIM]
      denominator_crops: *SC_BA_JA
      ratio: 0.2

  - name: cs_gfa_minimum_share
    enable: true
    args: {label: cs_gfa, crops: *SC_CS, min_share: 0.6}

  - name: territory_production_bound
    enable: true
    args:
      label: ba_quota_max
      groups: [{crops: *SC_BAN_EX, use_yield: true, rate_multiplier: 1.0}]
      sense: le
      threshold: 77877
  - name: territory_production_bound
    enable: false
    args:
      label: me_quota_max
      groups: [{crops: [ME], use_yield: true, rate_multiplier: 1.0}]
      sense: le
      threshold: 80000
  - name: territory_production_bound
    enable: false
    args:
      label: an_quota_max
      groups: [{crops: *SC_AN, use_yield: true, rate_multiplier: 0.6666666666666666}]
      sense: le
      threshold: 70000
  - name: territory_production_bound
    enable: false
    args:
      label: ig_quota_max
      groups: [{crops: *SC_IG, use_yield: true, rate_multiplier: 1.0}]
      sense: le
      threshold: 50000
  - name: territory_production_bound
    enable: false
    args:
      label: bc_quota_max
      groups: [{crops: *SC_BC, use_yield: true, rate_multiplier: 1.0}]
      sense: le
      threshold: 40000
  - name: territory_production_bound
    enable: true
    args:
      label: cs_quota_max
      groups: [{crops: *SC_CS, use_yield: true, rate_multiplier: 0.072}]
      sense: le
      threshold: 107000

  - name: territory_production_bound
    enable: true
    args:
      label: bc_prod_min
      groups: [{crops: *SC_BC, use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 4056
  - name: territory_production_bound
    enable: true
    args:
      label: ig_prod_min
      groups: [{crops: *SC_IG, use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 5125
  - name: territory_production_bound
    enable: true
    args:
      label: ma_prod_min
      groups: [{crops: *SC_MA, use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 26404
  - name: territory_production_bound
    enable: true
    args:
      label: an_prod_min
      groups: [{crops: *SC_AN, use_yield: true, rate_multiplier: 0.6666666666666666}]
      sense: ge
      threshold: 2322
  - name: territory_production_bound
    enable: true
    args:
      label: plu_prod_min
      groups: [{crops: *SC_PLU, use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 5879
  - name: territory_production_bound
    enable: true
    args:
      label: me_prod_min
      groups: [{crops: [ME], use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 4135
  - name: territory_production_bound
    enable: true
    args:
      label: pn_prod_min
      groups: [{crops: [PN_PIQ], use_yield: false, rate_multiplier: 1.0}]
      sense: ge
      threshold: 6096

  - name: territory_production_bound
    enable: true
    args:
      label: leg_prod_obj
      groups: [{crops: *SC_MA, use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 63059
  - name: territory_production_bound
    enable: false
    args:
      label: tub_prod_obj
      groups: [{crops: *SC_IG, use_yield: true, rate_multiplier: 1.0}]
      sense: ge
      threshold: 0
  - name: territory_production_bound
    enable: true
    args:
      label: fru_prod_obj
      groups:
        - {crops: *SC_BC, use_yield: true, rate_multiplier: 1.0}
        - {crops: *SC_AN, use_yield: true, rate_multiplier: 0.6666666666666666}
        - {crops: *SC_PLU, use_yield: true, rate_multiplier: 1.0}
        - {crops: [ME], use_yield: true, rate_multiplier: 1.0}
      sense: ge
      threshold: 30789
  - name: territory_production_bound
    enable: true
    args:
      label: pat_surf_obj
      groups: [{crops: [PN_PIQ], use_yield: false, rate_multiplier: 1.0}]
      sense: ge
      threshold: 12193
```

Append to the `categorical_rules:` list:

```yaml
  - name: friche_lock
    enable: true
    args:
      history_columns: [cult_2015, cult_2016, cult_2017]
      fallow_codes: [0, 10, 14]
      crops:
        [AG, AN, AN_NU, AN_PA, BA, BA_INT, BA_IRR, BA_PER, BA_SINT, BC, BC_BT, BC_GTMG,
         CF_NBT_NISM, CF_NBT_NIM, CF_SBT_NISM, CF_SBT_NIM, CF_NGT_NISM, CF_NGT_NIM,
         CF_CGT_NISM, CF_CGT_NIM, CF_EGT_NISM, CF_EGT_NIM,
         CS, CS_BT_NISM, CS_BT_NIM, CS_BT_IM, CS_SBT_NISM, CS_SBT_NIM, CS_SBT_IM,
         CS_NGT_NISM, CS_NGT_NIM, CS_NGT_IM, CS_CGT_NISM, CS_CGT_NIM, CS_CGT_IM,
         CS_EGT_NISM, CS_EGT_NIM, CS_EGT_IM, CS_MG_NISM, CS_MG_NIM, CS_MG_IM,
         IG, IG_PLA, IG_TUT, JA, MA, MA_TO_CHOU_JA, MA_PLBIO, MA_MOBIO, MA_ROTA, ME,
         PN, PN_PIQ, PN_TOUR, TH, VE, VE_BTGT, VE_PLUIE, MA_TO_CO_JA,
         MA_BAG_BIO_I, MA_BAG_BIO_NI, MA_BAG_VEG_I, MA_BAG_VEG_NI, MA_BAG_FER_I, MA_BAG_FER_NI,
         MA_BAG_NON_I, MA_BAG_NON_NI, MA_BRF_BIO_I, MA_BRF_BIO_NI, MA_BRF_VEG_I, MA_BRF_VEG_NI,
         MA_BRF_FER_I, MA_BRF_FER_NI, MA_BRF_NON_I, MA_BRF_NON_NI, MA_PAI_BIO_I, MA_PAI_BIO_NI,
         MA_PAI_VEG_I, MA_PAI_VEG_NI, MA_PAI_FER_I, MA_PAI_FER_NI, MA_PAI_NON_I, MA_PAI_NON_NI]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py tests/test_guadeloupe_model.py -v`
Expected: all PASS. The `friche_lock` crops-match test is the safety net for the
hand-transcribed 83-item list — if it fails, fix the `crops:` list in `config.yaml` to
exactly match `data/sets/CULT_NON_NC_2017.set` (do not edit the test).

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/config.yaml tests/test_guadeloupe_pipeline.py tests/test_guadeloupe_model.py
git commit -m "Enable Phase 1 territory/farm constraints in Guadeloupe config"
```

---

### Task 10: Full-suite and real-solve verification

**Files:**
- None modified — this task only runs and inspects; if it finds a bug, use
  `superpowers:systematic-debugging` to fix it in the relevant file from Tasks 1-9 and
  add a regression test before considering this task done.

- [ ] **Step 1: Run the full test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass, including `tests/test_main.py` (which runs the real ~24,700-row
dataset end to end through `main()`).

- [ ] **Step 2: Run `main.py` directly and inspect output**

Run: `.venv/Scripts/python.exe main.py`
Expected: prints `Total revenue (gross margin, MB_Ha_Cult): <number>` and `Plots
allocated to a crop: <n> / <total>`, solver reaches an optimal solution (no
infeasible/unbounded termination).

- [ ] **Step 3: If the solve is infeasible or unbounded, debug — do not disable constraints to force a pass**

An infeasible solve most likely means either (a) a production floor conflicts with a
quota ceiling on the real 2017 data (check GAMS reference values were transcribed
correctly — every scalar in this plan was verified directly against
`old_code_gms_format_now_txt/DONNEES.txt`, so re-check the `config.yaml` numbers against
Task 9's source first), or (b) a farm/plot referenced in `expl_parc` has no eligible
crops at all and some constraint requires it to have area in a specific family — check
with `dataset.parameters["farm_plots"]` and `dataset.parameters["eligible_pairs"]`
whether any farm named in a `farm_area_ratio_min` denominator has zero eligible plots for
that crop family. Use `superpowers:systematic-debugging` to isolate which single
constraint (temporarily disable one `enable: true` entry at a time in a scratch copy of
`config.yaml`, re-run `main.py`, binary-search) causes infeasibility, then fix the root
cause (likely a data-wiring bug from Tasks 1-3, not the constraint logic itself, since
all thresholds are GAMS-verified). Add a regression test capturing whatever was
wrong before moving on.

- [ ] **Step 4: Record final numbers for the handoff summary**

Note the printed total revenue and allocated-plot count — this goes into the summary you
report at the end of the overnight session so the user can compare against their GAMS
baseline expectations tomorrow morning.

- [ ] **Step 5: Commit (only if Step 3 required code changes)**

```bash
git add -A
git commit -m "Fix issue found during Phase 1 full-suite verification"
```

(If Steps 1-2 passed cleanly with no changes needed, skip this step — there is nothing to
commit.)

---

## Self-Review Notes

- **Spec coverage**: every row of the design doc's "Equation → mechanism map" table has a
  task: farm caps → Task 5, GFA → Task 8, quota ceilings/floors/nutrition → Task 4,
  fallow/rotation → Task 6, friche → Task 7, architecture → Task 1, data wiring → Task 2,
  case-study wiring → Task 3, config → Task 9, end-to-end check → Task 10.
- **Placeholder scan**: no TBD/TODO; every step has complete, runnable code copied from
  values verified directly against `DONNEES.txt`/`SETS.txt`/`MODELE.txt` during the
  design pass.
- **Type consistency**: `label`/`crops`/`groups`/`sense`/`threshold`/`ratio`/
  `numerator_crops`/`denominator_crops`/`max_share`/`min_share` argument names are used
  identically across Tasks 4-9 (constraint implementations and their `config.yaml`
  entries).
- Phase 2 (Markovitz objective, farm labor cap, farm banana quota) is **out of scope for
  this plan** — it needs its own research pass into `ENTREES.txt`'s ITK classification
  logic before a placeholder-free plan can be written for it, per the design doc's
  phasing decision. Write that plan after this one is implemented and verified.
