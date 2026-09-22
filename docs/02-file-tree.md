# 02 — File tree

## The organising principle

Three layers, and the border between them is a rule, not a habit:

```
core/            generic       speaks ONLY of plots, crops, farms.
                               No mention of Guadeloupe, the RPG, ILE/REGION, GFA.
case_studies/    concrete      the data, the agronomic rules, the reporting of one territory.
apps/            read-only     what only READS finished runs. Takes no part in the solve.
```

**Direction of dependencies**: `case_studies/` imports `core/`, never the reverse. `apps/`
imports both; **nothing under `core/` or `case_studies/` may import `apps/`**.

Why this discipline: it is what makes the model portable to another territory (see
[05](05-new-case-study.md)), and what keeps the GAMS vocabulary where it anchors parity.

---

## Root

```
main.py                     one full solve. The entry point.
pyproject.toml              dependencies, pytest config (pythonpath = ["."])
CLAUDE.md                   instructions for the Claude Code agent
docs/                       this documentation (status board and roadmap in docs/status/)
context/                    external sources: original GAMS, article, technical report
core/  case_studies/  apps/  scripts/  tests/
clement/                    the thesis, the defence and the internship paperwork (French, closed)
data/                       NOT VERSIONED — input tables + GIS. Copy separately.
outputs/                    NOT VERSIONED — one folder per run
.golden/                    NOT VERSIONED — non-regression checksums
.mosaica_solve_history.json NOT VERSIONED — durations of past solves (local to the machine)
```

---

## `core/` — the generic solver

### `core/config.py` (~750 lines) — the central file

Everything that turns YAML into an executable configuration.

| Function | Role |
|---|---|
| `load_config` | read a YAML file |
| `resolve_enabled` | filter a config list on `enable: true` and resolve the names in a registry -> `(function, args)` |
| `load_batch_spec` | load a batch spec following its `include:` and resolving `{group: …}` |
| `expand_group_refs` / `resolve_crop_groups` | the crop-group catalogue |
| `compose_runs` | turn a spec into a list of runs (plan / flat list / crossed catalogues) |
| `expand_runs` | unfold a `matrix:` into a Cartesian product |
| `merge_run_specs` | compose policy ⊕ forcing ⊕ sweep without losing either |
| `apply_overrides` | apply a run's overrides on the reference config |
| `order_sweep_points` | reorder a sweep so the warm-start chain is valid |
| `scale_territorial_bounds` | scale absolute thresholds to a `zone_filter` |

### `core/case_study.py` — which case study

Resolves by **name** the three functions a case study must expose. It is what keeps the name
"guadeloupe" in a flag rather than in a dozen imports.

### `core/model/` — build a model (and nothing else)

| File | Role |
|---|---|
| `registry.py` | `@register_constraint(name)` / `@register_objective(name)` fill two dictionaries |
| `builder.py` | creates the `ConcreteModel`, the binary variable `Y[plot, crop]` on the eligible pairs, then runs every enabled builder. **Requires exactly one active objective.** |
| `model_inputs.py` | `ModelInputs`: the only object the builders see. Three required fields, everything else optional with an empty default |
| `constraints.py` (~520 lines) | the generic constraints: territorial, per-zone and per-farm bounds, crop shares, inertia |
| `objectives.py` | gross margin, and risk-adjusted margin (Markowitz) |

### `core/solve/` — solve a model

| File | Role |
|---|---|
| `solver.py` | `SolverFactory('appsi_highs')`, options from the config |
| `progress.py` | prints a duration range before, the real duration after; `SolveHistory` |
| `timing.py` | times data / build / solve separately |
| `warm_start.py` | applies a past allocation **and audits it** against the constraints |
| `shadow_prices.py` | marginal cost of each named constraint (duals of the LP relaxation) |

**`progress.py` must never run the solve in the background.** `appsi_highs` loads the model
inside `capture_output(capture_fd=True)`, which redirects the process's stdout/stderr
descriptors; any concurrent I/O from another thread corrupts that state and breaks **every
real run**. Spec: `superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md`.

