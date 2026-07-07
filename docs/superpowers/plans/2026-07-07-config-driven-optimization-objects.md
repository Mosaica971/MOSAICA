# Config-driven optimization objects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let constraints, the objective, the solver, and agronomic eligibility criteria be selected and parameterized from `case_studies/guadeloupe/config.yaml` instead of hardcoded Python, via a small registry mechanism in `core/`.

**Architecture:** Named builder functions for constraints/objectives/categorical eligibility rules are registered in module-level dicts via decorators. `core/config.py` loads the YAML and resolves `{name, enable, args}` entries against a registry into `(callable, args)` pairs. `core/model/builder.py` and `case_studies/guadeloupe/data_pipeline.py` call the resolved callables with `**args`. Generic min/max agronomic bounds (`eligibility_criteria`) are pure config data, not registry-backed, since they parameterize one existing generic function rather than selecting between named behaviors.

**Tech Stack:** Python 3.10+, Pyomo, pandas, PyYAML (new), pytest.

## Global Constraints

- Python >= 3.10 (per `pyproject.toml` `requires-python`).
- New dependency `pyyaml` must be added to `pyproject.toml` `[project.dependencies]`.
- `objectives` config section: exactly one entry with `enable: true` is required; 0 or ≥2 is a `ValueError`.
- `constraints`, `eligibility_criteria`, `categorical_rules` config sections: 0 or more entries with `enable: true` allowed.
- `solver` config section is a single dict (`name` + `args`), never a list.
- Unknown `name` in a registry-backed section raises `KeyError` listing available registered names.
- `core/` modules must never hardcode a Guadeloupe-specific column/table name (e.g. `SURF_HA`, `IRRIG_PARC`, `TYPE_SOL`, `RISQUE_CLD`, `ILE`) — those only appear in `case_studies/guadeloupe/config.yaml` and `case_studies/guadeloupe/model.py`.
- Run tests with `.venv/Scripts/python.exe -m pytest <path> -v` from the repo root.

---

### Task 1: PyYAML dependency and `core/config.py`

**Files:**
- Modify: `pyproject.toml`
- Create: `core/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: str | Path) -> dict[str, Any]`, `resolve_enabled(entries: list[dict[str, Any]], registry: dict[str, Callable]) -> list[tuple[Callable, dict[str, Any]]]`.

- [ ] **Step 1: Add `pyyaml` to `pyproject.toml` dependencies**

Edit `pyproject.toml` so the `dependencies` list reads:

```toml
dependencies = [
    "pandas>=2.0",
    "pyomo>=6.7",
    "highspy>=1.7",
    "pyyaml>=6.0",
]
```

- [ ] **Step 2: Install the new dependency**

Run: `.venv/Scripts/python.exe -m pip install pyyaml>=6.0`
Expected: pip reports `Successfully installed pyyaml-...`

- [ ] **Step 3: Write the failing test**

Create `tests/test_config.py`:

```python
import pytest
import yaml

from core.config import load_config, resolve_enabled


def test_load_config_parses_yaml_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"solver": {"name": "appsi_highs", "args": {}}}))

    config = load_config(config_path)

    assert config == {"solver": {"name": "appsi_highs", "args": {}}}


def test_resolve_enabled_returns_only_enabled_entries_paired_with_args():
    registry = {"foo": lambda **kwargs: kwargs, "bar": lambda **kwargs: kwargs}
    entries = [
        {"name": "foo", "enable": True, "args": {"x": 1}},
        {"name": "bar", "enable": False, "args": {"y": 2}},
    ]

    resolved = resolve_enabled(entries, registry)

    assert len(resolved) == 1
    fn, args = resolved[0]
    assert fn is registry["foo"]
    assert args == {"x": 1}


def test_resolve_enabled_defaults_missing_args_to_empty_dict():
    registry = {"foo": lambda **kwargs: kwargs}
    entries = [{"name": "foo", "enable": True}]

    resolved = resolve_enabled(entries, registry)

    assert resolved == [(registry["foo"], {})]


def test_resolve_enabled_raises_key_error_for_unknown_name():
    registry = {"foo": lambda **kwargs: kwargs}
    entries = [{"name": "unknown", "enable": True}]

    with pytest.raises(KeyError, match="unknown"):
        resolve_enabled(entries, registry)
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.config'`

- [ ] **Step 5: Implement `core/config.py`**

Create `core/config.py`:

```python
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_enabled(
    entries: list[dict[str, Any]], registry: dict[str, Callable]
) -> list[tuple[Callable, dict[str, Any]]]:
    resolved = []
    for entry in entries:
        if not entry.get("enable", False):
            continue
        name = entry["name"]
        if name not in registry:
            available = ", ".join(sorted(registry))
            raise KeyError(f"Unknown component '{name}'. Available: {available}")
        resolved.append((registry[name], entry.get("args") or {}))
    return resolved
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_config.py -v`
Expected: PASS (4 tests)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml core/config.py tests/test_config.py
git commit -m "Add YAML config loader and enable/args resolver"
```

---

### Task 2: `ModelInputs` and the constraint/objective registry

**Files:**
- Create: `core/model/model_inputs.py`
- Create: `core/model/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `ModelInputs` dataclass (`plot_surface_ha`, `crop_margin_per_ha`, `eligible_pairs`); `CONSTRAINT_REGISTRY: dict[str, Callable]`, `OBJECTIVE_REGISTRY: dict[str, Callable]`, `register_constraint(name: str)`, `register_objective(name: str)` decorators.

- [ ] **Step 1: Write the failing test**

Create `tests/test_registry.py`:

```python
import pytest

from core.model.registry import (
    CONSTRAINT_REGISTRY,
    OBJECTIVE_REGISTRY,
    register_constraint,
    register_objective,
)


def test_register_constraint_adds_function_to_constraint_registry():
    @register_constraint("test_dummy_constraint")
    def dummy(model, inputs, **args):
        return None

    try:
        assert CONSTRAINT_REGISTRY["test_dummy_constraint"] is dummy
    finally:
        del CONSTRAINT_REGISTRY["test_dummy_constraint"]


def test_register_constraint_raises_on_duplicate_name():
    @register_constraint("test_dummy_duplicate")
    def dummy(model, inputs, **args):
        return None

    try:
        with pytest.raises(ValueError, match="already registered"):

            @register_constraint("test_dummy_duplicate")
            def dummy2(model, inputs, **args):
                return None
    finally:
        del CONSTRAINT_REGISTRY["test_dummy_duplicate"]


def test_register_objective_adds_function_to_objective_registry():
    @register_objective("test_dummy_objective")
    def dummy(model, inputs, **args):
        return None

    try:
        assert OBJECTIVE_REGISTRY["test_dummy_objective"] is dummy
    finally:
        del OBJECTIVE_REGISTRY["test_dummy_objective"]


def test_register_objective_raises_on_duplicate_name():
    @register_objective("test_dummy_objective_duplicate")
    def dummy(model, inputs, **args):
        return None

    try:
        with pytest.raises(ValueError, match="already registered"):

            @register_objective("test_dummy_objective_duplicate")
            def dummy2(model, inputs, **args):
                return None
    finally:
        del OBJECTIVE_REGISTRY["test_dummy_objective_duplicate"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.model.registry'`

- [ ] **Step 3: Implement `core/model/model_inputs.py`**

Create `core/model/model_inputs.py`:

```python
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass
class ModelInputs:
    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
```

- [ ] **Step 4: Implement `core/model/registry.py`**

Create `core/model/registry.py`:

```python
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)

CONSTRAINT_REGISTRY: dict[str, Callable] = {}
OBJECTIVE_REGISTRY: dict[str, Callable] = {}


def _make_register(registry: dict[str, Callable]) -> Callable[[str], Callable[[F], F]]:
    def register(name: str) -> Callable[[F], F]:
        def decorator(fn: F) -> F:
            if name in registry:
                raise ValueError(f"'{name}' is already registered")
            registry[name] = fn
            return fn

        return decorator

    return register


register_constraint = _make_register(CONSTRAINT_REGISTRY)
register_objective = _make_register(OBJECTIVE_REGISTRY)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_registry.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add core/model/model_inputs.py core/model/registry.py tests/test_registry.py
git commit -m "Add ModelInputs and the constraint/objective registry"
```

---

### Task 3: Registered constraint/objective builders and config-driven `build_crop_allocation_model`

**Files:**
- Create: `core/model/constraints.py`
- Create: `core/model/objectives.py`
- Modify: `core/model/builder.py` (full rewrite)
- Test: `tests/test_model_builder.py` (full rewrite)

**Interfaces:**
- Consumes: `resolve_enabled` from `core/config.py` (Task 1); `ModelInputs`, `CONSTRAINT_REGISTRY`, `OBJECTIVE_REGISTRY`, `register_constraint`, `register_objective` from `core/model/model_inputs.py` and `core/model/registry.py` (Task 2).
- Produces: `build_crop_allocation_model(plot_surface_ha: Mapping[str, float], crop_margin_per_ha: Mapping[str, float], eligible_pairs: Sequence[tuple[str, str]], config: dict[str, Any]) -> pyo.ConcreteModel`. Registers `"at_most_one_crop_per_plot"` in `CONSTRAINT_REGISTRY` and `"maximize_gross_margin"` in `OBJECTIVE_REGISTRY`.

- [ ] **Step 1: Rewrite the failing test**

Replace `tests/test_model_builder.py` with:

```python
import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model

CONFIG = {
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_build_model_creates_binary_variable_only_for_eligible_pairs():
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
        config=CONFIG,
    )

    assert set(model.Y.keys()) == set(eligible_pairs)
    for index in model.Y:
        assert model.Y[index].domain is pyo.Binary


def test_solving_model_picks_most_profitable_eligible_crop_per_plot():
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
        config=CONFIG,
    )

    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    assert pyo.value(model.Y["P1", "C1"]) == pytest.approx(0)
    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.Y["P2", "C1"]) == pytest.approx(1)
    assert pyo.value(model.objective) == pytest.approx(1.0 * 200.0 + 2.0 * 100.0)


def test_at_most_one_crop_per_plot_constraint_rejects_two_crops_at_once():
    eligible_pairs = [("P1", "C1"), ("P1", "C2")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
        config=CONFIG,
    )

    constraint = model.at_most_one_crop_per_plot["P1"]
    model.Y["P1", "C1"].fix(1)
    model.Y["P1", "C2"].fix(1)

    assert pyo.value(constraint.body) == pytest.approx(2)
    assert constraint.upper() == pytest.approx(1)


def test_build_model_skips_disabled_constraints():
    config = {
        "constraints": [{"name": "at_most_one_crop_per_plot", "enable": False, "args": {}}],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=config,
    )

    assert not hasattr(model, "at_most_one_crop_per_plot")


def test_build_model_raises_when_no_objective_enabled():
    config = {
        "constraints": [],
        "objectives": [{"name": "maximize_gross_margin", "enable": False, "args": {}}],
    }

    with pytest.raises(ValueError, match="exactly one enabled objective"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_build_model_raises_when_multiple_objectives_enabled():
    config = {
        "constraints": [],
        "objectives": [
            {"name": "maximize_gross_margin", "enable": True, "args": {}},
            {"name": "maximize_gross_margin", "enable": True, "args": {}},
        ],
    }

    with pytest.raises(ValueError, match="exactly one enabled objective"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_build_model_raises_for_unknown_constraint_name():
    config = {
        "constraints": [{"name": "not_a_real_constraint", "enable": True, "args": {}}],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    with pytest.raises(KeyError, match="not_a_real_constraint"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: FAIL with `TypeError: build_crop_allocation_model() missing 1 required positional argument: 'config'`

- [ ] **Step 3: Implement `core/model/constraints.py`**

Create `core/model/constraints.py`:

```python
from collections import defaultdict

