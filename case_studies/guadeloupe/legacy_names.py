"""Read runs written before the English renaming of 2026-09-22.

Until that date the recap keys, config labels, scenario coordinates and several CSV names
were French (`total_azote`, `mo_max_expl`, `P4_statu_quo`, `etp_by_region_output.csv`). The
runs in `outputs/` still carry them, and they are not rewritten: a run folder is a record of
what was solved, and the thesis tooling in `clement/memoire/` reads those files verbatim.

Instead, everything that READS a past run goes through this module, which renames legacy
names to current ones on the way in. Nothing here changes a number.

`LEGACY_NAMES` maps an old name to its current one. It applies to dict keys and to string
values alike, because the same name appears as both: a constraint label is a value in
`recap["constraints"]` and a key in `recap["shadow_prices"]`. A composite run name
(`P8_transition_agroecologique__F9_crise_systemique`) is renamed segment by segment.

The French keys below are deliberate. Do not run a bulk rename over this file:
tests/test_legacy_names.py fails if any entry maps a name onto itself.
"""

from __future__ import annotations

from typing import Any

LEGACY_NAMES: dict[str, str] = {
    # --- environment / economics / intensity / agroecology recap keys --------------------
    "total_azote": "total_nitrogen",
    "total_phosphore": "total_phosphorus",
    "total_potasse": "total_potassium",
    "total_ges": "total_ghg",
    "total_ift": "total_tfi",
    "surface_cld": "chlordecone_risk_area",
    "azote_per_ha": "nitrogen_per_ha",
    "ges_per_ha": "ghg_per_ha",
    "ift_per_ha": "tfi_per_ha",
    "total_etp": "total_fte",
    "etp_per_ha": "fte_per_ha",
    "gross_margin_per_etp": "gross_margin_per_fte",
    "subsidy_per_etp": "subsidy_per_fte",
    "azote_per_tonne": "nitrogen_per_tonne",
    "ift_per_tonne": "tfi_per_tonne",
    "surface_mae_ha": "aecm_area_ha",
    "surface_mae_share": "aecm_area_share",
    "mae_spending": "aecm_spending",
    "surface_bio_ha": "organic_area_ha",
    "surface_bio_share": "organic_area_share",
    "surface_bio_hors_prairie_ha": "organic_area_excl_grassland_ha",
    "surface_bio_hors_prairie_share": "organic_area_excl_grassland_share",
    # --- facts-table columns --------------------------------------------------------------
    "azote": "nitrogen",
    "ges": "ghg",
    "ift": "tfi",
    "etp": "fte",
    # --- indicator names a bound may target ------------------------------------------------
    "phosphore": "phosphorus",
    "potasse": "potassium",
    "eau": "water",
    "carbone": "carbon",
    "travail": "labor",
    "subvention": "subsidy",
    "mae": "aecm",
    "surface_mae": "aecm_area",
    "surface_bio": "organic_area",
    "marge": "margin",
    "cout": "cost",
    "vente": "sales",
    "rendement": "yield",
    "sol_contamine": "contaminated_soil",
    # --- config keys ------------------------------------------------------------------------
    "hours_per_etp": "hours_per_fte",
    # --- constraint and rule labels ---------------------------------------------------------
    "azote_max": "nitrogen_max",
    "emploi_min": "employment_min",
    "ba_quota_expl": "ba_quota_farm",
    "mo_max_expl": "labor_max_farm",
    "an_agro_max_expl": "an_agro_max_farm",
    "ig_agro_max_expl": "ig_agro_max_farm",
    "plafond_azote": "nitrogen_cap",
    "plafond_ift": "tfi_cap",
    "plafond_ges": "ghg_cap",
    "plafond_eau": "water_cap",
    "plancher_emploi": "employment_floor",
    "restriction_eau": "water_restriction",
    "budget_subventions": "subsidy_budget",
    "bio_min": "organic_min",
    "intensif_cap": "intensive_cap",
    "intensif_min": "intensive_min",
    "inertie": "inertia",
    "nitrates_ferme": "farm_nitrates",
    "arbo_surf_min": "orchard_area_min",
    "secheresse_irrig": "drought_irrigated_ban",
    "artificialisation": "land_take",
    "friche": "fallow",
    "friche_lock": "fallow_lock",
    # --- crop groups --------------------------------------------------------------------------
    "canne": "sugarcane",
    "banane_export": "export_banana",
    "igname": "yam",
    "ananas": "pineapple",
    "maraichage": "market_gardening",
    "arboriculture": "orchards",
    "vivrier": "food_crops",
    "bio_maraichage": "organic_market_gardening",
    "maraichage_reel": "distinct_market_gardening",
    "intensif_canne": "intensive_sugarcane",
    # --- sweeps -------------------------------------------------------------------------------
    "pareto_azote": "pareto_nitrogen",
    "pareto_subventions": "pareto_subsidies",
    "pareto_emploi": "pareto_employment",
    # --- policies -----------------------------------------------------------------------------
    "P1_deregulation_totale": "P1_full_deregulation",
    "P2_accelerationnisme_industriel": "P2_industrial_acceleration",
    "P3_intensification_moderee": "P3_moderate_intensification",
    "P4_statu_quo": "P4_status_quo",
    "P5_austerite_budgetaire": "P5_budget_austerity",
    "P6_verdissement_incitatif": "P6_incentive_greening",
    "P7_ecophyto_reglementaire": "P7_regulatory_ecophyto",
    "P8_transition_agroecologique": "P8_agroecological_transition",
    "P9_souverainete_alimentaire": "P9_food_sovereignty",
    "P10_bifurcation_agroecologique": "P10_agroecological_bifurcation",
    # --- forcings -----------------------------------------------------------------------------
    "F1_cyclone_majeur": "F1_major_cyclone",
    "F2_secheresse_severe": "F2_severe_drought",
    "F3_derive_climatique": "F3_climate_drift",
    "F4_choc_sanitaire": "F4_plant_health_shock",
    "F5_effondrement_prix_export": "F5_export_price_collapse",
    "F6_choc_intrants": "F6_input_price_shock",
    "F7_inflation_alimentaire": "F7_food_inflation",
    "F8_retrait_posei": "F8_posei_withdrawal",
    "F9_crise_systemique": "F9_systemic_crisis",
    "F10_conjoncture_favorable": "F10_favourable_conditions",
    "F11_artificialisation": "F11_land_take",
    # --- calibration runs ---------------------------------------------------------------------
    "calib_gams_parite": "calib_gams_parity",
    "calib_gams_parite_prix": "calib_gams_parity_prices",
    "calib_bc_seul": "calib_bc_only",
    "calib_retenu": "calib_selected",
    "calib_mo_fin_2017": "calib_fine_labor_2017",
    "mo_fin_observe": "fine_labor_observed",
    # --- farm-type labels (keys of calibration.farm_type_recall_by_type) -------------------
    "Non classe": "Unclassified",
    "Sans surface cultivee": "No cultivated area",
    "Arboriculteurs": "Fruit growers",
    "Bananiers": "Banana growers",
    "Canniers specialises": "Specialised cane growers",
    "Canniers diversifies": "Diversified cane growers",
    "Diversifies": "Diversified",
    "Eleveurs": "Livestock farmers",
    "Maraichers": "Market gardeners",
    "Canniers-eleveurs": "Cane and livestock farmers",
}

