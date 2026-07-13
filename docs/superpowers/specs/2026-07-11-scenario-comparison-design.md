# Public-policy scenario system & comparison — design (not yet implemented)

_2026-07-10 — design only, for user review before implementation (brique C)._

## Goal

Let the user define named public-policy scenarios (production quotas, crop bans, subsidy
changes, local transitions), run each to its own `outputs/output_N/` folder, and compare
indicators across scenarios (objective, ETP, production/subsidy/revenue, surface, Gini,
Shannon…). This builds directly on the existing config-driven architecture — most policy
levers already map to existing config mechanisms.

## Scenario definition

A **scenario** is the base `config.yaml` plus a set of overrides. Proposed form: one file
per scenario under `case_studies/guadeloupe/scenarios/<name>.yaml`, deep-merged onto the
base config at run time. The base config itself is the implicit "reference" scenario.

Deep-merge rules (to design precisely, but the intent):
- `constraints` / `objectives` / `categorical_rules`: matched by `label` (or `name`+args)
  so a scenario can enable/disable one entry or change a single threshold without
  restating the whole list.
- `zone_filter`, `labor`, `solver`: shallow-overridden.

## Policy lever → mechanism

| Policy lever | Mechanism (mostly already exists) |
|---|---|
| Production quota (min/max per crop group) | `territory_production_bound` (`sense`, `threshold`) |
| Crop ban (region / island / global) | `categorical_rules` — `region_crop_forbidden` exists; add a general `crop_forbidden` (optionally scoped by island/region) |
| Local transition / small-scale test | `zone_filter` (already implemented) |
| Objective change (e.g. risk-adjusted) | `objectives` enable toggle (already implemented) |
| **Subsidy change** | **NEW `subsidy_adjustments`** — see open questions |

## Running scenarios

`scripts/run_scenarios.py <name...>`: for each scenario, deep-merge onto base config,
`build_dataset → build_model → solve → generate_report`, and tag the recap with
`scenario_name` + the applied overrides. Each scenario writes its own `outputs/output_N/`.

Because a full solve is ~30–55 min (see VIGILANCE.md, the bottleneck is the MILP search),
running several scenarios at full scale is expensive. Recommend developing/validating
scenarios `zone_filter`-scoped first, then a deliberate full-scale batch.

## Comparison

- `compare_runs(output_dirs) -> DataFrame`: load each run's recap + indicator CSVs and
  assemble a comparison table — one column per scenario, plus deltas vs the reference —
  for the headline indicators (objective, `total_etp`, production/subsidy/revenue by crop,
  surface by region/island, Gini, Shannon).
- A comparison artifact persisted to `outputs/comparison_<timestamp>/` (CSV + PNGs).
- Dashboard "Comparaison" page: pick ≥2 runs, show grouped bars (crop names via
  `crop_labels`) and a delta table.

## Open questions / blockers (for user review)

1. **Subsidy scenarios are the one lever not yet config-driven.** Subsidy values live in
   `data/tables/indice_H/*` (POSEI/aide/MAE), consumed by
   `economics.compute_subsidy_per_ha_cult`. Two options:
   - (a) **Config `subsidy_adjustments`** — per-crop / per-scheme multipliers or deltas
     applied inside `compute_subsidy_per_ha_cult`. Light, keeps data immutable,
     scenario-friendly. **Recommended.**
   - (b) Scenario-specific data overlays (swap whole tables). Heavier, but exact.
   Decision needed before implementing subsidy scenarios.
2. **Full-scale comparison cost.** N scenarios × ~45 min. Options: accept it (overnight
   batch), or restrict full runs to a shortlist and use zone-scoped runs for exploration.
3. **Baseline resolution.** Cross-scenario per-crop *input* comparisons inherit the
   12-RPG-group limitation (VIGILANCE.md); scenario-vs-scenario *output* comparisons are
   at full fine-crop resolution and unaffected.

## Non-goals

- No multi-objective optimization, no automated policy search, no GUI scenario editor.
- No change to the solver or model numerics.
