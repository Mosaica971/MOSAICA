from typing import Any

import pyomo.environ as pyo


def solve_model(
    model: pyo.ConcreteModel, config: dict[str, Any], *, warm_start: bool = False
) -> Any:
    """Solve `model` with the solver named in `config['solver']`.

    `warm_start=True` hands HiGHS the values currently held by the model's variables as a
    MIP start (see core/model/warm_start.py for how to put them there and why it matters).
    It is a search hint only: the optimum, and the gap it is proven to, are unchanged.
    Pyomo's legacy APPSI wrapper maps the `warmstart` kwarg onto `config.warmstart`, which
    the Highs interface turns into `setSolution` (pyomo/contrib/appsi/solvers/highs.py).
    Passing it with no values set is harmless -- the interface checks and skips.
    """
    solver_config = config["solver"]
    solver_name = solver_config["name"]
    args = solver_config.get("args") or {}

    solver = pyo.SolverFactory(solver_name)
    # HiGHS options go through solver.options, NOT as solve() kwargs: the appsi_highs legacy
    # wrapper rejects unknown solve() kwargs (mip_rel_gap etc. raise TypeError there). The
    # option names are HiGHS's own (mip_rel_gap, time_limit, threads, ...).
    for key, value in args.items():
        solver.options[key] = value
    results = solver.solve(model, load_solutions=False, warmstart=warm_start)

    # `optimal` here means "proven within mip_rel_gap of the optimum" (HiGHS reports optimal
    # once the gap closes to the configured tolerance, not only at gap 0). A time limit hit
    # (`maxTimeLimit`) still leaves a feasible incumbent that is strictly better than a looser
    # gap would give, so we accept and load it -- but loudly, because it is NOT gap-proven.
    # Any other condition (infeasible, unbounded, error) has no usable solution: raise.
    condition = results.solver.termination_condition
    acceptable = {
        pyo.TerminationCondition.optimal,
        pyo.TerminationCondition.maxTimeLimit,
    }
    if condition not in acceptable:
        raise RuntimeError(
            f"Solver '{solver_name}' did not reach a usable solution "
            f"(termination condition: {condition})"
        )

    try:
        model.solutions.load_from(results)
    except (ValueError, RuntimeError, IndexError, AttributeError) as error:
        # maxTimeLimit before any incumbent was found -> nothing to load.
        raise RuntimeError(
            f"Solver '{solver_name}' terminated with '{condition}' and no loadable "
            f"solution (no incumbent found within the time limit)"
        ) from error

    if condition != pyo.TerminationCondition.optimal:
        print(
            f"WARNING: solver '{solver_name}' stopped at '{condition}' (time limit) rather "
            f"than closing the MIP gap; using the best incumbent found. Acreages may be "
            f"slightly sub-optimal.",
            flush=True,
        )
    return results