### `core/data/`

| File | Role |
|---|---|
| `readers.py` | reads the GAMS `.set` and `.txt` files |
| `dataset.py` | the container `Dataset(sets, parameters, scalars)` |
| `eligibility.py` | boolean plot x crop mask: numeric bounds ∩ categorical rules |
| `zone_filter.py` | restrict to a sub-territory |
| `shapefile.py` | ESRI reader in **pure Python** — no GDAL, no geopandas |

### `core/reporting/`

| File | Role |
|---|---|
| `run_folder.py` | creates `outputs/output_N/` (or a named folder), reads an allocation back |
| `robustness.py` | worst case (Wald), retention, CV, max regret (Savage), viability (Starr) over a grid |

---

## `case_studies/guadeloupe/`

Organised by **role**, not by data type.

```
config.yaml                       drives everything: constraints, objectives, eligibility, data
crop_groups.yaml                  named crop groups, shared by the scenario files
scenarios.yaml                    scenario batch (flat list)
plan.yaml                         the prospective plan -- what actually runs
scenarios_policies.yaml           catalogue: what a public authority decides (P1..P10)
scenarios_forcings.yaml           catalogue: what climate and markets impose (F0..F11)
scenarios_pareto.yaml             catalogue: the epsilon-constraint sweeps
scenarios_calibration*.yaml       regenerate the reference calibration runs and their variants
scenarios_labor.yaml              two measurements of the per-farm labour budget
references.yaml                   the three reference runs, with the justification of each choice
legacy_names.py                   reads runs written before the 2026-09-22 English renaming
status/indicator_catalog.yaml     every indicator and the levels it is reported at
status/parameter_choices.yaml     parameters with several plausible values, and the choice made
```

### `pipeline/data_pipeline.py` (~580 lines)

Reads the tables, applies the `zone_filter`, computes the economics, the typology and the
eligibility mask. Returns a `Dataset`. **The only place that touches `data/`** (apart from the
map, which reads `data/gis/`).

### `domain/` — the science, one crop at a time

| Module | Content |
|---|---|
| `economics.py` | margin, sales, subsidies, costs, labour hours per ha and per crop |
| `environment.py` | nitrogen, phosphorus, potassium, GHG, TFI |
| `water.py` | water need |
| `soil_carbon.py` | soil organic carbon — **the only indicator that also depends on the plot** (through `TYPE_SOL`) |
| `resilience.py` | exposure: margin at risk, revenue concentration, loss under a shock |
| `agroecology.py` | AECM (a *sourced* definition of agroecology) and organic itineraries, reported **separately** |
| `rpest.py` | Tixier's fuzzy tree — **the only indicator that depends on the (plot, crop) pair** |
| `farm_typology.py` | base crop group -> `TYPE_EXPL` farm type -> risk aversion `AVERS` |
| `crop_families.py` | folds the 84 fine crops onto the 12 observed RPG groups |
| `crop_labels.py` | readable English names, translated from `DESCRIPTION_SETS.txt` |
| `zones.py` | island/region code normalisation and labels |
| `geometry.py` | joins the RPG plot layer to the synthetic ids `P1..Pn` |
| `itk.py` | technical-operation aggregation shared by the per-crop rates |

### `model/`

- `constraints.py` — the Guadeloupe-specific constraints (GFA, banana fallow, …).
- `model.py` — builds `ModelInputs` from the `Dataset` and calls
  `build_crop_allocation_model`. **Import the module, never the package**: `__init__.py` is
  empty, so `import case_studies.guadeloupe.model` registers no constraint.

### `reporting/`

- `indicators.py` (~760 lines) — applies the per-crop rates to the solved allocation.
- `calibration.py` (~410 lines) — scores the run against the 2017 observation (PAD, confusion matrix).
- `report.py` (~510 lines) — writes the run folder.
- `plots.py` — the PNGs.
- `status.py` — the status board (indicators x levels, constraints x crops, parameter choices, roadmap).

