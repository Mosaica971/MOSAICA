# 01 — Usage

Every command runs from the **repository root**, with the local venv (PowerShell:
`.venv\Scripts\python`, bash: `.venv/bin/python`). The examples write `python` to stay
readable.

---

## 1. Solve once

```bash
python main.py                          # -> outputs/output_N/
python main.py --case-study guadeloupe  # explicit (default: $MOSAICA_CASE_STUDY, else guadeloupe)
```

No other option, on purpose: **everything is in `config.yaml`**, so that a run is reproducible
from the `config_used.yaml` it writes.

> **Slow: 30–60 min on the full territory, with a huge variance.** The bottleneck is the
> branch-and-bound search, not building the model (~15 s). At a fixed size the measured
> durations span a factor of about ten ([04 — Vigilance](04-vigilance.md) B.1). Do not iterate
> on it — see §2.

**Output** — a folder `outputs/output_N/` (or `outputs/<name>/` when the run is named):

| | |
|---|---|
| `recap.json` / `recap.md` | ~50 scalars, input -> output -> delta |
| `config_used.yaml` | the exact config of the run — what makes the run reproducible |
| `csv/` | allocation, indicators, calibration, `facts_<side>.csv` (the dashboard's source) |
| `plots/` | PNG figures |

Runs written before 2026-09-22 carry French keys and file names (`total_azote`,
`etp_by_region_output.csv`). Everything that reads a run goes through
`case_studies/guadeloupe/legacy_names.py`, so they read like new ones; the files are never
rewritten.

---

## 2. Iterate fast: shrink the territory

The two ways not to wait 40 minutes to test an idea.

**`zone_filter` in `config.yaml`** — restrict to an island, a region, some farms:

```yaml
zone_filter:
  include: {islands: [3]}          # Marie-Galante
  scale_territorial_bounds: true   # REQUIRED, see below
```

**Without `scale_territorial_bounds: true`, a reduced run is not smaller: it is infeasible.**
The territorial thresholds stay stated for the whole territory — the grassland floor asks its
6 096 ha of Marie-Galante alone. With the flag, every absolute threshold is scaled to the
share of area kept and the run goes **from infeasible to optimal in 5 s**. It is opt-in
because rewriting a threshold changes what the scenario says.

**`profile_solver.py`** — the same from the command line, with the time per phase:

```bash
python scripts/profile_solver.py --island 1
python scripts/profile_solver.py --farm E1471 --farm E2      # options combine
```

As soon as a filter is given, the territorial quotas are disabled automatically.

---

## 3. Run a scenario batch

A scenario is a small set of **overrides** applied on `config.yaml`. Each run produces its own
folder, plus a comparative `batch_summary_*.csv/.md`.

```bash
python scripts/run_scenarios.py                            # scenarios.yaml (flat list)
python scripts/run_scenarios.py --scenarios <file> --dry-run   # resolve without solving
python scripts/run_scenarios.py --stop-on-error            # default: carry on after a failure
```

**`--dry-run` is the reflex after any YAML edit.** It resolves every run (labels, constraint
names, crop groups) in a few seconds and catches the typo that would cost a night.

### 3.1 Prospective: three catalogues and a plan

| File | Role |
|---|---|
| `scenarios_policies.yaml` | **what is decided** — P1…P10, from deregulation to the agroecological bifurcation |
| `scenarios_forcings.yaml` | **what is imposed** — F0…F11, cyclone, drought, price shocks, land take |
| `scenarios_pareto.yaml` | the ε-constraint **sweeps** |
| **`plan.yaml`** | **what actually runs** — the only file to edit |

```yaml
# plan.yaml
scenarios:
  P1_full_deregulation:                              # the policy alone, unforced
  P4_status_quo: [F0_nominal, F9_systemic_crisis]    # shorthand for `forcings:`
  P5_budget_austerity: {forcings: "*"}               # the whole catalogue
  P8_agroecological_transition:
    forcings: [F0_nominal, F9_systemic_crisis]
    sweeps:
      - pareto_nitrogen                                           # front under unforced P8
      - {name: pareto_nitrogen, forcings: [F9_systemic_crisis]}   # ... and under the shock
```

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml --dry-run
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml --no-sweeps
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml
```

**Count before launching**: a cell costs (its forcings, or 1 if none) + (the points of each
sweep). The plan shipped is 37 runs (see its header). Staging options:

| Option | Effect |
|---|---|
| `--no-sweeps` | drops the fronts (7 solves each) |
| `--policies P8,P9` | one row |
| `--forcings F9_systemic_crisis` | one column |
| `--cross` | **overrides the plan** and takes the whole catalogue product |

A catalogue can still be run alone, without a plan:

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/scenarios_policies.yaml \
       --policies P8_agroecological_transition
```

The August 2026 campaign was solved under the former French names (`P4_statu_quo`,
`F9_crise_systemique`, `pareto_azote`). The dashboard maps them onto the current ones.

### 3.2 Pre-flight check — mandatory before a long batch

```bash
python scripts/check_scenario_feasibility.py --scenarios case_studies/guadeloupe/plan.yaml
```

Solves the **LP relaxation** of each scenario (~2–4 min against 30–60 min for the MILP). The
logic runs one way only, and that is the whole point:

- **infeasible in LP ⇒ infeasible for good.** Fix the scenario.
- feasible in LP ⇒ the MILP *can* still be infeasible (integrality can kill it), but every
  infeasibility actually met here was algebraic.

It also reports **symmetric crop groups** — crops the model cannot tell apart because they are
equal on every parameter it reads. That is both a branch-and-bound disaster and a modelling
trap (see [04 — Vigilance](04-vigilance.md#karusmart)).

### 3.3 Pareto fronts: what the next step costs

A scenario says "with this nitrogen ceiling, the margin is X". It does not say what the next
kilogram costs. A front does: the objective is fixed, one indicator is tightened step by
step, and the resulting curve **is** the trade-off.

```yaml
# scenarios_pareto.yaml
sweeps:
  - name: pareto_nitrogen
    enable: [nitrogen_max]
    matrix:
      args:nitrogen_max.threshold: [1930903, 1834358, ..., 1061997]   # 7 points = 7 solves
```

Three things to know:

1. **`args:<label>.<argument>`** targets the argument of the constraint carrying that label —
   a constraint threshold lives at no dotted config path. That is why `nitrogen_max` and
   `employment_min` exist as `enable: false` in `config.yaml`: empty shells that give the sweep
   something to hold.
2. **The points do not run in the written order.** They are reordered from the *tightest*
   threshold to the loosest, because feasibility implies only in that direction — an
   allocation feasible at 55 % of nitrogen is still feasible at 100 %, never the reverse. Each
   point then seeds the next: 1 cold solve instead of 7.
3. **A dominated point almost always signals a solve that did not converge, not a discovery.**
   Tightening a constraint cannot improve the objective.

The front gives the **marginal cost over the whole range**, where the dual price
(`core/solve/shadow_prices.py`) only gives the local slope. A large gap between the two means
the dual is read outside its neighbourhood of validity.

---

## 4. Speed up: the warm start

Beyond ~309 000 binary variables, HiGHS no longer finds a good initial solution on its own.
Giving it one changes **only how fast the optimum is proven**, never the optimum. Measured:
**720 s cold, 209 s warm**, identical objective.

```yaml
# config.yaml
solver:
  warm_start_from: outputs/calib_retenu
```

The start is **audited** against the model's constraints before the solve. If it violates
one, the run says so and starts cold — because **HiGHS discards an infeasible start
silently**, and a run would otherwise look warm while behaving cold.

To seed a run that **adds** a constraint, repair the allocation first:

```bash
python scripts/repair_allocation.py outputs/output_3 \
       --crops AG,VE_BTGT,VE_PLUIE --min-surface 335 --out outputs/_warmstart_plu
python scripts/audit_warm_start_seed.py --scenarios <spec> --run <name> --seed <folder>
```

In a batch the chaining is **automatic**: three seeds tried from nearest to farthest (previous
point of the same front -> the policy's nominal allocation -> the global
`--warm-start-from` seed). `--no-warm-start-chain` turns it off.

---

## 5. Inspect the data

```bash
python scripts/display_datasets.py     # every set/parameter/scalar build_dataset produces
```

The input tables, their sources and access levels are listed in the
[data catalogue](data/README.md), with the fill-in workbooks to add or correct data.

---

## 6. Calibration: does the model match reality?

Three tools, in this order.

```bash
python scripts/build_reference_state.py            # -> outputs/reference_2017/ (~5 s, no solve)
python scripts/compare_to_reference.py outputs/calib_retenu
python scripts/evaluate_calibration.py outputs/calib_retenu   # ~7 s, --all for every run
python scripts/pad_all_scales.py outputs/calib_retenu         # PAD at five scales
```

1. **`build_reference_state.py`** builds the observed 2017 situation, independent of any run.
   **Read its `REFERENCE.md` before interpreting any gap**: above all it says what the
   reference *cannot* say. Rerun it when `config.yaml` changes `year`, `zone_filter` or
   `baseline_representative_crops` — and only then.
2. **`compare_to_reference.py`** puts a run against it and writes `reference_comparison.md`
   into the run folder.
3. **`evaluate_calibration.py`** gives the detail by crop, sub-region and farm. New runs do it
   on their own in `generate_report`.

Method and thresholds: Chopin et al. (2015) §2.6 — **PAD < 15 %** over the territory,
**< 20 %** per sub-region, **80 %** of farms in their original type.

**Comparing our figures with theirs needs care** — the article publishes its PAD *per crop*
and never aggregated, counts non-cultivated plots, and its base year is 2010. Detail in
[04 — Vigilance](04-vigilance.md#calibration).

### Reference runs

Three series are fixed points, declared and **guarded** in `references.yaml`:

| Role | Folder | What it says |
|---|---|---|
| Observed 2017 (RPG) | `calib_selected/` (input side) | the land use actually declared |
| Calib GAMS parity | `calib_gams_parity/` | PAD 48.4 %, types 64.0 % — CALIB with no deviation |
| Calib selected | `calib_selected/` | types 86.9 %, plots 67.6 %, area 77.1 % |

The folders solved before 2026-09-22 are `calib_retenu/` and `calib_gams_parite/`;
`references.yaml` looks for both names. They predate the 2026-09-08 correction of the price
tables and are due to be regenerated (roadmap `regenerate-reference-runs`).

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/scenarios_calibration.yaml
python scripts/check_references.py --verbose      # guard, ~0 s, no solve
```

`check_references.py` is the **repository's only guard on the solve** — the tests are
data-free by choice and `golden_snapshot` stops before the resolution. Tolerance 5 %, chosen
above the measured branch-and-bound noise (0.15 PAD point over three HiGHS seeds).

---

## 7. Dashboard (read-only)

```bash
streamlit run apps/dashboard/app.py
```

It solves nothing and writes nothing: it opens `outputs/` folders.

| Page | What it answers |
|---|---|
| **Summary** (home) | on one screen: did the solve converge? the 4 calibration verdicts? where is the gap (ranked in **hectares**, not in PAD)? and **the reading traps specific to this run** |
| **Run detail** | one run in full: recap, input/output indicators, figures |
| **Comparison** | several runs side by side + config diff + allocation diff + composite score |
| **Calibration** | one run against the observation: PAD by crop, region x crop heatmap, farm-type confusion matrix |
| **Prospective** | a policy x forcing grid: heatmap, performance-robustness scatter, tornado, robustness |
| **Map** | observed and simulated plots, and the changes. Needs `data/gis/` |
| **Pareto** | the trade-off curve and the marginal cost |
| **Status** | what is implemented: indicators x levels, constraints x crops, parameter choices, roadmap |

**The two diffs read in this order**: the **configuration** diff says what was *asked*
(which constraints, which thresholds); the **allocation** diff says what that *moved*
(transition matrix, dominant flows). The first never says what the gap cost — a constraint
that does not bind changes no result.

---

## 8. Tests and guards

```bash
python -m pytest tests/test_readers.py    # one file — prefer this while iterating
python -m pytest                          # full suite — SLOW (~29 min)
python scripts/golden_snapshot.py --write # record the current behaviour
python scripts/golden_snapshot.py --check # detect any numeric drift
python scripts/check_references.py        # the reference runs have not moved
python scripts/build_status_board.py      # regenerate docs/status/STATUS.md (flags parameter drift)
```

Most tests are **data-free** by choice (a tiny hand-built config), hence fast. A few build the
real dataset and solve: they are the 29 minutes.

`golden_snapshot` builds the real dataset and every indicator block on a real allocation (~7 s,
**no solve**, hence exactly reproducible) and serialises ~680 checksums. **Run it after any
change to `pipeline/`, `domain/`, `core/data/` or `reporting/indicators.py`**: it catches the
numeric drift the data-free tests cannot see.

---

## 9. Cheat sheet

| I want to | Command |
|---|---|
| a full run | `python main.py` |
| iterate without waiting | `zone_filter` + `scale_territorial_bounds: true` |
| validate a scenario YAML | `run_scenarios.py --scenarios <f> --dry-run` |
| know whether a batch is feasible | `check_scenario_feasibility.py --scenarios <f>` |
| run the prospective plan | `run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml` |
| score a run against 2017 | `evaluate_calibration.py outputs/<run>` |
| check nothing drifted | `golden_snapshot.py --check` then `check_references.py` |
| see what is implemented | `build_status_board.py`, or the dashboard's Status page |
| look at the results | `streamlit run apps/dashboard/app.py` |
