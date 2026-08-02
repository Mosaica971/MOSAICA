# Config-driven optimization objects (constraints, objectives, solver, eligibility criteria)

## Goal

Let a user pick, without touching Python code, which optimization components are
mobilized to build a model: which constraints and objective are active, which solver
runs, and which agronomic eligibility criteria (altitude, slope, rainfall, plot size)
and categorical eligibility rules (irrigation, soil type, chlordecone risk) apply. This
is driven by a `config.yaml`, generic in `core/`, with a concrete instance per case
study.

## Non-goals

- No multi-objective weighted sum (exactly one objective must be enabled).
- No solver fallback list (exactly one solver config, not a list).
- No generalization of the categorical rules into an arbitrary boolean-expression DSL —
  they stay as a small set of parameterized, named Python functions.
- No change to the underlying optimization semantics of the existing constraint,
  objective, and eligibility logic — this is a refactor to make components
  selectable/configurable, not a modeling change.

## config.yaml schema

Lives at `case_studies/guadeloupe/config.yaml` for the Guadeloupe case study. Any future
case study provides its own file with the same schema.

```yaml
solver:
  name: appsi_highs          # passed to pyo.SolverFactory
  args: {}                   # forwarded as kwargs to solver.solve()

objectives:                  # exactly one entry must have enable: true
  - name: maximize_gross_margin
    enable: true
    args: {}

constraints:                 # zero or more entries with enable: true
  - name: at_most_one_crop_per_plot
    enable: true
    args: {}

eligibility_criteria:        # generic min/max agronomic envelope, zero or more enabled
  - name: altitude
    enable: true
    args: {attribute: ALTITUDE, min_col: ALTI_MIN, max_col: ALTI_MAX}
  - name: slope
    enable: true
    args: {attribute: PENTE, min_col: PENTE_MIN, max_col: PENTE_MAX}
  - name: rainfall
    enable: true
    args: {attribute: PLUVIO_PARC, min_col: PLUVIO_MIN, max_col: PLUVIO_MAX}
  - name: plot_size
    enable: true
    args: {attribute: SURF_HA, min_col: SURF_PARC_MIN, max_col: SURF_PARC_MAX}

categorical_rules:           # bespoke pandas conditions, zero or more enabled
  - name: irrigation_required
    enable: true
    args: {crops: [ME, MA_ROTA], irrigation_column: IRRIG_PARC}
  - name: soil_type_forbidden
    enable: true
    args: {crops: [AN_NU, AN_PA], soil_column: TYPE_SOL, forbidden_soil_types: [2]}
  - name: melon_soil_restriction
    enable: true
    args:
      crops: [ME]
      soil_column: TYPE_SOL
      forbidden_soil_types: [2, 3, 4]
      island_column: ILE
      forbidden_island: 1
  - name: max_risk_threshold
    enable: true
    args: {crops: [IG_TUT], risk_column: RISQUE_CLD, max_allowed: 3}
  - name: exact_risk_value
    enable: true
    args: {crops: [PN_PIQ], risk_column: RISQUE_CLD, allowed_value: 1}
```

`eligibility_criteria` is intentionally distinct from `constraints`: it filters the
(plot, crop) pairs before the Pyomo model exists, not a Pyomo component. `solver` is a
single dict (not a list) since only one solver is ever active.

Unknown `name` in a registry-backed section (`constraints`, `objectives`,
`categorical_rules`) raises `KeyError` listing the available registered names. Zero or
more than one enabled entry in `objectives` raises `ValueError`.

## Architecture

### New modules

- `core/config.py`
  - `load_config(path: str | Path) -> dict[str, Any]` — `yaml.safe_load`.
  - `resolve_enabled(entries: list[dict], registry: dict[str, Callable]) -> list[tuple[Callable, dict]]`
    — filters `enable: true` entries, resolves `name` against `registry`, pairs the
    callable with its `args` dict. Raises `KeyError` on unknown name.

- `core/model/registry.py`
  - `CONSTRAINT_REGISTRY: dict[str, Callable]`, `OBJECTIVE_REGISTRY: dict[str, Callable]`.
  - `register_constraint(name)`, `register_objective(name)` decorators. Raise if `name`
    is already registered (defensive, catches accidental duplicate names).

- `core/model/constraints.py`
  - Constraint builders registered via `@register_constraint(...)`. Signature:
    `(model: pyo.ConcreteModel, inputs: ModelInputs, **args) -> None`, mutates `model`
    in place.
  - Migrates `at_most_one_crop_per_plot` from the current `builder.py`.

