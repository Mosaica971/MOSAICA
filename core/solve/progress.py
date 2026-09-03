from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any, TypeVar

import pyomo.environ as pyo

from core.solve.solver import solve_model

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / ".mosaica_solve_history.json"
_MAX_ENTRIES_PER_CASE_STUDY = 20
# How far a past run's size may be from this one and still be considered the same problem.
_SIZE_TOLERANCE = 0.20
# How many recent comparable runs the range is read from.
_RECENT_FOR_ESTIMATE = 8

T = TypeVar("T")


class SolveHistory:
    """Durations of past solves, per case study, used to say what to expect before one.

    WHAT THIS CAN AND CANNOT DO. At a FIXED problem size the durations are wildly dispersed:
    on the 7 calibration solves recorded at 308 847 variables, 327 s to 3 625 s -- a factor 11,
    CV 91 % (96 % on the warm ones alone, so this is not a warm/cold pooling artefact). That
    dispersion is the branch-and-bound search itself, not noise in the measurement, so no
    estimator built on size can be a reliable point estimate. The earlier one returned a single
    number and was wrong by a median 75 % (max 195 %).

    THESE NUMBERS AGE. The history below is a ROLLING WINDOW of the last
    _MAX_ENTRIES_PER_CASE_STUDY solves, not a cumulative log, so a docstring that quotes it
    goes stale silently -- this paragraph used to say "the 20 recorded solves run 155 s to
    1 007 s, factor 6.5, CV 64 %", measured 2026-08-01 and overwritten since. Recount the file
    (2026-08-30 here) rather than trusting the figure; `docs/04-vigilance.md` B.1 and
    `memoire/build_chiffres.py` carry the same values and must move together.

    A RANGE from the same data is honest and still answers the question actually being asked
    -- "is this three minutes or three hours?". Hence `estimate_range`, which returns
    (fastest, slowest) over comparable runs, or None when it has nothing comparable.

    Three things it does that the previous version did not, each fixing a measured defect:
      * warm and cold solves are DIFFERENT POPULATIONS (720 s against 209 s on the same
        model) and are never pooled;
      * it reads the most RECENT comparable runs. The old one sorted by distance in size,
        and on an exact match Python's stable sort handed it the three OLDEST entries --
        so it never learned anything after the third run of a given size;
      * it refuses to answer outside a size band. The old one returned the same 456 s for
        200 000 and for 331 044 variables, because in both cases the three nearest entries
        were the same distant cluster.
    """

    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = path
        self._data: dict[str, list[dict[str, Any]]] = self._load()

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _comparable(
        self, case_study: str, problem_size: int, warm_start: bool
    ) -> list[dict[str, Any]]:
        band = max(1.0, problem_size * _SIZE_TOLERANCE)
        near = [
            entry
            for entry in self._data.get(case_study, [])
            if abs(entry["size"] - problem_size) <= band
        ]
        same_mode = [entry for entry in near if entry.get("warm") == warm_start]
        # Entries written before the warm flag existed carry no mode. They are used only when
        # nothing labelled matches -- better a wide range from unlabelled runs than none at
        # all -- but never mixed into a labelled pool, which would reintroduce the confound.
        return (same_mode or near)[-_RECENT_FOR_ESTIMATE:]

    def estimate_range(
        self, case_study: str, problem_size: int, warm_start: bool = False
    ) -> tuple[float, float, int] | None:
        """(fastest, slowest, how many runs) over comparable past solves, or None."""
        entries = self._comparable(case_study, problem_size, warm_start)
        if not entries:
            return None
        durations = [float(entry["duration"]) for entry in entries]
        return min(durations), max(durations), len(durations)

    def record(
        self,
        case_study: str,
        problem_size: int,
        duration_seconds: float,
        warm_start: bool = False,
    ) -> None:
        entries = self._data.setdefault(case_study, [])
        entries.append(
            {"size": problem_size, "duration": duration_seconds, "warm": warm_start}
        )
        del entries[:-_MAX_ENTRIES_PER_CASE_STUDY]
        self.path.write_text(json.dumps(self._data, indent=2))


def format_estimate(estimate: tuple[float, float, int] | None) -> str:
    """The range as it is printed. A range, never a point -- see `SolveHistory`."""
    if estimate is None:
        return ""
    low, high, count = estimate
    basis = f"d'apres {count} run comparable" + ("s" if count > 1 else "")
    # Collapsed to one number only when the spread is negligible, and then to the SLOW end:
    # an estimate that is read as a promise should err on the side of "longer".
    if high - low < 0.05 * max(high, 1.0):
        return f" (~{high:.0f}s, {basis})"
    return f" ({low:.0f}-{high:.0f}s, {basis})"


def run_with_progress(
    func: Callable[[], T],
    *,
    label: str,
    estimate: tuple[float, float, int] | None = None,
) -> tuple[T, float]:
    # Runs func synchronously on the calling (main) thread, bracketed by static
    # progress lines (ETA before, real duration after). It deliberately does NOT
    # background the solve behind a live animated bar: the HiGHS solver behind
    # `appsi_highs` -- whether reached via SolverFactory or the persistent APPSI
    # interface -- loads the model inside capture_output(capture_fd=True), which
    # redirects the process-global stdout/stderr file descriptors and toggles a
    # process-global lock. Any progress I/O emitted concurrently from another thread
    # corrupts that state ("semaphore released too many times" / broken stdout). The
    # only robust option with real file descriptors is to not overlap solve and I/O.
    # See docs/superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md.
    print(f"{label}{format_estimate(estimate)}...", file=sys.stderr, flush=True)

    start = time.monotonic()
    result = func()
    duration = time.monotonic() - start

    print(f"{label}: done in {duration:.1f}s", file=sys.stderr, flush=True)
    return result, duration


def solve_with_progress(
    model: pyo.ConcreteModel,
    config: dict[str, Any],
    *,
    case_study: str,
    history: SolveHistory | None = None,
    warm_start: bool = False,
) -> tuple[Any, float]:
    history = history or SolveHistory()
    problem_size = sum(1 for _ in model.component_data_objects(pyo.Var))
    # Warm and cold are asked for separately and recorded separately: the same model solved
    # from a seed took 209 s against 720 s cold, so pooling them would make both estimates
    # meaningless.
    estimate = history.estimate_range(case_study, problem_size, warm_start=warm_start)

    label = f"Solving [{case_study}, {problem_size} vars]"
    if warm_start:
        label += " [warm start]"

    results, duration = run_with_progress(
        lambda: solve_model(model, config, warm_start=warm_start),
        label=label,
        estimate=estimate,
    )

    history.record(case_study, problem_size, duration, warm_start=warm_start)
    return results, duration
