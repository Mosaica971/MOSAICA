import pandas as pd

from case_studies.guadeloupe.farm_typology import compute_base_crop_group


def test_compute_base_crop_group_maps_rpg_codes_to_base_groups():
    cult_2015 = pd.Series([6, 4, 10], index=["P1", "P2", "P3"])
    cult_2016 = pd.Series([6, 4, 10], index=["P1", "P2", "P3"])
    cult_2017 = pd.Series([6, 4, 13], index=["P1", "P2", "P3"])

    result = compute_base_crop_group(cult_2015, cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "CS", "P2": "BA", "P3": "ME"}


def test_compute_base_crop_group_covers_every_rpg_code():
    codes = list(range(1, 21))
    cult_2017 = pd.Series(codes, index=[f"P{c}" for c in codes])
    # Use a non-fallow prior-year code (6) everywhere so the continuity override never
    # fires, isolating the base mapping table itself.
    cult_2015 = pd.Series(6, index=cult_2017.index)
    cult_2016 = pd.Series(6, index=cult_2017.index)

    result = compute_base_crop_group(cult_2015, cult_2016, cult_2017)

    expected = {
        "P1": "AG", "P2": "AN", "P3": "BC", "P4": "BA", "P5": "VE", "P6": "CS",
        "P7": "PN", "P8": "MA", "P9": "MA", "P10": "JA", "P11": "MA", "P12": "MA",
        "P13": "ME", "P14": "NC", "P15": "MA", "P16": "PN", "P17": "PN", "P18": "IG",
        "P19": "VE", "P20": "VE",
    }
    assert result.to_dict() == expected


def test_compute_base_crop_group_applies_fallow_continuity_override():
    # cult_2015, cult_2016, cult_2017 all in {0, 10, 14} -> cult_2017 forced to 14 (NC),
    # per old_code_gms_format_now_txt/ENTREES.txt:50-57.
    cult_2015 = pd.Series([10], index=["P1"])
    cult_2016 = pd.Series([0], index=["P1"])
    cult_2017 = pd.Series([10], index=["P1"])  # would otherwise map to JA

    result = compute_base_crop_group(cult_2015, cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "NC"}


def test_compute_base_crop_group_does_not_override_when_one_year_is_not_fallow():
    cult_2015 = pd.Series([6], index=["P1"])  # 2015 was sugarcane, not fallow
    cult_2016 = pd.Series([10], index=["P1"])
    cult_2017 = pd.Series([10], index=["P1"])

    result = compute_base_crop_group(cult_2015, cult_2016, cult_2017)

    assert result.to_dict() == {"P1": "JA"}
