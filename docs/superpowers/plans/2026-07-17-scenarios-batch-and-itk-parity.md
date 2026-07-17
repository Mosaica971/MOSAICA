# Scenarios batch + ITK geographic parity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the config levers and constraints needed to express ~22 political-trajectory scenarios, port the un-ported GAMS geographic ITK eligibility bans, and author the scenario batch + cleanup + a GAMS port inventory.

**Architecture:** Everything rides the existing config-driven registry pattern. Three code units in Lot 1 (two multiplier levers in the data pipeline, one categorical rule, one MILP constraint), one generic categorical rule in Lot 2 that all ITK bans instantiate from YAML, then Lot 5 is pure YAML/markdown authoring validated without any solve. No solver runs this session.

**Tech Stack:** Python 3, pandas, Pyomo (HiGHS), pytest. Config in YAML. Repo root on `pythonpath`; venv at `.venv/`.

## Global Constraints

- **No solve this session.** Never run `main.py` or `scripts/run_scenarios.py`. Verification is unit tests + `build_dataset` (data load, no MILP solve) only.
- **GAMS parity is the reference.** Legacy behavior in `old_code_gms_format_now_txt/` is the source of truth; deviations must be documented.
- Run one test file with: `.venv/Scripts/python -m pytest tests/<file>.py -v`
- Categorical rules return `(crops: list[str], condition: pd.Series)` where `condition` is `True` on plots where the crops are **forbidden**; `forbid_where(mask, condition, crops)` applies it. (`core/data/eligibility.py`.)
- Multiplier levers use `apply_crop_multipliers(series, rules)` (`case_studies/guadeloupe/economics.py`): `rules` is `[{crops:[...], factor: float}, ...]`, cumulative on overlap, `None` = no-op.
- New MILP constraints whose term set can be empty MUST guard the "trivial Boolean" case with `Constraint.Feasible`/`Constraint.Infeasible` (see `territory_production_bound`).
- **REGION disambiguation:** GAMS ITK bans use `data_parc["REGION"]` (integer 1–7, macro agro-region) and `data_parc["COMMUNE"]` (INSEE) and `data_parc["ILE"]` (1=Basse-Terre, 2=Grande-Terre, 3=Marie-Galante). Do NOT use `REGION_CODE` (R0–R27 petites-régions; that is only for the melon rule).
- Spec: `docs/superpowers/specs/2026-07-17-scenarios-batch-and-gams-parity-port-design.md`. CF block (Lot 4) and MO_MAX (Lot 3) are OUT of this plan.

## File Structure

- `case_studies/guadeloupe/data_pipeline.py` — modify: extract & apply `yield_multipliers` (line 139) and `cost_multipliers` (after line 209).
- `core/data/eligibility.py` — modify: add `forbid_crops` and `attribute_forbidden` categorical rules.
- `core/model/constraints.py` — modify: add `crop_share_bound` constraint builder.
- `case_studies/guadeloupe/config.yaml` — modify: new crop-group anchors (`SC_CS_*`), new categorical-rule entries (ITK bans), doc/cleanup edits.
- `case_studies/guadeloupe/scenarios.yaml` — rewrite: ~22 scenarios.
- `docs/gams_port_inventory.md` — create: equation-by-equation port status.
- `VIGILANCE.md` — modify: resolve REGION point, log MO_MAX/CF deferrals.
- Tests: `tests/test_economics.py`, `tests/test_eligibility.py`, `tests/test_guadeloupe_constraints.py`, `tests/test_guadeloupe_config.py`, `tests/test_scenario_overrides.py`.

---

## LOT 1 — Levers and transition mechanisms

### Task 1: `yield_multipliers` lever (climate yield shock)

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py:108` (add extraction) and `:139` (wrap `rdt_cult`)
- Test: `tests/test_economics.py`

**Interfaces:**
- Consumes: existing `apply_crop_multipliers(series, rules)`.
- Produces: config key `economic_overrides.yield_multipliers` scaling `rdt_cult` at source (propagates to cost, subsidy, sales, GES, and territory-quota yields).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_economics.py`:

```python
def test_apply_crop_multipliers_scales_yield_for_a_climate_shock():
    import pandas as pd
    from case_studies.guadeloupe.economics import apply_crop_multipliers

    rdt = pd.Series({"BA_INT": 100.0, "CS_NGT_NISM": 80.0, "ME": 40.0})
    shocked = apply_crop_multipliers(rdt, [{"crops": ["BA_INT", "CS_NGT_NISM"], "factor": 0.6}])

    assert shocked["BA_INT"] == 60.0
    assert shocked["CS_NGT_NISM"] == 48.0
    assert shocked["ME"] == 40.0  # untouched
```

- [ ] **Step 2: Run test to verify it passes already (logic reused)**

Run: `.venv/Scripts/python -m pytest tests/test_economics.py::test_apply_crop_multipliers_scales_yield_for_a_climate_shock -v`
Expected: PASS (this documents that yield reuses the existing helper; the new work is wiring below).

- [ ] **Step 3: Wire extraction in the pipeline**

In `case_studies/guadeloupe/data_pipeline.py`, after line 108 (`subsidy_multipliers = econ_cfg.get("subsidy_multipliers")`), add:

```python
    yield_multipliers = econ_cfg.get("yield_multipliers")
    cost_multipliers = econ_cfg.get("cost_multipliers")
```

- [ ] **Step 4: Apply the yield shock at source**

Change line 139 from:

```python
    rdt_cult = read_wide_table(INDICE_H_DIR / "Rdt_Cult.txt")[year]
```
to:
```python
    # yield_multipliers (climate shock) scale rdt at source so the shock propagates to
    # variable cost, subsidy (POSEI_Q), sales, GES, and the yield-based territory quotas.
    rdt_cult = apply_crop_multipliers(
        read_wide_table(INDICE_H_DIR / "Rdt_Cult.txt")[year], yield_multipliers
    )
```

- [ ] **Step 5: Write the pipeline wiring test**

Add to `tests/test_guadeloupe_pipeline.py`:

```python
def test_yield_multiplier_scales_rdt_in_dataset():
    from copy import deepcopy
    from pathlib import Path
    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    cfg = load_config(Path("case_studies/guadeloupe/config.yaml"))
    cfg["zone_filter"] = {"include": {"islands": [3]}}  # Marie-Galante: smallest, fast
    base = build_dataset(cfg)

    shocked_cfg = deepcopy(cfg)
    shocked_cfg["economic_overrides"] = {
        "yield_multipliers": [{"crops": ["CS_MG_NISM"], "factor": 0.5}]
    }
    shocked = build_dataset(shocked_cfg)

    assert shocked.parameters["rdt_cult"]["CS_MG_NISM"] == (
        base.parameters["rdt_cult"]["CS_MG_NISM"] * 0.5
    )
```

- [ ] **Step 6: Run the pipeline test**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline.py::test_yield_multiplier_scales_rdt_in_dataset -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py tests/test_economics.py tests/test_guadeloupe_pipeline.py
git commit -m "feat(scenarios): yield_multipliers lever for climate yield shocks"
```

---

### Task 2: `cost_multipliers` lever (input/fuel cost shock)

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py` (after `variable_cost_per_ha_cult = compute_variable_cost_per_ha_cult(...)`, ~line 209)
- Test: `tests/test_guadeloupe_pipeline.py`

