# Live Solve Progress Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a live `tqdm`-style progress bar with an estimated time remaining while `main.py` runs the MILP solve, using a local history of past solve durations (by case study and problem size) to produce the estimate.

**Architecture:** `solve_model(model, config)` (`core/model/solver.py`) stays untouched and synchronous. A new `core/model/progress.py` module runs it in a background thread while the main thread drives a `tqdm` bar off elapsed wall-clock time, seeded with an ETA pulled from a local JSON history file (`SolveHistory`). `main.py` calls the new `solve_with_progress` wrapper instead of `solve_model` directly.

**Tech Stack:** Python 3.10+, Pyomo, `tqdm`, `threading` (stdlib), `json` (stdlib), `pytest`.

## Global Constraints

- `solve_model` (`core/model/solver.py`) and its existing tests (`tests/test_model_solver.py`) must not change.
- History file path: `<project root>/.mosaica_solve_history.json`, must be added to `.gitignore`.
- History keeps at most the most recent 20 entries per case study.
- ETA estimate uses the 3 nearest-by-size historical entries for that case study, weighted by `1 / (abs(size_diff) + 1)`.
- No history entry is recorded when the wrapped solve raises.
- `tqdm>=4.66` added to `pyproject.toml` `dependencies`.
- All new tests use `tmp_path` for `SolveHistory` — never the real default history path.

---

### Task 1: `SolveHistory` — local JSON-backed solve duration history

**Files:**
- Create: `core/model/progress.py`
- Test: `tests/test_model_progress.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `SolveHistory` class in `core/model/progress.py` with:
  - `SolveHistory(path: Path = DEFAULT_HISTORY_PATH)` constructor (loads existing file or starts empty; corrupt/missing file → empty).
  - `estimate_seconds(self, case_study: str, problem_size: int) -> float | None`
  - `record(self, case_study: str, problem_size: int, duration_seconds: float) -> None`
  - `DEFAULT_HISTORY_PATH: Path` module-level constant = `<project root>/.mosaica_solve_history.json`.
  - Internal storage attribute `self._data: dict[str, list[dict[str, float]]]` (used directly by later tasks' tests).

- [ ] **Step 1: Add `.mosaica_solve_history.json` to `.gitignore`**

Edit `.gitignore`, add a new line at the end:

```
.mosaica_solve_history.json
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_model_progress.py`:

```python
import pytest

from core.model.progress import SolveHistory


