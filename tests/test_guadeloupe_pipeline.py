from pathlib import Path

import pandas as pd
import pytest

from case_studies.guadeloupe.data_pipeline import (
    INDICE_H_DIR,
    TABLES_DIR,
    build_dataset,
    compute_farm_surface_ha,
)
from core.config import load_config
from core.data.readers import read_wide_table

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


def test_build_dataset_computes_crop_variance_per_ha_from_var_rdt_cult_init_column():
    dataset = build_dataset(CONFIG)

    crop_variance_per_ha = dataset.parameters["crop_variance_per_ha"]

    assert crop_variance_per_ha["AG"] == pytest.approx(0.3)


# --- data.year / data.scenario selection (brique #3) --------------------------------------

def test_build_dataset_defaults_to_2017_restit_without_data_section():
    config = {key: value for key, value in CONFIG.items() if key != "data"}

    dataset = build_dataset(config)

    # 2017 economics reproduced (AG price/yield unchanged from the hard-coded default).
    assert dataset.parameters["prix_cult"]["AG"] == pytest.approx(700)
    assert dataset.parameters["rdt_cult"]["AG"] == pytest.approx(20)


def test_build_dataset_rejects_unknown_year():
    config = {**CONFIG, "data": {"year": "1999", "scenario": "RESTIT"}}

    with pytest.raises(ValueError, match="data.year"):
        build_dataset(config)


def test_build_dataset_rejects_unknown_scenario():
    config = {**CONFIG, "data": {"year": "2017", "scenario": "BOGUS"}}

    with pytest.raises(ValueError, match="data.scenario"):
        build_dataset(config)


def test_build_dataset_year_selects_requested_economic_column():
    raw_2018 = read_wide_table(INDICE_H_DIR / "Prix_Cult.txt")["2018"]
    config = {**CONFIG, "data": {"year": "2018", "scenario": "RESTIT"}}

    dataset = build_dataset(config)

    assert dataset.parameters["prix_cult"].equals(raw_2018)


def test_build_dataset_accepts_init_baseline_column_as_year():
    raw_init = read_wide_table(INDICE_H_DIR / "Prix_Cult.txt")["init"]
    config = {**CONFIG, "data": {"year": "init", "scenario": "RESTIT"}}

    dataset = build_dataset(config)

    assert dataset.parameters["prix_cult"].equals(raw_init)


def test_build_dataset_scenario_selects_requested_otk_matrix():
    raw_smart = read_wide_table(TABLES_DIR / "Matrice_OTK_Cult_SMART.txt")
    config = {**CONFIG, "data": {"year": "2017", "scenario": "SMART"}}

    dataset = build_dataset(config)

    assert dataset.parameters["matrice_otk_cult"].equals(raw_smart)


def test_build_dataset_var_rdt_stays_on_init_column_regardless_of_year():
    config = {**CONFIG, "data": {"year": "2018", "scenario": "RESTIT"}}

    dataset = build_dataset(config)

    # crop variance must keep reading Var_Rdt_Cult's "init" column (0.3 for AG), not `year`.
    assert dataset.parameters["crop_variance_per_ha"]["AG"] == pytest.approx(0.3)


def test_build_dataset_computes_farm_risk_aversion_for_known_farm():
    dataset = build_dataset(CONFIG)

    farm_risk_aversion = dataset.parameters["farm_risk_aversion"]

    # E1: P1(3.68ha)+P2(3.3ha)+P3(1.36ha), all cult_2017=6 (Canne a sucre) -> base group
    # CS for every plot -> PART_CAN=1.0 (>=0.939) -> TYPE_EXPL=3 (Canniers) -> AVERS=0.30.
    assert farm_risk_aversion["E1"] == pytest.approx(0.30)


def test_build_dataset_farm_risk_aversion_is_not_degenerately_uniform():
    dataset = build_dataset(CONFIG)

    farm_risk_aversion = dataset.parameters["farm_risk_aversion"]

    # Every farm in expl_parc must get a classification (no missing/NaN AVERS).
    all_farms = set(dataset.parameters["expl_parc"]["farm"].unique())
    assert set(farm_risk_aversion.index) == all_farms
    assert not farm_risk_aversion.isna().any()

    # Guards against the exact failure mode data/tables/Avers.txt already has (a
    # uniform AVERS=1 for every farm, which would make risk-aversion meaningless): at
    # least 2 of the 9 possible values must appear across 4,638 real farms.
    assert farm_risk_aversion.nunique() >= 2
    assert set(farm_risk_aversion.unique()) <= {
        0.00, 0.30, 0.50, 0.55, 1.20, 1.30, 1.60, 2.30, 2.40,
    }


def test_build_dataset_base_crop_group_has_no_unmapped_plots():
    dataset = build_dataset(CONFIG)

    data_parc = dataset.parameters["data_parc"]
    from case_studies.guadeloupe.farm_typology import compute_base_crop_group

    base_crop_group = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])

    assert not base_crop_group.isna().any()


def test_build_dataset_zone_filter_include_restricts_to_one_island():
    config = {**CONFIG, "zone_filter": {"include": {"islands": [1]}}}

    dataset = build_dataset(config)

    data_parc = dataset.parameters["data_parc"]
    assert len(data_parc) == 8376  # real count of island-1 plots in Data_Parc_Gwad_2017.txt
    assert (data_parc["ILE"] == 1).all()
    # E1's plots (P1,P2,P3) are on island 2 -- must be gone.
    assert "E1" not in dataset.parameters["farm_plots"]
    # Every plot-mapping table must be filtered consistently, not just data_parc/expl_parc.
    assert dataset.parameters["reg_parc"]["plot"].isin(data_parc.index).all()
    assert len(dataset.parameters["reg_parc"]) == len(data_parc)
    assert dataset.parameters["bv_parc"]["plot"].isin(data_parc.index).all()
    assert dataset.parameters["cpt_parc"]["plot"].isin(data_parc.index).all()


