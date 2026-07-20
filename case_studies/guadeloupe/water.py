"""Per-ha water need by crop, from the monthly BESOIN_EAU rows of Data_Cult.

Faithful to OPTIMISATION.txt:2489-2560, with two documented departures (see VIGILANCE.md):
rainfall is never deducted (the monthly PLUVIO_*_PARC columns do not exist in the data), so
this is a *gross crop water need*, not a net irrigation need; and the mm -> m3 conversion
factor the GAMS omits is applied explicitly here. GAMS also divides its (factor-less) result
by 1e6 (OPTIMISATION.txt:2559); this module does not replicate that division, so the values
here are plain m3, not GAMS' millions-of-(unlabeled-unit).
"""

import pandas as pd

# 1 mm of water over 1 ha = 10 m3. GAMS omits this factor and divides by 1e6
# (OPTIMISATION.txt:2559); its author had flagged "pourquoi x 10?" in DECLAR_OPT.txt:2114.
M3_PER_MM_PER_HA = 10.0

MONTHLY_WATER_ROWS = [f"BESOIN_EAU_{month:02d}" for month in range(1, 13)]


def compute_monthly_water_need_per_ha_cult(data_cult: pd.DataFrame) -> pd.DataFrame:
    """Monthly crop water need (mm/month): rows = the 12 months in calendar order,
    columns = crops."""
    return data_cult.loc[MONTHLY_WATER_ROWS]


def compute_water_need_per_ha_cult(data_cult: pd.DataFrame) -> pd.Series:
    """Annual crop water need per ha (mm/year): sum of the 12 monthly rows."""
    return compute_monthly_water_need_per_ha_cult(data_cult).sum(axis=0)
