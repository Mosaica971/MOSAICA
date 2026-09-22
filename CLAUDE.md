# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Human-facing documentation is `docs/`** — five numbered files: how to run it (01), the file
> tree (02), how to extend it (03), **the traps to know before quoting any number (04)**, and how
> to port the model to another territory (05); plus `docs/status/` (what is implemented) and
> `docs/glossary.md`. `docs/archives/journal-vigilance.md` holds the full investigation log (in
> French). Keep `docs/04-vigilance.md` in sync when a new limitation is found: it is the file a
> newcomer reads, and this one is not.

> **Current workstream (since 2026-09-22): post-thesis.** Read
> `docs/superpowers/specs/2026-09-22-post-thesis-maelia-data-english-design.md` first. Done: the
> English renaming (code, config, scenarios, recap keys, dashboard, numbered docs) and the status
> board, and the data catalogue with access levels and fill-in workbooks (`docs/data/`). Postponed
> until the MAELIA training: the two MAELIA couplings. What is left is in
> **`docs/status/roadmap.yaml`**, which replaced `docs/TODO.md`. The thesis-era "no new solve"
> rule is **lifted** — but the standing preference on full solves below still holds.
>
> **The thesis (mémoire) is closed** (submitted 26/08, defended 1-4 Sept) and lives in
> `clement/memoire/`, next to `clement/soutenance/` and `clement/student_context/`. It stays in
> **French**, like its corpus (`clement/memoire/corpus/`, 491 items, checked by
> `audit_corpus.py`). To reopen it (internal technical note, article), read
> `clement/memoire/ETAT.md` first. Its generator `build_chiffres.py` reads the runs' `recap.json`
> directly, with their original French keys, on purpose.

## Language and names

**Everything in the repository is in English** except `clement/` and the dated specs/journal
written before 2026-09-22. `docs/glossary.md` fixes each translation (azote -> nitrogen,
GES -> GHG, ETP -> FTE, IFT -> TFI, MAE -> AECM, `_cult` suffix -> `crop_` prefix…). **GAMS
identifiers, data file names and data column names stay verbatim** (`Eq_BC_QUOTA_MAX`,
`Rdt_Cult`, `Data_Parc_Gwad_2017.txt`, `PENTE`, `RISQUE_CLD`): they anchor parity and name files
the project does not own.

**Runs written before 2026-09-22 carry French names** (`total_azote`, `mo_max_expl`,
`P4_statu_quo`, `etp_by_region_output.csv`, folders `calib_retenu/`, `p8_transition_agroecologique_*`).
`outputs/` is **never rewritten**: `case_studies/guadeloupe/legacy_names.py` renames on read, and
every reader goes through it (`apps/dashboard/loaders.load_recap / load_config_used / load_csv`).
When you rename a persisted name, add the old one to `LEGACY_NAMES`; `tests/test_legacy_names.py`
fails if an entry maps a name onto itself — **never run a bulk rename over that file**.
`references.yaml` accepts `run: [new_name, legacy_folder]`.

## What this is

Python/Pyomo rewrite of **MOSAICA**, a crop-allocation optimization model originally written in
GAMS. It solves a large binary MILP: assign each agricultural plot in Guadeloupe to at most one
crop so as to maximize the risk-adjusted gross margin, subject to agronomic eligibility, per-farm
rules, and territory-wide production quotas. The original GAMS source lives (as `.txt`) in
`context/gams/` and is the **reference for parity** — when a constraint or coefficient is in
question, that directory is the source of truth (`MODELE.txt`, `OPTIMISATION.txt`, `ENTREES.txt`,
`SETS.txt`, etc.). `context/SORTIES/` holds outputs of the real GAMS run (used since 2026-09-08).

Deviations from GAMS are deliberate and documented in config comments and `docs/04-vigilance.md`.

## Commands

The venv is at `.venv/`. Run tests with pytest (config in `pyproject.toml`,
`pythonpath = ["."]` so imports resolve from the repo root):

```bash
.venv/Scripts/python -m pytest tests/test_readers.py # one file
.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py::test_cs_gfa_minimum_share_constraint_only_applies_to_farms_with_gfa_surface  # one test
.venv/Scripts/python -m pytest                       # full suite — SLOW (~29 min)
```

The **full suite is slow** (~29 min: a few tests build the real dataset and run real HiGHS
solves). During iteration, run only the file(s) you're touching; save the full run for a final
check. The fast subset (everything except `test_main`, `test_guadeloupe_model`,
`test_model_solver`, `test_display_datasets`, `test_profile_solver`) runs in ~75 s.

