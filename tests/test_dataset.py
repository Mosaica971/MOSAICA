import pandas as pd

from core.data.dataset import Dataset, build_registry


def test_dataset_holds_sets_parameters_and_scalars():
    dataset = Dataset(
        sets={"crops": ["AG", "AN"]},
        parameters={"prices": pd.Series({"AG": 700, "AN": 0})},
        scalars={"quota_ba_max": 77877},
    )

    assert dataset.sets["crops"] == ["AG", "AN"]
    assert dataset.parameters["prices"]["AG"] == 700
    assert dataset.scalars["quota_ba_max"] == 77877


def test_build_registry_lists_every_entry_with_category_type_and_size():
    dataset = Dataset(
        sets={"crops": ["AG", "AN"]},
        parameters={
            "prices": pd.Series({"AG": 700, "AN": 0}),
            "data_parc": pd.DataFrame({"SURF_HA": [3.68, 3.3]}),
        },
        scalars={"quota_ba_max": 77877},
    )

    registry = build_registry(dataset)

    assert registry == [
        {"category": "sets", "name": "crops", "type": "list", "size": 2},
        {"category": "parameters", "name": "prices", "type": "Series", "size": 2},
        {"category": "parameters", "name": "data_parc", "type": "DataFrame", "size": (2, 1)},
        {"category": "scalars", "name": "quota_ba_max", "type": "int", "size": 1},
    ]
