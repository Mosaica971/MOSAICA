from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_enabled(
    entries: list[dict[str, Any]], registry: dict[str, Callable]
) -> list[tuple[Callable, dict[str, Any]]]:
    resolved = []
    for entry in entries:
        if not entry.get("enable", False):
            continue
        name = entry["name"]
        if name not in registry:
            available = ", ".join(sorted(registry))
            raise KeyError(f"Unknown component '{name}'. Available: {available}")
        resolved.append((registry[name], entry.get("args") or {}))
    return resolved
