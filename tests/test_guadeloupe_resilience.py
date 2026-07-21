import pandas as pd
import pytest

from case_studies.guadeloupe.domain import resilience


def test_climate_margin_at_risk_is_margin_times_loss_fraction():
    margin = pd.Series({"SAFE": 1000.0, "RISKY": 1000.0, "ZERO": 500.0})
    var_rdt = pd.Series({"SAFE": 0.1, "RISKY": 0.7, "ZERO": 0.0})

    at_risk = resilience.compute_climate_margin_at_risk_per_ha_cult(margin, var_rdt)

    assert at_risk["SAFE"] == pytest.approx(100.0)
    assert at_risk["RISKY"] == pytest.approx(700.0)


def test_zero_variance_crop_carries_no_climate_risk():
    """Prairies et jachere portent Var_Rdt = 0 dans les vraies donnees."""
    margin = pd.Series({"PRAIRIE": 800.0})
    var_rdt = pd.Series({"PRAIRIE": 0.0})

    at_risk = resilience.compute_climate_margin_at_risk_per_ha_cult(margin, var_rdt)

    assert at_risk["PRAIRIE"] == pytest.approx(0.0)


def test_price_shock_loss_is_delta_times_annualized_market_sales():
    # rdt 50 t/ha, prix 20 EUR/t, cycle 6 mois -> ventes annualisees 50*20/6*12 = 2000.
    rdt = pd.Series({"CROP": 50.0})
    prix = pd.Series({"CROP": 20.0})
    duree = pd.Series({"CROP": 6.0})

    loss = resilience.compute_price_shock_loss_per_ha_cult(rdt, prix, duree, 0.20)

    assert loss["CROP"] == pytest.approx(400.0)  # 20% de 2000


def test_price_shock_of_zero_loses_nothing_and_of_one_loses_all_market_sales():
    rdt = pd.Series({"CROP": 50.0})
    prix = pd.Series({"CROP": 20.0})
    duree = pd.Series({"CROP": 6.0})

    assert resilience.compute_price_shock_loss_per_ha_cult(rdt, prix, duree, 0.0)["CROP"] == 0.0
    assert resilience.compute_price_shock_loss_per_ha_cult(
        rdt, prix, duree, 1.0
    )["CROP"] == pytest.approx(2000.0)


def test_hhi_of_a_monoculture_is_one():
    assert resilience.compute_revenue_concentration_hhi(pd.Series({"A": 1000.0})) == pytest.approx(1.0)


def test_hhi_of_n_equal_crops_is_one_over_n():
    revenue = pd.Series({"A": 250.0, "B": 250.0, "C": 250.0, "D": 250.0})
    assert resilience.compute_revenue_concentration_hhi(revenue) == pytest.approx(0.25)


def test_hhi_ignores_zero_revenue_crops():
    """Une culture a revenu nul ne doit pas diluer l'indice."""
    concentrated = pd.Series({"A": 1000.0})
    padded = pd.Series({"A": 1000.0, "B": 0.0, "C": 0.0})

    assert resilience.compute_revenue_concentration_hhi(
        padded
    ) == pytest.approx(resilience.compute_revenue_concentration_hhi(concentrated))


def test_hhi_of_empty_or_zero_revenue_is_zero_not_a_division_error():
    assert resilience.compute_revenue_concentration_hhi(pd.Series(dtype=float)) == 0.0
    assert resilience.compute_revenue_concentration_hhi(pd.Series({"A": 0.0})) == 0.0


def test_default_price_shock_delta_is_twenty_percent():
    assert resilience.DEFAULT_PRICE_SHOCK_DELTA == 0.20
