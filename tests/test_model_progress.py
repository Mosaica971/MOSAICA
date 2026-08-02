import pytest
import time

from core.solve.progress import SolveHistory, format_estimate


def test_estimate_returns_none_when_no_entries(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")

    assert history.estimate_range("guadeloupe", 100) is None


def test_record_then_estimate_round_trip(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")

    history.record("guadeloupe", 100, 42.0)

    assert history.estimate_range("guadeloupe", 100) == (42.0, 42.0, 1)


def test_the_estimate_is_a_range_because_the_solve_time_is_not_a_number():
    # The reason this class returns a range at all: at a FIXED problem size the 20 recorded
    # Guadeloupe solves span 155 s to 1 007 s. A point estimate over that is wrong by a
    # median 75 %, so what is reported is the spread that was actually observed.
    history = SolveHistory.__new__(SolveHistory)
    history._data = {"g": [{"size": 100, "duration": d, "warm": False}
                           for d in (155.0, 206.0, 1007.0)]}

    assert history.estimate_range("g", 100) == (155.0, 1007.0, 3)


def test_warm_and_cold_solves_are_never_pooled(tmp_path):
    # 209 s warm against 720 s cold on the same model: mixing them makes both meaningless.
    history = SolveHistory(path=tmp_path / "history.json")
    history.record("guadeloupe", 100, 720.0, warm_start=False)
    history.record("guadeloupe", 100, 209.0, warm_start=True)

    assert history.estimate_range("guadeloupe", 100, warm_start=True) == (209.0, 209.0, 1)
    assert history.estimate_range("guadeloupe", 100, warm_start=False) == (720.0, 720.0, 1)


def test_entries_written_before_the_warm_flag_are_a_last_resort_not_a_pool(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"g": [{"size": 100, "duration": 500.0}]}')
    history = SolveHistory(path=path)

    # Nothing labelled: the unlabelled entry is better than no answer at all.
    assert history.estimate_range("g", 100, warm_start=True) == (500.0, 500.0, 1)

    # Once a labelled entry exists it wins outright, rather than widening the range with a
    # run whose mode nobody knows.
    history.record("g", 100, 200.0, warm_start=True)
    assert history.estimate_range("g", 100, warm_start=True) == (200.0, 200.0, 1)


def test_a_size_outside_the_band_gets_no_estimate_rather_than_a_wrong_one(tmp_path):
    # The defect this fixes: the old estimator answered 456 s for BOTH 200 000 and 331 044
    # variables, because in both cases the three "nearest" entries were the same distant
    # cluster. Refusing to answer is the honest output.
    history = SolveHistory(path=tmp_path / "history.json")
    history.record("guadeloupe", 100, 10.0)

    assert history.estimate_range("guadeloupe", 110) == (10.0, 10.0, 1)  # within 20 %
    assert history.estimate_range("guadeloupe", 200) is None             # outside


def test_the_estimate_reads_the_most_recent_runs_not_the_oldest(tmp_path):
    # The old estimator sorted by distance in size; on an exact match Python's stable sort
    # handed it the three OLDEST entries, so it never learned anything after the third run.
    history = SolveHistory(path=tmp_path / "history.json")
    for duration in (1000.0, 900.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0, 200.0, 100.0):
        history.record("guadeloupe", 100, duration)

    low, high, count = history.estimate_range("guadeloupe", 100)

    assert count == 8              # the recent window, not all ten
    assert (low, high) == (100.0, 800.0)  # the two oldest (1000, 900) are gone


def test_format_estimate_prints_a_range_and_collapses_a_tight_one():
    assert format_estimate(None) == ""
    assert "186-779s" in format_estimate((186.0, 779.0, 9))
    assert "9 run comparables" in format_estimate((186.0, 779.0, 9))
    # Spread under 5 %: one number, and the SLOW end of it.
    assert "~101s" in format_estimate((100.0, 101.0, 1))
    assert "1 run comparable" in format_estimate((100.0, 101.0, 1))


def test_record_truncates_to_last_20_entries(tmp_path):
    path = tmp_path / "history.json"
    history = SolveHistory(path=path)
    for i in range(25):
        history.record("guadeloupe", i, float(i))

    reloaded = SolveHistory(path=path)

    assert len(reloaded._data["guadeloupe"]) == 20
    assert reloaded._data["guadeloupe"][0]["size"] == 5
    assert reloaded._data["guadeloupe"][-1]["size"] == 24


def test_missing_file_falls_back_to_empty_history(tmp_path):
    history = SolveHistory(path=tmp_path / "does_not_exist.json")

    assert history.estimate_range("guadeloupe", 100) is None


def test_corrupt_file_falls_back_to_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("not valid json")

    history = SolveHistory(path=path)

    assert history.estimate_range("guadeloupe", 100) is None


def test_valid_json_of_the_wrong_shape_falls_back_to_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("[1, 2, 3]")

    history = SolveHistory(path=path)

    assert history.estimate_range("guadeloupe", 100) is None


def test_history_persists_across_instances(tmp_path):
    path = tmp_path / "history.json"
    SolveHistory(path=path).record("guadeloupe", 100, 5.0)

    reloaded = SolveHistory(path=path)

    assert reloaded.estimate_range("guadeloupe", 100) == (5.0, 5.0, 1)


def test_case_studies_are_kept_separate(tmp_path):
    path = tmp_path / "history.json"
    history = SolveHistory(path=path)
    history.record("guadeloupe", 100, 5.0)

    assert history.estimate_range("other_case_study", 100) is None


from core.solve.progress import run_with_progress


def test_run_with_progress_returns_result_and_duration():
    def slow_add():
        time.sleep(0.1)
        return 1 + 1

    result, duration = run_with_progress(slow_add, label="test", estimate=None)

    assert result == 2
    assert duration >= 0.08


def test_run_with_progress_works_with_a_known_estimate():
    def instant_value():
        return "done"

    result, duration = run_with_progress(instant_value, label="test", estimate=(10.0, 20.0, 3))

    assert result == "done"
    assert duration >= 0.0


def test_run_with_progress_reraises_exception_from_func():
    def boom():
        raise RuntimeError("solve failed")

    with pytest.raises(RuntimeError, match="solve failed"):
        run_with_progress(boom, label="test", estimate=None)


def test_run_with_progress_runs_func_on_the_calling_thread():
    # Architectural guard: the solve must NOT be backgrounded. The appsi_highs solver
    # loads the model inside capture_output(capture_fd=True); running it on a worker
    # thread while a progress bar writes from the main thread corrupts Pyomo's
    # process-global stdout/stderr fd state (crashes on real file descriptors). See
    # docs/superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md.
    import threading

    caller = threading.current_thread()
    seen: dict[str, threading.Thread] = {}

    def func():
        seen["thread"] = threading.current_thread()
        return "ok"

    result, _ = run_with_progress(func, label="test", estimate=None)

    assert result == "ok"
    assert seen["thread"] is caller


import pyomo.environ as pyo

from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs
from core.solve.progress import solve_with_progress

_SOLVE_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_solve_with_progress_records_history_on_success(tmp_path):
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
            eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        ),
        _SOLVE_CONFIG,
    )
    history = SolveHistory(path=tmp_path / "history.json")

    solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case", history=history)

    entries = history._data["test_case"]
    assert len(entries) == 1
    assert entries[0]["size"] == 2  # Y["P1","C1"], Y["P1","C2"]
    assert entries[0]["duration"] >= 0.0
    assert pyo.value(model.Y["P1", "C2"]) == pytest.approx(1)


