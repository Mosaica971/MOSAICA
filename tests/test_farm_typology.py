import pytest
import pandas as pd

from case_studies.guadeloupe.domain.farm_typology import compute_risk_aversion, compute_base_crop_group, compute_farm_type


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
    # the executable condition in context/gams/ENTREES.txt:49-57 (only
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
# the PART_* share formulas and threshold cascade at context/gams/
# OPTIMISATION.txt:1467-1561, and the AVERS lookup at :1744-1758.
_FARM_TYPE_SCENARIOS = {
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
    "plots, expected_type, expected_aversion", _FARM_TYPE_SCENARIOS.values(),
    ids=_FARM_TYPE_SCENARIOS.keys(),
)
def test_compute_type_expl_and_avers_classify_each_farm_type(
    plots, expected_type, expected_aversion
):
    farm_plots = {"FARM": [f"P{i}" for i in range(len(plots))]}
    base_crop_group = pd.Series(
        {f"P{i}": group for i, (group, _area) in enumerate(plots)}
    )
    plot_surface_ha = {f"P{i}": area for i, (_group, area) in enumerate(plots)}

    farm_type, farm_type_secondary = compute_farm_type(farm_plots, base_crop_group, plot_surface_ha)
    aversion = compute_risk_aversion(farm_type, farm_type_secondary)

    assert farm_type["FARM"] == expected_type
    assert aversion["FARM"] == pytest.approx(expected_aversion)


def test_compute_type_expl_returns_nan_bis_for_non_type_4_farms():
    farm_plots = {"FARM": ["P0"]}
    base_crop_group = pd.Series({"P0": "CS"})
    plot_surface_ha = {"P0": 1.0}

    farm_type, farm_type_secondary = compute_farm_type(farm_plots, base_crop_group, plot_surface_ha)

    assert farm_type["FARM"] == 3
    assert pd.isna(farm_type_secondary["FARM"])


def test_type_expl_labels_cover_the_eight_article_types_plus_the_edge_codes():
    from case_studies.guadeloupe.domain.farm_typology import (
        FARM_TYPE_LABELS,
        _RISK_AVERSION_BY_FARM_TYPE,
    )

    # The eight farm types of Chopin et al. (2015) Table 2, plus 0 (no cultivated surface)
    # and -1 (the np.select default, which no condition should ever leave standing).
    assert set(FARM_TYPE_LABELS) == {-1, 0, 1, 2, 3, 4, 5, 6, 7, 8}
    # Every type carrying a risk-aversion coefficient must be named.
    assert set(_RISK_AVERSION_BY_FARM_TYPE) <= set(FARM_TYPE_LABELS)


def test_avers_falls_back_to_the_type_4_base_value_when_bis_is_unset():
    """GAMS sets AVERS=1.40 for type 4 (OPTIMISATION.txt:1748) before the Bis cascade
    overwrites it. The real data always sets Bis, but an unset Bis must not yield NaN --
    a single NaN would make the Markowitz objective undefined for the whole territory."""
    import numpy as np
    import pandas as pd

    from case_studies.guadeloupe.domain.farm_typology import compute_risk_aversion

    farm_type = pd.Series({"E1": 4, "E2": 4, "E3": 4, "E4": 6})
    farm_type_secondary = pd.Series({"E1": 41.0, "E2": 42.0, "E3": np.nan, "E4": np.nan})

    aversion = compute_risk_aversion(farm_type, farm_type_secondary)

    assert aversion["E1"] == 0.50
    assert aversion["E2"] == 1.60
    assert aversion["E3"] == 1.40  # fallback, not NaN
    assert aversion["E4"] == 2.40
    assert aversion.notna().all()


def _one_farm(plots):
    """(farm_plots, base_crop_group, plot_surface_ha) for one farm of (group, area_ha) plots."""
    names = [f"P{i}" for i in range(len(plots))]
    groups = pd.Series({name: group for name, (group, _area) in zip(names, plots)})
    surface = {name: area for name, (_group, area) in zip(names, plots)}
    return {"FARM": names}, groups, surface


