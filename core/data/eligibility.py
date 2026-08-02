from collections.abc import Callable
from typing import Any

import pandas as pd


def compute_eligibility_mask(
    plot_attributes: pd.DataFrame,
    crop_bounds: pd.DataFrame,
    attribute_bounds: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    mask = pd.DataFrame(True, index=plot_attributes.index, columns=crop_bounds.index)
    for attribute, (min_col, max_col) in attribute_bounds.items():
        values = plot_attributes[attribute].to_numpy()[:, None]
        mins = crop_bounds[min_col].to_numpy()[None, :]
        maxs = crop_bounds[max_col].to_numpy()[None, :]
        within_bounds = (values >= mins) & (values <= maxs)
        mask &= pd.DataFrame(
            within_bounds, index=plot_attributes.index, columns=crop_bounds.index
        )
    return mask


def forbid_where(mask: pd.DataFrame, condition: pd.Series, crops: "list[str] | str") -> pd.DataFrame:
    """Clear `crops` on every plot matching `condition`.

    ``crops="*"`` means every crop in the mask -- for a rule that takes land out of
    production altogether (urbanisation, a protection perimeter) rather than banning a
    particular activity. Spelling out all 84 codes would work too, but would silently miss
    any crop added later, which is the opposite of what such a rule means.
    """
    result = mask.copy()
    columns = list(mask.columns) if crops == "*" else crops
    result.loc[condition, columns] = False
    return result


def eligible_pairs_from_mask(mask: pd.DataFrame) -> list[tuple[str, str]]:
    stacked = mask.stack()
    return list(stacked[stacked].index)


# Every rule below accepts (and ignores) extra keyword arguments, so a config entry may
# carry `label: <name>`. Labels are how a scenario batch targets ONE entry -- enable/disable
# and set_args match on the label first, and falling back to the rule `name` would hit every
# entry sharing it (there are six separate forbid_crops entries). A rule that is enabled in
# config.yaml is lifted by DISABLING its label, which is how a scenario reopens a ban.
CATEGORICAL_RULE_REGISTRY: dict[str, Callable] = {}


def register_categorical_rule(name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        if name in CATEGORICAL_RULE_REGISTRY:
            raise ValueError(f"'{name}' is already registered")
        CATEGORICAL_RULE_REGISTRY[name] = fn
        return fn

    return decorator


@register_categorical_rule("irrigation_required")
def rule_irrigation_required(
    plot_attributes: pd.DataFrame, *, crops: list[str], irrigation_column: str, **_args: Any
) -> tuple[list[str], pd.Series]:
    condition = plot_attributes[irrigation_column] == 0
    return crops, condition


@register_categorical_rule("soil_type_forbidden")
def rule_soil_type_forbidden(
    plot_attributes: pd.DataFrame,
    *,
    crops: list[str],
    soil_column: str,
    forbidden_soil_types: list[int],
    **_args: Any,
) -> tuple[list[str], pd.Series]:
    condition = plot_attributes[soil_column].isin(forbidden_soil_types)
    return crops, condition


@register_categorical_rule("region_crop_forbidden")
def rule_region_crop_forbidden(
    plot_attributes: pd.DataFrame,
    *,
    crops: list[str],
    region_column: str,
    forbidden_regions: list[str],
    **_args: Any,
) -> tuple[list[str], pd.Series]:
    condition = plot_attributes[region_column].isin(forbidden_regions)
    return crops, condition


@register_categorical_rule("max_risk_threshold")
def rule_max_risk_threshold(
    plot_attributes: pd.DataFrame,
    *,
    crops: list[str],
    risk_column: str,
    max_allowed: float,
    **_args: Any,
) -> tuple[list[str], pd.Series]:
    condition = plot_attributes[risk_column] <= max_allowed
    return crops, condition


@register_categorical_rule("exact_risk_value")
def rule_exact_risk_value(
    plot_attributes: pd.DataFrame,
    *,
    crops: list[str],
    risk_column: str,
    allowed_value: float,
    **_args: Any,
) -> tuple[list[str], pd.Series]:
    condition = plot_attributes[risk_column] == allowed_value
    return crops, condition


@register_categorical_rule("friche_lock")
def rule_friche_lock(
    plot_attributes: pd.DataFrame,
    *,
    crops: list[str],
    history_columns: list[str],
    fallow_codes: list[int],
    **_args: Any,
) -> tuple[list[str], pd.Series]:
    condition = pd.Series(True, index=plot_attributes.index)
    for column in history_columns:
        condition &= plot_attributes[column].isin(fallow_codes)
    return crops, condition


@register_categorical_rule("forbid_crops")
def rule_forbid_crops(
    plot_attributes: pd.DataFrame, *, crops: list[str], **_args: Any
) -> tuple[list[str], pd.Series]:
    """Forbid `crops` on every plot (unconditional). Used by climate/sanitary shock
    scenarios (drought disables irrigated crops, disease disables a filiere) and by the
    GAMS Eq_CS_IRR ban (irrigated sugarcane disabled everywhere)."""
    condition = pd.Series(True, index=plot_attributes.index)
    return crops, condition


@register_categorical_rule("land_take")
def rule_land_take(
    plot_attributes: pd.DataFrame,
    *,
    crops: "list[str] | str",
    share: float,
    order_by: str,
    ascending: bool = True,
    surface_column: str = "SURF_HA",
    **_args: Any,
) -> tuple["list[str] | str", pd.Series]:
    """Take `share` of the total surface out of production, plot by plot in `order_by` order.

    Land loss is the one pressure a crop-allocation model cannot express by changing a
    coefficient: farmland that is built on stops being farmland. It is also not the same as
    a zone_filter, which removes a named island or farm -- urbanisation eats a SHARE of the
    territory, and it eats it selectively.

    `order_by` names the attribute that decides who goes first, and it is the whole content
    of the scenario: sorting by ALTITUDE ascending takes the low flat land near the towns,
    which is what actually gets built on; sorting by SURF_HA ascending takes the small
    parcels first, which models fragmentation-driven abandonment instead. Plots are removed
    until their cumulative surface reaches the share, so the target is met in hectares and
    not in plot count.

    Note the territorial constraints are deliberately NOT rescaled alongside: keeping the
    same production targets on less land is exactly the pressure being modelled.
    """
    if not 0.0 <= share <= 1.0:
        raise ValueError(f"land_take: share must be within [0, 1], got {share}")
    if order_by not in plot_attributes.columns:
        available = ", ".join(sorted(plot_attributes.columns))
        raise KeyError(f"land_take: unknown order_by column {order_by!r}. Available: {available}")

    surface = plot_attributes[surface_column]
    target = float(surface.sum()) * share
    # Ties broken by the plot index so the same scenario always removes the same plots --
    # a forcing that shifted between runs would be unusable in a comparison.
    ranked = plot_attributes.sort_values(
        by=[order_by, surface_column], ascending=[ascending, True], kind="mergesort"
    ).index
    cumulative = surface.reindex(ranked).cumsum()
    taken = ranked[cumulative <= target] if target > 0 else ranked[:0]

    condition = pd.Series(False, index=plot_attributes.index)
    condition.loc[taken] = True
    return crops, condition


_COMPARATORS: dict[str, Callable[[pd.Series, Any], pd.Series]] = {
    "eq": lambda s, v: s == v,
    "ne": lambda s, v: s != v,
    "in": lambda s, v: s.isin(v),
    "not_in": lambda s, v: ~s.isin(v),
    "lt": lambda s, v: s < v,
    "le": lambda s, v: s <= v,
    "gt": lambda s, v: s > v,
    "ge": lambda s, v: s >= v,
}


@register_categorical_rule("attribute_forbidden")
def rule_attribute_forbidden(
    plot_attributes: pd.DataFrame,
    *,
    crops: list[str],
    conditions: list[dict[str, Any]],
    **_args: Any,
) -> tuple[list[str], pd.Series]:
    """Forbid `crops` on plots where ALL `conditions` hold (logical AND). Each condition is
    {column, op, value} with op in eq/ne/in/not_in/lt/le/gt/ge. Express an OR across columns
    with several rule entries (each forbids its subset; the mask keeps the union forbidden).
    Ports the GAMS geographic/soil/irrigation ITK bans (Eq_CS_*, Eq_IG_*_ILE, Eq_BA_*,
    Eq_BC_*, Eq_AG_*, Eq_VE_*)."""
    condition = pd.Series(True, index=plot_attributes.index)
    for spec in conditions:
        comparator = _COMPARATORS[spec["op"]]
        condition &= comparator(plot_attributes[spec["column"]], spec["value"])
    return crops, condition


def attribute_bounds_from_config(entries: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    return {
        entry["args"]["attribute"]: (entry["args"]["min_col"], entry["args"]["max_col"])
        for entry in entries
        if entry.get("enable", False)
    }
