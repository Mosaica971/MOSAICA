import pandas as pd

from core.data.eligibility import compute_eligibility_mask, eligible_pairs_from_mask


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
