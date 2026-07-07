import pandas as pd
import pytest

from case_studies.guadeloupe.data_pipeline import build_dataset, compute_farm_surface_ha


def test_compute_farm_surface_ha_sums_plot_surface_per_farm():
    plot_surface = pd.Series({"P1": 3.68, "P2": 3.3, "P3": 1.36, "P4": 1.24})
    expl_parc = pd.DataFrame(
        {
            "farm": ["E1", "E1", "E1", "E2"],
            "plot": ["P1", "P2", "P3", "P4"],
        }
    )

    result = compute_farm_surface_ha(plot_surface, expl_parc)

    assert result["E1"] == 3.68 + 3.3 + 1.36
    assert result["E2"] == 1.24


def test_build_dataset_loads_known_set_sizes():
    dataset = build_dataset()

    assert len(dataset.sets["crops"]) == 84
    assert len(dataset.sets["soils"]) == 5
    assert len(dataset.sets["otk"]) == 189
    assert len(dataset.parameters["expl_parc"]) == 24734
    assert dataset.parameters["expl_parc"]["farm"].nunique() == 4638


def test_build_dataset_computes_farm_surface_ha_matching_gams_init_logic():
    dataset = build_dataset()

    farm_surface_ha = dataset.parameters["farm_surface_ha"]

    assert farm_surface_ha["E1"] == pytest.approx(3.68 + 3.3 + 1.36)
    assert farm_surface_ha["E2"] == pytest.approx(1.24)


def test_build_dataset_selects_2017_column_for_price_and_yield():
    dataset = build_dataset()

    assert dataset.parameters["prix_cult"]["AG"] == pytest.approx(700)
    assert dataset.parameters["rdt_cult"]["AG"] == pytest.approx(20)


def test_build_dataset_computes_eligibility_mask_from_agronomic_bounds():
    dataset = build_dataset()

    mask = dataset.parameters["eligibility_mask"]

    # P1: altitude 23, pente 1, pluvio 1483 -- within CS's bounds (alti<=250, pente<=20)
    assert mask.loc["P1", "CS"] == True  # noqa: E712
    # P2483: altitude 301 -- exceeds CS's ALTI_MAX of 250
    assert mask.loc["P2483", "CS"] == False  # noqa: E712

    eligible_pairs = dataset.parameters["eligible_pairs"]
    total_pairs = mask.shape[0] * mask.shape[1]
    assert 0 < len(eligible_pairs) < total_pairs