**Interfaces:**
- Consumes: `apply_crop_multipliers`; `cost_multipliers` extracted in Task 1 Step 3.
- Produces: config key `economic_overrides.cost_multipliers` scaling `variable_cost_per_ha_cult` (affects margin only, not tonnages).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_guadeloupe_pipeline.py`:

```python
def test_cost_multiplier_scales_variable_cost_in_dataset():
    from copy import deepcopy
    from pathlib import Path
    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    cfg = load_config(Path("case_studies/guadeloupe/config.yaml"))
    cfg["zone_filter"] = {"include": {"islands": [3]}}
    base = build_dataset(cfg)

    shocked_cfg = deepcopy(cfg)
    shocked_cfg["economic_overrides"] = {
        "cost_multipliers": [{"crops": ["CS_MG_NISM"], "factor": 1.3}]
    }
    shocked = build_dataset(shocked_cfg)

    assert shocked.parameters["variable_cost_per_ha_cult"]["CS_MG_NISM"] == (
        base.parameters["variable_cost_per_ha_cult"]["CS_MG_NISM"] * 1.3
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline.py::test_cost_multiplier_scales_variable_cost_in_dataset -v`
Expected: FAIL with `KeyError: 'variable_cost_per_ha_cult'` (that key is NOT currently in the `parameters` dict — verified: the dict at lines 274-302 exposes `margin_per_ha_cult`, `sales_per_ha_cult`, `subsidy_per_ha_cult_annualized`, etc., but not the raw variable cost).

- [ ] **Step 3: Apply the cost shock and expose the parameter**

In `case_studies/guadeloupe/data_pipeline.py`, immediately after the `variable_cost_per_ha_cult = compute_variable_cost_per_ha_cult(...)` call (ends ~line 209), add:

```python
    # cost_multipliers (input/fuel shock) scale the variable cost only -- margin moves,
    # production/tonnage does not.
    variable_cost_per_ha_cult = apply_crop_multipliers(variable_cost_per_ha_cult, cost_multipliers)
```

Then, in the `parameters = {...}` dict (lines 274-302), add this key next to `margin_per_ha_cult` (needed by the test and useful for reporting):

```python
        "variable_cost_per_ha_cult": variable_cost_per_ha_cult,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline.py::test_cost_multiplier_scales_variable_cost_in_dataset -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py tests/test_guadeloupe_pipeline.py
git commit -m "feat(scenarios): cost_multipliers lever for input/fuel cost shocks"
```

---

### Task 3: `forbid_crops` categorical rule (unconditional eligibility cut)

**Files:**
- Modify: `core/data/eligibility.py`
- Test: `tests/test_eligibility.py`

**Interfaces:**
- Produces: categorical rule `forbid_crops` (args: `crops: list[str]`). Forbids the listed crops on **every** plot. Used by drought/disease scenarios and by `Eq_CS_IRR` (irrigated sugarcane disabled everywhere).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_eligibility.py`:

```python
def test_forbid_crops_forbids_listed_crops_on_all_plots():
    import pandas as pd
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY

    data_parc = pd.DataFrame({"ILE": [1, 2, 3]}, index=["P1", "P2", "P3"])
    rule = CATEGORICAL_RULE_REGISTRY["forbid_crops"]
    crops, condition = rule(data_parc, crops=["ME", "BA_IRR"])

    assert crops == ["ME", "BA_IRR"]
    assert condition.all()  # forbidden on every plot
    assert list(condition.index) == ["P1", "P2", "P3"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_eligibility.py::test_forbid_crops_forbids_listed_crops_on_all_plots -v`
Expected: FAIL with `KeyError: 'forbid_crops'`.

- [ ] **Step 3: Implement the rule**

In `core/data/eligibility.py`, after `rule_friche_lock` (line 123), add:

```python
@register_categorical_rule("forbid_crops")
def rule_forbid_crops(
    data_parc: pd.DataFrame, *, crops: list[str]
) -> tuple[list[str], pd.Series]:
    """Forbid `crops` on every plot (unconditional). Used by climate/sanitary shock
    scenarios (drought disables irrigated crops, disease disables a filiere) and by the
    GAMS Eq_CS_IRR ban (irrigated sugarcane disabled everywhere)."""
    condition = pd.Series(True, index=data_parc.index)
    return crops, condition
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_eligibility.py::test_forbid_crops_forbids_listed_crops_on_all_plots -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/data/eligibility.py tests/test_eligibility.py
git commit -m "feat(scenarios): forbid_crops categorical rule (unconditional eligibility cut)"
```

---

### Task 4: `crop_share_bound` constraint (min/max territorial share)

**Files:**
- Modify: `core/model/constraints.py`
- Test: `tests/test_guadeloupe_constraints.py`

**Interfaces:**
- Consumes: `ModelInputs` (`eligible_pairs`, `plot_surface_ha`), `model.Y`.
- Produces: constraint `crop_share_bound` (args: `label: str`, `numerator_crops: list[str]`, `denominator_crops: list[str]`, `sense: "ge"|"le"`, `share: float`). Enforces `area(numerator) {>=|<=} share * area(denominator)` summed over **all** plots (territory scale).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_guadeloupe_constraints.py` (top of file already has `import pyomo.environ as pyo`, `import pytest`, and `from core.model.builder import build_crop_allocation_model`). Follow the file's existing style — build the whole model from a config, then assert on `model.<label>`:

```python
def test_crop_share_bound_ge_enforces_minimum_bio_share():
    config = {
        "constraints": [
            {
                "name": "crop_share_bound",
                "enable": True,
                "args": {
                    "label": "bio_min",
                    "numerator_crops": ["MA_PLBIO"],
                    "denominator_crops": ["MA_PLBIO", "MA_ROTA"],
                    "sense": "ge",
                    "share": 0.3,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 10.0, "P2": 10.0},
        crop_margin_per_ha={"MA_PLBIO": 100.0, "MA_ROTA": 100.0},
        eligible_pairs=[("P1", "MA_PLBIO"), ("P1", "MA_ROTA"), ("P2", "MA_PLBIO"), ("P2", "MA_ROTA")],
        config=config,
        farm_plots={"E1": ["P1", "P2"]},
        farm_gfa_surface_ha={},
    )
    # P1 bio (10 ha), P2 non-bio (10 ha) -> bio area 10, total 20.
    model.Y["P1", "MA_PLBIO"].fix(1)
    model.Y["P1", "MA_ROTA"].fix(0)
    model.Y["P2", "MA_PLBIO"].fix(0)
    model.Y["P2", "MA_ROTA"].fix(1)
    # RHS has variables, so Pyomo canonicalizes to  body = num - share*denom >= 0.
    assert model.bio_min.lower() == pytest.approx(0.0)
    assert pyo.value(model.bio_min.body) == pytest.approx(10.0 - 0.3 * 20.0)  # = 4.0, feasible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py::test_crop_share_bound_ge_enforces_minimum_bio_share -v`
Expected: FAIL with `KeyError: 'crop_share_bound'`.

- [ ] **Step 3: Implement the constraint**

In `core/model/constraints.py`, after `build_farm_area_ratio_min_constraint`, add:

```python
@register_constraint("crop_share_bound")
def build_crop_share_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    numerator_crops: list[str],
    denominator_crops: list[str],
    sense: str,
    share: float,
    **_args,
) -> None:
    """Territory-wide share bound: area(numerator) {ge|le} share * area(denominator),
    summed over all plots. Used for a minimum bio share (numerator = bio variants,
    denominator = whole filiere, ge) or a maximum intensification share (numerator =
    intensive variants, le)."""
    if sense not in ("le", "ge"):
        raise ValueError(f"Unknown sense {sense!r}, expected 'le' or 'ge'")

    numerator_set = set(numerator_crops)
    denominator_set = set(denominator_crops)
    numerator_area = 0
    denominator_area = 0
    for plot, crop in inputs.eligible_pairs:
        if crop in numerator_set:
            numerator_area += model.Y[plot, crop] * inputs.plot_surface_ha[plot]
        if crop in denominator_set:
            denominator_area += model.Y[plot, crop] * inputs.plot_surface_ha[plot]

    # Both sides may be a plain 0 (no eligible pairs) -- guard the trivial Boolean, as in
    # territory_production_bound.
    if isinstance(numerator_area, (int, float)) and isinstance(denominator_area, (int, float)):
        satisfied = (
            numerator_area >= share * denominator_area
            if sense == "ge"
            else numerator_area <= share * denominator_area
        )
        setattr(
            model,
            label,
            pyo.Constraint(expr=pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible),
        )
        return

    expr = (
        numerator_area >= share * denominator_area
        if sense == "ge"
        else numerator_area <= share * denominator_area
    )
    setattr(model, label, pyo.Constraint(expr=expr))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py::test_crop_share_bound_ge_enforces_minimum_bio_share -v`
Expected: PASS. (If Pyomo canonicalizes lower/body differently than assumed, adjust to
`assert pyo.value(model.bio_min.body) - (model.bio_min.lower() or 0.0) == pytest.approx(4.0)` — the semantic check is `num - share*denom >= 0`.)

- [ ] **Step 5: Add the empty-term guard test**

Add to the same file (both numerator and denominator crops absent from `eligible_pairs` -> both sums are a plain `0`; the constraint must build via the `Constraint.Feasible` guard, not raise a "trivial Boolean"):

```python
def test_crop_share_bound_empty_terms_are_guarded():
    config = {
        "constraints": [
            {
                "name": "crop_share_bound",
                "enable": True,
                "args": {
                    "label": "intensif_cap",
                    "numerator_crops": ["BA_INT"],
                    "denominator_crops": ["MA_ROTA"],
                    "sense": "le",
                    "share": 0.2,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 5.0},
        crop_margin_per_ha={"MA_PLBIO": 50.0},
        eligible_pairs=[("P1", "MA_PLBIO")],  # neither BA_INT nor MA_ROTA eligible
        config=config,
        farm_plots={"E1": ["P1"]},
        farm_gfa_surface_ha={},
    )
    assert model.intensif_cap is not None  # built via guard (Constraint.Feasible), no exception
```

- [ ] **Step 6: Run both tests**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py -k crop_share_bound -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add core/model/constraints.py tests/test_guadeloupe_constraints.py
git commit -m "feat(scenarios): crop_share_bound constraint (min bio / max intensification share)"
```

---

## LOT 2 — Geographic ITK eligibility bans (GAMS parity)

### Task 5: `attribute_forbidden` generic categorical rule

**Files:**
- Modify: `core/data/eligibility.py`
- Test: `tests/test_eligibility.py`

**Interfaces:**
- Produces: categorical rule `attribute_forbidden` (args: `crops: list[str]`, `conditions: list[dict]`). Each condition is `{column: str, op: "eq"|"ne"|"in"|"not_in"|"lt"|"le"|"gt"|"ge", value: <scalar or list>}`. Conditions are **ANDed** (forbidden where ALL hold). OR across columns is expressed by using multiple rule entries (each removes its subset; the mask intersection yields the union of forbidden).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_eligibility.py`:

```python
def test_attribute_forbidden_single_and_multi_condition():
    import pandas as pd
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY

    data_parc = pd.DataFrame(
        {"ILE": [1, 2, 3, 2], "REGION": [5, 3, 1, 5], "COMMUNE": [97110, 97102, 97130, 97117]},
        index=["P1", "P2", "P3", "P4"],
    )
    rule = CATEGORICAL_RULE_REGISTRY["attribute_forbidden"]

    # Single condition: forbid where COMMUNE not in the Nord-Grande-Terre commune list
    crops, cond = rule(data_parc, crops=["CS_NGT_NISM"],
                       conditions=[{"column": "COMMUNE", "op": "not_in",
                                    "value": [97102, 97119, 97122]}])
    assert crops == ["CS_NGT_NISM"]
    assert cond.tolist() == [True, False, True, True]  # only P2 (97102) allowed

    # AND of two conditions: forbid CS_BT where ILE != 1 AND REGION != 5
    _, cond2 = rule(data_parc, crops=["CS_BT_NISM"],
                    conditions=[{"column": "ILE", "op": "ne", "value": 1},
                                {"column": "REGION", "op": "ne", "value": 5}])
    # P1 ILE1 -> allowed; P2 ILE2&REG3 -> forbidden; P3 ILE3&REG1 -> forbidden; P4 ILE2&REG5 -> allowed
    assert cond2.tolist() == [False, True, True, False]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_eligibility.py::test_attribute_forbidden_single_and_multi_condition -v`
Expected: FAIL with `KeyError: 'attribute_forbidden'`.

- [ ] **Step 3: Implement the rule**

In `core/data/eligibility.py`, after `rule_forbid_crops`, add:

```python
_COMPARATORS: dict[str, Callable[[pd.Series, Any], pd.Series]] = {
    "eq": lambda s, v: s == v,
    "ne": lambda s, v: s != v,
    "in": lambda s, v: s.isin(v),
    "not_in": lambda s, v: ~s.isin(v),
    "lt": lambda s, v: s < v,
    "le": lambda s, v: s <= v,
    "gt": lambda s, v: s > v,
    "ge": lambda s, v: s >= v,
}


@register_categorical_rule("attribute_forbidden")
def rule_attribute_forbidden(
    data_parc: pd.DataFrame, *, crops: list[str], conditions: list[dict[str, Any]]
) -> tuple[list[str], pd.Series]:
    """Forbid `crops` on plots where ALL `conditions` hold (logical AND). Each condition is
    {column, op, value} with op in eq/ne/in/not_in/lt/le/gt/ge. Express an OR across columns
    with several rule entries (each forbids its subset; the mask keeps the union forbidden).
    Ports the GAMS geographic/soil/irrigation ITK bans (Eq_CS_*, Eq_IG_*_ILE, Eq_BA_*,
    Eq_BC_*, Eq_AG_*, Eq_VE_*)."""
    condition = pd.Series(True, index=data_parc.index)
    for spec in conditions:
        comparator = _COMPARATORS[spec["op"]]
        condition &= comparator(data_parc[spec["column"]], spec["value"])
    return crops, condition
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_eligibility.py::test_attribute_forbidden_single_and_multi_condition -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/data/eligibility.py tests/test_eligibility.py
git commit -m "feat(parity): attribute_forbidden generic categorical rule for ITK bans"
```

---

### Task 6: Wire all ITK geographic bans into config.yaml

**Files:**
- Modify: `case_studies/guadeloupe/config.yaml` (crop-group anchors + `categorical_rules` entries)
- Test: `tests/test_guadeloupe_config.py`

**Interfaces:**
- Consumes: `attribute_forbidden` (Task 5), `forbid_crops` (Task 3).
- Produces: new eligibility bans active in every run.

The GAMS bans to transcribe (`MODELE.txt:254-319`, memberships from `SETS.txt:122-180`). Note ILE: 1=Basse-Terre, 2=Grande-Terre, 3=Marie-Galante.

- [ ] **Step 1: Add sugarcane sub-group anchors**

In `config.yaml` under `crop_families:` (after the `cs:` anchor, ~line 85), add:

```yaml
  cs_irrig: &SC_CS_IRRIG [CS_BT_IM, CS_SBT_IM, CS_NGT_IM, CS_CGT_IM, CS_EGT_IM, CS_MG_IM]
  cs_meca: &SC_CS_MECA
    [CS_BT_NIM, CS_BT_IM, CS_SBT_NIM, CS_SBT_IM, CS_NGT_NIM, CS_NGT_IM,
     CS_CGT_NIM, CS_CGT_IM, CS_EGT_NIM, CS_EGT_IM, CS_MG_NIM, CS_MG_IM]
  cs_bt: &SC_CS_BT [CS_BT_NISM, CS_BT_NIM, CS_BT_IM]
  cs_sbt: &SC_CS_SBT [CS_SBT_NISM, CS_SBT_NIM, CS_SBT_IM]
  cs_ngt: &SC_CS_NGT [CS_NGT_NISM, CS_NGT_NIM, CS_NGT_IM]
  cs_cgt: &SC_CS_CGT [CS_CGT_NISM, CS_CGT_NIM, CS_CGT_IM]
  cs_egt: &SC_CS_EGT [CS_EGT_NISM, CS_EGT_NIM, CS_EGT_IM]
  cs_mg: &SC_CS_MG [CS_MG_NISM, CS_MG_NIM, CS_MG_IM]
```

- [ ] **Step 2: Add the ITK ban entries**

In `config.yaml` under `categorical_rules:`, before `friche_lock` (line 368), add the block below. Each comment cites its GAMS equation.

```yaml
  # --- GAMS geographic/soil/irrigation ITK bans (MODELE.txt:254-319), ported 2026-07-17.
  # Uses data_parc["REGION"] (1-7 macro agro-region), COMMUNE (INSEE), ILE (1=BT,2=GT,3=MG).
  # Eq_CS_IRR: irrigated sugarcane disabled everywhere (IRRIG in {0,1} = all plots).
  - name: forbid_crops
    enable: true
    args: {crops: *SC_CS_IRRIG}
  # Eq_CS_SOL_SQUE: mechanized sugarcane forbidden on skeletal soil (SOL_COURT = 1).
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_MECA, conditions: [{column: SOL_COURT, op: eq, value: 1}]}
  # Eq_CS_CONFORM: mechanized sugarcane forbidden on ill-shaped plots (CONFORM > 1500).
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_MECA, conditions: [{column: CONFORM, op: gt, value: 1500}]}
  # Eq_CS_BT: Basse-Terre sugarcane forbidden where ILE != 1 AND REGION != 5.
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_BT, conditions: [{column: ILE, op: ne, value: 1}, {column: REGION, op: ne, value: 5}]}
  # Eq_CS_SBT: South Basse-Terre sugarcane forbidden where REGION != 5.
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_SBT, conditions: [{column: REGION, op: ne, value: 5}]}
  # Eq_CS_NGT: North Grande-Terre sugarcane forbidden outside its communes.
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_NGT, conditions: [{column: COMMUNE, op: not_in, value: [97102, 97119, 97122]}]}
  # Eq_CS_CGT: Centre Grande-Terre sugarcane forbidden outside its communes.
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_CGT, conditions: [{column: COMMUNE, op: not_in, value: [97116, 97113, 97101]}]}
  # Eq_CS_EGT: East Grande-Terre sugarcane forbidden outside its communes.
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_EGT, conditions: [{column: COMMUNE, op: not_in, value: [97117, 97128, 97125]}]}
  # Eq_CS_MG: Marie-Galante sugarcane forbidden where ILE != 3.
  - name: attribute_forbidden
    enable: true
    args: {crops: *SC_CS_MG, conditions: [{column: ILE, op: ne, value: 3}]}
  # Eq_IG_PLA_ILE: flat-yam forbidden in Basse-Terre (ILE = 1).
  - name: attribute_forbidden
    enable: true
    args: {crops: [IG_PLA], conditions: [{column: ILE, op: eq, value: 1}]}
  # Eq_IG_TUT_ILE: staked-yam forbidden outside Basse-Terre (ILE != 1).
  - name: attribute_forbidden
    enable: true
    args: {crops: [IG_TUT], conditions: [{column: ILE, op: ne, value: 1}]}
  # Eq_BA_IRR: irrigated banana forbidden on non-irrigated plots (IRRIG_PARC = 0).
  - name: attribute_forbidden
    enable: true
    args: {crops: [BA_IRR], conditions: [{column: IRRIG_PARC, op: eq, value: 0}]}
  # Eq_BA_IRR_BT: irrigated banana forbidden in Basse-Terre (ILE = 1; only GT allowed).
  - name: attribute_forbidden
    enable: true
    args: {crops: [BA_IRR], conditions: [{column: ILE, op: eq, value: 1}]}
  # Eq_BC_BT: Basse-Terre plantain forbidden outside Basse-Terre (ILE != 1).
  - name: attribute_forbidden
    enable: true
    args: {crops: [BC_BT], conditions: [{column: ILE, op: ne, value: 1}]}
  # Eq_BC_GTMG: GT/MG plantain forbidden in Basse-Terre (ILE = 1).
  - name: attribute_forbidden
    enable: true
    args: {crops: [BC_GTMG], conditions: [{column: ILE, op: eq, value: 1}]}
  # Eq_BC_IRR_BT: Basse-Terre plantain forbidden where PLUVIO < 2300 AND not irrigated.
  - name: attribute_forbidden
    enable: true
    args: {crops: [BC_BT], conditions: [{column: PLUVIO_PARC, op: lt, value: 2300}, {column: IRRIG_PARC, op: eq, value: 0}]}
  # Eq_BC_IRR_GTMG: GT/MG plantain forbidden where ILE != 1 AND not irrigated.
  - name: attribute_forbidden
    enable: true
    args: {crops: [BC_GTMG], conditions: [{column: ILE, op: ne, value: 1}, {column: IRRIG_PARC, op: eq, value: 0}]}
  # Eq_AG_IRR: citrus (AG) forbidden where not irrigated AND altitude < 400.
  - name: attribute_forbidden
    enable: true
    args: {crops: [AG], conditions: [{column: IRRIG_PARC, op: eq, value: 0}, {column: ALTITUDE, op: lt, value: 400}]}
  # Eq_AG_BT: citrus (AG) forbidden outside Basse-Terre (ILE > 1).
  - name: attribute_forbidden
    enable: true
    args: {crops: [AG], conditions: [{column: ILE, op: gt, value: 1}]}
  # Eq_VE_IRR: VE_BTGT forbidden where PLUVIO < 2700 AND not irrigated.
  - name: attribute_forbidden
    enable: true
    args: {crops: [VE_BTGT], conditions: [{column: PLUVIO_PARC, op: lt, value: 2700}, {column: IRRIG_PARC, op: eq, value: 0}]}
  # Eq_VE_BTGT: VE_BTGT forbidden where REGION in {4,5} (OR expressed as one isin).
  - name: attribute_forbidden
    enable: true
    args: {crops: [VE_BTGT], conditions: [{column: REGION, op: in, value: [4, 5]}]}
  # Eq_VE_PLUIE: VE_PLUIE forbidden where REGION = 6 (part 1 of OR).
  - name: attribute_forbidden
    enable: true
    args: {crops: [VE_PLUIE], conditions: [{column: REGION, op: eq, value: 6}]}
  # Eq_VE_PLUIE: VE_PLUIE forbidden where ILE != 1 (part 2 of OR).
  - name: attribute_forbidden
    enable: true
    args: {crops: [VE_PLUIE], conditions: [{column: ILE, op: ne, value: 1}]}
```

Note: `Eq_MA_TO_CHOU_JA_LOC` (MA_TO_CHOU_JA outside Basse-Terre) and `Eq_AN_PA` (AN_PA in small farms) are deferred to the inventory (Task 9) — the first needs its exact GAMS condition re-read, the second is a per-farm-size rule not a plot attribute. Do NOT invent them here.

- [ ] **Step 2b: Read the two deferred equations to confirm they are non-trivial**

Run: `grep -nA1 "Eq_MA_TO_CHOU_JA_LOC\|Eq_AN_PA" old_code_gms_format_now_txt/MODELE.txt`
Record their exact bodies in the Task 9 inventory. If `Eq_MA_TO_CHOU_JA_LOC` is a plain `ILE`/`REGION` ban, you MAY add it as one more `attribute_forbidden` entry (with a citing comment); otherwise leave it deferred.

- [ ] **Step 3: Write the parity test on real data (island 3 = Marie-Galante)**

Add to `tests/test_guadeloupe_config.py`:

```python
def test_itk_bans_confine_regional_sugarcane():
    from pathlib import Path
    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    cfg = load_config(Path("case_studies/guadeloupe/config.yaml"))
    cfg["zone_filter"] = {"include": {"islands": [3]}}  # Marie-Galante only
    ds = build_dataset(cfg)
    eligible_crops = {crop for _, crop in ds.parameters["eligible_pairs"]}

    # On Marie-Galante (ILE=3): NGT/CGT/EGT/BT/SBT sugarcane systems must be absent...
    for crop in ["CS_NGT_NISM", "CS_CGT_NISM", "CS_EGT_NISM", "CS_BT_NISM", "CS_SBT_NISM"]:
        assert crop not in eligible_crops, crop
    # ...and irrigated sugarcane (Eq_CS_IRR) is disabled everywhere.
    for crop in ["CS_MG_IM", "CS_BT_IM"]:
        assert crop not in eligible_crops, crop
```

Confirm the parameters key holding eligible pairs (`eligible_pairs`) matches the pipeline; if the dataset exposes them elsewhere (e.g. `dataset.sets["PAIRS"]`), use that instead — check `build_dataset`'s return and adjust the accessor.

- [ ] **Step 4: Run the parity test**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_config.py::test_itk_bans_confine_regional_sugarcane -v`
Expected: PASS.

- [ ] **Step 5: Run the full config + eligibility test files (no regressions)**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_config.py tests/test_eligibility.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add case_studies/guadeloupe/config.yaml tests/test_guadeloupe_config.py
git commit -m "feat(parity): port GAMS geographic/soil/irrigation ITK bans to config"
```

---

## LOT 5 — Scenarios, cleanup, inventory, VIGILANCE

### Task 7: Author the ~22-scenario batch

**Files:**
- Rewrite: `case_studies/guadeloupe/scenarios.yaml`
- Test: `tests/test_scenario_overrides.py`

**Interfaces:**
- Consumes: `core.config.apply_overrides`, `expand_runs`, `load_config`; levers/constraints from Lots 1-2.

- [ ] **Step 1: Write the batch spec**

Rewrite `case_studies/guadeloupe/scenarios.yaml` keeping the existing header comment block and `_crop_groups` anchors, then replace `runs:` with the taxonomy below. Reuse anchors `*G_BANANE`, `*G_CANNE`, `*G_MARAICHAGE` for economic shocks; add a `bio_maraichage` anchor for bio variants and an `intensif` anchor.

Add near `_crop_groups`:

```yaml
  bio_maraichage: &G_BIO_MA
    [MA_PLBIO, MA_MOBIO, MA_BAG_BIO_I, MA_BAG_BIO_NI, MA_BRF_BIO_I, MA_BRF_BIO_NI,
     MA_PAI_BIO_I, MA_PAI_BIO_NI]
  intensif: &G_INTENSIF
    [BA_INT, BA_IRR, CS_BT_IM, CS_SBT_IM, CS_NGT_IM, CS_CGT_IM, CS_EGT_IM, CS_MG_IM]
```

`runs:` (each entry documented; the mechanisms in parentheses tie back to Lots 1-2):

```yaml
runs:
  # --- Contrôle ---
  - name: baseline
    description: "Config de référence inchangée."

  # --- Fuite en avant / intensif ---
  - name: intensif_max
    description: "Subventions canne + banane +30%, plafonds canne/banane levés."
    overrides:
      economic_overrides.subsidy_multipliers:
        - {crops: *G_CANNE, factor: 1.3}
        - {crops: *G_BANANE, factor: 1.3}
    set_args:
      - {label: cs_quota_max, args: {threshold: 100000000}}
      - {label: ba_quota_max, args: {threshold: 100000000}}
  - name: marge_pure
    description: "Retire tous les planchers/objectifs de production -- optimum marge pure."
    disable: [bc_prod_min, ig_prod_min, ma_prod_min, an_prod_min, plu_prod_min, me_prod_min,
              pn_prod_min, leg_prod_obj, fru_prod_obj, pat_surf_obj]
  - name: export_roi
    description: "Prix banane +20% & canne +20%, part intensif forcée >= 50% de sa filière."
    overrides:
      economic_overrides.price_multipliers:
        - {crops: *G_BANANE, factor: 1.2}
        - {crops: *G_CANNE, factor: 1.2}
    enable_add:  # see Step 2 note on adding a constraint from a scenario
      - name: crop_share_bound
        args: {label: intensif_min, numerator_crops: *G_INTENSIF, denominator_crops: *G_CANNE, sense: ge, share: 0.5}
  - name: plafonds_leves
    description: "Lève les plafonds de production canne et banane."
    set_args:
      - {label: cs_quota_max, args: {threshold: 100000000}}
      - {label: ba_quota_max, args: {threshold: 100000000}}

  # --- Agroécologie ---
  - name: agroeco_smart
    description: "Scénario SMART (matrice OTK + subvention compost MAE version SMART)."
    overrides: {data.scenario: SMART}
  - name: cap_intensif
    description: "Plafond dur d'intensification : intensif <= 20% de la filière canne."
    enable_add:
      - name: crop_share_bound
        args: {label: intensif_cap, numerator_crops: *G_INTENSIF, denominator_crops: *G_CANNE, sense: le, share: 0.2}
  - name: rotations_plus
    description: "Rotations renforcées : jachère >= 40% de la banane export."
    set_args:
      - {label: ba_ja, args: {ratio: 0.4}}
  - name: mae_compost_boost
    description: "SMART + subvention maraîchage +25% (proxy incitation agroécologique)."
    overrides:
      data.scenario: SMART
      economic_overrides.subsidy_multipliers:
        - {crops: *G_MARAICHAGE, factor: 1.25}

  # --- Bio ---
  - name: bio_incitatif
    description: "Subvention +50% sur les variantes maraîchage bio (incitation, pas de contrainte)."
    overrides:
      economic_overrides.subsidy_multipliers:
        - {crops: *G_BIO_MA, factor: 1.5}
  - name: bio_contraint
    description: "Part bio dure : >= 30% du maraîchage en variantes bio."
    enable_add:
      - name: crop_share_bound
        args: {label: bio_min, numerator_crops: *G_BIO_MA, denominator_crops: *G_MARAICHAGE, sense: ge, share: 0.3}
  - name: bio_fort
    description: "Part bio 50% + subvention bio +50%."
    overrides:
      economic_overrides.subsidy_multipliers:
        - {crops: *G_BIO_MA, factor: 1.5}
    enable_add:
      - name: crop_share_bound
        args: {label: bio_min, numerator_crops: *G_BIO_MA, denominator_crops: *G_MARAICHAGE, sense: ge, share: 0.5}

  # --- Mise en commun ---
  - name: mise_en_commun
    description: "Allocation poolée : désactive les plafonds de rotation par exploitation."
    disable: [an_agro_max_expl, ig_agro_max_expl]
  - name: commun_bio
    description: "Mise en commun + part bio 30% (coopérative agroécologique)."
    disable: [an_agro_max_expl, ig_agro_max_expl]
    enable_add:
      - name: crop_share_bound
        args: {label: bio_min, numerator_crops: *G_BIO_MA, denominator_crops: *G_MARAICHAGE, sense: ge, share: 0.3}

  # --- Chocs économiques ---
  - name: choc_prix_banane
    description: "Prix banane export -30%."
    overrides:
      economic_overrides.price_multipliers:
        - {crops: *G_BANANE, factor: 0.7}
  - name: choc_subv_canne
    description: "Subvention canne -50%."
    overrides:
      economic_overrides.subsidy_multipliers:
        - {crops: *G_CANNE, factor: 0.5}
  - name: choc_prix_maraichage
    description: "Prix maraîchage -30% (test du plancher légumes)."
    overrides:
      economic_overrides.price_multipliers:
        - {crops: *G_MARAICHAGE, factor: 0.7}
  - name: choc_petrole
    description: "Choc intrants/carburant : coûts variables +40% partout."
    overrides:
      economic_overrides.cost_multipliers:
        - {crops: *G_CANNE, factor: 1.4}
        - {crops: *G_BANANE, factor: 1.4}
        - {crops: *G_MARAICHAGE, factor: 1.4}

  # --- Chocs climatiques ---
  - name: cyclone
    description: "Cyclone : rendement banane & canne -40%."
    overrides:
      economic_overrides.yield_multipliers:
        - {crops: *G_BANANE, factor: 0.6}
        - {crops: *G_CANNE, factor: 0.6}
  - name: secheresse
    description: "Sécheresse : rendement -30% (canne/banane/maraîchage) + cultures irriguées bannies."
    overrides:
      economic_overrides.yield_multipliers:
        - {crops: *G_CANNE, factor: 0.7}
        - {crops: *G_BANANE, factor: 0.7}
        - {crops: *G_MARAICHAGE, factor: 0.7}
    enable_add:
      - name: forbid_crops
        args: {crops: [BA_IRR, ME, MA_ROTA]}
  - name: maladie_cercosporiose
    description: "Cercosporiose : rendement banane -50%."
    overrides:
      economic_overrides.yield_multipliers:
        - {crops: *G_BANANE, factor: 0.5}

  # --- Mixes politiques ---
  - name: transition_sous_cyclone
    description: "Agroécologie (SMART + bio 30%) sous cyclone (rdt banane/canne -40%)."
    overrides:
      data.scenario: SMART
      economic_overrides.yield_multipliers:
        - {crops: *G_BANANE, factor: 0.6}
        - {crops: *G_CANNE, factor: 0.6}
    enable_add:
      - name: crop_share_bound
        args: {label: bio_min, numerator_crops: *G_BIO_MA, denominator_crops: *G_MARAICHAGE, sense: ge, share: 0.3}
  - name: fuite_en_avant_secheresse
    description: "Intensif (subv canne/banane +30%, plafonds levés) frappé par la sécheresse."
    overrides:
      economic_overrides.subsidy_multipliers:
        - {crops: *G_CANNE, factor: 1.3}
        - {crops: *G_BANANE, factor: 1.3}
      economic_overrides.yield_multipliers:
        - {crops: *G_CANNE, factor: 0.7}
        - {crops: *G_BANANE, factor: 0.7}
    set_args:
      - {label: cs_quota_max, args: {threshold: 100000000}}
      - {label: ba_quota_max, args: {threshold: 100000000}}
  - name: bio_commun_choc
    description: "Bio 40% + mise en commun + prix maraîchage -20%."
    disable: [an_agro_max_expl, ig_agro_max_expl]
    overrides:
      economic_overrides.price_multipliers:
        - {crops: *G_MARAICHAGE, factor: 0.8}
    enable_add:
      - name: crop_share_bound
        args: {label: bio_min, numerator_crops: *G_BIO_MA, denominator_crops: *G_MARAICHAGE, sense: ge, share: 0.4}
  - name: resilience_agroeco
    description: "Bio 30% + rotations renforcées (jachère 40%) sous cyclone banane/canne -40%."
    overrides:
      economic_overrides.yield_multipliers:
        - {crops: *G_BANANE, factor: 0.6}
        - {crops: *G_CANNE, factor: 0.6}
    set_args:
      - {label: ba_ja, args: {ratio: 0.4}}
    enable_add:
      - name: crop_share_bound
        args: {label: bio_min, numerator_crops: *G_BIO_MA, denominator_crops: *G_MARAICHAGE, sense: ge, share: 0.3}
```

- [ ] **Step 2: Confirm `apply_overrides` supports adding a new constraint entry**

Several scenarios above use an `enable_add:` channel to append a brand-new constraint entry (e.g. `crop_share_bound`) that does not exist in `config.yaml`. Inspect `core/config.py::apply_overrides` (and the scenarios.yaml header contract). If an "add a new constraint entry" channel already exists under another name, use that exact key instead of `enable_add` and update every scenario above. If NO such channel exists, implement it:

Run: `.venv/Scripts/python -c "import inspect, core.config as c; print(inspect.getsource(c.apply_overrides))"`

If needed, extend `apply_overrides` so a run may append entries to a config list section (constraints). Add a focused test in `tests/test_scenario_overrides.py`:

```python
def test_apply_overrides_can_add_a_new_constraint_entry():
    from core.config import apply_overrides
    base = {"constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}]}
    run = {"name": "x", "enable_add": [
        {"name": "crop_share_bound",
         "args": {"label": "bio_min", "numerator_crops": ["MA_PLBIO"],
                  "denominator_crops": ["MA_PLBIO", "MA_ROTA"], "sense": "ge", "share": 0.3}}]}
    merged = apply_overrides(base, run)
    labels = [e["args"].get("label") for e in merged["constraints"] if e.get("enable")]
    assert "bio_min" in labels
```

Implement `enable_add` in `apply_overrides` to append each listed entry (with `enable: True`) to `config["constraints"]` on the deep copy. Keep the existing `overrides`/`enable`/`disable`/`set_args`/`matrix` channels unchanged. Update the `scenarios.yaml` header comment to document `enable_add`.

- [ ] **Step 3: Write the no-solve batch validation test**

Add to `tests/test_scenario_overrides.py`:

```python
def test_every_scenario_resolves_without_solving():
    from pathlib import Path
    from core.config import apply_overrides, expand_runs, load_config, resolve_enabled
    from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY
    import case_studies.guadeloupe.model  # noqa: F401 -- registers case constraints/rules

    base = load_config(Path("case_studies/guadeloupe/config.yaml"))
    runs = expand_runs((load_config(Path("case_studies/guadeloupe/scenarios.yaml")) or {}).get("runs") or [])
    assert len(runs) >= 20

    for run in runs:
        cfg = apply_overrides(base, run)
        # Exactly one objective enabled, and every enabled constraint/rule name is registered.
        objs = resolve_enabled(cfg["objectives"], OBJECTIVE_REGISTRY)
        assert len(objs) == 1, run.get("name")
        resolve_enabled(cfg["constraints"], CONSTRAINT_REGISTRY)  # raises KeyError if a name is unknown
        resolve_enabled(cfg["categorical_rules"], CATEGORICAL_RULE_REGISTRY)
```

- [ ] **Step 4: Run the validation test**

Run: `.venv/Scripts/python -m pytest tests/test_scenario_overrides.py -v`
Expected: PASS (all scenarios resolve; no solve). Fix any anchor/label typo the test surfaces.

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/scenarios.yaml tests/test_scenario_overrides.py core/config.py
git commit -m "feat(scenarios): ~22 political-trajectory scenarios + enable_add channel"
```

---

### Task 8: Config cleanup

**Files:**
- Modify: `case_studies/guadeloupe/config.yaml`

- [ ] **Step 1: Annotate the no-op tuber objective**

Find the `tub_prod_obj` entry (disabled, threshold 0). Replace its comment with an explicit note that it is a documented placeholder kept for GAMS traceability (`Eq_TUB_PROD_OBJ`), intentionally `enable: false` with threshold 0 (a no-op), and should not be enabled without a real target. Do not delete it (keeps parity traceability).

- [ ] **Step 2: Document the cross-file anchor duplication**

At the top of `scenarios.yaml`'s `_crop_groups` block, add a one-line comment: YAML anchors do not cross files, so these groups intentionally mirror `config.yaml crop_families`; keep the two in sync by hand.

- [ ] **Step 3: Verify config still loads and resolves**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_config.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add case_studies/guadeloupe/config.yaml case_studies/guadeloupe/scenarios.yaml
git commit -m "chore(config): annotate tub_prod_obj no-op and cross-file anchor duplication"
```

---

### Task 9: GAMS port inventory document

**Files:**
- Create: `docs/gams_port_inventory.md`

- [ ] **Step 1: Extract the two deferred equations' exact bodies**

Run: `grep -nA2 "Eq_MA_TO_CHOU_JA_LOC\|Eq_AN_PA" old_code_gms_format_now_txt/MODELE.txt`
Record verbatim in the inventory (below).

- [ ] **Step 2: Write the inventory**

Create `docs/gams_port_inventory.md` with a table: one row per GAMS equation from `MODELE.txt` (parcelle/culture/système/exploitation/région/guadeloupe/CF blocks), columns: **Équation | Rôle | Statut (porté / implicite / différé / écarté) | Localisation Python / raison**. Populate from this session's findings:
  - Numeric bounds (ALTI/PENTE/PLUVIO/SURF) → `eligibility_criteria` (porté).
  - Soil/risk/melon/friche rules → existing `categorical_rules` (porté).
  - **New this session**: all ITK geographic bans (CS/IG/BA/BC/AG/VE) → `attribute_forbidden`/`forbid_crops` (porté, Task 6).
  - Farm rotation/quota (`Eq_*_AGRO_MAX`, `Eq_BA_JA/ROTA`, `Eq_CS_GFA`) → `farm_area_*`/`cs_gfa_minimum_share` (porté; GFA disabled by design).
  - Territory floors/caps + objectives → `territory_production_bound` + objectives (porté).
  - `Eq_MO_MAX_Expl` → **différé** : `MO_Expl_init` requires the non-existent fine 2017 allocation (aggregate baseline crops have zero OTK/MO). Note the reactivation path (representative-crop approximation).
  - Whole **CF block** (`Eq_CF_*`, `Eq_CF_MIN`, `Eq_CF_T0..T8`) → **différé (Lot 4, séparé)** : data present, pipeline wiring pending.
  - `Eq_MA_TO_CHOU_JA_LOC`, `Eq_AN_PA` → **différé** (bodies recorded in Step 1; add to `attribute_forbidden` later if plot-attribute-expressible).
  - `Eq_*_SUPP` (aggregate-code bans) → **implicite** : aggregate codes carry zero economics, never chosen.

- [ ] **Step 3: Commit**

```bash
git add docs/gams_port_inventory.md
git commit -m "docs(parity): GAMS equation port inventory"
```

---

### Task 10: Update VIGILANCE.md

**Files:**
- Modify: `VIGILANCE.md`

- [ ] **Step 1: Resolve the REGION point**

Move the "REGION vs REGION_CODE potentiellement redondants" open point to the "Résolu" section, with the resolution: `data_parc["REGION"]` (int 1–7) = GAMS macro agro-region (now used by the ITK bans), distinct from `REGION_CODE` (R0–R27 petites-régions, melon rule only). Dated 2026-07-17.

- [ ] **Step 2: Log the deferrals**

Add two "Points ouverts" entries: (a) **Majeur — `Eq_MO_MAX_Expl` non porté** (donnée `MO_Expl_init` inexistante, cf. inventory); (b) **Majeur — bloc CF non câblé** (données présentes, pipeline à faire — Lot 4 séparé). Reference `docs/gams_port_inventory.md` and the spec.

- [ ] **Step 3: Commit**

```bash
git add VIGILANCE.md
git commit -m "docs(vigilance): resolve REGION ambiguity, log MO_MAX and CF deferrals"
```

---

## Final verification (no solve)

- [ ] Run the touched test files together:

Run: `.venv/Scripts/python -m pytest tests/test_economics.py tests/test_eligibility.py tests/test_guadeloupe_constraints.py tests/test_guadeloupe_config.py tests/test_scenario_overrides.py tests/test_guadeloupe_pipeline.py -v`
Expected: all PASS.

- [ ] Confirm no scenario/config change accidentally triggered a solve (there should be no `outputs/output_N/` created by tests).
- [ ] Leave running the actual batch (`scripts/run_scenarios.py`) to the user, per the no-solve constraint.
