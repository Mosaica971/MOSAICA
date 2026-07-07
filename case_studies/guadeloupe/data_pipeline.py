from pathlib import Path

import pandas as pd

from core.data.dataset import Dataset
from core.data.eligibility import compute_eligibility_mask, eligible_pairs_from_mask
from core.data.readers import read_flat_set, read_mapping_set, read_wide_table

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SETS_DIR = DATA_DIR / "sets"
TABLES_DIR = DATA_DIR / "tables"
INDICE_H_DIR = TABLES_DIR / "indice_H"

YEAR = "2017"
SCENARIO = "RESTIT"

# Maps a plot attribute (Data_Parc_Gwad_2017 column) to the (min, max) bound
# columns that describe it per crop in Data_Cult. Only the generic min/max
# agronomic envelope is covered here (altitude, slope, rainfall, plot size) --
# categorical rules (chlordecone risk, irrigation, region restrictions) are a
# separate, Guadeloupe-specific concern deferred to a later milestone.
ELIGIBILITY_ATTRIBUTE_BOUNDS = {
    "ALTITUDE": ("ALTI_MIN", "ALTI_MAX"),
    "PENTE": ("PENTE_MIN", "PENTE_MAX"),
    "PLUVIO_PARC": ("PLUVIO_MIN", "PLUVIO_MAX"),
    "SURF_HA": ("SURF_PARC_MIN", "SURF_PARC_MAX"),
}


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

    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)

    plot_attributes = data_parc[list(ELIGIBILITY_ATTRIBUTE_BOUNDS.keys())]
    crop_bounds = data_cult.T
    eligibility_mask = compute_eligibility_mask(
        plot_attributes, crop_bounds, ELIGIBILITY_ATTRIBUTE_BOUNDS
    )
    eligible_pairs = eligible_pairs_from_mask(eligibility_mask)

    # Simplified margin proxy (price * yield, i.e. gross product before variable
    # costs and subsidies) used to bootstrap the optimization model. The full
    # GAMS MB_Ha_Cult formula also nets out OTK-based variable costs and POSEI/
    # national/PDRG subsidies -- deferred until those tables are wired in.
    revenue_per_ha_cult = prix_cult * rdt_cult

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
        "revenue_per_ha_cult": revenue_per_ha_cult,
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
