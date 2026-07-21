from pathlib import Path

import pandas as pd
import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe.model.model import build_model
from core.data.dataset import Dataset

CONFIG = {
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def _fake_dataset() -> Dataset:
    data_parc = pd.DataFrame({"SURF_HA": [1.0, 2.0]}, index=["P1", "P2"])
    margin_per_ha_cult = pd.Series({"C1": 100.0, "C2": 200.0})
    eligible_pairs = [("P1", "C1"), ("P1", "C2"), ("P2", "C1")]

    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "margin_per_ha_cult": margin_per_ha_cult,
            "eligible_pairs": eligible_pairs,
        },
        scalars={},
    )


def test_build_model_wires_dataset_into_crop_allocation_model():
    dataset = _fake_dataset()

    model = build_model(dataset, CONFIG)

    assert set(model.Y.keys()) == {("P1", "C1"), ("P1", "C2"), ("P2", "C1")}

    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.Y["P2", "C1"]) == pytest.approx(1)


def test_build_model_wires_farm_level_parameters_into_farms_set():
    dataset = _fake_dataset()
    dataset.parameters["farm_plots"] = {"E1": ["P1", "P2"]}
    dataset.parameters["farm_surface_ha"] = pd.Series({"E1": 3.0})

    model = build_model(dataset, CONFIG)

    assert set(model.FARMS) == {"E1"}


def test_build_model_from_real_dataset_creates_every_labeled_phase1_constraint():
    from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
    from core.config import load_config

    config = load_config(
        Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
    )
    dataset = build_dataset(config)

    model = build_model(dataset, config)

    for label in [
        "an_agro_max_expl", "ig_agro_max_expl",
        "ba_ja", "ba_rota",
        "ba_quota_max", "cs_quota_max",
        "bc_prod_min", "ig_prod_min", "ma_prod_min", "an_prod_min",
        "plu_prod_min", "me_prod_min", "pn_prod_min",
        "leg_prod_obj", "fru_prod_obj", "pat_surf_obj",
        # Calibration anchors, enabled 2026-07-21. cs_gfa carries
        # skip_when_no_eligible_area, without which 3 real GFA farms whose plots are all
        # fallow-locked make the whole solve infeasible.
        "cs_gfa", "mo_max_expl",
    ]:
        assert hasattr(model, label), f"expected constraint '{label}' to be built"

    for disabled_label in [
        "me_quota_max", "an_quota_max", "ig_quota_max", "bc_quota_max", "tub_prod_obj",
    ]:
        assert not hasattr(model, disabled_label)


def test_build_model_supports_enabling_risk_adjusted_objective():
    dataset = _fake_dataset()
    dataset.parameters["farm_plots"] = {"E1": ["P1"]}
    dataset.parameters["crop_variance_per_ha"] = pd.Series({"C1": 0.0, "C2": 1.0})
    dataset.parameters["farm_risk_aversion"] = pd.Series({"E1": 1.5})
    # Restrict to P1's two crops so the choice between them is unambiguous.
    dataset.parameters["eligible_pairs"] = [("P1", "C1"), ("P1", "C2")]

    config = {
        "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
        "objectives": [
            {"name": "maximize_gross_margin", "enable": False, "args": {}},
            {"name": "maximize_risk_adjusted_gross_margin", "enable": True, "args": {}},
        ],
    }

    model = build_model(dataset, config)
    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    # Plain gross margin would prefer C2 (200/ha over C1's 100/ha). Wiring
    # farm_risk_aversion=1.5 and crop_variance_per_ha[C2]=1.0 through model.py
    # makes C2's risk-adjusted value negative (200*(1-1.5*1.0)=-100), flipping
    # the optimal choice to C1. This fails if model.py's two passthrough lines
    # (crop_variance_per_ha=..., farm_risk_aversion=...) are ever dropped.
    assert pyo.value(model.Y["P1", "C1"]) == pytest.approx(1)
    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(0)
