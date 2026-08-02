"""Trade-off fronts from an epsilon-constraint sweep. Data-free: hand-built recaps."""

import pytest

from apps.dashboard import pareto


def _recap(name, azote, margin):
    return {
        "run_name": name,
        "environment": {"output": {"total_azote": azote}},
        "economics": {"output": {"total_gross_margin": margin}},
    }


def _sweep(points, sweep="pareto_azote"):
    """points = [(threshold, azote, margin)] -> {folder: recap}."""
    return {
        f"{sweep}__threshold={t}": _recap(f"{sweep}__threshold={t}", a, m)
        for t, a, m in points
    }


def test_sweep_name_strips_the_matrix_suffix():
    assert pareto.sweep_name("pareto_azote__threshold=1544722") == "pareto_azote"
    assert pareto.sweep_name("calib_retenu") == "calib_retenu"


def test_sweeps_in_groups_runs_by_their_prefix():
    recaps = {**_sweep([(1, 10, 100)]), **_sweep([(2, 20, 200)], sweep="pareto_emploi")}

    assert pareto.sweeps_in(recaps) == ["pareto_azote", "pareto_emploi"]


def test_sweep_of_prefers_the_recap_coordinates_over_the_name_prefix():
    # The case the name prefix gets wrong: a front traced under a policy is named
    # `<policy>__<sweep>__<point>`, so the prefix names the POLICY. Grouping on it would pile
    # every front of that policy into one curve.
    recap = _recap("P8_transition__pareto_azote__threshold=1544722", 10, 100)
    recap.update(run_policy="P8_transition", run_forcing=None, run_sweep="pareto_azote")

    assert pareto.sweep_of(recap) == "P8_transition__pareto_azote"


def test_sweep_of_separates_the_same_front_traced_under_different_forcings():
    nominal = _recap("P8__pareto_azote__threshold=1", 10, 100)
    nominal.update(run_policy="P8", run_forcing=None, run_sweep="pareto_azote")
    forced = _recap("P8__F9__pareto_azote__threshold=1", 9, 80)
    forced.update(run_policy="P8", run_forcing="F9", run_sweep="pareto_azote")

    assert pareto.sweep_of(nominal) != pareto.sweep_of(forced)
    assert pareto.sweeps_in({"a": nominal, "b": forced}) == [
        "P8__F9__pareto_azote", "P8__pareto_azote"
    ]


def test_sweep_of_falls_back_to_the_name_for_runs_predating_the_coordinates():
    # Those runs were always traced against the reference config, so the prefix WAS the sweep.
    assert pareto.sweep_of(_recap("pareto_azote__threshold=1544722", 10, 100)) == "pareto_azote"
    assert pareto.sweep_of({}, "output_12") == "output_12"


def test_collect_points_reads_both_axes_and_sorts_along_x():
    recaps = _sweep([(3, 300.0, 30.0), (1, 100.0, 10.0), (2, 200.0, 20.0)])

    points = pareto.collect_points(recaps, "pareto_azote", "total_azote",
                                   "total_gross_margin")

    assert [p.x for p in points] == [100.0, 200.0, 300.0]
    assert [p.y for p in points] == [10.0, 20.0, 30.0]


def test_a_run_missing_an_indicator_is_skipped_rather_than_placed_at_zero():
    recaps = _sweep([(1, 100.0, 10.0)])
    recaps["pareto_azote__threshold=2"] = {"run_name": "pareto_azote__threshold=2"}

    points = pareto.collect_points(recaps, "pareto_azote", "total_azote",
                                   "total_gross_margin")

    assert [p.label for p in points] == ["pareto_azote__threshold=1"]


def test_a_well_behaved_front_has_no_dominated_point():
    """Tightening a nitrogen ceiling costs margin: less azote AND less margin at every step,
    so no point dominates another."""
    recaps = _sweep([(1, 100.0, 50.0), (2, 200.0, 80.0), (3, 300.0, 95.0)])
    points = pareto.collect_points(recaps, "pareto_azote", "total_azote",
                                   "total_gross_margin")

    marked = pareto.mark_dominated(points, "total_azote", "total_gross_margin")

    assert [p.dominated for p in marked] == [False, False, False]


def test_a_point_worse_on_both_axes_is_dominated():
    """More nitrogen for less margin cannot be on a front -- it signals a solve that did not
    converge, which is exactly what the flag is for."""
    recaps = _sweep([(1, 100.0, 50.0), (2, 200.0, 40.0)])
    points = pareto.collect_points(recaps, "pareto_azote", "total_azote",
                                   "total_gross_margin")

    marked = pareto.mark_dominated(points, "total_azote", "total_gross_margin")
    dominated = [p.label for p in marked if p.dominated]

    assert dominated == ["pareto_azote__threshold=2"]


def test_domination_respects_each_indicators_own_direction():
    """Both axes are costs here (nitrogen and IFT), so LOW wins on both."""
    recaps = {
        "s__a": {"run_name": "s__a", "environment": {"output": {"total_azote": 100.0,
                                                                "total_ift": 10.0}}},
        "s__b": {"run_name": "s__b", "environment": {"output": {"total_azote": 200.0,
                                                                "total_ift": 20.0}}},
    }
    points = pareto.collect_points(recaps, "s", "total_azote", "total_ift")

    marked = pareto.mark_dominated(points, "total_azote", "total_ift")

    assert [p.dominated for p in marked] == [False, True]


def test_marginal_rates_give_the_slope_between_consecutive_front_points():
    recaps = _sweep([(1, 100.0, 50.0), (2, 200.0, 80.0)])
    points = pareto.mark_dominated(
        pareto.collect_points(recaps, "pareto_azote", "total_azote", "total_gross_margin"),
        "total_azote", "total_gross_margin",
    )

    rates = pareto.marginal_rates(points)

    assert len(rates) == 1
    assert rates[0]["delta_x"] == 100.0
    assert rates[0]["rate"] == pytest.approx(0.3)


def test_marginal_rates_skip_dominated_points():
    recaps = _sweep([(1, 100.0, 50.0), (2, 200.0, 40.0), (3, 300.0, 80.0)])
    points = pareto.mark_dominated(
        pareto.collect_points(recaps, "pareto_azote", "total_azote", "total_gross_margin"),
        "total_azote", "total_gross_margin",
    )

    rates = pareto.marginal_rates(points)

    assert [(r["from"], r["to"]) for r in rates] == [
        ("pareto_azote__threshold=1", "pareto_azote__threshold=3")
    ]


def test_the_figure_builds_on_an_empty_sweep_without_raising():
    figure = pareto.build_front_figure([], "total_azote", "total_gross_margin")

    assert figure is not None
