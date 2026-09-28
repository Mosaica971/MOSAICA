"""What MOSAICA already knows, crop by crop, of what MAELIA needs to simulate a new crop.

MAELIA simulates a crop from three files (docs/maelia/reference.md): a species column in
`especesCultivees.csv` (yield, phenology, water, nitrogen and carbon parameters), one ITK
column per situation in `reglesDeDecisions*.csv` (operations, dates, triggers, doses, work
time), and the economics (`prixVentes`, `primes`, `chargesOp`). None of the Guadeloupe crops
exists in the guide (docs/maelia M.2), so each must be created. This module reads the GAMS
tables MOSAICA holds and says, per fine crop, which of those parameters they already give,
which they only approximate, and which are missing.

`scripts/build_maelia_crop_table.py` renders it into docs/maelia/crop-parameters.md.
"""

from __future__ import annotations

import pandas as pd

from case_studies.guadeloupe.domain.crop_families import base_group_for
from case_studies.guadeloupe.domain.crop_labels import label_for
from case_studies.guadeloupe.domain.itk import annual_rate_per_ha

KNOWN, PARTIAL, MISSING, NONE = "✓", "~", "✗", "—"

# MAELIA's operation types (ITK application, § 4.7; tillage is PREPA + REPRISE there). A
# MOSAICA operation with none of these types has no slot in a MAELIA ITK: its labour hours
# and its cost are lost in the translation unless folded into another operation.
MAELIA_OPERATION_TYPES = (
    "tillage", "sowing", "hoeing", "fertilisation", "crop_protection", "irrigation", "harvest",
)
_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("irrigation", ("EAU_IRRIG", "MAT_IRRIG", "POSE_IRRIG")),
    ("fertilisation", ("EPAND_", "FERTI", "FUMIER", "ORGANOR", "AMENDEMENT", "UREE", "KCL",
                       "KNO3", "K2SO4", "DAP_")),
    ("crop_protection", ("PULVE_",)),  # sprayer passes; "PULVERISEUR" is a disc harrow
    ("sowing", ("PLANTATION_", "SEMIS_", "PLANTS_", "SEMENCES_", "VITROPLANTS")),
    ("harvest", ("RECOLTE_", "COUPE_TRANSP_CHARG_")),
    ("hoeing", ("BINAGE", "SARCLAGE_", "DESHERB_MANUEL", "BUTTAGE_")),
    ("tillage", ("LABOUR", "SOUS_SOLAGE", "ROME_PLOW", "PULVERISEUR", "DECHAUMAGE", "HERSAGE",
                 "CULTIVATEUR", "ROTOBECHE", "BECHAGE", "SILLONNAGE", "BILLONAGE", "GRIFFAGE",
                 "PREPA_MANU_SOL", "TROU_MANU", "DESTRUCT_PREC")),
)
# A product is a pesticide when Data_OTK gives it a TFI or a fate property (the PPDB columns).
_PESTICIDE_COLUMNS = ("IFT", "DT50", "KOC")


def maelia_operation_type(operation: str, operation_data: pd.DataFrame) -> str | None:
    """The MAELIA operation type of a MOSAICA operation (a Matrice_OTK_Cult row), or None.

    NPK fertilisers are named by their grades (`14_04_25_BA_INT`), hence the digit test.
    """
    for kind, prefixes in _PREFIXES:
        if operation.startswith(prefixes):
            return kind
    if operation[:2].isdigit():
        return "fertilisation"
    if operation in operation_data.index:
        row = operation_data.loc[operation]
        if any(float(row.get(col, 0) or 0) != 0 for col in _PESTICIDE_COLUMNS):
            return "crop_protection"
    return None


def operation_types(crop_operation_matrix: pd.DataFrame,
                    operation_data: pd.DataFrame) -> pd.Series:
    """MAELIA type of every operation of the matrix (None where MAELIA has no slot)."""
    return pd.Series({op: maelia_operation_type(op, operation_data)
                      for op in crop_operation_matrix.index}, dtype=object)


def _irrigation_cell(has_ops: bool, water_need: float) -> str:
    # The need is annual in effect: BESOIN_EAU_01..12 are flat over the year (vigilance C.4).
    if has_ops and water_need > 0:
        return f"{KNOWN} ops + need"
    if has_ops:
        return f"{PARTIAL} ops, no need"
    if water_need > 0:
        return f"{PARTIAL} need, no op"
    return NONE


def _lifespan_cell(plantation_years: float, cycle_months: float) -> str:
    if cycle_months > 12:
        return f"{MISSING} {cycle_months:g}-month cycle"
    if plantation_years > 1:
        return f"{MISSING} {plantation_years:g}-yr plantation"
    return "annual"


def _operations_cell(n_typed: int, n_used: int) -> str:
    symbol = KNOWN if n_typed == n_used else PARTIAL if n_typed else MISSING
    return f"{symbol} {n_typed}/{n_used}"


def _maelia_model(crop: str) -> str:
    group = base_group_for(crop)
    if group == "PN":
        return "HerbSim (not NC)"
    if group == "JA":
        return "gel (no ITK)"
    return "AqYield(NC)"


