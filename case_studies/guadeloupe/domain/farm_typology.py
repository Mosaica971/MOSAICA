from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

# context/gams/ENTREES.txt:62-103 -- RPG cult_2017 code -> base crop group.
_RPG_CODE_TO_BASE_GROUP: dict[int, str] = {
    1: "AG", 2: "AN", 3: "BC", 4: "BA", 5: "VE", 6: "CS", 7: "PN", 8: "MA",
    9: "MA", 10: "JA", 11: "MA", 12: "MA", 13: "ME", 14: "NC", 15: "MA",
    16: "PN", 17: "PN", 18: "IG", 19: "VE", 20: "VE",
}

# context/gams/ENTREES.txt:49-57 -- if a plot's cult_2016 and cult_2017
# are both in this set, cult_2017 is forced to 14 (not cultivated) before mapping. The
# source's own comment describes a 3-year (cult_2015/2016/2017) rule, but the
# cult_2015 clause of the actual IF condition is commented out (`*` in column 1) --
# only cult_2016/cult_2017 are checked by the code that actually runs.
_FALLOW_CONTINUITY_CODES = {0, 10, 14}


def compute_base_crop_group(cult_2016: pd.Series, cult_2017: pd.Series) -> pd.Series:
    both_fallow = cult_2016.isin(_FALLOW_CONTINUITY_CODES) & cult_2017.isin(
        _FALLOW_CONTINUITY_CODES
    )
    resolved_2017 = cult_2017.where(~both_fallow, 14)
    return resolved_2017.map(_RPG_CODE_TO_BASE_GROUP)


# context/gams/OPTIMISATION.txt:1467-1498 -- which base crop groups feed
# which SURF_*/PART_* family aggregate. A base group may feed more than one family (e.g.
# IG counts toward both "mar" and "tt"); "cultiv" is handled separately below since every
# group except NC counts toward it.
_FAMILIES_BY_BASE_GROUP: dict[str, tuple[str, ...]] = {
    "AG": ("plu",),
    "AN": (),
    "BA": ("ban",),
    "BC": ("bc",),
    "CS": ("can",),
    "IG": ("mar", "tt"),
    "JA": ("non",),
    "MA": ("mar",),
    "ME": ("mar",),
    "NC": ("non",),
    "PN": ("pat",),
    "VE": ("plu",),
}

_FAMILIES = ("can", "pat", "ban", "mar", "plu", "bc", "tt", "non")

# context/gams/OPTIMISATION.txt:1744-1758.
# Type 4 carries 1.40 in GAMS (OPTIMISATION.txt:1748), which is then overwritten by the
# TYPE_EXPL_Bis cascade below -- on the real data every type-4 farm gets a 41/42 value, so
# 1.40 never survives. It is kept here as an explicit fallback: without it, a type-4 farm
# with an unset Bis would map to NaN and propagate an undefined objective.
_RISK_AVERSION_BY_FARM_TYPE: dict[int, float] = {
    1: 1.30, 2: 1.20, 3: 0.30, 4: 1.40, 5: 0.55, 6: 2.40, 7: 0.00, 8: 2.30,
}
_RISK_AVERSION_BY_SECONDARY_TYPE: dict[int, float] = {41: 0.50, 42: 1.60}

# Readable names for the TYPE_EXPL codes. The eight types are those of Chopin et al. (2015)
# Table 2; 0 is the "no cultivated surface" short-circuit at the end of compute_farm_type,
# and -1 is np.select's default, which the cascade's final catch-all should make
# unreachable. ASCII only: these labels reach recap.md, which carries no accents.
FARM_TYPE_LABELS: dict[int, str] = {
    -1: "Unclassified",
    0: "No cultivated area",
    1: "Fruit growers",
    2: "Banana growers",
    3: "Specialised cane growers",
    4: "Diversified cane growers",
    5: "Diversified",
    6: "Livestock farmers",
    7: "Market gardeners",
    8: "Cane and livestock farmers",
}