Full end-to-end solve (builds data → model → solves with HiGHS → writes `outputs/output_N/`):

```bash
.venv/Scripts/python main.py
.venv/Scripts/python main.py --case-study guadeloupe   # or $MOSAICA_CASE_STUDY
```

**Which case study runs is resolved by name** (`core/case_study.py`), not wired into imports:
`main.py`, `run_scenarios.py`, `profile_solver.py` and `display_datasets.py` all take
`--case-study`. A case study is a package under `case_studies/` exposing exactly three functions
— `build_dataset(config)`, `build_model(dataset, config)`, `generate_report(...)` — plus its
`config.yaml`. `core/` speaks no Guadeloupe and that is checked; the calibration scripts
(`build_reference_state`, `evaluate_calibration`, `compare_to_reference`, `pad_all_scales`) are
case-study-specific by nature. See `docs/05-new-case-study.md`.

**Do NOT run `main.py` casually.** The full solve is slow (~30–60 min on the real dataset in the
calibration configuration, 2–3 h in the prospective one, with large run-to-run variance; the
bottleneck is the branch-and-bound search itself — see `docs/04-vigilance.md` B.1). Per standing
user preference, only run the full solve at end-of-day and only when asked; iterate with targeted
pytest instead. For scaled-down experiments use `zone_filter` in `config.yaml` (restrict to one
island/region/farm, with `scale_territorial_bounds: true`) or `scripts/profile_solver.py`.

Scenario batch (same pipeline as `main.py`, one `output_N/` per scenario + a batch summary;
spec in `case_studies/guadeloupe/scenarios.yaml`): `.venv/Scripts/python scripts/run_scenarios.py`.
Same caveat as `main.py` — real solves, don't run casually.

**Prospective scenarios are four files: three catalogues and one plan.** The catalogues declare
what exists — `scenarios_policies.yaml` (`policies:`, what a public authority decides),
`scenarios_forcings.yaml` (`forcings:`, what climate and markets impose),
`scenarios_pareto.yaml` (`sweeps:`, the ε-constraint fronts). **`plan.yaml` is what actually
runs**, and the only file to edit to change a batch: it `include:`s the three and then names,
per policy, which forcings it goes through and which fronts are traced under it.

```yaml
scenarios:
  P1_full_deregulation:                            # the policy alone, unforced
  P4_status_quo: [F0_nominal, F9_systemic_crisis]  # shorthand for `forcings:`
  P8_agroecological_transition:
    forcings: [F0_nominal, F9_systemic_crisis]
    sweeps: [pareto_nitrogen, {name: pareto_nitrogen, forcings: [F9_systemic_crisis]}]
```

