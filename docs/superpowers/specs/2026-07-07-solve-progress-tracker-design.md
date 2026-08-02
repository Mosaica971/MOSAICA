# Live solve progress tracker

## Goal

While `main.py` runs the MILP solve (`solve_model`, potentially the longest step of the
pipeline for larger case studies), show a live, `tqdm`-style progress indicator with an
estimated time remaining, so the user isn't staring at a silent terminal during a
branch-and-bound solve.

## Non-goals

- No true solver-internal progress (MIP gap, node count) — HiGHS/Pyomo don't expose a
  portable, per-solver progress callback worth building against here. The estimate is
  external: based on how long past solves of a similarly-sized problem took.
- No progress tracking for `build_dataset` / `build_model` — those are fast; only
  `solve_model` gets wrapped.
- No change to `solve_model` itself or its existing tests (`tests/test_model_solver.py`)
  — it stays a plain, synchronous, side-effect-documented function.
- No cross-machine or cross-user history sharing — the history file is local and
  gitignored.

## Architecture

`solve_model(model, config)` keeps running synchronously in a background thread while
the main thread drives a `tqdm` progress bar in a loop, polling elapsed wall-clock time.
The estimated total duration (the bar's `total`) comes from a local JSON history of past
solve durations for the same case study, keyed by problem size (number of Pyomo
variables) — nearest-size historical runs are averaged to produce the estimate. Each
successful solve is appended back into that history, so the estimate self-improves over
repeated runs.

### New module: `core/solve/progress.py`

- `SolveHistory`
  - `__init__(self, path: Path = DEFAULT_HISTORY_PATH)` — loads existing JSON (or starts
    empty if the file doesn't exist).
  - `estimate_seconds(self, case_study: str, problem_size: int) -> float | None` — takes
    the 3 stored entries for `case_study` whose `size` is closest to `problem_size`,
    returns their duration averaged and weighted by inverse size distance
    (`1 / (abs(size_diff) + 1)`). Returns `None` if no entries exist yet for that case
    study.
  - `record(self, case_study: str, problem_size: int, duration_seconds: float) -> None`
    — appends `{size, duration}`, truncates to the most recent 20 entries for that case
    study, writes the JSON file back out.
  - Storage shape: `{"<case_study>": [{"size": int, "duration": float}, ...]}`.
  - `DEFAULT_HISTORY_PATH` = `<project root>/.mosaica_solve_history.json`.

- `run_with_progress(func: Callable[[], T], *, label: str, estimate_seconds: float | None) -> tuple[T, float]`
  - Runs `func` in a daemon thread. Main thread opens a `tqdm` bar (`total=estimate_seconds`,
    or `total=None` for an indeterminate/elapsed-only bar when no estimate exists) and,
    every 0.2s, updates it with elapsed wall-clock time. If elapsed ever exceeds the
    current `total`, bumps `total` up to elapsed so the bar doesn't appear to overflow.
  - If `func` raises, the exception is captured on the worker thread and re-raised on the
    main thread after the bar closes (so a failing solve still surfaces its original
    `RuntimeError`/etc., not a thread-related error).
  - Returns `(result, actual_duration_seconds)`.

- `solve_with_progress(model: pyo.ConcreteModel, config: dict, *, case_study: str, history: SolveHistory | None = None) -> Any`
  - `problem_size = sum(1 for _ in model.component_data_objects(pyo.Var))`.
  - Looks up `history.estimate_seconds(case_study, problem_size)` (creates a default
    `SolveHistory()` if none passed).
  - Calls `run_with_progress(lambda: solve_model(model, config), label=f"Solving [{case_study}, {problem_size} vars]", estimate_seconds=estimate)`.
  - On success, calls `history.record(case_study, problem_size, duration)` and returns the
    solver results. On exception, propagates without recording (a fast infeasibility
    failure shouldn't pollute duration estimates).

### Modified: `main.py`

- Replaces the direct `solve_model(model, config)` call with
  `solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)`. Derives the
  case study name from the config file's parent directory (`"guadeloupe"`), no schema
  change needed in `config.yaml`.

### Modified: `pyproject.toml`

- Adds `tqdm>=4.66` to `dependencies`.

### Modified: `.gitignore`

- Adds `.mosaica_solve_history.json`.

## Display

- With an estimate: `Solving [guadeloupe, 1234 vars]:  62%|██████    | 42s/68s [ETA 00:26]`
- Without an estimate (first run for that size): `Solving [guadeloupe, 1234 vars]: 42s elapsed`
- Bar and label render via `tqdm`'s standard mechanics (adapts to non-TTY output
  automatically, as `tqdm` already does).

## Error handling

- Solve raises (e.g. infeasible model) → exception propagates unchanged to the caller of
  `solve_with_progress`; the progress bar closes cleanly first; no history entry is
  written for that run.
- No history file yet, or unreadable/corrupt JSON → `SolveHistory` treats it as empty
  history (falls back to indeterminate bar), rather than raising — a corrupted local
  cache file should never break a solve.
- History file directory not writable → `record` lets the write exception propagate;
  this is a local dev-machine concern, not worth silently swallowing.

## Testing

- `SolveHistory`: load-from-empty-path, `record` then `estimate_seconds` round-trip,
  nearest-neighbor weighting with multiple entries of different sizes, 20-entry
  truncation, missing/corrupt file falls back to empty — all against a `tmp_path` file,
  never the real default path.
- `run_with_progress`: wrap a fast dummy `func` (e.g. `time.sleep(0.05)` then return a
  sentinel) instead of a real solve, assert the returned value and that duration is
  roughly the sleep time; a second test wraps a `func` that raises and asserts the same
  exception type/message propagates on the main thread.
- `solve_with_progress`: reuses the existing tiny `build_crop_allocation_model` fixture
  from `test_model_solver.py`, passes a `SolveHistory` pointed at `tmp_path`, asserts a
  history entry gets recorded after a successful solve with the right `case_study` and
  `problem_size`, and that no entry is recorded when the underlying solve raises.
- No test exercises the real `tqdm` rendering or the default history path — those are
  wired up but not asserted on, consistent with the rest of the codebase's testing style.
