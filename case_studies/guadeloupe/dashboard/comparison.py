"""Pure, Streamlit-free helpers for the comparison dashboard page. All the data logic
(dimension keys, cane color coding, pivoting, shared axis limits, indicator normalization)
lives here so it can be unit-tested without a browser; the page (pages/) only wires these
to widgets and matplotlib. Consumes the tidy csv/facts_<side>.csv tables written by
report.compute_facts_table."""

from __future__ import annotations

from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Measures available on the y-axis, in display order, with French labels.
MEASURE_LABELS: dict[str, str] = {
    "surface": "Surface (ha)",
    "production": "Production (t)",
    "revenue": "Revenu / produit brut (€)",
    "gross_margin": "Marge brute (€)",
    "subsidy": "Subvention (€)",
    "sales": "Ventes (€)",
    "labor_cost": "Coût main d'œuvre (€)",
    "labor_hours": "Heures de travail (h)",
    "etp": "Emploi (ETP)",
}

X_DIMENSION_LABELS: dict[str, str] = {
    "culture": "Culture",
    "subculture": "Sous-culture",
    "region": "Région",
    "island": "Île",
}

# Fixed, meaningful colors for the three real cane irrigation x harvest combos, so they read
# the same across every chart regardless of which series/regions are shown.
_CANE_COMBO_COLORS: dict[str, str] = {
    "Non irrigué · récolte semi-mécanisée": "#8c6d31",
    "Non irrigué · récolte mécanisée": "#e7ba52",
    "Irrigué · récolte mécanisée": "#31a354",
}

# Sugarcane cultures whose sub-crops encode an irrigation x harvest combo we color by
# (region is deliberately ignored in that coloring -- see the design).
CANE_CULTURES = {"CS", "CF"}

# Combo token (last "_"-separated token of a cane code) -> human label. Only three combos
# exist in the data: irrigated is always mechanized (no "irrigated + semi-mechanized").
_CANE_COMBO_LABELS = {
    "NISM": "Non irrigué · récolte semi-mécanisée",
    "NIM": "Non irrigué · récolte mécanisée",
    "IM": "Irrigué · récolte mécanisée",
}

X_DIMENSIONS = ("culture", "subculture", "region", "island")


def culture_of(crop_code: str) -> str:
    """Base culture of a fine crop code: the prefix before the first '_'
    ('CS_BT_NISM' -> 'CS', 'MA_PLBIO' -> 'MA', 'ME' -> 'ME')."""
    return str(crop_code).split("_", 1)[0]


def cane_combo_of(crop_code: str) -> str | None:
    """Irrigation x harvest combo label for a cane sub-crop, or None if the code is not a
    recognized cane combo. Parsed from the last token ('CS_NGT_IM' -> 'Irrigué ...')."""
    if culture_of(crop_code) not in CANE_CULTURES:
        return None
    return _CANE_COMBO_LABELS.get(str(crop_code).rsplit("_", 1)[-1])


def x_key(crop: str, region: object, island: object, x_dim: str) -> object:
    """The x-axis category a fact row falls into for the chosen dimension."""
    if x_dim == "culture":
        return culture_of(crop)
    if x_dim == "subculture":
        return crop
    if x_dim == "region":
        return region
    if x_dim == "island":
        return island
    raise ValueError(f"unknown x dimension: {x_dim}")


def stack_key(crop: str, region: object, island: object, stack_by: str | None) -> object:
    """The stacking (color) category a fact row falls into. 'subculture' colors cane by its
    irrigation x harvest combo and every other crop by its own code; None/'none' collapses
    to a single stack."""
    if stack_by in (None, "none"):
        return "total"
    if stack_by == "subculture":
        combo = cane_combo_of(crop)
        return combo if combo is not None else crop
    if stack_by == "culture":
        return culture_of(crop)
    if stack_by == "region":
        return region
    if stack_by == "island":
        return island
    raise ValueError(f"unknown stack dimension: {stack_by}")


def pivot_measure(
    facts: pd.DataFrame, x_dim: str, measure: str, stack_by: str | None
) -> pd.DataFrame:
    """Pivot one series' facts into an (x category) x (stack category) table of summed
    `measure`. Row = x-axis bar, column = a colored stratum within that bar."""
    keyed = pd.DataFrame(
        {
            "_x": [
                x_key(c, r, i, x_dim)
                for c, r, i in zip(facts["crop"], facts["region"], facts["island"])
            ],
            "_stack": [
                stack_key(c, r, i, stack_by)
                for c, r, i in zip(facts["crop"], facts["region"], facts["island"])
            ],
            "_value": facts[measure].to_numpy(),
        }
    )
    return keyed.pivot_table(
        index="_x", columns="_stack", values="_value", aggfunc="sum", fill_value=0.0
    )


def shared_bar_ceiling(pivots: list[pd.DataFrame]) -> float:
    """Largest total bar height across every series (sum of a bar's strata), so all series
    can share one fixed y-axis. 0.0 if there is nothing to plot."""
    tops = [pivot.sum(axis=1).max() for pivot in pivots if not pivot.empty]
    return float(max(tops)) if tops else 0.0