import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_constraint


@register_constraint("at_most_one_crop_per_plot")
def build_at_most_one_crop_per_plot_constraint(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    plots_to_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        plots_to_crops[plot].append(crop)

    def _rule(model, plot):
        return sum(model.Y[plot, crop] for crop in plots_to_crops[plot]) <= 1

    model.at_most_one_crop_per_plot = pyo.Constraint(model.PLOTS, rule=_rule)
```

- [ ] **Step 4: Implement `core/model/objectives.py`**

Create `core/model/objectives.py`:

```python
import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_objective


@register_objective("maximize_gross_margin")
def build_maximize_gross_margin_objective(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * inputs.crop_margin_per_ha[crop]
            for plot, crop in inputs.eligible_pairs
        ),
        sense=pyo.maximize,
    )
```

- [ ] **Step 5: Rewrite `core/model/builder.py`**

Replace `core/model/builder.py` with:

```python
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import pyomo.environ as pyo

from core.config import resolve_enabled
from core.model import constraints as _constraints  # noqa: F401 (registers builders)
from core.model import objectives as _objectives  # noqa: F401 (registers builders)
from core.model.model_inputs import ModelInputs
from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY


def build_crop_allocation_model(
    plot_surface_ha: Mapping[str, float],
    crop_margin_per_ha: Mapping[str, float],
    eligible_pairs: Sequence[tuple[str, str]],
    config: dict[str, Any],
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()

    plots_to_crops = defaultdict(list)
    for plot, crop in eligible_pairs:
        plots_to_crops[plot].append(crop)

    model.PAIRS = pyo.Set(initialize=list(eligible_pairs), dimen=2)
    model.PLOTS = pyo.Set(initialize=list(plots_to_crops.keys()))
    model.Y = pyo.Var(model.PAIRS, within=pyo.Binary)

    inputs = ModelInputs(
        plot_surface_ha=plot_surface_ha,
        crop_margin_per_ha=crop_margin_per_ha,
        eligible_pairs=eligible_pairs,
    )

    for build_constraint, args in resolve_enabled(config["constraints"], CONSTRAINT_REGISTRY):
        build_constraint(model, inputs, **args)

    enabled_objectives = resolve_enabled(config["objectives"], OBJECTIVE_REGISTRY)
    if len(enabled_objectives) != 1:
        raise ValueError(
            f"Expected exactly one enabled objective, got {len(enabled_objectives)}"
        )
    build_objective, args = enabled_objectives[0]
    build_objective(model, inputs, **args)

    return model
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_builder.py -v`
Expected: PASS (7 tests)

- [ ] **Step 7: Commit**

```bash
git add core/model/constraints.py core/model/objectives.py core/model/builder.py tests/test_model_builder.py
git commit -m "Make build_crop_allocation_model config-driven via the registry"
```

---

### Task 4: Config-driven `solve_model`

**Files:**
- Modify: `core/model/solver.py` (full rewrite)
- Test: `tests/test_model_solver.py` (full rewrite)

**Interfaces:**
- Consumes: `build_crop_allocation_model(..., config: dict[str, Any])` from Task 3.
- Produces: `solve_model(model: pyo.ConcreteModel, config: dict[str, Any]) -> Any`.

- [ ] **Step 1: Rewrite the failing test**

Replace `tests/test_model_solver.py` with:

```python
import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model
from core.model.solver import solve_model

CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_solve_model_returns_optimal_solved_model():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=CONFIG,
    )

    solve_model(model, CONFIG)

    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.objective) == pytest.approx(200.0)


def test_solve_model_raises_on_infeasible_model():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1")],
        config=CONFIG,
    )
    model.Y["P1", "C1"].fix(1)
    model.infeasible_constraint = pyo.Constraint(expr=model.Y["P1", "C1"] == 0)

    with pytest.raises(RuntimeError, match="optimal"):
        solve_model(model, CONFIG)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_solver.py -v`
Expected: FAIL with `TypeError: solve_model() missing 1 required positional argument: 'config'`

- [ ] **Step 3: Rewrite `core/model/solver.py`**

Replace `core/model/solver.py` with:

```python
from typing import Any

import pyomo.environ as pyo


