from case_studies.guadeloupe.domain.crop_labels import CROP_LABELS, label_for


def test_label_for_returns_explicit_name_for_known_codes():
    assert label_for("CS") == "Sugarcane"
    assert label_for("AN") == "Pineapple"
    assert label_for("ME") == "Melon"


def test_label_for_falls_back_to_the_raw_code_when_unmapped():
    assert label_for("ZZZ_UNKNOWN") == "ZZZ_UNKNOWN"


def test_market_gardening_subtypes_decode_mulch_and_irrigation():
    assert label_for("MA_BAG_BIO_I") == "Open-field market gardening (bagasse, BIO, irrigated)"
    assert label_for("MA_PAI_NON_NI") == "Open-field market gardening (straw, NON, rain-fed)"


def test_all_twenty_four_mulch_subtypes_are_labelled():
    subtypes = [code for code in CROP_LABELS if code.startswith(("MA_BAG_", "MA_BRF_", "MA_PAI_"))]
    assert len(subtypes) == 24


def test_all_labels_are_non_empty_strings():
    assert CROP_LABELS
    assert all(isinstance(name, str) and name.strip() for name in CROP_LABELS.values())
