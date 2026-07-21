# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Python/Pyomo rewrite of **MOSAICA**, a crop-allocation optimization model originally
written in GAMS. It solves a large binary MILP: assign each agricultural plot in
Guadeloupe to at most one crop so as to maximize gross margin, subject to agronomic
eligibility, per-farm area rules, and territory-wide production quotas. The original
GAMS source lives (as `.txt`) in `old_code_gms_format_now_txt/` and is the **reference
for parity** — when a constraint or coefficient is in question, that directory is the
source of truth (`MODELE.txt`, `OPTIMISATION.txt`, `ENTREES.txt`, `SETS.txt`, etc.).

The active workstream is "GAMS parity" — porting legacy behavior faithfully. Deviations
from GAMS are deliberate and documented in config comments and `VIGILANCE.md`.

## Commands

The venv is at `.venv/`. Run tests with pytest (config in `pyproject.toml`,
`pythonpath = ["."]` so imports resolve from the repo root):

```bash
.venv/Scripts/python -m pytest tests/test_readers.py # one file
.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py::test_cs_gfa_minimum_share_constraint_only_applies_to_farms_with_gfa_surface  # one test
.venv/Scripts/python -m pytest                       # full suite — SLOW (~29 min)
```

The **full suite is slow** (~29 min: a few tests build the real dataset and run real
HiGHS solves). During iteration, run only the file(s) you're touching; save the full run
for a final check.

Full end-to-end solve (builds data → model → solves with HiGHS → writes `outputs/output_N/`):

```bash
.venv/Scripts/python main.py
```

**Do NOT run `main.py` casually.** The full solve is slow (~30–55 min on the real dataset,
with large run-to-run variance; the bottleneck is the branch-and-bound search itself — see
`VIGILANCE.md`). Per standing user preference, only run the full solve at end-of-day and
only when asked; iterate with targeted pytest instead. For scaled-down experiments use
`zone_filter` in `config.yaml` (restrict to one island/region/farm) or
`scripts/profile_solver.py` (phase-timed run on a zone subset).

Scenario batch (same pipeline as `main.py`, one `output_N/` per scenario + a batch summary;
spec in `case_studies/guadeloupe/scenarios.yaml`): `.venv/Scripts/python scripts/run_scenarios.py`.
Same caveat as `main.py` — real solves, don't run casually.

Read-only Streamlit dashboard over past runs: `streamlit run case_studies/guadeloupe/dashboard/app.py`.

## Data is not in the repo

`/data/` is **gitignored** — the `.set` and `.txt` input tables live locally only, as do
`/outputs/`, `.worktrees/`, and `.mosaica_solve_history.json`. Code that touches
`data/sets/` or `data/tables/` will fail on a fresh clone until those files are present.
There are no geographic coordinates in the data (no shapefile/lat-long); spatial
reporting is aggregated by `ILE`/`REGION`/`COMMUNE` only.

## Architecture

Two-layer design: a **case-study-agnostic `core/`** and a **`case_studies/guadeloupe/`**
that supplies the concrete data pipeline, GAMS-specific rules, and reporting.

**Config-driven registry pattern (the central idea).** Constraints, objectives,
eligibility criteria, and categorical rules are all Python functions registered by name
via decorators, then selected and parameterized entirely from
`case_studies/guadeloupe/config.yaml`. To add or change model behavior you usually edit
the YAML, not the builder.

- `core/model/registry.py` — `@register_constraint(name)` / `@register_objective(name)`
  populate `CONSTRAINT_REGISTRY` / `OBJECTIVE_REGISTRY`.
- `core/config.py` `resolve_enabled(entries, registry)` — reads a config list, keeps
  entries with `enable: true`, and returns `(builder_fn, args)` pairs. The same pattern
  drives constraints, objectives (exactly one must be enabled), eligibility, and
  categorical rules.
- Builders are **imported for their side effect** of registering (e.g.
  `from core.model import constraints as _constraints  # noqa: F401`). If a builder isn't
  imported somewhere on the path to `build_crop_allocation_model`, its name won't be in
  the registry and config referencing it raises `KeyError`. `core/model/builder.py`
  imports the core builders; `case_studies/guadeloupe/model.py` additionally imports
  `case_studies.guadeloupe.constraints` to register case-specific ones.

**Data flow** (`main.py` orchestrates):
1. `load_config(config.yaml)` → dict.
2. `build_dataset(config)` (`case_studies/guadeloupe/data_pipeline.py`) reads the `.set`/
   `.txt` tables, applies the `zone_filter`, computes economics
   (`economics.py`: margin/sales/subsidy per ha per crop), farm typology
   (`farm_typology.py`: base crop group → `TYPE_EXPL` → risk aversion `AVERS`), and the
   plot×crop **eligibility mask** (`core/data/eligibility.py` numeric bounds +
   `categorical_rules`). Returns a `Dataset(sets, parameters, scalars)`.
3. `build_model(dataset, config)` → `build_crop_allocation_model(...)` creates the Pyomo
   `ConcreteModel`: binary var `model.Y[plot, crop]` over eligible `PAIRS`, then runs every
   enabled constraint/objective builder against a `ModelInputs` bundle
   (`core/model/model_inputs.py`).
