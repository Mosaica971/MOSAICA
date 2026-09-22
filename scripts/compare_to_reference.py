"""Put a run side by side with the 2017 reference state.

    python scripts/compare_to_reference.py outputs/output_1

Reads the reference folder written by scripts/build_reference_state.py and the CSV/recap
files the run already wrote -- no dataset rebuild, no solve, ~1 s. Writes
`reference_comparison.md` into the run folder and prints the headline block.

Two readings the run's own recap does not give:

* the deviation per crop is confronted with the REPRODUCIBILITY FLOOR of the reference, so a
  crop the model structurally cannot place (orchards, citrus) is not read as a modelling
  failure;
* every indicator gap is confronted with the reference's OWN BRACKET. The observed side has
  no fine crops, so its economics is an assumption with a range; a gap smaller than that
  range says nothing about the model. This is the difference between "the model loses 970
  FTE" and "the model lands inside the uncertainty of the observed figure".

The run's recap and config are read through apps.dashboard.loaders, so a run written before
the English renaming of 2026-09-22 compares exactly like a new one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from apps.dashboard import loaders
from case_studies.guadeloupe.domain.farm_typology import FARM_TYPE_LABELS

from scripts._common import OUTPUTS_ROOT, ROOT, format_number as _n

REFERENCE_DIR_NAME = "reference_2017"
TOTAL_KEY = "TOTAL"

# Reference indicator -> where the same quantity lives in a run's recap.json. The reference
# is built with the very same indicators.* functions, so these are the same computations on
# two allocations, not two definitions of one word.
_RECAP_KEYS: dict[str, tuple[str, str]] = {
    "production_tonnes": ("economics", "total_production_tonnes"),
    "subsidy": ("economics", "total_subsidy"),
    "revenue": ("economics", "total_revenue"),
    "gross_margin": ("economics", "total_gross_margin"),
    "labor_cost": ("economics", "total_labor_cost"),
    "net_revenue": ("economics", "total_net_revenue"),
    "fte": ("economics", "total_fte"),
    "nitrogen": ("environment", "total_nitrogen"),
    "ghg": ("environment", "total_ghg"),
    "tfi": ("environment", "total_tfi"),
    "chlordecone_risk_area": ("environment", "chlordecone_risk_area"),
    "water_need_m3": ("environment", "total_water_need_m3"),
    "soil_carbon_balance": ("environment", "soil_carbon_balance"),
}


def _relative(path: Path) -> str:
    """Repo-relative path when the folder sits inside the repo, so the markdown stays
    readable (and copy-pasteable) whatever the absolute location is."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _run_side(recap: dict[str, Any], name: str) -> float | None:
    """The run's output-side value for a reference indicator, None when it has none."""
    if name == "sales":
        economics = recap["economics"]["output"]
        return economics["total_revenue"] - economics["total_subsidy"]
    if name == "labor_hours":
        return None  # compared through fte, which the recap carries directly
    block, key = _RECAP_KEYS.get(name, (None, None))
    if block is None:
        return None
    return recap[block]["output"][key]


def _reference_bracket(reference: dict[str, Any], name: str) -> tuple[float | None, float | None]:
    entry = reference["indicators"].get(name) or {}
    return entry.get("low"), entry.get("high")


def _within_bracket(value: float, low: float | None, high: float | None) -> bool | None:
    """True when the run's figure falls inside the reference's own uncertainty -- i.e. the
    gap is not evidence of anything. None when the indicator has no bracket."""
    if low is None or high is None:
        return None
    return min(low, high) <= value <= max(low, high)


def _verdict(passed: bool) -> str:
    return "OK" if passed else "OUTSIDE THRESHOLD"


