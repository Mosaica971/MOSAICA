from pathlib import Path

from core.config import load_config

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
)


def test_guadeloupe_config_loads_and_has_expected_sections():
    config = load_config(CONFIG_PATH)

    assert config["solver"]["name"] == "appsi_highs"
    # Markowitz since 2026-07-21: it is what GAMS's own CALIB/SCENARIO solves maximize, and
    # plain gross margin ignores the risk term that is the only thing separating the crops.
    assert [e["name"] for e in config["objectives"] if e["enable"]] == [
        "maximize_risk_adjusted_gross_margin"
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
    # Both re-enabled 2026-07-21 as calibration anchors; cs_gfa carries the documented
    # skip_when_no_eligible_area deviation without which 3 real farms make it infeasible.
    cs_gfa = next(e for e in config["constraints"] if e["name"] == "cs_gfa_minimum_share")
    assert cs_gfa["enable"] is True
    assert cs_gfa["args"]["skip_when_no_eligible_area"] is True
    assert "farm_labor_hours_max" in enabled_constraints
    assert len(enabled_constraints) == 19
    assert {
        e["args"]["attribute"] for e in config["eligibility_criteria"] if e["enable"]
    } == {"ALTITUDE", "PENTE", "PLUVIO_PARC", "SURF_HA"}
    assert {e["name"] for e in config["categorical_rules"] if e["enable"]} == {
        "irrigation_required",
        "soil_type_forbidden",
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

    from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
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


def test_eq_supp_suppressions_are_wired():
    """The Eq_*_SUPP family (MODELE.txt:324-340) removes activities from both GAMS models.
    Every one of these was selectable here before 2026-07-21, and the solver did pick TH."""
    config = load_config(CONFIG_PATH)

    forbidden = {
        crop
        for entry in config["categorical_rules"]
        if entry["name"] == "forbid_crops" and entry["enable"]
        for crop in entry["args"]["crops"]
    }

    # The eight aggregate codes exist only to encode the observed baseline.
    assert {"AN", "BA", "BC", "CS", "IG", "MA", "PN", "VE"} <= forbidden
    assert {"TH", "PN_TOUR", "CS_SBT_NISM", "CS_MG_NIM"} <= forbidden
    assert {f"CF_{zone}_{harvest}"
            for zone in ("NBT", "SBT", "NGT", "CGT", "EGT")
            for harvest in ("NISM", "NIM")} <= forbidden
    # The fine variants of the suppressed aggregates must NOT be caught: forbid_crops
    # matches exact codes, and suppressing e.g. every CS_* would empty the model.
    assert "CS_NGT_NISM" not in forbidden
    assert "MA_ROTA" not in forbidden
    assert "PN_PIQ" not in forbidden


def test_pasture_representative_is_the_activity_gams_keeps():
    """PN_TOUR is suppressed by Eq_PN_TOUR_SUPP, so it cannot stand for observed pasture --
    PN_PIQ is the surviving activity, and the one Eq_PN_PROD_MIN targets."""
    config = load_config(CONFIG_PATH)

    assert config["baseline_representative_crops"]["PN"] == "PN_PIQ"
