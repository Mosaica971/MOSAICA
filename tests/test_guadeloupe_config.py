from pathlib import Path

from core.config import load_config

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
)


def test_guadeloupe_config_loads_and_has_expected_sections():
    config = load_config(CONFIG_PATH)

    assert config["solver"]["name"] == "appsi_highs"
    assert [e["name"] for e in config["objectives"] if e["enable"]] == [
        "maximize_gross_margin"
    ]
    assert [e["name"] for e in config["constraints"] if e["enable"]] == [
        "at_most_one_crop_per_plot"
    ]
    assert {
        e["args"]["attribute"] for e in config["eligibility_criteria"] if e["enable"]
    } == {"ALTITUDE", "PENTE", "PLUVIO_PARC", "SURF_HA"}
    assert {e["name"] for e in config["categorical_rules"] if e["enable"]} == {
        "irrigation_required",
        "soil_type_forbidden",
        "melon_soil_restriction",
        "max_risk_threshold",
        "exact_risk_value",
        "region_crop_forbidden",
    }
