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

from case_studies.guadeloupe.domain.crop_labels import label_for

# Region / island codes -> human names, and the labelling functions themselves. All defined
# in domain/zones.py because reporting/ needs them too and reporting/ must not import
# dashboard/; re-exported here under the historical names this module's callers use
# (pages/2_Comparison.py). `label_region` / `label_island` are aliases of the domain
# functions rather than second implementations -- the two used to diverge on how they
# normalised a code, which is exactly the kind of duplication that produces two different
# labels for the same region depending on which one a page happened to call.
from case_studies.guadeloupe.domain.zones import (  # noqa: F401
    ISLAND_CODES,
    ISLAND_LABELS,
    REGION_CODES,
    REGION_LABELS,
    island_label as label_island,
    region_label as label_region,
)

# Measures available on the y-axis, in display order, with their labels.
MEASURE_LABELS: dict[str, str] = {
    "surface": "Area (ha)",
    "production": "Production (t)",
    "revenue": "Revenue / gross product (€)",
    "gross_margin": "Gross margin (€)",
    "subsidy": "Subsidy (€)",
    "sales": "Sales (€)",
    "labor_cost": "Labour cost (€)",
    "labor_hours": "Labour hours (h)",
    "fte": "Employment (FTE)",
}

X_DIMENSION_LABELS: dict[str, str] = {
    "culture": "Crop",
    "subculture": "Sub-crop",
    "region": "Region",
    "island": "Island",
}

# How the two sides of a run are named in series labels.
SIDE_LABELS: dict[str, str] = {"output": "output", "input": "input"}

# Fixed, meaningful colors for the three real cane irrigation x harvest combos, so they read
# the same across every chart regardless of which series/regions are shown.
_CANE_COMBO_COLORS: dict[str, str] = {
    "Rain-fed · semi-mechanised harvest": "#8c6d31",
    "Rain-fed · mechanised harvest": "#e7ba52",
    "Irrigated · mechanised harvest": "#31a354",
}

# Sugarcane cultures whose sub-crops encode an irrigation x harvest combo we color by
# (region is deliberately ignored in that coloring -- see the design).
CANE_CULTURES = {"CS", "CF"}

# Combo token (last "_"-separated token of a cane code) -> human label. Only three combos
# exist in the data: irrigated is always mechanized (no "irrigated + semi-mechanized").
_CANE_COMBO_LABELS = {
    "NISM": "Rain-fed · semi-mechanised harvest",
    "NIM": "Rain-fed · mechanised harvest",
    "IM": "Irrigated · mechanised harvest",
}

X_DIMENSIONS = ("culture", "subculture", "region", "island")

# Stable per-scenario colors (matplotlib tab10, as hex) used as the default value of the
# per-scenario color pickers and as the figure fallback when no override is supplied.
SERIES_PALETTE_HEX: tuple[str, ...] = (
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
)


def format_dim_value(dim: str, value: object) -> str:
    """Human label for a value on a given dimension: crop names for culture/subculture
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
    recognized cane combo. Parsed from the last token ('CS_NGT_IM' -> 'Irrigated ...')."""
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
    "total_fte": "benefit",
    "total_subsidy": "cost",
    "total_labor_cost": "cost",
    "gini_revenue_by_farm": "cost",
    "total_ghg": "cost",
    "total_tfi": "cost",
    "total_nitrogen": "cost",
    "chlordecone_risk_area": "cost",
    "total_water_need_m3": "cost",
    "soil_carbon_balance": "benefit",
    "soil_carbon_mineralization": "cost",
    # Exposure indicators: for each, higher = more fragile.
    "climate_margin_at_risk": "cost",
    "climate_margin_at_risk_ratio": "cost",
    "revenue_concentration_hhi": "cost",
    "price_shock_margin_loss": "cost",
    "price_shock_margin_loss_ratio": "cost",
    # Cropping diversity: higher = more diverse.
    "shannon": "benefit",
    # Mineral P and K applied: like nitrogen, a load on the environment.
    "total_phosphorus": "cost",
    "total_potassium": "cost",
    # Pesticide risk to water: every form of it is something to reduce.
    "rpest_surface_at_risk_ha": "cost",
    "rpest_surface_at_risk_share": "cost",
    "rpest_mean": "cost",
    "rpest_max": "cost",
    # Agroecological reach: more area under a measure or under organic management is the
    # stated goal. `aecm_spending` is the exception -- it is public money, hence a cost, and
    # reading it next to aecm_area_ha is what shows whether the money buys area.
    "aecm_area_ha": "benefit",
    "aecm_area_share": "benefit",
    "aecm_spending": "cost",
    "organic_area_ha": "benefit",
    "organic_area_share": "benefit",
    "organic_area_excl_grassland_ha": "benefit",
    "organic_area_excl_grassland_share": "benefit",
    # Intensity ratios. The environmental ones are per TONNE, so lower is cleaner production
    # -- unlike the per-hectare totals, which a policy can lower simply by farming less.
    "gross_margin_per_ha": "benefit",
    "fte_per_ha": "benefit",
    "production_per_ha": "benefit",
    "gross_margin_per_fte": "benefit",
    "nitrogen_per_tonne": "cost",
    "tfi_per_tonne": "cost",
    # Public spending efficiency: euros of subsidy bought per unit of result, so lower is
    # better value for public money. NOTE this judges the SPENDING, not the outcome -- a
    # policy that achieves nothing while spending nothing scores well here and badly on the
    # outcome axes. The two must be read together.
    "subsidy_per_tonne": "cost",
    "subsidy_per_fte": "cost",
    "subsidy_per_euro_margin": "cost",
    "subsidy_per_ha": "cost",
}


# --- The scalar indicator catalogue -------------------------------------------
# Which per-run scalars can be put on a comparison axis, how they are labelled, and where
# each lives in recap.json. Defined here rather than in a page because two pages need them
# (Comparison and Prospective) and a Streamlit page must not be imported by another.

ECON_INDICATORS: dict[str, str] = {
    "total_production_tonnes": "Production (t)",
    # Revenue = gross margin + subsidy, i.e. the exact sum of two other entries of this
    # very list. Kept for continuity, but selecting all three counts the same euros twice.
    "total_revenue": "Revenue (€) [= margin + subsidy]",
    "total_gross_margin": "Gross margin (€)",
    "total_net_revenue": "Net revenue (€)",
    "total_subsidy": "Subsidy (€)",
    "total_labor_cost": "Labour cost (€)",
    "total_fte": "Employment (FTE)",
}
ENV_INDICATORS: dict[str, str] = {
    "total_ghg": "GHG (t CO₂)",
    "total_tfi": "TFI (total)",
    "total_nitrogen": "Nitrogen (kg N)",
    "chlordecone_risk_area": "Chlordecone-risk area (ha)",
    "total_water_need_m3": "Water need (m³)",
    # These two are strongly correlated (balance = inputs - mineralization, and inputs are
    # near-constant), so selecting both roughly doubles soil carbon's weight in the score.
    "soil_carbon_balance": "Soil carbon balance (t C)",
    "soil_carbon_mineralization": "Carbon mineralisation (t C) [redundant]",
    "shannon": "Cropping diversity (Shannon)",
    "total_phosphorus": "Phosphorus (kg P₂O₅)",
    "total_potassium": "Potassium (kg K₂O)",
    # Rpest (Tixier). The surface at risk is the headline -- a mean hides the few very
    # exposed hectares that actually reach a catchment. Read the ranking, not the floor:
    # a pesticide-free crop scores ~2.4, not 0 (see domain/rpest.py).
    "rpest_surface_at_risk_ha": "Rpest — area at risk (ha)",
    "rpest_surface_at_risk_share": "Rpest — share at risk",
    "rpest_mean": "Mean Rpest (0-10)",
    "rpest_max": "Maximum Rpest (0-10)",
}
# Agroecology as the data encodes it. The two families are NOT summable: an AECM pays a named
# practice on conventional crops (green-harvest cane), the organic figure counts itineraries.
# `organic_area_ha` is dominated by pasture, whose itinerary uses an organic cattle process --
# on output_3 the entire organic area IS the pasture floor, and cropland is 0 ha. Hence the
# "excluding grassland" variant, which is the one to read for a statement about cropland.
AGROECOLOGY_INDICATORS: dict[str, str] = {
    "aecm_area_ha": "Area under AECM (ha)",
    "aecm_area_share": "Share under AECM",
    "aecm_spending": "AECM spending (€)",
    "organic_area_ha": "Organic area (ha, grassland included)",
    "organic_area_share": "Organic share (grassland included)",
    "organic_area_excl_grassland_ha": "Organic area excluding grassland (ha)",
    "organic_area_excl_grassland_share": "Organic share excluding grassland",
}
# Ratios derived from the totals. These stay comparable between scenarios allocating
# different areas -- and the subsidy_* ones are the public-policy evaluation metric proper:
# what a euro of public money buys.
INTENSITY_INDICATORS: dict[str, str] = {
    "gross_margin_per_ha": "Gross margin / ha (€)",
    "fte_per_ha": "Employment / ha (FTE)",
    "production_per_ha": "Production / ha (t)",
    "gross_margin_per_fte": "Gross margin / FTE (€)",
    "nitrogen_per_tonne": "Nitrogen / tonne produced (kg N)",
    "tfi_per_tonne": "TFI / tonne produced",
    "subsidy_per_tonne": "Subsidy / tonne (€)",
    "subsidy_per_fte": "Subsidy / FTE (€)",
    "subsidy_per_euro_margin": "Subsidy / € of margin",
    "subsidy_per_ha": "Subsidy / ha (€)",
}
# Food self-sufficiency ratios (crop-only variant), all benefit (higher = more autonomous).
AUTONOMY_INDICATORS: dict[str, str] = {
    "autonomy_limiting": "Self-sufficiency (limiting nutrient)",
    "autonomy_kcal": "Energy self-sufficiency (kcal)",
    "autonomy_prot": "Protein self-sufficiency",
    "autonomy_lip": "Lipid self-sufficiency",
    "autonomy_glu": "Carbohydrate self-sufficiency",
    "autonomy_fibres": "Fibre self-sufficiency",
    "autonomy_ca": "Calcium self-sufficiency",
    "autonomy_p": "Phosphorus self-sufficiency",
    "autonomy_mg": "Magnesium self-sufficiency",
    "autonomy_k": "Potassium self-sufficiency",
    "autonomy_fe": "Iron self-sufficiency",
}
# Exposure of a FIXED allocation to shocks -- nothing is re-optimized. Not to be confused
# with the robustness metrics of the prospective page, which re-solve under each forcing.
RESILIENCE_INDICATORS: dict[str, str] = {
    "climate_margin_at_risk": "Climate margin at risk (€) [absolute]",
    "climate_margin_at_risk_ratio": "Climate margin at risk (share)",
    "revenue_concentration_hhi": "Revenue concentration (HHI)",
    "price_shock_margin_loss": "Loss under price shock (€) [absolute]",
    "price_shock_margin_loss_ratio": "Loss under price shock (share)",
}
GINI_KEY = "gini_revenue_by_farm"
INDICATOR_LABELS: dict[str, str] = {
    **ECON_INDICATORS, **ENV_INDICATORS, **INTENSITY_INDICATORS,
    **AGROECOLOGY_INDICATORS, **AUTONOMY_INDICATORS, **RESILIENCE_INDICATORS,
    GINI_KEY: "Gini (revenue per farm)",
}


def indicator_value(recap: dict, side: str, indicator: str):
    """Scalar value of an indicator for one (run, side), or None when the run predates the
    block that holds it. Each family lives in its own recap block."""
    if indicator == GINI_KEY:
        return recap.get(GINI_KEY)
    if indicator == "shannon":
        return (recap.get("diversity") or {}).get(side, {}).get("shannon")
    if indicator in AGROECOLOGY_INDICATORS:
        return (recap.get("agroecology") or {}).get(side, {}).get(indicator)
    if indicator in INTENSITY_INDICATORS:
        return (recap.get("intensity") or {}).get(side, {}).get(indicator)
    if indicator in ENV_INDICATORS:
        return (recap.get("environment") or {}).get(side, {}).get(indicator)
    if indicator in RESILIENCE_INDICATORS:
        return (recap.get("resilience") or {}).get(side, {}).get(indicator)
    if indicator in AUTONOMY_INDICATORS:
        auto = (recap.get("food_autonomy") or {}).get(side, {})
        if indicator == "autonomy_limiting":
            return auto.get("limiting_crop_only")
        return auto.get("crop_only", {}).get(indicator[len("autonomy_"):])
    return (recap.get("economics") or {}).get(side, {}).get(indicator)


# Family each indicator belongs to, for the family-balanced composite score below. The
# families are the ones the run report itself is organised in, plus "intensity" for the
# derived ratios.
INDICATOR_FAMILY: dict[str, str] = {
    "total_production_tonnes": "economy",
    "total_revenue": "economy",
    "total_gross_margin": "economy",
    "total_net_revenue": "economy",
    "total_subsidy": "economy",
    "total_labor_cost": "economy",
    "total_fte": "economy",
    "total_ghg": "environment",
    "total_tfi": "environment",
    "total_nitrogen": "environment",
    "chlordecone_risk_area": "environment",
    "total_water_need_m3": "environment",
    "total_phosphorus": "environment",
    "total_potassium": "environment",
    "rpest_surface_at_risk_ha": "environment",
    "rpest_surface_at_risk_share": "environment",
    "rpest_mean": "environment",
    "rpest_max": "environment",
    "aecm_area_ha": "agroecology",
    "aecm_area_share": "agroecology",
    "aecm_spending": "agroecology",
    "organic_area_ha": "agroecology",
    "organic_area_share": "agroecology",
    "organic_area_excl_grassland_ha": "agroecology",
    "organic_area_excl_grassland_share": "agroecology",
    "soil_carbon_balance": "environment",
    "soil_carbon_mineralization": "environment",
    "shannon": "environment",
    "gini_revenue_by_farm": "equity",
    "climate_margin_at_risk": "exposure",
    "climate_margin_at_risk_ratio": "exposure",
    "revenue_concentration_hhi": "exposure",
    "price_shock_margin_loss": "exposure",
    "price_shock_margin_loss_ratio": "exposure",
    "gross_margin_per_ha": "intensity",
    "fte_per_ha": "intensity",
    "production_per_ha": "intensity",
    "gross_margin_per_fte": "intensity",
    "nitrogen_per_tonne": "intensity",
    "tfi_per_tonne": "intensity",
    "subsidy_per_tonne": "intensity",
    "subsidy_per_fte": "intensity",
    "subsidy_per_euro_margin": "intensity",
    "subsidy_per_ha": "intensity",
}
# Every autonomy_* key belongs to one family, resolved by prefix in indicator_family().
_AUTONOMY_FAMILY = "self_sufficiency"


def indicator_family(indicator: str) -> str:
    if indicator.startswith("autonomy_"):
        return _AUTONOMY_FAMILY
    return INDICATOR_FAMILY.get(indicator, "other")


# An indicator a constraint PINS is an input of the scenario, not one of its results.
# Scoring a policy on the ceiling it chose for itself is circular: a scenario that sets
# subsidies to zero wins the "public spending" axis by construction. This maps the
# indicator name a bound targets onto the recap key it determines.
_BOUND_INDICATOR_BY_RATE: dict[str, tuple[str, ...]] = {
    "subsidy": ("total_subsidy", "subsidy_per_tonne", "subsidy_per_fte",
                   "subsidy_per_euro_margin", "subsidy_per_ha"),
    "labor": ("total_fte", "fte_per_ha", "gross_margin_per_fte"),
    "tfi": ("total_tfi", "tfi_per_tonne"),
    "nitrogen": ("total_nitrogen", "nitrogen_per_tonne"),
    "ghg": ("total_ghg",),
    "water": ("total_water_need_m3",),
    "carbon": ("soil_carbon_balance",),
    "margin": ("total_gross_margin", "gross_margin_per_ha", "gross_margin_per_fte"),
}


def bound_indicators(recap: dict) -> set[str]:
    """Indicators this run PINNED with a constraint rather than produced.

    Read from recap['constraints'], which already lists every enabled constraint with its
    args -- so this works on runs written before this function existed. A production bound
    counts too: a territorial tonnage ceiling or floor determines total production.

    A zone-level bound (per farm, per catchment) is reported as well: it does not fix the
    territorial total outright, but it does shape it, and a reader deserves the warning.
    """
    pinned: set[str] = set()
    for entry in recap.get("constraints") or []:
        name = entry.get("name")
        args = entry.get("args") or {}
        if name in ("territory_indicator_bound", "zone_indicator_bound"):
            pinned.update(_BOUND_INDICATOR_BY_RATE.get(args.get("indicator"), ()))
        elif name == "territory_production_bound":
            pinned.add("total_production_tonnes")
            pinned.add("production_per_ha")
    return pinned


def compute_composite_scores(
    raw: pd.DataFrame,
    weights: dict[str, float],
    *,
    balance_families: bool = True,
) -> pd.Series:
    """Weighted composite score in [0,1] per series (scenario), one row of `raw` each.

    Each column is min-max normalized across the rows so 1 = best of the compared set;
    "cost" indicators (INDICATOR_DIRECTION) are inverted so lower raw = higher score. A
    constant column (or a single scenario) scores 0.5 (nothing to rank).

    `balance_families` divides each indicator's weight by the number of SELECTED indicators
    of its family, so a family contributes once however many of its members are on screen.
    Without it the score silently weights by how finely a family happens to be broken down:
    the eleven food-autonomy ratios are near-collinear (same production drives them all) and
    would carry eleven times the weight of greenhouse gases. The same trap applies to each
    exposure indicator and its ratio (same numerator), and to revenue = margin + subsidy.
    Pass False to get the historical, per-indicator behaviour.
    """
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

    effective = {c: float(weights[c]) for c in usable}
    if balance_families:
        counts: dict[str, int] = {}
        for col in usable:
            family = indicator_family(col)
            counts[family] = counts.get(family, 0) + 1
        effective = {c: effective[c] / counts[indicator_family(c)] for c in usable}

    w = pd.Series(effective, dtype=float)
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
    return f"{display_name} · {SIDE_LABELS.get(side, side)}"


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
    value_label = "Relative share (%)" if relative else measure_label

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
