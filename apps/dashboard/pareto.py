"""Trade-off fronts: what the next kilogram of nitrogen actually costs in margin.

A scenario answers "under this ceiling, the margin is X". It does not answer "what does the
next unit cost", and that is the question a policy is argued over. Sweeping a ceiling by
epsilon-constraint and plotting the results gives the whole curve -- which is a different
object from `shadow_prices.py`. A dual is the slope AT a point, valid infinitesimally; the
front shows the kinks, the flat stretches and the cliffs a dual cannot see, and those are
usually where the decision sits.

WHAT DOMINATION MEANS HERE. A point is dominated when another achieves at least as much on
both axes and strictly more on one, in each axis's own direction (margin up, nitrogen down --
read from `comparison.INDICATOR_DIRECTION`, so this works for any pair of indicators). Only
the non-dominated points form the front; the rest are drawn but greyed, because a dominated
point in a sweep is informative -- it usually means that solve did not converge, not that the
trade-off doubled back.

Pure and Streamlit-free.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from apps.dashboard.comparison import INDICATOR_DIRECTION, INDICATOR_LABELS, indicator_value

# Runs of a sweep share a name prefix ending here: `pareto_azote__threshold=1544722`.
SWEEP_SEPARATOR = "__"


@dataclass(frozen=True)
class Point:
    """One solve of a sweep, placed on the two axes being traded off."""

    run: str
    label: str
    x: float
    y: float
    dominated: bool = False


def sweep_of(recap: dict, fallback_name: str = "") -> str:
    """Which front a run belongs to.

    Two readings, and the order matters. A run written by a PLAN carries `run_sweep` (and
    `run_policy`) in its recap, and a front traced under a policy is named
    `<policy>__<sweep>__<point>` -- so the name prefix identifies the policy, and grouping on
    it would pile every front of a policy into one meaningless curve. The coordinates say
    what the run IS.

    The name-prefix reading survives only for runs written before those fields existed, where
    a sweep was always traced against the reference config and the prefix WAS the sweep.
    """
    sweep = recap.get("run_sweep")
    if sweep:
        policy = recap.get("run_policy")
        forcing = recap.get("run_forcing")
        # A front under P8 and the same front under P8 x F9 are different curves; naming them
        # apart is what keeps them from being averaged into one.
        return SWEEP_SEPARATOR.join(part for part in (policy, forcing, sweep) if part)
    name = recap.get("run_name") or fallback_name
    return str(name).split(SWEEP_SEPARATOR, 1)[0]


def sweep_name(run_name: str) -> str:
    """The sweep a run belongs to, read from its name alone: everything before the matrix
    suffix. `pareto_azote__threshold=1544722` -> `pareto_azote`. Prefer `sweep_of`, which
    reads the recap's own coordinates when it has them."""
    return str(run_name).split(SWEEP_SEPARATOR, 1)[0]


def sweeps_in(recaps: dict[str, dict]) -> list[str]:
    """Sweep names present among {run folder -> recap}, in alphabetical order.
    A run whose name carries no matrix suffix is a sweep of one and is included."""
    return sorted({
        sweep_of(recap, folder)
        for folder, recap in recaps.items()
        if (recap.get("run_name") or "")
    })


def collect_points(
    recaps: dict[str, dict], sweep: str, x_indicator: str, y_indicator: str, side: str = "output"
) -> list[Point]:
    """Points of one sweep, sorted along x. Runs missing either value are skipped -- a run
    predating the recap block that holds an indicator cannot be placed on that axis."""
    points: list[Point] = []
    for folder, recap in recaps.items():
        name = recap.get("run_name") or folder
        if sweep_of(recap, folder) != sweep:
            continue
        x = indicator_value(recap, side, x_indicator)
        y = indicator_value(recap, side, y_indicator)
        if x is None or y is None:
            continue
        points.append(Point(run=folder, label=str(name), x=float(x), y=float(y)))
    return sorted(points, key=lambda p: p.x)


def _better(value: float, other: float, indicator: str) -> bool:
    """Is `value` strictly better than `other` on this indicator's own direction?"""
    if INDICATOR_DIRECTION.get(indicator) == "cost":
        return value < other
    return value > other


def _at_least_as_good(value: float, other: float, indicator: str) -> bool:
    if INDICATOR_DIRECTION.get(indicator) == "cost":
        return value <= other
    return value >= other


def mark_dominated(
    points: list[Point], x_indicator: str, y_indicator: str
) -> list[Point]:
    """Same points, with `dominated` set. A point is dominated when another is at least as
    good on both axes and strictly better on one."""
    marked = []
    for point in points:
        dominated = any(
            other is not point
            and _at_least_as_good(other.x, point.x, x_indicator)
            and _at_least_as_good(other.y, point.y, y_indicator)
            and (
                _better(other.x, point.x, x_indicator)
                or _better(other.y, point.y, y_indicator)
            )
            for other in points
        )
        marked.append(
            Point(point.run, point.label, point.x, point.y, dominated=dominated)
        )
    return marked


def marginal_rates(points: list[Point]) -> list[dict[str, float]]:
    """Slope between consecutive NON-DOMINATED points: what one unit of x costs in y.

    This is the number the front exists to produce -- "the last 100 000 kg of nitrogen cost
    2.3 M EUR of margin, i.e. 23 EUR/kg" -- and it is comparable with the shadow price of the
    same constraint, which is the local version of it. A large gap between the two means the
    dual is being read outside its neighbourhood of validity.
    """
    front = sorted([p for p in points if not p.dominated], key=lambda p: p.x)
    rates = []
    for previous, current in zip(front, front[1:]):
        span = current.x - previous.x
        if not span:
            continue
        rates.append({
            "from": previous.label,
            "to": current.label,
            "delta_x": span,
            "delta_y": current.y - previous.y,
            "rate": (current.y - previous.y) / span,
        })
    return rates


def build_front_figure(
    points: list[Point], x_indicator: str, y_indicator: str
) -> "plt.Figure":
    """The front: non-dominated points joined by a line, dominated ones greyed and unjoined."""
    fig, ax = plt.subplots(figsize=(8, 5))
    front = sorted([p for p in points if not p.dominated], key=lambda p: p.x)
    dominated = [p for p in points if p.dominated]

    if front:
        ax.plot([p.x for p in front], [p.y for p in front],
                marker="o", color="#1f77b4", linewidth=2, zorder=3, label="Front (non dominé)")
    if dominated:
        ax.scatter([p.x for p in dominated], [p.y for p in dominated],
                   color="0.7", marker="x", zorder=2, label="Dominé (solve suspect)")
    for point in points:
        ax.annotate(
            # The LAST segment is the swept value -- `rsplit`, not `split`: a front traced
            # under a policy carries the policy and forcing in front of the sweep name, and
            # splitting from the left would label every point with all of that.
            point.label.rsplit(SWEEP_SEPARATOR, 1)[-1],
            (point.x, point.y), fontsize=7, textcoords="offset points", xytext=(4, 4),
            color="0.35",
        )

    ax.set_xlabel(INDICATOR_LABELS.get(x_indicator, x_indicator))
    ax.set_ylabel(INDICATOR_LABELS.get(y_indicator, y_indicator))
    ax.grid(alpha=0.3)
    ax.set_axisbelow(True)
    if front or dominated:
        ax.legend(fontsize=8)
    fig.tight_layout()
    return fig
