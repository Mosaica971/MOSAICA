"""Pure, Streamlit-free functions to read an outputs/output_N/ run folder (brique A)
for the dashboard (brique B). Read-only: never writes, never triggers a solve."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from core.reporting.run_folder import list_run_folders

def list_output_runs(outputs_root: Path) -> list[Path]:
    """Every run folder, newest first -- named (`calib_retenu/`) and numbered
    (`output_3/`) alike. Delegates to core so the dashboard and the scripts agree on what
    counts as a run: a folder carrying a `recap.json`."""
    return list_run_folders(outputs_root)


def load_recap(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "recap.json").read_text())


def load_config_used(run_dir: Path) -> dict[str, Any] | None:
    """The exact configuration this run was solved with, or None when the folder predates
    `config_used.yaml`. This is what makes a run auditable after the fact: the results are
    only readable next to the hypotheses that produced them."""
    path = run_dir / "config_used.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None


def run_display_name(run_dir: Path, recap: dict[str, Any]) -> str:
    """Human label for a run: its recap `run_name`, or the folder name as fallback
    (runs made before the run_name field, e.g. output_1/output_2)."""
    return recap.get("run_name") or run_dir.name


def load_facts(run_dir: Path, side: str) -> pd.DataFrame | None:
    """Tidy (crop x region) fact table for one side ('output'/'input'), or None if the run
    predates the facts table (older output folders)."""
    return load_csv(run_dir, f"facts_{side}.csv")


def load_calibration(run_dir: Path, name: str) -> pd.DataFrame | None:
    """One calibration block ('pad_by_crop', 'pad_by_crop_and_region', 'pad_by_farm',
    'farm_type_confusion', 'field_match'), or None for a run scored before the calibration
    reporting existed."""
    return load_csv(run_dir, f"calibration_{name}.csv")


def load_csv(run_dir: Path, name: str) -> pd.DataFrame | None:
    # CSVs now live in run_dir/csv/; fall back to the run root for older output folders
    # written before that reorg.
    path = run_dir / "csv" / name
    if not path.exists():
        path = run_dir / name
    if not path.exists():
        return None
    return pd.read_csv(path)
