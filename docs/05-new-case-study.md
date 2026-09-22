# 05 — Create a new case study

## Portability verdict

**The core is portable; the case study has to be rewritten.** That is the expected result — an
allocation model cannot guess a territory's agronomy — but the border is clean and checkable.

| | State | Detail |
|---|---|---|
| `core/` | **reusable as is** | Checked: no mention of Guadeloupe, the RPG, `ILE`/`REGION`/`COMMUNE`/`GFA`. It only speaks of plots, crops, farms, zones and per-hectare rates. `farm_restricted_surface_ha` is the generic name for "area under a land-tenure scheme" — GFA is its Guadeloupe instance. |
| Entry points | **parameterised** | `main.py`, `run_scenarios.py`, `profile_solver.py`, `display_datasets.py` take `--case-study`. The name resolves in `core/case_study.py`, or from `$MOSAICA_CASE_STUDY`. |
| The dashboard | **partly** | It reads generic recaps, but imports `case_studies.guadeloupe.domain` for labels and geometry, and `legacy_names` for old runs. To generalise when a second case exists, not before. |
| Calibration scripts | **specific by nature** | `build_reference_state.py`, `compare_to_reference.py`, `evaluate_calibration.py`, `pad_all_scales.py` encode Chopin's method against the 12 RPG groups. Another territory has its own observed groups. |
| `case_studies/guadeloupe/` | **to rewrite** | That is the point. |

**What honestly remains for a second case study**: generalise the dashboard labels, and decide
whether the calibration method factors out (it is generic in principle — PAD, confusion matrix
— but not in its vocabulary). Both are on the [roadmap](status/roadmap.yaml) as
`second-case-study`.

---

## The contract

A case study is a package under `case_studies/<name>/` exposing **exactly three functions** and
a config file:

```
case_studies/<name>/
  config.yaml                      the reference config
  pipeline/data_pipeline.py        build_dataset(config) -> Dataset
  model/model.py                   build_model(dataset, config) -> pyo.ConcreteModel
  reporting/report.py              generate_report(dataset, config, model, results, duration,
                                                   *, outputs_root) -> Path
```

Nothing else is called from outside. `core/case_study.py` resolves these three entry points by
name, and `available()` lists what is on disk.

**`model/model.py` is imported as a MODULE, never as a package**: `__init__.py` is empty, so
importing the package runs no decorator and registers no constraint.

---

## Step by step

### 1. The skeleton

```bash
mkdir -p case_studies/my_territory/{pipeline,model,domain,reporting}
# an empty __init__.py in each
```

Check right away that the resolver sees it:

```bash
python -c "from core.case_study import available; print(available())"
# -> ['guadeloupe', 'my_territory']   (as soon as config.yaml exists)
```

### 2. `pipeline/data_pipeline.py` -> a `Dataset`

The only module that touches your data. It must produce a `Dataset(sets, parameters,
scalars)` whose `parameters` contain at least:

| Key | Content |
|---|---|
| `plot_data` | DataFrame indexed by plot, with at least `SURF_HA` |
| `crop_margin_per_ha` | Series crop -> margin EUR/ha |
| `eligible_pairs` | list of `(plot, crop)` — **it is what bounds the size of the MILP** |

Then, depending on what your constraints use: `farm_plots`, `farm_surface_ha`, `crop_yield`,
`crop_variance_per_ha`, `farm_risk_aversion`, `crop_labor_hours_per_ha`,
`farm_labor_capacity_hours`, and one per-hectare, per-crop rate for each indicator.

**Reuse `core/data/`**: `readers.py` (GAMS `.set` / `.txt` formats), `eligibility.py` (boolean
mask), `zone_filter.py`. If your data is in another format, only the reader changes. Describe
each input table in a data catalogue (see [docs/data](data/README.md)): its source, licence and
access level are then known before anyone asks.

**`eligible_pairs` is tractability lever no. 1.** Creating a binary variable only for pairs
that are really possible is what makes the problem solvable: 84 crops x 24 734 plots = 2.1 M
theoretical pairs, brought down to ~309 000 by eligibility.

### 3. `domain/` -> the science, one crop at a time

Pure functions producing `crop -> rate/ha` series. No required structure: it is your agronomy.
The split worth copying is Guadeloupe's — one module per indicator family (`economics`,
`environment`, `water`, `soil_carbon`), testable without data.

**An indicator that depends on the PLOT and not only on the crop does not go through a per-crop
rate.** Two cases met: soil carbon (depends on the soil type) and water withdrawal (only
irrigable plots draw). For the second, the generic answer exists: `ModelInputs.plot_weights`.

### 4. `model/model.py` -> assemble `ModelInputs`

The shortest of the three. It does three things:

```python
from case_studies.my_territory.model import constraints as _c  # noqa: F401 (registers)
from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs

def build_model(dataset, config):
    inputs = ModelInputs(
        plot_surface_ha=dataset.parameters["plot_data"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["crop_margin_per_ha"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        # ... and whatever your constraints read
        crop_indicator_rates={"nitrogen": {...}, "water": {...}},
        plot_zones={"regions": {...}, "farms": {...}},
        plot_weights={"irrigable": {...}},
    )
    return build_crop_allocation_model(inputs, config)
```

