import pandas as pd

from core.data.eligibility import (
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
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
