"""Unit tests for the indicator-bound family of constraints.

Data-free, like the rest of the model tests: tiny hand-built ModelInputs, no data/ read.
Two plots, two crops, rates chosen so every expected quantity is a round number.
"""

import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs

_OBJECTIVE = [{"name": "maximize_gross_margin", "enable": True, "args": {}}]


def _inputs(**overrides):
    defaults = dict(
        plot_surface_ha={"P1": 10.0, "P2": 5.0},
        crop_margin_per_ha={"INTENSIF": 100.0, "EXTENSIF": 50.0},
        eligible_pairs=[
            ("P1", "INTENSIF"),
            ("P1", "EXTENSIF"),
            ("P2", "INTENSIF"),
            ("P2", "EXTENSIF"),
        ],
        farm_plots={"E1": ["P1"], "E2": ["P2"]},
        farm_surface_ha={"E1": 10.0, "E2": 5.0},
        crop_indicator_rates={
            "azote": {"INTENSIF": 200.0, "EXTENSIF": 20.0},
            "travail": {"INTENSIF": 1000.0, "EXTENSIF": 100.0},
            "eau": {"INTENSIF": 30.0, "EXTENSIF": 10.0},
        },
        plot_zones={
            "islands": {"P1": 1, "P2": 2},
            "farms": {"P1": "E1", "P2": "E2"},
        },
        plot_weights={"irrigable": {"P1": 1.0, "P2": 0.0}},
        crop_group={"INTENSIF": "GRP_A", "EXTENSIF": "GRP_B"},
        plot_baseline_group={"P1": "GRP_A", "P2": "GRP_B"},
    )
    defaults.update(overrides)
    return ModelInputs(**defaults)


def _build(name, args, inputs=None):
    config = {
        "constraints": [{"name": name, "enable": True, "args": args}],
        "objectives": _OBJECTIVE,
    }
    return build_crop_allocation_model(inputs or _inputs(), config)


def _assign(model, *chosen):
    """Fix every Y to 0, then to 1 for the listed (plot, crop) pairs. Evaluating a
    constraint body requires EVERY variable in it to have a value, not just the ones the
    test cares about."""
    for index in model.Y:
        model.Y[index].fix(0)
    for index in chosen:
        model.Y[index].fix(1)


def _is_satisfied(constraint, tol=1e-9):
    body = pyo.value(constraint.body)
    lower, upper = constraint.lower, constraint.upper
    if lower is not None and body < pyo.value(lower) - tol:
        return False
    if upper is not None and body > pyo.value(upper) + tol:
        return False
    return True


# --- territory_indicator_bound -------------------------------------------------


def test_territory_indicator_bound_sums_surface_times_rate():
    model = _build(
        "territory_indicator_bound",
        {"label": "n_max", "indicator": "azote", "sense": "le", "threshold": 1500.0},
    )
    _assign(model, ("P1", "INTENSIF"), ("P2", "EXTENSIF"))  # 10x200 + 5x20
    assert pyo.value(model.n_max.body) == pytest.approx(2100.0)
    assert model.n_max.upper() == pytest.approx(1500.0)
    assert not _is_satisfied(model.n_max)


def test_territory_indicator_bound_scale_converts_the_unit():
    # 1/1607 turns labour hours into full-time equivalents, so the threshold is in ETP.
    model = _build(
        "territory_indicator_bound",
        {
            "label": "emploi_min",
            "indicator": "travail",
            "sense": "ge",
            "threshold": 5.0,
            "scale": 1 / 1607,
        },
    )
    _assign(model, ("P1", "INTENSIF"))  # 10 ha x 1000 h = 10 000 h = 6.22 ETP
    assert pyo.value(model.emploi_min.body) == pytest.approx(10_000 / 1607)
    assert model.emploi_min.lower() == pytest.approx(5.0)
    assert _is_satisfied(model.emploi_min)


