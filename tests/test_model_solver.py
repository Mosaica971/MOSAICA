import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs
from core.model.solver import solve_model

CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_solve_model_returns_optimal_solved_model():
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
            eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        ),
        CONFIG,
    )

    solve_model(model, CONFIG)

    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.objective) == pytest.approx(200.0)


def test_solve_model_raises_on_infeasible_model():
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
        ),
        CONFIG,
    )
    model.Y["P1", "C1"].fix(1)
    model.infeasible_constraint = pyo.Constraint(expr=model.Y["P1", "C1"] == 0)

    with pytest.raises(RuntimeError, match="optimal"):
        solve_model(model, CONFIG)
