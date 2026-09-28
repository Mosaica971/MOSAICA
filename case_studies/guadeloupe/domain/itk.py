"""Shared ITK (technical-operation matrix) aggregation.

Every per-ha rate derived from Matrice_OTK_Cult -- variable cost, labor hours, nitrogen,
IFT, the surface term of GES -- follows the same GAMS shape: sum a per-application value
over a crop's operations, spreading amortized ones over the plantation lifetime, then
annualize. That rule lived in three hand-copied places; it lives here now.
"""

import pandas as pd


def annual_rate_per_ha(
    crop_operation_matrix: pd.DataFrame,
    per_application: pd.Series,
    crop_plantation_duration: pd.Series,
    crop_cycle_duration: pd.Series,
    amortized: pd.Series,
) -> pd.Series:
    """Annual per-ha rate over a crop's technical operations: amortized ops (AMORTI=1,
    e.g. plantation) spread over Duree_Plant_Cult, one-off ops (AMORTI=0) charged upfront,
    then / Duree_Cycle_Cult * 12.

    `per_application` and `amortized` are OTK-indexed (matrice rows); the durees are
    crop-indexed (matrice columns).
    """
    otk = crop_operation_matrix.multiply(per_application, axis=0)
    otk_amortized = otk.mul(amortized.astype(float), axis=0).div(crop_plantation_duration, axis=1)
    otk_upfront = otk.mul((~amortized).astype(float), axis=0)
    return (otk_upfront + otk_amortized).sum(axis=0) / crop_cycle_duration * 12