def test_territory_indicator_bound_crops_restricts_the_scope():
    model = _build(
        "territory_indicator_bound",
        {
            "label": "n_intensif",
            "indicator": "azote",
            "sense": "le",
            "threshold": 1e9,
            "crops": ["EXTENSIF"],
        },
    )
    _assign(model, ("P1", "INTENSIF"), ("P2", "EXTENSIF"))
    # P1 x INTENSIF is outside `crops` and contributes nothing; only P2 x EXTENSIF counts.
    assert pyo.value(model.n_intensif.body) == pytest.approx(100.0)


def test_territory_indicator_bound_plot_weight_zeroes_unweighted_plots():
    # The water case: only irrigable plots draw from the resource. P2 has weight 0.
    model = _build(
        "territory_indicator_bound",
        {
            "label": "eau_max",
            "indicator": "eau",
            "sense": "le",
            "threshold": 1e9,
            "scale": 10.0,
            "plot_weight": "irrigable",
        },
    )
    _assign(model, ("P1", "INTENSIF"), ("P2", "INTENSIF"))
    # P1: 10 ha x 30 mm x 10 = 3000 m3. P2 is not irrigable (weight 0) -> nothing.
    assert pyo.value(model.eau_max.body) == pytest.approx(3000.0)


def test_territory_indicator_bound_unknown_indicator_raises():
    with pytest.raises(KeyError, match="Unknown indicator"):
        _build(
            "territory_indicator_bound",
            {"label": "x", "indicator": "phosphore", "sense": "le", "threshold": 1.0},
        )


def test_territory_indicator_bound_unknown_plot_weight_raises():
    with pytest.raises(KeyError, match="Unknown plot_weight"):
        _build(
            "territory_indicator_bound",
            {
                "label": "x",
                "indicator": "azote",
                "sense": "le",
                "threshold": 1.0,
                "plot_weight": "pente_forte",
            },
        )


def test_territory_indicator_bound_rejects_unknown_sense():
    with pytest.raises(ValueError, match="Unknown sense"):
        _build(
            "territory_indicator_bound",
            {"label": "x", "indicator": "azote", "sense": "eq", "threshold": 1.0},
        )


def test_territory_indicator_bound_empty_term_set_is_a_feasibility_verdict():
    # No crop carries the rate -> a plain 0, which must not reach Pyomo as a bare bool.
    inputs = _inputs(crop_indicator_rates={"azote": {}})
    model = _build(
        "territory_indicator_bound",
        {"label": "n_max", "indicator": "azote", "sense": "le", "threshold": 10.0},
        inputs,
    )
    assert model.n_max.expr()  # 0 <= 10 -> Constraint.Feasible


def test_territory_indicator_bound_empty_term_set_can_be_infeasible():
    inputs = _inputs(crop_indicator_rates={"travail": {}})
    model = _build(
        "territory_indicator_bound",
        {"label": "emploi", "indicator": "travail", "sense": "ge", "threshold": 10.0},
        inputs,
    )
    assert not model.emploi.expr()  # 0 >= 10 is false -> Constraint.Infeasible


# --- zone_indicator_bound ------------------------------------------------------


def test_zone_indicator_bound_holds_once_per_zone():
    model = _build(
        "zone_indicator_bound",
        {
            "label": "n_ile",
            "zone": "islands",
            "indicator": "azote",
            "sense": "le",
            "threshold": 1000.0,
        },
    )
    assert set(model.n_ile) == {1, 2}
    _assign(model, ("P1", "INTENSIF"), ("P2", "INTENSIF"))
    assert pyo.value(model.n_ile[1].body) == pytest.approx(2000.0)  # 10 x 200
    assert pyo.value(model.n_ile[2].body) == pytest.approx(1000.0)  # 5 x 200
    assert model.n_ile[1].upper() == pytest.approx(1000.0)
    # Island 1 breaches its own ceiling while island 2 sits exactly on it: the point of a
    # zoned bound is that a territory-wide total would have hidden this.
    assert not _is_satisfied(model.n_ile[1])
    assert _is_satisfied(model.n_ile[2])


