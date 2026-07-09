# GAMS Parity Phase 2: Markovitz Risk-Adjusted Objective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port GAMS's `Eq_REV_MARKOVITZ` risk-adjusted objective as a second, opt-in Pyomo
objective (`maximize_risk_adjusted_gross_margin`) alongside the existing
`maximize_gross_margin`, including the farm-typology preprocessing pipeline
(`TYPE_EXPL`/`AVERS`) that supplies its per-farm risk-aversion coefficient.

**Architecture:** A new pure-pandas module (`case_studies/guadeloupe/farm_typology.py`)
classifies each farm's 2017 observed land use into a `TYPE_EXPL` category and looks up a
risk-aversion coefficient (`AVERS`) from it. `ModelInputs` gains two new farm/crop-keyed
fields; a new objective builder consumes them alongside the existing
`crop_margin_per_ha`/`eligible_pairs`. `case_studies/guadeloupe/data_pipeline.py` wires
the new preprocessing into `build_dataset`, and `config.yaml` gets a second, disabled-by-
default `objectives:` entry — one-line flip to enable, matching how Phase 1 shipped
`cs_gfa_minimum_share`.

**Tech Stack:** Python, pandas, numpy, Pyomo (`pyo.Objective`), pytest — same stack as
Phase 1, no new dependencies.

## Global Constraints

- **Source of truth:** every threshold, code, and lookup value in this plan is
  transcribed verbatim from `old_code_gms_format_now_txt/OPTIMISATION.txt` (lines
  1467-1561 for `TYPE_EXPL`/`TYPE_EXPL_Bis`, lines 1744-1758 for `AVERS`) and
  `old_code_gms_format_now_txt/ENTREES.txt` (lines 50-103 for the RPG→base-crop-group
  mapping and its continuity override), re-verified directly against source while
  writing this plan (2026-07-08) — do not "simplify" or "round" any threshold.
- **`AVERS` is computed in-memory from the ported cascade, never read from
  `data/tables/Avers.txt`.** That file is a uniform stub (`AVERS=1` for all 5,336 farms)
  and is not touched by this plan. Per 2026-07-08 user review: proceed on this basis, and
  leave a code comment flagging it for later verification against a real GAMS run's
  output if one becomes available (see Task 3, Step 3).
- **`maximize_gross_margin` stays the enabled-by-default objective.**
  `maximize_risk_adjusted_gross_margin` ships with `enable: false` in `config.yaml` — a
  one-line flip for a maintainer to switch. Per 2026-07-08 user review.
- **Nine possible final `AVERS` values, not ten:** `{0.00, 0.30, 0.50, 0.55, 1.20, 1.30,
  1.60, 2.30, 2.40}`. `1.40` (the bare `TYPE_EXPL=4` value) is never a farm's final value
  — every `TYPE_EXPL=4` farm is always subsequently reclassified by `TYPE_EXPL_Bis` into
  `41` (→0.50) or `42` (→1.60). Getting this wrong (e.g. by skipping the `TYPE_EXPL_Bis`
  step) would silently under/over-penalize every diversified-cane farm.
- **Only the base crop-group mapping is ported, not the full ITK-technique refinement
  cascade** (`ENTREES.txt:304-458`). Every plot gets exactly one of 12 base groups:
  `AG, AN, BA, BC, CS, IG, JA, MA, ME, NC, PN, VE`.
- **Existing registry patterns must be followed exactly:** `@register_objective(name)`
  from `core/model/registry.py` (see `core/model/objectives.py`'s existing
  `maximize_gross_margin` for the exact style — signature
  `(model: pyo.ConcreteModel, inputs: ModelInputs, **_args) -> None`, sets
  `model.objective = pyo.Objective(expr=..., sense=pyo.maximize)`).
- **No changes to `core/model/constraints.py`, `case_studies/guadeloupe/constraints.py`,
  or any existing constraint/rule** — this plan only adds an objective and its
  preprocessing inputs.

---

### Task 1: Wire risk-adjusted objective inputs through `ModelInputs`/builder and implement the objective

**Files:**
- Modify: `core/model/model_inputs.py`
- Modify: `core/model/builder.py`
- Modify: `core/model/objectives.py`
- Test: `tests/test_model_builder.py`

**Interfaces:**
- Consumes: existing `ModelInputs` dataclass (`core/model/model_inputs.py`), existing
  `build_crop_allocation_model` signature (`core/model/builder.py`), existing
  `@register_objective` decorator (`core/model/registry.py`).
- Produces: `ModelInputs.crop_variance_per_ha: Mapping[str, float]` (default `{}`),
  `ModelInputs.farm_risk_aversion: Mapping[str, float]` (default `{}`);
  `build_crop_allocation_model(..., crop_variance_per_ha=None, farm_risk_aversion=None)`
  keyword arguments; objective registered under the name
  `"maximize_risk_adjusted_gross_margin"`. Task 4 passes real data into these.

- [ ] **Step 1: Add the two new fields to `ModelInputs`**

