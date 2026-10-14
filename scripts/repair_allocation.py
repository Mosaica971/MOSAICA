"""Repair a past run's allocation so it can seed a new run as a warm start.

Two repairs, one per way a past allocation stops being feasible:

* a new SURFACE FLOOR (`--crops/--min-surface`): switch the cheapest plots onto the floored
  crops until the floor is met;
* tighter PER-FARM CAPS (`--farm-caps`): the labour budget (Eq_MO_MAX_Expl) and the per-farm
  production quotas (Eq_BA_QUOTA_Expl) of the current data. Needed when the caps themselves
  move -- on 2026-09-28 the baseline ITKs of domain/baseline_itk tightened the labour cap by
  10.6 % and the banana quota by 15 %, and every allocation solved before was rejected.

Why this exists: past ~309 000 binaries, HiGHS no longer finds a good incumbent unaided. On
2026-07-29 an orchard floor and a pineapple ceiling each hit the one-hour limit with an
incumbent 5.5% below a solution repaired by hand in seconds. Supplying that repair as a warm
start is the fix (core/solve/warm_start.py); this script produces it.

    python scripts/repair_allocation.py outputs/output_3 \
        --crops AG,VE_BTGT,VE_PLUIE --min-surface 335 --out outputs/_warmstart_plu
    python scripts/repair_allocation.py outputs/calib_gams_parite_prix --farm-caps \
        --scenarios case_studies/guadeloupe/scenarios_calibration_prices.yaml \
        --run calib_gams_parity_prices --out outputs/_warmstart_parity_prices

`--scenarios/--run` build the configuration of the run to seed (its overrides applied), so the
repair and its audit see exactly the constraints that run will; without them, config.yaml.

The floor heuristic is deliberately simple and greedy: among the plots that may be switched,
take the ones where moving to the best eligible target crop costs the least risk-adjusted
margin per hectare, until the floor is met. It respects the per-farm labour cap while doing
so, because that is the constraint the switches actually consume.

The farm-cap heuristic works farm by farm: while a farm exceeds a cap, move the plot whose
switch costs the least risk-adjusted margin per unit of excess removed, onto a crop that
demands no more labour -- or leave it empty. It never moves a plot ONTO a crop some ceiling
counts (territorial or per-farm production, area share, rotation denominator), nor AWAY from
a crop a floor or a rotation numerator counts, so it cannot break what the seed satisfied.

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
from core.config import apply_overrides, compose_runs, load_batch_spec, load_config
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
    plot_data = parameters["plot_data"]
    surface = plot_data["SURF_HA"]
    mask = parameters["eligibility_mask"]
    margin = parameters["crop_margin_per_ha"]
    variance = parameters["crop_variance_per_ha"].fillna(0.0)
    labor = parameters["crop_labor_hours_per_ha"]
    cap = pd.Series(parameters["farm_labor_capacity_hours"], dtype=float)
    farm = indicators.plot_to_farm(dataset).reindex(plot_data.index)
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
                "from": crop,
                "to": best,
                "ha": float(surface[plot]),
                "cost_eur": value_of(plot, crop) - value_of(plot, best),
                "delta_h": float(surface[plot]) * (float(labor[best]) - float(labor[crop])),
            }
        )

    frame = pd.DataFrame(candidates)
    if frame.empty:
        raise SystemExit("No plot can be switched: check --crops and --freeze.")
    frame["cost_eur_ha"] = frame["cost_eur"] / frame["ha"]
    frame = frame.sort_values("cost_eur_ha")

    switched = []
    for row in frame.itertuples():
        if held >= min_surface:
            break
        if row.delta_h > slack.get(row.farm, 0.0):
            continue
        slack[row.farm] -= row.delta_h
        allocation[row.plot] = row.to
        held += row.ha
        switched.append(row.Index)

    if held < min_surface:
        raise SystemExit(
            f"Floor out of reach for this heuristic: {held:.1f} ha out of "
            f"{min_surface:.1f} requested. The available labour hours are "
            f"probably the limiting factor."
        )
    return allocation, frame.loc[switched]


def _enabled(config: dict, name: str) -> list[dict]:
    return [
        e.get("args") or {}
        for e in config.get("constraints", [])
        if e.get("enable") and e["name"] == name
    ]


def repair_farm_caps(
    config: dict, run_dir: Path, freeze: set[str]
) -> tuple[dict[str, str], pd.DataFrame]:
    """Bring every farm back under its labour budget and its per-farm production quotas.

    Return (repaired allocation, table of the switches made). A plot moves either onto an
    eligible crop needing no more labour than its current one, or to empty (at most one crop
    per plot allows it); the cheapest move per unit of excess removed goes first.
    """
    dataset = build_dataset(config)
    parameters = dataset.parameters
    plot_data = parameters["plot_data"]
    surface = plot_data["SURF_HA"]
    mask = parameters["eligibility_mask"]
    margin = parameters["crop_margin_per_ha"]
    variance = parameters["crop_variance_per_ha"].fillna(0.0)
    labor = parameters["crop_labor_hours_per_ha"].fillna(0.0)
    crop_yield = parameters["crop_yield"].fillna(0.0)
    farm = indicators.plot_to_farm(dataset).reindex(plot_data.index)
    aversion = farm.map(parameters["farm_risk_aversion"]).fillna(0.0)

    # Caps, read the way the enabled builders read them (core/model/constraints.py).
    caps: list[tuple[str, dict, pd.Series]] = []
    for args in _enabled(config, "farm_labor_hours_max"):
        budget = pd.Series(parameters["farm_labor_capacity_hours"], dtype=float)
        caps.append(("labour_h", (budget * float(args.get("slack", 1.0))).to_dict(), labor))
    for args in _enabled(config, "farm_production_bound"):
        if args.get("sense", "le") != "le":
            continue
        reference = parameters["farm_baseline_production_t"].get(args["reference"], {})
        rate = crop_yield.where(crop_yield.index.isin(args["crops"]), 0.0)
        limits = {f: v * float(args.get("scale", 1.0)) for f, v in reference.items()}
        caps.append((f"{args['label']}_t", limits, rate))

    # Crops a move must never land on: anything a ceiling or a rotation denominator counts.
    blocked: set[str] = set()
    for args in _enabled(config, "territory_production_bound"):
        if args.get("sense") == "le":
            for group in args.get("groups", []):
                blocked.update(group.get("crops", []))
    for args in _enabled(config, "farm_production_bound"):
        blocked.update(args.get("crops", []))
    for args in _enabled(config, "farm_area_share_max"):
        blocked.update(args.get("crops", []))
    # ...and crops a plot must never leave: floors and rotation numerators.
    frozen = set(freeze)
    for args in _enabled(config, "farm_area_ratio_min"):
        blocked.update(args.get("denominator_crops", []))
        frozen.update(args.get("numerator_crops", []))

    def value_of(plot: str, crop) -> float:
        if crop is None:
            return 0.0
        return float(surface[plot]) * float(margin[crop]) * (
            1.0 - float(aversion[plot]) * float(variance[crop])
        )

    allocation: dict = dict(read_allocation(run_dir))
    by_farm: dict[str, list[str]] = {}
    for plot in allocation:
        by_farm.setdefault(farm[plot], []).append(plot)
    targets = [c for c in mask.columns if c not in blocked]

    def load(plots: list[str], rate: pd.Series) -> float:
        return sum(
            float(surface[p]) * float(rate.get(allocation[p], 0.0))
            for p in plots
            if allocation.get(p) is not None
        )

    switches = []
    for farm_id, plots in by_farm.items():
        while True:
            excess = {}
            for name, limits, rate in caps:
                if farm_id in limits:
                    over = load(plots, rate) - limits[farm_id]
                    if over > 1e-6:
                        excess[name] = over
            if not excess:
                break
            best = None
            for plot in plots:
                crop = allocation.get(plot)
                if crop is None or crop in frozen:
                    continue
                options = [
                    t for t in targets
                    if t != crop and bool(mask.at[plot, t]) and float(labor[t]) <= float(labor[crop])
                ]
                options.append(None)
                for target in options:
                    reduction = 0.0
                    for name, _limits, rate in caps:
                        if name in excess:
                            before = float(rate.get(crop, 0.0))
                            after = 0.0 if target is None else float(rate.get(target, 0.0))
                            reduction += float(surface[plot]) * (before - after) / excess[name]
                    if reduction <= 1e-12:
                        continue
                    cost = value_of(plot, crop) - value_of(plot, target)
                    score = cost / reduction
                    if best is None or score < best[0]:
                        best = (score, plot, crop, target, cost)
            if best is None:
                raise SystemExit(f"{farm_id}: over its cap and no plot can be moved -- {excess}")
            _score, plot, crop, target, cost = best
            # An empty plot is kept as None and dropped when the allocation is written.
            allocation[plot] = target
            switches.append(
                {"plot": plot, "farm": farm_id, "from": crop, "to": target or "(empty)",
                 "ha": float(surface[plot]), "cost_eur": cost}
            )
    return {p: c for p, c in allocation.items() if c is not None}, pd.DataFrame(switches)


def _config_for(args: argparse.Namespace) -> dict:
    """config.yaml, or the configuration of `--run` in `--scenarios` with its overrides."""
    config = load_config(CONFIG_PATH)
    if args.scenarios is None:
        return config
    runs = [
        r for r in compose_runs(load_batch_spec(args.scenarios, config))
        if args.run in r.get("name", "")
    ]
    if len(runs) != 1:
        raise SystemExit(f"--run {args.run!r} matches {len(runs)} run(s) in {args.scenarios}")
    return apply_overrides(config, runs[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=Path, help="Run to repair, e.g. outputs/output_3")
    parser.add_argument("--crops", help="Comma-separated crops the floor covers")
    parser.add_argument("--min-surface", type=float, help="Floor, in hectares")
    parser.add_argument(
        "--farm-caps", action="store_true",
        help="Repair the per-farm labour budget and production quotas instead of a floor.",
    )
    parser.add_argument("--scenarios", type=Path, help="Batch spec of the run to seed")
    parser.add_argument("--run", help="Name (or unique fragment) of the run to seed, with --scenarios")
    parser.add_argument("--out", type=Path, required=True, help="Folder to write the repaired allocation to")
    parser.add_argument(
        "--freeze",
        default=None,
        help="Comma-separated crops never switched away from. Defaults to every crop "
        "carrying an enabled production/surface floor.",
    )
    args = parser.parse_args(argv)
    if args.farm_caps == bool(args.crops or args.min_surface is not None):
        parser.error("pass either --farm-caps or --crops with --min-surface")
    if (args.scenarios is None) != (args.run is None):
        parser.error("--scenarios and --run go together")

    config = _config_for(args)
    freeze = (
        {c.strip() for c in args.freeze.split(",") if c.strip()}
        if args.freeze is not None
        else _floored_crops(config)
    )
    print(f"frozen crops: {sorted(freeze) or '(none)'}")
    if args.farm_caps:
        allocation, switches = repair_farm_caps(config, args.run_dir, freeze)
    else:
        crops = [c.strip() for c in args.crops.split(",") if c.strip()]
        print(f"target crops: {crops}")
        allocation, switches = repair(config, args.run_dir, crops, args.min_surface, freeze)
    print(
        f"\n{len(switches)} plots switched, {switches['ha'].sum():.1f} ha, "
        f"cost {switches['cost_eur'].sum():,.0f} EUR"
    )
    print(switches.groupby("from")["ha"].sum().sort_values(ascending=False).head(10).round(1).to_string())

    # The only thing that matters about a warm start: is it feasible? Rebuild and audit.
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    report = apply_allocation(model, allocation)
    violations = constraint_violations(model)
    print(f"\naudit : {report.summary()}")
    print(f"objective of the start: {objective_value(model):,.2f}")
    if violations:
        print(f"WARNING: {len(violations)} constraint(s) violated -- HiGHS will discard this start:")
        for name, amount in violations[:5]:
            print(f"   {name} : {amount:.6g}")
    else:
        print("start is FEASIBLE for the current configuration.")
        if not args.farm_caps:
            print("  (if the target floor is not yet enabled in config.yaml, enable it:")
            print("   that is precisely the run this start exists to unblock.)")

    csv_dir = args.out / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"plot": list(allocation.keys()), "crop": list(allocation.values())}
    ).to_csv(csv_dir / "allocation_output.csv", index=False)
    print(f"\nwritten to {args.out} -- usable through solver.warm_start_from in config.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