def solve_model(model: pyo.ConcreteModel, config: dict[str, Any]) -> Any:
    solver_config = config["solver"]
    solver_name = solver_config["name"]
    args = solver_config.get("args") or {}

    solver = pyo.SolverFactory(solver_name)
    results = solver.solve(model, load_solutions=False, **args)

    condition = results.solver.termination_condition
    if condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(
            f"Solver '{solver_name}' did not reach an optimal solution "
            f"(termination condition: {condition})"
        )

    model.solutions.load_from(results)
    return results
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_model_solver.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add core/model/solver.py tests/test_model_solver.py
git commit -m "Make solve_model read the solver name and args from config"
```

---

### Task 5: Categorical eligibility rule registry and generic bounds helper

**Files:**
- Modify: `core/data/eligibility.py`
- Test: `tests/test_eligibility.py` (append)

**Interfaces:**
- Consumes: nothing new (pandas only).
- Produces: `CATEGORICAL_RULE_REGISTRY: dict[str, Callable]`, `register_categorical_rule(name: str)`; rule functions `rule_irrigation_required`, `rule_soil_type_forbidden`, `rule_melon_soil_restriction`, `rule_max_risk_threshold`, `rule_exact_risk_value`, each `(data_parc: pd.DataFrame, **args) -> tuple[list[str], pd.Series]`; `attribute_bounds_from_config(entries: list[dict]) -> dict[str, tuple[str, str]]`.

- [ ] **Step 1: Append the failing tests**

In `tests/test_eligibility.py`, replace the existing import block:

```python
from core.data.eligibility import (
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
)
```

with:

```python
from core.data.eligibility import (
    attribute_bounds_from_config,
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
    rule_exact_risk_value,
    rule_irrigation_required,
    rule_max_risk_threshold,
    rule_melon_soil_restriction,
    rule_soil_type_forbidden,
)
```

Keep the 3 existing test functions unchanged, then append these new tests at the end of the file:

```python
def test_rule_irrigation_required_forbids_crops_without_irrigation():
    data_parc = pd.DataFrame({"IRRIG_PARC": [0, 1]}, index=["P1", "P2"])

    crops, condition = rule_irrigation_required(
        data_parc, crops=["ME"], irrigation_column="IRRIG_PARC"
    )

    assert crops == ["ME"]
    assert condition.tolist() == [True, False]


def test_rule_soil_type_forbidden_matches_listed_soil_types():
    data_parc = pd.DataFrame({"TYPE_SOL": [2, 3]}, index=["P1", "P2"])

    crops, condition = rule_soil_type_forbidden(
        data_parc, crops=["AN_NU"], soil_column="TYPE_SOL", forbidden_soil_types=[2]
    )

    assert crops == ["AN_NU"]
    assert condition.tolist() == [True, False]


def test_rule_melon_soil_restriction_matches_soil_type_or_island():
    data_parc = pd.DataFrame(
        {"TYPE_SOL": [2, 1, 1], "ILE": [0, 1, 0]}, index=["P1", "P2", "P3"]
    )

    crops, condition = rule_melon_soil_restriction(
        data_parc,
        crops=["ME"],
        soil_column="TYPE_SOL",
        forbidden_soil_types=[2, 3, 4],
        island_column="ILE",
        forbidden_island=1,
    )

    assert crops == ["ME"]
    assert condition.tolist() == [True, True, False]


def test_rule_max_risk_threshold_forbids_values_at_or_below_threshold():
    data_parc = pd.DataFrame({"RISQUE_CLD": [3, 4]}, index=["P1", "P2"])

    crops, condition = rule_max_risk_threshold(
        data_parc, crops=["IG_TUT"], risk_column="RISQUE_CLD", max_allowed=3
    )

    assert crops == ["IG_TUT"]
    assert condition.tolist() == [True, False]


def test_rule_exact_risk_value_forbids_the_matching_value():
    data_parc = pd.DataFrame({"RISQUE_CLD": [1, 2]}, index=["P1", "P2"])

    crops, condition = rule_exact_risk_value(
        data_parc, crops=["PN_PIQ"], risk_column="RISQUE_CLD", allowed_value=1
    )

    assert crops == ["PN_PIQ"]
    assert condition.tolist() == [True, False]


def test_attribute_bounds_from_config_keeps_only_enabled_entries():
    entries = [
        {
            "name": "altitude",
            "enable": True,
            "args": {"attribute": "ALTITUDE", "min_col": "ALTI_MIN", "max_col": "ALTI_MAX"},
        },
        {
            "name": "slope",
            "enable": False,
            "args": {"attribute": "PENTE", "min_col": "PENTE_MIN", "max_col": "PENTE_MAX"},
        },
    ]

    bounds = attribute_bounds_from_config(entries)

    assert bounds == {"ALTITUDE": ("ALTI_MIN", "ALTI_MAX")}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_eligibility.py -v`
Expected: FAIL with `ImportError: cannot import name 'rule_irrigation_required' from 'core.data.eligibility'`

- [ ] **Step 3: Append to `core/data/eligibility.py`**

In `core/data/eligibility.py`, replace the top import line:

```python
import pandas as pd
```

with:

```python
from collections.abc import Callable

import pandas as pd
```

Keep `compute_eligibility_mask`, `forbid_where`, `eligible_pairs_from_mask` unchanged, then append to the end of the file:

```python
CATEGORICAL_RULE_REGISTRY: dict[str, Callable] = {}


