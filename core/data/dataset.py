from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Dataset:
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
