"""Pure, Streamlit-free functions to read an outputs/output_N/ run folder (brique A)
for the dashboard (brique B). Read-only: never writes, never triggers a solve."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

_PREFIX = "output_"


def list_output_runs(outputs_root: Path) -> list[Path]:
    if not outputs_root.is_dir():
        return []
    numbered = [
        (int(child.name[len(_PREFIX):]), child)
        for child in outputs_root.iterdir()
        if child.is_dir()
        and child.name.startswith(_PREFIX)
        and child.name[len(_PREFIX):].isdigit()
    ]
    numbered.sort(key=lambda pair: pair[0], reverse=True)
    return [child for _, child in numbered]


def load_recap(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "recap.json").read_text())


def load_csv(run_dir: Path, name: str) -> pd.DataFrame | None:
    path = run_dir / name
    if not path.exists():
        return None
    return pd.read_csv(path)