A cell costs (its forcings, or 1 if none) + (the points of each sweep). **A sweep is not crossed
with the cell's forcings** — a front is one solve per point, and multiplying it by a forcing list
is how an afternoon becomes a week; a forced front is named explicitly. `--no-sweeps` drops every
front (staging), `--policies` / `--forcings` restrict to a row or a column, and `--cross`
**overrides** the plan to take the whole catalogue product (what the completeness test uses).
Every run carries `policy` / `forcing` / `sweep` into its recap, so the dashboard groups on
coordinates rather than parsing `__` out of a name. To run only missing cells, write a one-off
stage spec including the same catalogues (the executed August ones were removed; `git show
5bf32d9:case_studies/guadeloupe/plan_budget.yaml` shows the pattern). Always validate before
committing hours:

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml --dry-run
python scripts/check_scenario_feasibility.py --scenarios case_studies/guadeloupe/plan.yaml
```

**Crop groups are a catalogue, not a copy.** YAML anchors do not cross files, so a spec writes
`crops: {group: sugarcane}` and `core/config.load_batch_spec` substitutes the list. The catalogue
is `crop_families` from `config.yaml` **plus** `crop_groups.yaml` (the latter winning), so a group
the model already knows is never restated in a scenario file; `@name` members compose groups out
of groups. Two traps: the match is the *exact* one-key dict `{group: x}`, because
`territory_production_bound`'s args already carry a key literally named `groups`; and a catalogue
declares its own `crop_groups` include so it stays runnable alone (`--scenarios
scenarios_policies.yaml --policies P8`). `scenarios.yaml` deliberately still uses in-file anchors
— one file, no cross-file copy, nothing to gain.

`check_scenario_feasibility.py` solves each scenario's **LP relaxation** (~2 min vs 30-60 min for
the MILP). Infeasible there ⇒ infeasible for certain; feasible there is necessary, not sufficient.
It also reports **symmetric crop groups** — crops the model cannot tell apart because they are
equal on every parameter it reads. Those are both a branch-and-bound disaster (the search
permutes equivalent solutions) and a modelling trap (a share constraint distinguishing crops the
data does not distinguish is met by relabelling, at zero cost). The 25 experimental
market-gardening variants are exactly that; see `docs/04-vigilance.md` B.3.

`run_scenarios.py` **chains warm starts** (on by default), from three sources tried nearest-first
(`seed_candidates`): the **previous point of the same Pareto front**, then the policy's own
unforced allocation (a forcing changes coefficients, not the feasible set), then an optional
global `--warm-start-from <run>`. Every seed is audited — HiGHS discards an infeasible MIP start
silently, so an unaudited seed yields a run that looks warm and behaves cold.
`scripts/audit_warm_start_seed.py` checks a candidate seed without solving.

The front chain only works because `core/config.order_sweep_points` **reorders each sweep
tightest-first before the batch runs**, which is the reverse of how the YAML reads. Feasibility
implies one way only: under `sense: le` a solution feasible at a low ceiling stays feasible at a
high one, so ascending order makes every seed valid and descending order makes every seed
infeasible; under `sense: ge` it inverts. The reordering abstains whenever it cannot be sure — a
2-D matrix, a constraint with no `sense`, or an argument that is not the bound's level (`scale`
multiplies the indicator and therefore *inverts* the direction, which is why the allowlist
exists). Abstaining costs speed only: correctness rests on the audit, never on the order.
Design spec: `docs/superpowers/specs/2026-07-31-scenarios-prospectifs-design.md`.

Read-only Streamlit dashboard over past runs: `streamlit run apps/dashboard/app.py`. Its
**Prospective** page reads a policy × forcing grid rather than a flat run list (heatmap with
absolute / %-of-nominal / regret readings, performance-robustness scatter, per-policy tornado,
robustness table). A run joins the grid via `run_policy` / `run_forcing` in its recap. Its
**Status** page shows the status board live.

**The status board** (~1 s, no solve): `scripts/build_status_board.py [--with-data]` writes
`docs/status/STATUS.md` — indicators × aggregation levels (`status/indicator_catalog.yaml`),
constraints and eligibility rules × crops (derived from `config.yaml`, with the GAMS equation each
ports), parameters with several plausible values (`status/parameter_choices.yaml`, each checked
against config.yaml: exit 1 on drift), and the roadmap. Regenerate it after touching
`config.yaml`, a catalogue or the roadmap; `tests/test_status_board.py` keeps the declarations in
step with the code (e.g. a dashboard indicator missing from the catalogue fails).

**Score a run against the observed 2017 land use** (~7s, no solve; new runs do it themselves
inside `generate_report`):

```bash
.venv/Scripts/python scripts/evaluate_calibration.py outputs/output_12   # one run
.venv/Scripts/python scripts/evaluate_calibration.py --all               # every run
```

**The 2017 reference state** (~5s, no solve, deterministic) is the observed situation every
run is scored against, built as a standalone artifact rather than only as a run's "input" side:

```bash
.venv/Scripts/python scripts/build_reference_state.py        # -> outputs/reference_2017/
.venv/Scripts/python scripts/compare_to_reference.py outputs/calib_retenu
.venv/Scripts/python scripts/pad_all_scales.py outputs/calib_retenu   # PAD at five scales
```

`outputs/reference_2017/REFERENCE.md` documents how it is built and — more usefully — what it
cannot say: the observed side has no fine crops (hence the low/high bracket on every indicator),
and part of the observed acreage is unreproducible by construction (a floor under the PAD).
Rebuild it whenever `config.yaml` changes year, `zone_filter` or `baseline_representative_crops`.
Its keys are English since 2026-09-22; the last French-keyed copy is
`outputs/_legacy_reference_2017_fr/` (read by the thesis tooling).

**Invariance check before/after a refactor** — `scripts/golden_snapshot.py` builds the full real
dataset and every indicator block on a real allocation (~7s, **no MILP solve**, so it is exactly
reproducible) and serialises ~680 numeric checksums:

```bash
.venv/Scripts/python scripts/golden_snapshot.py --write   # record current behavior
.venv/Scripts/python scripts/golden_snapshot.py --check   # non-zero exit + diff on any drift
```

Use it whenever touching `pipeline/`, `domain/`, `core/data/` or `reporting/indicators.py`: it
catches numeric drift that the (deliberately synthetic, data-free) unit tests cannot. The
reference lands in `.golden/`, gitignored because it derives from the local `data/`. A rename
changes its keys: compare through the rename map rather than trusting `--check` alone.

## Data is not in the repo

`/data/` is **gitignored** — `data/sets/` (`.set`), `data/tables/` (`.txt`) and `data/gis/`
(the shapefile layers) live locally only, as do `/outputs/`, `.worktrees/`, `.golden/` and
`.mosaica_solve_history.json`. Code that touches them fails on a fresh clone until the files are
present. There are no geographic coordinates in `data/tables/`; outside `data/gis/`, spatial
reporting is aggregated by `ILE`/`REGION`/`COMMUNE` only. What each table holds, its source and
its access level are described in `docs/data/` (versioned).

**`context/` holds the external sources**, and is versioned (except the .docx): `context/gams/`
is the original GAMS — the source of truth for any parity question — and
`context/Chopin et al 2015 pour Hal.pdf` is the reference article (§2.6 = the calibration method,
Tables 1-2 = yields/margins and risk-aversion coefficients).

## Architecture

Three layers: a **case-study-agnostic `core/`**, a **`case_studies/guadeloupe/`** supplying the
concrete data pipeline, GAMS-specific rules and reporting, and an **`apps/`** holding what only
*reads* finished runs.

`core/` splits building a model from solving one: `core/model/` (`registry`, `builder`,
`constraints`, `objectives`, `model_inputs`) constructs the Pyomo problem and knows nothing about
how it will be solved; `core/solve/` (`solver`, `progress`, `timing`, `warm_start`,
`shadow_prices`) drives HiGHS and everything that happens around a solve. `core/data/` reads
tables; `core/reporting/` writes run folders and computes robustness over a grid.

`case_studies/guadeloupe/` is organized by role — `pipeline/` (`data_pipeline.py`), `domain/`
(per-crop science: `economics`, `environment`, `water`, `soil_carbon`, `resilience`,
`farm_typology`, `crop_labels`, `crop_families`, `zones`, `agroecology`, `rpest`, `geometry`,
`itk`), `model/` (`model.py`, `constraints.py`), `reporting/` (`indicators`, `calibration`,
`report`, `plots`, `status`), `status/` (the YAML catalogues of the status board), and
`legacy_names.py`. Note `model/model.py`: the module is `case_studies.guadeloupe.model.model`, and
importing only the *package* does not register the case-study constraints (see below).
`config.yaml`, `scenarios.yaml`, `plan.yaml` with its three catalogues, `crop_groups.yaml`,
`references.yaml` and the `scenarios_calibration*.yaml` / `scenarios_labor.yaml` specs stay at
the case-study root.

`apps/dashboard/` is the read-only Streamlit viewer. It lives **outside** `case_studies/` because
it is not part of the solve path at all: it opens `outputs/output_N/` folders and never builds a
dataset, a model or a solver. Nothing under `core/` or `case_studies/` may import it; it imports
`case_studies.guadeloupe.domain` (labels, geometry), `legacy_names` and `reporting.status` freely.

**Config-driven registry pattern (the central idea).** Constraints, objectives, eligibility
criteria, and categorical rules are all Python functions registered by name via decorators, then
selected and parameterized entirely from `case_studies/guadeloupe/config.yaml`. To add or change
model behavior you usually edit the YAML, not the builder.

- `core/model/registry.py` — `@register_constraint(name)` / `@register_objective(name)` populate
  `CONSTRAINT_REGISTRY` / `OBJECTIVE_REGISTRY`.
- `core/config.py` `resolve_enabled(entries, registry)` — reads a config list, keeps entries with
  `enable: true`, and returns `(builder_fn, args)` pairs. The same pattern drives constraints,
  objectives (exactly one must be enabled), eligibility, and categorical rules.
- Builders are **imported for their side effect** of registering (e.g.
  `from core.model import constraints as _constraints  # noqa: F401`). If a builder isn't imported
  somewhere on the path to `build_crop_allocation_model`, its name won't be in the registry and
  config referencing it raises `KeyError`. `core/model/builder.py` imports the core builders;
  `case_studies/guadeloupe/model/model.py` additionally imports
  `case_studies.guadeloupe.model.constraints` to register case-specific ones. Import the *module*
  (`case_studies.guadeloupe.model.model`), never just the package — the package `__init__.py` is
  empty, so `import case_studies.guadeloupe.model` registers nothing.
