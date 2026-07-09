from pathlib import Path
from typing import Any

import pandas as pd

from case_studies.guadeloupe.economics import (
    compute_gross_margin_per_ha_cult,
    compute_gross_product_per_ha_cult,
    compute_sales_per_ha_cult,
    compute_subsidy_per_ha_cult,
    compute_variable_cost_per_ha_cult,
)
from case_studies.guadeloupe.farm_typology import (
    compute_avers,
    compute_base_crop_group,
    compute_type_expl,
)
from core.config import load_config, resolve_enabled
from core.data.dataset import Dataset
from core.data.eligibility import (
    CATEGORICAL_RULE_REGISTRY,
    attribute_bounds_from_config,
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
)
from core.data.readers import read_flat_set, read_mapping_set, read_wide_table

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SETS_DIR = DATA_DIR / "sets"
TABLES_DIR = DATA_DIR / "tables"
INDICE_H_DIR = TABLES_DIR / "indice_H"
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

YEAR = "2017"
SCENARIO = "RESTIT"


def compute_farm_surface_ha(plot_surface: pd.Series, expl_parc: pd.DataFrame) -> pd.Series:
    merged = expl_parc.assign(surface=expl_parc["plot"].map(plot_surface))
    return merged.groupby("farm")["surface"].sum()


