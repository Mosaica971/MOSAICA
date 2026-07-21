import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe.model import constraints as _guadeloupe_constraints  # noqa: F401
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


def _is_satisfied(constraint, tol=1e-9):
    """True when the constraint holds at the current variable values, whichever way Pyomo
    canonicalised body/lower/upper."""
    body = pyo.value(constraint.body)
    lower, upper = constraint.lower, constraint.upper
    if lower is not None and body < pyo.value(lower) - tol:
        return False
    if upper is not None and body > pyo.value(upper) + tol:
        return False
    return True


def test_crop_share_bound_ge_enforces_minimum_bio_share():
    config = {
        "constraints": [
            {
                "name": "crop_share_bound",
                "enable": True,
                "args": {
                    "label": "bio_min",
                    "numerator_crops": ["MA_PLBIO"],
                    "denominator_crops": ["MA_PLBIO", "MA_ROTA"],
                    "sense": "ge",
                    "share": 0.3,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 10.0, "P2": 10.0},
        crop_margin_per_ha={"MA_PLBIO": 100.0, "MA_ROTA": 100.0},
        eligible_pairs=[
            ("P1", "MA_PLBIO"),
            ("P1", "MA_ROTA"),
            ("P2", "MA_PLBIO"),
            ("P2", "MA_ROTA"),
        ],
        config=config,
        farm_plots={"E1": ["P1", "P2"]},
        farm_gfa_surface_ha={},
    )
    # P1 bio (10 ha), P2 non-bio (10 ha) -> bio area 10, total 20.
    model.Y["P1", "MA_PLBIO"].fix(1)
    model.Y["P1", "MA_ROTA"].fix(0)
    model.Y["P2", "MA_PLBIO"].fix(0)
    model.Y["P2", "MA_ROTA"].fix(1)
    # Assert on satisfaction, not on Pyomo's internal canonicalisation of the sides.
    assert _is_satisfied(model.bio_min)  # bio share 10/20 = 50% >= 30%

    # Drop bio to 0% of the filiere -> the same constraint must now be violated.
    model.Y["P1", "MA_PLBIO"].fix(0)
    model.Y["P1", "MA_ROTA"].fix(1)
    assert not _is_satisfied(model.bio_min)


def test_crop_share_bound_empty_terms_are_guarded():
    config = {
        "constraints": [
            {
                "name": "crop_share_bound",
                "enable": True,
                "args": {
                    "label": "intensif_cap",
                    "numerator_crops": ["BA_INT"],
                    "denominator_crops": ["MA_ROTA"],
                    "sense": "le",
                    "share": 0.2,
                },
            }
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 5.0},
        crop_margin_per_ha={"MA_PLBIO": 50.0},
        eligible_pairs=[("P1", "MA_PLBIO")],  # neither BA_INT nor MA_ROTA eligible
        config=config,
        farm_plots={"E1": ["P1"]},
        farm_gfa_surface_ha={},
    )
    assert model.intensif_cap is not None  # built via guard (Constraint.Feasible)
