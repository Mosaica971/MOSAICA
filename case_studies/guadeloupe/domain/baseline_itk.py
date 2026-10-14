"""Fine technical system (ITK) of each plot of the observed 2017 baseline.

The RPG says "export banana" or "sugarcane", never which technical system the plot ran --
and every per-ha rate the model knows (labour, yield, cost, nitrogen...) belongs to a fine
ITK, not to the aggregate group. GAMS closes that gap with deterministic rules on the plot's
attributes (island, region, slope, farm size, irrigation, skeletal soil) that fill
`Matrice_Parc_Cult` (ENTREES.txt:299-457), then zero the aggregate column. This module
ports those rules to the letter; the farm labour budget MO_Expl_init, the per-farm banana
reference REF_BAN_EXPL_init and every input-side indicator are computed on its output.

It is an assumption of the GAMS model, not an observation: no source says which ITK was
actually practised in 2017. Its merit is to depend on the plot and to match GAMS exactly
(MO_Expl_init reproduced to 0.001 h per farm, see docs/04-vigilance.md C.2).

The same observed groups also drive the irrigation flag: before any rule or equation reads
IRRIG_PARC, GAMS overwrites it on the plots whose 2017 crop implies water (ENTREES.txt:136-159).
`assume_baseline_irrigation` ports that step; it must run before `assign_baseline_itk` and
before the eligibility mask, as it does in GAMS.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# The eight aggregate RPG codes GAMS splits into fine ITKs and then zeroes (ENTREES.txt:313-457).
# They carry no ITK line in Matrice_OTK_Cult, hence no rate of their own. AG, JA, ME and NC
# are single crops and stand for themselves.
AGGREGATE_GROUPS: tuple[str, ...] = ("AN", "BA", "BC", "CS", "IG", "MA", "PN", "VE")

# DONNEES.txt:135: farm surface (ha) below which plastic-mulch pineapple AN_PA is not run.
AN_SURF_EXPL_MIN = 10.0
# ENTREES.txt:333-341: export-banana thresholds, written as literals in GAMS.
BA_FARM_SURFACE_MIN = 10.0
BA_SLOPE_MAX = 25.0
# ENTREES.txt:412-417: North/South-West Basse-Terre cane plots below this size are harvested
# semi-mechanically.
CS_BT_PLOT_SURFACE_MIN = 0.2

# ENTREES.txt:139-141: observed groups GAMS takes as irrigated wherever they stand off
# Basse-Terre (ILE > 1), whatever the irrigation-network map says.
IRRIGATED_OFF_BASSE_TERRE_GROUPS: tuple[str, ...] = ("BC", "MA", "BA", "AG", "ME", "IG")
# ENTREES.txt:156: an observed orchard plot strictly above this size (ha) is taken as irrigated.
VE_IRRIGATED_PLOT_SURFACE_MIN = 0.5

# Plot attributes the rules read (Data_Parc_Gwad columns, plus the farm surface the pipeline
# exposes as SURF_EXPL_PARC = Surf_Expl_Parc_init, ENTREES.txt:115-119).
REQUIRED_COLUMNS: tuple[str, ...] = (
    "REGION", "ILE", "PENTE", "IRRIG_PARC", "SOL_COURT", "SURF_HA", "SURF_EXPL_PARC",
)


def assume_baseline_irrigation(plot_data: pd.DataFrame, base_crop_group: pd.Series) -> pd.Series:
    """plot -> IRRIG_PARC as GAMS rewrites it from the observed 2017 crop (ENTREES.txt:136-159).

    The file column is the irrigation-network map (0/1). GAMS sets it to 1, in place and
    before MODELE.txt reads it, on three kinds of plot: one observed in plantain, market
    gardening, export banana, citrus, melon or yam off Basse-Terre (138-144); one observed
    in citrus anywhere (147-151); one observed in orchard and larger than 0.5 ha (155-159).
    The reasoning is that a crop grown there in 2017 had water, map or no map. Every
    irrigation-dependent ban (Eq_ME_IRR, Eq_MA_ROTA_IRR, Eq_BA_IRR, Eq_BC_IRR_*, Eq_AG_IRR,
    Eq_VE_IRR, the MA rule of the baseline ITK) and the water indicator then read the
    rewritten flag. The rewrite only ever raises a 0 to 1; see docs/04-vigilance.md G.10.

    `base_crop_group` is the resolved RPG group, i.e. GAMS's aggregate Matrice_Parc_Cult
    (ENTREES.txt:62-103) at the point the rewrite runs.
    """
    required = ("IRRIG_PARC", "ILE", "SURF_HA")
    missing = [column for column in required if column not in plot_data.columns]
    if missing:
        raise KeyError(f"assume_baseline_irrigation needs plot_data columns {missing}")

    group = base_crop_group.reindex(plot_data.index)
    assumed_irrigated = (
        (group.isin(IRRIGATED_OFF_BASSE_TERRE_GROUPS) & (plot_data["ILE"] > 1))
        | (group == "AG")
        | ((group == "VE") & (plot_data["SURF_HA"] > VE_IRRIGATED_PLOT_SURFACE_MIN))
    )
    return plot_data["IRRIG_PARC"].where(~assumed_irrigated, 1)


def assign_baseline_itk(plot_data: pd.DataFrame, base_crop_group: pd.Series) -> pd.Series:
    """plot -> fine crop of the observed 2017 baseline, by the GAMS rules of ENTREES.txt:299-457.

    `base_crop_group` is the resolved RPG group (farm_typology.compute_base_crop_group, i.e.
    after the fallow-continuity rule). A plot whose group no rule covers keeps NaN, as GAMS
    leaves it with no ITK at all -- on the 2017 data that never happens.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in plot_data.columns]
    if missing:
        raise KeyError(f"assign_baseline_itk needs plot_data columns {missing}")

    group = base_crop_group.reindex(plot_data.index)
    region = plot_data["REGION"]
    island = plot_data["ILE"]
    slope = plot_data["PENTE"]
    # Both flags are tested against 0 AND 1 separately, as GAMS does: a value that is neither
    # fires no rule rather than falling into a default branch.
    rain_fed = plot_data["IRRIG_PARC"] == 0
    irrigated = plot_data["IRRIG_PARC"] == 1
    deep_soil = plot_data["SOL_COURT"] == 0
    skeletal = plot_data["SOL_COURT"] == 1
    plot_surface = plot_data["SURF_HA"]
    farm_surface = plot_data["SURF_EXPL_PARC"]
    basse_terre = island == 1

    # Single crops keep their own code; the eight aggregates start empty and are filled below.
    itk = group.where(~group.isin(AGGREGATE_GROUPS)).astype(object)

    def assign(family: str, condition: pd.Series, crop: str) -> None:
        itk[(group == family) & condition] = crop

    # Orchards (ENTREES.txt:304-313): South-East Basse-Terre is the rain-fed system.
    assign("VE", region == 5, "VE_PLUIE")
    assign("VE", region != 5, "VE_BTGT")

    # Pineapple (318-327): plastic mulch only on farms large enough to run it.
    assign("AN", farm_surface >= AN_SURF_EXPL_MIN, "AN_PA")
    assign("AN", farm_surface < AN_SURF_EXPL_MIN, "AN_NU")

    # Export banana (332-346): irrigated off Basse-Terre; on Basse-Terre, steep plots are the
    # "perched" system and flat ones intensive or semi-intensive by farm size.
    flat = slope <= BA_SLOPE_MAX
    assign("BA", flat & basse_terre & (farm_surface >= BA_FARM_SURFACE_MIN), "BA_INT")
    assign("BA", flat & basse_terre & (farm_surface < BA_FARM_SURFACE_MIN), "BA_SINT")
    assign("BA", ~flat & basse_terre, "BA_PER")
    assign("BA", ~basse_terre, "BA_IRR")

    # Plantain (351-359) and yam (364-372): Basse-Terre systems vs the others.
    assign("BC", ~basse_terre, "BC_GTMG")
    assign("BC", basse_terre, "BC_BT")
    assign("IG", ~basse_terre, "IG_PLA")
    assign("IG", basse_terre, "IG_TUT")

    # Market gardening (377-395): the tomato-cabbage-fallow rotation on rain-fed Basse-Terre,
    # the irrigated rotation everywhere else.
    assign("MA", basse_terre & rain_fed, "MA_TO_CO_JA")
    assign("MA", basse_terre & irrigated, "MA_ROTA")
    assign("MA", ~basse_terre, "MA_ROTA")

    # Grassland (400-405): tethered livestock on every plot (the SURF >= 0 test is always true).
    assign("PN", plot_surface >= 0, "PN_PIQ")

    # Sugarcane (410-458): harvest mechanisation by region, skeletal soil and plot size.
    north_west_bt = region.isin([4, 6])
    assign("CS", north_west_bt & (plot_surface < CS_BT_PLOT_SURFACE_MIN), "CS_BT_NISM")
    assign("CS", north_west_bt & (plot_surface >= CS_BT_PLOT_SURFACE_MIN), "CS_BT_NIM")
    assign("CS", region == 5, "CS_SBT_NIM")
    for code, zone in ((3, "NGT"), (2, "EGT"), (1, "CGT")):
        assign("CS", (region == code) & deep_soil, f"CS_{zone}_NIM")
        assign("CS", (region == code) & skeletal, f"CS_{zone}_NISM")
    assign("CS", region == 7, "CS_MG_NISM")

    return itk.replace({None: np.nan}).rename("crop")
