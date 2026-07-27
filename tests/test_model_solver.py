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

    # Infeasible is not in the acceptable set (optimal / maxTimeLimit), so it still raises.
    with pytest.raises(RuntimeError, match="did not reach a usable solution"):
        solve_model(model, CONFIG)


def test_solve_model_routes_args_into_solver_options():
    """HiGHS options must reach solver.options, not solve()'s kwargs -- the appsi_highs
    legacy wrapper raises TypeError on an unknown solve() kwarg like mip_rel_gap, so a
    regression here would surface as a hard crash on every real run."""
    captured = {}

    class _FakeSolver:
        def __init__(self):
            self.options = {}

        def solve(self, model, **kwargs):
            captured["options"] = dict(self.options)
            captured["solve_kwargs"] = kwargs

            class _R:
                class solver:
                    termination_condition = pyo.TerminationCondition.optimal

            model.solutions = type("S", (), {"load_from": staticmethod(lambda r: None)})()
            return _R()

    original = pyo.SolverFactory
    pyo.SolverFactory = lambda name: _FakeSolver()
    try:
        config = {
            "solver": {"name": "appsi_highs", "args": {"mip_rel_gap": 0.01, "time_limit": 3600}},
        }
        solve_model(pyo.ConcreteModel(), config)
    finally:
        pyo.SolverFactory = original

    assert captured["options"] == {"mip_rel_gap": 0.01, "time_limit": 3600}
    # Only load_solutions may ride along on solve(); options must not leak there.
    assert "mip_rel_gap" not in captured["solve_kwargs"]
    assert captured["solve_kwargs"].get("load_solutions") is False
