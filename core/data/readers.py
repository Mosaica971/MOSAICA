from pathlib import Path

import pandas as pd


def read_flat_set(path: Path) -> list[str]:
    """A GAMS .set file with one element per line, blank lines skipped."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def read_mapping_set(path: Path, parent_name: str, child_name: str) -> pd.DataFrame:
    """A GAMS two-dimensional .set file (`parent.child` per line) as a two-column table."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    pairs = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Malformed mapping line in {path}: {stripped!r}")
        pairs.append(parts)
    return pd.DataFrame(pairs, columns=[parent_name, child_name])


def read_wide_table(path: Path) -> pd.DataFrame:
    """A tab-separated table whose first column is the row index."""
    return pd.read_csv(path, sep="\t", index_col=0)
