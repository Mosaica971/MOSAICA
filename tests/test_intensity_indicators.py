"""Intensity and public-spending-efficiency ratios. Pure arithmetic on totals dicts."""

import pytest

from case_studies.guadeloupe.reporting.indicators import compute_intensity_totals


def _totals():
    economics = {
        "total_production_tonnes": 1000.0,
        "total_subsidy": 50_000.0,
        "total_gross_margin": 200_000.0,
        "total_etp": 10.0,
    }
    environment = {"total_azote": 4000.0, "total_ift": 250.0}
    return economics, environment


def test_land_and_labour_intensities():
    ratios = compute_intensity_totals(*_totals(), surface_ha=100.0)
    assert ratios["gross_margin_per_ha"] == pytest.approx(2000.0)
    assert ratios["etp_per_ha"] == pytest.approx(0.1)
    assert ratios["production_per_ha"] == pytest.approx(10.0)
    assert ratios["gross_margin_per_etp"] == pytest.approx(20_000.0)


def test_environmental_intensity_is_per_tonne_not_per_hectare():
    # The point of the per-tonne form: a policy can lower total nitrogen simply by farming
    # fewer hectares, and only this ratio says whether production itself got cleaner.
    ratios = compute_intensity_totals(*_totals(), surface_ha=100.0)
    assert ratios["azote_per_tonne"] == pytest.approx(4.0)
    assert ratios["ift_per_tonne"] == pytest.approx(0.25)


def test_public_spending_efficiency():
    ratios = compute_intensity_totals(*_totals(), surface_ha=100.0)
    assert ratios["subsidy_per_tonne"] == pytest.approx(50.0)
    assert ratios["subsidy_per_etp"] == pytest.approx(5000.0)
    assert ratios["subsidy_per_euro_margin"] == pytest.approx(0.25)
    assert ratios["subsidy_per_ha"] == pytest.approx(500.0)


def test_zero_denominator_yields_none_not_zero():
    # "No hectares allocated" is not "zero euros per hectare"; a 0 would be averaged into a
    # composite score as though it had been measured.
    economics, environment = _totals()
    ratios = compute_intensity_totals(economics, environment, surface_ha=0.0)
    assert ratios["gross_margin_per_ha"] is None
    assert ratios["subsidy_per_ha"] is None
    assert ratios["azote_per_tonne"] == pytest.approx(4.0)  # unaffected by surface


def test_zero_production_and_zero_employment_are_handled():
    ratios = compute_intensity_totals(
        {"total_production_tonnes": 0.0, "total_subsidy": 10.0,
         "total_gross_margin": 0.0, "total_etp": 0.0},
        {"total_azote": 5.0, "total_ift": 1.0},
        surface_ha=10.0,
    )
    assert ratios["azote_per_tonne"] is None
    assert ratios["subsidy_per_etp"] is None
    assert ratios["gross_margin_per_etp"] is None
    assert ratios["subsidy_per_euro_margin"] is None
    assert ratios["subsidy_per_ha"] == pytest.approx(1.0)


def test_missing_keys_are_treated_as_zero_rather_than_raising():
    ratios = compute_intensity_totals({}, {}, surface_ha=10.0)
    assert ratios["gross_margin_per_ha"] == pytest.approx(0.0)
    assert ratios["azote_per_tonne"] is None


def test_every_ratio_has_a_direction_declared_for_the_composite_score():
    from apps.dashboard.comparison import INDICATOR_DIRECTION

    for key in compute_intensity_totals(*_totals(), surface_ha=100.0):
        assert key in INDICATOR_DIRECTION, key
