"""Hand a MILP solver a known-good starting solution.

A warm start does not change what the optimum is. It changes only how fast the solver can
prove it: branch-and-bound prunes a node when the node's LP bound is worse than the best
solution found so far, so a good incumbent supplied up front prunes from the first node
instead of after the solver's heuristics stumble on one. With `mip_rel_gap` termination it
matters twice over -- the gap is measured against the incumbent, so a good start can close
it immediately.

Why this module exists here rather than in a script: on 2026-07-29 two territorial
constraints (a pineapple ceiling, an orchard floor) each hit the one-hour limit with an
incumbent 5.5% below a solution repaired by hand in seconds from the previous run. The
model is past the size where HiGHS finds a good incumbent unaided, so every further
constraint needs one supplied. See docs/04-vigilance.md, "Le PAD residuel".

Two functions, deliberately separate:

- `apply_allocation` writes a plot -> crop assignment into `model.Y`. HiGHS reads
  `var.value` off every variable when `warmstart=True` (pyomo/contrib/appsi/solvers/
  highs.py::_warm_start), so the whole vector must be written, zeros included.
- `constraint_violations` audits that assignment against the model's own constraints
  BEFORE solving. An infeasible start is not an error -- the solver discards it -- but it
  is an hour wasted, and silently getting no speed-up is the failure mode this guards.

Both are case-study-agnostic: they know about `Y`, `PAIRS` and Pyomo constraints, nothing
about crops, farms or Guadeloupe.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pyomo.environ as pyo


@dataclass(frozen=True)
class WarmStartReport:
    """What `apply_allocation` could and could not place.

    `dropped` is the interesting one: a pair the source allocation holds but this model has
    no variable for, i.e. the eligibility mask changed between the two runs. A large
    `dropped` means the start is stale and probably infeasible.
    """

    assigned: int = 0
    dropped: list[tuple[str, str]] = field(default_factory=list)
    plots_left_empty: int = 0

    def summary(self) -> str:
        text = f"{self.assigned} paires placees, {self.plots_left_empty} parcelles laissees vides"
        if self.dropped:
            text += f", {len(self.dropped)} paires ignorees (non eligibles dans ce modele)"
        return text


def apply_allocation(
    model: pyo.ConcreteModel, allocation: Mapping[str, str]
) -> WarmStartReport:
    """Write `allocation` (plot -> crop) into `model.Y` as a complete 0/1 vector.

    Every variable is written, not only the ones set to 1: HiGHS builds its start from
    `var.value` over all columns, and a `None` there is read as 0.0 anyway -- writing the
    zeros explicitly is what makes the intent, and the audit below, well defined.

    Pairs the model does not carry are skipped rather than raising: allocations are read
    back from earlier runs whose eligibility mask may differ, and the useful behaviour is
    to start from what still applies.
    """
    dropped = []
    wanted = {}
    for plot, crop in allocation.items():
        if (plot, crop) in model.PAIRS:
            wanted[plot] = crop
        else:
            dropped.append((plot, crop))

    assigned = 0
    for plot, crop in model.PAIRS:
        chosen = wanted.get(plot) == crop
        model.Y[plot, crop].set_value(1.0 if chosen else 0.0, skip_validation=False)
        assigned += chosen

    plots_left_empty = sum(1 for plot in model.PLOTS if plot not in wanted)
    return WarmStartReport(
        assigned=assigned, dropped=dropped, plots_left_empty=plots_left_empty
    )


def constraint_violations(
    model: pyo.ConcreteModel, tolerance: float = 1e-6
) -> list[tuple[str, float]]:
    """Constraints the current variable values violate, as (name, amount) worst first.

    Evaluates each active constraint's body at the values now held by the variables. A
    constraint whose body cannot be evaluated (a variable left at None) is reported with an
    infinite violation rather than skipped -- an unevaluable start is not a feasible one.

    Empty list = the assignment satisfies every constraint, so it is a genuine incumbent
    and the solver's first bound comparison will already be meaningful.
    """
    violations: list[tuple[str, float]] = []
    for constraint in model.component_data_objects(pyo.Constraint, active=True):
        try:
            body = pyo.value(constraint.body)
        except (ValueError, TypeError):
            violations.append((constraint.name, float("inf")))
            continue

        amount = 0.0
        if constraint.has_lb():
            amount = max(amount, pyo.value(constraint.lower) - body)
        if constraint.has_ub():
            amount = max(amount, body - pyo.value(constraint.upper))
        if amount > tolerance:
            violations.append((constraint.name, amount))

    violations.sort(key=lambda item: item[1], reverse=True)
    return violations


def objective_value(model: pyo.ConcreteModel) -> float:
    """The objective at the current variable values -- the incumbent the solver is being
    handed. Compare it against a past run's to know whether the start is worth supplying."""
    return float(pyo.value(model.objective))
