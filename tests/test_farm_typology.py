import pytest
import pandas as pd

from case_studies.guadeloupe.domain.farm_typology import compute_avers, compute_base_crop_group, compute_type_expl


def test_compute_base_crop_group_maps_rpg_codes_to_base_groups():
    cult_2016 = pd.Series([6, 4, 10], index=["P1", "P2", "P3"])
    cult_2017 = pd.Series([6, 4, 13], index=["P1", "P2", "P3"])

    result = compute_base_crop_group(cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "CS", "P2": "BA", "P3": "ME"}


def test_compute_base_crop_group_covers_every_rpg_code():
    codes = list(range(1, 21))
    cult_2017 = pd.Series(codes, index=[f"P{c}" for c in codes])
    # Use a non-fallow prior-year code (6) everywhere so the continuity override never
    # fires, isolating the base mapping table itself.
    cult_2016 = pd.Series(6, index=cult_2017.index)

    result = compute_base_crop_group(cult_2016, cult_2017)

    expected = {
        "P1": "AG", "P2": "AN", "P3": "BC", "P4": "BA", "P5": "VE", "P6": "CS",
        "P7": "PN", "P8": "MA", "P9": "MA", "P10": "JA", "P11": "MA", "P12": "MA",
        "P13": "ME", "P14": "NC", "P15": "MA", "P16": "PN", "P17": "PN", "P18": "IG",
        "P19": "VE", "P20": "VE",
    }
    assert result.to_dict() == expected


def test_compute_base_crop_group_applies_fallow_continuity_override():
    # cult_2016 and cult_2017 both in {0, 10, 14} -> cult_2017 forced to 14 (NC), per
    # the executable condition in old_code_gms_format_now_txt/ENTREES.txt:49-57 (only
    # cult_2016/cult_2017 are checked -- the cult_2015 clause is commented out in GAMS).
    cult_2016 = pd.Series([0], index=["P1"])
    cult_2017 = pd.Series([10], index=["P1"])  # would otherwise map to JA

    result = compute_base_crop_group(cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "NC"}


def test_compute_base_crop_group_does_not_override_when_2016_is_not_fallow():
    cult_2016 = pd.Series([6], index=["P1"])  # 2016 was sugarcane, not fallow
    cult_2017 = pd.Series([10], index=["P1"])

    result = compute_base_crop_group(cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "JA"}


# Each scenario is a farm made of (base_group, area_ha) plots, hand-computed against
# the PART_* share formulas and threshold cascade at old_code_gms_format_now_txt/
# OPTIMISATION.txt:1467-1561, and the AVERS lookup at :1744-1758.
_TYPE_EXPL_SCENARIOS = {
    # PART_CAN = 8.34/8.34 = 1.0 >= 0.939 -> type 3 (Canniers) -> AVERS 0.30
    "canniers": ([("CS", 8.34)], 3, 0.30),
    # PART_PLU = 1.0 >= 0.522, all earlier branches false -> type 1 (Arboriculteurs)
    "arboriculteurs": ([("VE", 1.0)], 1, 1.30),
    # PART_BAN = 0.5/1.0 = 0.5 >= 0.364, PART_PAT < 0.327, PART_CAN < 0.625 -> type 2
    "bananiers": ([("BA", 0.5), ("AN", 0.5)], 2, 1.20),
    # PART_PAT = 1.0 >= 0.606, PART_CAN < 0.625 -> type 6 (Eleveurs)
    "eleveurs": ([("PN", 1.0)], 6, 2.40),
    # PART_MAR = 0.9 >= 0.801, earlier branches false -> type 7 (Maraichers)
    "maraichers": ([("MA", 0.9), ("AN", 0.1)], 7, 0.00),
    # PART_PAT = 0.4 (in [0.327, 0.606)), PART_CAN = 0.3 < 0.625 -> type 8
    "mixtes_canniers_eleveurs": ([("PN", 0.4), ("CS", 0.3), ("AN", 0.3)], 8, 2.30),
    # PART_MAR=0.5 < 0.801, PART_PLU=0 < 0.522, earlier branches false -> type 5
    "diversifies": ([("ME", 0.5), ("AN", 0.5)], 5, 0.55),
    # SURF_CUL = 0 (only NC area) -> forced to type 0 (Frichiers) regardless of shares
    "frichiers": ([("NC", 1.0)], 0, 0.00),
    # PART_CAN = 6.25/10 = 0.625 (in [0.625,0.939)) -> type 4. All of PART_MAR, PART_PLU,
    # PART_BC, PART_TT > 0 (AG->plu, BC->bc, IG->mar&tt) -> Bis 41 -> AVERS 0.50
    "canniers_diversifies_bis41": (
        [("CS", 6.25), ("AG", 1.0), ("BC", 1.0), ("IG", 1.75)], 4, 0.50
    ),
    # PART_CAN = 7/10 = 0.7 (in [0.625,0.939)) -> type 4. PART_PLU=PART_BC=PART_TT=0
    # (only PART_MAR=0.3 > 0) -> Bis 42 condition fires last -> AVERS 1.60
    "canniers_diversifies_bis42": ([("CS", 7.0), ("MA", 3.0)], 4, 1.60),
}


@pytest.mark.parametrize(
    "plots, expected_type, expected_avers", _TYPE_EXPL_SCENARIOS.values(),
    ids=_TYPE_EXPL_SCENARIOS.keys(),
)
def test_compute_type_expl_and_avers_classify_each_farm_type(
    plots, expected_type, expected_avers
):
    farm_plots = {"FARM": [f"P{i}" for i in range(len(plots))]}
    base_crop_group = pd.Series(
        {f"P{i}": group for i, (group, _area) in enumerate(plots)}
    )
    plot_surface_ha = {f"P{i}": area for i, (_group, area) in enumerate(plots)}

    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface_ha)
    avers = compute_avers(type_expl, type_expl_bis)

    assert type_expl["FARM"] == expected_type
    assert avers["FARM"] == pytest.approx(expected_avers)


def test_compute_type_expl_returns_nan_bis_for_non_type_4_farms():
    farm_plots = {"FARM": ["P0"]}
    base_crop_group = pd.Series({"P0": "CS"})
    plot_surface_ha = {"P0": 1.0}

    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface_ha)

    assert type_expl["FARM"] == 3
    assert pd.isna(type_expl_bis["FARM"])
