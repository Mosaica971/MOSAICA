"""Shadow prices from the linear relaxation. Tiny hand-built model, no data/."""

import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs
from core.solve.shadow_prices import by_label, compute_shadow_prices


def _config(threshold: float):
    return {
        "solver": {"name": "appsi_highs", "args": {"mip_rel_gap": 0.0}},
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
        "constraints": [
            {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
            {
                "name": "territory_indicator_bound",
                "enable": True,
                "args": {"label": "plafond_azote", "indicator": "azote",
                         "sense": "le", "threshold": threshold},
            },
        ],
    }


def _model(threshold: float):
    inputs = ModelInputs(
        # Two plots of 1 ha. RICHE earns 100/ha but costs 10 kg N; PAUVRE earns 10 and
        # costs nothing. With nitrogen scarce, the last kilogram is worth (100-10)/10 = 9.
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"RICHE": 100.0, "PAUVRE": 10.0},
        eligible_pairs=[("P1", "RICHE"), ("P1", "PAUVRE"), ("P2", "RICHE"), ("P2", "PAUVRE")],
        crop_indicator_rates={"azote": {"RICHE": 10.0, "PAUVRE": 0.0}},
    )
    return build_crop_allocation_model(inputs, _config(threshold))


def test_a_binding_ceiling_gets_a_positive_dual():
    model = _model(10.0)  # room for one RICHE plot only
    prices = compute_shadow_prices(model, _config(10.0))
    assert "plafond_azote" in prices
    price = prices["plafond_azote"]
    assert price.binding
    # Swapping one plot from PAUVRE to RICHE gains 90 EUR for 10 kg N -> 9 EUR/kg.
    assert abs(price.dual) == pytest.approx(9.0, rel=1e-6)


def test_a_slack_ceiling_prices_at_zero():
    model = _model(1000.0)  # far more nitrogen than the two plots can use
    prices = compute_shadow_prices(model, _config(1000.0))
    assert prices["plafond_azote"].dual == pytest.approx(0.0)
    assert not prices["plafond_azote"].binding


def test_the_model_is_restored_after_the_relaxation():
    # The run keeps using this model for reporting, so the diagnostic must leave no trace.
    model = _model(10.0)
    for var in model.Y.values():
        var.set_value(0.0)
    model.Y["P1", "RICHE"].set_value(1.0)

    compute_shadow_prices(model, _config(10.0))

    for var in model.Y.values():
        assert var.domain is pyo.Binary
        assert not var.fixed
    assert model.Y["P1", "RICHE"].value == pytest.approx(1.0)


def test_by_label_keeps_only_the_constraints_a_scenario_names():
    model = _model(10.0)
    config = _config(10.0)
    summary = by_label(compute_shadow_prices(model, config), config)
    assert set(summary) == {"plafond_azote"}
    assert summary["plafond_azote"]["members"] == 1
    assert summary["plafond_azote"]["is_binding"]


def test_by_label_aggregates_an_indexed_constraint():
    """A per-farm rule produces one constraint per farm; the label must summarise them."""
    inputs = ModelInputs(
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"RICHE": 100.0, "PAUVRE": 10.0},
        eligible_pairs=[("P1", "RICHE"), ("P1", "PAUVRE"), ("P2", "RICHE"), ("P2", "PAUVRE")],
        farm_plots={"E1": ["P1"], "E2": ["P2"]},
        crop_indicator_rates={"azote": {"RICHE": 10.0, "PAUVRE": 0.0}},
        plot_zones={"farms": {"P1": "E1", "P2": "E2"}},
    )
    config = {
        "solver": {"name": "appsi_highs", "args": {}},
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
        "constraints": [
            {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
            {"name": "zone_indicator_bound", "enable": True,
             "args": {"label": "nitrates", "zone": "farms", "indicator": "azote",
                      "sense": "le", "threshold": 5.0}},
        ],
    }
    model = build_crop_allocation_model(inputs, config)
    summary = by_label(compute_shadow_prices(model, config), config)
    assert summary["nitrates"]["members"] == 2
    assert summary["nitrates"]["binding"] == 2


def test_a_failure_returns_no_prices_rather_than_raising():
    model = _model(10.0)
    broken = dict(_config(10.0))
    broken["solver"] = {"name": "no_such_solver", "args": {}}
    assert compute_shadow_prices(model, broken) == {}