Read `core/model/model_inputs.py` — it currently ends with `crop_yield_per_ha`. Add two
more fields after it:

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
    crop_variance_per_ha: Mapping[str, float] = field(default_factory=dict)
    farm_risk_aversion: Mapping[str, float] = field(default_factory=dict)
```

- [ ] **Step 2: Write the failing test for the objective builder**

Add to `tests/test_model_builder.py` (append at the end of the file):

```python
def test_risk_adjusted_objective_penalizes_risky_crop_on_averse_farm():
    eligible_pairs = [("P1", "C1"), ("P2", "C1")]
    config = {
        "constraints": [],
        "objectives": [
            {"name": "maximize_risk_adjusted_gross_margin", "enable": True, "args": {}}
        ],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=eligible_pairs,
        config=config,
        farm_plots={"FARM_AVERSE": ["P1"], "FARM_NEUTRAL": ["P2"]},
        crop_variance_per_ha={"C1": 0.4},
        farm_risk_aversion={"FARM_AVERSE": 1.30, "FARM_NEUTRAL": 0.0},
    )
    for plot, crop in eligible_pairs:
        model.Y[plot, crop].fix(1)

    expected = 1.0 * 100.0 * (1 - 1.30 * 0.4) + 1.0 * 100.0 * (1 - 0.0 * 0.4)
    assert pyo.value(model.objective) == pytest.approx(expected)


def test_risk_adjusted_objective_defaults_to_zero_variance_and_aversion():
    eligible_pairs = [("P1", "C1")]
    config = {
        "constraints": [],
        "objectives": [
            {"name": "maximize_risk_adjusted_gross_margin", "enable": True, "args": {}}
        ],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0},
        crop_margin_per_ha={"C1": 50.0},
        eligible_pairs=eligible_pairs,
        config=config,
        farm_plots={"FARM1": ["P1"]},
    )
    model.Y["P1", "C1"].fix(1)

    assert pyo.value(model.objective) == pytest.approx(2.0 * 50.0)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v -k risk_adjusted`
Expected: both new tests FAIL — `KeyError: "'maximize_risk_adjusted_gross_margin' is not
registered"` (or similar), since the objective doesn't exist yet.

- [ ] **Step 4: Add the two new keyword arguments to `build_crop_allocation_model`**

In `core/model/builder.py`, change the function signature and body:

```python
def build_crop_allocation_model(
    plot_surface_ha: Mapping[str, float],
    crop_margin_per_ha: Mapping[str, float],
    eligible_pairs: Sequence[tuple[str, str]],
    config: dict[str, Any],
    farm_plots: Mapping[str, Sequence[str]] | None = None,
    farm_surface_ha: Mapping[str, float] | None = None,
    farm_gfa_surface_ha: Mapping[str, float] | None = None,
    crop_yield_per_ha: Mapping[str, float] | None = None,
    crop_variance_per_ha: Mapping[str, float] | None = None,
    farm_risk_aversion: Mapping[str, float] | None = None,
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()
    farm_plots = {} if farm_plots is None else farm_plots
    farm_surface_ha = {} if farm_surface_ha is None else farm_surface_ha
    farm_gfa_surface_ha = {} if farm_gfa_surface_ha is None else farm_gfa_surface_ha
    crop_yield_per_ha = {} if crop_yield_per_ha is None else crop_yield_per_ha
    crop_variance_per_ha = {} if crop_variance_per_ha is None else crop_variance_per_ha
    farm_risk_aversion = {} if farm_risk_aversion is None else farm_risk_aversion

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
        crop_variance_per_ha=crop_variance_per_ha,
        farm_risk_aversion=farm_risk_aversion,
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

(Only the signature, the four new default-handling lines, and the `ModelInputs(...)` call
changed — everything else in the file is unchanged.)

- [ ] **Step 5: Implement the risk-adjusted objective builder**

In `core/model/objectives.py`, append below the existing
`build_maximize_gross_margin_objective`:

```python
@register_objective("maximize_risk_adjusted_gross_margin")
def build_maximize_risk_adjusted_gross_margin_objective(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    plot_to_farm = {
        plot: farm for farm, plots in inputs.farm_plots.items() for plot in plots
    }
    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop]
            * inputs.plot_surface_ha[plot]
            * inputs.crop_margin_per_ha[crop]
            * (
                1
                - inputs.farm_risk_aversion.get(plot_to_farm.get(plot), 0.0)
                * inputs.crop_variance_per_ha.get(crop, 0.0)
            )
            for plot, crop in inputs.eligible_pairs
        ),
        sense=pyo.maximize,
    )
```

This is algebraically `Σ Y·surface·margin·(1 − AVERS(farm)·Var(crop))`, identical to GAMS's
`Σ Y·surface·margin − AVERS(farm)·Σ Y·surface·margin·Var(crop)`
(`old_code_gms_format_now_txt/MODELE.txt:424-430`). `plot_to_farm` is built once per
objective call (not per pair) to keep this linear in `len(eligible_pairs)`, avoiding a
quadratic filter over `eligible_pairs` for every plot.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: all tests in the file PASS, including the two new ones.

- [ ] **Step 7: Commit**

```bash
git add core/model/model_inputs.py core/model/builder.py core/model/objectives.py tests/test_model_builder.py
git commit -m "Add maximize_risk_adjusted_gross_margin objective (Markovitz port)"
```

---

### Task 2: `farm_typology.py` — base crop-group mapping

**Files:**
- Create: `case_studies/guadeloupe/farm_typology.py`
- Test: `tests/test_farm_typology.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure function of two `pd.Series`).
- Produces: `compute_base_crop_group(cult_2016: pd.Series, cult_2017: pd.Series) ->
  pd.Series` — same index as the inputs, values are one of the 12 base-group strings.
  Task 3 and Task 4 both call this.

