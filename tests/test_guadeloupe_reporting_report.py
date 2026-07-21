import json

import pandas as pd
import pytest
import yaml

from case_studies.guadeloupe.reporting import report
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs
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
            # Chlordécone: for the output allocation (both ME, uptake class 3), P1 (r=2,
            # soil 4) is flagged at-risk, P2 (r=5) is not.
            "RISQUE_CLD": [2, 5],
            "TYPE_SOL": [4, 1],
            # Water/carbon indicators (added alongside compute_environmental_totals's
            # water+carbon keys): both plots irrigable, uniform initial carbon fraction.
            "IRRIG_PARC": [1, 1],
            "PART_C_INIT": [4.0, 4.0],
        },
        index=["P1", "P2"],
    )
    expl_parc = pd.DataFrame({"farm": ["E1", "E1"], "plot": ["P1", "P2"]})
    # Water/carbon: only touched by compute_environmental_totals's new keys, not asserted
    # on by value here -- just enough shape to not KeyError.
    data_sol = pd.DataFrame(
        {
            "VERTISOL": [0.5, 1.0, 0.25],
            "FERRALSOL": [0.3, 1.0, 0.25],
            "ANDOSOL": [0.2, 1.0, 0.25],
            "NITISOL": [0.1, 1.0, 0.25],
            "AUTRES": [0.4, 1.0, 0.25],
        },
        index=["KAER", "DENS", "PROF"],
    )
    data_cult = pd.DataFrame(
        {
            **{f"BESOIN_EAU_{m:02d}": [5.0, 5.0] for m in range(1, 13)},
            "BIOM_AER": [10.0, 10.0],
            "RAC": [0.5, 0.5],
            "CARB": [0.4, 0.4],
            "HRES": [0.5, 0.5],
            "KCROP": [1.0, 1.0],
        },
        index=["CS", "ME"],
    ).T
    monthly_water_need_per_ha_cult = data_cult.loc[
        [f"BESOIN_EAU_{m:02d}" for m in range(1, 13)]
    ]
    water_need_per_ha_cult = monthly_water_need_per_ha_cult.sum(axis=0)
    carbon_input_per_ha_cult = pd.Series({"CS": 3.0, "ME": 3.0})
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "rdt_cult": pd.Series({"CS": 80.0, "ME": 20.0}),
            "sales_per_ha_cult": pd.Series({"CS": 3000.0, "ME": 5000.0}),
            "subsidy_per_ha_cult_annualized": pd.Series({"CS": 500.0, "ME": 200.0}),
            "labor_hours_per_ha_cult": pd.Series({"CS": 400.0, "ME": 800.0}),
            "margin_per_ha_cult": pd.Series({"CS": 1500.0, "ME": 2000.0}),
            # Resilience (Task 3): fractional yield-loss margin variance, market price
            # (EUR/t) and cycle duration (months) -- only touched by
            # compute_resilience_totals, not asserted on by value in the pre-existing tests.
            "crop_variance_per_ha": pd.Series({"CS": 0.1, "ME": 0.15}),
            "prix_cult": pd.Series({"CS": 37.5, "ME": 250.0}),
            "duree_cycle_cult": pd.Series({"CS": 12.0, "ME": 12.0}),
            "azote_per_ha_cult": pd.Series({"CS": 100.0, "ME": 50.0}),
            "ges_per_ha_cult": pd.Series({"CS": 2.0, "ME": 1.0}),
            "ift_per_ha_cult": pd.Series({"CS": 3.0, "ME": 6.0}),
            "cld_uptake_cult": pd.Series({"CS": 4, "ME": 3}),
            "nutri_cult": pd.DataFrame(
                {"CS": [10.0, 2.0], "ME": [100.0, 5.0]}, index=["Kcal", "Prot"]
            ),
            "nutri_alim": pd.DataFrame(
                {"Ind_Moy": [100.0, 20.0, 6.0], "peche": [5.0, 8.0, 2.0]},
                index=["Q_Tot", "Kcal", "Prot"],
            ),
            "data_sol": data_sol,
            "data_cult": data_cult,
            "water_need_per_ha_cult": water_need_per_ha_cult,
            "monthly_water_need_per_ha_cult": monthly_water_need_per_ha_cult,
            "carbon_input_per_ha_cult": carbon_input_per_ha_cult,
        },
        scalars={},
    )


