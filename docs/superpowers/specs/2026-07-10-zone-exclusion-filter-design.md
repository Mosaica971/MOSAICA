# Zone exclusion/inclusion filter (config-driven)

## Goal

Let a user restrict, via `config.yaml` only, which plots enter the optimization
universe at all — by island, region, farm, or individual plot id — before the dataset
is built. Two use cases: faster small-scale test runs to validate the solver, and
modeling local/regional policy-transition scenarios (e.g. "what if this region were
optimized on its own").

## Non-goals

- No CLI override — `config.yaml` only, consistent with `eligibility_criteria` and
  `categorical_rules`.
- No automatic rescaling of territory-wide production quotas
  (`territory_production_bound` entries) to the filtered subset. Filtering only changes
  which plots exist; existing quota thresholds stay as configured. A user testing a
  small subset is expected to `enable: false` the territory constraints that no longer
  make sense, the same way they already toggle any other constraint entry today. This
  will be documented in `docs/04-vigilance.md`.
- No change to eligibility/categorical-rule semantics — this is a new, earlier filter
  stage, not a replacement for them.
- No integration with the (separate, on-hold) output-persistence-reporting work — noted
  as a natural follow-up once that branch merges (the `zone_filter` config block can be
  copied verbatim into a run's recap), not built here.

## config.yaml schema

New optional top-level section. Absent, or all four lists empty on both sides, means no
filtering (today's full-Guadeloupe behavior, unchanged).

```yaml
zone_filter:
  include:               # kept only if it satisfies ALL non-empty criteria (AND)
    islands: []
    regions: []
    farms: []
    plots: []
  exclude:                # removed if it matches ANY non-empty criterion (OR)
    islands: [1]
    regions: []
    farms: []
    plots: []
```

`exclude` is always applied after `include` and wins on conflict (a plot both included
and excluded is removed).

## Architecture

Follows the existing `core/` (generic) vs `case_studies/guadeloupe/` (column-name-aware)
split used by `eligibility_criteria`/`categorical_rules`.

### `core/data/zone_filter.py` (new)

```python
def resolve_kept_plots(
    plot_index: pd.Index,
    criteria: dict[str, pd.Series],   # {"islands": ..., "regions": ..., "farms": ..., "plots": ...}
    config: dict,
) -> pd.Index
```

- Each `criteria` value is a `pd.Series` aligned to `plot_index` giving the value to
  compare against the corresponding `include`/`exclude` list (for `"plots"`, the caller
  passes a series equal to the index itself).
- No-op (returns `plot_index` unchanged) when `config` has no `zone_filter` key.
- `include`: mask starts all-`True`; each non-empty criterion list ANDs it down via
  `series.isin(values)`.
- `exclude`: mask starts all-`False`; each non-empty criterion list ORs it up.
- Result: `plot_index[include_mask & ~exclude_mask]`.
- Raises `ValueError` if the result is empty.
- Logs a warning (not an error) for any id listed in an `include`/`exclude` criterion
  that matches zero plots in the corresponding series — catches typos (e.g. a wrong
  region code) without blocking legitimate filters.

### `case_studies/guadeloupe/data_pipeline.py`

`build_dataset` currently computes `plot_surface`/`farm_surface_ha`/`farm_plots` (lines
81-86) *before* `REGION_CODE` is assigned to `data_parc` (lines 88-90). This ordering
gets adjusted so the filter can use `REGION_CODE`:

1. Load `data_parc`, `expl_parc`, `bv_parc`, `reg_parc`, `cpt_parc` (unchanged).
2. Assign `REGION_CODE` to `data_parc` (moved earlier, otherwise unchanged).
3. Build `plot_to_farm = expl_parc.set_index("plot")["farm"].reindex(data_parc.index)`.
4. Call `resolve_kept_plots(data_parc.index, {"islands": data_parc["ILE"], "regions":
   data_parc["REGION_CODE"], "farms": plot_to_farm, "plots":
   pd.Series(data_parc.index, index=data_parc.index)}, config)`.
5. Filter `data_parc = data_parc.loc[kept]` and `expl_parc`/`bv_parc`/`reg_parc`/
   `cpt_parc` to rows whose `"plot"` is in `kept`.
6. Proceed with `plot_surface`, `farm_surface_ha`, `farm_plots`, `farm_gfa_surface_ha`,
   `base_crop_group`, `type_expl`, eligibility, etc. exactly as today, now operating on
   the filtered frames — every downstream aggregate (farm surfaces, risk aversion,
   eligibility, model `PLOTS`/`PAIRS`) is automatically consistent with the filtered
   universe with no further changes needed.

## Error handling

- `zone_filter` present but filters out every plot → `ValueError` with a message naming
  the active include/exclude criteria (not a silent empty model).
- Id in a filter list matching nothing → warning, not an error.
- Unknown key inside `zone_filter.include`/`.exclude` (typo, e.g. `region` instead of
  `regions`) → `KeyError`, consistent with how the rest of `config.yaml` fails on
  unknown names.

## Testing

- `core/data/zone_filter.py` unit tests: no `zone_filter` key (no-op), empty lists
  (no-op), include-only, exclude-only, include+exclude combined (exclude wins),
  multi-criterion include is AND, all-excluded raises, unmatched id warns, unknown key
  raises `KeyError`.
- `case_studies/guadeloupe/data_pipeline.py` integration test: real data, `zone_filter`
  restricting to one island — asserts `data_parc`/`expl_parc`/etc. are filtered
  consistently and `build_dataset` still produces a valid `Dataset`.
