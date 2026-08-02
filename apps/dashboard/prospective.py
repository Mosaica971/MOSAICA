"""Pure, Streamlit-free helpers for the prospective (policy x forcing) dashboard page.

Turns a list of run folders into a policy x forcing grid, then into the three figures that
make such a grid readable: the heatmap, the performance-robustness scatter and the per-policy
tornado. The robustness arithmetic itself lives in core/reporting/robustness.py; this module
only assembles the grid and draws it.

Naming: a run belongs to the grid when its recap carries `run_policy` / `run_forcing` (set by
scripts/run_scenarios.py). Runs written before those fields fall back to splitting `run_name`
on the "__" separator that compose_runs uses, so an existing batch stays readable.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core.reporting.robustness import PolicyRobustness

_SEPARATOR = "__"


def grid_coordinates(recap: dict, fallback_name: str) -> tuple[str, str] | None:
    """(policy, forcing) of a run, or None when it is not part of a grid.

    Prefers the explicit recap fields; falls back to the name convention only when they are
    absent, and only when the name splits into exactly two parts -- guessing on a name that
    happens to contain "__" would invent a grid that was never run.
    """
    policy = recap.get("run_policy")
    forcing = recap.get("run_forcing")
    if policy and forcing:
        return str(policy), str(forcing)
    name = recap.get("run_name") or fallback_name
    parts = str(name).split(_SEPARATOR)
    if len(parts) == 2 and all(parts):
        return parts[0], parts[1]
    return None


def build_grid(
    entries: list[dict], indicator_of: "callable"
) -> dict[tuple[str, str], float | None]:
    """{(policy, forcing): value} from run entries [{policy, forcing, recap, ...}].

    A run whose indicator is missing, or which did not solve, contributes None -- which the
    robustness module treats as the worst possible outcome rather than dropping it. That is
    the whole point: a policy with no solution under a forcing has failed, and silently
    omitting the cell would flatter it.
    """
    grid: dict[tuple[str, str], float | None] = {}
    for entry in entries:
        key = (entry["policy"], entry["forcing"])
        if not _solved(entry.get("recap") or {}):
            grid[key] = None
            continue
        grid[key] = indicator_of(entry)
    return grid


_UNSOLVED = {"infeasible", "infeasibleorunbounded", "error", "nosolution"}


def _solved(recap: dict) -> bool:
    condition = str(recap.get("termination_condition", "")).strip().lower()
    return condition not in _UNSOLVED


def grid_frame(
    grid: dict[tuple[str, str], float | None],
    policies: list[str],
    forcings: list[str],
) -> pd.DataFrame:
    """The grid as a policies x forcings DataFrame, in the given order, NaN where missing."""
    return pd.DataFrame(
        [[_as_float(grid.get((p, f))) for f in forcings] for p in policies],
        index=policies,
        columns=forcings,
    )


def _as_float(value) -> float:
    return float("nan") if value is None else float(value)


_ROBUSTNESS_COLUMNS = (
    "Nominal", "Pire cas", "Médiane", "Meilleur", "Rétention", "Instabilité (CV)",
    "Regret max", "Viabilité", "Forçages", "Infaisables",
)


def robustness_frame(summaries: list[PolicyRobustness]) -> pd.DataFrame:
    """The robustness table, one row per policy, with French column names for display.

    An empty list yields an empty frame carrying the right columns rather than raising:
    `set_index` on a frame with no rows has no "Politique" column to find, and a table with
    nothing in it is a legitimate state (every policy filtered out of the grid).
    """
    if not summaries:
        return pd.DataFrame(columns=list(_ROBUSTNESS_COLUMNS), index=pd.Index([], name="Politique"))
    return pd.DataFrame(
        [
            {
                "Politique": s.policy,
                "Nominal": s.nominal,
                "Pire cas": s.worst,
                "Médiane": s.median,
                "Meilleur": s.best,
                "Rétention": s.retention,
                "Instabilité (CV)": s.coefficient_of_variation,
                "Regret max": s.max_regret,
                "Viabilité": s.viability,
                "Forçages": s.forcings_evaluated,
                "Infaisables": s.forcings_infeasible,
            }
            for s in summaries
        ]
    ).set_index("Politique")


def build_heatmap_figure(
    frame: pd.DataFrame,
    *,
    title: str,
    colorbar_label: str,
    higher_is_better: bool = True,
    centre: float | None = None,
    value_format: str = "{:,.0f}",
) -> "plt.Figure":
    """Policy x forcing heatmap, annotated with each cell's value.

    `centre`, when given, anchors a diverging colormap on that value -- the reading that
    matters for a normalised grid, where 1.0 means "as good as the reference" and the eye
    should immediately separate above from below. Absolute grids get a sequential map.
    Missing cells (no solution) are drawn hatched and labelled, never left blank: an empty
    square reads as "not run" when it actually means "this policy broke".
    """
    policies = list(frame.index)
    forcings = list(frame.columns)
    values = frame.to_numpy(dtype=float)

    fig, ax = plt.subplots(
        figsize=(max(7.0, 1.15 * len(forcings) + 3), max(3.5, 0.55 * len(policies) + 2))
    )
    cmap = plt.get_cmap("RdYlGn" if higher_is_better else "RdYlGn_r").with_extremes(
        bad="#d9d9d9"
    )

    masked = np.ma.masked_invalid(values)
    if centre is not None and masked.count():
        spread = max(
            abs(float(masked.max()) - centre), abs(centre - float(masked.min())), 1e-9
        )
        image = ax.imshow(masked, cmap=cmap, aspect="auto",
                          vmin=centre - spread, vmax=centre + spread)
    else:
        image = ax.imshow(masked, cmap=cmap, aspect="auto")

    ax.set_xticks(range(len(forcings)))
    ax.set_xticklabels(forcings, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(policies)))
    ax.set_yticklabels(policies, fontsize=8)
    ax.set_title(title, fontsize=10)

    for i in range(len(policies)):
        for j in range(len(forcings)):
            value = values[i, j]
            if np.isnan(value):
                ax.add_patch(
                    plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                  hatch="///", edgecolor="#888888", linewidth=0)
                )
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=7, color="#444444")
            else:
                ax.text(j, i, value_format.format(value), ha="center", va="center",
                        fontsize=7, color="#111111")

    fig.colorbar(image, ax=ax, label=colorbar_label, shrink=0.85)
    fig.tight_layout()
    return fig


def build_performance_robustness_figure(
    summaries: list[PolicyRobustness],
    *,
    performance_label: str,
    colors: "dict[str, object] | None" = None,
) -> "plt.Figure":
    """Nominal performance (x) against worst-case retention (y).

    The single most informative view of a policy x forcing design, because it separates the
    two things a scenario comparison keeps conflating: how good a policy is when nothing goes
    wrong, and how much of that it keeps when something does. The median of each axis splits
    the plane into four readable quadrants -- notably "performant but fragile", which is
    where an intensification strategy is expected to land.

    A policy that is infeasible under some forcing has no retention; it is drawn on the
    baseline with a marked symbol rather than dropped.
    """
    fig, ax = plt.subplots(figsize=(8, 5.5))
    default = plt.get_cmap("tab10").colors
    overrides = colors or {}

    plotted = [s for s in summaries if s.nominal is not None]
    if not plotted:
        ax.text(0.5, 0.5, "Aucune politique évaluable", ha="center", va="center")
        return fig

    xs = [s.nominal for s in plotted]
    ys = [s.retention if s.retention is not None else 0.0 for s in plotted]
    x_split, y_split = float(np.median(xs)), float(np.median([y for y in ys if y > 0] or [0.0]))
    ax.axvline(x_split, color="0.85", linewidth=1, zorder=0)
    ax.axhline(y_split, color="0.85", linewidth=1, zorder=0)

    for idx, summary in enumerate(plotted):
        color = overrides.get(summary.policy) or default[idx % len(default)]
        broken = summary.retention is None
        ax.scatter(
            summary.nominal, ys[idx], s=150 if broken else 110, color=color, zorder=3,
            marker="X" if broken else "o",
            edgecolor="black" if broken else "none", linewidth=1.2,
        )
        ax.annotate(
            summary.policy + (" (infaisable)" if broken else ""),
            (summary.nominal, ys[idx]), textcoords="offset points", xytext=(7, 5), fontsize=8,
        )

    ax.set_xlabel(f"Performance nominale — {performance_label}")
    ax.set_ylabel("Rétention au pire cas (pire / nominal)")
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    _annotate_quadrants(ax, x_split, y_split)
    fig.tight_layout()
    return fig


def _annotate_quadrants(ax, x_split: float, y_split: float) -> None:
    x_low, x_high = ax.get_xlim()
    y_low, y_high = ax.get_ylim()
    labels = [
        (x_low, y_high, "modeste\nmais robuste", "left", "top"),
        (x_high, y_high, "performant\net robuste", "right", "top"),
        (x_low, y_low, "à éviter", "left", "bottom"),
        (x_high, y_low, "performant\nmais fragile", "right", "bottom"),
    ]
    for x, y, text, ha, va in labels:
        ax.text(x, y, text, ha=ha, va=va, fontsize=7, color="0.5", style="italic")


def build_tornado_figure(
    frame: pd.DataFrame,
    policy: str,
    nominal_forcing: str,
    *,
    value_label: str,
    higher_is_better: bool = True,
) -> "plt.Figure":
    """Each forcing's deviation from the policy's own unforced value, sorted by magnitude.

    Reads as one sentence: which shock hurts this policy most. Bars are coloured by whether
    the deviation is favourable or adverse in the indicator's own direction, so a cost
    indicator does not read backwards.
    """
    row = frame.loc[policy]
    if nominal_forcing not in row.index or not np.isfinite(row[nominal_forcing]):
        fig, ax = plt.subplots(figsize=(7, 2))
        ax.text(0.5, 0.5, f"Pas de valeur nominale ({nominal_forcing})",
                ha="center", va="center")
        return fig

    base = float(row[nominal_forcing])
    deltas = {f: float(row[f]) - base for f in row.index if f != nominal_forcing}
    finite = {f: d for f, d in deltas.items() if np.isfinite(d)}
    broken = [f for f, d in deltas.items() if not np.isfinite(d)]
    ordered = sorted(finite.items(), key=lambda kv: abs(kv[1]))

    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.36 * (len(ordered) + len(broken)) + 1.5)))
    labels = [f for f, _ in ordered]
    values = [d for _, d in ordered]
    favourable = [(d > 0) == higher_is_better for d in values]
    ax.barh(range(len(values)), values,
            color=["#4daf4a" if ok else "#e41a1c" for ok in favourable])

    # Infeasible forcings have no numeric deviation but are the most important outcome, so
    # they get their own rows at the top rather than being silently absent.
    for offset, forcing in enumerate(broken):
        y = len(values) + offset
        ax.text(0, y, "  infaisable", va="center", fontsize=8, color="#e41a1c", weight="bold")
        labels.append(forcing)

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel(f"Écart au nominal ({nominal_forcing}) — {value_label}")
    ax.set_title(policy, fontsize=10)
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig
