import pandas as pd
import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model

CONFIG = {
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_build_model_creates_binary_variable_only_for_eligible_pairs():
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
        config=CONFIG,
    )

    assert set(model.Y.keys()) == set(eligible_pairs)
    for index in model.Y:
        assert model.Y[index].domain is pyo.Binary


def test_solving_model_picks_most_profitable_eligible_crop_per_plot():
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
        config=CONFIG,
    )

    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    assert pyo.value(model.Y["P1", "C1"]) == pytest.approx(0)
    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.Y["P2", "C1"]) == pytest.approx(1)
    assert pyo.value(model.objective) == pytest.approx(1.0 * 200.0 + 2.0 * 100.0)


def test_at_most_one_crop_per_plot_constraint_rejects_two_crops_at_once():
    eligible_pairs = [("P1", "C1"), ("P1", "C2")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
        config=CONFIG,
    )

    constraint = model.at_most_one_crop_per_plot["P1"]
    model.Y["P1", "C1"].fix(1)
    model.Y["P1", "C2"].fix(1)

    assert pyo.value(constraint.body) == pytest.approx(2)
    assert constraint.upper() == pytest.approx(1)


def test_build_model_skips_disabled_constraints():
    config = {
        "constraints": [{"name": "at_most_one_crop_per_plot", "enable": False, "args": {}}],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=config,
    )

    assert not hasattr(model, "at_most_one_crop_per_plot")


def test_build_model_raises_when_no_objective_enabled():
    config = {
        "constraints": [],
        "objectives": [{"name": "maximize_gross_margin", "enable": False, "args": {}}],
    }

    with pytest.raises(ValueError, match="exactly one enabled objective"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_build_model_raises_when_multiple_objectives_enabled():
    config = {
        "constraints": [],
        "objectives": [
            {"name": "maximize_gross_margin", "enable": True, "args": {}},
            {"name": "maximize_gross_margin", "enable": True, "args": {}},
        ],
    }

    with pytest.raises(ValueError, match="exactly one enabled objective"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_build_model_raises_for_unknown_constraint_name():
    config = {
        "constraints": [{"name": "not_a_real_constraint", "enable": True, "args": {}}],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    with pytest.raises(KeyError, match="not_a_real_constraint"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_build_model_creates_farms_set_from_farm_plots():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1"), ("P2", "C1")],
        config=CONFIG,
        farm_plots={"E1": ["P1", "P2"]},
    )

    assert set(model.FARMS) == {"E1"}


def test_build_model_defaults_to_empty_farms_set_when_farm_plots_omitted():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1")],
        config=CONFIG,
    )

    assert list(model.FARMS) == []


def test_build_model_accepts_pandas_series_for_farm_level_parameters():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1")],
        config=CONFIG,
        farm_plots={"E1": ["P1"]},
        farm_surface_ha=pd.Series({"E1": 1.0}),
        crop_yield_per_ha=pd.Series({"C1": 2.0}),
    )

    assert set(model.FARMS) == {"E1"}


def test_territory_production_bound_constraint_limits_total_yield_le_threshold():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "quota_c1",
                    "groups": [{"crops": ["C1"], "use_yield": True, "rate_multiplier": 1.0}],
                    "sense": "le",
                    "threshold": 5.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1"), ("P2", "C1")],
        config=config,
        crop_yield_per_ha={"C1": 2.0},
    )
    model.Y["P1", "C1"].fix(1)
    model.Y["P2", "C1"].fix(1)

    # 2.0ha*2.0yield + 2.0ha*2.0yield = 8.0
    assert pyo.value(model.quota_c1.body) == pytest.approx(8.0)
    assert model.quota_c1.upper() == pytest.approx(5.0)


def test_territory_production_bound_constraint_supports_area_only_groups():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "min_pasture",
                    "groups": [
                        {"crops": ["PN_PIQ"], "use_yield": False, "rate_multiplier": 1.0}
                    ],
                    "sense": "ge",
                    "threshold": 1.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 3.0},
        crop_margin_per_ha={"PN_PIQ": 10.0},
        eligible_pairs=[("P1", "PN_PIQ")],
        config=config,
    )
    model.Y["P1", "PN_PIQ"].fix(1)

    assert pyo.value(model.min_pasture.body) == pytest.approx(3.0)
    assert model.min_pasture.lower() == pytest.approx(1.0)


def test_territory_production_bound_constraint_sums_multiple_groups():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "combined",
                    "groups": [
                        {"crops": ["C1"], "use_yield": True, "rate_multiplier": 1.0},
                        {"crops": ["C2"], "use_yield": True, "rate_multiplier": 0.5},
                    ],
                    "sense": "ge",
                    "threshold": 0.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"C1": 10.0, "C2": 10.0},
        eligible_pairs=[("P1", "C1"), ("P2", "C2")],
        config=config,
        crop_yield_per_ha={"C1": 4.0, "C2": 4.0},
    )
    model.Y["P1", "C1"].fix(1)
    model.Y["P2", "C2"].fix(1)

    # group1: 1.0ha*4.0*1.0=4.0, group2: 1.0ha*4.0*0.5=2.0, total=6.0
    assert pyo.value(model.combined.body) == pytest.approx(6.0)


def test_territory_production_bound_constraint_raises_for_unknown_sense():
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "bad",
                    "groups": [{"crops": ["C1"], "use_yield": False, "rate_multiplier": 1.0}],
                    "sense": "eq",
                    "threshold": 1.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    with pytest.raises(ValueError, match="Unknown sense"):
        build_crop_allocation_model(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 10.0},
            eligible_pairs=[("P1", "C1")],
            config=config,
        )


def test_territory_production_bound_constraint_handles_no_matching_eligible_pairs():
    # Regression: sum() over zero matching pairs is a plain Python 0, not a Pyomo
    # expression. Comparing two plain numbers produces a bare bool, which Pyomo
    # rejects unless the rule explicitly returns Constraint.Feasible/.Infeasible.
    # This must not raise.
    config = {
        "constraints": [
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {
                    "label": "empty_group",
                    "groups": [{"crops": ["NOT_ELIGIBLE_ANYWHERE"], "use_yield": False, "rate_multiplier": 1.0}],
                    "sense": "ge",
                    "threshold": 0.0,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 10.0},
        eligible_pairs=[("P1", "C1")],
        config=config,
    )

    assert model.empty_group.expr()
