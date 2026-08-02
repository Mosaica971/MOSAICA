"""Phosphorus / potassium grades read off Data_OTK fertiliser names. Data-free."""

import pandas as pd
import pytest

from case_studies.guadeloupe.domain.environment import (
    compute_azote_per_ha_cult,
    compute_phosphore_per_ha_cult,
    compute_potasse_per_ha_cult,
    nutrient_grades,
)


def test_npk_triplet_is_read_as_p_and_k():
    assert nutrient_grades("08_20_20") == (0.20, 0.20)
    assert nutrient_grades("11_11_33") == (0.11, 0.33)
    assert nutrient_grades("12_06_20") == (0.06, 0.20)


def test_triplet_is_found_even_with_a_crop_suffix_or_prefix():
    # The real table names several rows per crop: 14_04_25_BA_INT, 11_11_33_MAR, 08_20_20_CS.
    assert nutrient_grades("14_04_25_BA_INT") == (0.04, 0.25)
    assert nutrient_grades("11_11_33_CONC") == (0.11, 0.33)
    assert nutrient_grades("08_20_20_CS") == (0.20, 0.20)


def test_dap_is_a_pair_not_a_triplet():
    # DAP_18_46 is 18-46-0: the second number is P2O5, and there is no K. Reading it as a
    # triplet would be impossible (only two numbers) and reading 46 as K would be wrong.
    assert nutrient_grades("DAP_18_46") == (0.46, 0.0)


def test_named_single_nutrient_salts():
    assert nutrient_grades("KNO3") == (0.0, 0.46)
    assert nutrient_grades("K2SO4") == (0.0, 0.50)
    assert nutrient_grades("KCL") == (0.0, 0.60)
    assert nutrient_grades("UREE") == (0.0, 0.0)  # urea is 46-0-0: nitrogen only


def test_rows_that_declare_no_grade_contribute_nothing():
    # Operations, phytosanitary products and organic amendments alike: this is a MINERAL
    # P/K budget, and anything without a declared grade must read as 0, never as a guess.
    for name in ("LABOUR", "FUMIER", "ORGANOR", "FERTI_MA_PLBIO", "ROUND_UP_FLASH",
                 "PLANTATION_CS", "GRESIL"):
        assert nutrient_grades(name) == (0.0, 0.0), name


def test_a_bare_number_run_is_not_mistaken_for_a_grade():
    assert nutrient_grades("MACHINE_123456") == (0.0, 0.0)
    assert nutrient_grades("CODE_1234_5678") == (0.0, 0.0)


def _tiny_itk():
    """One crop, two operations: 100 kg of 08_20_20 and 50 kg of urea, both one-off."""
    data_otk = pd.DataFrame(
        {"DOSE": [100.0, 50.0], "AZOTE": [0.08, 0.46], "AMORTI": [0, 0]},
        index=["08_20_20", "UREE"],
    )
    matrice = pd.DataFrame({"CROP": [1.0, 1.0]}, index=["08_20_20", "UREE"])
    duree_plant = pd.Series({"CROP": 1.0})
    duree_cycle = pd.Series({"CROP": 12.0})
    return data_otk, matrice, duree_plant, duree_cycle


def test_p_and_k_use_the_same_formula_as_nitrogen():
    data_otk, matrice, plant, cycle = _tiny_itk()
    kwargs = dict(
        data_otk=data_otk, matrice_otk_cult=matrice,
        duree_plant_cult=plant, duree_cycle_cult=cycle,
    )
    azote = compute_azote_per_ha_cult(**kwargs)["CROP"]
    phosphore = compute_phosphore_per_ha_cult(**kwargs)["CROP"]
    potasse = compute_potasse_per_ha_cult(**kwargs)["CROP"]

    # N: 100 x 0.08 + 50 x 0.46 = 8 + 23 = 31, annualised x12/12.
    assert azote == pytest.approx(31.0)
    # P2O5: only the compound fertiliser declares one -> 100 x 0.20 = 20.
    assert phosphore == pytest.approx(20.0)
    # K2O: 100 x 0.20 = 20; urea carries none.
    assert potasse == pytest.approx(20.0)
