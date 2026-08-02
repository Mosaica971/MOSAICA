"""What "agroecological" means in THIS dataset, rather than in general.

The bio-share indicator was deferred in 2026-07 as "not identifiable in the data", and the
2026-07-31 measurement showed why the obvious candidates fail: the 25 MA_{BAG,BRF,PAI}_*
variants are byte-identical copies of one conventional activity, so their BIO / VEG / FER /
NON suffixes carry nothing. Building a policy on them constrains a label, not a practice.

Two things in the data DO identify a practice, and they are different from one another:

**1. Agri-environmental payments (MAE).** Three tables pay for a named practice, and each
payment is attached to the crops that perform it:
  * `MAE_Recolte_Vert_Cult`  --  82 EUR/ha on all 18 sugarcane systems: harvesting green,
    i.e. without burning the field first;
  * `MAE_Jachere_Sol_Nu_Cult` -- 658 EUR/ha on the three intensive export bananas: the
    sanitary bare fallow that breaks the nematode cycle;
  * `MAE_Compost_Cult`       -- 900 EUR/ha on the ten fibre-cane systems, in the SMART
    scenario only (zero throughout RESTIT).
A crop drawing one of these is doing something the public purse has decided to pay for. That
is a defensible, sourced definition of "under an agri-environmental measure" -- and note it
is emphatically NOT organic: green-harvest cane is conventional cane that stopped burning.

**2. Certified-organic itineraries.** A handful of Data_OTK operations exist only for organic
systems -- the two organic fertilisations, the organic mulch sheet, the organic cattle
process. A crop whose ITK uses one is organic by construction of its own itinerary, which is
a stronger claim than a suffix in its name. On the real data this selects exactly MA_PLBIO
and MA_MOBIO -- the same two crops the nutrient figures single out independently, at 0 kg N
and IFT 0 against MA_ROTA's 277 and 15. Two unrelated routes to the same answer.

Keep the two apart in any reporting: one measures a policy's reach, the other a production
method. Adding them would count green-harvest cane as organic.
"""

from __future__ import annotations

import pandas as pd

# Data_OTK operations that only an organic itinerary uses.
ORGANIC_OPERATIONS: tuple[str, ...] = (
    "FERTI_MA_PLBIO",   # organic fertilisation, plein champ
    "FERTI_MA_MOBIO",   # organic fertilisation, sous abri
    "BACHE_MA_BIO",     # organic mulch sheet
    "PROC_BIO_BOVIN",   # organic cattle process
)


def compute_mae_per_ha_cult(
    mae_recolte_vert_cult: pd.Series,
    mae_jachere_sol_nu_cult: pd.Series,
    mae_compost_cult: pd.Series,
) -> pd.Series:
    """Agri-environmental payment per ha per year, by crop (EUR/ha/an).

    The same sum `compute_subsidy_per_ha_cult` folds into its `pdrg` term -- isolated here
    because a scenario needs to see the agri-environmental component on its own, and the
    total subsidy hides it among POSEI and national aid.
    """
    return (
        mae_recolte_vert_cult.fillna(0.0)
        + mae_jachere_sol_nu_cult.fillna(0.0)
        + mae_compost_cult.fillna(0.0)
    )


def compute_under_mae_cult(mae_per_ha_cult: pd.Series) -> pd.Series:
    """1.0 for a crop drawing an agri-environmental payment, 0.0 otherwise.

    A 0/1 rate is what makes "at least N hectares under an agri-environmental measure"
    expressible as an ordinary territory_indicator_bound: multiplied by plot surface, it
    sums to hectares.
    """
    return (mae_per_ha_cult.fillna(0.0) > 0).astype(float)


def compute_organic_cult(matrice_otk_cult: pd.DataFrame) -> pd.Series:
    """1.0 for a crop whose technical itinerary uses an organic-only operation.

    Reads the ITK matrix (operations x crops) rather than the crop code, so a crop is
    organic because of what it DOES, not because of how it is named.
    """
    present = [op for op in ORGANIC_OPERATIONS if op in matrice_otk_cult.index]
    if not present:
        return pd.Series(0.0, index=matrice_otk_cult.columns)
    used = (matrice_otk_cult.loc[present].fillna(0.0) > 0).any(axis=0)
    return used.astype(float)