**This is where the local vocabulary is translated into the generic one**: your
`area_under_lease` becomes `farm_restricted_surface_ha`, your communes become an entry of
`plot_zones`. Keep that translation here and nowhere else — it is what holds the
`core/` <-> `case_studies/` border.

The `# noqa: F401` import of `constraints` **is not decorative**: without it none of your
constraints is registered and any config naming them raises `KeyError`.

### 5. `config.yaml`

Minimal structure:

```yaml
data: {year: "2020", scenario: BASE}
solver: {name: appsi_highs, args: {time_limit: 3600, mip_rel_gap: 0.01}}
labor: {hours_per_fte: 1607, cost_per_hour: 0}

crop_families:
  cereals: [WHEAT, BARLEY]

eligibility_criteria: [...]     # numeric bounds
categorical_rules: [...]        # categorical bans

constraints:
  - name: at_most_one_crop_per_plot
    enable: true
    args: {}
  - name: territory_indicator_bound
    enable: true
    args: {label: nitrogen_cap, indicator: nitrogen, sense: le, threshold: 1000000}

objectives:                     # EXACTLY one active
  - name: maximize_gross_margin
    enable: true
    args: {}
```

**Comment every disabled entry with its reason.** It is the repository's convention and it has
real value: several Guadeloupe `enable: false` are correct and tested, but cause a genuine
infeasibility on the data.

### 6. `reporting/report.py`

`generate_report(dataset, config, model, results, duration, *, outputs_root) -> Path`. It
decodes the solution, computes the indicators and writes the run folder. Reuse
`core/reporting/run_folder.py` to create the folder and read an allocation back.

**The minimal `recap.json` contract** — it is what the dashboard and the batch scripts read:

```json
{
  "run_name": "...", "run_policy": null, "run_forcing": null, "run_sweep": null,
  "termination_condition": "optimal", "solve_duration_seconds": 209.4,
  "solver": {...}, "constraints": [...],
  "economics": {"output": {"total_gross_margin": 0, "total_fte": 0, ...}},
  "environment": {"output": {"total_nitrogen": 0, ...}},
  "output": {"total_surface_ha": 0}
}
```

`constraints` is what lets `bound_indicators` detect after the fact the indicators fixed by a
constraint — trap no. 1 of [04](04-vigilance.md#a1). Do not skip it.

### 7. Run it

```bash
python scripts/display_datasets.py --case-study my_territory     # does the data come out?
python scripts/profile_solver.py --case-study my_territory       # does it build and solve?
python main.py --case-study my_territory                         # a full run
python scripts/run_scenarios.py --case-study my_territory \
       --scenarios case_studies/my_territory/scenarios.yaml --dry-run
```

Or set the default once and for all:

```powershell
$env:MOSAICA_CASE_STUDY = "my_territory"
```

---

## What to plan from the start

Five decisions that cost dearly when taken late — each one a trap met here.

**1. An external source for every threshold.** A ceiling or a floor fitted **on the observed
land use** produces a zero PAD by construction: it calibrates nothing, it forces. The two
deviations kept in Guadeloupe hold because they are sourced elsewhere (original GAMS parameter,
national agricultural statistics) and the result does not depend on the exact value — a
**plateau** in the threshold sweep proves it. That is the test that tells a correction from a
fit. Record each choice in a `parameter_choices.yaml` like
`case_studies/guadeloupe/status/parameter_choices.yaml`.

**2. Crops that are really distinct.** Two crops equal on every parameter the model reads are
interchangeable: a branch-and-bound disaster, and any share constraint telling them apart is met
**by mere relabelling, at zero cost**. Run `check_scenario_feasibility.py` on the first dataset
— it reports them.

**3. A state variable if a stock is at stake.** The model is **static**: it can liquidate a herd
for free and redeploy the livestock farmer's labour elsewhere. If your territory has stocks
(herds, perennial plantations, machinery), no area constraint represents them properly.
`baseline_inertia_min` is a crude proxy.

**4. The granularity of the observed baseline.** If your history only encodes the crop at an
aggregate level, every "input" indicator rests on an **assumption** of representative variant —
and that assumption contaminates the labour ceiling, hence the optimum. Make it configurable and
documented from the start.

**5. The size of the problem.** Beyond ~309 000 binaries, HiGHS no longer finds a good incumbent
unaided and a solve can return a **provably wrong** result (see
[04](04-vigilance.md#tractabilite)). Watch `eligible_pairs` and plan the warm start.

---

## Once it runs

```bash
python scripts/golden_snapshot.py --write    # freeze the behaviour, then --check after any refactor
```

Then write, in order of return:

1. **data-free tests** for your constraints (a tiny hand-built config);
2. a **`references.yaml`** with your reference runs and the justification of each choice,
   guarded by `check_references.py`;
3. your own section in [04 — Vigilance](04-vigilance.md), as you discover what your data does
   not say. It is the most useful document of the repository.
