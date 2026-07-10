import json

import pandas as pd
import pytest

from case_studies.guadeloupe.reporting import report
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model
from core.model.solver import solve_model

_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def _tiny_dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0],
            "REGION": ["R1", "R1"],
            "ILE": [1, 1],
            "cult_2016": [6, 6],
            "cult_2017": [6, 6],
        },
        index=["P1", "P2"],
    )
    expl_parc = pd.DataFrame({"farm": ["E1", "E1"], "plot": ["P1", "P2"]})
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "rdt_cult": pd.Series({"CS": 80.0, "ME": 20.0}),
            "sales_per_ha_cult": pd.Series({"CS": 3000.0, "ME": 5000.0}),
            "subsidy_per_ha_cult_annualized": pd.Series({"CS": 500.0, "ME": 200.0}),
        },
        scalars={},
    )


def test_generate_report_writes_full_output_folder(tmp_path):
    dataset = _tiny_dataset()
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0, "P2": 3.0},
        crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
        eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        config=_CONFIG,
    )
    results = solve_model(model, _CONFIG)

    output_dir = report.generate_report(
        dataset, _CONFIG, model, results, duration=1.23, outputs_root=tmp_path
    )

    assert output_dir == tmp_path / "output_1"
    assert (output_dir / "recap.json").exists()
    assert (output_dir / "recap.md").exists()
    assert (output_dir / "config_used.yaml").exists()
    assert (output_dir / "allocation_input.csv").exists()
    assert (output_dir / "allocation_output.csv").exists()
    assert (output_dir / "plots" / "production_by_crop.png").exists()
    assert (output_dir / "plots" / "subsidy_by_crop.png").exists()
    assert (output_dir / "plots" / "revenue_by_crop.png").exists()

    recap = json.loads((output_dir / "recap.json").read_text())
    assert recap["solve_duration_seconds"] == pytest.approx(1.23)
    assert recap["objective"]["name"] == "maximize_gross_margin"
    assert recap["constraints"] == [{"name": "at_most_one_crop_per_plot", "args": {}}]
    assert recap["total_plots"] == 2
    assert recap["total_farms"] == 1
