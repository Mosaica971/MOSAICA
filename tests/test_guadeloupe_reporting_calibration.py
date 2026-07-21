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


def test_pad_by_crop_and_region_scores_each_subregion():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop_and_region(
        dataset, _simulated(), calibration.thresholds_from_config({})
    )
    # R1 observed: CS 5 (P1+P2), PN 3 (P5). R1 simulated: CS 2 (P1), MA 3 (P2), PN 3 (P5).
    assert frame.loc[("R1", "CS"), "pad_pct"] == pytest.approx(60.0)
    assert frame.loc[("R1", "PN"), "pad_pct"] == pytest.approx(0.0)
    # R2 observed: ME 1 (P3), IG 1 (P6). R2 simulated: ME 1 only.
    assert frame.loc[("R2", "ME"), "pad_pct"] == pytest.approx(0.0)
    assert frame.loc[("R2", "IG"), "pad_pct"] == pytest.approx(100.0)


def test_pad_by_crop_and_region_carries_a_total_per_region():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop_and_region(
        dataset, _simulated(), calibration.thresholds_from_config({})
    )
    # R1: deviations CS 3 + MA 3 = 6 over 8 observed hectares.
    assert frame.loc[("R1", calibration.TOTAL_KEY), "pad_pct"] == pytest.approx(75.0)
    # R2: deviation IG 1 over 2 observed hectares.
    assert frame.loc[("R2", calibration.TOTAL_KEY), "pad_pct"] == pytest.approx(50.0)


def test_pad_by_crop_and_region_uses_the_subregional_threshold():
    dataset = _small_dataset()
    thresholds = calibration.CalibrationThresholds(
        regional_pad_max=0.0, subregional_pad_max=60.0
    )
    frame = calibration.pad_by_crop_and_region(dataset, _simulated(), thresholds)
    assert bool(frame.loc[("R1", "CS"), "within_threshold"]) is True  # 60 <= 60
    assert bool(frame.loc[("R2", "IG"), "within_threshold"]) is False  # 100 > 60


def test_pad_by_farm_scores_each_holding():
    dataset = _small_dataset()
    frame = calibration.pad_by_farm(
        dataset, _simulated(), calibration.thresholds_from_config({})
    )
    # E1 observed 5 ha of cane, simulated 2 cane + 3 market gardening -> 6 ha of deviation.
    assert frame.loc["E1", "observed_ha"] == pytest.approx(5.0)
    assert frame.loc["E1", "pad_pct"] == pytest.approx(120.0)
    # E2 keeps its melon and its non-cultivated plot: nothing moved.
    assert frame.loc["E2", "pad_pct"] == pytest.approx(0.0)
    assert bool(frame.loc["E2", "within_threshold"]) is True
    # E3 loses its yam: 1 ha of deviation over 4 observed.
    assert frame.loc["E3", "pad_pct"] == pytest.approx(25.0)
    assert bool(frame.loc["E3", "within_threshold"]) is False


def test_field_match_rate_counts_plots_and_hectares_per_region():
    dataset = _small_dataset()
    frame = calibration.field_match_rate(dataset, _simulated())
    # R1 holds P1 (CS=CS, match, 2 ha), P2 (CS vs MA, miss, 3 ha), P5 (PN=PN, match, 3 ha).
    assert frame.loc["R1", "matched_plots"] == 2
    assert frame.loc["R1", "total_plots"] == 3
    assert frame.loc["R1", "matched_ha"] == pytest.approx(5.0)
    assert frame.loc["R1", "total_ha"] == pytest.approx(8.0)
    assert frame.loc["R1", "area_match_pct"] == pytest.approx(62.5)


def test_field_match_rate_ignores_plots_absent_from_both_sides():
    dataset = _small_dataset()
    frame = calibration.field_match_rate(dataset, _simulated())
    # P4 is NC in 2017 and unallocated by the solver: it belongs to no crop's acreage on
    # either side, so it must not inflate the denominator. P6 (yam lost) must.
    assert frame.loc["R2", "total_plots"] == 2
    assert frame.loc["R2", "matched_plots"] == 1


def test_field_match_rate_total_row():
    dataset = _small_dataset()
    total = calibration.field_match_rate(dataset, _simulated()).loc[calibration.TOTAL_KEY]
    assert total["matched_plots"] == 3
    assert total["total_plots"] == 5
    assert total["plot_match_pct"] == pytest.approx(60.0)
    assert total["matched_ha"] == pytest.approx(6.0)
    assert total["total_ha"] == pytest.approx(10.0)
    assert total["area_match_pct"] == pytest.approx(60.0)


def test_field_match_rate_is_total_when_the_simulation_reproduces_the_baseline():
    dataset = _small_dataset()
    identical = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "PN", "P6": "IG"})
    total = calibration.field_match_rate(dataset, identical).loc[calibration.TOTAL_KEY]
    assert total["plot_match_pct"] == pytest.approx(100.0)
    assert total["area_match_pct"] == pytest.approx(100.0)
