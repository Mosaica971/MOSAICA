from dataclasses import dataclass
from typing import Any

from pyomo.contrib.appsi.base import TerminationCondition
from pyomo.contrib.appsi.solvers.highs import Highs
import pyomo.environ as pyo


@dataclass
class SolveResult:
    """Normalized solve outcome. Shields callers from the APPSI results shape --
    report.py only needs the (stringified) termination condition."""

    termination_condition: str


def solve_model(model: pyo.ConcreteModel, config: dict[str, Any]) -> SolveResult:
    # Persistent APPSI interface rather than SolverFactory('appsi_highs'): profiling
    # (brique D) showed the LegacySolver wrapper spends ~15s translating the ~500k-var
    # model into HiGHS structures, dwarfing the ~6s HiGHS solve. The persistent path
    # skips that wrapper for ~25% less wall-clock. See docs/superpowers/specs/
    # 2026-07-10-solver-appsi-persistent-interface-design.md.
    solver_config = config["solver"]
    solver_name = solver_config["name"]
    args = solver_config.get("args") or {}

    solver = Highs()
    solver.config.load_solution = False  # we load explicitly, only on an optimal solve
    solver.highs_options.update(args)

    results = solver.solve(model)

    condition = results.termination_condition
    if condition != TerminationCondition.optimal:
        raise RuntimeError(
            f"Solver '{solver_name}' did not reach an optimal solution "
            f"(termination condition: {condition.name})"
        )

    solver.load_vars()
    return SolveResult(termination_condition=condition.name)