def register_categorical_rule(name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        if name in CATEGORICAL_RULE_REGISTRY:
            raise ValueError(f"'{name}' is already registered")
        CATEGORICAL_RULE_REGISTRY[name] = fn
        return fn

    return decorator


@register_categorical_rule("irrigation_required")
def rule_irrigation_required(
    data_parc: pd.DataFrame, *, crops: list[str], irrigation_column: str
) -> tuple[list[str], pd.Series]:
    condition = data_parc[irrigation_column] == 0
    return crops, condition


@register_categorical_rule("soil_type_forbidden")
def rule_soil_type_forbidden(
    data_parc: pd.DataFrame,
    *,
    crops: list[str],
    soil_column: str,
    forbidden_soil_types: list[int],
) -> tuple[list[str], pd.Series]:
    condition = data_parc[soil_column].isin(forbidden_soil_types)
    return crops, condition


@register_categorical_rule("melon_soil_restriction")
def rule_melon_soil_restriction(
    data_parc: pd.DataFrame,
    *,
    crops: list[str],
    soil_column: str,
    forbidden_soil_types: list[int],
    island_column: str,
    forbidden_island: int,
) -> tuple[list[str], pd.Series]:
    condition = data_parc[soil_column].isin(forbidden_soil_types) | (
        data_parc[island_column] == forbidden_island
    )
    return crops, condition


@register_categorical_rule("max_risk_threshold")
def rule_max_risk_threshold(
    data_parc: pd.DataFrame, *, crops: list[str], risk_column: str, max_allowed: float
) -> tuple[list[str], pd.Series]:
    condition = data_parc[risk_column] <= max_allowed
    return crops, condition


@register_categorical_rule("exact_risk_value")
def rule_exact_risk_value(
    data_parc: pd.DataFrame, *, crops: list[str], risk_column: str, allowed_value: float
) -> tuple[list[str], pd.Series]:
    condition = data_parc[risk_column] == allowed_value
    return crops, condition


def attribute_bounds_from_config(entries: list[dict]) -> dict[str, tuple[str, str]]:
    return {
        entry["args"]["attribute"]: (entry["args"]["min_col"], entry["args"]["max_col"])
        for entry in entries
        if entry.get("enable", False)
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_eligibility.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add core/data/eligibility.py tests/test_eligibility.py
git commit -m "Add categorical eligibility rule registry and attribute_bounds_from_config"
```

---

### Task 6: `case_studies/guadeloupe/config.yaml`

**Files:**
- Create: `case_studies/guadeloupe/config.yaml`
- Test: `tests/test_guadeloupe_config.py`

**Interfaces:**
- Consumes: `load_config` from Task 1.
- Produces: the concrete YAML config file used by the remaining tasks.

- [ ] **Step 1: Write the failing test**

Create `tests/test_guadeloupe_config.py`:

```python
from pathlib import Path

from core.config import load_config

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
)


def test_guadeloupe_config_loads_and_has_expected_sections():
    config = load_config(CONFIG_PATH)

    assert config["solver"]["name"] == "appsi_highs"
    assert [e["name"] for e in config["objectives"] if e["enable"]] == [
        "maximize_gross_margin"
    ]
    assert [e["name"] for e in config["constraints"] if e["enable"]] == [
        "at_most_one_crop_per_plot"
    ]
    assert {
        e["args"]["attribute"] for e in config["eligibility_criteria"] if e["enable"]
    } == {"ALTITUDE", "PENTE", "PLUVIO_PARC", "SURF_HA"}
    assert {e["name"] for e in config["categorical_rules"] if e["enable"]} == {
        "irrigation_required",
        "soil_type_forbidden",
        "melon_soil_restriction",
        "max_risk_threshold",
        "exact_risk_value",
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_config.py -v`
Expected: FAIL with `FileNotFoundError` (config.yaml does not exist yet)

- [ ] **Step 3: Create `case_studies/guadeloupe/config.yaml`**

Create `case_studies/guadeloupe/config.yaml`:

```yaml
solver:
  name: appsi_highs
  args: {}

objectives:
  - name: maximize_gross_margin
    enable: true
    args: {}

constraints:
  - name: at_most_one_crop_per_plot
    enable: true
    args: {}

eligibility_criteria:
  - name: altitude
    enable: true
    args:
      attribute: ALTITUDE
      min_col: ALTI_MIN
      max_col: ALTI_MAX
  - name: slope
    enable: true
    args:
      attribute: PENTE
      min_col: PENTE_MIN
      max_col: PENTE_MAX
  - name: rainfall
    enable: true
    args:
      attribute: PLUVIO_PARC
      min_col: PLUVIO_MIN
      max_col: PLUVIO_MAX
  - name: plot_size
    enable: true
    args:
      attribute: SURF_HA
      min_col: SURF_PARC_MIN
      max_col: SURF_PARC_MAX

categorical_rules:
  - name: irrigation_required
    enable: true
    args:
      crops: [ME, MA_ROTA]
      irrigation_column: IRRIG_PARC
  - name: soil_type_forbidden
    enable: true
    args:
      crops: [AN_NU, AN_PA]
      soil_column: TYPE_SOL
      forbidden_soil_types: [2]
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
    args:
      crops: [IG_TUT]
      risk_column: RISQUE_CLD
      max_allowed: 3
  - name: exact_risk_value
    enable: true
    args:
      crops: [PN_PIQ]
      risk_column: RISQUE_CLD
      allowed_value: 1
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_config.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/config.yaml tests/test_guadeloupe_config.py
git commit -m "Add the Guadeloupe case study config.yaml"
```

---

### Task 7: Config-driven `build_dataset` and `display_datasets.py`

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py` (full rewrite)
- Modify: `display_datasets.py` (full rewrite)
- Test: `tests/test_guadeloupe_pipeline.py` (full rewrite)

**Interfaces:**
- Consumes: `resolve_enabled`, `load_config` from Task 1; `CATEGORICAL_RULE_REGISTRY`, `attribute_bounds_from_config` from Task 5; `case_studies/guadeloupe/config.yaml` from Task 6.
- Produces: `build_dataset(config: dict[str, Any]) -> Dataset` (replaces the old no-arg signature); `compute_farm_surface_ha` unchanged.

- [ ] **Step 1: Rewrite the failing test**

Replace `tests/test_guadeloupe_pipeline.py` with:

```python
from pathlib import Path

import pandas as pd
import pytest

from case_studies.guadeloupe.data_pipeline import build_dataset, compute_farm_surface_ha
from core.config import load_config

CONFIG = load_config(
    Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
)


def test_compute_farm_surface_ha_sums_plot_surface_per_farm():
    plot_surface = pd.Series({"P1": 3.68, "P2": 3.3, "P3": 1.36, "P4": 1.24})
    expl_parc = pd.DataFrame(
        {
            "farm": ["E1", "E1", "E1", "E2"],
            "plot": ["P1", "P2", "P3", "P4"],
        }
    )

    result = compute_farm_surface_ha(plot_surface, expl_parc)

    assert result["E1"] == 3.68 + 3.3 + 1.36
    assert result["E2"] == 1.24


def test_build_dataset_loads_known_set_sizes():
    dataset = build_dataset(CONFIG)

    assert len(dataset.sets["crops"]) == 84
    assert len(dataset.sets["soils"]) == 5
    assert len(dataset.sets["otk"]) == 189
    assert len(dataset.parameters["expl_parc"]) == 24734
    assert dataset.parameters["expl_parc"]["farm"].nunique() == 4638


def test_build_dataset_computes_farm_surface_ha_matching_gams_init_logic():
    dataset = build_dataset(CONFIG)

    farm_surface_ha = dataset.parameters["farm_surface_ha"]

    assert farm_surface_ha["E1"] == pytest.approx(3.68 + 3.3 + 1.36)
    assert farm_surface_ha["E2"] == pytest.approx(1.24)


def test_build_dataset_selects_2017_column_for_price_and_yield():
    dataset = build_dataset(CONFIG)

    assert dataset.parameters["prix_cult"]["AG"] == pytest.approx(700)
    assert dataset.parameters["rdt_cult"]["AG"] == pytest.approx(20)


def test_build_dataset_computes_eligibility_mask_from_agronomic_bounds():
    dataset = build_dataset(CONFIG)

    mask = dataset.parameters["eligibility_mask"]

    # P1: altitude 23, pente 1, pluvio 1483 -- within CS's bounds (alti<=250, pente<=20)
    assert mask.loc["P1", "CS"] == True  # noqa: E712
    # P2483: altitude 301 -- exceeds CS's ALTI_MAX of 250
    assert mask.loc["P2483", "CS"] == False  # noqa: E712

    eligible_pairs = dataset.parameters["eligible_pairs"]
    total_pairs = mask.shape[0] * mask.shape[1]
    assert 0 < len(eligible_pairs) < total_pairs


def test_build_dataset_computes_gross_margin_per_ha_cult():
    dataset = build_dataset(CONFIG)

    margin_per_ha_cult = dataset.parameters["margin_per_ha_cult"]

    # AG: PB=rdt*prix=20*700=14000 (no subsidies/bagasse for citrus), CV~8001.31
    # from OTK variable costs -- hand-verified via a one-off script using
    # case_studies.guadeloupe.economics against the real data tables.
    assert margin_per_ha_cult["AG"] == pytest.approx(5998.69, abs=0.01)


def test_build_dataset_applies_guadeloupe_categorical_eligibility_rules():
    dataset = build_dataset(CONFIG)

    mask = dataset.parameters["eligibility_mask"]

    # P5: IRRIG_PARC=0 -- melon requires irrigation (Eq_ME_IRR)
    assert mask.loc["P5", "ME"] == False  # noqa: E712
    # P78: RISQUE_CLD=3 (<=3) -- irrigated yam forbidden on CLD-polluted soils (Eq_IG_CLD)
    assert mask.loc["P78", "IG_TUT"] == False  # noqa: E712
    # P366: TYPE_SOL=2 (calcareous) -- pineapple forbidden on calcareous soil (Eq_AN_SOL_Parc)
    assert mask.loc["P366", "AN_NU"] == False  # noqa: E712


def test_build_dataset_skips_disabled_categorical_rule():
    config = {**CONFIG, "categorical_rules": [
        {**entry, "enable": False} for entry in CONFIG["categorical_rules"]
    ]}

    dataset = build_dataset(config)

    mask = dataset.parameters["eligibility_mask"]

    # P5 would be forbidden for ME by irrigation_required, but that rule is disabled here.
    assert mask.loc["P5", "ME"] == True  # noqa: E712
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py -v`
Expected: FAIL with `TypeError: build_dataset() takes 0 positional arguments but 1 was given`

- [ ] **Step 3: Rewrite `case_studies/guadeloupe/data_pipeline.py`**

Replace `case_studies/guadeloupe/data_pipeline.py` with:

```python
from pathlib import Path
from typing import Any

import pandas as pd

from case_studies.guadeloupe.economics import (
    compute_gross_margin_per_ha_cult,
    compute_gross_product_per_ha_cult,
    compute_subsidy_per_ha_cult,
    compute_variable_cost_per_ha_cult,
)
from core.config import load_config, resolve_enabled
from core.data.dataset import Dataset
from core.data.eligibility import (
    CATEGORICAL_RULE_REGISTRY,
    attribute_bounds_from_config,
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
)
from core.data.readers import read_flat_set, read_mapping_set, read_wide_table

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SETS_DIR = DATA_DIR / "sets"
TABLES_DIR = DATA_DIR / "tables"
INDICE_H_DIR = TABLES_DIR / "indice_H"
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

YEAR = "2017"
SCENARIO = "RESTIT"


def compute_farm_surface_ha(plot_surface: pd.Series, expl_parc: pd.DataFrame) -> pd.Series:
    merged = expl_parc.assign(surface=expl_parc["plot"].map(plot_surface))
    return merged.groupby("farm")["surface"].sum()


def build_dataset(config: dict[str, Any]) -> Dataset:
    sets = {
        "crops": read_flat_set(SETS_DIR / "CULT_2017.set"),
        "soils": read_flat_set(SETS_DIR / "SOL.set"),
        "otk": read_flat_set(SETS_DIR / "OTK.set"),
        "watersheds": read_flat_set(SETS_DIR / "BV_2017.set"),
        "catchments": read_flat_set(SETS_DIR / "CPT_2017.set"),
    }

    expl_parc = read_mapping_set(SETS_DIR / "EXPL_PARC_2017.set", "farm", "plot")
    bv_parc = read_mapping_set(SETS_DIR / "BV_PARC_2017.set", "watershed", "plot")
    reg_parc = read_mapping_set(SETS_DIR / "REG_PARC_2017.set", "region", "plot")
    cpt_parc = read_mapping_set(SETS_DIR / "CPT_PARC_2017.set", "catchment", "plot")

    data_parc = read_wide_table(TABLES_DIR / "Data_Parc_Gwad_2017.txt")
    data_cult = read_wide_table(TABLES_DIR / "Data_Cult.txt")
    data_otk = read_wide_table(TABLES_DIR / "Data_OTK.txt")
    matrice_otk_cult = read_wide_table(TABLES_DIR / f"Matrice_OTK_Cult_{SCENARIO}.txt")
    prix_cult = read_wide_table(INDICE_H_DIR / "Prix_Cult.txt")[YEAR]
    rdt_cult = read_wide_table(INDICE_H_DIR / "Rdt_Cult.txt")[YEAR]
    bagasse_cult = read_wide_table(INDICE_H_DIR / "Bagasse_Cult.txt")[YEAR]
    duree_plant_cult = read_wide_table(INDICE_H_DIR / "Duree_Plant_Cult.txt")[YEAR]
    duree_cycle_cult = read_wide_table(INDICE_H_DIR / "Duree_Cycle_Cult.txt")[YEAR]
    cout_recolte_cult = read_wide_table(INDICE_H_DIR / "Cout_Recolte_Cult.txt")[YEAR]
    cout_transp_cult = read_wide_table(INDICE_H_DIR / "Cout_Transp_Cult.txt")[YEAR]
    posei_surf_cult = read_wide_table(INDICE_H_DIR / "POSEI_Surf_Cult.txt")[YEAR]
    posei_q_cult = read_wide_table(INDICE_H_DIR / "POSEI_Q_Cult.txt")[YEAR]
    aide_indus_cult = read_wide_table(INDICE_H_DIR / "Aide_Indus_Cult.txt")[YEAR]
    aide_replant_cult = read_wide_table(INDICE_H_DIR / "Aide_Replant_Cult.txt")[YEAR]
    aide_transp_cult = read_wide_table(INDICE_H_DIR / "Aide_Transp_Cult.txt")[YEAR]
    aide_garantie_prix_cult = read_wide_table(INDICE_H_DIR / "Aide_Garantie_Prix_Cult.txt")[YEAR]
    mae_recolte_vert_cult = read_wide_table(INDICE_H_DIR / "MAE_Recolte_Vert_Cult.txt")[YEAR]
    mae_jachere_sol_nu_cult = read_wide_table(INDICE_H_DIR / "MAE_Jachere_Sol_Nu_Cult.txt")[YEAR]
    mae_compost_cult = read_wide_table(INDICE_H_DIR / f"MAE_Compost_Cult_{SCENARIO}.txt")[YEAR]
    mb_add_cult = read_wide_table(INDICE_H_DIR / "MB_ADD_Cult.txt")[YEAR]

    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)

    attribute_bounds = attribute_bounds_from_config(config["eligibility_criteria"])
    plot_attributes = data_parc[list(attribute_bounds.keys())]
    crop_bounds = data_cult.T
    eligibility_mask = compute_eligibility_mask(plot_attributes, crop_bounds, attribute_bounds)
    for build_rule, args in resolve_enabled(
        config["categorical_rules"], CATEGORICAL_RULE_REGISTRY
    ):
        crops, condition = build_rule(data_parc, **args)
        eligibility_mask = forbid_where(eligibility_mask, condition, crops)
    eligible_pairs = eligible_pairs_from_mask(eligibility_mask)

    variable_cost_per_ha_cult = compute_variable_cost_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
        cout_recolte_cult=cout_recolte_cult,
        cout_transp_cult=cout_transp_cult,
        rdt_cult=rdt_cult,
    )
    subsidy_per_ha_cult = compute_subsidy_per_ha_cult(
        posei_surf_cult=posei_surf_cult,
        posei_q_cult=posei_q_cult,
        aide_indus_cult=aide_indus_cult,
        aide_replant_cult=aide_replant_cult,
        aide_transp_cult=aide_transp_cult,
        aide_garantie_prix_cult=aide_garantie_prix_cult,
        mae_recolte_vert_cult=mae_recolte_vert_cult,
        mae_jachere_sol_nu_cult=mae_jachere_sol_nu_cult,
        mae_compost_cult=mae_compost_cult,
        mb_add_cult=mb_add_cult,
        rdt_cult=rdt_cult,
        duree_cycle_cult=duree_cycle_cult,
        duree_plant_cult=duree_plant_cult,
    )
    gross_product_per_ha_cult = compute_gross_product_per_ha_cult(
        rdt_cult=rdt_cult,
        prix_cult=prix_cult,
        bagasse_cult=bagasse_cult,
        subsidy_per_ha_cult=subsidy_per_ha_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    margin_per_ha_cult = compute_gross_margin_per_ha_cult(
        gross_product_per_ha_cult=gross_product_per_ha_cult,
        variable_cost_per_ha_cult=variable_cost_per_ha_cult,
    )

    parameters = {
        "expl_parc": expl_parc,
        "bv_parc": bv_parc,
        "reg_parc": reg_parc,
        "cpt_parc": cpt_parc,
        "data_parc": data_parc,
        "data_cult": data_cult,
        "data_otk": data_otk,
        "matrice_otk_cult": matrice_otk_cult,
        "prix_cult": prix_cult,
        "rdt_cult": rdt_cult,
        "farm_surface_ha": farm_surface_ha,
        "eligibility_mask": eligibility_mask,
        "eligible_pairs": eligible_pairs,
        "margin_per_ha_cult": margin_per_ha_cult,
    }

    return Dataset(sets=sets, parameters=parameters, scalars={})


if __name__ == "__main__":
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    print(f"crops: {len(dataset.sets['crops'])}")
    print(f"soils: {len(dataset.sets['soils'])}")
    print(f"otk: {len(dataset.sets['otk'])}")
    print(f"plots (expl_parc rows): {len(dataset.parameters['expl_parc'])}")
    print(f"farms: {dataset.parameters['expl_parc']['farm'].nunique()}")
    print(f"farm_surface_ha sample:\n{dataset.parameters['farm_surface_ha'].head()}")
```

- [ ] **Step 4: Rewrite `display_datasets.py`**

Replace `display_datasets.py` with:

```python
from pathlib import Path

from case_studies.guadeloupe.data_pipeline import build_dataset
from core.config import load_config
from core.data.dataset import build_registry

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"


def main() -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    registry = build_registry(dataset)

    for row in registry:
        print(f"{row['category']:<12} {row['name']:<20} {row['type']:<12} {row['size']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py tests/test_display_datasets.py -v`
Expected: PASS (9 tests in `test_guadeloupe_pipeline.py`, 1 in `test_display_datasets.py`)

- [ ] **Step 6: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py display_datasets.py tests/test_guadeloupe_pipeline.py
git commit -m "Make build_dataset config-driven for eligibility criteria and categorical rules"
```

---

### Task 8: Config-driven `build_model`

**Files:**
- Modify: `case_studies/guadeloupe/model.py` (full rewrite)
- Test: `tests/test_guadeloupe_model.py` (full rewrite)

**Interfaces:**
- Consumes: `build_crop_allocation_model(..., config: dict[str, Any])` from Task 3.
- Produces: `build_model(dataset: Dataset, config: dict[str, Any]) -> pyo.ConcreteModel`.

- [ ] **Step 1: Rewrite the failing test**

Replace `tests/test_guadeloupe_model.py` with:

```python
import pandas as pd
import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe.model import build_model
from core.data.dataset import Dataset

CONFIG = {
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def _fake_dataset() -> Dataset:
    data_parc = pd.DataFrame({"SURF_HA": [1.0, 2.0]}, index=["P1", "P2"])
    margin_per_ha_cult = pd.Series({"C1": 100.0, "C2": 200.0})
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "margin_per_ha_cult": margin_per_ha_cult,
            "eligible_pairs": eligible_pairs,
        },
        scalars={},
    )


def test_build_model_wires_dataset_into_crop_allocation_model():
    dataset = _fake_dataset()

    model = build_model(dataset, CONFIG)

    assert set(model.Y.keys()) == {("P1", "C1"), ("P1", "C2"), ("P2", "C1")}

    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.Y["P2", "C1"]) == pytest.approx(1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_model.py -v`
Expected: FAIL with `TypeError: build_model() missing 1 required positional argument: 'config'`

- [ ] **Step 3: Rewrite `case_studies/guadeloupe/model.py`**

Replace `case_studies/guadeloupe/model.py` with:

```python
from typing import Any

import pyomo.environ as pyo

from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model


def build_model(dataset: Dataset, config: dict[str, Any]) -> pyo.ConcreteModel:
    return build_crop_allocation_model(
        plot_surface_ha=dataset.parameters["data_parc"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["margin_per_ha_cult"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        config=config,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_model.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/model.py tests/test_guadeloupe_model.py
git commit -m "Make build_model pass config through to build_crop_allocation_model"
```

---

### Task 9: Wire `main.py` to the config file and run the full suite

**Files:**
- Modify: `main.py` (full rewrite)
- Test: `tests/test_main.py` (no changes expected — verifies `main()` still takes no arguments)

**Interfaces:**
- Consumes: `load_config` from Task 1; `build_dataset(config)` from Task 7; `build_model(dataset, config)` from Task 8; `solve_model(model, config)` from Task 4.
- Produces: `main() -> None`, unchanged public signature.

- [ ] **Step 1: Confirm the existing test still describes the desired behavior**

Read `tests/test_main.py` — it calls `main()` with no arguments and checks stdout for `"Total revenue"` and `"Plots allocated"`. No test changes needed since `main()`'s signature does not change; the config load moves inside `main()`.

- [ ] **Step 2: Run the test to verify it currently fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_main.py -v`
Expected: FAIL (`main.py` still calls `build_dataset()`, `build_model(dataset)`, `solve_model(model)` with the old pre-Task-7/8/4 signatures, which now require a `config` argument)

- [ ] **Step 3: Rewrite `main.py`**

Replace `main.py` with:

```python
from pathlib import Path

import pyomo.environ as pyo

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from core.config import load_config
from core.model.solver import solve_model

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"


def main() -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    solve_model(model, config)

    total_revenue = pyo.value(model.objective)
    allocated_plots = sum(1 for index in model.Y if pyo.value(model.Y[index]) > 0.5)
    total_plots = len(dataset.parameters["data_parc"])

    print(f"Total revenue (gross margin, MB_Ha_Cult): {total_revenue:,.2f}")
    print(f"Plots allocated to a crop: {allocated_plots} / {total_plots}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python.exe -m pytest tests/test_main.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Run the full test suite**

Run: `.venv/Scripts/python.exe -m pytest -v`
Expected: PASS, all tests green (no failures, no errors)

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "Load the Guadeloupe config.yaml once in main() and thread it through"
```

---

## Manual verification

- [ ] Run `.venv/Scripts/python.exe main.py` and confirm it prints `Total revenue` and `Plots allocated` lines, matching current behavior on `master`.
- [ ] Edit `case_studies/guadeloupe/config.yaml`, set `categorical_rules[0].enable` (`irrigation_required`) to `false`, rerun `main.py`, and confirm the printed total revenue changes (more plots become eligible for melon) — proof the config actually drives the model, not just passes through unused.
- [ ] Revert that edit before considering the work done.