- A config entry porting a GAMS equation carries a `label` named after it (`bc_quota_max` for
  `Eq_BC_QUOTA_MAX`) or a comment naming it right above; the status board reads either.

**Data flow** (`main.py` orchestrates):
1. `load_config(config.yaml)` → dict.
2. `build_dataset(config)` (`case_studies/guadeloupe/pipeline/data_pipeline.py`) reads the `.set`/
   `.txt` tables, applies the `zone_filter`, computes economics (`domain/economics.py`:
   margin/sales/subsidy per ha per crop, e.g. `crop_margin_per_ha`), farm typology
   (`domain/farm_typology.py`: base crop group → `TYPE_EXPL` farm type → risk aversion `AVERS`),
   and the plot×crop **eligibility mask** (`core/data/eligibility.py` numeric bounds +
   `categorical_rules`). Returns a `Dataset(sets, parameters, scalars)`; the raw GAMS tables are
   `plot_data`, `crop_data`, `operation_data`, `crop_operation_matrix`, `crop_price`,
   `crop_yield`…
3. `build_model(dataset, config)` → `build_crop_allocation_model(...)` creates the Pyomo
   `ConcreteModel`: binary var `model.Y[plot, crop]` over eligible `PAIRS`, then runs every
   enabled constraint/objective builder against a `ModelInputs` bundle
   (`core/model/model_inputs.py`).