def test_zone_indicator_bound_threshold_per_ha_scales_by_zone_surface():
    # The nitrates-directive form: 170 kgN per hectare of the farm, so each farm's limit
    # is its own area x 170.
    model = _build(
        "zone_indicator_bound",
        {
            "label": "nitrates",
            "zone": "farms",
            "indicator": "azote",
            "sense": "le",
            "threshold_per_ha": 170.0,
        },
    )
    assert model.nitrates["E1"].upper() == pytest.approx(1700.0)  # 10 ha
    assert model.nitrates["E2"].upper() == pytest.approx(850.0)  # 5 ha


def test_zone_indicator_bound_explicit_thresholds_limit_the_index_set():
    model = _build(
        "zone_indicator_bound",
        {
            "label": "n_ile",
            "zone": "islands",
            "indicator": "azote",
            "sense": "le",
            "thresholds": {1: 500.0},
        },
    )
    assert set(model.n_ile) == {1}  # island 2 is left unconstrained
    assert model.n_ile[1].upper() == pytest.approx(500.0)


def test_zone_indicator_bound_per_ha_counts_only_weighted_hectares():
    # P2 is not irrigable, so farm E2 has zero regulated hectares and E1 keeps its 10.
    model = _build(
        "zone_indicator_bound",
        {
            "label": "eau_ferme",
            "zone": "farms",
            "indicator": "eau",
            "sense": "le",
            "threshold_per_ha": 100.0,
            "plot_weight": "irrigable",
        },
    )
    assert model.eau_ferme["E1"].upper() == pytest.approx(1000.0)
    assert "E2" not in model.eau_ferme  # no weighted term -> zone absent entirely


def test_zone_indicator_bound_requires_a_limit():
    with pytest.raises(ValueError, match="threshold"):
        _build(
            "zone_indicator_bound",
            {"label": "x", "zone": "islands", "indicator": "azote", "sense": "le"},
        )


def test_zone_indicator_bound_unknown_zone_raises():
    with pytest.raises(KeyError, match="Unknown zone"):
        _build(
            "zone_indicator_bound",
            {
                "label": "x",
                "zone": "cantons",
                "indicator": "azote",
                "sense": "le",
                "threshold": 1.0,
            },
        )


# --- baseline_inertia_min ------------------------------------------------------


def test_baseline_inertia_min_counts_only_plots_keeping_their_group():
    model = _build("baseline_inertia_min", {"label": "inertie", "min_share": 0.5})
    # P1's baseline is GRP_A: INTENSIF keeps it. P2's is GRP_B, so INTENSIF changes it.
    _assign(model, ("P1", "INTENSIF"), ("P2", "INTENSIF"))
    # unchanged = 10 ha, allocated = 15 ha, required = 7.5 -> satisfied.
    assert _is_satisfied(model.inertie)


def test_baseline_inertia_min_binds_when_too_much_land_changes():
    model = _build("baseline_inertia_min", {"label": "inertie", "min_share": 0.8})
    _assign(model, ("P1", "EXTENSIF"), ("P2", "INTENSIF"))  # both plots change group
    # unchanged = 0 against 0.8 x 15 = 12 required.
    assert not _is_satisfied(model.inertie)


def test_baseline_inertia_min_is_a_share_of_allocated_area_not_of_the_territory():
    # Leaving land unallocated must not breach the rule: allocating P1 alone, in its own
    # baseline group, is 100% unchanged even though half the territory is idle.
    model = _build("baseline_inertia_min", {"label": "inertie", "min_share": 0.9})
    _assign(model, ("P1", "INTENSIF"))
    assert _is_satisfied(model.inertie)


def test_baseline_inertia_min_ignores_plots_without_a_baseline():
    inputs = _inputs(plot_baseline_group={"P1": "GRP_A"})
    model = _build("baseline_inertia_min", {"label": "inertie", "min_share": 0.5}, inputs)
    _assign(model, ("P2", "INTENSIF"))  # no baseline -> can never count as unchanged
    assert not _is_satisfied(model.inertie)


def test_baseline_inertia_min_rejects_a_share_outside_zero_one():
    with pytest.raises(ValueError, match="min_share"):
        _build("baseline_inertia_min", {"label": "inertie", "min_share": 1.5})
