"""Robustness of a policy across a grid of external forcings.

Reads a grid of outcomes -- {(policy, forcing): value} -- and summarises, per policy, how
well an indicator holds up when the world does not cooperate. Pure arithmetic on plain
dicts: no pandas dependency on the input side, no run folders, no solver.

WHY THIS IS NOT THE `resilience` BLOCK OF A RUN. That block applies a price shock *after*
the solve to a frozen allocation, so it measures EXPOSURE -- what is lost if nobody can
react. The grid here re-solves the model under each forcing, so the allocation has already
adapted within whatever room the policy leaves it. That is ADAPTIVE CAPACITY UNDER POLICY
CONSTRAINT, a different quantity. Never average the two into one score.

THREE DELIBERATE CHOICES, each of which changes conclusions:

* **Infeasibility is the worst outcome, not a missing value.** A policy with no solution
  under a forcing has failed absolutely; dropping the cell would silently reward it by
  computing its statistics over the forcings it survived. Pass such cells as None and they
  are counted, excluded from the spread statistics, and made to dominate the worst case.
* **Forcings are not averaged by default.** A favourable outlook and a systemic crisis are
  not equally likely, and a mean over them asserts a probability distribution nobody chose.
  The headline statistics are order statistics (worst case, median) and regret. `weights`
  exists for when you do want to assert one.
* **Regret is computed against the best policy in the same column**, i.e. against what one
  should have chosen with hindsight for that particular forcing. That is Savage's criterion,
  and it is the reason the grid was built rather than a set of independent runs.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from statistics import median, pstdev

# A grid cell holds the indicator's value, or None when that (policy, forcing) pair had no
# solution (infeasible, or the run errored out).
Grid = Mapping[tuple[str, str], "float | None"]


@dataclass(frozen=True)
class PolicyRobustness:
    """One policy's profile on one indicator, across the forcings it was run against."""

    policy: str
    nominal: float | None
    worst: float | None
    best: float | None
    median: float | None
    mean: float | None
    # Standard deviation over the feasible cells, and its ratio to the mean. The ratio is
    # the comparable one across indicators of different units.
    spread: float | None
    coefficient_of_variation: float | None
    # worst / nominal, i.e. the share of its own unforced promise the policy still delivers
    # in its worst forcing. None when there is no nominal, or when the nominal is 0.
    retention: float | None
    # Savage: the largest shortfall against the best policy of the same forcing.
    max_regret: float | None
    # Starr / RDM satisficing: share of forcings meeting the viability threshold. Infeasible
    # cells count as failures, which is the point.
    viability: float | None
    forcings_evaluated: int
    forcings_infeasible: int
    infeasible_forcings: tuple[str, ...] = field(default_factory=tuple)


def policies_in(grid: Grid) -> list[str]:
    return sorted({policy for policy, _ in grid})


def forcings_in(grid: Grid) -> list[str]:
    return sorted({forcing for _, forcing in grid})


def _feasible_values(grid: Grid, policy: str) -> dict[str, float]:
    return {
        forcing: float(value)
        for (p, forcing), value in grid.items()
        if p == policy and value is not None and math.isfinite(float(value))
    }


def _best_by_forcing(grid: Grid, higher_is_better: bool) -> dict[str, float]:
    """Best value achieved by ANY policy under each forcing -- the hindsight benchmark."""
    best: dict[str, float] = {}
    for (_, forcing), value in grid.items():
        if value is None or not math.isfinite(float(value)):
            continue
        value = float(value)
        if forcing not in best:
            best[forcing] = value
        else:
            best[forcing] = max(best[forcing], value) if higher_is_better else min(best[forcing], value)
    return best


