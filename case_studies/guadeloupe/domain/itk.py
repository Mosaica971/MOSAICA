"""Shared ITK (technical-operation matrix) aggregation.

Every per-ha rate derived from Matrice_OTK_Cult -- variable cost, labor hours, nitrogen,
IFT, the surface term of GES -- follows the same GAMS shape: sum a per-application value
over a crop's operations, spreading amortized ones over the plantation lifetime, then
annualize. That rule lived in three hand-copied places; it lives here now.
"""

import pandas as pd


def annual_rate_per_ha_cult(
    matrice_otk_cult: pd.DataFrame,
    per_application: pd.Series,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    amortized: pd.Series,
) -> pd.Series:
    """Annual per-ha rate over a crop's technical operations: amortized ops (AMORTI=1,
    e.g. plantation) spread over Duree_Plant_Cult, one-off ops (AMORTI=0) charged upfront,
    then / Duree_Cycle_Cult * 12.

    `per_application` and `amortized` are OTK-indexed (matrice rows); the durees are
    crop-indexed (matrice columns).
    """
    otk = matrice_otk_cult.multiply(per_application, axis=0)
    otk_amortized = otk.mul(amortized.astype(float), axis=0).div(duree_plant_cult, axis=1)
    otk_upfront = otk.mul((~amortized).astype(float), axis=0)
    return (otk_upfront + otk_amortized).sum(axis=0) / duree_cycle_cult * 12
