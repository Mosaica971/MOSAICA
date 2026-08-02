"""Annual soil organic carbon balance: crop residues + organic amendments - mineralization.

Faithful to OPTIMISATION.txt:2880-2947, with two documented departures (see docs/04-vigilance.md):
the GAMS iterates the stock over years (C_ORG = C_ORG + flux, NB_BOUCLE loop) while this
model is single-year, so only the *annual flux* is ported; and the amendment term is not
annualized by Duree_Cycle/Duree_Plant, unlike azote/GES/costs -- that is what the GAMS does
(OPTIMISATION.txt:2919), and it looks like a source-side oversight.

All carbon quantities are in t C/ha (stocks) or t C/ha/year (flows).
"""

import pandas as pd

# Data_Parc's numeric TYPE_SOL -> Data_Sol column name, per OPTIMISATION.txt:2880-2896.
# CAREFUL: Data_Sol's own column order (and SOL.set) is NITISOL, ANDOSOL, FERRALSOL,
# AUTRES, VERTISOL -- a DIFFERENT order. Indexing Data_Sol positionally yields wrong but
# plausible coefficients, so always map by name through this dict.
TYPE_SOL_TO_SOIL_NAME = {
    1: "VERTISOL",
    2: "FERRALSOL",
    3: "ANDOSOL",
    4: "NITISOL",
    5: "AUTRES",
}

# PART_C_INIT is a percentage; DENS is t/m3, PROF is m, and 10000 m2 = 1 ha.
_PERCENT = 100.0
_M2_PER_HA = 10000.0


def _soil_attribute_by_plot(
    data_parc: pd.DataFrame, data_sol: pd.DataFrame, attribute: str
) -> pd.Series:
    """One Data_Sol row (KAER, DENS, PROF...) resolved per plot through TYPE_SOL."""
    soil_names = data_parc["TYPE_SOL"].map(TYPE_SOL_TO_SOIL_NAME)
    return soil_names.map(data_sol.loc[attribute])


def compute_residue_carbon_per_ha_cult(data_cult: pd.DataFrame) -> pd.Series:
    """Carbon returned by crop residues (t C/ha/year): aerial biomass plus root biomass,
    times carbon content, times the humification coefficient."""
    aerial = data_cult.loc["BIOM_AER"]
    total_residue = aerial * (1.0 + data_cult.loc["RAC"])
    return total_residue * data_cult.loc["CARB"] * data_cult.loc["HRES"]


def compute_amendment_carbon_per_ha_cult(
    data_otk: pd.DataFrame, matrice_otk_cult: pd.DataFrame
) -> pd.Series:
    """Carbon brought by organic amendments (t C/ha/year): sum over the crop's ITK
    operations of DOSE * HUM * CARB * FHUM. Deliberately NOT annualized -- see module
    docstring."""
    per_operation = (
        data_otk["DOSE"] * data_otk["HUM"] * data_otk["CARB"] * data_otk["FHUM"]
    )
    return matrice_otk_cult.multiply(per_operation, axis=0).sum(axis=0)


def compute_carbon_input_per_ha_cult(
    data_cult: pd.DataFrame, data_otk: pd.DataFrame, matrice_otk_cult: pd.DataFrame
) -> pd.Series:
    """Total carbon input per ha per year: residues + amendments."""
    residues = compute_residue_carbon_per_ha_cult(data_cult)
    amendments = compute_amendment_carbon_per_ha_cult(data_otk, matrice_otk_cult)
    return residues.add(amendments.reindex(residues.index).fillna(0.0), fill_value=0.0)


def compute_initial_soil_carbon_per_ha_plot(
    data_parc: pd.DataFrame, data_sol: pd.DataFrame
) -> pd.Series:
    """Initial soil organic carbon stock (t C/ha) per plot, from its measured carbon
    fraction and its soil type's bulk density and depth."""
    density = _soil_attribute_by_plot(data_parc, data_sol, "DENS")
    depth = _soil_attribute_by_plot(data_parc, data_sol, "PROF")
    return data_parc["PART_C_INIT"] / _PERCENT * density * depth * _M2_PER_HA


def compute_mineralization_per_ha_plot(
    allocation: pd.Series,
    data_parc: pd.DataFrame,
    data_sol: pd.DataFrame,
    data_cult: pd.DataFrame,
    initial_carbon: pd.Series,
) -> pd.Series:
    """Carbon lost to mineralization (t C/ha/year) on each allocated plot: the plot's
    carbon stock times its soil's aerobic mineralization rate times the crop's KCROP."""
    if allocation.empty:
        return pd.Series(dtype=float)
    kaer = _soil_attribute_by_plot(data_parc, data_sol, "KAER").reindex(allocation.index)
    kcrop = pd.Series(
        data_cult.loc["KCROP"].reindex(allocation.to_numpy()).to_numpy(),
        index=allocation.index,
    )
    return initial_carbon.reindex(allocation.index) * kaer * kcrop


def compute_carbon_balance_per_ha_plot(
    allocation: pd.Series,
    data_parc: pd.DataFrame,
    data_sol: pd.DataFrame,
    data_cult: pd.DataFrame,
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
) -> pd.Series:
    """Net annual carbon balance (t C/ha/year) per allocated plot. Negative means the
    system depletes soil carbon."""
    if allocation.empty:
        return pd.Series(dtype=float)
    inputs_by_crop = compute_carbon_input_per_ha_cult(data_cult, data_otk, matrice_otk_cult)
    inputs = pd.Series(
        inputs_by_crop.reindex(allocation.to_numpy()).to_numpy(), index=allocation.index
    )
    initial_carbon = compute_initial_soil_carbon_per_ha_plot(data_parc, data_sol)
    outputs = compute_mineralization_per_ha_plot(
        allocation, data_parc, data_sol, data_cult, initial_carbon
    )
    return inputs - outputs
