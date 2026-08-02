"""Prospective grid helpers + the composite-score corrections. Data-free."""

import numpy as np
import pandas as pd
import pytest

from apps.dashboard import comparison, prospective


# --- grid assembly -------------------------------------------------------------


def test_grid_coordinates_prefers_the_explicit_recap_fields():
    recap = {"run_policy": "P1", "run_forcing": "F2", "run_name": "something__else"}
    assert prospective.grid_coordinates(recap, "output_7") == ("P1", "F2")


def test_grid_coordinates_falls_back_to_the_name_convention():
    assert prospective.grid_coordinates({"run_name": "P1__F2"}, "output_7") == ("P1", "F2")


def test_grid_coordinates_refuses_to_guess_on_an_ambiguous_name():
    # Three parts: splitting would invent a grid that was never run.
    assert prospective.grid_coordinates({"run_name": "P1__F2__extra"}, "output_7") is None
    assert prospective.grid_coordinates({"run_name": "plain_run"}, "output_7") is None
    assert prospective.grid_coordinates({}, "output_7") is None


def test_build_grid_marks_an_unsolved_run_as_missing_rather_than_zero():
    entries = [
        {"policy": "P1", "forcing": "F0", "recap": {"termination_condition": "optimal"}},
        {"policy": "P1", "forcing": "F1", "recap": {"termination_condition": "infeasible"}},
    ]
    grid = prospective.build_grid(entries, lambda e: 42.0)
    assert grid[("P1", "F0")] == 42.0
    # The indicator function is never even consulted for an infeasible run.
    assert grid[("P1", "F1")] is None


def test_build_grid_passes_through_a_missing_indicator_as_none():
    entries = [{"policy": "P1", "forcing": "F0", "recap": {"termination_condition": "optimal"}}]
    assert prospective.build_grid(entries, lambda e: None) == {("P1", "F0"): None}


def test_grid_frame_orders_rows_and_columns_and_uses_nan_for_gaps():
    grid = {("P2", "F1"): 5.0, ("P1", "F0"): 1.0, ("P1", "F1"): None}
    frame = prospective.grid_frame(grid, ["P1", "P2"], ["F0", "F1"])
    assert list(frame.index) == ["P1", "P2"]
    assert list(frame.columns) == ["F0", "F1"]
    assert frame.loc["P1", "F0"] == 1.0
    assert np.isnan(frame.loc["P1", "F1"])
    assert np.isnan(frame.loc["P2", "F0"])  # absent from the grid entirely


# --- figures build without a display -------------------------------------------


def _frame():
    return pd.DataFrame(
        [[100.0, 20.0], [70.0, float("nan")]],
        index=["P1", "P2"], columns=["F0", "F1"],
    )


def test_heatmap_figure_builds_with_a_missing_cell():
    fig = prospective.build_heatmap_figure(
        _frame(), title="t", colorbar_label="c", higher_is_better=True
    )
    assert fig.axes


def test_tornado_figure_builds_and_reports_an_infeasible_forcing():
    fig = prospective.build_tornado_figure(_frame(), "P2", "F0", value_label="€")
    assert fig.axes


def test_tornado_without_a_nominal_value_says_so_instead_of_crashing():
    frame = pd.DataFrame([[float("nan"), 5.0]], index=["P1"], columns=["F0", "F1"])
    fig = prospective.build_tornado_figure(frame, "P1", "F0", value_label="€")
    assert fig.axes


def test_performance_robustness_figure_builds_including_a_broken_policy():
    from core.reporting import robustness

    grid = {("P1", "F0"): 100.0, ("P1", "F1"): 20.0, ("P2", "F0"): 70.0, ("P2", "F1"): None}
    summaries = robustness.summarise_grid(grid, nominal_forcing="F0")
    fig = prospective.build_performance_robustness_figure(summaries, performance_label="€")
    assert fig.axes


def test_robustness_frame_exposes_one_row_per_policy():
    from core.reporting import robustness

    grid = {("P1", "F0"): 100.0, ("P1", "F1"): 20.0, ("P2", "F0"): 70.0, ("P2", "F1"): 66.0}
    table = prospective.robustness_frame(
        robustness.summarise_grid(grid, nominal_forcing="F0")
    )
    assert list(table.index) == ["P1", "P2"]
    assert table.loc["P1", "Pire cas"] == 20.0


def test_robustness_frame_of_an_empty_grid_is_an_empty_table_not_a_crash():
    """Every policy filtered out is a legitimate state; `set_index` on a row-less frame has
    no "Politique" column to find and used to raise a KeyError."""
    table = prospective.robustness_frame([])

    assert table.empty
    assert table.index.name == "Politique"
    assert "Pire cas" in table.columns


# --- composite score corrections -----------------------------------------------


