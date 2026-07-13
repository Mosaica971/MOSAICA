import time
from collections.abc import Callable
from typing import TypeVar

TDataset = TypeVar("TDataset")
TModel = TypeVar("TModel")
TResults = TypeVar("TResults")


def time_phases(
    build_dataset: Callable[[], TDataset],
    build_model: Callable[[TDataset], TModel],
    solve: Callable[[TModel], TResults],
) -> tuple[TDataset, TModel, TResults, dict[str, float]]:
    start = time.monotonic()
    dataset = build_dataset()
    after_dataset = time.monotonic()

    model = build_model(dataset)
    after_model = time.monotonic()

    results = solve(model)
    after_solve = time.monotonic()

    timings = {
        "data_pipeline": after_dataset - start,
        "model_build": after_model - after_dataset,
        "solve": after_solve - after_model,
    }
    return dataset, model, results, timings
