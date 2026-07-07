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
