from pathlib import Path

import pandas as pd

from case_studies.guadeloupe.economics import (
    compute_gross_margin_per_ha_cult,
    compute_gross_product_per_ha_cult,
    compute_subsidy_per_ha_cult,
    compute_variable_cost_per_ha_cult,
)
from core.data.dataset import Dataset
from core.data.eligibility import (
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
)
from core.data.readers import read_flat_set, read_mapping_set, read_wide_table

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SETS_DIR = DATA_DIR / "sets"
TABLES_DIR = DATA_DIR / "tables"
INDICE_H_DIR = TABLES_DIR / "indice_H"

YEAR = "2017"
SCENARIO = "RESTIT"

# Maps a plot attribute (Data_Parc_Gwad_2017 column) to the (min, max) bound
# columns that describe it per crop in Data_Cult -- the generic min/max
# agronomic envelope (altitude, slope, rainfall, plot size).
ELIGIBILITY_ATTRIBUTE_BOUNDS = {
    "ALTITUDE": ("ALTI_MIN", "ALTI_MAX"),
    "PENTE": ("PENTE_MIN", "PENTE_MAX"),
    "PLUVIO_PARC": ("PLUVIO_MIN", "PLUVIO_MAX"),
    "SURF_HA": ("SURF_PARC_MIN", "SURF_PARC_MAX"),
}


def build_categorical_eligibility_rules(
    data_parc: pd.DataFrame,
) -> list[tuple[list[str], pd.Series]]:
    """Guadeloupe-specific eligibility rules ported from MODELE.GMS "interdiction"
    equations that are not expressible as a simple per-attribute min/max envelope.
    Only a representative subset is ported so far (irrigation, soil type,
    chlordecone risk) -- the remaining region/commune/mechanization restrictions
    are deferred to a later milestone.
    """
    return [
        (["ME"], data_parc["IRRIG_PARC"] == 0),  # Eq_ME_IRR: melon requires irrigation
        (["MA_ROTA"], data_parc["IRRIG_PARC"] == 0),  # Eq_MA_ROTA_IRR
        # Eq_AN_SOL_Parc: pineapple forbidden on calcareous soil (TYPE_SOL=2)
        (["AN_NU", "AN_PA"], data_parc["TYPE_SOL"] == 2),
        # Eq_ME_SOL_Parc: melon forbidden on non-calcareous Grande-Terre soils or Basse-Terre
        (["ME"], data_parc["TYPE_SOL"].isin([2, 3, 4]) | (data_parc["ILE"] == 1)),
        (["IG_TUT"], data_parc["RISQUE_CLD"] <= 3),  # Eq_IG_CLD: chlordecone risk
        (["PN_PIQ"], data_parc["RISQUE_CLD"] == 1),  # Eq_PN_PIQ_CLD: chlordecone risk
    ]


def compute_farm_surface_ha(plot_surface: pd.Series, expl_parc: pd.DataFrame) -> pd.Series:
    merged = expl_parc.assign(surface=expl_parc["plot"].map(plot_surface))
    return merged.groupby("farm")["surface"].sum()


def build_dataset() -> Dataset:
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
    data_cult = read_wide_table(TABLES_DIR / "Data_Cult.txt")
    data_otk = read_wide_table(TABLES_DIR / "Data_OTK.txt")
    matrice_otk_cult = read_wide_table(TABLES_DIR / f"Matrice_OTK_Cult_{SCENARIO}.txt")
    prix_cult = read_wide_table(INDICE_H_DIR / "Prix_Cult.txt")[YEAR]
    rdt_cult = read_wide_table(INDICE_H_DIR / "Rdt_Cult.txt")[YEAR]
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

    plot_attributes = data_parc[list(ELIGIBILITY_ATTRIBUTE_BOUNDS.keys())]
    crop_bounds = data_cult.T
    eligibility_mask = compute_eligibility_mask(
        plot_attributes, crop_bounds, ELIGIBILITY_ATTRIBUTE_BOUNDS
    )
    for crops, condition in build_categorical_eligibility_rules(data_parc):
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
        "farm_surface_ha": farm_surface_ha,
        "eligibility_mask": eligibility_mask,
        "eligible_pairs": eligible_pairs,
        "margin_per_ha_cult": margin_per_ha_cult,
    }

    return Dataset(sets=sets, parameters=parameters, scalars={})


if __name__ == "__main__":
    dataset = build_dataset()
    print(f"crops: {len(dataset.sets['crops'])}")
    print(f"soils: {len(dataset.sets['soils'])}")
    print(f"otk: {len(dataset.sets['otk'])}")
    print(f"plots (expl_parc rows): {len(dataset.parameters['expl_parc'])}")
    print(f"farms: {dataset.parameters['expl_parc']['farm'].nunique()}")
    print(f"farm_surface_ha sample:\n{dataset.parameters['farm_surface_ha'].head()}")