def compute_farm_type(
    farm_plots: Mapping[str, Sequence[str]],
    base_crop_group: pd.Series,
    plot_surface_ha: Mapping[str, float],
) -> tuple[pd.Series, pd.Series]:
    """(farm type, secondary type) per farm from the area shares of its observed groups.

    GAMS TYPE_EXPL (ENTREES.txt): the 8 types of Chopin et al. (2015), 0 for a farm with no
    cultivated area. The secondary type only exists for type 4 (diversified cane growers)
    and refines its risk aversion; it is NaN elsewhere.
    """
    farms = list(farm_plots.keys())
    plot_to_farm = {plot: farm for farm, plots in farm_plots.items() for plot in plots}

    frame = pd.DataFrame(
        {
            "farm": pd.Series(plot_to_farm),
            "group": base_crop_group,
            "surface": pd.Series(plot_surface_ha),
        }
    ).dropna(subset=["farm", "group"])

    def surface_by_farm(groups: set[str]) -> pd.Series:
        subset = frame[frame["group"].isin(groups)]
        return subset.groupby("farm")["surface"].sum().reindex(farms, fill_value=0.0)

    all_groups = set(_FAMILIES_BY_BASE_GROUP.keys())
    surf_cultiv = surface_by_farm(all_groups - {"NC"})
    surf = {
        family: surface_by_farm(
            {group for group, families in _FAMILIES_BY_BASE_GROUP.items() if family in families}
        )
        for family in _FAMILIES
    }

    denom = surf_cultiv - surf["non"]
    safe_denom = denom.where(denom != 0, 1.0)

    def part(family: str) -> pd.Series:
        return (surf[family] / safe_denom).where(denom != 0, 0.0)

    part_can, part_pat, part_ban = part("can"), part("pat"), part("ban")
    part_mar, part_plu = part("mar"), part("plu")
    part_bc, part_tt = part("bc"), part("tt")

    # context/gams/OPTIMISATION.txt:1542-1552 -- the second, authoritative
    # cascade (the first one at :1530-1540 is dead code, unconditionally overwritten
    # before anything reads it; see the design spec for the full justification).
    conditions = [
        (part_can >= 0.625) & (part_can < 0.939),
        part_can >= 0.939,
        (part_can < 0.625) & (part_pat >= 0.606),
        (part_can < 0.625) & (part_pat < 0.606) & (part_pat >= 0.327),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban >= 0.364),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban < 0.364) & (part_mar >= 0.801),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban < 0.364) & (part_mar < 0.801)
        & (part_plu >= 0.522),
        (part_can < 0.625) & (part_pat < 0.327) & (part_ban < 0.364) & (part_mar < 0.801)
        & (part_plu < 0.522),
    ]
    choices = [4, 3, 6, 8, 2, 7, 1, 5]
    farm_type = pd.Series(
        np.select(conditions, choices, default=-1), index=farms
    ).astype(int)
    farm_type[surf_cultiv == 0] = 0

    # context/gams/OPTIMISATION.txt:1557-1561 -- sub-split for
    # TYPE_EXPL=4 farms. Both conditions are evaluated in GAMS's written order (41 then
    # 42); whichever is true last wins, so the 42 assignment below is applied after 41.
    farm_type_secondary = pd.Series(np.nan, index=farms)
    is_type_4 = farm_type == 4
    bis_41 = (part_mar > 0) | (part_plu > 0) | (part_bc > 0) | (part_tt > 0)
    bis_42 = (part_mar == 0) | (part_plu == 0) | (part_bc == 0) | (part_tt == 0)
    farm_type_secondary[is_type_4 & bis_41] = 41
    farm_type_secondary[is_type_4 & bis_42] = 42

    return farm_type, farm_type_secondary


def compute_risk_aversion(farm_type: pd.Series, farm_type_secondary: pd.Series) -> pd.Series:
    """Risk-aversion coefficient per farm, from its OBSERVED type -- GAMS indexes AVERS on
    STOCK_TYPE_EXPL("init") (OPTIMISATION.txt:1745), not on any re-derived typology.

    Type 4 goes through the Bis sub-cascade; its 1.40 base value only shows through if Bis
    is unset, which the real data never produces but which must not yield NaN.
    """
    aversion = farm_type.map(_RISK_AVERSION_BY_FARM_TYPE).fillna(0.0)
    is_type_4 = farm_type == 4
    secondary_aversion = farm_type_secondary.map(_RISK_AVERSION_BY_SECONDARY_TYPE)
    return aversion.where(~is_type_4, secondary_aversion.fillna(_RISK_AVERSION_BY_FARM_TYPE[4]))
