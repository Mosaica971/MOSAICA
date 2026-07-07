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
