import pandas as pd
import pytest

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.domain.crop_labels import CROP_LABELS
from case_studies.guadeloupe.domain.farm_typology import _RPG_CODE_TO_BASE_GROUP


def test_fine_variants_fold_onto_their_family():
    assert crop_families.base_group_for("CS_NGT_NISM") == "CS"
    assert crop_families.base_group_for("MA_BAG_BIO_I") == "MA"
    assert crop_families.base_group_for("VE_PLUIE") == "VE"
    assert crop_families.base_group_for("PN_TOUR") == "PN"


def test_fibre_cane_folds_onto_sugarcane():
    # The RPG nomenclature has a single sugarcane code (6): CF and CS are indistinguishable
    # in the observed data, so both must land on CS for the comparison to mean anything.
    assert crop_families.base_group_for("CF_NBT_NIM") == "CS"


def test_tomato_folds_onto_market_gardening():
    assert crop_families.base_group_for("TH") == "MA"


def test_aggregate_codes_map_to_themselves():
    for code in ("AG", "ME", "JA", "NC", "CS", "MA"):
        assert crop_families.base_group_for(code) == code


def test_unknown_code_raises():
    with pytest.raises(KeyError):
        crop_families.base_group_for("ZZ_UNKNOWN")


def test_every_labelled_crop_maps_to_an_observed_group():
    # Guard for the future: adding a crop to CROP_LABELS without declaring its family
    # breaks this test rather than silently skewing the calibration metrics.
    for code in CROP_LABELS:
        assert crop_families.base_group_for(code) in crop_families.OBSERVED_BASE_GROUPS


def test_observed_groups_match_the_rpg_vocabulary():
    assert crop_families.OBSERVED_BASE_GROUPS == frozenset(_RPG_CODE_TO_BASE_GROUP.values())


def test_base_groups_for_maps_a_series():
    crops = pd.Series({"P1": "CS_MG_IM", "P2": "TH", "P3": "AG"})
    result = crop_families.base_groups_for(crops)
    assert result.to_dict() == {"P1": "CS", "P2": "MA", "P3": "AG"}
    assert list(result.index) == ["P1", "P2", "P3"]
