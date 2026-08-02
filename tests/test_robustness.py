"""Robustness metrics over a policy x forcing grid. Data-free: hand-built grids only."""

import math

import pytest

from core.reporting import robustness


def _grid():
    """Two policies, three forcings. A is high but collapses under the bad forcing; B is
    lower but steady -- the exact contrast the metrics exist to separate."""
    return {
        ("A", "F0"): 100.0, ("A", "F1"): 90.0, ("A", "F2"): 20.0,
        ("B", "F0"): 70.0, ("B", "F1"): 68.0, ("B", "F2"): 66.0,
    }


def test_worst_case_and_retention_separate_level_from_stability():
    a = robustness.summarise_policy(_grid(), "A", nominal_forcing="F0")
    b = robustness.summarise_policy(_grid(), "B", nominal_forcing="F0")
    assert a.nominal == 100.0 and b.nominal == 70.0  # A looks better unforced
    assert a.worst == 20.0 and b.worst == 66.0  # ... and is far worse when forced
    assert a.retention == pytest.approx(0.20)
    assert b.retention == pytest.approx(66 / 70)


def test_max_regret_is_measured_against_the_best_policy_of_each_forcing():
    a = robustness.summarise_policy(_grid(), "A", nominal_forcing="F0")
    b = robustness.summarise_policy(_grid(), "B", nominal_forcing="F0")
    # Best per forcing: F0 -> 100 (A), F1 -> 90 (A), F2 -> 66 (B).
    assert a.max_regret == pytest.approx(46.0)  # F2: 66 - 20
    assert b.max_regret == pytest.approx(30.0)  # F0: 100 - 70


def test_cost_indicator_flips_worst_best_and_regret():
    grid = {("A", "F0"): 10.0, ("A", "F1"): 50.0, ("B", "F0"): 20.0, ("B", "F1"): 22.0}
    a = robustness.summarise_policy(grid, "A", higher_is_better=False, nominal_forcing="F0")
    assert a.worst == 50.0  # for a cost, the worst outcome is the largest
    assert a.best == 10.0
    # Best per forcing is now the smallest: F0 -> 10 (A), F1 -> 22 (B). A's regret is at F1.
    assert a.max_regret == pytest.approx(28.0)


def test_cost_indicator_retention_stays_at_most_one_for_a_worsening_policy():
    grid = {("A", "F0"): 10.0, ("A", "F1"): 50.0}
    a = robustness.summarise_policy(grid, "A", higher_is_better=False, nominal_forcing="F0")
    # Nominal 10 kg, worst 50 kg -> the policy keeps a fifth of its promise, not five times it.
    assert a.retention == pytest.approx(0.2)


def test_infeasible_cell_is_counted_not_dropped():
    grid = {("A", "F0"): 100.0, ("A", "F1"): 90.0, ("A", "F2"): None}
    a = robustness.summarise_policy(grid, "A", nominal_forcing="F0")
    assert a.forcings_evaluated == 3
    assert a.forcings_infeasible == 1
    assert a.infeasible_forcings == ("F2",)
    # The worst case is an absence of solution, not the worst survivor -- reporting 90 here
    # would make a policy that broke look like the steadiest of the set.
    assert a.worst is None
    assert a.retention is None
    assert a.max_regret is None


def test_viability_counts_an_infeasible_forcing_as_a_failure():
    grid = {("A", "F0"): 100.0, ("A", "F1"): 90.0, ("A", "F2"): None}
    a = robustness.summarise_policy(grid, "A", viability_threshold=80.0)
    assert a.viability == pytest.approx(2 / 3)


def test_viability_direction_follows_the_indicator():
    grid = {("A", "F0"): 10.0, ("A", "F1"): 50.0}
    lower = robustness.summarise_policy(
        grid, "A", higher_is_better=False, viability_threshold=20.0
    )
    assert lower.viability == pytest.approx(0.5)  # only the 10 meets a "<= 20" target


def test_policy_with_no_feasible_cell_is_reported_not_crashed():
    grid = {("A", "F0"): None, ("A", "F1"): None}
    a = robustness.summarise_policy(grid, "A", nominal_forcing="F0", viability_threshold=1.0)
    assert a.worst is None and a.median is None and a.mean is None
    assert a.viability == 0.0
    assert a.forcings_infeasible == 2


def test_mean_is_unweighted_by_default_and_weighted_on_request():
    grid = {("A", "F0"): 100.0, ("A", "F1"): 0.0}
    assert robustness.summarise_policy(grid, "A").mean == pytest.approx(50.0)
    weighted = robustness.summarise_policy(grid, "A", weights={"F0": 9.0, "F1": 1.0})
    assert weighted.mean == pytest.approx(90.0)


def test_coefficient_of_variation_ranks_stability():
    a = robustness.summarise_policy(_grid(), "A")
    b = robustness.summarise_policy(_grid(), "B")
    assert b.coefficient_of_variation < a.coefficient_of_variation


def test_normalise_vs_nominal_is_a_share_of_each_policys_own_reference():
    out = robustness.normalise_grid(_grid(), "vs_nominal", nominal_forcing="F0")
    assert out[("A", "F2")] == pytest.approx(0.20)
    assert out[("B", "F2")] == pytest.approx(66 / 70)
    assert out[("A", "F0")] == pytest.approx(1.0)


def test_normalise_regret_puts_a_one_in_every_column():
    out = robustness.normalise_grid(_grid(), "regret")
    for forcing in ("F0", "F1", "F2"):
        column = [out[(p, forcing)] for p in ("A", "B")]
        assert max(column) == pytest.approx(1.0)
    assert out[("A", "F2")] == pytest.approx(20 / 66)


def test_normalise_regret_inverts_for_a_cost_indicator():
    grid = {("A", "F0"): 10.0, ("B", "F0"): 20.0}
    out = robustness.normalise_grid(grid, "regret", higher_is_better=False)
    # The smallest value is the best, so it must score 1.0 and the larger one below it.
    assert out[("A", "F0")] == pytest.approx(1.0)
    assert out[("B", "F0")] == pytest.approx(0.5)


def test_normalise_handles_missing_cells_and_zero_reference():
    grid = {("A", "F0"): 0.0, ("A", "F1"): 5.0, ("B", "F0"): None, ("B", "F1"): 1.0}
    out = robustness.normalise_grid(grid, "vs_nominal", nominal_forcing="F0")
    assert out[("A", "F1")] is None  # zero reference -> undefined, not infinite
    assert out[("B", "F1")] is None  # missing reference


def test_normalise_rejects_vs_nominal_without_a_reference():
    with pytest.raises(ValueError, match="nominal_forcing"):
        robustness.normalise_grid(_grid(), "vs_nominal")


def test_unknown_normalisation_mode_raises():
    with pytest.raises(ValueError, match="unknown normalisation"):
        robustness.normalise_grid(_grid(), "whatever")


def test_summarise_grid_covers_every_policy_in_order():
    summaries = robustness.summarise_grid(_grid(), nominal_forcing="F0")
    assert [s.policy for s in summaries] == ["A", "B"]
    assert robustness.policies_in(_grid()) == ["A", "B"]
    assert robustness.forcings_in(_grid()) == ["F0", "F1", "F2"]


def test_non_finite_values_are_treated_as_missing():
    grid = {("A", "F0"): 100.0, ("A", "F1"): float("nan"), ("A", "F2"): math.inf}
    a = robustness.summarise_policy(grid, "A", nominal_forcing="F0")
    assert a.forcings_infeasible == 2
    assert a.best == 100.0