def test_solve_with_progress_does_not_record_history_on_failure(tmp_path):
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0},
            eligible_pairs=[("P1", "C1")],
        ),
        _SOLVE_CONFIG,
    )
    model.Y["P1", "C1"].fix(1)
    model.infeasible_constraint = pyo.Constraint(expr=model.Y["P1", "C1"] == 0)
    history = SolveHistory(path=tmp_path / "history.json")

    with pytest.raises(RuntimeError, match="did not reach a usable solution"):
        solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case", history=history)

    assert "test_case" not in history._data


def test_solve_with_progress_defaults_to_a_fresh_solve_history_when_none_given():
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
            eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        ),
        _SOLVE_CONFIG,
    )

    # No history= passed: solve_with_progress must construct its own SolveHistory()
    # and must not raise even though this touches the real default history path
    # (consistent with the design's non-goal: the default path is wired up but
    # not asserted on beyond "it doesn't blow up").
    solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case_default_history")


def test_solve_with_progress_returns_results_and_duration(tmp_path):
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 1.0},
            crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
            eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        ),
        _SOLVE_CONFIG,
    )
    history = SolveHistory(path=tmp_path / "history.json")

    results, duration = solve_with_progress(
        model, _SOLVE_CONFIG, case_study="test_case", history=history
    )

    assert results is not None
    assert duration >= 0.0
