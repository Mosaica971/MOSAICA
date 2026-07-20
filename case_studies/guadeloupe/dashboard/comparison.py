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
import matplotlib.ticker
import numpy as np
import pandas as pd

from case_studies.guadeloupe.crop_labels import label_for

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

# Region / island codes -> human names (GAMS source: DESCRIPTION_SETS.txt). The facts tables
# store the raw numeric codes; these turn "1, 2, ..." into readable axis/legend labels.
REGION_LABELS: dict[str, str] = {
    "1": "CGT · Centre Grande-Terre",
    "2": "EGT · Est Grande-Terre",
    "3": "NGT · Nord Grande-Terre",
    "4": "NBT · Nord Basse-Terre",
    "5": "SEBT · Sud-Est Basse-Terre",
    "6": "SOBT · Sud-Ouest Basse-Terre",
    "7": "MG · Marie-Galante",
}
ISLAND_LABELS: dict[str, str] = {
    "1": "Basse-Terre",
    "2": "Grande-Terre",
    "3": "Marie-Galante",
}
# Full universe of region / island codes, so an exhaustive axis can include codes absent from
# a given allocation (as zero-height bars).
REGION_CODES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
ISLAND_CODES: tuple[int, ...] = (1, 2, 3)

# Stable per-scenario colors (matplotlib tab10, as hex) used as the default value of the
# per-scenario color pickers and as the figure fallback when no override is supplied.
SERIES_PALETTE_HEX: tuple[str, ...] = (
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
)


def _code_key(value: object) -> str:
    """Normalize a region/island cell (int, float, numpy int, or str) to its str code key."""
    try:
        return str(int(float(value)))  # 4 / 4.0 / np.int64(4) / "4" -> "4"
    except (TypeError, ValueError):
        return str(value)


def label_region(value: object) -> str:
    return REGION_LABELS.get(_code_key(value), str(value))


def label_island(value: object) -> str:
    return ISLAND_LABELS.get(_code_key(value), str(value))


def format_dim_value(dim: str, value: object) -> str:
    """Human label for a value on a given dimension: French crop names for culture/subculture
    (falls back to the raw code, so cane-combo strata labels pass through untouched), region /
    island names for those, str otherwise."""
    if dim in ("culture", "subculture"):
        return label_for(str(value))
    if dim == "region":
        return label_region(value)
    if dim == "island":
        return label_island(value)
    return str(value)


def ordered_categories(
    series_pivots: list[tuple[str, pd.DataFrame]],
    universe: "list | tuple | None",
    include_zeros: bool,
    sort_by_value: bool,
) -> list:
    """Final ordered x-axis category list across all series. With `include_zeros` and a
    `universe`, every universe category is kept (zero bars included); otherwise only categories
    with a non-zero total appear. `sort_by_value` ranks by descending total (ties by label),
    else lexicographically."""
    totals: dict[object, float] = {}
    for _, pivot in series_pivots:
        for cat, value in pivot.sum(axis=1).items():
            totals[cat] = totals.get(cat, 0.0) + float(value)
    if include_zeros and universe:
        cats = list(dict.fromkeys([*universe, *totals]))
    else:
        cats = [cat for cat, total in totals.items() if total != 0.0]
    if sort_by_value:
        return sorted(cats, key=lambda c: (-totals.get(c, 0.0), str(c)))
    return sorted(cats, key=str)


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


# Direction of each scalar indicator for the composite score: "benefit" (higher is
# better) or "cost" (lower is better -> inverted before averaging). Anything not listed
# defaults to "benefit".
INDICATOR_DIRECTION: dict[str, str] = {
    "total_production_tonnes": "benefit",
    "total_revenue": "benefit",
    "total_gross_margin": "benefit",
    "total_net_revenue": "benefit",
    "total_etp": "benefit",
    "total_subsidy": "cost",
    "total_labor_cost": "cost",
    "gini_revenue_by_farm": "cost",
    "total_ges": "cost",
    "total_ift": "cost",
    "total_azote": "cost",
    "surface_cld": "cost",
    "total_water_need_m3": "cost",
    "soil_carbon_balance": "benefit",
    "soil_carbon_mineralization": "cost",
}


def compute_composite_scores(raw: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Weighted composite score in [0,1] per series (scenario), one row of `raw` each.

    Each column is min-max normalized across the rows so 1 = best of the compared set;
    "cost" indicators (INDICATOR_DIRECTION) are inverted so lower raw = higher score. A
    constant column (or a single scenario) scores 0.5 (nothing to rank). The score is the
    weighted mean over columns that are present in `raw` and carry a strictly positive
    weight; with no such column every series scores 0.5."""
    usable = [c for c in raw.columns if weights.get(c, 0.0) > 0.0]
    if not usable:
        return pd.Series(0.5, index=raw.index)

    normalized = pd.DataFrame(index=raw.index)
    for col in usable:
        values = raw[col].astype(float)
        lo, hi = values.min(), values.max()
        if hi == lo:
            normalized[col] = 0.5
            continue
        benefit = (values - lo) / (hi - lo)
        normalized[col] = 1.0 - benefit if INDICATOR_DIRECTION.get(col) == "cost" else benefit

    w = pd.Series({c: weights[c] for c in usable}, dtype=float)
    return (normalized[usable] * w).sum(axis=1) / w.sum()


def autonomy_ratios_frame(
    autonomy_by_series: dict[str, dict], variant: str
) -> pd.DataFrame:
    """Nutrient (rows) x series (cols) self-sufficiency ratios for one variant
    ('crop_only' or 'with_fishing'), from each series' recap food_autonomy[side] dict.
    Backs the dedicated autonomy panel's grouped bars."""
    return pd.DataFrame(
        {label: auto.get(variant, {}) for label, auto in autonomy_by_series.items()}
    )


def series_label(display_name: str, side: str) -> str:
    """Base label for a (run, side) series in legends and pickers: the run's display
    name (its recap `run_name`, or folder name) plus the side. Not guaranteed unique --
    two runs sharing a run_name collide; series_labels() disambiguates a full list."""
    side_fr = {"output": "sortie", "input": "entrée"}.get(side, side)
    return f"{display_name} · {side_fr}"


def series_labels(rows: list[tuple[str, str]]) -> list[str]:
    """Disambiguated series labels, aligned with `rows` = [(base_label, folder_name), ...].
    A base_label shared by several rows (two runs with the same run_name and side) gets
    ` (folder_name)` appended so dashboard series keys stay unique; unique labels pass
    through untouched. Two series of one run never collide (their side differs)."""
    counts: dict[str, int] = {}
    for base_label, _ in rows:
        counts[base_label] = counts.get(base_label, 0) + 1
    return [
        f"{base_label} ({folder})" if counts[base_label] > 1 else base_label
        for base_label, folder in rows
    ]


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
    categories: "list | None" = None,
    horizontal: bool = False,
    relative: bool = False,
    series_colors: "dict[str, object] | None" = None,
    format_x: Callable[[object], str] = str,
    format_stack: Callable[[object], str] = str,
) -> "plt.Figure":
    """Grouped bars: one bar per series within each x category. Unstacked -> one color per
    series (legend = series, colored via `series_colors` when given). Stacked -> each bar is
    split into strata colored consistently (legend = strata, relabeled by `format_stack`; the
    bar order within a group is the series order passed in).

    `categories`, when given, fixes the x-axis order and set (pass the full universe to keep
    zero-height bars). The value axis uses the shared, fixed `ceiling` so every series reads on
    the same scale; `relative=True` rescales each stacked bar to 0-100% instead. `horizontal`
    lays the bars out as `barh` (readable for the ~70 sub-culture codes). `log` applies only to
    plain (non-stacked, non-relative) bars, with `floor` as its lower bound."""
    if categories is None:
        categories = sorted(set().union(*[p.index for _, p in series_pivots])) if series_pivots else []
    strata = sorted(set().union(*[p.columns for _, p in series_pivots])) if series_pivots else []
    n = max(len(series_pivots), 1)
    pos = np.arange(len(categories))
    width = 0.8 / n
    effective_log = log and not stacked and not relative
    value_label = "Part relative (%)" if relative else measure_label

    if horizontal:
        fig, ax = plt.subplots(figsize=(10, max(4, len(categories) * 0.32 * n + 1.5)))
    else:
        fig, ax = plt.subplots(figsize=(max(9, len(categories) * 0.55 * n + 2), 6))
    default_colors = plt.get_cmap("tab10").colors
    stratum_colors = _stratum_colors(strata)
    overrides = series_colors or {}

    def _draw(center, length, base, **kwargs):
        if horizontal:
            ax.barh(center, length, height=width, left=base, **kwargs)
        else:
            ax.bar(center, length, width, bottom=base, **kwargs)

    for s_idx, (label, pivot) in enumerate(series_pivots):
        aligned = pivot.reindex(index=categories, columns=strata, fill_value=0.0)
        if relative and stacked:
            totals = aligned.sum(axis=1).replace(0.0, np.nan)
            aligned = aligned.div(totals, axis=0).fillna(0.0) * 100.0
        offset = (s_idx - (n - 1) / 2) * width
        if not stacked:
            values = aligned.sum(axis=1).to_numpy()
            color = overrides.get(label) or default_colors[s_idx % len(default_colors)]
            _draw(pos + offset, values, 0, color=color, label=label)
        else:
            bottoms = np.zeros(len(categories))
            for stratum in strata:
                values = aligned[stratum].to_numpy()
                _draw(pos + offset, values, bottoms, color=stratum_colors[stratum],
                      label=format_stack(stratum) if s_idx == 0 else None,
                      edgecolor="white", linewidth=0.3)
                bottoms = bottoms + values

    tick_labels = [format_x(c) for c in categories]
    if horizontal:
        ax.set_yticks(pos)
        ax.set_yticklabels(tick_labels)
        ax.invert_yaxis()  # first (largest) category on top
        ax.set_xlabel(value_label)
        ax.set_ylabel(x_axis_label)
        ax.grid(axis="x", alpha=0.3)
    else:
        ax.set_xticks(pos)
        ax.set_xticklabels(tick_labels, rotation=45, ha="right")
        ax.set_ylabel(value_label)
        ax.set_xlabel(x_axis_label)
        ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)

    value_axis = ax.set_xlim if horizontal else ax.set_ylim
    if relative:
        value_axis(0, 100)
    elif effective_log:
        (ax.set_xscale if horizontal else ax.set_yscale)("log")
        value_axis(floor * 0.9 if floor > 0 else None, ceiling * 1.15 if ceiling > 0 else None)
    else:
        value_axis(0, ceiling * 1.05 if ceiling > 0 else None)

    if strata != ["total"] or not stacked:
        ax.legend(fontsize=8, ncol=2, loc="best")
    fig.tight_layout()
    return fig


def _compact_tick(value: float, _pos: object = None) -> str:
    """Short tick label that reads for both euros (M/k) and small ratios (Gini)."""
    magnitude = abs(value)
    if magnitude >= 1e6:
        return f"{value / 1e6:.1f}M"
    if magnitude >= 1e3:
        return f"{value / 1e3:.0f}k"
    if magnitude >= 10:
        return f"{value:.0f}"
    return f"{value:.2f}"


def _axis_range(values: "np.ndarray") -> tuple[float, float]:
    """Native (min, max) for one indicator's axis, padded; constant columns get a small span."""
    finite = values[np.isfinite(values)]
    low, high = float(finite.min()), float(finite.max())
    if low == high:
        pad = abs(low) * 0.05 or 1.0
        return low - pad, high + pad
    margin = (high - low) * 0.05
    return low - margin, high + margin


def build_indicator_parallel_axes_figure(
    raw: pd.DataFrame,
    indicator_labels: dict[str, str],
    series_colors: "dict[str, object] | None" = None,
) -> "plt.Figure":
    """Parallel coordinates with independent, native-scale axes: one vertical axis per indicator
    (each labelled in its own real units -- no cross-indicator normalization), one broken line
    per scenario crossing every axis. `raw` is indexed by series (scenario), one column per
    indicator; `series_colors` overrides the per-scenario line color."""
    indicators = list(raw.columns)
    series = list(raw.index)
    n = max(len(indicators), 1)
    ranges = {ind: _axis_range(raw[ind].to_numpy(dtype=float)) for ind in indicators}

    def to_unit(ind: str, value: float) -> float:
        low, high = ranges[ind]
        return (value - low) / (high - low)

    fig, host = plt.subplots(figsize=(max(6.0, n * 2.4), 5.5))
    x = np.arange(n)
    default_colors = plt.get_cmap("tab10").colors
    overrides = series_colors or {}

    for axis_x in x:
        host.axvline(axis_x, color="0.85", linewidth=1, zorder=0)
    for s_idx, s in enumerate(series):
        ys = [to_unit(ind, float(raw.loc[s, ind])) for ind in indicators]
        color = overrides.get(s) or default_colors[s_idx % len(default_colors)]
        host.plot(x, ys, marker="o", color=color, linewidth=2, label=str(s), zorder=2)

    host.set_xlim(-0.3, n - 0.7)
    host.set_ylim(0, 1)
    host.set_xticks(x)
    host.set_xticklabels([indicator_labels.get(i, i) for i in indicators], fontsize=9)
    host.get_yaxis().set_visible(False)
    for spine in ("left", "right", "top"):
        host.spines[spine].set_visible(False)

    # A twin y-axis per indicator, its spine anchored at the indicator's x, showing native ticks.
    # The leftmost axis puts its ticks/labels on the left (outside the lines) so they don't
    # overlap the plot; every other axis labels to the right of its line.
    for i, ind in enumerate(indicators):
        axis = host.twinx()
        axis.set_ylim(*ranges[ind])
        side = "left" if i == 0 else "right"
        other = "right" if i == 0 else "left"
        axis.spines[side].set_position(("data", x[i]))
        axis.yaxis.set_ticks_position(side)
        axis.yaxis.set_label_position(side)
        axis.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(6))
        axis.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_compact_tick))
        for spine in (other, "top", "bottom"):
            axis.spines[spine].set_visible(False)
        axis.tick_params(labelsize=7)

    host.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.04, 1))
    fig.tight_layout()
    return fig
