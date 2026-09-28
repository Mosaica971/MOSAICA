"""Runs written before the 2026-09-22 renaming must read like new ones."""

from case_studies.guadeloupe import legacy_names


def test_no_entry_maps_a_name_onto_itself():
    # A bulk rename run over the module would turn "total_azote": "total_nitrogen" into
    # "total_nitrogen": "total_nitrogen" -- silently disabling the whole layer.
    identities = [old for old, new in legacy_names.LEGACY_NAMES.items() if old == new]
    assert not identities


def test_no_current_name_is_also_a_legacy_name():
    chained = set(legacy_names.LEGACY_NAMES.values()) & set(legacy_names.LEGACY_NAMES)
    assert not chained


def test_recap_keys_and_values_are_upgraded_but_numbers_and_run_name_are_not():
    recap = {
        "run_name": "P4_statu_quo__F0_nominal",
        "run_policy": "P4_statu_quo",
        "environment": {"output": {"total_azote": 1.5, "surface_cld": 2.0}},
        "constraints": [{"name": "farm_labor_hours_max", "args": {"label": "mo_max_expl"}}],
        "shadow_prices": {"mo_max_expl": {"dual": 3.0}},
        "calibration": {"farm_type_recall_by_type": {"Bananiers": 100.0}},
    }
    upgraded = legacy_names.upgrade_recap(recap)
    assert upgraded["run_name"] == "P4_statu_quo__F0_nominal"
    assert upgraded["run_policy"] == "P4_status_quo"
    assert upgraded["environment"]["output"] == {"total_nitrogen": 1.5, "chlordecone_risk_area": 2.0}
    assert upgraded["constraints"][0]["args"]["label"] == "labor_max_farm"
    assert upgraded["shadow_prices"] == {"labor_max_farm": {"dual": 3.0}}
    assert upgraded["calibration"]["farm_type_recall_by_type"] == {"Banana growers": 100.0}


def test_composite_names_are_renamed_segment_by_segment():
    assert (
        legacy_names.rename("P8_transition_agroecologique__F9_crise_systemique__pareto_azote")
        == "P8_agroecological_transition__F9_systemic_crisis__pareto_nitrogen"
    )


def test_crop_codes_and_unknown_strings_pass_through():
    assert legacy_names.upgrade(["CS_MG_NISM", "PN_PIQ", "anything"]) == [
        "CS_MG_NISM", "PN_PIQ", "anything",
    ]


def test_renamed_csv_files_offer_their_legacy_name():
    assert legacy_names.csv_candidates("fte_by_region_output.csv") == [
        "fte_by_region_output.csv", "etp_by_region_output.csv",
    ]
    assert legacy_names.csv_candidates("facts_output.csv") == ["facts_output.csv"]
