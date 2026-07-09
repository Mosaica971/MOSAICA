import pandas as pd

# old_code_gms_format_now_txt/ENTREES.txt:62-103 -- RPG cult_2017 code -> base crop group.
_RPG_CODE_TO_BASE_GROUP: dict[int, str] = {
    1: "AG", 2: "AN", 3: "BC", 4: "BA", 5: "VE", 6: "CS", 7: "PN", 8: "MA",
    9: "MA", 10: "JA", 11: "MA", 12: "MA", 13: "ME", 14: "NC", 15: "MA",
    16: "PN", 17: "PN", 18: "IG", 19: "VE", 20: "VE",
}

# old_code_gms_format_now_txt/ENTREES.txt:49-57 -- if a plot's cult_2016 and cult_2017
# are both in this set, cult_2017 is forced to 14 (Non cultivé) before mapping. The
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
