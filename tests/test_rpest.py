"""Rpest (Tixier) fuzzy pesticide-risk tree. Data-free."""

import pandas as pd
import pytest

from case_studies.guadeloupe.domain.rpest import (
    compute_crop_properties,
    compute_rpest_by_pair,
    unfavourability,
)


def test_unfavourability_is_linear_between_the_thresholds():
    values = pd.Series([0.0, 500.0, 1000.0, 2000.0, 3000.0])
    degrees = unfavourability(values, favourable=500.0, unfavourable=2000.0)
    assert degrees.tolist() == pytest.approx([0.0, 0.0, 1 / 3, 1.0, 1.0])


def test_unfavourability_handles_a_reversed_scale():
    # ADI: a HIGH acceptable daily intake is the favourable end, so the slope is negative.
    degrees = unfavourability(pd.Series([1.0, 0.5, 0.0]), favourable=1.0, unfavourable=0.0)
    assert degrees.tolist() == pytest.approx([0.0, 0.5, 1.0])


def test_unfavourability_with_equal_thresholds_is_zero_not_infinite():
    assert unfavourability(pd.Series([5.0]), 1.0, 1.0).tolist() == [0.0]


def _thresholds():
    return pd.DataFrame(
        {
            "Favorable": [0.0, 1.0, 1.0, 1.8, 500.0, 500.0, 1.0],
            "Defavorable": [5.0, 0.0, 2.0, 2.8, 2000.0, 2000.0, 0.0],
        },
        index=["SEUIL_DOSE_CULT", "SEUIL_ADI_CULT", "SEUIL_DT50_CULT",
               "SEUIL_GUS_CULT   ", "SEUIL_RUI_PARC", "SEUIL_DRAI_PARC",
               "SEUIL_MIN_ADIAQUATOX"],
    )


def _properties(**overrides):
    base = {"DT50": 0.0, "ADI": 1.0, "AQUATOX": 1.0, "GUS": 0.0, "QMA": 0.0}
    base.update(overrides)
    return pd.DataFrame([base], index=["CROP"])


def _plots(runoff: float, drainage: float):
    return pd.DataFrame(
        {"RUI_PARC": [runoff], "DRAI_PARC": [drainage]}, index=["P1"]
    )


def test_a_clean_crop_on_a_clean_plot_scores_zero():
    score = compute_rpest_by_pair(
        _properties(), _plots(runoff=0.0, drainage=0.0), _thresholds(), ["CROP"]
    )
    assert score.loc["P1", "CROP"] == pytest.approx(0.0)


def test_the_worst_crop_on_the_worst_plot_scores_ten():
    score = compute_rpest_by_pair(
        _properties(DT50=10.0, ADI=0.0, AQUATOX=0.0, GUS=5.0, QMA=50.0),
        _plots(runoff=5000.0, drainage=5000.0),
        _thresholds(),
        ["CROP"],
    )
    assert score.loc["P1", "CROP"] == pytest.approx(10.0)


def test_the_plot_matters_as_well_as_the_crop():
    """The same crop scores worse on a runoff-prone plot -- that is the point of Rpest,
    which no per-crop rate can express."""
    props = _properties(QMA=50.0, DT50=10.0, ADI=0.0, AQUATOX=0.0, GUS=5.0)
    clean = compute_rpest_by_pair(props, _plots(0.0, 0.0), _thresholds(), ["CROP"])
    dirty = compute_rpest_by_pair(props, _plots(5000.0, 5000.0), _thresholds(), ["CROP"])
    assert dirty.loc["P1", "CROP"] > clean.loc["P1", "CROP"]


def test_trailing_spaces_in_a_threshold_identifier_are_tolerated():
    # R_Tixier.txt really does pad "SEUIL_GUS_CULT" with spaces; an exact lookup would drop
    # the leaching term.
    thresholds = _thresholds()
    assert "SEUIL_GUS_CULT   " in thresholds.index
    score = compute_rpest_by_pair(_properties(), _plots(0.0, 0.0), thresholds, ["CROP"])
    assert not score.empty


def test_unknown_crops_are_dropped_rather_than_raising():
    score = compute_rpest_by_pair(
        _properties(), _plots(0.0, 0.0), _thresholds(), ["CROP", "ABSENT"]
    )
    assert list(score.columns) == ["CROP"]


def test_crop_properties_sum_over_the_operations_the_crop_uses():
    """The GAMS documents a dose-weighted mean, but the dose cancels between numerator and
    denominator, leaving a plain sum. Ported as written -- see the module docstring."""
    data_otk = pd.DataFrame(
        {"DOSE": [2.0, 100.0], "AMORTI": [0, 0], "DT50": [30.0, 30.0],
         "ADI": [1.0, 1.0], "AQUATOX": [1.0, 1.0], "GUS": [2.0, 2.0], "QMA": [1.0, 1.0]},
        index=["PHYTO_A", "PHYTO_B"],
    )
    matrice = pd.DataFrame({"BOTH": [1.0, 1.0], "ONE": [1.0, 0.0]}, index=["PHYTO_A", "PHYTO_B"])
    props = compute_crop_properties(
        data_otk, matrice, pd.Series({"BOTH": 1.0, "ONE": 1.0}),
        pd.Series({"BOTH": 12.0, "ONE": 12.0}),
    )
    # A sum, not a mean: two products of DT50 30 give 60, one gives 30. Note the very
    # different doses (2 vs 100) have no effect at all -- which is the quirk.
    assert props.loc["BOTH", "DT50"] == pytest.approx(60.0)
    assert props.loc["ONE", "DT50"] == pytest.approx(30.0)
    # QMA, by contrast, IS a genuine annualised load and does follow the dose.
    assert props.loc["BOTH", "QMA"] == pytest.approx(102.0)


def test_a_pesticide_free_crop_does_not_reach_zero_on_the_real_thresholds():
    """Documented artefact: 'no product' encodes like 'the most toxic product', because a
    zero ADI sits at the unfavourable end of its scale. The ranking stays usable; the
    absolute floor does not."""
    thresholds = _thresholds()
    clean = _properties(ADI=0.0, AQUATOX=0.0)  # what a crop using no product sums to
    score = compute_rpest_by_pair(clean, _plots(0.0, 0.0), thresholds, ["CROP"])
    assert score.loc["P1", "CROP"] > 0.0
