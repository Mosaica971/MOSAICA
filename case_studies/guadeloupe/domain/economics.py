from typing import Any

import pandas as pd

from case_studies.guadeloupe.domain.itk import annual_rate_per_ha


def apply_crop_multipliers(
    series: pd.Series, rules: list[dict[str, Any]] | None
) -> pd.Series:
    """Scale a per-crop economic Series (e.g. crop_price, crop_subsidy_per_ha) by
    crop-group multipliers, for price-shock / subsidy-cut scenarios without new data.

    `rules` is a list of ``{crops: [...], factor: <float>}`` entries. Each entry
    multiplies the factor into every listed crop present in the Series; entries stack
    cumulatively when their crop lists overlap. A None/empty `rules` is a no-op that
    returns the Series unchanged (so a config without economic_overrides reproduces the
    baseline economics exactly). Crop codes not present in the Series index are ignored.

    ``crops: "*"`` means every crop in the Series -- for the territory-wide shocks a
    prospective scenario needs (abolishing all subsidies, a general price collapse) which
    would otherwise have to enumerate all 84 codes and would silently miss any added later.
    """
    if not rules:
        return series
    factors = pd.Series(1.0, index=series.index)
    for rule in rules:
        crops = rule["crops"]
        if crops == "*":
            factors *= rule["factor"]
            continue
        present = [c for c in crops if c in factors.index]
        factors.loc[present] *= rule["factor"]
    return series * factors


def compute_crop_variable_cost_per_ha(
    operation_data: pd.DataFrame,
    crop_operation_matrix: pd.DataFrame,
    crop_plantation_duration: pd.Series,
    crop_cycle_duration: pd.Series,
    crop_harvest_cost: pd.Series,
    crop_transport_cost: pd.Series,
    crop_yield: pd.Series,
) -> pd.Series:
    """CV_Ha_Cult: variable cost per ha (OPTIMISATION.GMS lines 11-19).

    Each OTK (technical operation) costs dose*price per application. Amortized
    operations (AMORTI=1, e.g. plantation) are spread over the plantation
    lifetime (Duree_Plant_Cult); one-off operations (AMORTI=0) are not.
    """
    cost_from_otk = annual_rate_per_ha(
        crop_operation_matrix,
        operation_data["DOSE"] * operation_data["PRIX_UNIT"],
        crop_plantation_duration,
        crop_cycle_duration,
        operation_data["AMORTI"] == 1,
    )
    return cost_from_otk + (crop_harvest_cost + crop_transport_cost) * crop_yield


def compute_crop_labor_hours_per_ha(
    operation_data: pd.DataFrame,
    crop_operation_matrix: pd.DataFrame,
    crop_plantation_duration: pd.Series,
    crop_cycle_duration: pd.Series,
) -> pd.Series:
    """MO_Ha_Cult: labor hours per ha per year (ENTREES.txt:463-466).

    Same OTK structure as compute_crop_variable_cost_per_ha, but each technical
    operation is weighted by its labor requirement (DOSE*MO_EXPL, in hours) instead
    of its monetary cost (DOSE*PRIX_UNIT). Amortized operations (AMORTI=1, e.g.
    plantation) are spread over the plantation lifetime; one-off operations are not.
    Unlike cost, there is no harvest/transport term -- labor is entirely in the OTK.
    """
    return annual_rate_per_ha(
        crop_operation_matrix,
        operation_data["DOSE"] * operation_data["MO_EXPL"],
        crop_plantation_duration,
        crop_cycle_duration,
        operation_data["AMORTI"] == 1,
    )


def compute_crop_subsidy_per_ha(
    posei_area_aid: pd.Series,
    posei_volume_aid: pd.Series,
    industry_aid: pd.Series,
    replanting_aid: pd.Series,
    transport_aid: pd.Series,
    price_guarantee_aid: pd.Series,
    aecm_green_harvest: pd.Series,
    aecm_bare_fallow: pd.Series,
    aecm_compost: pd.Series,
    additional_margin: pd.Series,
    crop_yield: pd.Series,
    crop_cycle_duration: pd.Series,
    crop_plantation_duration: pd.Series,
) -> pd.Series:
    """SUB_TOT_Ha_Cult: total subsidies per ha (OPTIMISATION.GMS lines 21-34).

    Sums POSEI (EU aid), national, and PDRG (agri-environmental, MAE) subsidy
    schemes, plus a flat additional-margin adjustment (MB_ADD_Cult).
    """
    posei = (
        posei_area_aid
        + (posei_volume_aid + industry_aid) * crop_yield / crop_cycle_duration * 12
        + replanting_aid / crop_plantation_duration
    )
    national = (transport_aid + price_guarantee_aid) * crop_yield / crop_cycle_duration * 12
    pdrg = aecm_green_harvest + aecm_bare_fallow + aecm_compost

    return posei + national + pdrg + additional_margin


def compute_crop_sales_per_ha(
    crop_yield: pd.Series,
    crop_price: pd.Series,
    crop_bagasse: pd.Series,
    crop_cycle_duration: pd.Series,
) -> pd.Series:
    """Sales-only component of PB_Ha_Cult, annualized the same way (excludes subsidy)."""
    return crop_yield * (crop_price + crop_bagasse) / crop_cycle_duration * 12


def compute_crop_gross_product_per_ha(
    crop_yield: pd.Series,
    crop_price: pd.Series,
    crop_bagasse: pd.Series,
    crop_subsidy_per_ha: pd.Series,
    crop_cycle_duration: pd.Series,
) -> pd.Series:
    """PB_Ha_Cult: gross product per ha, annualized (OPTIMISATION.GMS lines 36-38)."""
    sales = compute_crop_sales_per_ha(crop_yield, crop_price, crop_bagasse, crop_cycle_duration)
    return sales + crop_subsidy_per_ha / crop_cycle_duration * 12


def compute_crop_gross_margin_per_ha(
    crop_gross_product_per_ha: pd.Series,
    crop_variable_cost_per_ha: pd.Series,
) -> pd.Series:
    """MB_Ha_Cult: gross margin per ha (OPTIMISATION.GMS lines 40-42)."""
    return crop_gross_product_per_ha - crop_variable_cost_per_ha
