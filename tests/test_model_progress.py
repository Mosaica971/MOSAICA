import pytest
import time

from core.model.progress import SolveHistory


def test_estimate_seconds_returns_none_when_no_entries(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_record_then_estimate_round_trip(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")

    history.record("guadeloupe", 100, 42.0)

    assert history.estimate_seconds("guadeloupe", 100) == pytest.approx(42.0)


def test_estimate_weights_by_proximity_to_problem_size(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")
    history.record("guadeloupe", 100, 10.0)
    history.record("guadeloupe", 200, 20.0)

    estimate = history.estimate_seconds("guadeloupe", 110)

    # Closer to the size=100/duration=10.0 entry, so the estimate should
    # lean toward 10.0 rather than sit at the midpoint (15.0).
    assert 10.0 < estimate < 15.0


def test_estimate_uses_only_3_nearest_neighbors(tmp_path):
    history = SolveHistory(path=tmp_path / "history.json")
    history.record("guadeloupe", 100, 10.0)
    history.record("guadeloupe", 101, 10.0)
    history.record("guadeloupe", 102, 10.0)
    history.record("guadeloupe", 9999, 999.0)  # far away, must be excluded

    estimate = history.estimate_seconds("guadeloupe", 100)

    assert estimate == pytest.approx(10.0)


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

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_corrupt_file_falls_back_to_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("not valid json")

    history = SolveHistory(path=path)

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_valid_json_of_the_wrong_shape_falls_back_to_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("[1, 2, 3]")

    history = SolveHistory(path=path)

    assert history.estimate_seconds("guadeloupe", 100) is None


def test_history_persists_across_instances(tmp_path):
    path = tmp_path / "history.json"
    SolveHistory(path=path).record("guadeloupe", 100, 5.0)

    reloaded = SolveHistory(path=path)

    assert reloaded.estimate_seconds("guadeloupe", 100) == pytest.approx(5.0)


def test_case_studies_are_kept_separate(tmp_path):
    path = tmp_path / "history.json"
    history = SolveHistory(path=path)
    history.record("guadeloupe", 100, 5.0)

    assert history.estimate_seconds("other_case_study", 100) is None


from core.model.progress import run_with_progress


def test_run_with_progress_returns_result_and_duration():
    def slow_add():
        time.sleep(0.1)
        return 1 + 1

    result, duration = run_with_progress(slow_add, label="test", estimate_seconds=None)

    assert result == 2
    assert duration >= 0.08


def test_run_with_progress_works_with_a_known_estimate():
    def instant_value():
        return "done"

    result, duration = run_with_progress(instant_value, label="test", estimate_seconds=10.0)

    assert result == "done"
    assert duration >= 0.0


def test_run_with_progress_reraises_exception_from_worker_thread():
    def boom():
        raise RuntimeError("solve failed")

    with pytest.raises(RuntimeError, match="solve failed"):
        run_with_progress(boom, label="test", estimate_seconds=None)


import pyomo.environ as pyo

from core.model.builder import build_crop_allocation_model
from core.model.progress import solve_with_progress

_SOLVE_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def test_solve_with_progress_records_history_on_success(tmp_path):
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=_SOLVE_CONFIG,
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
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0},
        eligible_pairs=[("P1", "C1")],
        config=_SOLVE_CONFIG,
    )
    model.Y["P1", "C1"].fix(1)
    model.infeasible_constraint = pyo.Constraint(expr=model.Y["P1", "C1"] == 0)
    history = SolveHistory(path=tmp_path / "history.json")

    with pytest.raises(RuntimeError, match="optimal"):
        solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case", history=history)

    assert "test_case" not in history._data


def test_solve_with_progress_defaults_to_a_fresh_solve_history_when_none_given():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=_SOLVE_CONFIG,
    )

    # No history= passed: solve_with_progress must construct its own SolveHistory()
    # and must not raise even though this touches the real default history path
    # (consistent with the design's non-goal: the default path is wired up but
    # not asserted on beyond "it doesn't blow up").
    solve_with_progress(model, _SOLVE_CONFIG, case_study="test_case_default_history")


def test_solve_with_progress_returns_results_and_duration(tmp_path):
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0},
        crop_margin_per_ha={"C1": 100.0, "C2": 200.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2")],
        config=_SOLVE_CONFIG,
    )
    history = SolveHistory(path=tmp_path / "history.json")

    results, duration = solve_with_progress(
        model, _SOLVE_CONFIG, case_study="test_case", history=history
    )

    assert results is not None
    assert duration >= 0.0