def build_dataset(config: dict[str, Any]) -> Dataset:
    sets = {
        "crops": read_flat_set(SETS_DIR / "CULT_2017.set"),
        "soils": read_flat_set(SETS_DIR / "SOL.set"),
        "otk": read_flat_set(SETS_DIR / "OTK.set"),
        "watersheds": read_flat_set(SETS_DIR / "BV_2017.set"),
        "catchments": read_flat_set(SETS_DIR / "CPT_2017.set"),
    }

    expl_parc = read_mapping_set(SETS_DIR / "EXPL_PARC_2017.set", "farm", "plot")
    bv_parc = read_mapping_set(SETS_DIR / "BV_PARC_2017.set", "watershed", "plot")
    reg_parc = read_mapping_set(SETS_DIR / "REG_PARC_2017.set", "region", "plot")
    cpt_parc = read_mapping_set(SETS_DIR / "CPT_PARC_2017.set", "catchment", "plot")

    data_parc = read_wide_table(TABLES_DIR / "Data_Parc_Gwad_2017.txt")
    data_rpg = read_wide_table(TABLES_DIR / "Data_RPG_Gwad_2017.txt")
    data_cult = read_wide_table(TABLES_DIR / "Data_Cult.txt")
    data_otk = read_wide_table(TABLES_DIR / "Data_OTK.txt")
    matrice_otk_cult = read_wide_table(TABLES_DIR / f"Matrice_OTK_Cult_{SCENARIO}.txt")
    prix_cult = read_wide_table(INDICE_H_DIR / "Prix_Cult.txt")[YEAR]
    rdt_cult = read_wide_table(INDICE_H_DIR / "Rdt_Cult.txt")[YEAR]
    var_rdt_cult = read_wide_table(INDICE_H_DIR / "Var_Rdt_Cult.txt")["init"]
    bagasse_cult = read_wide_table(INDICE_H_DIR / "Bagasse_Cult.txt")[YEAR]
    duree_plant_cult = read_wide_table(INDICE_H_DIR / "Duree_Plant_Cult.txt")[YEAR]
    duree_cycle_cult = read_wide_table(INDICE_H_DIR / "Duree_Cycle_Cult.txt")[YEAR]
    cout_recolte_cult = read_wide_table(INDICE_H_DIR / "Cout_Recolte_Cult.txt")[YEAR]
    cout_transp_cult = read_wide_table(INDICE_H_DIR / "Cout_Transp_Cult.txt")[YEAR]
    posei_surf_cult = read_wide_table(INDICE_H_DIR / "POSEI_Surf_Cult.txt")[YEAR]
    posei_q_cult = read_wide_table(INDICE_H_DIR / "POSEI_Q_Cult.txt")[YEAR]
    aide_indus_cult = read_wide_table(INDICE_H_DIR / "Aide_Indus_Cult.txt")[YEAR]
    aide_replant_cult = read_wide_table(INDICE_H_DIR / "Aide_Replant_Cult.txt")[YEAR]
    aide_transp_cult = read_wide_table(INDICE_H_DIR / "Aide_Transp_Cult.txt")[YEAR]
    aide_garantie_prix_cult = read_wide_table(INDICE_H_DIR / "Aide_Garantie_Prix_Cult.txt")[YEAR]
    mae_recolte_vert_cult = read_wide_table(INDICE_H_DIR / "MAE_Recolte_Vert_Cult.txt")[YEAR]
    mae_jachere_sol_nu_cult = read_wide_table(INDICE_H_DIR / "MAE_Jachere_Sol_Nu_Cult.txt")[YEAR]
    mae_compost_cult = read_wide_table(INDICE_H_DIR / f"MAE_Compost_Cult_{SCENARIO}.txt")[YEAR]
    mb_add_cult = read_wide_table(INDICE_H_DIR / "MB_ADD_Cult.txt")[YEAR]

    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)
    farm_plots = expl_parc.groupby("farm")["plot"].apply(list).to_dict()
    farm_gfa_surface_ha = compute_farm_surface_ha(
        plot_surface * data_parc["GFA_PARC"], expl_parc
    )

    data_parc = data_parc.assign(
        REGION_CODE=data_parc.index.map(reg_parc.set_index("plot")["region"])
    )
    data_parc = data_parc.join(data_rpg[["cult_2015", "cult_2016", "cult_2017"]])

    base_crop_group = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])
    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface)
    farm_risk_aversion = compute_avers(type_expl, type_expl_bis)

    attribute_bounds = attribute_bounds_from_config(config["eligibility_criteria"])
    plot_attributes = data_parc[list(attribute_bounds.keys())]
    crop_bounds = data_cult.T
    eligibility_mask = compute_eligibility_mask(plot_attributes, crop_bounds, attribute_bounds)
    for build_rule, args in resolve_enabled(
        config["categorical_rules"], CATEGORICAL_RULE_REGISTRY
    ):
        crops, condition = build_rule(data_parc, **args)
        eligibility_mask = forbid_where(eligibility_mask, condition, crops)
    eligible_pairs = eligible_pairs_from_mask(eligibility_mask)

    variable_cost_per_ha_cult = compute_variable_cost_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
        cout_recolte_cult=cout_recolte_cult,
        cout_transp_cult=cout_transp_cult,
        rdt_cult=rdt_cult,
    )
    subsidy_per_ha_cult = compute_subsidy_per_ha_cult(
        posei_surf_cult=posei_surf_cult,
        posei_q_cult=posei_q_cult,
        aide_indus_cult=aide_indus_cult,
        aide_replant_cult=aide_replant_cult,
        aide_transp_cult=aide_transp_cult,
        aide_garantie_prix_cult=aide_garantie_prix_cult,
        mae_recolte_vert_cult=mae_recolte_vert_cult,
        mae_jachere_sol_nu_cult=mae_jachere_sol_nu_cult,
        mae_compost_cult=mae_compost_cult,
        mb_add_cult=mb_add_cult,
        rdt_cult=rdt_cult,
        duree_cycle_cult=duree_cycle_cult,
        duree_plant_cult=duree_plant_cult,
    )
    sales_per_ha_cult = compute_sales_per_ha_cult(
        rdt_cult=rdt_cult,
        prix_cult=prix_cult,
        bagasse_cult=bagasse_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    subsidy_per_ha_cult_annualized = subsidy_per_ha_cult / duree_cycle_cult * 12
    gross_product_per_ha_cult = compute_gross_product_per_ha_cult(
        rdt_cult=rdt_cult,
        prix_cult=prix_cult,
        bagasse_cult=bagasse_cult,
        subsidy_per_ha_cult=subsidy_per_ha_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    margin_per_ha_cult = compute_gross_margin_per_ha_cult(
        gross_product_per_ha_cult=gross_product_per_ha_cult,
        variable_cost_per_ha_cult=variable_cost_per_ha_cult,
    )

    parameters = {
        "expl_parc": expl_parc,
        "bv_parc": bv_parc,
        "reg_parc": reg_parc,
        "cpt_parc": cpt_parc,
        "data_parc": data_parc,
        "data_cult": data_cult,
        "data_otk": data_otk,
        "matrice_otk_cult": matrice_otk_cult,
        "prix_cult": prix_cult,
        "rdt_cult": rdt_cult,
        "crop_variance_per_ha": var_rdt_cult,
        "farm_risk_aversion": farm_risk_aversion,
        "farm_surface_ha": farm_surface_ha,
        "farm_plots": farm_plots,
        "farm_gfa_surface_ha": farm_gfa_surface_ha,
        "eligibility_mask": eligibility_mask,
        "eligible_pairs": eligible_pairs,
        "margin_per_ha_cult": margin_per_ha_cult,
        "sales_per_ha_cult": sales_per_ha_cult,
        "subsidy_per_ha_cult_annualized": subsidy_per_ha_cult_annualized,
    }

    return Dataset(sets=sets, parameters=parameters, scalars={})


if __name__ == "__main__":
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    print(f"crops: {len(dataset.sets['crops'])}")
    print(f"soils: {len(dataset.sets['soils'])}")
    print(f"otk: {len(dataset.sets['otk'])}")
    print(f"plots (expl_parc rows): {len(dataset.parameters['expl_parc'])}")
    print(f"farms: {dataset.parameters['expl_parc']['farm'].nunique()}")
    print(f"farm_surface_ha sample:\n{dataset.parameters['farm_surface_ha'].head()}")
