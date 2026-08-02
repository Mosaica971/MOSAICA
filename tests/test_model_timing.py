import pytest

from core.solve.timing import time_phases


def test_time_phases_chains_results_and_returns_duration_per_phase():
    call_order = []

    def build_dataset():
        call_order.append("dataset")
        return "DATASET"

    def build_model(dataset):
        assert dataset == "DATASET"
        call_order.append("model")
        return "MODEL"

    def solve(model):
        assert model == "MODEL"
        call_order.append("solve")
        return "RESULTS"

    dataset, model, results, timings = time_phases(build_dataset, build_model, solve)

    assert dataset == "DATASET"
    assert model == "MODEL"
    assert results == "RESULTS"
    assert call_order == ["dataset", "model", "solve"]
    assert set(timings) == {"data_pipeline", "model_build", "solve"}
    assert all(duration >= 0.0 for duration in timings.values())


def test_time_phases_propagates_exception_from_a_phase_without_calling_later_phases():
    def build_dataset():
        raise ValueError("boom")

    def build_model(dataset):
        raise AssertionError("must not be called when build_dataset fails")

    def solve(model):
        raise AssertionError("must not be called when build_dataset fails")

    with pytest.raises(ValueError, match="boom"):
        time_phases(build_dataset, build_model, solve)