**Correction (2026-07-09, found during this task's review):** an earlier version of
this plan specified a 3-year (`cult_2015`/`cult_2016`/`cult_2017`) fallow-continuity
check. Reading the raw bytes of `old_code_gms_format_now_txt/ENTREES.txt:49-57` shows
the `cult_2015` clause of the GAMS `IF` condition is commented out (`*` in column 1,
line 51) — GAMS's own executable rule only checks `cult_2016` and `cult_2017`. The
human-readable comment one line above states the rule as "en 2015, 2016 et 2017", but
that comment does not match the code that actually runs. `cult_2015` plays no role and
is dropped from this function's signature entirely — see the design spec's "Correction
made during plan-writing" section (updated 2026-07-09) for the full byte-level citation.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_farm_typology.py`:

```python
import pandas as pd

from case_studies.guadeloupe.farm_typology import compute_base_crop_group


def test_compute_base_crop_group_maps_rpg_codes_to_base_groups():
    cult_2016 = pd.Series([6, 4, 10], index=["P1", "P2", "P3"])
    cult_2017 = pd.Series([6, 4, 13], index=["P1", "P2", "P3"])

    result = compute_base_crop_group(cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "CS", "P2": "BA", "P3": "ME"}


def test_compute_base_crop_group_covers_every_rpg_code():
    codes = list(range(1, 21))
    cult_2017 = pd.Series(codes, index=[f"P{c}" for c in codes])
    # Use a non-fallow prior-year code (6) everywhere so the continuity override never
    # fires, isolating the base mapping table itself.
    cult_2016 = pd.Series(6, index=cult_2017.index)

    result = compute_base_crop_group(cult_2016, cult_2017)

    expected = {
        "P1": "AG", "P2": "AN", "P3": "BC", "P4": "BA", "P5": "VE", "P6": "CS",
        "P7": "PN", "P8": "MA", "P9": "MA", "P10": "JA", "P11": "MA", "P12": "MA",
        "P13": "ME", "P14": "NC", "P15": "MA", "P16": "PN", "P17": "PN", "P18": "IG",
        "P19": "VE", "P20": "VE",
    }
    assert result.to_dict() == expected


def test_compute_base_crop_group_applies_fallow_continuity_override():
    # cult_2016 and cult_2017 both in {0, 10, 14} -> cult_2017 forced to 14 (NC), per
    # the executable condition in old_code_gms_format_now_txt/ENTREES.txt:49-57 (only
    # cult_2016/cult_2017 are checked -- the cult_2015 clause is commented out in GAMS).
    cult_2016 = pd.Series([0], index=["P1"])
    cult_2017 = pd.Series([10], index=["P1"])  # would otherwise map to JA

    result = compute_base_crop_group(cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "NC"}


def test_compute_base_crop_group_does_not_override_when_2016_is_not_fallow():
    cult_2016 = pd.Series([6], index=["P1"])  # 2016 was sugarcane, not fallow
    cult_2017 = pd.Series([10], index=["P1"])

    result = compute_base_crop_group(cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "JA"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_farm_typology.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'case_studies.guadeloupe.farm_typology'`.

- [ ] **Step 3: Implement `compute_base_crop_group`**

Create `case_studies/guadeloupe/farm_typology.py`:

```python
import pandas as pd

# old_code_gms_format_now_txt/ENTREES.txt:62-103 -- RPG cult_2017 code -> base crop group.
_RPG_CODE_TO_BASE_GROUP: dict[int, str] = {
    1: "AG", 2: "AN", 3: "BC", 4: "BA", 5: "VE", 6: "CS", 7: "PN", 8: "MA",
    9: "MA", 10: "JA", 11: "MA", 12: "MA", 13: "ME", 14: "NC", 15: "MA",
    16: "PN", 17: "PN", 18: "IG", 19: "VE", 20: "VE",
}

# old_code_gms_format_now_txt/ENTREES.txt:49-57 -- if a plot's cult_2016 and cult_2017
# are both in this set, cult_2017 is forced to 14 (Non cultivé) before mapping. The
# source's own comment describes a 3-year (cult_2015/2016/2017) rule, but the
# cult_2015 clause of the actual IF condition is commented out (`*` in column 1) --
# only cult_2016/cult_2017 are checked by the code that actually runs.
_FALLOW_CONTINUITY_CODES = {0, 10, 14}


def compute_base_crop_group(cult_2016: pd.Series, cult_2017: pd.Series) -> pd.Series:
    both_fallow = cult_2016.isin(_FALLOW_CONTINUITY_CODES) & cult_2017.isin(
        _FALLOW_CONTINUITY_CODES
    )
    resolved_2017 = cult_2017.where(~both_fallow, 14)
    return resolved_2017.map(_RPG_CODE_TO_BASE_GROUP)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_farm_typology.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/farm_typology.py tests/test_farm_typology.py
git commit -m "Add compute_base_crop_group: RPG code to base crop-group mapping"
```

---

### Task 3: `farm_typology.py` — `TYPE_EXPL`/`TYPE_EXPL_Bis` cascade and `AVERS` lookup

**Files:**
- Modify: `case_studies/guadeloupe/farm_typology.py`
- Test: `tests/test_farm_typology.py`

**Interfaces:**
- Consumes: `compute_base_crop_group`'s output (Task 2) as the `base_crop_group`
  argument below.
- Produces: `compute_type_expl(farm_plots: Mapping[str, Sequence[str]], base_crop_group:
  pd.Series, plot_surface_ha: Mapping[str, float]) -> tuple[pd.Series, pd.Series]` —
  returns `(type_expl, type_expl_bis)`, both indexed by farm id from `farm_plots.keys()`;
  `type_expl` values are `int` in `{0..8}`; `type_expl_bis` is `41`, `42`, or `NaN` (NaN
  for every farm not classified `type_expl == 4`). `compute_avers(type_expl: pd.Series,
  type_expl_bis: pd.Series) -> pd.Series` — farm-indexed `float` risk-aversion
  coefficients. Task 4 calls both.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_farm_typology.py`:

```python
import pytest

from case_studies.guadeloupe.farm_typology import compute_avers, compute_type_expl


# Each scenario is a farm made of (base_group, area_ha) plots, hand-computed against
# the PART_* share formulas and threshold cascade at old_code_gms_format_now_txt/
# OPTIMISATION.txt:1467-1561, and the AVERS lookup at :1744-1758.
_TYPE_EXPL_SCENARIOS = {
    # PART_CAN = 8.34/8.34 = 1.0 >= 0.939 -> type 3 (Canniers) -> AVERS 0.30
    "canniers": ([("CS", 8.34)], 3, 0.30),
    # PART_PLU = 1.0 >= 0.522, all earlier branches false -> type 1 (Arboriculteurs)
    "arboriculteurs": ([("VE", 1.0)], 1, 1.30),
    # PART_BAN = 0.5/1.0 = 0.5 >= 0.364, PART_PAT < 0.327, PART_CAN < 0.625 -> type 2
    "bananiers": ([("BA", 0.5), ("AN", 0.5)], 2, 1.20),
    # PART_PAT = 1.0 >= 0.606, PART_CAN < 0.625 -> type 6 (Eleveurs)
    "eleveurs": ([("PN", 1.0)], 6, 2.40),
    # PART_MAR = 0.9 >= 0.801, earlier branches false -> type 7 (Maraichers)
    "maraichers": ([("MA", 0.9), ("AN", 0.1)], 7, 0.00),
    # PART_PAT = 0.4 (in [0.327, 0.606)), PART_CAN = 0.3 < 0.625 -> type 8
    "mixtes_canniers_eleveurs": ([("PN", 0.4), ("CS", 0.3), ("AN", 0.3)], 8, 2.30),
    # PART_MAR=0.5 < 0.801, PART_PLU=0 < 0.522, earlier branches false -> type 5
    "diversifies": ([("ME", 0.5), ("AN", 0.5)], 5, 0.55),
    # SURF_CUL = 0 (only NC area) -> forced to type 0 (Frichiers) regardless of shares
    "frichiers": ([("NC", 1.0)], 0, 0.00),
    # PART_CAN = 6.25/10 = 0.625 (in [0.625,0.939)) -> type 4. All of PART_MAR, PART_PLU,
    # PART_BC, PART_TT > 0 (AG->plu, BC->bc, IG->mar&tt) -> Bis 41 -> AVERS 0.50
    "canniers_diversifies_bis41": (
        [("CS", 6.25), ("AG", 1.0), ("BC", 1.0), ("IG", 1.75)], 4, 0.50
    ),
    # PART_CAN = 7/10 = 0.7 (in [0.625,0.939)) -> type 4. PART_PLU=PART_BC=PART_TT=0
    # (only PART_MAR=0.3 > 0) -> Bis 42 condition fires last -> AVERS 1.60
    "canniers_diversifies_bis42": ([("CS", 7.0), ("MA", 3.0)], 4, 1.60),
}


@pytest.mark.parametrize(
    "plots, expected_type, expected_avers", _TYPE_EXPL_SCENARIOS.values(),
    ids=_TYPE_EXPL_SCENARIOS.keys(),
)
def test_compute_type_expl_and_avers_classify_each_farm_type(
    plots, expected_type, expected_avers
):
    farm_plots = {"FARM": [f"P{i}" for i in range(len(plots))]}
    base_crop_group = pd.Series(
        {f"P{i}": group for i, (group, _area) in enumerate(plots)}
    )
    plot_surface_ha = {f"P{i}": area for i, (_group, area) in enumerate(plots)}

    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface_ha)
    avers = compute_avers(type_expl, type_expl_bis)

    assert type_expl["FARM"] == expected_type
    assert avers["FARM"] == pytest.approx(expected_avers)


