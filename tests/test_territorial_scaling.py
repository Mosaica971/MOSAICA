"""Scaling territorial thresholds to a zone_filter's share of the territory. Data-free."""

import pytest

from core.config import scale_territorial_bounds


def _config():
    return {
        "constraints": [
            {"name": "territory_production_bound", "enable": True,
             "args": {"label": "pn_prod_min", "sense": "ge", "threshold": 6096.0}},
            {"name": "territory_indicator_bound", "enable": True,
             "args": {"label": "plafond_azote", "sense": "le", "threshold": 1_930_903.0}},
            {"name": "zone_indicator_bound", "enable": True,
             "args": {"label": "nitrates", "zone": "farms", "threshold_per_ha": 170.0}},
            {"name": "zone_indicator_bound", "enable": True,
             "args": {"label": "eau_bv", "zone": "watersheds", "threshold": 1000.0,
                      "thresholds": {"BV1": 400.0, "BV2": 600.0}}},
            {"name": "crop_share_bound", "enable": True,
             "args": {"label": "bio_min", "sense": "ge", "share": 0.25}},
            {"name": "farm_area_share_max", "enable": True,
             "args": {"label": "an_max", "max_share": 0.75}},
            {"name": "farm_labor_hours_max", "enable": True,
             "args": {"label": "mo", "slack": 1.5}},
            {"name": "baseline_inertia_min", "enable": True,
             "args": {"label": "inertie", "min_share": 0.7}},
        ]
    }


def _args(config, label):
    return next(
        e["args"] for e in config["constraints"] if e["args"].get("label") == label
    )


def test_absolute_territorial_thresholds_are_scaled():
    scaled = scale_territorial_bounds(_config(), 0.25)
    assert _args(scaled, "pn_prod_min")["threshold"] == pytest.approx(1524.0)
    assert _args(scaled, "plafond_azote")["threshold"] == pytest.approx(482_725.75)
    assert _args(scaled, "eau_bv")["threshold"] == pytest.approx(250.0)


def test_per_zone_threshold_dicts_are_scaled_entry_by_entry():
    scaled = scale_territorial_bounds(_config(), 0.5)
    assert _args(scaled, "eau_bv")["thresholds"] == {"BV1": 200.0, "BV2": 300.0}


def test_scale_free_arguments_are_left_alone():
    # Ratios and per-farm budgets already describe an intensity, not a quantity: scaling
    # them would change what the scenario says rather than resize it.
    scaled = scale_territorial_bounds(_config(), 0.25)
    assert _args(scaled, "nitrates")["threshold_per_ha"] == pytest.approx(170.0)
    assert _args(scaled, "bio_min")["share"] == pytest.approx(0.25)
    assert _args(scaled, "an_max")["max_share"] == pytest.approx(0.75)
    assert _args(scaled, "mo")["slack"] == pytest.approx(1.5)
    assert _args(scaled, "inertie")["min_share"] == pytest.approx(0.7)


def test_the_original_config_is_untouched():
    base = _config()
    scale_territorial_bounds(base, 0.25)
    assert _args(base, "pn_prod_min")["threshold"] == pytest.approx(6096.0)


def test_a_factor_of_one_is_a_no_op():
    assert scale_territorial_bounds(_config(), 1.0) == _config()


def test_booleans_are_not_treated_as_numbers():
    config = {"constraints": [
        {"name": "territory_production_bound", "enable": True,
         "args": {"label": "x", "threshold": True}}
    ]}
    assert scale_territorial_bounds(config, 0.5)["constraints"][0]["args"]["threshold"] is True
