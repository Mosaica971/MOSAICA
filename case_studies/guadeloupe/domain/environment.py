"""Per-ha environmental rates by crop (azote / GES / IFT), computed from the ITK
(technical-operation matrix) exactly like the economic per-ha rates in economics.py.

Each rate sums a per-application value over the crop's operations (Matrice_OTK_Cult),
splitting amortized operations (AMORTI=1, spread over Duree_Plant_Cult) from one-off
ones (AMORTI=0), then annualizes with / Duree_Cycle_Cult * 12. Faithful to
OPTIMISATION.txt lines 98-127.
"""

import re

import pandas as pd

from case_studies.guadeloupe.domain.itk import annual_rate_per_ha_cult

# --- Phosphorus and potassium, recovered from the fertiliser NAMES -------------
# Data_OTK carries an AZOTE column but nothing for P or K. The fertiliser rows are named by
# their NPK formula, though (08_20_20, DAP_18_46, 14_04_25_BA_INT, ...), and the nitrogen
# fraction implied by each name matches the AZOTE column EXACTLY -- checked on the real data
# 2026-08-01: DAP_18_46 -> 0.18, 08_20_20 -> 0.08, UREE -> 0.46, KNO3/KCL/K2SO4 -> 0.00.
# That agreement is what licenses reading P2O5 and K2O off the same names with the same
# DOSE x fraction formula: it is the file's own convention, not an outside assumption.
#
# TWO LIMITS, both deliberate and both visible in the data:
#   * single-nutrient salts are named chemically, not numerically (KNO3, K2SO4, KCL, UREE),
#     so their grades come from the table below rather than from a pattern;
#   * KNO3 carries AZOTE = 0.00 in Data_OTK although potassium nitrate is ~13 % N. That is
#     an upstream inconsistency; it is NOT corrected here (parity mandate) and the same
#     zero is therefore mirrored in the nitrogen figures. Flagged in docs/04-vigilance.md.
# Anything not matched contributes 0: organic amendments (FUMIER, ORGANOR, GRESIL, the
# FERTI_MA_*BIO composts) carry no declared grade, so this is a MINERAL P/K budget only.

# Grades as mass fractions of P2O5 and K2O, for the rows whose name is not an NPK triplet.
_NAMED_GRADES: dict[str, tuple[float, float]] = {
    "KNO3": (0.00, 0.46),    # potassium nitrate 13-0-46
    "K2SO4": (0.00, 0.50),   # sulphate of potash 0-0-50
    "KCL": (0.00, 0.60),     # muriate of potash 0-0-60
    "UREE": (0.00, 0.00),    # urea 46-0-0
    "DAP": (0.46, 0.00),     # diammonium phosphate 18-46-0
}

# An NPK triplet anywhere in the row name: "08_20_20", "14_04_25_BA_INT", "DAP_18_46".
_TRIPLET = re.compile(r"(?<!\d)(\d{2})_(\d{2})_(\d{2})(?!\d)")
_PAIR = re.compile(r"^DAP_(\d{2})_(\d{2})(?!\d)")


def nutrient_grades(name: str) -> tuple[float, float]:
    """(P2O5, K2O) mass fractions implied by a Data_OTK row name; (0, 0) when it says
    nothing. Names are matched most-specific first so DAP_18_46 reads as a P fertiliser
    rather than as an unlabelled pair."""
    text = str(name).upper()
    pair = _PAIR.match(text)
    if pair:
        return int(pair.group(2)) / 100.0, 0.0
    triplet = _TRIPLET.search(text)
    if triplet:
        return int(triplet.group(2)) / 100.0, int(triplet.group(3)) / 100.0
    for key, grades in _NAMED_GRADES.items():
        if text == key or text.startswith(f"{key}_"):
            return grades
    return 0.0, 0.0


def _nutrient_rate(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    index: int,
) -> pd.Series:
    grades = pd.Series(
        [nutrient_grades(name)[index] for name in data_otk.index], index=data_otk.index
    )
    amortized = data_otk["AMORTI"] == 1
    per_application = data_otk["DOSE"] * grades
    return annual_rate_per_ha_cult(
        matrice_otk_cult, per_application, duree_plant_cult, duree_cycle_cult, amortized
    )


def compute_phosphore_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """Mineral phosphorus applied per ha per year (kg P2O5/ha/an), by the nitrogen formula
    with the grade read off the fertiliser name. Organic amendments contribute 0."""
    return _nutrient_rate(
        data_otk, matrice_otk_cult, duree_plant_cult, duree_cycle_cult, 0
    )


def compute_potasse_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """Mineral potassium applied per ha per year (kg K2O/ha/an). See compute_phosphore."""
    return _nutrient_rate(
        data_otk, matrice_otk_cult, duree_plant_cult, duree_cycle_cult, 1
    )


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
    return annual_rate_per_ha_cult(
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
    return annual_rate_per_ha_cult(
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
    surface_rate = annual_rate_per_ha_cult(
        matrice_otk_cult, data_otk["GES_SURF"], duree_plant_cult, duree_cycle_cult, amortized
    )
    # Production-linked emissions apply to upfront operations only.
    ges_q_upfront = data_otk["GES_Q"] * (~amortized).astype(float)
    otk_q = matrice_otk_cult.multiply(ges_q_upfront, axis=0)
    production_rate = otk_q.sum(axis=0) * rdt_cult / duree_cycle_cult * 12
    return (surface_rate + production_rate) / coeff_c_co2
