"""Run a batch of scenarios sequentially.

Each scenario is a small set of edits applied on top of the reference config
(case_studies/guadeloupe/config.yaml); the batch spec lives in
case_studies/guadeloupe/scenarios.yaml. Every scenario runs the same pipeline as
main.py (build_dataset -> build_model -> solve -> generate_report) and writes its own
timestamped outputs/output_N/ folder, tagged with the scenario name in recap.json.

Features:
  * matrix: a run may fan out into the cartesian product of parameter values (expand_runs).
  * continue_on_error (default): a failed/infeasible run is recorded and the batch goes on.
  * summary: a batch_summary_<timestamp>.csv/.md comparing every run is written at the end.

Usage:
    .venv/Scripts/python scripts/run_scenarios.py
    .venv/Scripts/python scripts/run_scenarios.py --scenarios path/to/other.yaml
    .venv/Scripts/python scripts/run_scenarios.py --stop-on-error

Note: like main.py, this launches real HiGHS solves (~30s each on the full dataset).
Use `zone_filter` overrides in your scenarios to shrink runs while iterating.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Running this file directly puts scripts/ on sys.path, not the repo root, so the
# case_studies/core imports below would fail. Prepend the repo root ourselves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyomo.environ as pyo

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from case_studies.guadeloupe.reporting.report import generate_report
from core.config import apply_overrides, expand_runs, load_config
from core.model.progress import solve_with_progress

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "case_studies" / "guadeloupe" / "config.yaml"
SCENARIOS_PATH = ROOT / "case_studies" / "guadeloupe" / "scenarios.yaml"
OUTPUTS_ROOT = ROOT / "outputs"

_FIELDS = ["name", "status", "objective", "allocated_plots", "duration_s", "output_dir", "error"]


def run_scenarios(
    config_path: Path = CONFIG_PATH,
    scenarios_path: Path = SCENARIOS_PATH,
    outputs_root: Path = OUTPUTS_ROOT,
    continue_on_error: bool = True,
) -> list[dict[str, Any]]:
    base_config = load_config(config_path)
    runs = expand_runs((load_config(scenarios_path) or {}).get("runs") or [])
    if not runs:
        print(f"No runs found in {scenarios_path}")
        return []

    print(f"Scenario batch: {len(runs)} run(s) from {scenarios_path.name}\n")
    rows: list[dict[str, Any]] = []
    for index, run_spec in enumerate(runs, start=1):
        name = run_spec.get("name") or f"run_{index}"
        print(f"[{index}/{len(runs)}] === {name} ===")
        row: dict[str, Any] = {f: None for f in _FIELDS}
        row["name"] = name
        try:
            config = apply_overrides(base_config, run_spec)
            config["run_name"] = name

            dataset = build_dataset(config)
            model = build_model(dataset, config)
            results, duration = solve_with_progress(
                model, config, case_study=config_path.parent.name
            )
            term = str(results.solver.termination_condition)
            output_dir = generate_report(
                dataset, config, model, results, duration, outputs_root=outputs_root
            )
            row.update(
                status=term,
                objective=pyo.value(model.objective),
                allocated_plots=sum(1 for i in model.Y if pyo.value(model.Y[i]) > 0.5),
                duration_s=round(duration, 1),
                output_dir=str(output_dir),
            )
            print(
                f"    {term} | objective = {row['objective']:,.2f} "
                f"| plots = {row['allocated_plots']} | {row['duration_s']}s -> {output_dir}\n"
            )
        except Exception as exc:  # noqa: BLE001 -- one bad run must not sink the batch
            row["status"] = "error"
            row["error"] = f"{type(exc).__name__}: {exc}"
            print(f"    ERROR: {row['error']}\n")
            if not continue_on_error:
                rows.append(row)
                _write_summary(outputs_root, rows)
                raise
        rows.append(row)

    summary_path = _write_summary(outputs_root, rows)
    print(f"Batch summary written to: {summary_path}")
    return rows


def _write_summary(outputs_root: Path, rows: list[dict[str, Any]]) -> Path:
    outputs_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = outputs_root / f"batch_summary_{stamp}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    md_lines = [
        f"# Batch summary ({stamp})",
        "",
        "| Scenario | Status | Objective | Plots | Duration (s) |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        obj = f"{r['objective']:,.2f}" if r["objective"] is not None else "-"
        plots = r["allocated_plots"] if r["allocated_plots"] is not None else "-"
        dur = r["duration_s"] if r["duration_s"] is not None else "-"
        md_lines.append(f"| {r['name']} | {r['status']} | {obj} | {plots} | {dur} |")
    (outputs_root / f"batch_summary_{stamp}.md").write_text("\n".join(md_lines), encoding="utf-8")
    return csv_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Reference config.yaml")
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS_PATH, help="Batch spec YAML")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort the batch on the first failing run (default: continue).",
    )
    args = parser.parse_args()

    run_scenarios(
        config_path=args.config,
        scenarios_path=args.scenarios,
        continue_on_error=not args.stop_on_error,
    )
