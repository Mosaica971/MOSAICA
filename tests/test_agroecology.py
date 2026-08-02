"""Agroecology as the dataset encodes it: MAE payments and organic itineraries. Data-free."""

import pandas as pd
import pytest

from apps.dashboard import comparison
from case_studies.guadeloupe.domain.agroecology import (
    ORGANIC_OPERATIONS,
    compute_mae_per_ha_cult,
    compute_organic_cult,
    compute_under_mae_cult,
)


def test_mae_sums_the_three_measures():
    vert = pd.Series({"CS": 82.0, "BA": 0.0, "MA": 0.0})
    jachere = pd.Series({"CS": 0.0, "BA": 658.0, "MA": 0.0})
    compost = pd.Series({"CS": 0.0, "BA": 0.0, "MA": 0.0})
    total = compute_mae_per_ha_cult(vert, jachere, compost)
    assert total["CS"] == pytest.approx(82.0)
    assert total["BA"] == pytest.approx(658.0)
    assert total["MA"] == pytest.approx(0.0)


def test_missing_values_do_not_poison_the_sum():
    total = compute_mae_per_ha_cult(
        pd.Series({"CS": 82.0}), pd.Series({"CS": float("nan")}), pd.Series({"CS": 0.0})
    )
    assert total["CS"] == pytest.approx(82.0)


def test_under_mae_is_a_zero_one_rate_so_it_sums_to_hectares():
    flag = compute_under_mae_cult(pd.Series({"CS": 82.0, "MA": 0.0, "BA": 658.0}))
    assert flag.tolist() == [1.0, 0.0, 1.0]


def test_organic_is_read_from_the_itinerary_not_the_crop_name():
    # MA_FAUXBIO is named like an organic crop but performs no organic operation;
    # PN_PIQ is not, and does.
    matrice = pd.DataFrame(
        {
            "MA_PLBIO": [1.0, 0.0, 0.0],
            "MA_FAUXBIO": [0.0, 0.0, 1.0],
            "PN_PIQ": [0.0, 1.0, 0.0],
        },
        index=["FERTI_MA_PLBIO", "PROC_BIO_BOVIN", "LABOUR"],
    )
    organic = compute_organic_cult(matrice)
    assert organic["MA_PLBIO"] == 1.0
    assert organic["PN_PIQ"] == 1.0
    assert organic["MA_FAUXBIO"] == 0.0


def test_organic_is_zero_everywhere_when_no_organic_operation_exists():
    matrice = pd.DataFrame({"CS": [1.0]}, index=["LABOUR"])
    assert compute_organic_cult(matrice).tolist() == [0.0]


def test_organic_operations_are_all_genuine_data_otk_rows():
    """A typo here would silently classify nothing as organic."""
    from case_studies.guadeloupe.pipeline.data_pipeline import TABLES_DIR
    from core.data.readers import read_wide_table

    rows = set(read_wide_table(TABLES_DIR / "Data_OTK.txt").index)
    missing = [op for op in ORGANIC_OPERATIONS if op not in rows]
    assert not missing, f"opérations absentes de Data_OTK : {missing}"


def test_the_two_agroecology_families_are_separate_in_the_dashboard():
    # Summing an MAE area with an organic area would file green-harvest cane as organic.
    assert comparison.indicator_family("surface_mae_ha") == "agroecologie"
    assert comparison.indicator_family("surface_bio_ha") == "agroecologie"
    # Spending is public money: a cost, unlike the areas it buys.
    assert comparison.INDICATOR_DIRECTION["mae_spending"] == "cost"
    assert comparison.INDICATOR_DIRECTION["surface_mae_ha"] == "benefit"


def test_agroecology_indicators_read_their_own_recap_block():
    recap = {"agroecology": {"output": {"surface_mae_ha": 14502.0, "surface_bio_ha": 6096.0}}}
    assert comparison.indicator_value(recap, "output", "surface_mae_ha") == 14502.0
    assert comparison.indicator_value(recap, "output", "surface_bio_ha") == 6096.0
    assert comparison.indicator_value({}, "output", "surface_mae_ha") is None