3b. **Optional warm start.** `core/solve/warm_start.py` writes a past run's allocation into
   `model.Y` (`apply_allocation`) and — the part that matters — **audits it against the model's
   own constraints before solving** (`constraint_violations`). HiGHS discards an infeasible MIP
   start silently, so without the audit a run looks warm-started and behaves exactly like a cold
   one. Driven by `solver.warm_start_from` in `config.yaml` (a run folder); `main.py` loads,
   applies, audits, and only then passes `warm_start=True` down to `solve_model`, which maps it
   onto Pyomo's `warmstart` kwarg → `Highs.setSolution`. A warm start changes only how fast the
   optimum is **proven**, never what it is. It became necessary past ~309 000 binaries, where
   HiGHS stops finding good incumbents unaided. Measured: 720 s cold → 209 s warm, identical
   objective. To seed a run that adds a new constraint the old allocation must be repaired first
   — `scripts/repair_allocation.py`.
4. `solve_with_progress(model, config, case_study=...)` (`core/solve/progress.py`) runs
   `solve_model` (`core/solve/solver.py`, `SolverFactory('appsi_highs')` → HiGHS)
   **synchronously on the main thread**, printing an expected-duration **range** before and the
   real duration after. It is a range, not a point, because at a fixed size the recorded solves
   span a factor of ~10 (`docs/04-vigilance.md` B.1). **`.mosaica_solve_history.json` is a
   rolling window of the last 20 solves per case study**, not a cumulative log — recount it
   rather than quote a figure. `SolveHistory.estimate_range` reads the **most recent** comparable
   runs (same size ±20 %, same warm/cold mode) and **returns None outside the size band**. Note:
   the solve must NOT be backgrounded behind a live progress bar — `appsi_highs` loads the model
   inside `capture_output(capture_fd=True)`, and concurrent progress I/O from another thread
   corrupts Pyomo's process-global stdout/stderr fd state, crashing every real run (see
   `docs/superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md`).
5. `generate_report(...)` (`case_studies/guadeloupe/reporting/report.py`) decodes the solution,
   computes indicators (`reporting/indicators.py`), renders PNGs (`reporting/plots.py`), and
   writes a timestamped `outputs/output_N/` folder (`core/reporting/run_folder.py`) with a recap,
   CSVs, YAML, and charts. The dashboard (`apps/dashboard/`) is a read-only viewer over those
   folders.

**`data/gis/` (not versioned) carries the 2017 RPG plot layer.** `core/data/shapefile.py` reads
it in pure Python — no GDAL, no geopandas — and `domain/geometry.py` joins it to the synthetic ids
`P1..Pn` by **farm signature**, for lack of a common identifier: 99.4 % of plots. The **Map** page
shows observed, simulated and changes. Read `docs/04-vigilance.md` F.1 before concluding on a
single plot — ~1 557 of them have an interchangeable twin. That join is also the first obstacle
to handing an allocation to MAELIA.

**Three more environmental indicators, each with its trap** (documented in
`docs/04-vigilance.md`): **phosphorus and potassium** read off the NPK fertiliser names
(validated against the `AZOTE` column, which confirms them to the thousandth);
**`domain/agroecology.py`**, where the AECMs (MAE) give a *sourced* definition of agroecology and
the `FERTI_MA_*BIO` operations a definition of organic — reported separately, because
green-harvested cane is not organic, and grassland dominates organic-by-itinerary; and
**`domain/rpest.py`**, Tixier's fuzzy tree, the only indicator that depends on the **(plot, crop)
pair**, since it crosses the crop's products with the plot's runoff and drainage.

