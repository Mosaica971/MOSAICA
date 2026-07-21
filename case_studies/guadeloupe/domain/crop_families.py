"""Fine crop code -> observed RPG base group.

The observed 2017 land use is only known at aggregate/RPG resolution -- 12 groups, see
farm_typology._RPG_CODE_TO_BASE_GROUP -- while the solver allocates one of the fine crops
of CULT_2017.set. Any observed-vs-simulated comparison must therefore fold the fine codes
back onto the 12 observed groups. Chopin et al. (2015) do exactly that in Fig. 4, which
compares "10 agricultural uses" and not the 36 cropping systems of their activity database.

Every fine code starts with its family token (CS_NGT_NISM, MA_BAG_BIO_I, ...), so the token
before the first underscore drives the mapping. Two tokens do not name their own group:
CF (fibre cane) folds onto CS because RPG code 6 covers both cane types, and TH (tomato)
folds onto MA because the RPG nomenclature files tomato under market gardening.
"""

import pandas as pd

NON_CULTIVATED = "NC"

_GROUP_BY_TOKEN: dict[str, str] = {
    "AG": "AG",   # agrumes
    "AN": "AN",   # ananas
    "BA": "BA",   # banane fruit
    "BC": "BC",   # banane plantain
    "CF": "CS",   # canne fibre -> canne (RPG code 6 covers both)
    "CS": "CS",   # canne a sucre
    "IG": "IG",   # igname et tubercules tropicaux
    "JA": "JA",   # jachere
    "MA": "MA",   # maraichage
    "ME": "ME",   # melon
    "NC": "NC",   # non cultive
    "PN": "PN",   # prairies & savanes
    "TH": "MA",   # tomate -> maraichage
    "VE": "VE",   # vergers hors agrumes
}

OBSERVED_BASE_GROUPS: frozenset[str] = frozenset(_GROUP_BY_TOKEN.values())


def base_group_for(crop: str) -> str:
    """Observed RPG group of a fine crop code. Raises KeyError on an undeclared family."""
    token = str(crop).split("_", 1)[0]
    try:
        return _GROUP_BY_TOKEN[token]
    except KeyError:
        raise KeyError(
            f"crop {crop!r}: family token {token!r} has no observed RPG group. "
            f"Declare it in crop_families._GROUP_BY_TOKEN."
        ) from None


def base_groups_for(crops: pd.Series) -> pd.Series:
    """Element-wise base_group_for over a plot-indexed crop Series."""
    return crops.map(base_group_for)