# (plots, type under "gams", type under "cultivated_area") -- the farms on which the two
# share denominators part ways. GAMS divides by SURF_CUL - SURF_NON, i.e. crops minus the
# NC area; "cultivated_area" by crops + fallow.
_DENOMINATOR_SCENARIOS = {
    # NC inflates every GAMS share: cane 5/(8-4) = 1.25 -> type 3; 5/8 = 0.625 -> type 4.
    "nc_inflates_the_cane_share": ([("CS", 5.0), ("MA", 3.0), ("NC", 4.0)], 3, 4),
    # More NC than crops: GAMS denominator 2-3 = -1, every share <= 0 -> catch-all type 5.
    # Without the NC, the farm is plainly all cane.
    "more_nc_than_crops": ([("CS", 2.0), ("NC", 3.0)], 5, 3),
    # Fallow is taken out by GAMS (cane 6/6 = 1.0 -> type 3) and counted in by the other
    # (6/10 = 0.6, under every threshold -> type 5).
    "fallow_counts_as_worked_land": ([("CS", 6.0), ("JA", 4.0)], 3, 5),
    # No NC, no fallow: same denominator, same type.
    "identical_without_nc_or_fallow": ([("PN", 4.0), ("CS", 3.0), ("AN", 3.0)], 8, 8),
    # Nothing cultivated at all stays type 0 either way.
    "no_cultivated_area": ([("NC", 2.0)], 0, 0),
}


@pytest.mark.parametrize(
    "plots, gams_type, cultivated_type", _DENOMINATOR_SCENARIOS.values(),
    ids=_DENOMINATOR_SCENARIOS.keys(),
)
def test_the_two_share_denominators(plots, gams_type, cultivated_type):
    farm_plots, groups, surface = _one_farm(plots)

    by_gams, _ = compute_farm_type(farm_plots, groups, surface, method="gams")
    by_area, _ = compute_farm_type(farm_plots, groups, surface, method="cultivated_area")

    assert by_gams["FARM"] == gams_type
    assert by_area["FARM"] == cultivated_type


def test_default_method_is_the_gams_denominator():
    """Callers that name no method -- and configs written before the option existed --
    must keep getting GAMS's shares."""
    farm_plots, groups, surface = _one_farm([("CS", 2.0), ("NC", 3.0)])

    assert compute_farm_type(farm_plots, groups, surface)[0]["FARM"] == 5


def test_unknown_typology_method_is_rejected():
    from case_studies.guadeloupe.domain.farm_typology import typology_method_from_config

    farm_plots, groups, surface = _one_farm([("CS", 1.0)])

    with pytest.raises(ValueError, match="cultivated"):
        compute_farm_type(farm_plots, groups, surface, method="cultivated")
    with pytest.raises(ValueError, match="farm_typology.method"):
        typology_method_from_config({"farm_typology": {"method": "cultivated"}})
    assert typology_method_from_config({}) == "gams"
    assert typology_method_from_config({"farm_typology": {"method": "cultivated_area"}}) == (
        "cultivated_area"
    )


@pytest.mark.parametrize("method", ["gams", "cultivated_area"])
@pytest.mark.parametrize(
    "plots", [[("JA", 2.0)], [("JA", 2.0), ("NC", 1.0)]], ids=["fallow", "fallow_and_nc"]
)
def test_a_fallow_only_farm_is_diversified(method, plots):
    """It holds land it works (fallow), so it is not type 0, and no crop, so every share is
    zero and the cascade ends on its last branch. Deliberately nothing looks at what the
    farm grew before -- neither the year before nor the observed type."""
    farm_plots, groups, surface = _one_farm(plots)

    farm_type, secondary = compute_farm_type(farm_plots, groups, surface, method=method)

    assert farm_type["FARM"] == 5
    assert compute_risk_aversion(farm_type, secondary)["FARM"] == pytest.approx(0.55)