def crop_coverage(
    crop_data: pd.DataFrame,
    operation_data: pd.DataFrame,
    crop_operation_matrix: pd.DataFrame,
    crop_yield: pd.Series,
    crop_price: pd.Series,
    crop_subsidy_per_ha: pd.Series,
    crop_variable_cost_per_ha: pd.Series,
    crop_plantation_duration: pd.Series,
    crop_cycle_duration: pd.Series,
) -> tuple[pd.DataFrame, list[str]]:
    """One row per fine crop that carries an ITK, one column per MAELIA parameter block.

    Returns the table and the codes left out: those with no operation at all (the RPG group
    headers `CS`, `BA`… and `NC`), which MOSAICA never allocates a management to.
    """
    matrix = crop_operation_matrix.fillna(0)
    types = operation_types(matrix, operation_data)
    labour_per_op = (operation_data["DOSE"] * operation_data["MO_EXPL"]).reindex(matrix.index)
    amortized = (operation_data["AMORTI"] == 1).reindex(matrix.index, fill_value=False)
    labour = annual_rate_per_ha(matrix, labour_per_op.fillna(0), crop_plantation_duration,
                                crop_cycle_duration, amortized)
    untyped = types.isna()
    labour_untyped = annual_rate_per_ha(matrix, labour_per_op.fillna(0).where(untyped, 0),
                                        crop_plantation_duration, crop_cycle_duration, amortized)
    water_need = crop_data.loc[[f"BESOIN_EAU_{m:02d}" for m in range(1, 13)]].sum()

    rows, left_out = [], []
    for crop in matrix.columns:
        used = matrix.index[matrix[crop] != 0]
        if len(used) == 0:
            left_out.append(crop)
            continue
        kinds = set(types[used].dropna())
        n_typed = int(types[used].notna().sum())
        total_h = float(labour.get(crop, 0))
        share = float(labour_untyped.get(crop, 0)) / total_h if total_h > 0 else 0.0
        row = {
            "crop": crop,
            "label": label_for(crop),
            "family": base_group_for(crop),
            "yield": KNOWN if crop_yield.get(crop, 0) > 0 else MISSING,
            "phenology": MISSING,
            "water_roots": PARTIAL if crop_data.at["KCROP", crop] > 0
                           and crop_data.at["LONG_RAC", crop] > 0 else MISSING,
            "biomass_carbon": PARTIAL if crop_data.at["BIOM_AER", crop] > 0
                              and crop_data.at["CARB", crop] > 0 else MISSING,
            "nitrogen_need": MISSING,
            "operations": _operations_cell(n_typed, len(used)),
            "labour_untyped": f"{share:.0%}",
            "dates_triggers": MISSING,
            "fertilisation": KNOWN if "fertilisation" in kinds else NONE,
            "crop_protection": KNOWN if "crop_protection" in kinds else NONE,
            "irrigation": _irrigation_cell("irrigation" in kinds, float(water_need[crop])),
            "price": KNOWN if crop_price.get(crop, 0) > 0 else "0",
            "subsidies": KNOWN if crop_subsidy_per_ha.get(crop, 0) > 0 else "none",
            "costs": KNOWN if crop_variable_cost_per_ha.get(crop, 0) > 0 else MISSING,
            "lifespan": _lifespan_cell(float(crop_plantation_duration.get(crop, 1)),
                                       float(crop_cycle_duration.get(crop, 12))),
            "maelia_model": _maelia_model(crop),
        }
        if row["family"] == "JA":  # MAELIA's set-aside (`gel`) needs no species and no ITK
            for key in ("yield", "phenology", "water_roots", "biomass_carbon", "nitrogen_need",
                        "dates_triggers"):
                row[key] = NONE
        rows.append(row)
    return pd.DataFrame(rows), left_out


# (column, header) of the per-crop table, grouped by the MAELIA file each block fills.
COLUMNS: tuple[tuple[str, str], ...] = (
    ("yield", "Yield"),
    ("phenology", "Phenology"),
    ("water_roots", "Kc, roots"),
    ("biomass_carbon", "Biomass, C"),
    ("nitrogen_need", "N need"),
    ("operations", "Ops typed"),
    ("labour_untyped", "Untyped h"),
    ("dates_triggers", "Dates, triggers"),
    ("fertilisation", "Fertilisation"),
    ("crop_protection", "Protection"),
    ("irrigation", "Irrigation"),
    ("price", "Price"),
    ("subsidies", "Subsidies"),
    ("costs", "Op. costs"),
    ("lifespan", "Lifespan"),
    ("maelia_model", "MAELIA model"),
)

FAMILY_NAMES = {
    "AG": "Citrus", "AN": "Pineapple", "BA": "Dessert banana", "BC": "Plantain",
    "CS": "Sugarcane and fibre cane", "IG": "Yam", "JA": "Fallow",
    "MA": "Market gardening (incl. tomato)", "ME": "Melon", "PN": "Grassland",
    "VE": "Orchards",
}


def render_table(coverage: pd.DataFrame) -> str:
    """The per-crop table, one Markdown table per family."""
    head = "| code | crop | " + " | ".join(h for _, h in COLUMNS) + " |"
    rule = "|" + "---|" * (len(COLUMNS) + 2)
    out = []
    for family, block in coverage.groupby("family", sort=True):
        out += [f"### {FAMILY_NAMES.get(family, family)} ({len(block)})", "", head, rule]
        for _, row in block.iterrows():
            cells = " | ".join(str(row[c]) for c, _ in COLUMNS)
            out.append(f"| `{row['crop']}` | {row['label']} | {cells} |")
        out.append("")
    return "\n".join(out)


def render_summary(coverage: pd.DataFrame) -> str:
    """How many crops each block is known, approximated or missing for."""
    lines = ["| block | " + " | ".join(f"{s}" for s in (KNOWN, PARTIAL, MISSING)) + " | other |",
             "|---|---|---|---|---|"]
    for column, header in COLUMNS:
        if column in ("labour_untyped", "maelia_model"):
            continue
        values = coverage[column].astype(str).str[:1]
        counts = [int((values == s).sum()) for s in (KNOWN, PARTIAL, MISSING)]
        other = len(coverage) - sum(counts)
        lines.append(f"| {header} | " + " | ".join(map(str, counts)) + f" | {other} |")
    return "\n".join(lines)