---

## `apps/dashboard/` — the Streamlit viewer

Lives **outside `case_studies/`** because it takes no part in the solve: it opens `outputs/`
folders and never builds a dataset, a model or a solver.

```
app.py                    Summary page (home)
pages/1_Run_detail.py     2_Comparison.py   3_Calibration.py
pages/4_Prospective.py    5_Map.py          6_Pareto.py      7_Status.py
loaders.py                reading run folders (through legacy_names)
comparison.py             (~770 lines) fact tables, indicator directions, composite score
synthesis.py              the alerts specific to one run
config_diff.py            what two runs ASKED differently
allocation_diff.py        what that MOVED on the ground
prospective.py            the policy x forcing grid
pareto.py                 fronts, domination, marginal cost
maps.py                   map rendering
references.py             loading the reference runs
```

---

## `scripts/`

**Generic** (work on any case study, through `--case-study`):

| Script | Role |
|---|---|
| `run_scenarios.py` | scenario batch |
| `profile_solver.py` | per-phase timing on a sub-zone |
| `display_datasets.py` | inspect the dataset |
| `golden_snapshot.py` | numeric non-regression (~680 checksums) |
| `repair_allocation.py` | repair an allocation to make it a warm-start seed |
| `audit_warm_start_seed.py` | check whether a past allocation would be accepted as a seed, without solving |
| `_common.py` | shared paths and formatting — **no project import**, so `--help` stays instant |

**Guadeloupe-specific** (they import `domain/` or `reporting/`, by nature):
`build_reference_state.py`, `compare_to_reference.py`, `evaluate_calibration.py`,
`pad_all_scales.py`, `check_references.py`, `check_scenario_feasibility.py`,
`build_status_board.py`, `build_data_templates.py`, `validate_data_workbook.py`.

---

## `tests/`

~60 files, **data-free by choice**: they build tiny configs by hand (see
`tests/test_guadeloupe_constraints.py` for the style). A handful build the real dataset and
solve — they are the 29 minutes of the full suite.

What this choice implies: **the tests do not guard the solve**. `golden_snapshot.py` covers the
pipeline and the indicators up to the allocation, `check_references.py` covers the results of
the reference runs. Nothing else watches the resolution.

---

## `data/` (not versioned)

```
data/sets/      the GAMS .set files (CULT_2017.set, REG_PARC_2017.set, …)
data/tables/    the .txt files (Data_Parc, Data_OTK, Data_Cult, Data_Sol, indice_H/…)
data/gis/       the GIS layers, including 01_RPG 2017/ (the real plot layer)
```

There is **no coordinate** in `data/tables/`: spatial reporting aggregates by
`ILE`/`REGION`/`COMMUNE`. Geometry only comes from `data/gis/`, joined through a rebuilt join
(see [04](04-vigilance.md#carte)). What each table holds, where it comes from and who may see
it: [data catalogue](data/README.md).

---

## `context/` (external sources)

```
context/gams/                            the original GAMS -- SOURCE OF TRUTH for parity
context/Chopin et al 2015 pour Hal.pdf   the reference article
context/Rapport technique … .docx        variable dictionary (not versioned)
context/SORTIES/                         outputs of the real GAMS run (used since 2026-09-08)
```

In `context/gams/`: `MODELE.txt` (the equations), `OPTIMISATION.txt` (the computations),
`ENTREES.txt` (the derivations), `SETS.txt` (the sets), `DESCRIPTION_SETS.txt` (the labels).
**When in doubt about a constraint or a coefficient, that is where it is settled.**

---

## `docs/`

```
README.md                      index
01-usage.md … 05-new-case-study.md
glossary.md                    French source terms and their English names
status/                        STATUS.md (generated) and roadmap.yaml
data/                          data catalogue, access levels, fill-in workbooks
gams_port_inventory.md         state of the port, equation by equation
superpowers/specs/             one spec per work item -- the WHY of each decision
archives/journal-vigilance.md  the full investigation log (French)
```