4. `solve_with_progress(model, config, case_study=...)` (`core/model/progress.py`) runs
   `solve_model` (`core/model/solver.py`, `SolverFactory('appsi_highs')` → HiGHS)
   **synchronously on the main thread**, printing a static ETA before and the real
   duration after. The ETA comes from `SolveHistory` (past durations keyed by problem size
   in `.mosaica_solve_history.json`). Note: the solve must NOT be backgrounded behind a
   live progress bar — `appsi_highs` (via either `SolverFactory` or the persistent
   interface) loads the model inside `capture_output(capture_fd=True)`, and concurrent
   progress I/O from another thread corrupts Pyomo's process-global stdout/stderr fd state,
   crashing every real run (see
   `docs/superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md`).
5. `generate_report(...)` (`case_studies/guadeloupe/reporting/report.py`) decodes the
   solution, computes indicators (`reporting/indicators.py`), renders PNGs
   (`reporting/plots.py`), and writes a timestamped `outputs/output_N/` folder
   (`core/reporting/run_folder.py`) with a recap, CSVs, YAML, and charts. The dashboard
   (`case_studies/guadeloupe/dashboard/`) is a read-only viewer over those folders.

Les indicateurs environnementaux vivent dans trois modules par culture — `environment.py`
(azote/GES/IFT), `water.py` (besoin en eau) et `soil_carbon.py` (bilan de carbone organique) —
tous calculés dans `data_pipeline` puis appliqués à l'allocation par `reporting/indicators.py`.
Le carbone est le seul à dépendre de la **parcelle** (via `TYPE_SOL` → `Data_Sol.txt`) et non
seulement de la culture : il ne passe donc pas par l'helper `rate()` de `compute_facts_table`.

`resilience.py` ajoute trois indicateurs d'**exposition** (marge à risque climatique via
`Var_Rdt_Cult`, concentration du revenu, perte sous choc de prix), agrégés par
`compute_resilience_totals` et stockés dans `recap["resilience"]`. Attention : exposer un
indicateur au score composite demande **deux** ajouts — `INDICATOR_DIRECTION`
(`dashboard/comparison.py`) pour le sens, et un groupe de `_INDICATOR_LABELS`
(`dashboard/pages/2_Comparaison.py`) pour l'appartenance au sélecteur. Le premier seul ne
branche rien.

**Eligibility** is a boolean plot×crop matrix: numeric attribute bounds (altitude, slope,
rainfall, plot size) intersected with `categorical_rules` (irrigation, soil type, region
bans, `friche_lock` fallow history, etc.). Only eligible `(plot, crop)` pairs become
decision variables, which keeps the MILP tractable.

## Conventions & gotchas

- **`territory_production_bound` and the "trivial Boolean" trap.** When a constraint's
  `sum()` matches zero `(plot, crop)` pairs it returns a plain Python `0`, not a Pyomo
  expression; comparing it yields a bare `bool` that Pyomo rejects. Both
  `territory_production_bound` (`core/model/constraints.py`) and `cs_gfa_minimum_share`
  guard for this with `Constraint.Feasible`/`Constraint.Infeasible`. Replicate this guard
  in any new constraint whose term set can be empty.
- **Disabled config entries are intentional, with reasons in the YAML comments.** E.g.
  `cs_gfa_minimum_share` and `maximize_risk_adjusted_gross_margin` are correct and tested
  but disabled because enabling them causes a genuine (GAMS-matching) infeasibility on the
  real 2017 data, or diverges from the chosen default. Read the comment before flipping an
  `enable:` flag.
- `VIGILANCE.md` (French) is the **cross-session log of open issues and known data gaps**
  (the *why*); `TODO.md` is what remains **to implement** (the *what next*). Read both at
  the start of substantive work; move resolved VIGILANCE items to its "Résolu" section as
  one-liners rather than deleting them. User-facing commands live in `PRISE_EN_MAIN.md`.
- `docs/superpowers/specs/` (design docs) and `docs/superpowers/plans/` (implementation
  plans) hold the reasoning behind each feature. Only **unexecuted** plans are kept —
  executed ones are deleted, their rationale surviving in the matching spec.
- Tests exercise builders in isolation with tiny hand-built configs and `plot_surface_ha`/
  `eligible_pairs` dicts (see `tests/test_guadeloupe_constraints.py`) — they do not read
  `data/`. Follow that style for new model logic so tests stay fast and data-free.
- **`data.year` / `data.scenario` come from `config.yaml`** (defaults `2017` / `RESTIT`,
  which reproduce the historical hard-coded behavior). `year` selects the economic
  time-series column in the `indice_H` tables (`2017`–`2022`, or `init`/`calib`) and drives
  **economics only** — the plot/farm structure stays pinned to 2017, the only year whose
  structural data exists. `scenario` (`RESTIT`|`SMART`) selects `Matrice_OTK_Cult_<scenario>`
  and `MAE_Compost_Cult_<scenario>`. `data_pipeline.build_dataset` validates both (fail-fast
  `ValueError`) and `var_rdt_cult` deliberately stays on its `init` column regardless of
  `year`. The chosen year/scenario is recorded in each run's recap.
