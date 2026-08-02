import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe.model import constraints as _guadeloupe_constraints  # noqa: F401
from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs
from core.solve.solver import solve_model


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
        ModelInputs(
            plot_surface_ha={"P1": 10.0, "P2": 4.0},
            crop_margin_per_ha={"CS": 50.0, "OTHER": 100.0},
            eligible_pairs=[("P1", "CS"), ("P1", "OTHER"), ("P2", "CS")],
            farm_plots={"E1": ["P1"], "E2": ["P2"]},
            farm_restricted_surface_ha={"E1": 10.0},
        ),
        config,
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
        ModelInputs(
            plot_surface_ha={"P1": 4.0},
            crop_margin_per_ha={"OTHER": 50.0},
            eligible_pairs=[("P1", "OTHER")],
            farm_plots={"E1": ["P1"]},
            farm_restricted_surface_ha={"E1": 4.0},
        ),
        config,
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
        ModelInputs(
            plot_surface_ha={"P1": 10.0, "P2": 10.0},
            crop_margin_per_ha={"MA_PLBIO": 100.0, "MA_ROTA": 100.0},
            eligible_pairs=[
            ("P1", "MA_PLBIO"),
            ("P1", "MA_ROTA"),
            ("P2", "MA_PLBIO"),
            ("P2", "MA_ROTA"),
        ],
            farm_plots={"E1": ["P1", "P2"]},
            farm_restricted_surface_ha={},
        ),
        config,
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
        ModelInputs(
            plot_surface_ha={"P1": 5.0},
            crop_margin_per_ha={"MA_PLBIO": 50.0},
            eligible_pairs=[("P1", "MA_PLBIO")],  # neither BA_INT nor MA_ROTA eligible
            farm_plots={"E1": ["P1"]},
            farm_restricted_surface_ha={},
        ),
        config,
    )
    assert model.intensif_cap is not None  # built via guard (Constraint.Feasible)


def _labor_inputs(**overrides) -> ModelInputs:
    """Two farms of two plots each, one cheap crop (cane-like) and one costly one
    (market-gardening-like), so the labour cap alone decides what is reachable."""
    base = dict(
        plot_surface_ha={"P1": 10.0, "P2": 10.0, "P3": 10.0, "P4": 10.0},
        crop_margin_per_ha={"CHEAP": 100.0, "COSTLY": 1000.0},
        eligible_pairs=[
            (plot, crop)
            for plot in ("P1", "P2", "P3", "P4")
            for crop in ("CHEAP", "COSTLY")
        ],
        farm_plots={"E1": ["P1", "P2"], "E2": ["P3", "P4"]},
        crop_labor_hours_per_ha={"CHEAP": 10.0, "COSTLY": 1000.0},
        # E1 observed cheap crops on both plots: 2 x 10 ha x 10 h = 200 h.
        # E2 observed the costly one: 2 x 10 ha x 1000 h = 20 000 h.
        farm_labor_capacity_hours={"E1": 200.0, "E2": 20000.0},
    )
    base.update(overrides)
    return ModelInputs(**base)