def test_family_balancing_stops_a_finely_split_family_from_dominating():
    # Two autonomy ratios (same family, perfectly collinear here) against one GHG figure.
    # P1 wins both autonomy columns; P2 wins the GHG column.
    raw = pd.DataFrame(
        {
            "autonomy_kcal": [1.0, 0.0],
            "autonomy_prot": [1.0, 0.0],
            "total_ges": [100.0, 0.0],
        },
        index=["P1", "P2"],
    )
    weights = {c: 1.0 for c in raw.columns}

    unbalanced = comparison.compute_composite_scores(raw, weights, balance_families=False)
    # Autonomy carries 2/3 of the weight purely because it is split in two columns.
    assert unbalanced["P1"] == pytest.approx(2 / 3)

    balanced = comparison.compute_composite_scores(raw, weights, balance_families=True)
    # One family, one voice: autonomy and environment now tie.
    assert balanced["P1"] == pytest.approx(0.5)
    assert balanced["P2"] == pytest.approx(0.5)


def test_family_balancing_defaults_to_on():
    raw = pd.DataFrame(
        {"autonomy_kcal": [1.0, 0.0], "autonomy_prot": [1.0, 0.0], "total_ges": [100.0, 0.0]},
        index=["P1", "P2"],
    )
    weights = {c: 1.0 for c in raw.columns}
    assert comparison.compute_composite_scores(raw, weights)["P1"] == pytest.approx(0.5)


def test_cost_indicators_are_still_inverted_under_balancing():
    raw = pd.DataFrame({"total_ges": [100.0, 0.0]}, index=["dirty", "clean"])
    scores = comparison.compute_composite_scores(raw, {"total_ges": 1.0})
    assert scores["clean"] == pytest.approx(1.0)
    assert scores["dirty"] == pytest.approx(0.0)


def test_indicator_family_resolves_every_autonomy_key_by_prefix():
    assert comparison.indicator_family("autonomy_fe") == "autonomie"
    assert comparison.indicator_family("total_ges") == "environnement"
    assert comparison.indicator_family("subsidy_per_etp") == "intensite"
    assert comparison.indicator_family("inconnu") == "autre"


def test_every_labelled_indicator_has_a_family():
    unfamilied = [
        key for key in comparison.INDICATOR_LABELS
        if comparison.indicator_family(key) == "autre"
    ]
    assert unfamilied == []


# --- pinned-indicator detection -------------------------------------------------


def test_bound_indicators_flags_what_a_constraint_pins():
    recap = {
        "constraints": [
            {"name": "territory_indicator_bound",
             "args": {"label": "budget", "indicator": "subvention", "sense": "le"}},
            {"name": "territory_indicator_bound",
             "args": {"label": "emploi", "indicator": "travail", "sense": "ge"}},
        ]
    }
    pinned = comparison.bound_indicators(recap)
    assert "total_subsidy" in pinned
    assert "subsidy_per_etp" in pinned  # the derived ratios are pinned too
    assert "total_etp" in pinned
    assert "total_ges" not in pinned


def test_bound_indicators_covers_zone_bounds_and_production_bounds():
    recap = {
        "constraints": [
            {"name": "zone_indicator_bound", "args": {"zone": "farms", "indicator": "azote"}},
            {"name": "territory_production_bound", "args": {"label": "cs_quota_max"}},
        ]
    }
    pinned = comparison.bound_indicators(recap)
    assert "total_azote" in pinned
    assert "total_production_tonnes" in pinned


def test_bound_indicators_is_empty_for_a_run_without_such_constraints():
    recap = {"constraints": [{"name": "at_most_one_crop_per_plot", "args": {}}]}
    assert comparison.bound_indicators(recap) == set()
    assert comparison.bound_indicators({}) == set()


# --- indicator lookup -----------------------------------------------------------


def test_indicator_value_reads_each_family_from_its_own_recap_block():
    recap = {
        "economics": {"output": {"total_gross_margin": 1.0}},
        "environment": {"output": {"total_ges": 2.0}},
        "intensity": {"output": {"subsidy_per_etp": 3.0}},
        "diversity": {"output": {"shannon": 4.0}},
        "resilience": {"output": {"revenue_concentration_hhi": 5.0}},
        "food_autonomy": {"output": {"crop_only": {"kcal": 6.0}, "limiting_crop_only": 7.0}},
        "gini_revenue_by_farm": 8.0,
    }
    read = lambda key: comparison.indicator_value(recap, "output", key)  # noqa: E731
    assert read("total_gross_margin") == 1.0
    assert read("total_ges") == 2.0
    assert read("subsidy_per_etp") == 3.0
    assert read("shannon") == 4.0
    assert read("revenue_concentration_hhi") == 5.0
    assert read("autonomy_kcal") == 6.0
    assert read("autonomy_limiting") == 7.0
    assert read("gini_revenue_by_farm") == 8.0


def test_indicator_value_returns_none_for_a_run_predating_a_block():
    assert comparison.indicator_value({}, "output", "subsidy_per_etp") is None
    assert comparison.indicator_value({}, "output", "shannon") is None
