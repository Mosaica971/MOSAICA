"""Region / island codes and their human names (GAMS source: DESCRIPTION_SETS.txt).

The seven REGION codes are the seven "areas with homogeneous soil and climate conditions"
of Chopin et al. (2015), Table 5. Tables and figures store the raw numeric codes; these
turn "1, 2, ..." into readable labels. Lives in domain/ rather than dashboard/ because
reporting/ needs it too, and reporting/ must not import dashboard/.
"""

REGION_LABELS: dict[str, str] = {
    "1": "CGT · Centre Grande-Terre",
    "2": "EGT · Est Grande-Terre",
    "3": "NGT · Nord Grande-Terre",
    "4": "NBT · Nord Basse-Terre",
    "5": "SEBT · Sud-Est Basse-Terre",
    "6": "SOBT · Sud-Ouest Basse-Terre",
    "7": "MG · Marie-Galante",
}
ISLAND_LABELS: dict[str, str] = {
    "1": "Basse-Terre",
    "2": "Grande-Terre",
    "3": "Marie-Galante",
}
# Full universe of region / island codes, so an exhaustive axis can include codes absent
# from a given allocation (as zero-height bars).
REGION_CODES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
ISLAND_CODES: tuple[int, ...] = (1, 2, 3)


def code_key(value: object) -> str:
    """Normalise a region/island code to its label-dict key.

    3, 3.0, "3", "3.0" and numpy's int64(3) all give "3"; anything not numeric (the "TOTAL"
    row of a calibration table, say) passes through as its own string so the callers below
    can fall back on it. Numeric codes reach here from three places with three types -- a
    CSV read by pandas gives floats, a set file gives strings, a groupby key gives numpy
    scalars -- which is why the conversion goes through float rather than string surgery.
    """
    try:
        return str(int(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value)


def region_label(value: object) -> str:
    return REGION_LABELS.get(code_key(value), str(value))


def island_label(value: object) -> str:
    return ISLAND_LABELS.get(code_key(value), str(value))
