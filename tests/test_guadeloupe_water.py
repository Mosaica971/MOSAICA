import pandas as pd

from case_studies.guadeloupe.domain import water


def _data_cult() -> pd.DataFrame:
    """Data_Cult miniature: lignes = attributs, colonnes = cultures (comme la vraie table)."""
    rows = {f"BESOIN_EAU_{m:02d}": [10.0 * m, 0.0] for m in range(1, 13)}
    rows["KCROP"] = [0.9, 0.5]  # ligne non liée à l'eau, doit être ignorée
    return pd.DataFrame(rows, index=["CROP_A", "CROP_B"]).T


def test_monthly_water_need_returns_twelve_rows_in_calendar_order():
    monthly = water.compute_monthly_water_need_per_ha_cult(_data_cult())
    assert list(monthly.index) == [
        "BESOIN_EAU_01", "BESOIN_EAU_02", "BESOIN_EAU_03", "BESOIN_EAU_04",
        "BESOIN_EAU_05", "BESOIN_EAU_06", "BESOIN_EAU_07", "BESOIN_EAU_08",
        "BESOIN_EAU_09", "BESOIN_EAU_10", "BESOIN_EAU_11", "BESOIN_EAU_12",
    ]
    assert len(monthly.index) == 12
    assert monthly.loc["BESOIN_EAU_01", "CROP_A"] == 10.0
    assert monthly.loc["BESOIN_EAU_12", "CROP_A"] == 120.0


def test_monthly_water_need_ignores_unrelated_rows():
    monthly = water.compute_monthly_water_need_per_ha_cult(_data_cult())
    assert "KCROP" not in monthly.index


def test_annual_water_need_sums_the_twelve_months():
    annual = water.compute_water_need_per_ha_cult(_data_cult())
    # 10 + 20 + ... + 120 = 780
    assert annual["CROP_A"] == 780.0
    assert annual["CROP_B"] == 0.0


def test_m3_conversion_constant_is_ten():
    """1 mm sur 1 ha = 10 m3. Le GAMS omet ce facteur (OPTIMISATION.txt:2559)."""
    assert water.M3_PER_MM_PER_HA == 10.0
