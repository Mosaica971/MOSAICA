from case_studies.guadeloupe.dashboard import comparison
from case_studies.guadeloupe.domain import zones


def test_the_seven_subregions_of_the_article_are_named():
    assert zones.REGION_CODES == (1, 2, 3, 4, 5, 6, 7)
    assert zones.REGION_LABELS["1"] == "CGT · Centre Grande-Terre"
    assert zones.REGION_LABELS["7"] == "MG · Marie-Galante"
    assert set(zones.REGION_LABELS) == {str(code) for code in zones.REGION_CODES}


def test_islands_are_named():
    assert zones.ISLAND_CODES == (1, 2, 3)
    assert set(zones.ISLAND_LABELS) == {str(code) for code in zones.ISLAND_CODES}


def test_region_label_accepts_int_and_str_and_falls_back():
    assert zones.region_label(3) == zones.REGION_LABELS["3"]
    assert zones.region_label("3") == zones.REGION_LABELS["3"]
    assert zones.region_label("TOTAL") == "TOTAL"


def test_comparison_still_exposes_the_moved_symbols():
    # pages/2_Comparaison.py reads them through `comparison`; the move must be invisible.
    assert comparison.REGION_LABELS is zones.REGION_LABELS
    assert comparison.ISLAND_LABELS is zones.ISLAND_LABELS
    assert comparison.REGION_CODES is zones.REGION_CODES
    assert comparison.ISLAND_CODES is zones.ISLAND_CODES
