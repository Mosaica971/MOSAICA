"""What the last unit of each constraint costs.

A scenario says "with nitrogen capped at 1.55 Mkg the margin is X". It does not say what the
last kilogram of that cap is worth -- and that is the number a policy is argued over. The
dual of a constraint is exactly that: the rate at which the objective would improve if the
constraint were relaxed by one unit.

A MILP has no duals, so they must come from a linear programme. The usual recipe -- fix the
integers at the optimum and re-solve -- **does not work on this model**, and the failure is
instructive: every variable here is binary, so fixing them all leaves an LP with no free
variables at all, a constant objective, and duals that are uniformly zero. Measured on a real
reduced solve on 2026-08-01: 17 008 constraints, every dual exactly 0.00.

What this module does instead is read the duals of the **linear relaxation** (binaries freed
into [0, 1]). For a resource-type constraint -- a territorial ceiling on nitrogen, a labour
budget, a spending envelope -- that is the standard and meaningful estimate: the relaxation's
dual prices the same physical scarcity.

Three caveats, all reported alongside the numbers and none of them optional reading:

* the duals belong to the **relaxed** optimum, not to the integer allocation the run reports.
  They estimate the marginal value of the constraint; they do not describe the run's own
  solution.
* this model's relaxation is known to be **deeply fractional** (the risk-adjusted objective
  has mixed-sign coefficients -- see config.yaml on mip_rel_gap), so the estimate is looser
  here than in a textbook production LP.
* a dual is **local**. It prices an infinitesimal relaxation. Loosen a ceiling far enough
  that a different set of plots becomes worth switching and the answer jumps; the dual says
  nothing about that.

So: a reading aid for ranking which constraints actually bite and roughly what they cost,
never a figure to quote as the cost of a policy. The honest way to price a bound exactly
remains to re-solve with it moved -- which is what the epsilon-constraint sweeps are for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pyomo.environ as pyo


@dataclass(frozen=True)
class ShadowPrice:
    """One constraint's marginal value, in objective units per unit of the constraint."""

    name: str
    dual: float
    # Where the constraint sits relative to its bound. A slack constraint has a zero dual
    # and costs nothing; only a binding one has a price.
    slack: float
    binding: bool


def compute_shadow_prices(
    model: pyo.ConcreteModel,
    config: dict[str, Any],
    *,
    tolerance: float = 1e-6,
) -> dict[str, ShadowPrice]:
    """Relax the binaries into [0, 1], solve the LP, return its duals.

    The model is restored to its original domains and values before returning, so the caller
    can keep using it for reporting -- the run's own allocation is never disturbed.

    Returns {} rather than raising when the LP does not solve: shadow prices are a bonus on
    top of a finished run, and losing them must never lose the run.
    """
    original_domains = {index: var.domain for index, var in model.Y.items()}
    original_values = {index: var.value for index, var in model.Y.items()}
    original_bounds = {index: (var.lb, var.ub) for index, var in model.Y.items()}
    if not hasattr(model, "dual"):
        model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    try:
        for var in model.Y.values():
            var.domain = pyo.NonNegativeReals
            var.setlb(0.0)
            var.setub(1.0)

        solver_config = config.get("solver") or {}
        solver = pyo.SolverFactory(solver_config.get("name", "appsi_highs"))
        # The MILP's gap and time limit are meaningless for an LP and would only risk an
        # early stop, so they are deliberately not passed through.
        results = solver.solve(model, load_solutions=False)
        if str(results.solver.termination_condition) != "optimal":
            return {}
        model.solutions.load_from(results)

        prices: dict[str, ShadowPrice] = {}
        for constraint in model.component_data_objects(pyo.Constraint, active=True):
            dual = model.dual.get(constraint)
            if dual is None:
                continue
            slack = _slack(constraint)
            prices[constraint.name] = ShadowPrice(
                name=constraint.name,
                dual=float(dual),
                slack=slack,
                binding=abs(slack) <= tolerance,
            )
        return prices
    except Exception:  # noqa: BLE001 -- a missing bonus must not sink a finished run
        return {}
    finally:
        for index, var in model.Y.items():
            var.domain = original_domains[index]
            lower, upper = original_bounds[index]
            var.setlb(lower)
            var.setub(upper)
            var.set_value(original_values[index], skip_validation=True)


def _slack(constraint: pyo.Constraint) -> float:
    """Distance from the constraint's body to its nearest active bound; inf if unbounded."""
    try:
        body = pyo.value(constraint.body)
    except (ValueError, TypeError):
        return float("inf")
    slacks = []
    if constraint.has_lb():
        slacks.append(body - pyo.value(constraint.lower))
    if constraint.has_ub():
        slacks.append(pyo.value(constraint.upper) - body)
    return min(slacks) if slacks else float("inf")


def by_label(
    prices: dict[str, ShadowPrice], config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Shadow prices keyed by the config LABEL that produced them, keeping only the
    constraints a scenario actually names.

    A labelled constraint may be scalar (one territorial bound) or indexed (one per farm or
    per watershed). For an indexed one the individual duals are summarised -- their total is
    what relaxing the whole family by one unit each would be worth, and the count of binding
    members says how widely the rule actually bites.
    """
    labels = [
        entry["args"]["label"]
        for entry in config.get("constraints") or []
        if entry.get("enable") and (entry.get("args") or {}).get("label")
    ]
    summary: dict[str, dict[str, Any]] = {}
    for label in labels:
        members = [
            price for name, price in prices.items()
            if name == label or name.startswith(f"{label}[")
        ]
        if not members:
            continue
        binding = [m for m in members if m.binding]
        summary[label] = {
            "dual": sum(m.dual for m in members),
            "max_dual": max((abs(m.dual) for m in members), default=0.0),
            "members": len(members),
            "binding": len(binding),
            "is_binding": bool(binding),
        }
    return summary