def test_compute_type_expl_returns_nan_bis_for_non_type_4_farms():
    farm_plots = {"FARM": ["P0"]}
    base_crop_group = pd.Series({"P0": "CS"})
    plot_surface_ha = {"P0": 1.0}

    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface_ha)

    assert type_expl["FARM"] == 3
    assert pd.isna(type_expl_bis["FARM"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_farm_typology.py -v -k "type_expl or avers"`
Expected: FAIL with `ImportError: cannot import name 'compute_type_expl'`.

- [ ] **Step 3: Implement `compute_type_expl` and `compute_avers`**

Append to `case_studies/guadeloupe/farm_typology.py`:

```python
from collections.abc import Mapping, Sequence

import numpy as np

# old_code_gms_format_now_txt/OPTIMISATION.txt:1467-1498 -- which base crop groups feed
# which SURF_*/PART_* family aggregate. A base group may feed more than one family (e.g.
# IG counts toward both "mar" and "tt"); "cultiv" is handled separately below since every
# group except NC counts toward it.
_FAMILIES_BY_BASE_GROUP: dict[str, tuple[str, ...]] = {
    "AG": ("plu",),
    "AN": (),
    "BA": ("ban",),
    "BC": ("bc",),
    "CS": ("can",),
    "IG": ("mar", "tt"),
    "JA": ("non",),
    "MA": ("mar",),
    "ME": ("mar",),
    "NC": ("non",),
    "PN": ("pat",),
    "VE": ("plu",),
}

_FAMILIES = ("can", "pat", "ban", "mar", "plu", "bc", "tt", "non")

# old_code_gms_format_now_txt/OPTIMISATION.txt:1744-1758.
_AVERS_BY_TYPE_EXPL: dict[int, float] = {
    1: 1.30, 2: 1.20, 3: 0.30, 5: 0.55, 6: 2.40, 7: 0.00, 8: 2.30,
}
_AVERS_BY_TYPE_EXPL_BIS: dict[int, float] = {41: 0.50, 42: 1.60}


def compute_type_expl(
    farm_plots: Mapping[str, Sequence[str]],
    base_crop_group: pd.Series,
    plot_surface_ha: Mapping[str, float],
) -> tuple[pd.Series, pd.Series]:
    farms = list(farm_plots.keys())
    plot_to_farm = {plot: farm for farm, plots in farm_plots.items() for plot in plots}

    frame = pd.DataFrame(
        {
            "farm": pd.Series(plot_to_farm),
            "group": base_crop_group,
            "surface": pd.Series(plot_surface_ha),
        }
    ).dropna(subset=["farm", "group"])

    def surface_by_farm(groups: set[str]) -> pd.Series:
        subset = frame[frame["group"].isin(groups)]
        return subset.groupby("farm")["surface"].sum().reindex(farms, fill_value=0.0)

    all_groups = set(_FAMILIES_BY_BASE_GROUP.keys())
    surf_cultiv = surface_by_farm(all_groups - {"NC"})
    surf = {
        family: surface_by_farm(
            {group for group, families in _FAMILIES_BY_BASE_GROUP.items() if family in families}
        )
        for family in _FAMILIES
    }

    denom = surf_cultiv - surf["non"]
    safe_denom = denom.where(denom != 0, 1.0)

    def part(family: str) -> pd.Series:
        return (surf[family] / safe_denom).where(denom != 0, 0.0)

    part_can, part_pat, part_ban = part("can"), part("pat"), part("ban")
    part_mar, part_plu = part("mar"), part("plu")
    part_bc, part_tt = part("bc"), part("tt")

    # old_code_gms_format_now_txt/OPTIMISATION.txt:1542-1552 -- the second, authoritative
    # cascade (the first one at :1530-1540 is dead code, unconditionally overwritten
    # before anything reads it; see the design spec for the full justification).
    conditions = [
        (part_can >= 0.625) & (part_can < 0.939),
        part_can >= 0.939,
        (part_can < 0.625) & (part_pat >= 0.606),
        (part_can < 0.625) & (part_pat < 0.606) & (part_pat >= 0.327),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban >= 0.364),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban < 0.364) & (part_mar >= 0.801),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban < 0.364) & (part_mar < 0.801)
        & (part_plu >= 0.522),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban < 0.364) & (part_mar < 0.801)
        & (part_plu < 0.522),
    ]
    choices = [4, 3, 6, 8, 2, 7, 1, 5]
    type_expl = pd.Series(
        np.select(conditions, choices, default=-1), index=farms
    ).astype(int)
    type_expl[surf_cultiv == 0] = 0

    # old_code_gms_format_now_txt/OPTIMISATION.txt:1557-1561 -- sub-split for
    # TYPE_EXPL=4 farms. Both conditions are evaluated in GAMS's written order (41 then
    # 42); whichever is true last wins, so the 42 assignment below is applied after 41.
    type_expl_bis = pd.Series(np.nan, index=farms)
    is_type_4 = type_expl == 4
    bis_41 = (part_mar > 0) | (part_plu > 0) | (part_bc > 0) | (part_tt > 0)
    bis_42 = (part_mar == 0) | (part_plu == 0) | (part_bc == 0) | (part_tt == 0)
    type_expl_bis[is_type_4 & bis_41] = 41
    type_expl_bis[is_type_4 & bis_42] = 42

    return type_expl, type_expl_bis


