from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any, TypeVar

import pyomo.environ as pyo

from core.model.solver import solve_model

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / ".mosaica_solve_history.json"
_MAX_ENTRIES_PER_CASE_STUDY = 20
_NEIGHBORS_FOR_ESTIMATE = 3

T = TypeVar("T")


class SolveHistory:
    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = path
        self._data: dict[str, list[dict[str, float]]] = self._load()

    def _load(self) -> dict[str, list[dict[str, float]]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

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
    suffix = f" (est ~{estimate_seconds:.0f}s)" if estimate_seconds else ""
    print(f"{label}{suffix}...", file=sys.stderr, flush=True)

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
) -> tuple[Any, float]:
    history = history or SolveHistory()
    problem_size = sum(1 for _ in model.component_data_objects(pyo.Var))
    estimate = history.estimate_seconds(case_study, problem_size)

    results, duration = run_with_progress(
        lambda: solve_model(model, config),
        label=f"Solving [{case_study}, {problem_size} vars]",
        estimate_seconds=estimate,
    )

    history.record(case_study, problem_size, duration)
    return results, duration
