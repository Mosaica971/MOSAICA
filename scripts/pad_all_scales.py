"""Report a run's PAD (Chopin et al. 2015, Eq. 7) at the five scales asked for:
territory-wide, island by island, region by region, farm by farm, and field by field.

Rebuilds the dataset from the run's own config overlay (~7s, no MILP solve), scores the
simulated allocation against the observed 2017 land use, and prints one figure per scale.
The island scale is the addition of 2026-07-23 (calibration.pad_by_island); the other four
come straight from the existing calibration module.

    python scripts/pad_all_scales.py outputs/output_13

The field scale is a match rate, not a share deviation: Chopin et al. express agreement at
the plot level as the fraction of plots whose simulated crop equals the observed one, since
a per-plot "PAD" over a single crop is either 0% or undefined. It is reported as such.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import calibration

from scripts.evaluate_calibration import load_run_config, load_simulated_allocation

TOTAL = calibration.TOTAL_KEY


def _verdict(pad: float, threshold: float) -> str:
    return "OK" if pad <= threshold else "HORS SEUIL"


def report(run_dir: Path) -> None:
    config = load_run_config(run_dir)
    dataset = build_dataset(config)
    allocation = load_simulated_allocation(run_dir)
    thresholds = calibration.thresholds_from_config(config)

    by_crop = calibration.pad_by_crop(dataset, allocation, thresholds)
    by_island = calibration.pad_by_island(dataset, allocation, thresholds)
    by_region = calibration.pad_by_crop_and_region(dataset, allocation, thresholds)
    by_farm = calibration.pad_by_farm(dataset, allocation, thresholds)
    field = calibration.field_match_rate(dataset, allocation)

    # Persist the one table the run's own report does not write.
    by_island.to_csv(run_dir / "csv" / "calibration_pad_by_island.csv")

    print(f"\n=== PAD aux 5 echelles -- {run_dir.name} ===")
    print("(PAD = 100*|observe-simule|/observe sur les 12 groupes RPG observes)\n")

    # 1. Global / territorial.
    territorial = float(by_crop.loc[TOTAL, "pad_pct"])
    print("1. GLOBALE (territoire)")
    print(
        f"   PAD territorial : {territorial:6.1f}%   "
        f"(seuil {thresholds.regional_pad_max:.0f}%, {_verdict(territorial, thresholds.regional_pad_max)})"
    )

    # 2. Island by island.
    print("\n2. ILE PAR ILE")
    for island, row in by_island.iterrows():
        pad = float(row["pad_pct"])
        print(
            f"   Ile {str(island):<12} PAD {pad:6.1f}%   "
            f"(obs {row['observed_ha']:9.1f} ha / sim {row['simulated_ha']:9.1f} ha, "
            f"{_verdict(pad, thresholds.subregional_pad_max)})"
        )

    # 3. Region by region: the per-region TOTAL rows of the sub-regional table.
    print("\n3. REGION PAR REGION (7 sous-regions)")
    totals = by_region[by_region.index.get_level_values("crop") == TOTAL]
    for (region, _crop), row in totals.iterrows():
        pad = float(row["pad_pct"])
        print(
            f"   Region {str(region):<10} PAD {pad:6.1f}%   "
            f"(obs {row['observed_ha']:9.1f} ha / sim {row['simulated_ha']:9.1f} ha, "
            f"{_verdict(pad, thresholds.subregional_pad_max)})"
        )

    # 4. Farm by farm: a distribution, not a single figure -- the acreage-weighted mean of
    #    the per-farm PADs collapses back to the territorial PAD, so what a farm scale adds
    #    is how the deviation spreads across holdings.
    pad_farm = by_farm["pad_pct"].dropna()
    within = int(by_farm["within_threshold"].fillna(False).astype(bool).sum())
    evaluated = int(by_farm["pad_pct"].notna().sum())
    print("\n4. EXPLOITATION PAR EXPLOITATION")
    print(f"   Exploitations evaluees      : {evaluated}")
    print(
        f"   PAD median / moyen          : {pad_farm.median():6.1f}% / {pad_farm.mean():6.1f}%"
    )
    print(
        f"   Sous le seuil {thresholds.farm_pad_max:.0f}%          : "
        f"{within} / {evaluated}  ({100.0 * within / evaluated:4.1f}%)"
    )
    print(
        f"   Quartiles PAD (25/50/75)    : "
        f"{pad_farm.quantile(0.25):5.1f}% / {pad_farm.quantile(0.5):5.1f}% / "
        f"{pad_farm.quantile(0.75):5.1f}%"
    )

    # 5. Field by field: a match rate.
    total = field.loc[TOTAL]
    print("\n5. PARCELLE PAR PARCELLE (taux de correspondance, pas un PAD)")
    print(
        f"   Parcelles bien simulees     : {total['plot_match_pct']:6.1f}%  "
        f"({int(total['matched_plots'])} / {int(total['total_plots'])})"
    )
    print(f"   Surface bien simulee        : {total['area_match_pct']:6.1f}%")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="An outputs/output_N folder.")
    args = parser.parse_args(argv)
    report(args.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