def compute_avers(type_expl: pd.Series, type_expl_bis: pd.Series) -> pd.Series:
    avers = type_expl.map(_AVERS_BY_TYPE_EXPL).fillna(0.0)
    is_type_4 = type_expl == 4
    avers = avers.where(~is_type_4, type_expl_bis.map(_AVERS_BY_TYPE_EXPL_BIS))
    return avers
```

Note on the `Avers.txt` open item (per Global Constraints above): this function computes
`AVERS` entirely from `type_expl`/`type_expl_bis`, never from
`data/tables/Avers.txt`. If a real GAMS run's `STOCK_AVERS` output ever becomes
available, cross-checking a sample of farms against this function's output would confirm
or refute the cascade transcription above — flagged here for whoever does that check.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_farm_typology.py -v`
Expected: all tests PASS (4 from Task 2 + 10 parametrized `test_compute_type_expl_and_avers_classify_each_farm_type` cases + 1 more = 15 total).

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/farm_typology.py tests/test_farm_typology.py
git commit -m "Add compute_type_expl and compute_avers: farm-typology cascade and AVERS lookup"
```

---

### Task 4: Wire farm typology into the Guadeloupe data pipeline, model, and config

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py`
- Modify: `case_studies/guadeloupe/model.py`
- Modify: `case_studies/guadeloupe/config.yaml`
- Test: `tests/test_guadeloupe_pipeline.py`
- Test: `tests/test_guadeloupe_model.py`
- Test: `tests/test_guadeloupe_config.py`

