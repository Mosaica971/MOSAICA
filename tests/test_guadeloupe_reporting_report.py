import json

import pandas as pd
import pytest
import yaml

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
            "labor_hours_per_ha_cult": pd.Series({"CS": 400.0, "ME": 800.0}),
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
    for side in ("input", "output"):
        assert (output_dir / "plots" / f"production_by_crop_{side}.png").exists()
        assert (output_dir / "plots" / f"subsidy_by_crop_{side}.png").exists()
        assert (output_dir / "plots" / f"revenue_by_crop_{side}.png").exists()
        assert (output_dir / "plots" / f"surface_by_region_{side}.png").exists()

    recap = json.loads((output_dir / "recap.json").read_text())
    assert recap["solve_duration_seconds"] == pytest.approx(1.23)
    assert recap["objective"]["name"] == "maximize_gross_margin"
    assert recap["constraints"] == [{"name": "at_most_one_crop_per_plot", "args": {}}]
    assert recap["total_plots"] == 2
    assert recap["total_farms"] == 1

    assert isinstance(recap["timestamp"], str) and recap["timestamp"]
    assert isinstance(recap["termination_condition"], str) and recap["termination_condition"]
    assert "optimal" in recap["termination_condition"].lower()
    assert recap["solver"] == {"name": "appsi_highs", "args": {}}

    expected_summary_keys = {"total_surface_ha", "active_plot_count", "farm_count"}
    for key in ("input", "output", "delta"):
        summary = recap[key]
        assert set(summary.keys()) == expected_summary_keys
        for value in summary.values():
            assert isinstance(value, (int, float))

    allocation_output = pd.read_csv(output_dir / "allocation_output.csv")
    assert list(allocation_output.columns) == [
        "plot",
        "crop",
        "farm",
        "region",
        "island",
        "surface_ha",
    ]
    assert len(allocation_output) == 2
    assert set(allocation_output["plot"]) == {"P1", "P2"}

    recap_md = (output_dir / "recap.md").read_text()
    assert recap_md
    assert "maximize_gross_margin" in recap_md

    config_used = yaml.safe_load((output_dir / "config_used.yaml").read_text())
    assert config_used == _CONFIG


def test_generate_report_writes_additional_indicators(tmp_path):
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

    for name in (
        "subsidy_per_tonne_by_crop.csv",
        "subsidy_per_euro_sold_by_crop.csv",
        "revenue_by_farm.csv",
        "production_by_crop_input.csv",
        "production_by_crop_output.csv",
        "subsidy_by_crop_input.csv",
        "subsidy_by_crop_output.csv",
        "revenue_by_crop_input.csv",
        "revenue_by_crop_output.csv",
        "etp_by_region_input.csv",
        "etp_by_region_output.csv",
        "etp_by_island_input.csv",
        "etp_by_island_output.csv",
        "etp_by_farm_input.csv",
        "etp_by_farm_output.csv",
        "shannon_diversity_by_region_input.csv",
        "shannon_diversity_by_region_output.csv",
        "shannon_diversity_by_island_input.csv",
        "shannon_diversity_by_island_output.csv",
        "surface_by_region_input.csv",
        "surface_by_region_output.csv",
        "surface_by_island_input.csv",
        "surface_by_island_output.csv",
    ):
        assert (output_dir / name).exists(), name
    assert (output_dir / "plots" / "etp_by_region_output.png").exists()
    assert (output_dir / "plots" / "etp_by_region_input.png").exists()

    revenue_by_farm = pd.read_csv(output_dir / "revenue_by_farm.csv")
    assert list(revenue_by_farm.columns) == ["farm", "revenue"]
    assert set(revenue_by_farm["farm"]) == {"E1"}

    recap = json.loads((output_dir / "recap.json").read_text())
    assert isinstance(recap["gini_revenue_by_farm"], float)

    # Economics block: input=baseline (both plots CS, representative unmapped in this config),
    # output=solved (both go to ME, higher margin). See indicators fixture rates.
    econ = recap["economics"]
    assert set(econ) == {"input", "output", "delta"}
    # input production: (2+3)ha * rdt CS 80 = 400 t
    assert econ["input"]["total_production_tonnes"] == pytest.approx(400.0)
    # output ETP: both plots ME, labor 800 h/ha -> (2+3)*800 = 4000 h / 1607 default
    assert econ["output"]["total_etp"] == pytest.approx(4000.0 / 1607.0)
    for key in ("total_production_tonnes", "total_subsidy", "total_revenue", "total_etp"):
        assert econ["delta"][key] == pytest.approx(econ["output"][key] - econ["input"][key])
    etp_by_region = pd.read_csv(output_dir / "etp_by_region_output.csv")
    assert list(etp_by_region.columns) == ["region", "etp"]

    surface_by_region_output = pd.read_csv(output_dir / "surface_by_region_output.csv")
    assert "region" in surface_by_region_output.columns