**`core/solve/shadow_prices.py`** gives the marginal cost of each named constraint. Careful:
fixing the integers does NOT work here (the model is purely binary, so the resulting LP has no
free variable left and every dual is 0) — the duals read are those of the **LP relaxation**, with
the caveats the module details.

**`zone_filter.scale_territorial_bounds: true`** scales the territorial thresholds to the share
of area kept. Without it a reduced run is not smaller, it is **infeasible** (the grassland floor
asks its 6 096 ha of the whole island). Opt-in: rewriting a threshold changes what the scenario
says.

The environmental indicators live in three per-crop modules of `domain/` — `environment.py`
(nitrogen/GHG/TFI), `water.py` (water need) and `soil_carbon.py` (soil organic carbon) — all
computed in `data_pipeline` then applied to the allocation by `reporting/indicators.py`. Carbon
is the only one that depends on the **plot** (through `TYPE_SOL` → `Data_Sol.txt`) and not only
on the crop: it therefore does not go through the `rate()` helper of `compute_facts_table`.

**Two notions of resilience, never to be added.** `recap["resilience"]` measures the
**exposure** of a *frozen* allocation: the price shock is applied after the solve, so it answers
"what is lost if nobody reacts". `core/reporting/robustness.py` measures **adaptive capacity
under policy constraint** over a policy × forcing grid: the model re-optimised under each
forcing, within the limits the policy leaves it. The module provides worst case (Wald),
retention, CV, maximum regret (Savage) and viability domain (Starr), with three deliberate
choices: infeasibility is the **worst outcome**, not a missing value; forcings are **not
averaged** by default (an average would assert a probability distribution nobody chose); regret
is computed against the best policy **of the same forcing**.

**Composite-score trap.** An indicator a constraint *fixes* is a hypothesis of the scenario, not
its result: scoring a policy on the subsidy ceiling it set itself is circular.
`comparison.bound_indicators(recap)` detects them from `recap["constraints"]` (so after the fact
on runs already written) and the page flags them. Moreover
`compute_composite_scores(..., balance_families=True)` — the default — normalises the weight
**per family**: without it the eleven self-sufficiency ratios, nearly collinear, weigh eleven
times GHG, and the score measures how finely the list is cut rather than performance.

`domain/resilience.py` adds three **exposure** indicators (climate margin at risk through
`Var_Rdt_Cult`, revenue concentration, loss under a price shock), aggregated by
`compute_resilience_totals` and stored in `recap["resilience"]`. Careful: exposing an indicator
to the composite score needs **two** additions in `apps/dashboard/comparison.py` —
`INDICATOR_DIRECTION` for the direction, and a label in one of the family dictionaries
(`ECON_INDICATORS`, `ENV_INDICATORS`, …) for membership of the selector — plus its entry in
`status/indicator_catalog.yaml`. The first alone wires nothing.

**The dashboard opens on a Summary page** (`apps/dashboard/app.py`) that answers on one screen:
did the solve converge, the four calibration verdicts against their thresholds, the crop groups
carrying the gap (ranked in **hectares**, not in PAD), and the reading traps that apply to
*this* run — derived from the recap by `apps/dashboard/synthesis.run_alerts`. Each alert encodes
a trap documented here or in `04-vigilance.md` (solve not proven optimal, PAD pinned by
`pn_prod_min`/`bc_quota_max`, indicator fixed by a constraint, pure gross-margin objective), so
the caveat travels with the number.

**Three reference runs are declared in `case_studies/guadeloupe/references.yaml`** — observed
2017, GAMS-parity calibration, selected calibration — each with the justification of its choice
and the metrics it must reproduce. The two calibration runs are regenerated in one command from
`scenarios_calibration.yaml`, and their folder **carries their name** (`outputs/calib_selected/`,
not `output_7`): `run_folder.create_output_folder` accepts a name, and discovery works on the
presence of a `recap.json` — which puts named and numbered folders on the same footing and
naturally excludes `reference_2017/` (it writes `reference.json`). **The folders on disk
(`calib_retenu/`, `calib_gams_parite/`) predate the 2026-09-08 correction of the price tables**
and are due to be regenerated (roadmap `regenerate-reference-runs`).

```bash
.venv/Scripts/python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/scenarios_calibration.yaml
.venv/Scripts/python scripts/check_references.py     # guard, ~0 s, no solve
```

