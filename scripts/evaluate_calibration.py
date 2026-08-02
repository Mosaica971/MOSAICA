"""Score a past run against the observed 2017 land use (Chopin et al. 2015, §2.6).

Reads a run's simulated allocation from its allocation_output.csv, rebuilds the dataset
from the run's own config_used.yaml (~7s, no MILP solve), computes every calibration block
and writes them next to the run's other CSVs -- exactly what generate_report now does for
new runs, made available for the runs that predate it.

    python scripts/evaluate_calibration.py outputs/output_12
    python scripts/evaluate_calibration.py --all

The dataset rebuild is not optional: the farm-type confusion matrix needs the full plot
universe, NC plots included, and allocation_input.csv drops them. Scoring from the CSVs
alone would shift the PART_* shares and could flip a farm's type.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import yaml

from apps.dashboard.loaders import list_output_runs
from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import calibration
from case_studies.guadeloupe.reporting.report import write_calibration
from core.config import load_config

from scripts._common import CONFIG_PATH, OUTPUTS_ROOT

_ALLOCATION_CSV = "allocation_output.csv"


def load_simulated_allocation(run_dir: Path) -> pd.Series:
    """plot -> fine crop, from a run's allocation_output.csv (csv/ or, for older runs,
    the run root)."""
    path = run_dir / "csv" / _ALLOCATION_CSV
    if not path.exists():
        path = run_dir / _ALLOCATION_CSV
    if not path.exists():
        raise FileNotFoundError(f"{run_dir}: no {_ALLOCATION_CSV} (csv/ or run root)")
    frame = pd.read_csv(path)
    return pd.Series(frame["crop"].to_numpy(), index=frame["plot"], name="crop")


def load_run_config(run_dir: Path) -> dict:
    """Config to score a run with: the current config.yaml, overlaid with the run's own
    zone_filter, data selection and calibration thresholds.

    Deliberately NOT the run's config_used.yaml taken verbatim. An older run may name
    components that no longer exist in the registry -- output_12 references the
    `melon_soil_restriction` categorical rule, dropped in the 2026-07-21 refactor -- and
    build_dataset would raise on it. Nothing the overlay leaves behind matters here: the
    calibration metrics need the plot universe (zone_filter), the economic year/scenario
    and the thresholds, never the eligibility mask, the constraints or the objective.
    """
    config = load_config(CONFIG_PATH)
    path = run_dir / "config_used.yaml"
    if not path.exists():
        return config

    run_config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("zone_filter", "data"):
        # Popping matters as much as setting: the current config may carry a zone_filter
        # the run did not have, which would silently score it on a subset.
        if key in run_config:
            config[key] = run_config[key]
        else:
            config.pop(key, None)

    thresholds = (run_config.get("reporting") or {}).get("calibration")
    if thresholds:
        config.setdefault("reporting", {})["calibration"] = thresholds
    return config


def evaluate_run(run_dir: Path) -> calibration.CalibrationResult:
    config = load_run_config(run_dir)
    dataset = build_dataset(config)
    result = calibration.evaluate(dataset, load_simulated_allocation(run_dir), config)
    write_calibration(result, run_dir)
    return result


def _print_verdicts(run_dir: Path, result: calibration.CalibrationResult) -> None:
    summary = result.summary()

    def line(label: str, value: float | None, threshold: float, ok: bool) -> str:
        shown = "n/a" if value is None else f"{value:6.1f}%"
        return f"  {label:<34} {shown}  (seuil {threshold:.0f}%)  {'OK' if ok else 'HORS SEUIL'}"

    print(f"\n{run_dir.name}")
    print(
        line(
            "PAD territorial",
            summary["regional_pad_pct"],
            summary["thresholds"]["regional_pad_max"],
            summary["regional_within_threshold"],
        )
    )
    print(
        line(
            "Types d'exploitation reproduits",
            summary["farm_type_match_pct"],
            summary["thresholds"]["farm_type_match_min"],
            summary["farm_type_within_threshold"],
        )
    )
    print(
        f"  {'Cultures sous seuil':<34} "
        f"{summary['crops_within_threshold']} / {summary['crops_evaluated']}"
    )
    print(
        f"  {'Exploitations sous seuil':<34} "
        f"{summary['farms_within_threshold']} / {summary['farms_evaluated']}"
    )
    print(
        f"  {'Parcelles bien simulees':<34} {summary['plot_match_pct']:6.1f}%  "
        f"({summary['matched_plots']} / {summary['total_plots']})"
    )
    print(f"  {'Surface bien simulee':<34} {summary['area_match_pct']:6.1f}%")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", type=Path, help="An outputs/output_N folder.")
    parser.add_argument("--all", action="store_true", help="Score every run in outputs/.")
    args = parser.parse_args(argv)
    if bool(args.run_dir) == args.all:
        parser.error("pass exactly one of a run folder / --all")

    # list_output_runs already filters outputs/ to well-formed output_N folders and sorts
    # them; it is Streamlit-free by design, so a script may use it.
    runs = list_output_runs(OUTPUTS_ROOT) if args.all else [args.run_dir]

    failures = 0
    for run_dir in runs:
        try:
            _print_verdicts(run_dir, evaluate_run(run_dir))
        except (FileNotFoundError, KeyError) as error:
            print(f"\n{run_dir.name}\n  ignore : {error}", file=sys.stderr)
            failures += 1
    return 1 if failures and len(runs) == 1 else 0


if __name__ == "__main__":
    raise SystemExit(main())
