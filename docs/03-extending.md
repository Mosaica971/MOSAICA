# 03 — Extending the model

## The central idea: the config-driven registry

Constraints, objectives, eligibility criteria and categorical rules are **Python functions
registered under a name**, then selected and parameterised **entirely from the YAML**.
Practical consequence: *to change the model's behaviour, you usually edit the config, not the
code.*

```
@register_constraint("my_thing")   ->   CONSTRAINT_REGISTRY["my_thing"]
                                              |
config.yaml:  - name: my_thing          resolve_enabled() keeps enable: true,
                enable: true            resolves the name, returns (function, args)
                args: {threshold: 42}         |
                                        builder.py calls function(model, inputs, **args)
```

**Trap no. 1: a builder that is not imported is not registered.** Decorators only run when
their module is imported. `core/model/builder.py` imports the generic builders;
`case_studies/guadeloupe/model/model.py` also imports the case study's. If your module is
imported nowhere on the path to `build_crop_allocation_model`, the config naming it raises
`KeyError: Unknown component`.

---

## Add a constraint

**First: is it really a new constraint?** The existing generic builders cover a lot, from the
YAML alone:

| Builder | What it expresses |
|---|---|
| `territory_production_bound` | ceiling/floor on a **physical production** (t, or ha with `use_yield: false`) |
| `territory_indicator_bound` | ceiling/floor on **any per-hectare rate** the case study exposes — nitrogen, TFI, GHG, water, carbon, hours, subsidy euros |
| `zone_indicator_bound` | the same bound **per island / region / watershed / farm** (`threshold_per_ha` x the zone's hectares = the nitrates-directive form) |
| `crop_share_bound` | the share of one crop group within another |
| `farm_area_share_max` | a maximum area share per farm |
| `farm_labor_hours_max` | the per-farm labour ceiling |
| `baseline_inertia_min` | a share of the area that stays in its 2017 use |

A nitrogen ceiling, a public-spending envelope and an employment floor are **the same
builder** with a different `indicator:`. Writing code for that is a mistake.

### If it really is new

```python
# core/model/constraints.py  (or case_studies/<case>/model/constraints.py if case-specific)
@register_constraint("thing_ceiling")
def build_thing_ceiling(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,        # REQUIRED: this is how a scenario targets this entry
    crops: list[str],
    threshold: float,
    **_args,           # REQUIRED: absorbs any extra key the config may carry
) -> None:
    """One line saying what is bounded, in which unit."""
    total = sum(
        model.Y[plot, crop] * inputs.plot_surface_ha[plot]
        for plot, crop in inputs.eligible_pairs
        if crop in set(crops)
    )
    # TRIVIAL-BOOLEAN TRAP: sum() over zero pairs returns a Python 0, not a Pyomo
    # expression. Comparing it gives a bare bool, which Pyomo REJECTS.
    if isinstance(total, (int, float)):
        setattr(model, label, pyo.Constraint(
            expr=pyo.Constraint.Feasible if total <= threshold else pyo.Constraint.Infeasible))
        return
    setattr(model, label, pyo.Constraint(expr=total <= threshold))
```

```yaml
# config.yaml
constraints:
  # Eq_THING_MAX (MODELE.txt:123): what it ports and why it is on.
  - name: thing_ceiling
    enable: true
    args: {label: thing_max, crops: [CS, BA], threshold: 1000}
```

**Four rules:**

1. **Always a `label:`.** It is the key a scenario's `enable`/`disable`/`set_args` use to target
   *one* entry. Without a label they fall back on the `name`, which may be shared by six
   entries. When the entry ports a GAMS equation, name the label after it
   (`bc_quota_max` for `Eq_BC_QUOTA_MAX`): the status board then shows the provenance.
2. **Always `**_args`.** Otherwise any extra key in the config breaks the build.
3. **The trivial-boolean guard** whenever the set of terms can be empty.
4. **A comment above the config entry** naming the GAMS equation and why it is on or off.

**One test, data-free.** That is the repository's style (`tests/test_guadeloupe_constraints.py`):

```python
def test_thing_ceiling_bounds_the_area():
    inputs = ModelInputs(
        plot_surface_ha={"P1": 10.0, "P2": 5.0},
        crop_margin_per_ha={"CS": 100.0},
        eligible_pairs=[("P1", "CS"), ("P2", "CS")],
    )
    model = build_crop_allocation_model(inputs, {
        "constraints": [{"name": "thing_ceiling", "enable": True,
                         "args": {"label": "thing_max", "crops": ["CS"], "threshold": 12.0}}],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    })
    assert hasattr(model, "thing_max")
```

---

## Add an objective

Same mechanism, registry `OBJECTIVE_REGISTRY`, in `core/model/objectives.py`.

**Exactly one objective must be active** — `build_crop_allocation_model` raises otherwise. A
scenario that changes objective must therefore `enable` the new one **and** `disable` the old
one in the same block.

**A run that changes objective is not comparable with the others on the `objective`
column**: it is not the same function. Compare on the physical and economic columns (gross
margin, FTE, nitrogen, TFI…), which are computed identically whatever the objective.

---

## Add an eligibility rule

Eligibility is a boolean plot x crop matrix: the **numeric bounds** (altitude, slope,
rainfall, size) intersected with the **categorical rules**.

```python
# core/data/eligibility.py
@register_categorical_rule("my_rule")
def rule_my_rule(
    plot_attributes: pd.DataFrame, *, crops: list[str], column: str, **_args
) -> tuple[list[str], pd.Series]:
    """Returns (the crops to forbid, the condition on the plots)."""
    return crops, plot_attributes[column] > 42
```

A rule receives the plot table and returns `(crops, condition)`; `forbid_where` then clears
those crops on the matching plots.

**Each rule forbids its own subset, and the mask keeps the UNION of what is forbidden.** So an
`attribute_forbidden` entry ANDs its conditions, and an **OR is written as several entries**.
That is exactly how the melon soil/island ban is written in `config.yaml`. Before writing a new
rule, check whether `attribute_forbidden` (conditions `eq/ne/in/not_in/lt/le/gt/ge`) says it
already: a rule whose name states what it forbids is easier to read than a dedicated one.

A rule enabled in `config.yaml` is lifted in a scenario by **disabling its label** — that is
how a scenario reopens a ban.

---

## Add a crop

The most intrusive, because the data rules. In order:

1. **`data/sets/CULT_2017.set`** — the crop code. Without it, nothing exists.
2. **`data/tables/`** — a row in every crop-indexed table: `Prix_Cult_CF_<scenario>`,
   `Rdt_Cult_CF_<scenario>`, `Data_Cult` (agronomic bounds), `Matrice_OTK_Cult_<scenario>` (the
   technical itinerary, from which nitrogen, TFI, GHG, hours… come), `Var_Rdt_Cult`. The fill-in
   workbooks of the [data catalogue](data/README.md) list the expected columns.
3. **`domain/crop_families.py`** — which RPG group the crop folds onto. Without it, calibration
   cannot compare it with the observation and `baseline_inertia_min` ignores it.
4. **`domain/crop_labels.py`** — the readable name for the figures.
5. **`config.yaml`** — add it to the relevant `crop_families`, and to the categorical rules that
   must constrain it.
6. **`crop_groups.yaml`** — if it belongs to a scenario group (`food_crops`, `organic_…`).

**Then check.** A crop added without a distinct itinerary is a **symmetric copy** — the worst
case for branch-and-bound, and a modelling trap (a share constraint telling apart crops the
data does not tell apart is met by mere relabelling, at zero cost). The detector exists:

```bash
python scripts/check_scenario_feasibility.py --scenarios <file>   # reports symmetric groups
python scripts/golden_snapshot.py --check                         # numeric drift elsewhere
```

See [04 — Vigilance](04-vigilance.md#karusmart): 25 crops of the dataset are exactly that case.

---

## Add an indicator

An indicator crosses five layers. Skipping the last two is the classic mistake.

1. **The per-crop computation** — a `domain/` module (`environment.py`, `water.py`…) producing a
   series `crop -> rate/ha`.
2. **The pipeline** — `data_pipeline.build_dataset` stores that series in
   `dataset.parameters["crop_<thing>_per_ha"]`.
3. **The reporting** — `reporting/indicators.py` applies it to the allocation (the `rate()`
   helper of `compute_facts_table`), and the total lands in the recap.
4. **Make it boundable** — add the entry to `_INDICATOR_PARAMETERS` in
   `case_studies/<case>/model/model.py`. **This is what lets a scenario write a
   `territory_indicator_bound` on it, without another line of code.**
5. **Declare it** — an entry in `case_studies/guadeloupe/status/indicator_catalog.yaml` (its
   unit, family, aggregation class, the levels it is reported at). `tests/test_status_board.py`
   fails if the dashboard offers an indicator the catalogue does not know.

**To expose it to the dashboard's composite score, TWO additions are needed**:
`INDICATOR_DIRECTION` in `apps/dashboard/comparison.py` (the direction: cost or benefit) **and**
a label in one of that module's family dictionaries (`ECON_INDICATORS`, `ENV_INDICATORS`, …),
which is what puts it in the selector. The first alone wires nothing.

**Two unit traps, both actually met**:
- a per-crop rate cannot carry a dependence on the **plot**. Water is only drawn on irrigable
  plots: without `plot_weight: irrigable`, a bound counts 56 Mm³ where the report says 35.
  Carbon has the same problem (the balance depends on the soil type).
- **the threshold must be stated in the constraint's own terms, not read off `recap.json`.**

---

## Change solver

```yaml
# config.yaml
solver:
  name: appsi_highs        # Pyomo SolverFactory name
  args:                    # passed as is to the solver
    time_limit: 10800
    mip_rel_gap: 0.01
```

For another solver (CBC, Gurobi…), changing `name` is enough *in principle* —
`core/solve/solver.py` only does `SolverFactory(name)`. Three measured caveats:

- **the `warm_start`** maps onto Pyomo's `warmstart` kwarg, which not every solver supports the
  same way;
- **the file-descriptor conflict** described in [02](02-file-tree.md) is specific to
  `appsi_highs`, but the rule "do not run the solve in the background" remains the safest;
- the **persistent APPSI interface** was tested then **reverted**: the ~25 % gain measured on one
  island does not hold at full scale.

`solver.args.time_limit` is the lever to raise for a hard scenario (an orchard-area floor,
stacked ceilings). A solve that hits the limit returns a **provably sub-optimal incumbent**:
check it before interpreting (see [04](04-vigilance.md#tractabilite)).

---

## Write a scenario

A scenario is a set of **overrides** on `config.yaml`. Four channels, and only one can create:

| Channel | What it does |
|---|---|
| `overrides: {dotted.path: value}` | replaces a scalar value / a dict / a whole key |
| `enable: [token]` / `disable: [token]` | flips `enable:` on the entries matching the **label** (failing that, the `name`) |
| `set_args: [{label, args}]` | merges arguments into the entry carrying that label |
| `enable_add: [{name, section, args}]` | **adds an entry that does not exist** in the base config |

`set_args` can only patch an entry **already declared**. That is why `nitrogen_max` and
`employment_min` live as `enable: false` in `config.yaml`: empty shells that give the sweeps
something to hold.

**An asymmetry to know**: `apply_overrides` always applies `enable` **before** `disable`. A token
disabled by either spec stays disabled whatever the other says. A forcing that must re-enable
what a policy switched off has to go through `enable_add`.

**Policy x forcing composition**: when both write the same dotted path and both values are
**lists**, they are **concatenated** (which is what the multiplier lists want). Everything else
is a replacement, the forcing winning.

**Always validate before paying for hours of computation:**

```bash
python scripts/run_scenarios.py --scenarios <file> --dry-run
python scripts/check_scenario_feasibility.py --scenarios <file>
```

---

## Before committing

```bash
python -m pytest tests/<the files touched>.py          # fast
python scripts/golden_snapshot.py --check              # if pipeline/domain/core.data/indicators
python scripts/check_references.py                     # if the model or the config moved
python scripts/build_status_board.py                   # if config.yaml or a catalogue moved
python -m pytest                                       # final check (~29 min)
```

And **read the comment before flipping an `enable:`**. Several `config.yaml` entries are
disabled on purpose, correct and tested, but causing a real (and GAMS-consistent)
infeasibility on the 2017 data. The reason is written right above.

When a renamed identifier or recap key is involved, add its old name to
`case_studies/guadeloupe/legacy_names.py`, so the runs already on disk keep reading.
