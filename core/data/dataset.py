from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Dataset:
    """Everything a case study hands to its model: index sets, parameters (tables and
    series, keyed by name) and scalars. `core/` reads it by name only."""

    sets: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, pd.DataFrame | pd.Series] = field(default_factory=dict)
    scalars: dict[str, float] = field(default_factory=dict)


def _size_of(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.shape
    if hasattr(value, "__len__"):
        return len(value)
    return 1


def build_registry(dataset: Dataset) -> list[dict[str, Any]]:
    """One row {category, name, type, size} per entry, for `scripts/display_datasets.py`."""
    rows = []
    for category in ("sets", "parameters", "scalars"):
        for name, value in getattr(dataset, category).items():
            rows.append(
                {
                    "category": category,
                    "name": name,
                    "type": type(value).__name__,
                    "size": _size_of(value),
                }
            )
    return rows