def test_estimate_seconds_returns_none_when_no_entries(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_record_then_estimate_round_trip(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")

    history.record("guadeloupe", 100, 42.0)

    assert history.estimate_seconds("guadeloupe", 100) == pytest.approx(42.0)


def test_estimate_weights_by_proximity_to_problem_size(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")
    history.record("guadeloupe", 100, 10.0)
    history.record("guadeloupe", 200, 20.0)

    estimate = history.estimate_seconds("guadeloupe", 110)

    # Closer to the size=100/duration=10.0 entry, so the estimate should
    # lean toward 10.0 rather than sit at the midpoint (15.0).
    assert 10.0 < estimate < 15.0


def test_estimate_uses_only_3_nearest_neighbors(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")
    history.record("guadeloupe", 100, 10.0)
    history.record("guadeloupe", 101, 10.0)
    history.record("guadeloupe", 102, 10.0)
    history.record("guadeloupe", 9999, 999.0)  # far away, must be excluded

    estimate = history.estimate_seconds("guadeloupe", 100)

    assert estimate == pytest.approx(10.0)


def test_record_truncates_to_last_20_entries(tmp_path):
    path = tmp_path / "history.json"
    history = SolveHistory(path=path)
    for i in range(25):
        history.record("guadeloupe", i, float(i))

    reloaded = SolveHistory(path=path)

    assert len(reloaded._data["guadeloupe"]) == 20
    assert reloaded._data["guadeloupe"][0]["size"] == 5
    assert reloaded._data["guadeloupe"][-1]["size"] == 24


def test_missing_file_falls_back_to_empty_history(tmp_path):
    history = SolveHistory(path=tmp_path / "does_not_exist.json")

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_corrupt_file_falls_back_to_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("not valid json")

    history = SolveHistory(path=path)

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_history_persists_across_instances(tmp_path):
    path = tmp_path / "history.json"
    SolveHistory(path=path).record("guadeloupe", 100, 5.0)

    reloaded = SolveHistory(path=path)

    assert reloaded.estimate_seconds("guadeloupe", 100) == pytest.approx(5.0)


def test_case_studies_are_kept_separate(tmp_path):
    path = tmp_path / "history.json"
    history = SolveHistory(path=path)
    history.record("guadeloupe", 100, 5.0)

    assert history.estimate_seconds("other_case_study", 100) is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_model_progress.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.model.progress'` (or `ImportError`).

- [ ] **Step 4: Implement `SolveHistory`**

Create `core/model/progress.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / ".mosaica_solve_history.json"
_MAX_ENTRIES_PER_CASE_STUDY = 20
_NEIGHBORS_FOR_ESTIMATE = 3


class SolveHistory:
    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = path
        self._data: dict[str, list[dict[str, float]]] = self._load()

    def _load(self) -> dict[str, list[dict[str, float]]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def estimate_seconds(self, case_study: str, problem_size: int) -> float | None:
        entries = self._data.get(case_study, [])
        if not entries:
            return None

        neighbors = sorted(entries, key=lambda e: abs(e["size"] - problem_size))
        neighbors = neighbors[:_NEIGHBORS_FOR_ESTIMATE]

        weights = [1.0 / (abs(e["size"] - problem_size) + 1.0) for e in neighbors]
        total_weight = sum(weights)
        return sum(w * e["duration"] for w, e in zip(weights, neighbors)) / total_weight

    def record(self, case_study: str, problem_size: int, duration_seconds: float) -> None:
        entries = self._data.setdefault(case_study, [])
        entries.append({"size": problem_size, "duration": duration_seconds})
        del entries[:-_MAX_ENTRIES_PER_CASE_STUDY]
        self.path.write_text(json.dumps(self._data, indent=2))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_model_progress.py -v`
Expected: PASS (9 passed).

- [ ] **Step 6: Commit**

```bash
git add core/model/progress.py tests/test_model_progress.py .gitignore
git commit -m "Add SolveHistory for tracking past solve durations by case study and size"
```

---

### Task 2: `run_with_progress` — generic threaded `tqdm` runner

**Files:**
- Modify: `core/model/progress.py`
- Modify: `tests/test_model_progress.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: nothing from Task 1 directly (independent of `SolveHistory`).
- Produces: `run_with_progress(func: Callable[[], T], *, label: str, estimate_seconds: float | None) -> tuple[T, float]` in `core/model/progress.py` — runs `func` in a background thread, drives a `tqdm` bar off elapsed time in the calling thread, returns `(func_return_value, actual_duration_seconds)`. Re-raises any exception `func` raised, on the calling thread, after the bar closes.

- [ ] **Step 1: Add the `tqdm` dependency**

Edit `pyproject.toml`, add `"tqdm>=4.66",` to the `dependencies` list (alongside `pandas`, `pyomo`, `highspy`, `pyyaml`):

```toml
dependencies = [
    "pandas>=2.0",
    "pyomo>=6.7",
    "highspy>=1.7",
    "pyyaml>=6.0",
    "tqdm>=4.66",
]
```

Then install it:

Run: `pip install -e .`
Expected: `tqdm` installed successfully.

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_model_progress.py`:

```python
import time

from core.model.progress import run_with_progress


def test_run_with_progress_returns_result_and_duration():
    def slow_add():
        time.sleep(0.05)
        return 1 + 1

    result, duration = run_with_progress(slow_add, label="test", estimate_seconds=None)

    assert result == 2
    assert duration >= 0.05


def test_run_with_progress_works_with_a_known_estimate():
    def instant_value():
        return "done"

    result, duration = run_with_progress(instant_value, label="test", estimate_seconds=10.0)

    assert result == "done"
    assert duration >= 0.0


def test_run_with_progress_reraises_exception_from_worker_thread():
    def boom():
        raise RuntimeError("solve failed")

    with pytest.raises(RuntimeError, match="solve failed"):
        run_with_progress(boom, label="test", estimate_seconds=None)
```

Move the `import pytest` that already exists at the top of the file if needed — it's already imported from Task 1, no change required there.

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_model_progress.py -v -k run_with_progress`
Expected: FAIL with `ImportError: cannot import name 'run_with_progress'`.

- [ ] **Step 4: Implement `run_with_progress`**

Replace the full contents of `core/model/progress.py` with (this extends Task 1's file: the import block gains `threading`, `time`, `Callable`, `TypeVar`, `tqdm`; `SolveHistory` itself is unchanged; `run_with_progress` is appended at the end):

```python
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, TypeVar

from tqdm import tqdm

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / ".mosaica_solve_history.json"
_MAX_ENTRIES_PER_CASE_STUDY = 20
_NEIGHBORS_FOR_ESTIMATE = 3
_POLL_INTERVAL_SECONDS = 0.2

T = TypeVar("T")


class SolveHistory:
    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = path
        self._data: dict[str, list[dict[str, float]]] = self._load()

    def _load(self) -> dict[str, list[dict[str, float]]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def estimate_seconds(self, case_study: str, problem_size: int) -> float | None:
        entries = self._data.get(case_study, [])
        if not entries:
            return None

        neighbors = sorted(entries, key=lambda e: abs(e["size"] - problem_size))
        neighbors = neighbors[:_NEIGHBORS_FOR_ESTIMATE]

        weights = [1.0 / (abs(e["size"] - problem_size) + 1.0) for e in neighbors]
        total_weight = sum(weights)
        return sum(w * e["duration"] for w, e in zip(weights, neighbors)) / total_weight

    def record(self, case_study: str, problem_size: int, duration_seconds: float) -> None:
        entries = self._data.setdefault(case_study, [])
        entries.append({"size": problem_size, "duration": duration_seconds})
        del entries[:-_MAX_ENTRIES_PER_CASE_STUDY]
        self.path.write_text(json.dumps(self._data, indent=2))


def run_with_progress(
    func: Callable[[], T],
    *,
    label: str,
    estimate_seconds: float | None,
) -> tuple[T, float]:
    outcome: dict[str, T] = {}
    error: dict[str, BaseException] = {}

    def _target() -> None:
        try:
            outcome["value"] = func()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller's thread below
            error["value"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    start = time.monotonic()
    thread.start()

    bar_format = (
        "{desc}: {bar} {n:.0f}s/{total:.0f}s [ETA {remaining}]"
        if estimate_seconds
        else "{desc}: {n:.0f}s elapsed"
    )
    with tqdm(total=estimate_seconds, desc=label, bar_format=bar_format) as bar:
        last = 0.0
        while thread.is_alive():
            elapsed = time.monotonic() - start
            if bar.total is not None and elapsed > bar.total:
                bar.total = elapsed
            bar.update(elapsed - last)
            last = elapsed
            thread.join(timeout=_POLL_INTERVAL_SECONDS)

        elapsed = time.monotonic() - start
        if bar.total is not None and elapsed > bar.total:
            bar.total = elapsed
        bar.update(elapsed - last)

    duration = time.monotonic() - start
    if "value" in error:
        raise error["value"]
    return outcome["value"], duration
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_model_progress.py -v`
Expected: PASS (12 passed).

- [ ] **Step 6: Commit**

```bash
git add core/model/progress.py tests/test_model_progress.py pyproject.toml
git commit -m "Add run_with_progress: threaded tqdm runner for blocking calls"
```

---

### Task 3: `solve_with_progress` — wires `SolveHistory` + `run_with_progress` + `solve_model`

**Files:**
- Modify: `core/model/progress.py`
- Modify: `tests/test_model_progress.py`

**Interfaces:**
- Consumes: `SolveHistory` (Task 1), `run_with_progress` (Task 2), `solve_model(model, config)` from `core/model/solver.py` (unchanged), `build_crop_allocation_model` from `core/model/builder.py` (unchanged, used only in tests).
- Produces: `solve_with_progress(model: pyo.ConcreteModel, config: dict, *, case_study: str, history: SolveHistory | None = None) -> Any` in `core/model/progress.py` — the function `main.py` (Task 4) will call.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_model_progress.py`:

```python
import pyomo.environ as pyo

from core.model.builder import build_crop_allocation_model
from core.model.progress import solve_with_progress

_SOLVE_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_solve_with_progress_records_history_on_success(tmp_path):
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=_SOLVE_CONFIG,
    )
    history = SolveHistory(path=tmp_path / "history.json")

    solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case", history=history)

    entries = history._data["test_case"]
    assert len(entries) == 1
    assert entries[0]["size"] == 2  # Y["P1","C1"], Y["P1","C2"]
    assert entries[0]["duration"] >= 0.0
    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)


def test_solve_with_progress_does_not_record_history_on_failure(tmp_path):
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1")],
        config=_SOLVE_CONFIG,
    )
    model.Y["P1", "C1"].fix(1)
    model.infeasible_constraint = pyo.Constraint(expr=model.Y["P1", "C1"] == 0)
    history = SolveHistory(path=tmp_path / "history.json")

    with pytest.raises(RuntimeError, match="optimal"):
        solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case", history=history)

    assert "test_case" not in history._data


def test_solve_with_progress_defaults_to_a_fresh_solve_history_when_none_given():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=_SOLVE_CONFIG,
    )

    # No history= passed: solve_with_progress must construct its own SolveHistory()
    # and must not raise even though this touches the real default history path
    # (consistent with the design's non-goal: the default path is wired up but
    # not asserted on beyond "it doesn't blow up").
    solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case_default_history")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_model_progress.py -v -k solve_with_progress`
Expected: FAIL with `ImportError: cannot import name 'solve_with_progress'`.

- [ ] **Step 3: Implement `solve_with_progress`**

In `core/model/progress.py`, change the top of the file so the import block reads exactly:

```python
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import pyomo.environ as pyo
from tqdm import tqdm

from core.model.solver import solve_model
```

(this adds `Any` to the `typing` import, plus the two new `import pyomo.environ as pyo` and `from core.model.solver import solve_model` lines — everything else in the file, `SolveHistory` and `run_with_progress`, is unchanged), then append the function at the end of `core/model/progress.py`:

```python
def solve_with_progress(
    model: pyo.ConcreteModel,
    config: dict[str, Any],
    *,
    case_study: str,
    history: SolveHistory | None = None,
) -> Any:
    history = history or SolveHistory()
    problem_size = sum(1 for _ in model.component_data_objects(pyo.Var))
    estimate = history.estimate_seconds(case_study, problem_size)

    results, duration = run_with_progress(
        lambda: solve_model(model, config),
        label=f"Solving [{case_study}, {problem_size} vars]",
        estimate_seconds=estimate,
    )

    history.record(case_study, problem_size, duration)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_model_progress.py -v`
Expected: PASS (15 passed).

- [ ] **Step 5: Commit**

```bash
git add core/model/progress.py tests/test_model_progress.py
git commit -m "Add solve_with_progress: wires SolveHistory into the tqdm-driven solve"
```

---

### Task 4: Wire `main.py` to use `solve_with_progress`

**Files:**
- Modify: `main.py`
- Modify: `tests/test_main.py` (no code change expected, just re-run to confirm it still passes)

**Interfaces:**
- Consumes: `solve_with_progress(model, config, *, case_study: str, history=None)` from `core/model/progress.py` (Task 3).

- [ ] **Step 1: Update `main.py`**

Current `main.py`:

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

Replace it with:

```python
from pathlib import Path

import pyomo.environ as pyo

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from core.config import load_config
from core.model.progress import solve_with_progress

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"


def main() -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)

    total_revenue = pyo.value(model.objective)
    allocated_plots = sum(1 for index in model.Y if pyo.value(model.Y[index]) > 0.5)
    total_plots = len(dataset.parameters["data_parc"])

    print(f"Total revenue (gross margin, MB_Ha_Cult): {total_revenue:,.2f}")
    print(f"Plots allocated to a crop: {allocated_plots} / {total_plots}")


if __name__ == "__main__":
    main()
```

(Only the `solve_model` import and its call site change — everything else is untouched.)

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS, including `tests/test_main.py::test_main_runs_full_pipeline_and_prints_solution_summary` (the `tqdm` bar writes to stderr, not stdout, so it doesn't interfere with `capsys.readouterr().out` assertions).

- [ ] **Step 3: Manually verify the live bar**

Run: `python main.py`
Expected: A `tqdm` progress line appears on the terminal while the solve runs (indeterminate — elapsed-only — on this first real run since `.mosaica_solve_history.json` doesn't have a `guadeloupe` entry of this problem size yet), then the usual `Total revenue` / `Plots allocated` lines print. Confirm `.mosaica_solve_history.json` now exists at the project root with a `guadeloupe` entry.

Run: `python main.py` again.
Expected: The bar now shows a `%`/ETA (a history entry exists for this exact problem size from the previous run).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "Wire main.py to show a live solve progress bar via solve_with_progress"
```
