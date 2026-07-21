import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import evaluate_calibration


def test_load_simulated_allocation_reads_the_output_csv(tmp_path):
    run_dir = tmp_path / "output_1"
    (run_dir / "csv").mkdir(parents=True)
    (run_dir / "csv" / "allocation_output.csv").write_text(
        "plot,crop,farm,region,island,surface_ha\n"
        "P1,CS_NGT_NISM,E1,1,2,2.0\n"
        "P2,MA_ROTA,E1,1,2,3.0\n"
    )
    allocation = evaluate_calibration.load_simulated_allocation(run_dir)
    assert allocation.to_dict() == {"P1": "CS_NGT_NISM", "P2": "MA_ROTA"}
    assert allocation.name == "crop"


def test_load_simulated_allocation_falls_back_to_the_run_root(tmp_path):
    # Runs written before the csv/ reorg keep their CSVs at the run root.
    run_dir = tmp_path / "output_2"
    run_dir.mkdir(parents=True)
    (run_dir / "allocation_output.csv").write_text(
        "plot,crop,farm,region,island,surface_ha\nP1,PN_TOUR,E1,1,2,2.0\n"
    )
    assert evaluate_calibration.load_simulated_allocation(run_dir).to_dict() == {"P1": "PN_TOUR"}


def test_load_simulated_allocation_reports_a_missing_run(tmp_path):
    run_dir = tmp_path / "output_3"
    run_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="allocation_output.csv"):
        evaluate_calibration.load_simulated_allocation(run_dir)


def test_run_config_overlays_the_run_s_thresholds_and_zone(tmp_path):
    run_dir = tmp_path / "output_4"
    run_dir.mkdir()
    (run_dir / "config_used.yaml").write_text(
        "zone_filter:\n"
        "  include:\n"
        "    islands: [1]\n"
        "reporting:\n"
        "  calibration:\n"
        "    farm_pad_max: 42\n"
    )
    config = evaluate_calibration.load_run_config(run_dir)
    assert config["reporting"]["calibration"]["farm_pad_max"] == 42
    assert config["zone_filter"] == {"include": {"islands": [1]}}
    # The structural sections come from the live config.yaml, not from the run, so a run
    # naming a since-removed component still scores.
    assert "categorical_rules" in config
    assert "eligibility_criteria" in config


def test_run_config_ignores_components_the_registry_no_longer_knows(tmp_path):
    # output_12's config_used.yaml names `melon_soil_restriction`, dropped in the
    # 2026-07-21 refactor. Taking the run config verbatim would make build_dataset raise.
    run_dir = tmp_path / "output_5"
    run_dir.mkdir()
    (run_dir / "config_used.yaml").write_text(
        "categorical_rules:\n- name: melon_soil_restriction\n  enable: true\n  args: {}\n"
    )
    config = evaluate_calibration.load_run_config(run_dir)
    rule_names = {rule["name"] for rule in config["categorical_rules"]}
    assert "melon_soil_restriction" not in rule_names


def test_run_config_drops_a_zone_filter_the_run_did_not_have(tmp_path):
    run_dir = tmp_path / "output_6"
    run_dir.mkdir()
    (run_dir / "config_used.yaml").write_text("solver:\n  name: appsi_highs\n")
    config = evaluate_calibration.load_run_config(run_dir)
    # Scoring a whole-territory run on a subset because config.yaml happens to carry a
    # zone_filter today would be a silent, badly wrong verdict.
    assert "zone_filter" not in config