**Interfaces:**
- Consumes: `compute_base_crop_group`, `compute_type_expl`, `compute_avers` (Task 2/3);
  `ModelInputs.crop_variance_per_ha`/`farm_risk_aversion` and the
  `"maximize_risk_adjusted_gross_margin"` objective (Task 1).
- Produces: `dataset.parameters["crop_variance_per_ha"]` and
  `dataset.parameters["farm_risk_aversion"]` (both `pd.Series`), consumed by `model.py`
  and available to Task 5's real-dataset tests.

- [ ] **Step 1: Write the failing pipeline tests**

Append to `tests/test_guadeloupe_pipeline.py`:

```python
def test_build_dataset_computes_crop_variance_per_ha_from_var_rdt_cult_init_column():
    dataset = build_dataset(CONFIG)

    crop_variance_per_ha = dataset.parameters["crop_variance_per_ha"]

    assert crop_variance_per_ha["AG"] == pytest.approx(0.3)


def test_build_dataset_computes_farm_risk_aversion_for_known_farm():
    dataset = build_dataset(CONFIG)

    farm_risk_aversion = dataset.parameters["farm_risk_aversion"]

    # E1: P1(3.68ha)+P2(3.3ha)+P3(1.36ha), all cult_2017=6 (Canne a sucre) -> base group
    # CS for every plot -> PART_CAN=1.0 (>=0.939) -> TYPE_EXPL=3 (Canniers) -> AVERS=0.30.
    assert farm_risk_aversion["E1"] == pytest.approx(0.30)
```

Append to `tests/test_guadeloupe_model.py` (read the file first to match its existing
import/fixture style before appending):

```python
def test_build_model_supports_enabling_risk_adjusted_objective():
    config = load_config(CONFIG_PATH)
    config = {
        **config,
        "objectives": [
            {"name": "maximize_gross_margin", "enable": False, "args": {}},
            {"name": "maximize_risk_adjusted_gross_margin", "enable": True, "args": {}},
        ],
    }
    dataset = build_dataset(config)

    model = build_model(dataset, config)

    assert model.objective is not None
```

(Match this test's imports — `load_config`, `CONFIG_PATH`, `build_dataset`, `build_model`
— to whatever names `tests/test_guadeloupe_model.py` already imports at the top of the
file; do not introduce new import aliases.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py tests/test_guadeloupe_model.py -v -k "risk_aversion or crop_variance or risk_adjusted"`
Expected: FAIL — `KeyError: 'crop_variance_per_ha'` / `KeyError: 'farm_risk_aversion'` /
objective-not-registered-enabled error.

- [ ] **Step 3: Wire the preprocessing into `build_dataset`**

In `case_studies/guadeloupe/data_pipeline.py`:

Add to the imports at the top:

```python
from case_studies.guadeloupe.farm_typology import (
    compute_avers,
    compute_base_crop_group,
    compute_type_expl,
)
```

Add one line alongside the other `INDICE_H_DIR` reads (near `rdt_cult = ...` at line 58):

```python
    var_rdt_cult = read_wide_table(INDICE_H_DIR / "Var_Rdt_Cult.txt")["init"]
```

After the existing line
`data_parc = data_parc.join(data_rpg[["cult_2015", "cult_2016", "cult_2017"]])`, add:

```python
    base_crop_group = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])
    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface)
    farm_risk_aversion = compute_avers(type_expl, type_expl_bis)
