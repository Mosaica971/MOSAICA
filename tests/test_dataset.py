import pandas as pd

from core.data.dataset import Dataset


def test_dataset_holds_sets_parameters_and_scalars():
    dataset = Dataset(
        sets={"crops": ["AG", "AN"]},
        parameters={"prices": pd.Series({"AG": 700, "AN": 0})},
        scalars={"quota_ba_max": 77877},
    )

    assert dataset.sets["crops"] == ["AG", "AN"]
    assert dataset.parameters["prices"]["AG"] == 700
    assert dataset.scalars["quota_ba_max"] == 77877
