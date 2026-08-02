"""Pre-flight feasibility check for a scenario batch -- no MILP solve.

Each scenario is built exactly as run_scenarios.py would, then its binary variables are
relaxed to the [0, 1] interval and the resulting LP is solved. The logic is one-way and
that is the whole point:

    LP infeasible  => the MILP is infeasible too. Certain. Fix the scenario.
    LP feasible    => the MILP MAY still be infeasible (integrality can kill it), but every
                      infeasibility this project has actually hit was algebraic, not
                      integral -- a labour cap against a production floor, a share required
                      of crops that no plot may carry.

An LP over ~309 000 relaxed binaries takes seconds where the MILP takes 30-55 minutes, so
this turns "the batch died at 3 a.m. on run 7" into a 2-minute check beforehand. The LP
objective it prints is also a valid upper bound on the scenario's MILP objective.

Usage:
    .venv/Scripts/python scripts/check_scenario_feasibility.py
    .venv/Scripts/python scripts/check_scenario_feasibility.py --scenarios <path> --cross
    .venv/Scripts/python scripts/check_scenario_feasibility.py --policies P9,P10
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pyomo.environ as pyo
from pyomo.opt import TerminationCondition

from case_studies.guadeloupe.model.model import build_model, _INDICATOR_PARAMETERS
from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from core.config import apply_overrides, compose_runs, load_batch_spec, load_config

from scripts._common import CONFIG_PATH, SCENARIOS_PATH

_INFEASIBLE = {
    TerminationCondition.infeasible,
    TerminationCondition.infeasibleOrUnbounded,
}

# Parameters that fully determine how the model sees a crop. Two crops equal on all of them
# are interchangeable to the solver.
_IDENTITY_PARAMETERS = ("margin_per_ha_cult", "crop_variance_per_ha", *_INDICATOR_PARAMETERS.values())


def symmetric_crop_groups(dataset) -> list[list[str]]:
    """Groups of crops the model cannot tell apart: equal on every parameter it reads.

    Interchangeable copies are the worst case for branch-and-bound -- the search explores
    equivalent permutations of the same solution and never proves optimality. They are also
    a modelling hazard in their own right: a share constraint that distinguishes crops the
    DATA does not distinguish is satisfied by relabelling, at zero cost, and so constrains
    nothing while looking like a policy.

    Found for real on 2026-07-31: the 25 experimental market-gardening variants are
    byte-identical copies of one conventional activity, and reopening them added 548 000
    binaries of pure symmetry plus a no-op organic share. Hence this check runs before any
    batch.
    """
    active = sorted({crop for _, crop in dataset.parameters["eligible_pairs"]})
    columns = {
        name: dataset.parameters[name].reindex(active)
        for name in _IDENTITY_PARAMETERS
        if name in dataset.parameters
    }
    table = pd.DataFrame(columns).round(6)
    groups = table.groupby(list(table.columns), dropna=False).groups
    return [sorted(map(str, members)) for members in groups.values() if len(members) > 1]


def check(
    config_path: Path = CONFIG_PATH,
    scenarios_path: Path = SCENARIOS_PATH,
    cross: bool = False,
    policies: list[str] | None = None,
    forcings: list[str] | None = None,
    # Sweeps are checked by DEFAULT here, unlike anywhere else. The tightest point of a front
    # is precisely the run most likely to be infeasible, so a pre-flight check that skipped
    # it would skip the thing it exists for -- and an LP point costs minutes against the
    # front's hours.
    sweeps: bool = True,
) -> list[tuple[str, str, float | None]]:
    base_config = load_config(config_path)
    runs = compose_runs(
        load_batch_spec(scenarios_path, base_config),
        cross=cross,
        policies=policies,
        forcings=forcings,
        sweeps=sweeps,
    )
    print(f"Feasibility pre-check: {len(runs)} scenario(s) from {scenarios_path.name}")
    print("(LP relaxation -- infeasible here is certain, feasible here is necessary but "
          "not sufficient)\n")

    solver = pyo.SolverFactory("appsi_highs")
    results: list[tuple[str, str, float | None]] = []
    for index, run_spec in enumerate(runs, start=1):
        name = run_spec.get("name") or f"run_{index}"
        started = time.perf_counter()
        try:
            config = apply_overrides(base_config, run_spec)
            dataset = build_dataset(config)
            for group in symmetric_crop_groups(dataset):
                print(
                    f"      SYMETRIE: {len(group)} cultures indistinguables par le modele "
                    f"({', '.join(group[:4])}{'...' if len(group) > 4 else ''}) -- "
                    f"branch-and-bound bien plus lent, et toute contrainte qui les "
                    f"distingue est satisfaite par simple renommage."
                )
            model = build_model(dataset, config)
            for var in model.Y.values():
                var.domain = pyo.NonNegativeReals
                var.setlb(0.0)
                var.setub(1.0)
            # load_solutions=False is required, not stylistic: on an infeasible LP the
            # appsi_highs interface raises when it tries to load a solution that does not
            # exist, and the exception would be reported as a build error rather than as
            # the infeasibility verdict this script is for.
            outcome = solver.solve(model, load_solutions=False)
            term = outcome.solver.termination_condition
            if term in _INFEASIBLE:
                verdict, bound = "INFEASIBLE", None
            else:
                verdict = str(term)
                bound = getattr(outcome.solver, "best_feasible_objective", None)
                if bound is None:
                    model.solutions.load_from(outcome)
                    bound = pyo.value(model.objective)
        except Exception as exc:  # noqa: BLE001 -- a build error is a result, not a crash
            verdict, bound = f"error: {type(exc).__name__}: {exc}", None
        elapsed = time.perf_counter() - started
        shown = f"{bound:,.0f}" if bound is not None else "-"
        print(f"  [{index:>3}/{len(runs)}] {name:<48} {verdict:<14} bound={shown:>16}  {elapsed:.0f}s")
        results.append((name, verdict, bound))

    bad = [r for r in results if r[1] == "INFEASIBLE" or r[1].startswith("error")]
    print(f"\n{len(results) - len(bad)}/{len(results)} scenario(s) pass the LP check.")
    for name, verdict, _ in bad:
        print(f"  FAILS: {name} -- {verdict}")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS_PATH)
    parser.add_argument("--cross", action="store_true")
    parser.add_argument(
        "--policies", type=lambda s: [p.strip() for p in s.split(",") if p.strip()]
    )
    parser.add_argument(
        "--forcings", type=lambda s: [p.strip() for p in s.split(",") if p.strip()]
    )
    parser.add_argument(
        "--no-sweeps",
        action="store_true",
        help="Skip the Pareto sweeps a plan declares (checked by default -- their tightest "
        "point is the likeliest infeasibility in the batch).",
    )
    args = parser.parse_args()
    outcome = check(
        config_path=args.config,
        scenarios_path=args.scenarios,
        cross=args.cross or bool(args.forcings),
        policies=args.policies,
        forcings=args.forcings,
        sweeps=not args.no_sweeps,
    )
    failures = sum(1 for _, verdict, _ in outcome if verdict == "INFEASIBLE" or verdict.startswith("error"))
    sys.exit(1 if failures else 0)
