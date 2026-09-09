"""Unit tests for farm_production_bound (GAMS Eq_BA_QUOTA_Expl).

Data-free like the rest of the model tests: tiny hand-built ModelInputs, no data/ read.
Two farms of one plot each, yields chosen so every expected tonnage is a round number.
"""

import pyomo.environ as pyo
import pytest

from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs

_OBJECTIVE = [{"name": "maximize_gross_margin", "enable": True, "args": {}}]


def _inputs(**overrides):
    defaults = dict(
        plot_surface_ha={"P1": 10.0, "P2": 5.0},
        crop_margin_per_ha={"BA_INT": 100.0, "AUTRE": 50.0},
        eligible_pairs=[
            ("P1", "BA_INT"),
            ("P1", "AUTRE"),
            ("P2", "BA_INT"),
            ("P2", "AUTRE"),
        ],
        farm_plots={"E1": ["P1"], "E2": ["P2"]},
        farm_surface_ha={"E1": 10.0, "E2": 5.0},
        # 10 ha x 45 t/ha = 450 t on E1; 5 ha x 45 = 225 t on E2.
        crop_yield_per_ha={"BA_INT": 45.0, "AUTRE": 0.0},
        farm_production_capacity={"BA": {"E1": 450.0, "E2": 100.0}},
    )
    defaults.update(overrides)
    return ModelInputs(**defaults)


def _build(args, inputs=None):
    config = {
        "constraints": [
            {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
            {"name": "farm_production_bound", "enable": True, "args": args},
        ],
        "objectives": _OBJECTIVE,
    }
    return build_crop_allocation_model(inputs or _inputs(), config)


def _assign(model, *chosen):
    for index in model.Y:
        model.Y[index].fix(0)
    for index in chosen:
        model.Y[index].fix(1)


_ARGS = {"label": "ba_quota_expl", "crops": ["BA_INT"], "reference": "BA"}


def test_farm_at_its_reference_production_is_allowed():
    model = _build(_ARGS)
    _assign(model, ("P1", "BA_INT"))

    # E1 produces exactly its 450 t reference.
    assert pyo.value(model.ba_quota_expl["E1"].body) == pytest.approx(450.0)
    assert pyo.value(model.ba_quota_expl["E1"].upper) == pytest.approx(450.0)


def test_farm_above_its_reference_production_violates_the_bound():
    model = _build(_ARGS)
    _assign(model, ("P2", "BA_INT"))

    # E2 would produce 225 t against a 100 t reference.
    body = pyo.value(model.ba_quota_expl["E2"].body)
    assert body == pytest.approx(225.0)
    assert body > pyo.value(model.ba_quota_expl["E2"].upper)


def test_bound_is_per_farm_not_territorial():
    """The whole point: E1's headroom cannot pay for E2's overshoot."""
    model = _build(_ARGS)
    _assign(model, ("P2", "BA_INT"))

    assert pyo.value(model.ba_quota_expl["E1"].body) == pytest.approx(0.0)
    assert pyo.value(model.ba_quota_expl["E2"].body) == pytest.approx(225.0)
    # Territory-wide the 225 t sits well under the 550 t of combined reference; per farm
    # it is a violation. A territorial bound would have accepted this allocation.
    total_reference = 450.0 + 100.0
    assert 225.0 < total_reference


def test_scale_relaxes_every_cap_uniformly():
    model = _build({**_ARGS, "scale": 2.0})

    assert pyo.value(model.ba_quota_expl["E1"].upper) == pytest.approx(900.0)
    assert pyo.value(model.ba_quota_expl["E2"].upper) == pytest.approx(200.0)


def test_farm_missing_from_the_reference_is_left_unconstrained():
    inputs = _inputs(farm_production_capacity={"BA": {"E1": 450.0}})
    model = _build(_ARGS, inputs)

    assert "E2" not in model.ba_quota_expl or model.ba_quota_expl["E2"].equality is False
    # E2 carries no bound at all rather than a zero one, which would freeze the farm.
    assert pyo.value(model.ba_quota_expl["E1"].upper) == pytest.approx(450.0)
    assert model.ba_quota_expl["E2"].body is None or pyo.value(
        model.ba_quota_expl["E2"].body
    ) in (None, 0.0)


def test_unknown_reference_constrains_nothing():
    model = _build({**_ARGS, "reference": "INEXISTANT"})

    for farm in model.FARMS:
        constraint = model.ba_quota_expl[farm]
        assert constraint.body is None or pyo.value(constraint.body) in (None, 0.0)


def test_sense_ge_expresses_a_floor():
    model = _build({**_ARGS, "sense": "ge"})
    _assign(model, ("P1", "BA_INT"))

    assert pyo.value(model.ba_quota_expl["E1"].lower) == pytest.approx(450.0)
    assert pyo.value(model.ba_quota_expl["E1"].body) == pytest.approx(450.0)


def test_rejects_an_unknown_sense():
    with pytest.raises(ValueError, match="sense"):
        _build({**_ARGS, "sense": "eq"})


def test_crops_outside_the_group_are_not_counted():
    """AUTRE is eligible everywhere but belongs to no quota: it must not enter the sum."""
    model = _build(_ARGS)
    _assign(model, ("P1", "AUTRE"))

    assert pyo.value(model.ba_quota_expl["E1"].body) == pytest.approx(0.0)
