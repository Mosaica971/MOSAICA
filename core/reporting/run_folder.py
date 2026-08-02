"""Where a run's results land, and how a past run is read back.

Two naming schemes coexist on purpose. A run with no name gets the historical
`output_N` counter; a run that knows what it is gets a **folder named after itself**
(`calib_gams_parite/`), because `outputs/output_7` tells a reader nothing six weeks later
and the reference runs of this project are consulted for months. Both are discovered the
same way -- by carrying a `recap.json` -- so nothing downstream has to care which it got.
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

_PREFIX = "output_"
_ALLOCATION_CSV = "allocation_output.csv"
_RECAP = "recap.json"


def slugify(name: str) -> str:
    """Folder-safe slug for a run name: accents folded, spaces and punctuation collapsed
    to single underscores, lowercased. Returns "" when nothing usable is left, which the
    caller reads as "fall back on the numbered scheme"."""
    folded = unicodedata.normalize("NFKD", str(name))
    ascii_only = folded.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]+", "_", ascii_only)).strip("_").lower()


def create_output_folder(
    outputs_root: Path = Path("outputs"), name: str | None = None
) -> Path:
    """Fresh folder for one run's results.

    With `name`, the folder is that name slugified -- and a numeric suffix is appended
    rather than reusing an existing folder, because overwriting a past run in place would
    destroy the very thing this project compares against. Without a name (or when the name
    slugifies to nothing), the historical `output_N` counter applies.
    """
    outputs_root.mkdir(parents=True, exist_ok=True)

    slug = slugify(name) if name else ""
    if slug:
        candidate = outputs_root / slug
        suffix = 2
        while candidate.exists():
            candidate = outputs_root / f"{slug}_{suffix}"
            suffix += 1
        candidate.mkdir()
        return candidate

    existing = [
        int(child.name[len(_PREFIX):])
        for child in outputs_root.iterdir()
        if child.is_dir()
        and child.name.startswith(_PREFIX)
        and child.name[len(_PREFIX):].isdigit()
    ]
    output_dir = outputs_root / f"{_PREFIX}{max(existing, default=0) + 1}"
    output_dir.mkdir()
    return output_dir


def _run_index(path: Path) -> int | None:
    """The N of an `output_N` folder, or None for a named run."""
    if path.name.startswith(_PREFIX) and path.name[len(_PREFIX):].isdigit():
        return int(path.name[len(_PREFIX):])
    return None


def list_run_folders(outputs_root: Path) -> list[Path]:
    """Every run folder under `outputs_root`, most interesting first.

    A run folder is one holding a `recap.json` -- which is what makes named and numbered
    runs equal citizens, and which also excludes `reference_2017/` (it writes
    `reference.json`: it is an artefact ABOUT the observed state, not a solve).

    **Named runs come first**, by modification time; then numbered ones, by index
    descending. Two reasons this beats one global sort by mtime. A named run is one someone
    deliberately named, so it is a reference and belongs at the top of a picker; and the
    numbered scheme's index already IS its creation order, so ordering it by index is both
    the historical contract and deterministic -- where mtime is not, since a filesystem
    whose timestamp resolution is coarser than a test's runtime reports ties.
    """
    if not outputs_root.is_dir():
        return []
    folders = [
        child
        for child in outputs_root.iterdir()
        if child.is_dir() and (child / _RECAP).exists()
    ]
    named = [f for f in folders if _run_index(f) is None]
    numbered = [f for f in folders if _run_index(f) is not None]
    named.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    numbered.sort(key=lambda path: _run_index(path), reverse=True)
    return named + numbered


def read_allocation(run_dir: Path) -> dict[str, str]:
    """plot -> crop, from a past run's allocation_output.csv.

    Looks in `csv/` first and then the run root, because runs written before the
    2026-07-13 reorganisation put their CSVs at the top level. Used to warm-start a new
    solve from an old one (core/solve/warm_start.py).
    """
    path = run_dir / "csv" / _ALLOCATION_CSV
    if not path.exists():
        path = run_dir / _ALLOCATION_CSV
    if not path.exists():
        raise FileNotFoundError(f"{run_dir}: no {_ALLOCATION_CSV} (looked in csv/ and the root)")
    frame = pd.read_csv(path)
    return dict(zip(frame["plot"].astype(str), frame["crop"].astype(str)))
