"""Per-ha environmental rate functions (azote / GES / IFT), mirroring economics.py.
Data-free: tiny hand-built OTK matrix with values chosen for clean expected numbers.

The OTK machinery (AMORTI split, /Duree_Cycle*12 annualization) matches
compute_variable_cost_per_ha_cult; formulas are OPTIMISATION.txt lines 98-127.
"""

import pandas as pd
import pytest

from case_studies.guadeloupe import environment


def _otk_fixture():
    # Two operations: one upfront (AMORTI=0), one amortized (AMORTI=1), both on crop C1.
    data_otk = pd.DataFrame(
        {
            "DOSE": [2.0, 1.0],
            "AMORTI": [0, 1],
            "AZOTE": [3.0, 4.0],
            "IFT": [1.0, 2.0],
            "GES_SURF": [5.0, 6.0],
            "GES_Q": [0.1, 0.2],
        },
        index=["OP_UP", "OP_AM"],
    )
    matrice_otk_cult = pd.DataFrame({"C1": [1.0, 1.0]}, index=["OP_UP", "OP_AM"])
    duree_plant_cult = pd.Series({"C1": 2.0})
    duree_cycle_cult = pd.Series({"C1": 6.0})  # /6*12 == *2
    rdt_cult = pd.Series({"C1": 10.0})
    return data_otk, matrice_otk_cult, duree_plant_cult, duree_cycle_cult, rdt_cult


def test_azote_per_ha_cult_splits_amortized_and_annualizes():
    data_otk, matrice, dplant, dcycle, _ = _otk_fixture()
    # upfront DOSE*AZOTE = 2*3 = 6 ; amortized (1*4)/2 = 2 ; (6+2)/6*12 = 16
    result = environment.compute_azote_per_ha_cult(data_otk, matrice, dplant, dcycle)
    assert result["C1"] == pytest.approx(16.0)


def test_ift_per_ha_cult_uses_ift_without_dose():
    data_otk, matrice, dplant, dcycle, _ = _otk_fixture()
    # upfront IFT = 1 ; amortized 2/2 = 1 ; (1+1)/6*12 = 4
    result = environment.compute_ift_per_ha_cult(data_otk, matrice, dplant, dcycle)
    assert result["C1"] == pytest.approx(4.0)


def test_ges_per_ha_cult_adds_production_term_upfront_only_and_divides_by_coeff():
    data_otk, matrice, dplant, dcycle, rdt = _otk_fixture()
    # surface: upfront 5 + amortized 6/2=3 -> (8)/6*12 = 16
    # production (upfront op only): GES_Q*Rdt = 0.1*10 = 1 -> /6*12 = 2
    # (16 + 2) / coeff(0.5) = 36
    result = environment.compute_ges_per_ha_cult(
        data_otk, matrice, dplant, dcycle, rdt, coeff_c_co2=0.5
    )
    assert result["C1"] == pytest.approx(36.0)
