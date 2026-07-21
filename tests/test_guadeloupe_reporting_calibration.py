import numpy as np
import pandas as pd
import pytest

from case_studies.guadeloupe.reporting import calibration
from core.data.dataset import Dataset


def _small_dataset() -> Dataset:
    """Six plots, three farms, two regions.

    Observed 2017 (RPG code -> group): P1/P2 cane, P3 melon, P4 non-cultivated,
    P5 pasture, P6 yam. cult_2016 equals cult_2017 everywhere so the fallow-continuity
    override of compute_base_crop_group is a no-op, except on P4 where both are 14 and it
    stays 14 (NC) anyway.
    """
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0, 1.0, 4.0, 3.0, 1.0],
            "REGION": ["R1", "R1", "R2", "R2", "R1", "R2"],
            "ILE": [1, 1, 2, 2, 1, 2],
            "cult_2016": [6, 6, 13, 14, 7, 18],
            "cult_2017": [6, 6, 13, 14, 7, 18],
        },
        index=["P1", "P2", "P3", "P4", "P5", "P6"],
    )
    expl_parc = pd.DataFrame(
        {
            "farm": ["E1", "E1", "E2", "E2", "E3", "E3"],
            "plot": ["P1", "P2", "P3", "P4", "P5", "P6"],
        }
    )
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "farm_plots": {"E1": ["P1", "P2"], "E2": ["P3", "P4"], "E3": ["P5", "P6"]},
        },
        scalars={},
    )


def _simulated() -> pd.Series:
    """P1 stays cane, P2 flips to market gardening, P3/P5 keep their group,
    P4 and P6 are left unallocated by the solver."""
    return pd.Series(
        {"P1": "CS_NGT_NISM", "P2": "MA_ROTA", "P3": "ME", "P5": "PN_TOUR"}, name="crop"
    )


def test_thresholds_default_to_the_article_values():
    thresholds = calibration.thresholds_from_config({})
    assert thresholds.regional_pad_max == 15.0
    assert thresholds.subregional_pad_max == 20.0
    assert thresholds.farm_pad_max == 20.0
    assert thresholds.farm_type_match_min == 80.0


def test_thresholds_read_the_config_section():
    config = {"reporting": {"calibration": {"regional_pad_max": 5, "farm_pad_max": 33.5}}}
    thresholds = calibration.thresholds_from_config(config)
    assert thresholds.regional_pad_max == 5.0
    assert thresholds.farm_pad_max == 33.5
    assert thresholds.subregional_pad_max == 20.0  # untouched keys keep their default


def test_simulated_groups_folds_fine_crops_and_drops_non_cultivated():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS_NGT_NISM", "P2": "NC", "P3": "TH"})
    result = calibration.simulated_groups(dataset, allocation)
    assert result.to_dict() == {"P1": "CS", "P3": "MA"}


def test_pad_by_crop_scores_each_group_and_the_total():
    dataset = _small_dataset()
    thresholds = calibration.thresholds_from_config({})
    frame = calibration.pad_by_crop(dataset, _simulated(), thresholds)

    # Observed: CS 5 ha, ME 1, PN 3, IG 1 (NC excluded). Simulated: CS 2, MA 3, ME 1, PN 3.
    assert frame.loc["CS", "observed_ha"] == pytest.approx(5.0)
    assert frame.loc["CS", "simulated_ha"] == pytest.approx(2.0)
    assert frame.loc["CS", "abs_deviation_ha"] == pytest.approx(3.0)
    assert frame.loc["CS", "pad_pct"] == pytest.approx(60.0)
    assert bool(frame.loc["CS", "within_threshold"]) is False

    assert frame.loc["PN", "pad_pct"] == pytest.approx(0.0)
    assert bool(frame.loc["PN", "within_threshold"]) is True

    # A group that vanished from the output deviates by 100%.
    assert frame.loc["IG", "simulated_ha"] == pytest.approx(0.0)
    assert frame.loc["IG", "pad_pct"] == pytest.approx(100.0)


def test_pad_is_undefined_for_a_crop_absent_from_the_observed_side():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop(dataset, _simulated(), calibration.thresholds_from_config({}))
    assert frame.loc["MA", "observed_ha"] == pytest.approx(0.0)
    assert frame.loc["MA", "simulated_ha"] == pytest.approx(3.0)
    assert np.isnan(frame.loc["MA", "pad_pct"])
    assert pd.isna(frame.loc["MA", "within_threshold"])


def test_pad_by_crop_total_row_is_the_ratio_of_sums():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop(dataset, _simulated(), calibration.thresholds_from_config({}))
    total = frame.loc[calibration.TOTAL_KEY]
    # Deviations: CS 3 + IG 1 + MA 3 = 7 over 10 observed hectares.
    assert total["observed_ha"] == pytest.approx(10.0)
    assert total["abs_deviation_ha"] == pytest.approx(7.0)
    assert total["pad_pct"] == pytest.approx(70.0)
    assert bool(total["within_threshold"]) is False


def test_pad_is_zero_when_the_simulation_reproduces_the_baseline():
    dataset = _small_dataset()
    identical = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "PN", "P6": "IG"})
    frame = calibration.pad_by_crop(dataset, identical, calibration.thresholds_from_config({}))
    assert frame["pad_pct"].fillna(0.0).abs().max() == pytest.approx(0.0)
    assert frame["within_threshold"].dropna().all()