_LABOR_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [
        {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
        {"name": "farm_labor_hours_max", "enable": True, "args": {"label": "mo_max"}},
    ],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_farm_labor_hours_max_confines_a_farm_to_its_observed_workload():
    model = build_crop_allocation_model(_labor_inputs(), _LABOR_CONFIG)
    solve_model(model, _LABOR_CONFIG)

    chosen = {
        plot: crop for plot, crop in model.PAIRS if pyo.value(model.Y[plot, crop]) > 0.5
    }
    # E1's 200 h budget buys the cheap crop on both plots (200 h) but not one hectare-year
    # of the costly one (10 000 h): without the cap, margin alone would pick COSTLY.
    assert chosen.get("P1") == "CHEAP"
    assert chosen.get("P2") == "CHEAP"
    # E2 observed the costly crop, so it keeps the budget to grow it.
    assert chosen.get("P3") == "COSTLY"
    assert chosen.get("P4") == "COSTLY"


def test_farm_labor_hours_max_slack_relaxes_the_cap():
    # GAMS keeps scenario multipliers commented right under the formula
    # (ENTREES.txt:470-472: "x 1.7 pour S1, x 1.3 pour S2, x 10 pour S3").
    config = {
        **_LABOR_CONFIG,
        "constraints": [
            {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
            {
                "name": "farm_labor_hours_max",
                "enable": True,
                "args": {"label": "mo_max", "slack": 100.0},
            },
        ],
    }
    model = build_crop_allocation_model(_labor_inputs(), config)
    solve_model(model, config)

    chosen = {
        plot: crop for plot, crop in model.PAIRS if pyo.value(model.Y[plot, crop]) > 0.5
    }
    # 200 h x 100 = 20 000 h, enough for the costly crop on both of E1's plots.
    assert chosen.get("P1") == "COSTLY"
    assert chosen.get("P2") == "COSTLY"


def test_farm_labor_hours_max_is_skipped_for_a_farm_with_no_capacity_entry():
    """A farm absent from the capacity mapping is not constrained, rather than being
    silently frozen at zero -- the mapping is optional, like every ModelInputs field."""
    inputs = _labor_inputs(farm_labor_capacity_hours={"E1": 200.0})
    model = build_crop_allocation_model(inputs, _LABOR_CONFIG)
    solve_model(model, _LABOR_CONFIG)

    chosen = {
        plot: crop for plot, crop in model.PAIRS if pyo.value(model.Y[plot, crop]) > 0.5
    }
    assert chosen.get("P3") == "COSTLY"
    assert chosen.get("P4") == "COSTLY"


def test_farm_labor_hours_max_without_rates_constrains_nothing():
    inputs = _labor_inputs(crop_labor_hours_per_ha={})
    model = build_crop_allocation_model(inputs, _LABOR_CONFIG)
    solve_model(model, _LABOR_CONFIG)

    chosen = {
        plot: crop for plot, crop in model.PAIRS if pyo.value(model.Y[plot, crop]) > 0.5
    }
    assert set(chosen.values()) == {"COSTLY"}


def _gfa_inputs_with_no_eligible_cane() -> ModelInputs:
    """A GFA farm whose only plot cannot carry sugarcane -- the real E1471/E273/E3955 shape,
    where friche_lock forbids CS on every plot the farm owns."""
    return ModelInputs(
        plot_surface_ha={"P1": 10.0},
        crop_margin_per_ha={"JA": 50.0},
        eligible_pairs=[("P1", "JA")],  # no CS pair at all
        farm_plots={"E1": ["P1"]},
        farm_surface_ha={"E1": 10.0},
        farm_restricted_surface_ha={"E1": 10.0},
    )


def _gfa_config(**args) -> dict:
    return {
        "solver": {"name": "appsi_highs", "args": {}},
        "constraints": [
            {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
            {
                "name": "cs_gfa_minimum_share",
                "enable": True,
                "args": {"label": "cs_gfa", "crops": ["CS_NGT_NISM"], "min_share": 0.6, **args},
            },
        ],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    }


def test_cs_gfa_stays_infeasible_by_default_for_a_farm_with_no_eligible_cane():
    # Faithful GAMS behaviour: the equation really is unsatisfiable for such a farm, and
    # solve_model turns a non-optimal termination into a loud RuntimeError.
    model = build_crop_allocation_model(_gfa_inputs_with_no_eligible_cane(), _gfa_config())

    with pytest.raises(RuntimeError, match="did not reach a usable solution"):
        solve_model(model, _gfa_config())


def test_cs_gfa_skips_that_farm_when_the_deviation_flag_is_on():
    config = _gfa_config(skip_when_no_eligible_area=True)
    model = build_crop_allocation_model(_gfa_inputs_with_no_eligible_cane(), config)
    results = solve_model(model, config)

    assert "optimal" in str(results.solver.termination_condition).lower()
    chosen = {plot: crop for plot, crop in model.PAIRS if pyo.value(model.Y[plot, crop]) > 0.5}
    assert chosen == {"P1": "JA"}