`check_references.py` is **the repository's only guard on the solve**: the tests are data-free by
choice and `golden_snapshot` covers the pipeline and the indicators, not the resolution. Its
tolerance is 5 % because the measured branch-and-bound noise is 0.15 PAD point — an exact-equality
guard would fail on a mere re-run.

**Two diffs, to read in this order.** `apps/dashboard/config_diff.py` puts the
`config_used.yaml` of two runs side by side: which constraints one enables that the other does
not, which thresholds moved. `apps/dashboard/allocation_diff.py` says what those lines
**moved**: transition matrix, dominant flows, net balance per crop. Between the two calibrations,
the first shows two constraints and the second `CS → PN` 2 972 ha and `BC → BA` 1 189 ha. The
config diff says what was **asked**, never what the gap **cost** — a constraint that does not
bind changes no result. Mind the resolution of the allocation diff: `fine` (84 codes) only makes
sense between two **simulated** runs; against the observation, only the 12 RPG groups exist.

**ε-constraint Pareto fronts** (`scenarios_pareto.yaml`, `apps/dashboard/pareto.py`, page
**Pareto**). A sweep is a run carrying a `matrix:`, unfolded by `expand_runs` into one solve per
point. Two `enable: false` levers live in `config.yaml` (`nitrogen_max`, `employment_min`) only so
that `matrix: {args:<label>.<argument>: [...]}` can vary their threshold — `set_args` can only
touch an entry already declared. A front is traced either against the reference config (the
catalogue run alone) or **under a policy** declared in `plan.yaml` — and that is the interesting
object, the marginal cost of nitrogen not being the same at 70 % and at 30 % inertia. Consequence
for reading: the run is then named `<policy>__<forcing>__<sweep>__<point>`, so the prefix before
`__` names the **policy**, not the sweep — `pareto.sweep_of` groups on
`run_sweep`/`run_policy`/`run_forcing` of the recap, the prefix serving only as a fallback for
older runs. The check on the first point (inactive threshold ⇒ margin equal to the unswept run) is
then made against the policy, not against `calib_selected`. The front gives the **marginal cost**
over the whole range, where the dual price of `shadow_prices.py` only gives its local slope; a
large gap between the two means the dual is read outside its neighbourhood of validity. A
**dominated** point on a front almost always signals an unconverged solve, not a discovery:
tightening a constraint cannot improve the objective.

`reporting/calibration.py` scores the run against the observed reality, after Chopin et al.
(2015) §2.6: territorial, sub-regional and per-farm PAD (percentage absolute deviation),
confusion matrix of the 8 farm types, plot agreement rate. Everything is compared at the level of
the **12 observed RPG groups** — `domain/crop_families.base_group_for()` folds the 84 fine crops
onto them, because the 2017 observation has no finer resolution. Written into each run
(`recap["calibration"]` + `csv/calibration_*.csv`), replayable on a past run with
`scripts/evaluate_calibration.py` (rebuilds the `Dataset`, ~7 s, no solve).

