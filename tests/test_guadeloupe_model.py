import pandas as pd
import pyomo.environ as pyo
import pytest

from case_studies.guadeloupe.model import build_model
from core.data.dataset import Dataset


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

    model = build_model(dataset)

    assert set(model.Y.keys()) == {("P1", "C1"), ("P1", "C2"), ("P2", "C1")}

    solver = pyo.SolverFactory("appsi_highs")
    solver.solve(model)

    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)
    assert pyo.value(model.Y["P2", "C1"]) == pytest.approx(1)
