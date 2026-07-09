# Output persistence & indicator reporting

## Goal

After a solve, persist a self-contained, numbered results folder
(`outputs/output_N/`) with a human/machine-readable recap of the run, the
allocation table, and PNG charts of key indicators — computed both for the
observed 2017 baseline ("input") and the optimized solution ("output"), plus
their deltas. This is the foundation the future dashboard (a separate,
not-yet-designed piece) will read from.

## Non-goals

- No interactive dashboard / web UI — a later, separate design.
- No real geographic map — no parcel geometry exists in the repo (no
  shapefile/GeoJSON, no lat/lon in `Data_Parc_Gwad_2017.txt`); indicators use
  `ILE`/`REGION`/`COMMUNE` breakdowns instead. Tracked in `VIGILANCE.md`.
- No revenue/ETP indicator — no labor data exists anywhere in the repo.
  Tracked in `VIGILANCE.md`.
- No zone-exclusion / sub-scoping — a separate, not-yet-designed piece.
- No config changes to make `YEAR`/`SCENARIO` selectable — tracked as a minor
  vigilance item, out of scope here.

## Architecture

### New module: `core/reporting/`

- `indicators.py` — pure functions computing indicators from a `Dataset` plus
  an allocation (a `plot -> crop` mapping — either the observed baseline
  `data_parc["cult_2017"]` or the optimized `model.Y` solution decoded to the
  same shape). Same functions run against both allocations so a delta is a
  plain subtraction. Computes, per crop: production (t), subsidy (€, €/t,
  €/€ sold), sales revenue (€), total revenue (sales + subsidy); per farm:
  total revenue and a Gini coefficient over the farm revenue distribution;
  per farm/region: a Shannon diversity index over crop surface shares.
- `plots.py` — matplotlib rendering of the `indicators.py` outputs to PNG:
  bar chart of production/crop, bar chart of subsidy/crop (and the two
  normalized variants), bar chart of total revenue, a region/island surface
  breakdown standing in for the unavailable map.
- `report.py` — orchestrates a full run: takes the `Dataset`, resolved
  `config`, solved `model`, `results`, and `duration`; computes input/output
  indicators + deltas; renders PNGs into `plots/`; writes `recap.md` and
  `recap.json` (same content) with plot/farm counts, enabled constraints
  (name + args), the enabled objective + its solved value, solver name/args,
  termination condition, problem size, solve duration, and a timestamp; and
  writes `allocation_input.csv` / `allocation_output.csv`
  (`plot, crop, farm, region, island, surface_ha`).
- `run_folder.py` — `create_output_folder(outputs_root: Path = Path("outputs")) -> Path`:
  scans `outputs_root` for existing `output_<N>` directories, creates and
  returns `output_<max(N)+1>` (or `output_1` if none exist). `outputs_root`
  is a parameter (not hardcoded) so tests point it at `tmp_path`.

### Modified: `core/model/progress.py`

`solve_with_progress` already computes `duration` internally but only uses it
to call `history.record(...)` before discarding it. Changes its return type
from `results` to `(results, duration)` so `report.py` can record the exact
solve time without recomputing it. Updates the one call site (`main.py`) and
existing tests accordingly.

### Modified: `case_studies/guadeloupe/economics.py`

`compute_gross_product_per_ha_cult` currently sums the sales component
(`rdt * (prix + bagasse)`) and the annualized subsidy component into one
number. Splits it into two functions — `compute_sales_per_ha_cult` and the
existing `compute_gross_product_per_ha_cult` calling it internally — so
`indicators.py` can report sales and subsidies separately without
duplicating the annualization formula.

### Modified: `main.py`

Replaces the two `print()` calls with a call to
`core.reporting.report.generate_report(...)`, passing the dataset, config,
solved model, results, and duration from `solve_with_progress`.

## Error handling

- No parcel geometry / no ETP data are permanent constraints of the current
  data, not error conditions — the affected indicators are simply not
  computed (not stubbed with placeholder values).
- `create_output_folder` assumes single-user local execution — no locking
  against concurrent runs (consistent with this being a local research tool,
  same assumption `SolveHistory` already makes).
- If a farm has zero revenue variance (all identical), Gini returns `0.0`
  rather than dividing by zero.

## Testing

- `indicators.py`: each indicator function tested against a small hand-built
  `Dataset` + allocation fixture with known expected output (production,
  subsidy variants, revenue, Gini on a known distribution, Shannon index on a
  known distribution).
- `plots.py`: smoke-tested — asserts a PNG file is created and non-empty for
  each chart function, not pixel content.
- `report.py`: end-to-end test against the existing tiny model-builder
  fixtures (mirroring `tests/test_model_solver.py`), asserting the full
  `output_N/` folder structure and that `recap.json` round-trips the
  expected keys.
- `run_folder.py`: empty dir → `output_1`; existing `output_1`, `output_3` →
  `output_4`; non-`output_*` clutter in the dir is ignored.
- `economics.py` split: existing tests for `compute_gross_product_per_ha_cult`
  keep passing unchanged; new test asserts
  `sales + subsidy_annualized == gross_product` for a sample input.