```

Add two entries to the `parameters` dict (alongside the existing `"rdt_cult": rdt_cult,`):

```python
        "crop_variance_per_ha": var_rdt_cult,
        "farm_risk_aversion": farm_risk_aversion,
```

- [ ] **Step 4: Pass the new parameters through `build_model`**

In `case_studies/guadeloupe/model.py`:

```python
from typing import Any

import pyomo.environ as pyo

from case_studies.guadeloupe import constraints as _guadeloupe_constraints  # noqa: F401
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
        crop_variance_per_ha=dataset.parameters.get("crop_variance_per_ha", {}),
        farm_risk_aversion=dataset.parameters.get("farm_risk_aversion", {}),
    )
```

- [ ] **Step 5: Add the disabled-by-default objective entry to `config.yaml`**

In `case_studies/guadeloupe/config.yaml`, change the `objectives:` block from:

```yaml
objectives:
  - name: maximize_gross_margin
    enable: true
    args: {}
```

to:

```yaml
objectives:
  - name: maximize_gross_margin
    enable: true
    args: {}

  # Disabled by default: GAMS's own real solves (CALIB, SCENARIO) always maximize this
  # risk-adjusted objective rather than plain gross margin
  # (OPTIMISATION.txt:174-185), but this codebase keeps maximize_gross_margin as the
  # default per 2026-07-08 user review -- see docs/superpowers/specs/
  # 2026-07-08-gams-parity-phase2-markovitz-itk-design.md. AVERS is computed in-memory
  # from the TYPE_EXPL/TYPE_EXPL_Bis cascade (case_studies/guadeloupe/farm_typology.py)
  # rather than read from data/tables/Avers.txt (a uniform, unvalidated stub) -- flagged
  # for later verification against a real GAMS run if one becomes available.
  - name: maximize_risk_adjusted_gross_margin
    enable: false
    args: {}
```

- [ ] **Step 6: Update `test_guadeloupe_config.py`'s objectives assertion**

In `tests/test_guadeloupe_config.py`, the existing assertion
`assert [e["name"] for e in config["objectives"] if e["enable"]] == ["maximize_gross_margin"]`
still holds unchanged (the new objective is disabled). Add one new assertion directly
below it to lock in that the disabled entry exists:

```python
    assert {e["name"] for e in config["objectives"]} == {
        "maximize_gross_margin",
        "maximize_risk_adjusted_gross_margin",
    }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py tests/test_guadeloupe_model.py tests/test_guadeloupe_config.py -v`
Expected: all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py case_studies/guadeloupe/model.py case_studies/guadeloupe/config.yaml tests/test_guadeloupe_pipeline.py tests/test_guadeloupe_model.py tests/test_guadeloupe_config.py
git commit -m "Wire farm-typology AVERS/Var_Rdt_Cult into the Guadeloupe pipeline and config"
```

---

### Task 5: Real-dataset distribution check

**Files:**
- Test: `tests/test_guadeloupe_pipeline.py`

**Interfaces:**
- Consumes: `dataset.parameters["farm_risk_aversion"]` and
  `dataset.parameters["crop_variance_per_ha"]` (Task 4), built from the real 2017
  Guadeloupe dataset (`build_dataset(CONFIG)`).
- Produces: nothing consumed by later tasks — this is the plan's regression net against
  a wiring bug that would silently produce a uniform/degenerate `AVERS` (the same failure
  mode `data/tables/Avers.txt` already has).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_guadeloupe_pipeline.py`:

```python
def test_build_dataset_farm_risk_aversion_is_not_degenerately_uniform():
    dataset = build_dataset(CONFIG)

    farm_risk_aversion = dataset.parameters["farm_risk_aversion"]

    # Every farm in expl_parc must get a classification (no missing/NaN AVERS).
    all_farms = set(dataset.parameters["expl_parc"]["farm"].unique())
    assert set(farm_risk_aversion.index) == all_farms
    assert not farm_risk_aversion.isna().any()

    # Guards against the exact failure mode data/tables/Avers.txt already has (a
    # uniform AVERS=1 for every farm, which would make risk-aversion meaningless): at
    # least 2 of the 9 possible values must appear across 4,638 real farms.
    assert farm_risk_aversion.nunique() >= 2
    assert set(farm_risk_aversion.unique()) <= {
        0.00, 0.30, 0.50, 0.55, 1.20, 1.30, 1.60, 2.30, 2.40,
    }


def test_build_dataset_base_crop_group_has_no_unmapped_plots():
    dataset = build_dataset(CONFIG)

    data_parc = dataset.parameters["data_parc"]
    from case_studies.guadeloupe.farm_typology import compute_base_crop_group

    base_crop_group = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])

    assert not base_crop_group.isna().any()
