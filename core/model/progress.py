from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

import pyomo.environ as pyo
from tqdm import tqdm

from core.model.solver import solve_model

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