def test_build_dataset_zone_filter_exclude_removes_one_farm():
    config = {**CONFIG, "zone_filter": {"exclude": {"farms": ["E1"]}}}

    dataset = build_dataset(config)

    data_parc = dataset.parameters["data_parc"]
    assert len(data_parc) == 24734 - 3  # E1 has exactly 3 plots: P1, P2, P3
    assert "P1" not in data_parc.index
    assert "E1" not in dataset.parameters["expl_parc"]["farm"].values


def test_build_dataset_zone_filter_raises_when_selection_is_empty():
    config = {**CONFIG, "zone_filter": {"include": {"farms": ["NONEXISTENT_FARM"]}}}

    with pytest.raises(ValueError, match="zone_filter excludes every plot"):
        build_dataset(config)


def test_build_dataset_exposes_sales_and_annualized_subsidy_per_ha_cult():
    dataset = build_dataset(CONFIG)

    sales = dataset.parameters["sales_per_ha_cult"]
    subsidy_annualized = dataset.parameters["subsidy_per_ha_cult_annualized"]
    margin = dataset.parameters["margin_per_ha_cult"]

    # AG: PB=rdt*prix=20*700=14000, no subsidies/bagasse (see the existing
    # gross-margin test's comment) -- sales alone should equal the full gross
    # product, and reconciling with the already-verified margin gives the
    # same CV~8001.31 hand-verified variable cost.
    assert sales["AG"] == pytest.approx(14000.0, abs=0.01)
    assert subsidy_annualized["AG"] == pytest.approx(0.0, abs=0.01)
    assert (sales["AG"] + subsidy_annualized["AG"] - margin["AG"]) == pytest.approx(8001.31, abs=1.0)

    # BA_INT (intensive banana): subsidy_per_ha_cult=18658.0 (POSEI + national aid,
    # dominated by Aide_Indus_Cult/POSEI_Q_Cult), duree_cycle_cult=12 --
    # hand-verified via a one-off script calling
    # case_studies.guadeloupe.economics.compute_subsidy_per_ha_cult against the
    # real data tables, giving subsidy_per_ha_cult_annualized = 18658.0 / 12 * 12
    # = 18658.0. Unlike AG (subsidy=0), this exercises the annualization
    # division/multiplication against a meaningfully nonzero subsidy.
    assert subsidy_annualized["BA_INT"] == pytest.approx(18658.0, abs=0.01)


def test_yield_multiplier_scales_rdt_in_dataset():
    from copy import deepcopy
    from pathlib import Path

    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    cfg = load_config(Path("case_studies/guadeloupe/config.yaml"))
    cfg["zone_filter"] = {"include": {"islands": [3]}}  # Marie-Galante: smallest, fast
    base = build_dataset(cfg)

    shocked_cfg = deepcopy(cfg)
    shocked_cfg["economic_overrides"] = {
        "yield_multipliers": [{"crops": ["CS_MG_NISM"], "factor": 0.5}]
    }
    shocked = build_dataset(shocked_cfg)

    assert shocked.parameters["rdt_cult"]["CS_MG_NISM"] == (
        base.parameters["rdt_cult"]["CS_MG_NISM"] * 0.5
    )


def test_cost_multiplier_scales_variable_cost_in_dataset():
    from copy import deepcopy
    from pathlib import Path

    from case_studies.guadeloupe.data_pipeline import build_dataset
    from core.config import load_config

    cfg = load_config(Path("case_studies/guadeloupe/config.yaml"))
    cfg["zone_filter"] = {"include": {"islands": [3]}}
    base = build_dataset(cfg)

    shocked_cfg = deepcopy(cfg)
    shocked_cfg["economic_overrides"] = {
        "cost_multipliers": [{"crops": ["CS_MG_NISM"], "factor": 1.3}]
    }
    shocked = build_dataset(shocked_cfg)

    assert shocked.parameters["variable_cost_per_ha_cult"]["CS_MG_NISM"] == (
        base.parameters["variable_cost_per_ha_cult"]["CS_MG_NISM"] * 1.3
    )


def test_build_dataset_registers_water_and_carbon_rates():
    """Les nouveaux taux sont enregistrés, indexés par culture, et non dégénérés."""
    dataset = build_dataset(CONFIG)
    crops = dataset.sets["crops"]

    water_need = dataset.parameters["water_need_per_ha_cult"]
    carbon_input = dataset.parameters["carbon_input_per_ha_cult"]
    monthly = dataset.parameters["monthly_water_need_per_ha_cult"]

    assert set(water_need.index) == set(crops)
    assert set(carbon_input.index) == set(crops)
    assert list(monthly.index) == [f"BESOIN_EAU_{m:02d}" for m in range(1, 13)]
    # Le total annuel est bien la somme des 12 mois.
    assert water_need.sum() == pytest.approx(monthly.to_numpy().sum())
    # Non dégénéré: au moins une culture a un besoin en eau et un apport carbone non nuls.
    assert (water_need > 0).any()
    assert (carbon_input > 0).any()


def test_build_dataset_loads_soil_table_with_all_five_soils():
    dataset = build_dataset(CONFIG)
    data_sol = dataset.parameters["data_sol"]

    assert set(data_sol.index) >= {"KAER", "DENS", "PROF"}
    assert set(data_sol.columns) == {
        "NITISOL", "ANDOSOL", "FERRALSOL", "AUTRES", "VERTISOL"
    }
    # Les coefficients de minéralisation diffèrent entre sols -- sinon le choix du sol
    # n'aurait aucun effet sur le bilan carbone.
    assert data_sol.loc["KAER"].nunique() > 1
