from pathlib import Path

import pandas as pd

_PREFIX = "output_"
_ALLOCATION_CSV = "allocation_output.csv"


def create_output_folder(outputs_root: Path = Path("outputs")) -> Path:
    outputs_root.mkdir(parents=True, exist_ok=True)
    existing = [
        int(child.name[len(_PREFIX):])
        for child in outputs_root.iterdir()
        if child.is_dir()
        and child.name.startswith(_PREFIX)
        and child.name[len(_PREFIX):].isdigit()
    ]
    next_index = max(existing, default=0) + 1
    output_dir = outputs_root / f"{_PREFIX}{next_index}"
    output_dir.mkdir()
    return output_dir


def read_allocation(run_dir: Path) -> dict[str, str]:
    """plot -> crop, from a past run's allocation_output.csv.

    Looks in `csv/` first and then the run root, because runs written before the
    2026-07-13 reorganisation put their CSVs at the top level. Used to warm-start a new
    solve from an old one (core/model/warm_start.py).
    """
    path = run_dir / "csv" / _ALLOCATION_CSV
    if not path.exists():
        path = run_dir / _ALLOCATION_CSV
    if not path.exists():
        raise FileNotFoundError(f"{run_dir}: no {_ALLOCATION_CSV} (looked in csv/ and the root)")
    frame = pd.read_csv(path)
    return dict(zip(frame["plot"].astype(str), frame["crop"].astype(str)))
