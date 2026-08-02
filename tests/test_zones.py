from apps.dashboard import comparison
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


def test_code_key_normalises_every_type_a_code_arrives_as():
    """A code reaches the labellers as a str (set file), a float (pandas CSV) or a numpy
    scalar (groupby key); all three must land on the same label-dict key."""
    assert zones.code_key(3) == zones.code_key(3.0) == zones.code_key("3") == "3"
    assert zones.code_key("3.0") == "3"
    assert zones.code_key("TOTAL") == "TOTAL"  # non-numeric passes through for the fallback


def test_comparison_still_exposes_the_moved_symbols():
    # pages/2_Comparaison.py reads them through `comparison`; the move must be invisible.
    assert comparison.REGION_LABELS is zones.REGION_LABELS
    assert comparison.ISLAND_LABELS is zones.ISLAND_LABELS
    assert comparison.REGION_CODES is zones.REGION_CODES
    assert comparison.ISLAND_CODES is zones.ISLAND_CODES


def test_the_labellers_are_the_domain_ones_not_a_second_implementation():
    """These used to be two implementations normalising codes differently, so the same
    region could read two ways depending on which one a page called. Aliases, not copies."""
    assert comparison.label_region is zones.region_label
    assert comparison.label_island is zones.island_label