- `core/model/objectives.py`
  - Objective builders registered via `@register_objective(...)`. Signature:
    `(model: pyo.ConcreteModel, inputs: ModelInputs, **args) -> None`, sets
    `model.objective`.
  - Migrates `maximize_gross_margin` from the current `builder.py`.

### Modified modules

- `core/model/builder.py`
  - Adds `ModelInputs` dataclass: `plot_surface_ha`, `crop_margin_per_ha`,
    `eligible_pairs` — the same three generic quantities the function takes today.
    Keeps `core/` agnostic of case-study-specific column/table names (e.g. `SURF_HA`,
    `data_parc`), which stay in `case_studies/guadeloupe/model.py`.
  - `build_crop_allocation_model(plot_surface_ha, crop_margin_per_ha, eligible_pairs, config)`:
    builds `PAIRS`/`PLOTS`/`Y` as today (structural, not config-gated), wraps the three
    inputs into a `ModelInputs`, then:
    - applies every enabled entry from `config["constraints"]` via
      `resolve_enabled(..., CONSTRAINT_REGISTRY)`, calling `fn(model, inputs, **args)`.
    - resolves `config["objectives"]`, asserts exactly one enabled entry, calls
      `fn(model, inputs, **args)`.

- `core/solve/solver.py`
  - `solve_model(model: pyo.ConcreteModel, config: dict) -> Any` replaces the
    `solver_name: str = "appsi_highs"` parameter. Reads `config["solver"]["name"]` and
    `config["solver"].get("args", {})`, passes `name` to `pyo.SolverFactory` (already a
    registry — no custom solver registry needed) and forwards `args` as kwargs to
    `solver.solve(model, load_solutions=False, **args)`.

- `core/data/eligibility.py`
  - Adds `CATEGORICAL_RULE_REGISTRY` + `register_categorical_rule(name)` decorator.
  - Adds the 5 generic rule functions, each `(data_parc: pd.DataFrame, **args) -> tuple[list[str], pd.Series]`,
    with required (no-default) kwargs so no case-study-specific column name is hardcoded
    in `core/`:
    - `irrigation_required(data_parc, *, crops, irrigation_column)`
    - `soil_type_forbidden(data_parc, *, crops, soil_column, forbidden_soil_types)`
    - `melon_soil_restriction(data_parc, *, crops, soil_column, forbidden_soil_types, island_column, forbidden_island)`
    - `max_risk_threshold(data_parc, *, crops, risk_column, max_allowed)`
    - `exact_risk_value(data_parc, *, crops, risk_column, allowed_value)`
  - Adds `attribute_bounds_from_config(entries: list[dict]) -> dict[str, tuple[str, str]]`
    — turns the enabled `eligibility_criteria` entries into the
    `{attribute: (min_col, max_col)}` shape `compute_eligibility_mask` already accepts.

- `case_studies/guadeloupe/data_pipeline.py`
  - `build_dataset(config: dict) -> Dataset` replaces the hardcoded
    `ELIGIBILITY_ATTRIBUTE_BOUNDS` dict with
    `attribute_bounds_from_config(config["eligibility_criteria"])`.
  - Replaces `build_categorical_eligibility_rules(data_parc)` with a loop over
    `resolve_enabled(config["categorical_rules"], CATEGORICAL_RULE_REGISTRY)` calling
    each `fn(data_parc, **args)` and feeding the result into `forbid_where` as today.

- `case_studies/guadeloupe/model.py`
  - `build_model(dataset: Dataset, config: dict) -> pyo.ConcreteModel` passes `config`
    through to `build_crop_allocation_model`.

- `main.py`
  - Loads `config.yaml` once via `load_config`, passes it to `build_dataset`,
    `build_model`, `solve_model`.

- `pyproject.toml`
  - Adds `pyyaml` to `dependencies`.

## Error handling

- Unknown `name` in `constraints` / `objectives` / `categorical_rules` → `KeyError`
  listing available registered names.
- `objectives` section with 0 or ≥2 enabled entries → `ValueError` with an explicit
  message.
- Duplicate registration of the same name in a registry (programming error, not a config
  error) → raised at import time by the `register_*` decorators.

## Testing

Existing tests (`test_model_builder.py`, `test_model_solver.py`, `test_eligibility.py`,
`test_guadeloupe_pipeline.py`, `test_guadeloupe_model.py`, `test_main.py`) are updated to
pass a `config` dict (either the real `case_studies/guadeloupe/config.yaml` or a minimal
in-memory dict) instead of the previous positional/keyword parameters they replace. New
tests cover: `resolve_enabled` (enable filtering, unknown-name error), the
exactly-one-objective validation, and each of the 5 categorical rule functions with
representative inputs.
