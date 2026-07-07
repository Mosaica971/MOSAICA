import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model


def test_build_model_creates_binary_variable_only_for_eligible_pairs():
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 2.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=eligible_pairs,
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
    )

    constraint = model.at_most_one_crop_per_plot["P1"]
    model.Y["P1", "C1"].fix(1)
    model.Y["P1", "C2"].fix(1)

    assert pyo.value(constraint.body) == pytest.approx(2)
    assert constraint.upper() == pytest.approx(1)
