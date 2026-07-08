import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe import constraints as _guadeloupe_constraints  # noqa: F401
from core.model.builder import build_crop_allocation_model


def test_cs_gfa_minimum_share_constraint_only_applies_to_farms_with_gfa_surface():
    config = {
        "constraints": [
            {
                "name": "cs_gfa_minimum_share",
                "enable": True,
                "args": {"label": "cs_gfa", "crops": ["CS"], "min_share": 0.6},
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 10.0, "P2": 4.0},
        crop_margin_per_ha={"CS": 50.0, "OTHER": 100.0},
        eligible_pairs=[("P1", "CS"), ("P1", "OTHER"), ("P2", "CS")],
        config=config,
        farm_plots={"E1": ["P1"], "E2": ["P2"]},
        farm_gfa_surface_ha={"E1": 10.0},
    )
    model.Y["P1", "CS"].fix(1)

    assert pyo.value(model.cs_gfa["E1"].body) == pytest.approx(10.0)
    assert model.cs_gfa["E1"].lower() == pytest.approx(6.0)
    assert "E2" not in model.cs_gfa


def test_cs_gfa_minimum_share_constraint_handles_gfa_farm_with_no_eligible_cs_plots():
    # Regression: a GFA farm with zero CS-eligible plots sums to a plain 0, not a
    # Pyomo expression -- must resolve via Constraint.Infeasible, not crash (see
    # territory_production_bound's note in core/model/constraints.py).
    config = {
        "constraints": [
            {
                "name": "cs_gfa_minimum_share",
                "enable": True,
                "args": {"label": "cs_gfa", "crops": ["CS"], "min_share": 0.6},
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }

    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 4.0},
        crop_margin_per_ha={"OTHER": 50.0},
        eligible_pairs=[("P1", "OTHER")],
        config=config,
        farm_plots={"E1": ["P1"]},
        farm_gfa_surface_ha={"E1": 4.0},
    )

    # 0.6 * 4.0ha = 2.4ha required, but 0ha CS-eligible -- genuinely infeasible,
    # matching GAMS's algebraic infeasibility for the same equation.
    assert not model.cs_gfa["E1"].expr()
