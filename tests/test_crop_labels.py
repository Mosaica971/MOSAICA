from case_studies.guadeloupe.domain.crop_labels import CROP_LABELS, label_for


def test_label_for_returns_explicit_name_for_known_codes():
    assert label_for("CS") == "Canne à sucre"
    assert label_for("AN") == "Ananas"
    assert label_for("ME") == "Melon"


def test_label_for_falls_back_to_the_raw_code_when_unmapped():
    assert label_for("ZZZ_UNKNOWN") == "ZZZ_UNKNOWN"


def test_maraichage_subtypes_decode_mulch_and_irrigation():
    assert label_for("MA_BAG_BIO_I") == "Maraîchage plein champ (bagasse, BIO, irrigué)"
    assert label_for("MA_PAI_NON_NI") == "Maraîchage plein champ (paille, NON, non irrigué)"


def test_all_labels_are_non_empty_strings():
    assert CROP_LABELS
    assert all(isinstance(name, str) and name.strip() for name in CROP_LABELS.values())