**Bounding an indicator, not just production.** `territory_production_bound` can only bound
physical output. `territory_indicator_bound` bounds *any* per-hectare rate the case study exposes
in `ModelInputs.crop_indicator_rates` — nitrogen, TFI, GHG, water, soil carbon, labour hours,
subsidy euros — so one builder writes a nitrates ceiling, a public-spending envelope and an
employment floor. `zone_indicator_bound` holds the same bound per island/region/watershed/**farm**
(`threshold_per_ha` × the zone's own hectares is the nitrates-directive form), and
`baseline_inertia_min` requires a share of allocated area to stay in its observed 2017 group. Two
traps: `ModelInputs.plot_weights` exists because rates are per-crop while water is only drawn on
irrigable plots (a bound without `plot_weight: irrigable` counts 56 Mm³ where the report says
35); and an **employment floor above the labour cap is infeasible** — `farm_labor_hours_max`
grants 3 891 FTE at `slack: 1.0`, so any floor above that must raise the slack in the same
scenario (and raising it is not sufficient either — vigilance B.4).

**Eligibility** is a boolean plot×crop matrix: numeric attribute bounds (altitude, slope,
rainfall, plot size) intersected with `categorical_rules` (irrigation, soil type, region bans,
`fallow_lock` fallow history, etc.). Only eligible `(plot, crop)` pairs become decision
variables, which keeps the MILP tractable.

A categorical rule receives the plot table as `plot_attributes` and returns `(crops,
condition)`; `forbid_where` then clears those crops on the matching plots. Since each rule forbids
its own subset and the mask keeps the **union** forbidden, a single `attribute_forbidden` entry
ANDs its conditions and an **OR is expressed as several entries** (that is how the ME soil/island
ban is written in `config.yaml`). Prefer `attribute_forbidden`, whose conditions say what is
forbidden: `max_risk_threshold` / `exact_risk_value` read backwards (their "allowed" arguments are
the forbidden values) and are kept only for old configs.

**`core/` speaks no Guadeloupe.** It reasons about plots, crops and farms only: no `plot_data`
columns like `ILE`, no GFA. `ModelInputs.farm_restricted_surface_ha` is the generic name for
"surface of the farm's plots flagged as subject to a land-tenure scheme" — the case study maps its
`farm_gfa_surface_ha` parameter onto it in `model/model.py`. Keep it that way: case-study
vocabulary belongs in `case_studies/`, where it anchors GAMS parity.

## Conventions & gotchas

- **`territory_production_bound` and the "trivial Boolean" trap.** When a constraint's `sum()`
  matches zero `(plot, crop)` pairs it returns a plain Python `0`, not a Pyomo expression;
  comparing it yields a bare `bool` that Pyomo rejects. Both `territory_production_bound`
  (`core/model/constraints.py`) and `cs_gfa_minimum_share` guard for this with
  `Constraint.Feasible`/`Constraint.Infeasible`. Replicate this guard in any new constraint whose
  term set can be empty.
- **Disabled config entries are intentional, with reasons in the YAML comments.** E.g.
  `cs_gfa_minimum_share` and the production floors are correct and tested but disabled because
  enabling them causes a genuine (GAMS-matching) infeasibility on the real 2017 data. Read the
  comment before flipping an `enable:` flag.
- **Where each kind of knowledge goes.** `docs/04-vigilance.md` holds the **traps and known data
  gaps** — the *why*, and the file a newcomer must read before quoting a number; a newly
  discovered limitation belongs there. `docs/status/roadmap.yaml` is what remains **to
  implement** (the *what next*), with a status per item. A parameter with several plausible
  values goes in `case_studies/guadeloupe/status/parameter_choices.yaml`. A whole investigation —
  with the dead ends and the measurement that closed them — belongs in a new spec under
  `docs/superpowers/specs/`. The historical log is `docs/archives/journal-vigilance.md`, no longer
  maintained. Read `04`, the roadmap and `docs/status/STATUS.md` at the start of substantive work.
- **Comments say why, give units, cite the GAMS line, and avoid measured figures that will
  rot** — point to the vigilance entry holding the measurement instead. The comment review of
  2026-09-22 found a backwards rule description, a stale time limit and claims contradicted by
  later fixes; a comment is wrong as soon as the code it describes moves.
- `docs/superpowers/specs/` (design docs) and `docs/superpowers/plans/` (implementation plans)
  hold the reasoning behind each feature. Only **unexecuted** plans are kept — executed ones are
  deleted, their rationale surviving in the matching spec. The same holds for one-off batch specs
  (the August `plan_etape_*.yaml` were removed once run).
- Tests exercise builders in isolation with tiny hand-built configs and `plot_surface_ha`/
  `eligible_pairs` dicts (see `tests/test_guadeloupe_constraints.py`) — they do not read `data/`.
  Follow that style for new model logic so tests stay fast and data-free.
- **`data.year` / `data.scenario` come from `config.yaml`** (defaults `2017` / `RESTIT`, which
  reproduce the historical behavior). `year` selects the economic time-series column in the
  `indice_H` tables (`2017`–`2022`, or `init`/`calib`) and drives **economics only** — the
  plot/farm structure stays pinned to 2017, the only year whose structural data exists.
  `scenario` (`RESTIT`|`SMART`) selects `Matrice_OTK_Cult_<scenario>`,
  `MAE_Compost_Cult_<scenario>` and the price/yield tables `Prix_Cult_CF_<scenario>` /
  `Rdt_Cult_CF_<scenario>` (the files GAMS actually includes, since 2026-09-08).
  `data_pipeline.build_dataset` validates both (fail-fast `ValueError`) and the yield variance
  deliberately stays on its `init` column regardless of `year`. The chosen year/scenario is
  recorded in each run's recap.
- **PowerShell pitfalls met in this repo**: passing a one-pair nested array (`@(@('a','b'))`)
  flattens it — use `,@('a','b')`; native-exe arguments lose their embedded double quotes; and
  `Set-Content -Encoding utf8` writes a BOM. Do multi-file text replacements from a Python script
  instead.