def test_generate_report_writes_full_output_folder(tmp_path):
    dataset = _tiny_dataset()
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 2.0, "P2": 3.0},
            crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
            eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        ),
        _CONFIG,
    )
    results = solve_model(model, _CONFIG)

    output_dir = report.generate_report(
        dataset, _CONFIG, model, results, duration=1.23, outputs_root=tmp_path
    )

    assert output_dir == tmp_path / "output_1"
    assert (output_dir / "recap.json").exists()
    assert (output_dir / "recap.md").exists()
    assert (output_dir / "config_used.yaml").exists()
    assert (output_dir / "csv" / "allocation_input.csv").exists()
    assert (output_dir / "csv" / "allocation_output.csv").exists()
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

    allocation_output = pd.read_csv(output_dir / "csv" / "allocation_output.csv")
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
        ModelInputs(
            plot_surface_ha={"P1": 2.0, "P2": 3.0},
            crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
            eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        ),
        _CONFIG,
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
        "gross_margin_by_crop_input.csv",
        "gross_margin_by_crop_output.csv",
        "labor_cost_by_crop_input.csv",
        "labor_cost_by_crop_output.csv",
        "facts_input.csv",
        "facts_output.csv",
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
        assert (output_dir / "csv" / name).exists(), name
    for name in (
        "etp_by_region_output.png",
        "etp_by_region_input.png",
        "gross_margin_by_crop_output.png",
        "labor_cost_by_crop_output.png",
    ):
        assert (output_dir / "plots" / name).exists(), name

    revenue_by_farm = pd.read_csv(output_dir / "csv" / "revenue_by_farm.csv")
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
    # output gross margin: both plots ME, margin 2000/ha -> (2+3)*2000 = 10000
    assert econ["output"]["total_gross_margin"] == pytest.approx(10000.0)
    # no cost_per_hour in _CONFIG -> labor cost defaults to 0, net revenue == gross margin
    assert econ["output"]["total_labor_cost"] == pytest.approx(0.0)
    assert econ["output"]["total_net_revenue"] == pytest.approx(10000.0)
    for key in (
        "total_production_tonnes", "total_subsidy", "total_revenue", "total_gross_margin",
        "total_variable_cost", "total_labor_cost", "total_net_revenue", "total_etp",
    ):
        assert econ["delta"][key] == pytest.approx(econ["output"][key] - econ["input"][key])
    # Environment block: symmetric to economics. Output = both ME; input = both CS.
    env = recap["environment"]
    assert set(env) == {"input", "output", "delta"}
    # output (both ME, 5 ha): GES 5*1=5, IFT 5*6=30, azote 5*50=250, surface_cld=P1=2.0
    assert env["output"]["total_ges"] == pytest.approx(5.0)
    assert env["output"]["total_ift"] == pytest.approx(30.0)
    assert env["output"]["total_azote"] == pytest.approx(250.0)
    assert env["output"]["surface_cld"] == pytest.approx(2.0)
    assert env["output"]["ges_per_ha"] == pytest.approx(5.0 / 5.0)
    # input (both CS, 5 ha): GES 5*2=10 ; CS uptake class 4 -> no chlordécone risk
    assert env["input"]["total_ges"] == pytest.approx(10.0)
    assert env["input"]["surface_cld"] == pytest.approx(0.0)
    for key in ("total_ges", "total_ift", "total_azote", "surface_cld"):
        assert env["delta"][key] == pytest.approx(env["output"][key] - env["input"][key])

    facts_output = pd.read_csv(output_dir / "csv" / "facts_output.csv")
    assert {"ges", "ift", "azote", "surface_cld"} <= set(facts_output.columns)

    # Food-autonomy block. Output = both ME (100 t): Kcal ratio 10000/2000=5.0, Prot
    # 500/600=0.833 (limiting). Input = both CS (400 t): Kcal 4000/2000=2.0.
    auto = recap["food_autonomy"]
    assert set(auto) == {"input", "output", "delta"}
    assert auto["output"]["population"] == pytest.approx(100.0)
    assert auto["output"]["crop_only"]["kcal"] == pytest.approx(5.0)
    assert auto["output"]["crop_only"]["prot"] == pytest.approx(500.0 / 600.0)
    assert auto["output"]["limiting_crop_only"] == pytest.approx(500.0 / 600.0)
    assert auto["output"]["with_fishing"]["kcal"] == pytest.approx(10040.0 / 2000.0)
    assert auto["input"]["crop_only"]["kcal"] == pytest.approx(2.0)
    assert auto["delta"]["limiting_crop_only"] == pytest.approx(
        auto["output"]["limiting_crop_only"] - auto["input"]["limiting_crop_only"]
    )
    assert auto["delta"]["crop_only"]["kcal"] == pytest.approx(5.0 - 2.0)

    etp_by_region = pd.read_csv(output_dir / "csv" / "etp_by_region_output.csv")
    assert list(etp_by_region.columns) == ["region", "etp"]

    surface_by_region_output = pd.read_csv(output_dir / "csv" / "surface_by_region_output.csv")
    assert "region" in surface_by_region_output.columns


def test_recap_carries_resilience_block_for_both_sides(tmp_path):
    """Le recap expose les indicateurs d'exposition, cote entree comme sortie."""
    import json

    dataset = _tiny_dataset()
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 2.0, "P2": 3.0},
            crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
            eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        ),
        _CONFIG,
    )
    results = solve_model(model, _CONFIG)
    output_dir = report.generate_report(
        dataset, _CONFIG, model, results, duration=1.23, outputs_root=tmp_path
    )
    recap = json.loads((output_dir / "recap.json").read_text())

    assert "resilience" in recap
    for side in ("input", "output", "delta"):
        assert side in recap["resilience"]
    for key in (
        "climate_margin_at_risk",
        "climate_margin_at_risk_ratio",
        "revenue_concentration_hhi",
        "price_shock_margin_loss",
        "price_shock_margin_loss_ratio",
    ):
        assert key in recap["resilience"]["output"]
