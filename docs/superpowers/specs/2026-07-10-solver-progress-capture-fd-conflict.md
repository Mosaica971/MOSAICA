# Solve progress bar vs Pyomo `capture_output(capture_fd=True)` — synchronous progress

_2026-07-10_

## Symptom

Running a real solve through `solve_with_progress` (which backgrounded the solve on a
daemon thread and animated a `tqdm` bar on the main thread) crashes:

```
pyomo/contrib/appsi/solvers/highs.py  set_instance -> capture_output(capture_fd=True)
pyomo/common/tee.py __exit__ -> capture_output_lock.release()
ValueError: semaphore or lock released too many times
```

...whenever `stdout`/`stderr` have real file descriptors (a terminal, a file, or a
pipe). On a full run the fd state is also left broken, so subsequent stdout is lost and
the process exits non-zero.

## Root cause

`SolverFactory('appsi_highs')` is **not** a different solver from the persistent APPSI
`Highs` — the LegacySolver wrapper calls the very same
`pyomo.contrib.appsi.solvers.highs.Highs.set_instance`, which loads the model inside
`capture_output(capture_fd=True)`. That context manager:

- redirects the **process-global** stdout/stderr file descriptors via `dup2`, and
- acquires/releases a **process-global** `capture_output_lock` (a plain `threading.Lock`)
  in its `__enter__`/`__exit__`.

`run_with_progress` ran the solve on a **daemon thread** while the **main** thread wrote
the `tqdm` bar to stderr. That concurrent I/O corrupts the global lock/fd state.

Verified by isolation:

- Solve on the main thread with no concurrent bar → **works** (this is what
  `scripts/profile_solver.py` and the ETP smoke run do; both succeed on real fds).
- Solve on a worker thread with no concurrent I/O → works.
- Add *any* concurrent progress I/O (bar or ticker), on the main thread or a worker,
  merged or separate streams, even routed to a duplicated fd → **crashes**. The global
  lock is shared regardless.
- Under pytest the crash does **not** reproduce: pytest's captured stdout/stderr have no
  real `fileno()`, so `capture_fd` is a no-op and there is nothing to corrupt. This is
  why the threaded bar passed its unit tests yet crashed every real invocation.

This is independent of the (separately reverted) APPSI-vs-SolverFactory speed question:
both routes hit the same `capture_fd` machinery, so **the animated bar cannot coexist
with an `appsi_highs` solve on real file descriptors**.

## Decision

Make `run_with_progress` **synchronous**: run the solve on the calling (main) thread,
bracketed by two static prints — an ETA line before (`Solving [...] (est ~Ns)...`, from
`SolveHistory`) and the real duration after (`... done in Ns`). No worker thread, no
`tqdm`. This is the only option that runs reliably on real file descriptors; the live
animation is not recoverable without monkeypatching Pyomo internals (rejected as
fragile). The `SolveHistory` ETA feature is retained as the static estimate.
`run_with_progress`'s public contract (`(result, duration)`, exceptions propagate) is
unchanged, so `solve_with_progress` and its consumers are unaffected. `tqdm` is dropped
from `pyproject.toml`.

## Testing

- `test_run_with_progress_runs_func_on_the_calling_thread` locks the architectural
  decision (the solve is not backgrounded — the root cause of the crash).
- Existing progress/solve/report tests keep passing (fast, data-free).
- The crash cannot be reproduced under pytest (see above); it was reproduced and the fix
  confirmed via real-fd subset runs (`solve_with_progress` on a `zone_filter` subset,
  exit 0, usable stdout, correct report).
