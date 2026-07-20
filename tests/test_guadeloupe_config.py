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
    assert {e["name"] for e in config["objectives"]} == {
        "maximize_gross_margin",
        "maximize_risk_adjusted_gross_margin",
    }
    enabled_constraints = [e["name"] for e in config["constraints"] if e["enable"]]
    assert enabled_constraints[0] == "at_most_one_crop_per_plot"
    assert enabled_constraints.count("farm_area_share_max") == 2
    assert enabled_constraints.count("farm_area_ratio_min") == 2
    assert enabled_constraints.count("territory_production_bound") == 12
    assert "cs_gfa_minimum_share" not in enabled_constraints
    assert len(enabled_constraints) == 17
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
        "friche_lock",
        # GAMS geographic/soil/irrigation ITK bans, ported 2026-07-20.
        "attribute_forbidden",
        "forbid_crops",
    }


def test_ba_rota_numerator_crops_match_sc_cs_anchor_plus_ja_and_canne_fibre():
    # ba_rota's numerator is hand-written longhand (YAML can't splice an anchor list
    # inline with extra items), unlike friche_lock's crop list which has a set-file
    # equivalence test. This guards it from silently drifting out of sync with the
    # *SC_CS anchor it's supposed to mirror.
    config = load_config(CONFIG_PATH)

    ba_rota = next(
        entry
        for entry in config["constraints"]
        if entry["name"] == "farm_area_ratio_min" and entry["args"]["label"] == "ba_rota"
    )

    sc_cf = {
        "CF_NBT_NISM", "CF_NBT_NIM", "CF_SBT_NISM", "CF_SBT_NIM",
        "CF_NGT_NISM", "CF_NGT_NIM", "CF_CGT_NISM", "CF_CGT_NIM",
        "CF_EGT_NISM", "CF_EGT_NIM",
    }
    expected = {"JA"} | set(config["crop_families"]["cs"]) | sc_cf

    assert set(ba_rota["args"]["numerator_crops"]) == expected
    assert len(ba_rota["args"]["numerator_crops"]) == len(expected)


def test_itk_bans_confine_regional_sugarcane():
    from pathlib import Path

    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    cfg = load_config(Path("case_studies/guadeloupe/config.yaml"))
    cfg["zone_filter"] = {"include": {"islands": [3]}}  # Marie-Galante only
    ds = build_dataset(cfg)
    eligible_crops = {crop for _, crop in ds.parameters["eligible_pairs"]}

    # On Marie-Galante (ILE=3): NGT/CGT/EGT/BT/SBT sugarcane systems must be absent...
    for crop in ["CS_NGT_NISM", "CS_CGT_NISM", "CS_EGT_NISM", "CS_BT_NISM", "CS_SBT_NISM"]:
        assert crop not in eligible_crops, crop
    # ...and irrigated sugarcane (Eq_CS_IRR) is disabled everywhere.
    for crop in ["CS_MG_IM", "CS_BT_IM"]:
        assert crop not in eligible_crops, crop
    # Eq_AG_BT (citrus only on Basse-Terre) and the faithful Eq_VE_PLUIE ban.
    assert "AG" not in eligible_crops
    assert "VE_PLUIE" not in eligible_crops
    # Marie-Galante's own non-irrigated non-mechanised system stays available.
    assert "CS_MG_NISM" in eligible_crops
