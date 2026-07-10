# Solver speedup — persistent APPSI HiGHS interface

_2026-07-10_

> **STATUS: REVERTED (2026-07-10).** This approach was implemented (commit `3c8e450`) and
> then rolled back the same day. A full `main.py` run showed the ~25% gain measured on the
> island-1 subset does **not** transfer to the real 1.68M-var problem — at full scale the
> bottleneck is the MILP branch-and-bound search, not the ~15s Pyomo→HiGHS translation this
> change removes. The persistent interface also loads the model inside
> `capture_output(capture_fd=True)`, which is incompatible with the background-threaded
> animated `tqdm` progress bar (global stdout/stderr fd corruption). With no real gain and
> the loss of the live bar, the change was reverted to `SolverFactory` + the animated bar.
> This document is kept for its root-cause analysis (the thread/`capture_output` conflict)
> in case APPSI is revisited via the real perf levers (MIP gap, warm start, fewer binaries).
> See `VIGILANCE.md`.

## Problem

Profiling (brique D, see `2026-07-10-solver-performance-design.md` and `VIGILANCE.md`)
showed the solve wall-clock is dominated not by the HiGHS optimization (~6s, mostly
presolve, 0 branch-and-bound nodes) but by the `SolverFactory('appsi_highs')`
**LegacySolver** wrapper converting the Pyomo model (~500k binary vars) into HiGHS's
internal structures (~15s). Using Pyomo's **persistent APPSI HiGHS interface**
(`pyomo.contrib.appsi.solvers.highs.Highs`) instead cuts ~25% off the wall-clock
(measured 16s vs 21.5s on the island-1 subset) by avoiding that wrapper. No
`solver.args` tuning (threads/parallel/presolve) helps, because the bottleneck is the
model translation, not the algorithm.

The blocker last session was API shape: the APPSI results object exposes
`results.termination_condition` (an APPSI enum), not the legacy
`results.solver.termination_condition`, which `solve_model` and `report.py` rely on.

## Goal

Switch `solve_model` to the persistent APPSI HiGHS interface, and contain the different
results shape so the rest of the codebase stays clean.

## Design

Only two files consume the solver/results shape: `core/model/solver.py` (internal) and
`case_studies/guadeloupe/reporting/report.py::_build_recap`
(`str(results.solver.termination_condition)`).

### `core/model/solver.py`

- New `@dataclass SolveResult` with a single field `termination_condition: str` — the
  normalized public contract `solve_model` returns.
- `solve_model(model, config)`:
  - `opt = Highs()`
  - `opt.config.load_solution = False` (mirror the current `load_solutions=False`; we
    load explicitly).
  - Map `config["solver"]["args"]` (dict, `{}` today) onto `opt.highs_options` — preserves
    the config knob for raw HiGHS options.
  - `results = opt.solve(model)`
  - If `results.termination_condition != TerminationCondition.optimal`: raise
    `RuntimeError` whose message contains the word `optimal` (keeps the existing
    `test_solve_model_raises_on_infeasible_model` regex passing).
  - `opt.load_vars()` — load the solution back into `model` so `pyo.value(model.Y[...])`
    and `pyo.value(model.objective)` work downstream.
  - `return SolveResult(termination_condition=results.termination_condition.name)` →
    `"optimal"`, consistent with the recap's current human-readable value.

`config["solver"]["name"]` stays read and logged in the recap; the persistent HiGHS
interface is used directly (the model is HiGHS-specific — no need to keep the generic
`SolverFactory(name)` dispatch).

### `case_studies/guadeloupe/reporting/report.py`

- `_build_recap`: `str(results.solver.termination_condition)` → `results.termination_condition`
  (already a string on `SolveResult`).

### `core/model/progress.py` — solve must run on the main thread (no live bar)

The persistent APPSI solver loads the model inside `capture_output(capture_fd=True)`
(`pyomo/contrib/appsi/solvers/highs.py`), which redirects the process-global
stdout/stderr **file descriptors** (via `dup2`) and toggles a process-global
`capture_output_lock`. `run_with_progress` previously ran the solve in a background
daemon thread while the main thread animated a `tqdm` bar on stderr. That concurrency
corrupts the global lock/fd state → `ValueError: semaphore or lock released too many
times` (and, at shutdown, a broken stdout fd + lost output). The old
`SolverFactory('appsi_highs')` LegacySolver path tolerated the threaded bar; the faster
persistent path does not — proven by isolation (a bare main-thread solve, or a bare
worker-thread solve with no concurrent I/O, both succeed; adding any concurrent progress
I/O reproduces the crash, even with the bar routed to a duplicated fd).

Resolution (user decision 2026-07-10: keep the fast solver, drop the live bar):
`run_with_progress` now runs `func` **synchronously on the calling (main) thread**,
bracketed by two static prints — an ETA line before (`Solving [...] (est ~Ns)...`) and
the real duration after (`... done in Ns`). No worker thread, no `tqdm`. The
`SolveHistory` ETA feature is retained (as the static estimate); only the live animation
is gone. `tqdm` is dropped from `pyproject.toml`. `run_with_progress`'s public contract
(`(result, duration)`, exceptions propagate) is unchanged, so `solve_with_progress` and
its tests are unaffected.

### Unchanged

`scripts/profile_solver.py`, `main.py` — neither depends on the results shape nor the
progress mechanism; they pass values through.

## Testing

- Existing `tests/test_model_solver.py` (optimal solve + infeasible → `RuntimeError`
  matching `optimal`) exercises the entire new path on a 2-variable model — fast,
  real, end-to-end, no full-dataset solve.
- Add a test locking the contract `report.py` consumes: `solve_model` returns a
  `SolveResult` whose `.termination_condition == "optimal"` on a feasible model.
- Add `test_run_with_progress_runs_func_on_the_calling_thread` — an architectural guard
  that the solve is not backgrounded (the root cause of the concurrency crash).

The concurrency crash itself cannot be reproduced under pytest: pytest's captured
stdout/stderr have no real `fileno()`, so the solver's `capture_fd` redirection is a
no-op and the collision never occurs. It was instead reproduced and fixed via a
**real-fd run on a tiny `zone_filter` subset** (three small farms, ~6 plots, territory
quotas disabled), driving the full `solve_with_progress` → `generate_report` path and
confirming exit 0, a correct recap (`termination=optimal`), and a usable stdout after
the solve. Per standing user preference the full `main.py` solve is not run this session;
the ~25% gain is re-confirmed on the full run at an end-of-day `main.py` pass.

## Non-goals

- No change to the model, constraints, objective, or numerical results — same optimum,
  just reached with less wrapper overhead.
- No re-profiling of the full run this session (would need the ~30-min solve).