def positive_floor(pivots: list[pd.DataFrame]) -> float:
    """Smallest strictly-positive stratum value across all series -- a sensible lower bound
    for a log axis (which cannot show the many exact-zero strata). 1.0 if none is positive."""
    positives = [
        float(pivot.to_numpy()[pivot.to_numpy() > 0].min())
        for pivot in pivots
        if not pivot.empty and (pivot.to_numpy() > 0).any()
    ]
    return min(positives) if positives else 1.0


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalize each column to 0..1 across rows (for parallel-coordinates axes).
    A constant column maps to 0.5 (its scenarios are tied on that indicator)."""
    out = frame.astype(float).copy()
    for column in out.columns:
        col = out[column]
        span = col.max() - col.min()
        out[column] = 0.5 if span == 0 else (col - col.min()) / span
    return out


def series_label(run_name: str, side: str, year: object, scenario: object) -> str:
    """Stable, human label for a (run, side) series in legends and pickers."""
    side_fr = {"output": "sortie", "input": "entrée"}.get(side, side)
    return f"{run_name} · {side_fr} ({year}/{scenario})"


def _stratum_colors(strata: list[object]) -> dict[object, object]:
    """Stable color per stratum: cane combos keep their fixed colors, the rest are taken
    deterministically from tab20."""
    palette = plt.get_cmap("tab20").colors
    colors: dict[object, object] = {}
    generic = 0
    for stratum in strata:
        if stratum in _CANE_COMBO_COLORS:
            colors[stratum] = _CANE_COMBO_COLORS[stratum]
        else:
            colors[stratum] = palette[generic % len(palette)]
            generic += 1
    return colors


def build_grouped_bar_figure(
    series_pivots: list[tuple[str, pd.DataFrame]],
    *,
    measure_label: str,
    x_axis_label: str,
    stacked: bool,
    log: bool,
    ceiling: float,
    floor: float,
    format_x: Callable[[object], str] = str,
) -> "plt.Figure":
    """Grouped bars: one bar per series within each x category. Unstacked -> one color per
    series (legend = series). Stacked -> each bar is split into strata colored consistently
    (legend = strata; the bar order within a group is the series order passed in). The y-axis
    uses the shared, fixed `ceiling` so every series reads on the same scale; log applies only
    when not stacked (a log axis misrepresents stacked sums), with `floor` as its lower bound."""
    categories = sorted(set().union(*[p.index for _, p in series_pivots])) if series_pivots else []
    strata = sorted(set().union(*[p.columns for _, p in series_pivots])) if series_pivots else []
    n = max(len(series_pivots), 1)
    x = np.arange(len(categories))
    width = 0.8 / n
    effective_log = log and not stacked

    fig, ax = plt.subplots(figsize=(max(9, len(categories) * 0.55 * n + 2), 6))
    series_colors = plt.get_cmap("tab10").colors
    stratum_colors = _stratum_colors(strata)

    for s_idx, (label, pivot) in enumerate(series_pivots):
        aligned = pivot.reindex(index=categories, columns=strata, fill_value=0.0)
        offset = (s_idx - (n - 1) / 2) * width
        if not stacked:
            # single "total" stratum -> one color per series
            values = aligned.sum(axis=1).to_numpy()
            ax.bar(x + offset, values, width, color=series_colors[s_idx % len(series_colors)],
                   label=label)
        else:
            bottoms = np.zeros(len(categories))
            for stratum in strata:
                values = aligned[stratum].to_numpy()
                ax.bar(x + offset, values, width, bottom=bottoms,
                       color=stratum_colors[stratum],
                       label=str(stratum) if s_idx == 0 else None,
                       edgecolor="white", linewidth=0.3)
                bottoms = bottoms + values

    ax.set_xticks(x)
    ax.set_xticklabels([format_x(c) for c in categories], rotation=45, ha="right")
    ax.set_ylabel(measure_label)
    ax.set_xlabel(x_axis_label)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    if effective_log:
        ax.set_yscale("log")
        ax.set_ylim(floor * 0.9 if floor > 0 else None, ceiling * 1.15 if ceiling > 0 else None)
    else:
        ax.set_ylim(0, ceiling * 1.05 if ceiling > 0 else None)
    if strata != ["total"] or not stacked:
        ax.legend(fontsize=8, ncol=2, loc="upper right")
    fig.tight_layout()
    return fig


def build_parallel_coordinates_figure(
    normalized: pd.DataFrame, raw: pd.DataFrame, indicator_labels: dict[str, str]
) -> "plt.Figure":
    """Parallel-coordinates: one vertical axis per indicator (normalized 0..1 across the
    shown series), one broken line per series. Each axis is annotated with its real min/max
    so the normalization stays legible."""
    indicators = list(normalized.columns)
    x = np.arange(len(indicators))
    fig, ax = plt.subplots(figsize=(max(8, len(indicators) * 1.6), 6))
    colors = plt.get_cmap("tab10").colors

    for axis_x in x:
        ax.axvline(axis_x, color="0.8", linewidth=1, zorder=0)
    for s_idx, series in enumerate(normalized.index):
        ax.plot(x, normalized.loc[series].to_numpy(), marker="o",
                color=colors[s_idx % len(colors)], label=str(series))
    for axis_x, indicator in zip(x, indicators):
        ax.text(axis_x, 1.02, f"{raw[indicator].max():,.2f}", ha="center", va="bottom", fontsize=7)
        ax.text(axis_x, -0.02, f"{raw[indicator].min():,.2f}", ha="center", va="top", fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels([indicator_labels.get(i, i) for i in indicators], rotation=30, ha="right")
    ax.set_yticks([0, 0.5, 1])
    ax.set_ylim(-0.08, 1.08)
    ax.set_ylabel("Valeur normalisée (0–1 sur les séries affichées)")
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    return fig
