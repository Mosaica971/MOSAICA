from collections.abc import Callable

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


def forbid_where(mask: pd.DataFrame, condition: pd.Series, crops: list[str]) -> pd.DataFrame:
    result = mask.copy()
    result.loc[condition, crops] = False
    return result


def eligible_pairs_from_mask(mask: pd.DataFrame) -> list[tuple[str, str]]:
    stacked = mask.stack()
    return list(stacked[stacked].index)


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
    data_parc: pd.DataFrame, *, crops: list[str], irrigation_column: str
) -> tuple[list[str], pd.Series]:
    condition = data_parc[irrigation_column] == 0
    return crops, condition


@register_categorical_rule("soil_type_forbidden")
def rule_soil_type_forbidden(
    data_parc: pd.DataFrame,
    *,
    crops: list[str],
    soil_column: str,
    forbidden_soil_types: list[int],
) -> tuple[list[str], pd.Series]:
    condition = data_parc[soil_column].isin(forbidden_soil_types)
    return crops, condition


@register_categorical_rule("melon_soil_restriction")
def rule_melon_soil_restriction(
    data_parc: pd.DataFrame,
    *,
    crops: list[str],
    soil_column: str,
    forbidden_soil_types: list[int],
    island_column: str,
    forbidden_island: int,
) -> tuple[list[str], pd.Series]:
    condition = data_parc[soil_column].isin(forbidden_soil_types) | (
        data_parc[island_column] == forbidden_island
    )
    return crops, condition


@register_categorical_rule("max_risk_threshold")
def rule_max_risk_threshold(
    data_parc: pd.DataFrame, *, crops: list[str], risk_column: str, max_allowed: float
) -> tuple[list[str], pd.Series]:
    condition = data_parc[risk_column] <= max_allowed
    return crops, condition


@register_categorical_rule("exact_risk_value")
def rule_exact_risk_value(
    data_parc: pd.DataFrame, *, crops: list[str], risk_column: str, allowed_value: float
) -> tuple[list[str], pd.Series]:
    condition = data_parc[risk_column] == allowed_value
    return crops, condition


def attribute_bounds_from_config(entries: list[dict]) -> dict[str, tuple[str, str]]:
    return {
        entry["args"]["attribute"]: (entry["args"]["min_col"], entry["args"]["max_col"])
        for entry in entries
        if entry.get("enable", False)
    }
