from typing import Any

import pyomo.environ as pyo


def solve_model(model: pyo.ConcreteModel, config: dict[str, Any]) -> Any:
    solver_config = config["solver"]
    solver_name = solver_config["name"]
    args = solver_config.get("args") or {}

    solver = pyo.SolverFactory(solver_name)
    results = solver.solve(model, load_solutions=False, **args)

    condition = results.solver.termination_condition
    if condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(
            f"Solver '{solver_name}' did not reach an optimal solution "
            f"(termination condition: {condition})"
        )

    model.solutions.load_from(results)
    return results
