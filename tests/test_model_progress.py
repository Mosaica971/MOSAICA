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
        time.sleep(0.05)
        return 1 + 1

    result, duration = run_with_progress(slow_add, label="test", estimate_seconds=None)

    assert result == 2
    assert duration >= 0.05


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
