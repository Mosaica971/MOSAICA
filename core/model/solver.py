from typing import Any

import pyomo.environ as pyo


def solve_model(model: pyo.ConcreteModel, config: dict[str, Any]) -> Any:
    solver_config = config["solver"]
    solver_name = solver_config["name"]
    args = solver_config.get("args") or {}

    solver = pyo.SolverFactory(solver_name)
    # HiGHS options go through solver.options, NOT as solve() kwargs: the appsi_highs legacy
    # wrapper rejects unknown solve() kwargs (mip_rel_gap etc. raise TypeError there). The
    # option names are HiGHS's own (mip_rel_gap, time_limit, threads, ...).
    for key, value in args.items():
        solver.options[key] = value
    results = solver.solve(model, load_solutions=False)

    condition = results.solver.termination_condition
    if condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(
            f"Solver '{solver_name}' did not reach an optimal solution "
            f"(termination condition: {condition})"
        )

    model.solutions.load_from(results)
    return results