def compare(run_dir: Path, reference_dir: Path) -> str:
    recap = loaders.load_recap(run_dir)
    reference = json.loads((reference_dir / "reference.json").read_text(encoding="utf-8"))
    pad_by_crop = pd.read_csv(run_dir / "csv" / "calibration_pad_by_crop.csv", index_col=0)
    field_match = pd.read_csv(run_dir / "csv" / "calibration_field_match.csv", index_col=0)
    confusion = pd.read_csv(
        run_dir / "csv" / "calibration_farm_type_confusion.csv", index_col=0
    )
    repro = pd.read_csv(
        reference_dir / "csv" / "reference_reproducibility.csv", index_col=0
    )
    run_config = loaders.load_config_used(run_dir) or {}
    hours_per_fte = float((run_config.get("labor") or {}).get("hours_per_fte", 1607.0))

    calib = recap["calibration"]
    universe = reference["universe"]
    total = pad_by_crop.loc[TOTAL_KEY]
    field_total = field_match.loc[TOTAL_KEY]

    lines = [
        f"# {run_dir.name} vs the 2017 reference state",
        "",
        f"- Reference: `{reference_dir.name}` "
        f"({_n(universe['cultivated_area_ha'])} ha cultivated, "
        f"{_n(universe['cultivated_plots'])} plots, "
        f"{_n(universe['farms'])} farms)",
        f"- Run: objective `{recap['objective']['name']}` = "
        f"{_n(recap['objective']['value'])}, solved in "
        f"{recap['solve_duration_seconds']:.0f} s ({recap['termination_condition']})",
        f"- Year / scenario: {recap['data']['year']} / {recap['data']['scenario']}",
        "",
        "## 1. Calibration verdict",
        "",
        "| Metric | Value | Threshold (Chopin et al. 2015) | Verdict |",
        "|---|---:|---:|---|",
        f"| Territorial PAD | {calib['regional_pad_pct']:.1f} % | "
        f"{calib['thresholds']['regional_pad_max']:.0f} % | "
        f"{_verdict(calib['regional_within_threshold'])} |",
        f"| Crops under threshold | {calib['crops_within_threshold']} / "
        f"{calib['crops_evaluated']} | 8 / 10 | "
        f"{_verdict(calib['crops_within_threshold'] >= 8)} |",
        f"| Farm types reproduced | {calib['farm_type_match_pct']:.1f} % | "
        f"{calib['thresholds']['farm_type_match_min']:.0f} % | "
        f"{_verdict(calib['farm_type_within_threshold'])} |",
        f"| Farms under threshold | {calib['farms_within_threshold']} / "
        f"{calib['farms_evaluated']} | - | - |",
        f"| Plots correctly simulated | {calib['plot_match_pct']:.1f} % | 66 % (article) | "
        f"{_verdict(calib['plot_match_pct'] >= 66)} |",
        f"| Area correctly simulated | {calib['area_match_pct']:.1f} % | 77 % (article) | "
        f"{_verdict(calib['area_match_pct'] >= 77)} |",
        "",
        "PAD floor induced by eligibility alone: "
        f"{reference['pad_floor_pct']:.1f} % "
        f"({_n(reference['irreproducible_area_ha'])} ha irreproducible). The observed gap",
        "is therefore overwhelmingly a choice of the model, not an impossibility.",
        "",
        "## 2. Land use: observed vs simulated",
        "",
        "`irreprod.` recalls the part of the observation no fine variant could carry.",
        "",
        "| Group | Observed (ha) | Simulated (ha) | Gap (ha) | PAD | Irreprod. (ha) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for group, row in pad_by_crop.drop(index=TOTAL_KEY).iterrows():
        pad = "-" if pd.isna(row["pad_pct"]) else f"{row['pad_pct']:.0f} %"
        irreproducible = (
            _n(repro.loc[group, "irreproducible_ha"]) if group in repro.index else "-"
        )
        lines.append(
            f"| {group} | {_n(row['observed_ha'])} | {_n(row['simulated_ha'])} | "
            f"{row['simulated_ha'] - row['observed_ha']:+,.0f} | {pad} | {irreproducible} |".replace(
                ",", " "
            )
        )
    lines += [
        f"| **TOTAL** | {_n(total['observed_ha'])} | {_n(total['simulated_ha'])} | "
        f"{total['simulated_ha'] - total['observed_ha']:+,.0f} | "
        f"{total['pad_pct']:.1f} % | "
        f"{_n(repro['irreproducible_ha'].sum())} |".replace(",", " "),
        "",
        "## 3. Indicators: reference vs run",
        "",
        "The \"inside the bracket\" column compares the gap with the reference's own",
        "uncertainty (see REFERENCE.md section 4.1). \"yes\" = the run falls within the range",
        "of plausible observed cropping plans: the gap to the central value proves nothing.",
        "",
        "| Indicator | Reference (central) | Bracket | Run | Gap | Inside the bracket |",
        "|---|---:|---:|---:|---:|:--:|",
    ]

    verdicts: list[tuple[str, bool | None]] = []
    for name, entry in reference["indicators"].items():
        central = entry.get("central")
        run_value = _run_side(recap, name)
        if run_value is None or central is None:
            continue
        low, high = _reference_bracket(reference, name)
        # FTE has no bracket of its own; it is labor_hours / hours_per_fte, so it inherits it.
        if name == "fte":
            hours = reference["indicators"].get("labor_hours") or {}
            low = (hours.get("low") or 0) / hours_per_fte or None
            high = (hours.get("high") or 0) / hours_per_fte or None
        inside = _within_bracket(run_value, low, high)
        verdicts.append((name, inside))
        bracket = "-" if low is None or high is None else f"{_n(low)} - {_n(high)}"
        gap = f"{100.0 * (run_value - central) / central:+.0f} %" if central else "-"
        flag = {True: "yes", False: "no", None: "-"}[inside]
        lines.append(
            f"| {name} | {_n(central)} | {bracket} | {_n(run_value)} | {gap} | {flag} |"
        )

    inside_count = sum(1 for _, value in verdicts if value is True)
    bracketed = sum(1 for _, value in verdicts if value is not None)

    lines += [
        "",
        f"{inside_count} bracketed indicator(s) out of {bracketed} fall inside the reference's",
        "bracket.",
        "",
        "## 4. Farm types",
        "",
        "Reading reminder: the diagonal is the reproduction rate. The row-marginal is the",
        "reference (observed typology), the column-marginal what the run produces.",
        "",
        "| Type | Observed | Simulated | Reproduced (recall) |",
        "|---|---:|---:|---:|",
    ]
    recall = calib.get("farm_type_recall_by_type", {})
    observed_totals = confusion.sum(axis=1)
    simulated_totals = confusion.sum(axis=0)
    for code in confusion.index:
        diagonal = confusion.loc[code, str(code)] if str(code) in confusion.columns else 0
        observed = observed_totals.loc[code]
        share = f"{100.0 * diagonal / observed:.0f} %" if observed else "-"
        lines.append(
            f"| {code} {FARM_TYPE_LABELS.get(int(code), '')} | {_n(observed)} | "
            f"{_n(simulated_totals.get(str(code), 0))} | {share} |"
        )
    if recall:
        worst = sorted(recall.items(), key=lambda item: item[1])[:3]
        lines += [
            "",
            "Least well reproduced types: "
            + ", ".join(f"{label} ({value:.0f} %)" for label, value in worst)
            + ".",
        ]

    lines += [
        "",
        "## 5. Going further",
        "",
        f"- `python scripts/pad_all_scales.py {_relative(run_dir)}`: the PAD at five scales,",
        "  island by island included (rebuilds the dataset, ~7 s).",
        "- `csv/calibration_pad_by_crop_and_region.csv`: the sub-regional detail.",
        f"- `{_relative(reference_dir)}/REFERENCE.md`: how the reference is built and what it",
        "  cannot say.",
        "",
        f"Plot agreement: {int(field_total['matched_plots'])} plots out of "
        f"{int(field_total['total_plots'])} carry the observed crop "
        f"({field_total['area_match_pct']:.1f} % of the area).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="An outputs/output_N folder.")
    parser.add_argument(
        "--reference",
        type=Path,
        default=OUTPUTS_ROOT / REFERENCE_DIR_NAME,
        help=f"Reference folder (default outputs/{REFERENCE_DIR_NAME}).",
    )
    args = parser.parse_args(argv)

    if not (args.reference / "reference.json").exists():
        parser.error(
            f"{args.reference} has no reference.json -- run scripts/build_reference_state.py first"
        )

    markdown = compare(args.run_dir, args.reference)
    destination = args.run_dir / "reference_comparison.md"
    destination.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\nWritten to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