# CSV files whose name changed. A reader asks for the current name; `csv_candidates` also
# offers the legacy one, for runs written before the renaming.
LEGACY_CSV_NAMES: dict[str, str] = {
    f"fte_by_{scale}_{side}.csv": f"etp_by_{scale}_{side}.csv"
    for scale in ("region", "island", "farm")
    for side in ("input", "output")
}


def rename(name: str) -> str:
    """Current name for a legacy one; composite `a__b__c` names segment by segment."""
    if name in LEGACY_NAMES:
        return LEGACY_NAMES[name]
    if "__" in name:
        return "__".join(LEGACY_NAMES.get(part, part) for part in name.split("__"))
    return name


def upgrade(value: Any) -> Any:
    """`value` with every legacy dict key and string renamed, recursively. Numbers, and any
    string that is not a legacy name, pass through untouched."""
    if isinstance(value, dict):
        return {rename(k) if isinstance(k, str) else k: upgrade(v) for k, v in value.items()}
    if isinstance(value, list):
        return [upgrade(item) for item in value]
    if isinstance(value, str):
        return rename(value)
    return value


def upgrade_recap(recap: dict[str, Any]) -> dict[str, Any]:
    """A recap.json as the current code expects it. `run_name` is kept verbatim: it is the
    name the run was solved under, which is what a reader looks for on disk."""
    upgraded = upgrade(recap)
    if "run_name" in recap:
        upgraded["run_name"] = recap["run_name"]
    return upgraded


def upgrade_config(config: dict[str, Any]) -> dict[str, Any]:
    """A config_used.yaml as the current code expects it (labels, rule names, indicators)."""
    return upgrade(config)


def csv_candidates(name: str) -> list[str]:
    """File names to try, current first, for a CSV that may predate the renaming."""
    legacy = LEGACY_CSV_NAMES.get(name)
    return [name, legacy] if legacy else [name]
