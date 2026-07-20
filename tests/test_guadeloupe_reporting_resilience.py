import pandas as pd
import pytest

from core.data.dataset import Dataset
from case_studies.guadeloupe.reporting import indicators


def _dataset() -> Dataset:
    """Deux parcelles, deux cultures. SAFE ne risque rien, RISKY perd 50%."""
    data_parc = pd.DataFrame({"SURF_HA": [2.0, 3.0]}, index=["P1", "P2"])
    parameters = {
        "data_parc": data_parc,
        "margin_per_ha_cult": pd.Series({"SAFE": 100.0, "RISKY": 200.0}),
        "crop_variance_per_ha": pd.Series({"SAFE": 0.0, "RISKY": 0.5}),
        "rdt_cult": pd.Series({"SAFE": 10.0, "RISKY": 20.0}),
        "prix_cult": pd.Series({"SAFE": 6.0, "RISKY": 6.0}),
        "duree_cycle_cult": pd.Series({"SAFE": 12.0, "RISKY": 12.0}),
        "sales_per_ha_cult": pd.Series({"SAFE": 60.0, "RISKY": 120.0}),
        "subsidy_per_ha_cult_annualized": pd.Series({"SAFE": 40.0, "RISKY": 80.0}),
    }
    return Dataset(sets={}, parameters=parameters, scalars={})


def _allocation() -> pd.Series:
    return pd.Series(["SAFE", "RISKY"], index=["P1", "P2"])


def test_climate_margin_at_risk_weights_by_surface():
    totals = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    # P1: 2 ha x 100 EUR x 0.0 = 0. P2: 3 ha x 200 EUR x 0.5 = 300.
    assert totals["climate_margin_at_risk"] == pytest.approx(300.0)


def test_climate_ratio_is_relative_to_total_margin():
    totals = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    # Marge totale: 2 x 100 + 3 x 200 = 800. Ratio 300 / 800.
    assert totals["climate_margin_at_risk_ratio"] == pytest.approx(0.375)


def test_price_shock_loss_scales_with_delta():
    # Ventes marche annualisees: SAFE 10*6/12*12 = 60/ha, RISKY 20*6/12*12 = 120/ha.
    # Surface: 2 x 60 + 3 x 120 = 480. A delta 0.20 -> 96.
    at_20 = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    at_40 = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.40)

    assert at_20["price_shock_margin_loss"] == pytest.approx(96.0)
    assert at_40["price_shock_margin_loss"] == pytest.approx(192.0)
    assert at_20["price_shock_margin_loss_ratio"] == pytest.approx(96.0 / 800.0)


def test_revenue_concentration_uses_revenue_not_margin():
    totals = indicators.compute_resilience_totals(_dataset(), _allocation(), 0.20)
    # Revenu = ventes + subvention. P1: 2 x (60+40) = 200. P2: 3 x (120+80) = 600.
    # Total 800, parts 0.25 et 0.75 -> HHI = 0.0625 + 0.5625 = 0.625.
    assert totals["revenue_concentration_hhi"] == pytest.approx(0.625)


def test_empty_allocation_yields_zeros_not_errors():
    totals = indicators.compute_resilience_totals(_dataset(), pd.Series(dtype=object), 0.20)
    for key, value in totals.items():
        assert value == 0.0, f"{key} devrait etre 0 sur une allocation vide"
