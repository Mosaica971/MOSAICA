import pandas as pd

from core.data.eligibility import (
    attribute_bounds_from_config,
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
    rule_exact_risk_value,
    rule_friche_lock,
    rule_irrigation_required,
    rule_max_risk_threshold,
    rule_melon_soil_restriction,
    rule_region_crop_forbidden,
    rule_soil_type_forbidden,
)


def test_compute_eligibility_mask_applies_min_max_bounds_per_attribute():
    plot_attributes = pd.DataFrame(
        {"ALTITUDE": [100, 300], "PENTE": [5, 5]},
        index=["P1", "P2"],
    )
    crop_bounds = pd.DataFrame(
        {
            "ALTI_MIN": [0, 0],
            "ALTI_MAX": [200, 500],
            "PENTE_MIN": [0, 0],
            "PENTE_MAX": [10, 3],
        },
        index=["C1", "C2"],
    )
    attribute_bounds = {
        "ALTITUDE": ("ALTI_MIN", "ALTI_MAX"),
        "PENTE": ("PENTE_MIN", "PENTE_MAX"),
    }

    mask = compute_eligibility_mask(plot_attributes, crop_bounds, attribute_bounds)

    assert mask.loc["P1", "C1"] == True  # noqa: E712 (within both bounds)
    assert mask.loc["P1", "C2"] == False  # noqa: E712 (pente 5 > pente_max 3)
    assert mask.loc["P2", "C1"] == False  # noqa: E712 (altitude 300 > alti_max 200)
    assert mask.loc["P2", "C2"] == False  # noqa: E712 (pente 5 > pente_max 3)


def test_eligible_pairs_from_mask_returns_only_true_cells_as_plot_crop_pairs():
    mask = pd.DataFrame(
        {"C1": [True, False], "C2": [False, False]},
        index=["P1", "P2"],
    )

    pairs = eligible_pairs_from_mask(mask)

    assert pairs == [("P1", "C1")]


def test_forbid_where_clears_target_crops_only_for_plots_matching_condition():
    mask = pd.DataFrame(
        {"C1": [True, True], "C2": [True, True]},
        index=["P1", "P2"],
    )
    condition = pd.Series({"P1": True, "P2": False})

    result = forbid_where(mask, condition, crops=["C1"])

    assert result.loc["P1", "C1"] == False  # noqa: E712 (P1 matches condition)
    assert result.loc["P2", "C1"] == True  # noqa: E712 (P2 does not match condition)
    assert result.loc["P1", "C2"] == True  # noqa: E712 (C2 not targeted by the rule)


def test_rule_irrigation_required_forbids_crops_without_irrigation():
    data_parc = pd.DataFrame({"IRRIG_PARC": [0, 1]}, index=["P1", "P2"])

    crops, condition = rule_irrigation_required(
        data_parc, crops=["ME"], irrigation_column="IRRIG_PARC"
    )

    assert crops == ["ME"]
    assert condition.tolist() == [True, False]


def test_rule_soil_type_forbidden_matches_listed_soil_types():
    data_parc = pd.DataFrame({"TYPE_SOL": [2, 3]}, index=["P1", "P2"])

    crops, condition = rule_soil_type_forbidden(
        data_parc, crops=["AN_NU"], soil_column="TYPE_SOL", forbidden_soil_types=[2]
    )

    assert crops == ["AN_NU"]
    assert condition.tolist() == [True, False]


def test_rule_melon_soil_restriction_matches_soil_type_or_island():
    data_parc = pd.DataFrame(
        {"TYPE_SOL": [2, 1, 1], "ILE": [0, 1, 0]}, index=["P1", "P2", "P3"]
    )

    crops, condition = rule_melon_soil_restriction(
        data_parc,
        crops=["ME"],
        soil_column="TYPE_SOL",
        forbidden_soil_types=[2, 3, 4],
        island_column="ILE",
        forbidden_island=1,
    )

    assert crops == ["ME"]
    assert condition.tolist() == [True, True, False]


def test_rule_max_risk_threshold_forbids_values_at_or_below_threshold():
    data_parc = pd.DataFrame({"RISQUE_CLD": [3, 4]}, index=["P1", "P2"])

    crops, condition = rule_max_risk_threshold(
        data_parc, crops=["IG_TUT"], risk_column="RISQUE_CLD", max_allowed=3
    )

    assert crops == ["IG_TUT"]
    assert condition.tolist() == [True, False]


def test_rule_exact_risk_value_forbids_the_matching_value():
    data_parc = pd.DataFrame({"RISQUE_CLD": [1, 2]}, index=["P1", "P2"])

    crops, condition = rule_exact_risk_value(
        data_parc, crops=["PN_PIQ"], risk_column="RISQUE_CLD", allowed_value=1
    )

    assert crops == ["PN_PIQ"]
    assert condition.tolist() == [True, False]


def test_rule_region_crop_forbidden_matches_listed_regions():
    data_parc = pd.DataFrame({"REGION_CODE": ["R1", "R2"]}, index=["P1", "P2"])

    crops, condition = rule_region_crop_forbidden(
        data_parc, crops=["ME"], region_column="REGION_CODE", forbidden_regions=["R1"]
    )

    assert crops == ["ME"]
    assert condition.tolist() == [True, False]


def test_attribute_bounds_from_config_keeps_only_enabled_entries():
    entries = [
        {
            "name": "altitude",
            "enable": True,
            "args": {"attribute": "ALTITUDE", "min_col": "ALTI_MIN", "max_col": "ALTI_MAX"},
        },
        {
            "name": "slope",
            "enable": False,
            "args": {"attribute": "PENTE", "min_col": "PENTE_MIN", "max_col": "PENTE_MAX"},
        },
    ]

    bounds = attribute_bounds_from_config(entries)

    assert bounds == {"ALTITUDE": ("ALTI_MIN", "ALTI_MAX")}


def test_rule_friche_lock_matches_plots_fallow_for_every_listed_year():
    data_parc = pd.DataFrame(
        {
            "cult_2015": [14, 14, 5],
            "cult_2016": [14, 5, 14],
            "cult_2017": [10, 14, 14],
        },
        index=["P1", "P2", "P3"],
    )

    crops, condition = rule_friche_lock(
        data_parc,
        crops=["AG", "CS"],
        history_columns=["cult_2015", "cult_2016", "cult_2017"],
        fallow_codes=[0, 10, 14],
    )

    assert crops == ["AG", "CS"]
    # P1: 14,14,10 -- all fallow codes, locked. P2/P3: one year has a real crop (5).
    assert condition.tolist() == [True, False, False]
