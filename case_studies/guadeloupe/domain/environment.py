"""Per-ha environmental rates by crop (azote / GES / IFT), computed from the ITK
(technical-operation matrix) exactly like the economic per-ha rates in economics.py.

Each rate sums a per-application value over the crop's operations (Matrice_OTK_Cult),
splitting amortized operations (AMORTI=1, spread over Duree_Plant_Cult) from one-off
ones (AMORTI=0), then annualizes with / Duree_Cycle_Cult * 12. Faithful to
OPTIMISATION.txt lines 98-127.
"""

import pandas as pd


def _otk_annual_rate_per_ha_cult(
    matrice_otk_cult: pd.DataFrame,
    per_application: pd.Series,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    amortized: pd.Series,
) -> pd.Series:
    """Annual per-ha rate: sum of per-application values over a crop's operations, with
    amortized ops spread over Duree_Plant_Cult, then / Duree_Cycle_Cult * 12. `amortized`,
    `per_application` are OTK-indexed (matrice rows); the durees are crop-indexed (columns)."""
    otk = matrice_otk_cult.multiply(per_application, axis=0)
    otk_amortized = otk.mul(amortized.astype(float), axis=0).div(duree_plant_cult, axis=1)
    otk_upfront = otk.mul((~amortized).astype(float), axis=0)
    return (otk_upfront + otk_amortized).sum(axis=0) / duree_cycle_cult * 12


def compute_azote_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """AZOTE_Ha_Cult: nitrogen applied per ha per year (kg N/ha/an). Per application =
    DOSE * AZOTE."""
    amortized = data_otk["AMORTI"] == 1
    per_application = data_otk["DOSE"] * data_otk["AZOTE"]
    return _otk_annual_rate_per_ha_cult(
        matrice_otk_cult, per_application, duree_plant_cult, duree_cycle_cult, amortized
    )


def compute_ift_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """IFT_Ha_Cult: treatment frequency index per ha per year. Per application = IFT
    (not scaled by DOSE, unlike azote/cost)."""
    amortized = data_otk["AMORTI"] == 1
    per_application = data_otk["IFT"]
    return _otk_annual_rate_per_ha_cult(
        matrice_otk_cult, per_application, duree_plant_cult, duree_cycle_cult, amortized
    )


def compute_ges_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    rdt_cult: pd.Series,
    coeff_c_co2: float,
) -> pd.Series:
    """GES_Ha_Cult: greenhouse-gas emissions per ha per year (t CO2/ha/an). Two terms,
    both annualized then divided by COEFF_C_CO2 (carbon->CO2):
      - surface term GES_SURF, present in both branches (upfront + amortized/Duree_Plant);
      - production term GES_Q * Rdt_Cult, on one-off (AMORTI=0) operations only.
    """
    amortized = data_otk["AMORTI"] == 1
    surface_rate = _otk_annual_rate_per_ha_cult(
        matrice_otk_cult, data_otk["GES_SURF"], duree_plant_cult, duree_cycle_cult, amortized
    )
    # Production-linked emissions apply to upfront operations only.
    ges_q_upfront = data_otk["GES_Q"] * (~amortized).astype(float)
    otk_q = matrice_otk_cult.multiply(ges_q_upfront, axis=0)
    production_rate = otk_q.sum(axis=0) * rdt_cult / duree_cycle_cult * 12
    return (surface_rate + production_rate) / coeff_c_co2
