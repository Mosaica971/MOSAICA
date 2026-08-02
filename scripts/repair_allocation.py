"""Repair a past run's allocation so it satisfies a new surface floor, for use as a warm start.

Why this exists: past ~309 000 binaries, HiGHS no longer finds a good incumbent unaided. On
2026-07-29 an orchard floor and a pineapple ceiling each hit the one-hour limit with an
incumbent 5.5% below a solution repaired by hand in seconds. Supplying that repair as a warm
start is the fix (core/solve/warm_start.py); this script produces it.

    python scripts/repair_allocation.py outputs/output_3 \
        --crops AG,VE_BTGT,VE_PLUIE --min-surface 335 --out outputs/_warmstart_plu

The heuristic is deliberately simple and greedy: among the plots that may be switched, take
the ones where moving to the best eligible target crop costs the least risk-adjusted margin
per hectare, until the floor is met. It respects the per-farm labour cap while doing so,
because that is the constraint the switches actually consume.

It does NOT try to be clever, and it does not need to: a warm start only has to be feasible
and decent, the solver improves it from there. What matters is that it IS feasible, so the
script rebuilds the model and audits the result -- and says so plainly when it is not.

--freeze protects crops another constraint pins (anything carrying its own floor). It
defaults to the crops of every enabled `sense: ge` territory bound, which is the sensible
reading of "do not rob a crop that has a floor of its own".
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from case_studies.guadeloupe.model.model import build_model
from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import indicators
from core.config import load_config
from core.solve.warm_start import apply_allocation, constraint_violations, objective_value
from core.reporting.run_folder import read_allocation

from scripts._common import CONFIG_PATH


def _floored_crops(config: dict) -> set[str]:
    """Crops carrying a production/surface floor -- taking area from them would break it."""
    floored: set[str] = set()
    for entry in config.get("constraints", []):
        args = entry.get("args") or {}
        if not entry.get("enable") or args.get("sense") != "ge":
            continue
        for group in args.get("groups", []):
            floored.update(group.get("crops", []))
    return floored


def repair(
    config: dict,
    run_dir: Path,
    crops: list[str],
    min_surface: float,
    freeze: set[str],
) -> tuple[dict[str, str], pd.DataFrame]:
    """Return (repaired allocation, table of the switches made)."""
    dataset = build_dataset(config)
    parameters = dataset.parameters
    data_parc = parameters["data_parc"]
    surface = data_parc["SURF_HA"]
    mask = parameters["eligibility_mask"]
    margin = parameters["margin_per_ha_cult"]
    variance = parameters["crop_variance_per_ha"].fillna(0.0)
    labor = parameters["labor_hours_per_ha_cult"]
    cap = pd.Series(parameters["farm_labor_capacity_hours"], dtype=float)
    farm = indicators.plot_to_farm(dataset).reindex(data_parc.index)
    aversion = farm.map(parameters["farm_risk_aversion"]).fillna(0.0)

    allocation = dict(read_allocation(run_dir))
    targets = [crop for crop in crops if crop in mask.columns]

    def value_of(plot: str, crop: str) -> float:
        return (
            float(surface[plot])
            * float(margin[crop])
            * (1.0 - float(aversion[plot]) * float(variance[crop]))
        )

    held = sum(float(surface[p]) for p, c in allocation.items() if c in targets)
    hours = pd.Series(
        {
            plot: float(surface[plot]) * float(labor[crop])
            for plot, crop in allocation.items()
        }
    )
    slack = (cap - hours.groupby(farm.reindex(hours.index)).sum().reindex(cap.index).fillna(0.0)).clip(lower=0.0)

    candidates = []
    for plot, crop in allocation.items():
        if crop in targets or crop in freeze:
            continue
        options = [c for c in targets if bool(mask.at[plot, c])]
        if not options:
            continue
        best = max(options, key=lambda c: value_of(plot, c))
        candidates.append(
            {
                "plot": plot,
                "farm": farm[plot],
                "de": crop,
                "vers": best,
                "ha": float(surface[plot]),
                "cout_eur": value_of(plot, crop) - value_of(plot, best),
                "delta_h": float(surface[plot]) * (float(labor[best]) - float(labor[crop])),
            }
        )

    frame = pd.DataFrame(candidates)
    if frame.empty:
        raise SystemExit("Aucune parcelle basculable : verifiez --crops et --freeze.")
    frame["cout_eur_ha"] = frame["cout_eur"] / frame["ha"]
    frame = frame.sort_values("cout_eur_ha")

    switched = []
    for row in frame.itertuples():
        if held >= min_surface:
            break
        if row.delta_h > slack.get(row.farm, 0.0):
            continue
        slack[row.farm] -= row.delta_h
        allocation[row.plot] = row.vers
        held += row.ha
        switched.append(row.Index)

    if held < min_surface:
        raise SystemExit(
            f"Plancher inatteignable par cette heuristique : {held:.1f} ha sur "
            f"{min_surface:.1f} demandes. Les heures de main d'oeuvre disponibles sont "
            f"probablement le facteur limitant."
        )
    return allocation, frame.loc[switched]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help="Run to repair, e.g. outputs/output_3")
    parser.add_argument("--crops", required=True, help="Comma-separated crops the floor covers")
    parser.add_argument("--min-surface", type=float, required=True, help="Floor, in hectares")
    parser.add_argument("--out", type=Path, required=True, help="Folder to write the repaired allocation to")
    parser.add_argument(
        "--freeze",
        default=None,
        help="Comma-separated crops never switched away from. Defaults to every crop "
        "carrying an enabled production/surface floor.",
    )
    args = parser.parse_args(argv)

    config = load_config(CONFIG_PATH)
    freeze = (
        {c.strip() for c in args.freeze.split(",") if c.strip()}
        if args.freeze is not None
        else _floored_crops(config)
    )
    crops = [c.strip() for c in args.crops.split(",") if c.strip()]
    print(f"cultures cibles : {crops}")
    print(f"cultures gelees : {sorted(freeze) or '(aucune)'}")

    allocation, switches = repair(config, args.run_dir, crops, args.min_surface, freeze)
    print(
        f"\n{len(switches)} parcelles basculees, {switches['ha'].sum():.1f} ha, "
        f"cout {switches['cout_eur'].sum():,.0f} EUR"
    )
    print(switches.groupby("de")["ha"].sum().sort_values(ascending=False).head(10).round(1).to_string())

    # The only thing that matters about a warm start: is it feasible? Rebuild and audit.
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    report = apply_allocation(model, allocation)
    violations = constraint_violations(model)
    print(f"\naudit : {report.summary()}")
    print(f"objectif du depart : {objective_value(model):,.2f}")
    if violations:
        print(f"ATTENTION : {len(violations)} contrainte(s) violee(s) -- ce depart sera ignore par HiGHS :")
        for name, amount in violations[:5]:
            print(f"   {name} : {amount:.6g}")
    else:
        print("depart FAISABLE pour la configuration courante.")
        print("  (si le plancher vise n'est pas encore active dans config.yaml, activez-le :")
        print("   c'est precisement le run que ce depart sert a debloquer.)")

    csv_dir = args.out / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"plot": list(allocation.keys()), "crop": list(allocation.values())}
    ).to_csv(csv_dir / "allocation_output.csv", index=False)
    print(f"\necrit dans {args.out} -- utilisable via solver.warm_start_from dans config.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
