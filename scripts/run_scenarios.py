"""Run a batch of scenarios sequentially.

Each scenario is a small set of edits applied on top of the reference config
(case_studies/guadeloupe/config.yaml); the batch spec lives in
case_studies/guadeloupe/scenarios.yaml. Every scenario runs the same pipeline as
main.py (build_dataset -> build_model -> solve -> generate_report) and writes its own
timestamped outputs/output_N/ folder, tagged with the scenario name in recap.json.

A spec may be written three ways:
  * `scenarios:` -- a PLAN: it `include:`s catalogues of policies, forcings and Pareto
    sweeps, then names per policy exactly which forcings it goes through and which fronts
    are traced under it. The form to write new work in (case_studies/guadeloupe/plan.yaml);
  * `runs:` -- a flat list of scenarios (case_studies/guadeloupe/scenarios.yaml);
  * `policies:` + `forcings:` -- the catalogues on their own, run as a full product with
    --cross (policies alone without it).

Features:
  * matrix: a run may fan out into the cartesian product of parameter values (expand_runs),
    which is how a Pareto sweep is written -- one solve per point.
  * continue_on_error (default): a failed/infeasible run is recorded and the batch goes on.
  * summary: a batch_summary_<timestamp>.csv/.md comparing every run is written at the end,
    with the headline economics/environment numbers read back from each run's recap.json.

Usage:
    .venv/Scripts/python scripts/run_scenarios.py
    .venv/Scripts/python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml
    .venv/Scripts/python scripts/run_scenarios.py --dry-run          # resolve, don't solve
    .venv/Scripts/python scripts/run_scenarios.py --no-sweeps        # plan minus the fronts
    .venv/Scripts/python scripts/run_scenarios.py --cross            # policies x forcings
    .venv/Scripts/python scripts/run_scenarios.py --policies P3_statu_quo --forcings F4_cyclone
    .venv/Scripts/python scripts/run_scenarios.py --stop-on-error

Note: like main.py, this launches real HiGHS solves (30-55 min each on the full dataset).
Use `zone_filter` overrides in your scenarios to shrink runs while iterating, and --dry-run
to validate a spec before committing a machine to a multi-hour batch.
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Running this file directly puts scripts/ on sys.path, not the repo root, so the
# case_studies/core imports below would fail. Prepend the repo root ourselves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyomo.environ as pyo

from core.case_study import CaseStudy, add_argument, load
from core.config import (
    apply_overrides,
    compose_runs,
    load_batch_spec,
    load_config,
    order_sweep_points,
)
from core.solve.progress import solve_with_progress
from core.solve.warm_start import apply_allocation, constraint_violations
from core.reporting.run_folder import read_allocation

from scripts._common import OUTPUTS_ROOT, SCENARIOS_PATH

_MAX_VIOLATIONS_SHOWN = 5


def _decode_allocation(model: Any) -> dict[str, str]:
    return {
        plot: crop for plot, crop in model.Y if pyo.value(model.Y[plot, crop]) > 0.5
    }


def seed_candidates(
    run_spec: dict[str, Any],
    sweep_seeds: dict[tuple[Any, Any, Any], tuple[dict[str, str], str]],
    policy_seeds: dict[str, dict[str, str]],
    global_seed: tuple[dict[str, str], str] | None,
    chain: bool = True,
) -> list[tuple[dict[str, str], str]]:
    """Seeds to try for `run_spec`, NEAREST FIRST -- the ordering is the whole point.

    A front's previous point differs from this run by one threshold and nothing else, so it
    is the closest allocation that will ever exist; the policy's own unforced run differs by
    a coefficient shock; a global seed differs by everything. Trying them in that order means
    the first one accepted by the audit is also the best one available.

    Pure, so the choice can be tested without a solver: the caller applies and audits each
    candidate in turn and stops at the first that survives.
    """
    candidates: list[tuple[dict[str, str], str]] = []
    if chain:
        key = (run_spec.get("policy"), run_spec.get("forcing"), run_spec.get("sweep"))
        if run_spec.get("sweep") and key in sweep_seeds:
            allocation, origin = sweep_seeds[key]
            candidates.append((allocation, f"{origin} (point precedent)"))
        policy = run_spec.get("policy")
        if policy and policy in policy_seeds:
            candidates.append((policy_seeds[policy], f"{policy} (nominal)"))
    if global_seed:
        candidates.append(global_seed)
    return candidates


def _try_warm_start(model: Any, allocation: dict[str, str], origin: str) -> bool:
    """Seed `model` from `allocation` and say whether the seed is usable.

    Always audited, never assumed: HiGHS discards an infeasible MIP start SILENTLY, so an
    unaudited seed produces a run that looks warm and behaves exactly like a cold one. On a
    violation we report it and fall back to a cold solve rather than pretending.
    """
    if not allocation:
        return False
    report = apply_allocation(model, allocation)
    violations = constraint_violations(model)
    if violations:
        shown = ", ".join(
            f"{name} ({amount:.4g})" for name, amount in violations[:_MAX_VIOLATIONS_SHOWN]
        )
        more = (
            f" (+{len(violations) - _MAX_VIOLATIONS_SHOWN} autres)"
            if len(violations) > _MAX_VIOLATIONS_SHOWN
            else ""
        )
        print(
            f"    warm start depuis {origin} REJETE : {len(violations)} contrainte(s) "
            f"violee(s) : {shown}{more} -> depart a froid"
        )
        return False
    print(f"    warm start depuis {origin} : {report.summary()}")
    return True

# Headline numbers pulled back out of each run's recap.json, so one batch summary answers
# "what did this policy do" without opening ten folders. (recap path, column name).
_RECAP_COLUMNS: list[tuple[tuple[str, ...], str]] = [
    (("economics", "output", "total_gross_margin"), "marge_brute"),
    (("economics", "output", "total_subsidy"), "subventions"),
    (("economics", "output", "total_etp"), "etp"),
    (("economics", "output", "total_production_tonnes"), "production_t"),
    (("output", "total_surface_ha"), "surface_ha"),
    (("environment", "output", "total_azote"), "azote_kg"),
    (("environment", "output", "total_ift"), "ift"),
    (("environment", "output", "total_ges"), "ges_tco2"),
    (("environment", "output", "total_water_need_m3"), "eau_m3"),
    (("food_autonomy", "output", "limiting_with_fishing"), "autonomie_min"),
    (("resilience", "output", "revenue_concentration_hhi"), "hhi_revenu"),
    # Distance to the observed 2017 land use. On a prospective scenario this is NOT a score
    # to minimise -- a scenario that changes policy is meant to move away from 2017; it is
    # here as a magnitude-of-upheaval reading.
    (("calibration", "regional_pad_pct"), "pad_vs_2017"),
]

_FIELDS = (
    ["name", "policy", "forcing", "status", "objective"]
    + [column for _, column in _RECAP_COLUMNS]
    + ["allocated_plots", "duration_s", "output_dir", "error"]
)


def _recap_metrics(output_dir: Path) -> dict[str, Any]:
    """Best-effort read of the run's recap. A missing key yields a blank cell rather than
    sinking the batch: the recap schema evolves, and a summary is not worth a failed run."""
    try:
        recap = json.loads((output_dir / "recap.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    metrics: dict[str, Any] = {}
    for path, column in _RECAP_COLUMNS:
        node: Any = recap
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, (int, float)):
            metrics[column] = round(float(node), 2)
    return metrics


def run_scenarios(
    config_path: Path | None = None,
    scenarios_path: Path = SCENARIOS_PATH,
    outputs_root: Path = OUTPUTS_ROOT,
    continue_on_error: bool = True,
    cross: bool = False,
    policies: list[str] | None = None,
    forcings: list[str] | None = None,
    dry_run: bool = False,
    warm_start_from: Path | None = None,
    warm_start_chain: bool = True,
    sweeps: bool = True,
    case_study: CaseStudy | str | None = None,
) -> list[dict[str, Any]]:
    case = case_study if isinstance(case_study, CaseStudy) else load(case_study)
    config_path = config_path or case.config_path
    base_config = load_config(config_path)
    runs = compose_runs(
        load_batch_spec(scenarios_path, base_config),
        cross=cross,
        policies=policies,
        forcings=forcings,
        sweeps=sweeps,
    )
    if warm_start_chain:
        # Tightest point of each front first, so every solve can seed the next one. Read
        # `order_sweep_points` before changing this: run in the order the YAML lists them,
        # every seed of the chain is infeasible and the front silently solves cold.
        runs = order_sweep_points(runs, base_config)
    if not runs:
        print(f"No runs found in {scenarios_path}")
        return []

    if dry_run:
        # Resolving every run without solving is the cheap way to catch a typo'd label or an
        # unregistered constraint name before committing a machine to a multi-hour batch.
        print(f"Dry run: {len(runs)} run(s) from {scenarios_path.name}\n")
        for index, run_spec in enumerate(runs, start=1):
            name = run_spec.get("name") or f"run_{index}"
            # The coordinates, spelled out: a plan is only auditable if the dry run says
            # which cell each solve belongs to, and the name alone cannot be trusted for
            # that (every sweep name contains the "__" the name is built with).
            coordinates = " ".join(
                f"{key}={run_spec[key]}"
                for key in ("policy", "forcing", "sweep")
                if run_spec.get(key)
            )
            try:
                apply_overrides(base_config, run_spec)
                print(f"  [{index:>3}] {name:<58} {coordinates}")
            except Exception as exc:  # noqa: BLE001 -- report every bad run, not just the first
                print(f"  [{index:>3}] {name}  -> ERROR {type(exc).__name__}: {exc}")
        return []

    print(f"Scenario batch: {len(runs)} run(s) from {scenarios_path.name}\n")
    rows: list[dict[str, Any]] = []

    # Three sources of seed, tried nearest-first (see `candidates` below).
    #
    # `sweep_seeds` -- the PREVIOUS POINT of the same front. Runs of a sweep differ by one
    # threshold and nothing else, so consecutive allocations are as close as two solves of
    # this model ever get. Valid only because `order_sweep_points` put the tightest point
    # first: relaxing a bound cannot make a feasible allocation infeasible, tightening one
    # routinely does.
    #
    # `policy_seeds` -- the policy's own first solved allocation, i.e. its unforced one. A
    # forcing changes COEFFICIENTS (prices, yields, costs, variance), not the feasible set, so
    # that allocation is still feasible under the policy's own forcings -- and a feasible
    # incumbent is exactly what HiGHS cannot find unaided past ~309 000 binaries. The
    # exceptions are real but few (a forcing that bans crops or adds a bound, a yield drop
    # under a tonnage floor).
    #
    # `seed_allocation` -- an optional global one read from a past run folder.
    #
    # None of the three is trusted: every seed is audited against the model's own constraints
    # before the solve, and a rejected one falls back to cold rather than pretending.
    seed_allocation: dict[str, str] = {}
    if warm_start_from is not None:
        seed_allocation = read_allocation(warm_start_from)
        print(f"Graine globale : {warm_start_from} ({len(seed_allocation)} parcelles)\n")
    policy_seeds: dict[str, dict[str, str]] = {}
    sweep_seeds: dict[tuple[Any, Any, Any], tuple[dict[str, str], str]] = {}
    for index, run_spec in enumerate(runs, start=1):
        name = run_spec.get("name") or f"run_{index}"
        print(f"[{index}/{len(runs)}] === {name} ===")
        row: dict[str, Any] = {f: None for f in _FIELDS}
        row["name"] = name
        row["policy"] = run_spec.get("policy")
        row["forcing"] = run_spec.get("forcing")
        try:
            config = apply_overrides(base_config, run_spec)
            config["run_name"] = name
            # Grid coordinates for a composed run; absent on a plain one. `run_sweep` is what
            # lets the Pareto page group a front by what it IS rather than by a name prefix,
            # which stops meaning anything once a front is traced under a policy.
            config["run_policy"] = run_spec.get("policy")
            config["run_forcing"] = run_spec.get("forcing")
            config["run_sweep"] = run_spec.get("sweep")

            dataset = case.build_dataset(config)
            model = case.build_model(dataset, config)

            # `any` short-circuits, so the first seed the audit accepts is used and the
            # remaining (more distant) ones are never applied.
            policy = run_spec.get("policy")
            sweep_key = (policy, run_spec.get("forcing"), run_spec.get("sweep"))
            candidates = seed_candidates(
                run_spec,
                sweep_seeds,
                policy_seeds,
                (seed_allocation, str(warm_start_from)) if seed_allocation else None,
                chain=warm_start_chain,
            )
            warm = any(_try_warm_start(model, alloc, origin) for alloc, origin in candidates)

            results, duration = solve_with_progress(
                model, config, case_study=case.name, warm_start=warm
            )
            term = str(results.solver.termination_condition)
            if warm_start_chain:
                allocation = _decode_allocation(model)
                # Keep the FIRST solved allocation of each policy as its seed. The first is
                # the nominal one (F0 leads the forcings list, and sweeps come after the
                # cells), i.e. the unforced allocation -- the most broadly feasible seed for
                # that policy's other cells.
                if policy and policy not in policy_seeds:
                    policy_seeds[policy] = allocation
                # A sweep's seed, by contrast, is REPLACED at every point: what seeds the next
                # threshold is the one solved just before it, not the front's first point.
                # Feeding an incumbent forward this way cannot bias the front -- a warm start
                # changes how fast an optimum is proven, never what it is -- so even a point
                # that hit its time limit is a legitimate seed for the next.
                if run_spec.get("sweep"):
                    sweep_seeds[sweep_key] = (allocation, name)
            output_dir = case.generate_report(
                dataset, config, model, results, duration, outputs_root=outputs_root
            )
            row.update(
                status=term,
                objective=pyo.value(model.objective),
                allocated_plots=sum(1 for i in model.Y if pyo.value(model.Y[i]) > 0.5),
                duration_s=round(duration, 1),
                output_dir=str(output_dir),
            )
            row.update(_recap_metrics(output_dir))
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

    # The markdown table carries the readable subset; the CSV alongside it has every column.
    md_columns = [
        ("marge_brute", "Marge brute"),
        ("subventions", "Subventions"),
        ("etp", "ETP"),
        ("azote_kg", "N (kg)"),
        ("ift", "IFT"),
        ("eau_m3", "Eau (m3)"),
        ("autonomie_min", "Autonomie"),
    ]
    header = " | ".join(["Scenario", "Status"] + [label for _, label in md_columns] + ["Duration (s)"])
    md_lines = [
        f"# Batch summary ({stamp})",
        "",
        f"| {header} |",
        "|" + "---|" * (len(md_columns) + 3),
    ]
    for r in rows:
        def _fmt(key: str) -> str:
            value = r.get(key)
            return f"{value:,.0f}" if isinstance(value, (int, float)) else "-"

        dur = r["duration_s"] if r["duration_s"] is not None else "-"
        cells = " | ".join(_fmt(key) for key, _ in md_columns)
        md_lines.append(f"| {r['name']} | {r['status']} | {cells} | {dur} |")
    (outputs_root / f"batch_summary_{stamp}.md").write_text("\n".join(md_lines), encoding="utf-8")
    return csv_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Reference config.yaml (default: the case study's own).",
    )
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS_PATH, help="Batch spec YAML")
    add_argument(parser)
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort the batch on the first failing run (default: continue).",
    )
    parser.add_argument(
        "--cross",
        action="store_true",
        help="Cross every policy with every forcing (policies x forcings). Without it, a "
        "policies/forcings spec runs the policies alone -- which is the staged default, "
        "because the full product is a multi-night batch.",
    )
    parser.add_argument(
        "--policies",
        type=lambda s: [part.strip() for part in s.split(",") if part.strip()],
        help="Comma-separated policy names to run (default: all).",
    )
    parser.add_argument(
        "--forcings",
        type=lambda s: [part.strip() for part in s.split(",") if part.strip()],
        help="Comma-separated forcing names to cross with (implies --cross).",
    )
    parser.add_argument(
        "--no-sweeps",
        action="store_true",
        help="Drop every Pareto sweep the plan declares. A front is one solve per point, so "
        "this is how a plan is staged: the cells first, the fronts once they are worth it.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List and resolve the runs without solving -- catches bad labels in seconds.",
    )
    parser.add_argument(
        "--warm-start-from",
        type=Path,
        help="Seed every run from this past run folder's allocation (audited; a seed that "
        "violates a constraint is reported and the run falls back to a cold solve).",
    )
    parser.add_argument(
        "--no-warm-start-chain",
        action="store_true",
        help="Disable seeding each policy's forced runs from its own unforced allocation. "
        "The chain is on by default because it is nearly free and it is what makes a "
        "crossed batch affordable.",
    )
    args = parser.parse_args()

    run_scenarios(
        config_path=args.config,
        scenarios_path=args.scenarios,
        continue_on_error=not args.stop_on_error,
        cross=args.cross or bool(args.forcings),
        policies=args.policies,
        forcings=args.forcings,
        dry_run=args.dry_run,
        warm_start_from=args.warm_start_from,
        warm_start_chain=not args.no_warm_start_chain,
        sweeps=not args.no_sweeps,
        case_study=args.case_study,
    )
