from typing import Any

import pyomo.environ as pyo


def solve_model(model: pyo.ConcreteModel, solver_name: str = "appsi_highs") -> Any:
    solver = pyo.SolverFactory(solver_name)
    results = solver.solve(model, load_solutions=False)

    condition = results.solver.termination_condition
    if condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(
            f"Solver '{solver_name}' did not reach an optimal solution "
            f"(termination condition: {condition})"
        )

    model.solutions.load_from(results)
    return results
