from pathlib import Path

import pandas as pd
import pytest

from case_studies.guadeloupe.data_pipeline import build_dataset, compute_farm_surface_ha
from core.config import load_config

CONFIG = load_config(
    Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
)


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
    dataset = build_dataset(CONFIG)

    assert len(dataset.sets["crops"]) == 84
    assert len(dataset.sets["soils"]) == 5
    assert len(dataset.sets["otk"]) == 189
    assert len(dataset.parameters["expl_parc"]) == 24734
    assert dataset.parameters["expl_parc"]["farm"].nunique() == 4638


def test_build_dataset_computes_farm_surface_ha_matching_gams_init_logic():
    dataset = build_dataset(CONFIG)

    farm_surface_ha = dataset.parameters["farm_surface_ha"]

    assert farm_surface_ha["E1"] == pytest.approx(3.68 + 3.3 + 1.36)
    assert farm_surface_ha["E2"] == pytest.approx(1.24)


def test_build_dataset_selects_2017_column_for_price_and_yield():
    dataset = build_dataset(CONFIG)

    assert dataset.parameters["prix_cult"]["AG"] == pytest.approx(700)
    assert dataset.parameters["rdt_cult"]["AG"] == pytest.approx(20)


def test_build_dataset_computes_eligibility_mask_from_agronomic_bounds():
    dataset = build_dataset(CONFIG)

    mask = dataset.parameters["eligibility_mask"]

    # P1: altitude 23, pente 1, pluvio 1483 -- within CS's bounds (alti<=250, pente<=20)
    assert mask.loc["P1", "CS"] == True  # noqa: E712
    # P2483: altitude 301 -- exceeds CS's ALTI_MAX of 250
    assert mask.loc["P2483", "CS"] == False  # noqa: E712

    eligible_pairs = dataset.parameters["eligible_pairs"]
    total_pairs = mask.shape[0] * mask.shape[1]
    assert 0 < len(eligible_pairs) < total_pairs


def test_build_dataset_computes_gross_margin_per_ha_cult():
    dataset = build_dataset(CONFIG)

    margin_per_ha_cult = dataset.parameters["margin_per_ha_cult"]

    # AG: PB=rdt*prix=20*700=14000 (no subsidies/bagasse for citrus), CV~8001.31
    # from OTK variable costs -- hand-verified via a one-off script using
    # case_studies.guadeloupe.economics against the real data tables.
    assert margin_per_ha_cult["AG"] == pytest.approx(5998.69, abs=0.01)


def test_build_dataset_applies_guadeloupe_categorical_eligibility_rules():
    dataset = build_dataset(CONFIG)

    mask = dataset.parameters["eligibility_mask"]

    # P5: IRRIG_PARC=0 -- melon requires irrigation (Eq_ME_IRR)
    assert mask.loc["P5", "ME"] == False  # noqa: E712
    # P78: RISQUE_CLD=3 (<=3) -- irrigated yam forbidden on CLD-polluted soils (Eq_IG_CLD)
    assert mask.loc["P78", "IG_TUT"] == False  # noqa: E712
    # P366: TYPE_SOL=2 (calcareous) -- pineapple forbidden on calcareous soil (Eq_AN_SOL_Parc)
    assert mask.loc["P366", "AN_NU"] == False  # noqa: E712
    # P938: region R1, a non-melon-producing commune (Eq_ME_Reg) -- otherwise
    # ME-eligible under every other rule/bound, hand-verified via a one-off
    # script against the real data tables.
    assert mask.loc["P938", "ME"] == False  # noqa: E712


def test_build_dataset_skips_disabled_categorical_rule():
    config = {**CONFIG, "categorical_rules": [
        {**entry, "enable": False} for entry in CONFIG["categorical_rules"]
    ]}

    dataset = build_dataset(config)

    mask = dataset.parameters["eligibility_mask"]

    # P5 would be forbidden for ME by irrigation_required, but that rule is disabled here.
    assert mask.loc["P5", "ME"] == True  # noqa: E712
    # P938 would be forbidden for ME by region_crop_forbidden, but disabled here.
    assert mask.loc["P938", "ME"] == True  # noqa: E712


def test_build_dataset_computes_farm_plots_grouping():
    dataset = build_dataset(CONFIG)

    farm_plots = dataset.parameters["farm_plots"]

    assert farm_plots["E1"] == ["P1", "P2", "P3"]


def test_build_dataset_computes_farm_gfa_surface_ha():
    dataset = build_dataset(CONFIG)

    farm_gfa_surface_ha = dataset.parameters["farm_gfa_surface_ha"]

    # E5: 7 plots (P12..P18), all GFA_PARC=1, total surface 8.1ha -- entirely GFA-tenure
    assert farm_gfa_surface_ha["E5"] == pytest.approx(8.1)
    # E1002: 26 plots, only P7119 (1.67ha) has GFA_PARC=1
    assert farm_gfa_surface_ha["E1002"] == pytest.approx(1.67)


def test_build_dataset_merges_land_use_history_columns_into_data_parc():
    dataset = build_dataset(CONFIG)

    data_parc = dataset.parameters["data_parc"]

    # P9: fallow/non-cultivated (code 14) in 2015, 2016, and 2017 -- a friche-lock case
    assert data_parc.loc["P9", "cult_2015"] == 14
    assert data_parc.loc["P9", "cult_2016"] == 14
    assert data_parc.loc["P9", "cult_2017"] == 14


def test_build_dataset_applies_friche_lock_categorical_rule():
    dataset = build_dataset(CONFIG)

    mask = dataset.parameters["eligibility_mask"]

    # P9: fallow (code 14) in 2015, 2016, and 2017 -- friche-locked (Eq_FRICHE)
    assert mask.loc["P9", "AG"] == False  # noqa: E712


def test_friche_lock_config_crops_match_cult_non_nc_set_file_exactly():
    from core.data.readers import read_flat_set

    friche_entry = next(
        entry for entry in CONFIG["categorical_rules"] if entry["name"] == "friche_lock"
    )
    expected = read_flat_set(
        Path(__file__).resolve().parent.parent / "data" / "sets" / "CULT_NON_NC_2017.set"
    )

    assert set(friche_entry["args"]["crops"]) == set(expected)
    assert len(friche_entry["args"]["crops"]) == len(expected)