def summarise_policy(
    grid: Grid,
    policy: str,
    *,
    higher_is_better: bool = True,
    nominal_forcing: str | None = None,
    viability_threshold: float | None = None,
    weights: Mapping[str, float] | None = None,
) -> PolicyRobustness:
    """Robustness profile of one policy on the indicator the grid holds.

    `higher_is_better` flips every notion of "worst" and "best" (margin vs nitrogen).
    `nominal_forcing` names the neutral cell used as the denominator of `retention`.
    `viability_threshold` is read in the indicator's own units, in the direction implied by
    `higher_is_better`. `weights` turns `mean` into a weighted mean over the forcings, which
    is the only statistic here that a probability judgement should touch.
    """
    values = _feasible_values(grid, policy)
    all_forcings = [f for (p, f) in grid if p == policy]
    infeasible = tuple(sorted(f for f in all_forcings if f not in values))

    nominal = values.get(nominal_forcing) if nominal_forcing is not None else None

    if not values:
        return PolicyRobustness(
            policy=policy, nominal=None, worst=None, best=None, median=None, mean=None,
            spread=None, coefficient_of_variation=None, retention=None, max_regret=None,
            viability=0.0 if all_forcings else None,
            forcings_evaluated=len(all_forcings), forcings_infeasible=len(infeasible),
            infeasible_forcings=infeasible,
        )

    numbers = list(values.values())
    worst = min(numbers) if higher_is_better else max(numbers)
    best = max(numbers) if higher_is_better else min(numbers)
    # An infeasible forcing IS the worst case -- there is no value to compare, so the worst
    # case is reported as None rather than as the worst of the survivors, which would read
    # as if the policy had held.
    if infeasible:
        worst = None

    mean = _weighted_mean(values, weights)
    spread = pstdev(numbers) if len(numbers) > 1 else 0.0
    cv = (spread / abs(mean)) if (mean not in (None, 0.0)) else None

    retention = None
    if nominal not in (None, 0.0) and worst is not None:
        # For a cost indicator the ratio is inverted (nominal / worst), so a worst case of
        # exactly 0 -- every cell at zero nitrogen, say -- would divide by zero. Undefined
        # rather than infinite: "kept infinitely more than it promised" is not a reading.
        retention = (
            worst / nominal if higher_is_better else (nominal / worst if worst else None)
        )

    benchmark = _best_by_forcing(grid, higher_is_better)
    regrets = [
        (benchmark[f] - v) if higher_is_better else (v - benchmark[f])
        for f, v in values.items()
        if f in benchmark
    ]
    # A policy that is infeasible somewhere has unbounded regret there; represented as None
    # so a ranking cannot quietly place it above a policy that merely did badly.
    max_regret = max(regrets, default=0.0) if not infeasible else None

    viability = None
    if viability_threshold is not None and all_forcings:
        met = sum(
            1
            for f in all_forcings
            if f in values
            and (values[f] >= viability_threshold if higher_is_better else values[f] <= viability_threshold)
        )
        viability = met / len(all_forcings)

    return PolicyRobustness(
        policy=policy, nominal=nominal, worst=worst, best=best,
        median=median(numbers), mean=mean, spread=spread, coefficient_of_variation=cv,
        retention=retention, max_regret=max_regret, viability=viability,
        forcings_evaluated=len(all_forcings), forcings_infeasible=len(infeasible),
        infeasible_forcings=infeasible,
    )


def _weighted_mean(
    values: Mapping[str, float], weights: Mapping[str, float] | None
) -> float | None:
    if not values:
        return None
    if not weights:
        return sum(values.values()) / len(values)
    applicable = {f: float(weights[f]) for f in values if f in weights and weights[f] > 0}
    if not applicable:
        return sum(values.values()) / len(values)
    total = sum(applicable.values())
    return sum(values[f] * w for f, w in applicable.items()) / total


def summarise_grid(
    grid: Grid,
    *,
    higher_is_better: bool = True,
    nominal_forcing: str | None = None,
    viability_threshold: float | None = None,
    weights: Mapping[str, float] | None = None,
    policies: Iterable[str] | None = None,
) -> list[PolicyRobustness]:
    """One PolicyRobustness per policy, in the order given (or sorted by name)."""
    wanted = list(policies) if policies is not None else policies_in(grid)
    return [
        summarise_policy(
            grid,
            policy,
            higher_is_better=higher_is_better,
            nominal_forcing=nominal_forcing,
            viability_threshold=viability_threshold,
            weights=weights,
        )
        for policy in wanted
    ]


def normalise_grid(
    grid: Grid,
    mode: str,
    *,
    higher_is_better: bool = True,
    nominal_forcing: str | None = None,
) -> dict[tuple[str, str], float | None]:
    """Rescale the grid for display. Three readings of the same numbers:

    * `absolute` -- untouched.
    * `vs_nominal` -- each cell as a share of its own policy's unforced value, so the
      heatmap shows how much of its promise each policy keeps under each forcing. Answers
      "how badly is this policy hurt", independently of how good it was to begin with.
    * `regret` -- each cell as a share of the best value achieved by any policy under that
      same forcing. Answers "how far from the best available choice, in hindsight". A column
      always contains at least one 1.0.
    """
    if mode == "absolute":
        return dict(grid)
    if mode == "vs_nominal":
        if nominal_forcing is None:
            raise ValueError("mode 'vs_nominal' needs nominal_forcing")
        out: dict[tuple[str, str], float | None] = {}
        for (policy, forcing), value in grid.items():
            base = grid.get((policy, nominal_forcing))
            if value is None or base in (None, 0):
                out[(policy, forcing)] = None
            else:
                out[(policy, forcing)] = float(value) / float(base)
        return out
    if mode == "regret":
        benchmark = _best_by_forcing(grid, higher_is_better)
        out = {}
        for (policy, forcing), value in grid.items():
            reference = benchmark.get(forcing)
            if value is None or reference in (None, 0):
                out[(policy, forcing)] = None
            else:
                ratio = float(value) / float(reference)
                # For a cost indicator the benchmark is the SMALLEST value, so the ratio is
                # >= 1 and must be inverted to keep "1.0 = best" true in both directions.
                out[(policy, forcing)] = ratio if higher_is_better else (1.0 / ratio)
        return out
    raise ValueError(f"unknown normalisation mode {mode!r}")