```

- [ ] **Step 2: Run test to verify it fails or passes for the right reason**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py -v -k "degenerately or unmapped"`
Expected: since Task 4 already wired everything, this may PASS immediately — that's
fine, it's still a real regression test now guarding real behavior. If it FAILS, it means
a real 2017 `cult_2017` value falls outside the 20-code mapping table in
`compute_base_crop_group`; investigate the actual failing plot's raw value (print
`base_crop_group[base_crop_group.isna()]` and cross-reference against `data_parc.loc[...,
["cult_2015","cult_2016","cult_2017"]]`) before touching the mapping table, since the
table in Task 2 was transcribed verbatim from source — an unmapped value likely means the
continuity-override guard needs a wider fallow-code set, not a wrong table entry.

- [ ] **Step 3: Commit**

```bash
git add tests/test_guadeloupe_pipeline.py
git commit -m "Add real-dataset regression tests for farm_risk_aversion and base_crop_group"
```

---

### Task 6: Full-suite verification

**Files:**
- None modified — this task only runs and inspects; if it finds a bug, use
  `superpowers:systematic-debugging` to fix it in the relevant file from Tasks 1-5 and
  add a regression test before considering this task done.

- [ ] **Step 1: Run the full test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass, including the real end-to-end solve in `tests/test_main.py`
(which still uses the default `maximize_gross_margin` objective, since
`maximize_risk_adjusted_gross_margin` ships disabled — this run is not expected to take
meaningfully longer than Phase 1's).

- [ ] **Step 2: Sanity-check the risk-adjusted objective builds on the full real dataset**

This checks the new objective's wiring at real scale without paying for a second
~1-hour solve. Run:

```bash
.venv/Scripts/python.exe -c "
from case_studies.guadeloupe.data_pipeline import build_dataset, CONFIG_PATH
from case_studies.guadeloupe.model import build_model
from core.config import load_config

config = load_config(CONFIG_PATH)
config = {
    **config,
    'objectives': [
        {'name': 'maximize_gross_margin', 'enable': False, 'args': {}},
        {'name': 'maximize_risk_adjusted_gross_margin', 'enable': True, 'args': {}},
    ],
}
dataset = build_dataset(config)
model = build_model(dataset, config)
print('objective terms:', len(dataset.parameters['eligible_pairs']))
print('model built OK, objective sense:', model.objective.sense)
"
```

Expected: prints without error, `objective sense: maximize`. This does not run the
solver (which would take ~1 hour on the real dataset per Phase 1's Task 10) — building
the Pyomo model object is enough to confirm every input (`farm_risk_aversion`,
`crop_variance_per_ha`, `plot_to_farm`) resolves without a `KeyError` across all ~24,700
real plots. Actually solving with Markovitz enabled, if wanted for a numeric comparison
against the `maximize_gross_margin` baseline, is a separate follow-up left to whoever
reviews this branch — not required for this plan's tests to be considered complete.

- [ ] **Step 3: Record a one-line note in the progress ledger**

Append to `.superpowers/sdd/progress.md`:

```
Phase 2 (Markovitz objective): complete. TYPE_EXPL/AVERS cascade + Var_Rdt_Cult wired;
maximize_risk_adjusted_gross_margin ships disabled by default (config.yaml). Full suite
passing; risk-adjusted objective confirmed to build cleanly on the real 24,700-plot
dataset (not solved end-to-end -- that's a follow-up left to whoever wants the numeric
comparison against maximize_gross_margin's baseline).
```

- [ ] **Step 4: Commit**

```bash
git add .superpowers/sdd/progress.md
git commit -m "Record Phase 2 completion in the progress ledger"
```

---

## Self-Review Notes

- **Spec coverage:** every element of the corrected design spec
  (`docs/superpowers/specs/2026-07-08-gams-parity-phase2-markovitz-itk-design.md`) has a
  task: `ModelInputs`/objective → Task 1, base crop-group mapping → Task 2,
  `TYPE_EXPL`/`TYPE_EXPL_Bis`/`AVERS` → Task 3, pipeline/model/config wiring → Task 4,
  real-dataset sanity check → Task 5, full-suite verification → Task 6. The two resolved
  open items (in-memory `AVERS`, default-disabled objective) are both encoded as Global
  Constraints and enforced by Task 4's config.yaml diff and Task 3's code comment.
- **Placeholder scan:** no TBD/TODO; every code step is complete, runnable code
  transcribed from values re-verified directly against GAMS source during plan-writing
  (not reused from the earlier, incomplete research pass).
- **Type consistency:** `compute_base_crop_group`, `compute_type_expl`, `compute_avers`
  signatures are identical between their introduction (Tasks 2-3) and their call sites
  (Task 4). `ModelInputs.crop_variance_per_ha`/`farm_risk_aversion` field names match
  exactly between Task 1's dataclass and Task 4's `data_pipeline.py`/`model.py` wiring.
  `"maximize_risk_adjusted_gross_margin"` is spelled identically in Task 1's
  `@register_objective` call, Task 4's `config.yaml`, and every test.
- The full ITK-technique refinement cascade, any multi-year `LOOP` structure, and
  re-validating/replacing `data/tables/Avers.txt` on disk remain explicitly out of scope,
  per the design spec.
