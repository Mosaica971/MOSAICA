import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from case_studies.guadeloupe.domain.economics import (
    apply_crop_multipliers,
    compute_gross_margin_per_ha_cult,
    compute_gross_product_per_ha_cult,
    compute_labor_hours_per_ha_cult,
    compute_sales_per_ha_cult,
    compute_subsidy_per_ha_cult,
    compute_variable_cost_per_ha_cult,
)
from case_studies.guadeloupe.domain.environment import (
    compute_azote_per_ha_cult,
    compute_ges_per_ha_cult,
    compute_ift_per_ha_cult,
    compute_phosphore_per_ha_cult,
    compute_potasse_per_ha_cult,
)
from case_studies.guadeloupe.domain.farm_typology import (
    compute_avers,
    compute_base_crop_group,
    compute_type_expl,
)
from case_studies.guadeloupe.domain import agroecology, rpest, soil_carbon, water
from core.config import load_config, resolve_enabled
from core.data.dataset import Dataset
from core.data.eligibility import (
    CATEGORICAL_RULE_REGISTRY,
    attribute_bounds_from_config,
    compute_eligibility_mask,
    eligible_pairs_from_mask,
    forbid_where,
)
from core.data.readers import read_flat_set, read_mapping_set, read_wide_table
from core.data.zone_filter import resolve_kept_plots

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
SETS_DIR = DATA_DIR / "sets"
TABLES_DIR = DATA_DIR / "tables"
INDICE_H_DIR = TABLES_DIR / "indice_H"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

DEFAULT_YEAR = "2017"
DEFAULT_SCENARIO = "RESTIT"
DEFAULT_COEFF_C_CO2 = 0.272


def _available_years() -> list[str]:
    """Column labels available in the indice_H economic tables (canonical table:
    Prix_Cult_CF_<scenario>.txt). Includes the special ``init``/``calib`` columns alongside the
    calendar years 2017..2022."""
    return list(read_wide_table(INDICE_H_DIR / f"Prix_Cult_CF_{DEFAULT_SCENARIO}.txt").columns)


def _available_scenarios() -> list[str]:
    """Scenario suffixes for which the scenario-specific input tables exist on disk,
    discovered from the Matrice_OTK_Cult_<scenario>.txt file names (e.g. RESTIT, SMART)."""
    prefix = "Matrice_OTK_Cult_"
    return sorted(path.stem[len(prefix):] for path in TABLES_DIR.glob(f"{prefix}*.txt"))


def _validate_data_selection(year: str, scenario: str) -> None:
    """Fail fast, with an explicit message, when config's ``data.year``/``data.scenario``
    have no backing data -- otherwise a bare pandas KeyError (year) or FileNotFoundError
    (scenario) surfaces deep inside the pipeline.

    ``year`` selects a column in the indice_H economic tables; ``scenario`` selects the
    Matrice_OTK_Cult_<scenario> and MAE_Compost_Cult_<scenario> input files."""
    years = _available_years()
    if year not in years:
        raise ValueError(
            f"data.year={year!r} is not an available economic-table column; "
            f"expected one of {years}."
        )
    required = [
        TABLES_DIR / f"Matrice_OTK_Cult_{scenario}.txt",
        INDICE_H_DIR / f"MAE_Compost_Cult_{scenario}.txt",
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise ValueError(
            f"data.scenario={scenario!r} is missing required file(s) {missing}; "
            f"available scenarios: {_available_scenarios()}."
        )


def compute_farm_surface_ha(plot_surface: pd.Series, expl_parc: pd.DataFrame) -> pd.Series:
    merged = expl_parc.assign(surface=expl_parc["plot"].map(plot_surface))
    return merged.groupby("farm")["surface"].sum()


def compute_farm_labor_capacity_hours(
    *,
    base_crop_group: pd.Series,
    plot_surface: pd.Series,
    expl_parc: pd.DataFrame,
    labor_hours_per_ha_cult: pd.Series,
    representative_crops: dict[str, str],
) -> pd.Series:
    """Labour (h/year) each farm's OBSERVED 2017 cropping plan required -- GAMS MO_Expl_init
    (ENTREES.txt:466-469), the budget Eq_MO_MAX_Expl caps the farm's allocation against.

    GAMS reads the labour rate straight off Matrice_Parc_Cult, which holds the AGGREGATE RPG
    codes. Nine of those twelve have no ITK line at all (Matrice_OTK_Cult's AN/BA/BC/CS/IG/
    MA/NC/PN/VE columns are entirely zero; only AG, JA and ME, the families with no fine
    variant, are filled). Taken literally the cap would be ~0 for most farms and the model
    would allocate nothing. We therefore price each observed family through its
    representative fine variant -- the same documented assumption the input-side indicators
    use, extended here to a constraint that *shapes the allocation*. See docs/04-vigilance.md and
    docs/superpowers/specs/2026-07-21-calibration-levers-design.md.
    """
    fine = base_crop_group.map(lambda family: representative_crops.get(family, family))
    rate = labor_hours_per_ha_cult.reindex(fine.to_numpy()).to_numpy()
    hours_by_plot = pd.Series(plot_surface.reindex(fine.index).to_numpy() * rate, index=fine.index)
    farm_of_plot = expl_parc.set_index("plot")["farm"]
    return hours_by_plot.groupby(farm_of_plot.reindex(hours_by_plot.index)).sum()


def read_fine_baseline_allocation(path: str | Path) -> dict[str, dict[str, float]]:
    """Read a GAMS-style wide plot x crop allocation table into {plot: {crop: ha}}.

    The 2017 baseline we normally carry has only the 12 aggregate RPG groups; the GAMS run
    wrote its own FINE baseline, one ITK per plot, in SORTIES/ASSOL_PARC_INIT.TXT. Reading it
    is what lets a farm-level budget be computed on the real cropping plan instead of on the
    representative-crop stand-in.

    Two quirks of GAMS's `put` writer are handled here: the file is comma-delimited with
    quoted labels (not the tab-separated layout of data/tables), and its header line is one
    field SHORT because the last two crop names are written glued together without a
    separator -- so the trailing pair is restored by name rather than trusted from the header.
    """
    path = Path(path)
    with path.open(encoding="latin-1") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        crops = [name.strip('"') for name in header[1:-1]] + ["MA_PAI_NON_I", "MA_PAI_NON_NI"]
        allocation: dict[str, dict[str, float]] = {}
        for row in reader:
            plot = row[0].strip('"')
            planted = {crop: float(value) for crop, value in zip(crops, row[1:]) if float(value)}
            if planted:
                allocation[plot] = planted
    return allocation


def compute_farm_labor_capacity_hours_from_fine_baseline(
    *,
    fine_baseline: dict[str, dict[str, float]],
    expl_parc: pd.DataFrame,
    labor_hours_per_ha_cult: pd.Series,
) -> pd.Series:
    """MO_Expl_init computed the way GAMS computes it (ENTREES.txt:466-469).

    `MO_Parc_init(SP) = sum(SC, SURF_Parc_init(SP) * Matrice_Parc_Cult(SP,SC) * MO_Ha_Cult_init(SC))`
    -- and Matrice_Parc_Cult holds the FINE ITK per plot, not the aggregate RPG code. That is
    the difference with compute_farm_labor_capacity_hours, which prices each observed group
    through one representative variant because the fine plan was thought unavailable.

    Validated end to end: these same rates applied to the GAMS CALIB allocation reproduce its
    reported TRAVAIL_TOT to 156 h out of 5 292 000 (0.003 %, GAMS's own 4-digit rounding).
    """
    farm_of_plot = expl_parc.set_index("plot")["farm"]
    hours: dict[str, float] = defaultdict(float)
    for plot, planted in fine_baseline.items():
        farm = farm_of_plot.get(plot)
        if farm is None:
            continue
        hours[farm] += sum(
            surface * float(labor_hours_per_ha_cult.get(crop, 0.0))
            for crop, surface in planted.items()
        )
    return pd.Series(hours, dtype=float)


def compute_farm_baseline_production_t(
    *,
    base_crop_group: pd.Series,
    plot_surface: pd.Series,
    expl_parc: pd.DataFrame,
    rdt_cult: pd.Series,
    representative_crops: dict[str, str],
) -> dict[str, dict[str, float]]:
    """Tonnes each farm's OBSERVED 2017 plan produced, per observed RPG group.

    This is GAMS REF_BAN_EXPL_init (ENTREES.txt:477-483) generalised: that parameter sums
    SURF_Parc_init x Matrice_Parc_Cult x Rdt_Cult over the four export-banana ITKs of a
    farm, and Eq_BA_QUOTA_Expl then caps the farm's banana tonnage at it. Computing one
    group at a time here rather than banana only means a second per-farm quota costs a
    config entry, not another pipeline function.

    THE CAVEAT THAT MATTERS. GAMS reads the observed FINE ITK per plot; we only have the
    12 aggregate RPG groups, so each group is priced through its representative fine
    variant -- the same documented assumption compute_farm_labor_capacity_hours makes, and
    the same one docs/04-vigilance.md flags. For banana it is not neutral: the observed mix
    was 1 258 ha BA_INT (45 t/ha), 288 ha BA_PER (18), 204 ha BA_SINT (27) and 169 ha
    BA_IRR (34), so pricing all 1 921 ha at BA_INT's 45 t/ha overstates the reference by
    about 18 %. The resulting cap is therefore LOOSER than the GAMS one, never tighter --
    it can only under-constrain, which is the safe direction for a parity fix.
    context/SORTIES/ASSOL_PARC_INIT.TXT holds the real fine baseline and would remove the
    approximation; wiring it in is a separate decision.
    """
    fine = base_crop_group.map(lambda family: representative_crops.get(family, family))
    rate = rdt_cult.reindex(fine.to_numpy()).fillna(0.0).to_numpy()
    tonnes = pd.Series(plot_surface.reindex(fine.index).to_numpy() * rate, index=fine.index)
    farm_of_plot = expl_parc.set_index("plot")["farm"].reindex(fine.index)

    frame = pd.DataFrame({"group": base_crop_group, "farm": farm_of_plot, "tonnes": tonnes})
    frame = frame.dropna(subset=["farm"])
    grouped = frame.groupby(["group", "farm"])["tonnes"].sum()
    return {
        str(group): {str(farm): float(value) for (_, farm), value in part.items()}
        for group, part in grouped.groupby(level=0)
    }


def build_dataset(config: dict[str, Any]) -> Dataset:
    # `year` selects the economic time-series column (2017..2022, or init/calib); the plot/
    # farm structure stays pinned to 2017 (no other year's structural data exists). `scenario`
    # (RESTIT|SMART) selects the OTK cost matrix and MAE-compost subsidy tables. Defaults
    # reproduce the historical hard-coded behaviour, so a config without a `data` section is
    # unchanged.
    data_cfg: dict[str, Any] = config.get("data", {})
    year: str = data_cfg.get("year", DEFAULT_YEAR)
    scenario: str = data_cfg.get("scenario", DEFAULT_SCENARIO)
    _validate_data_selection(year, scenario)

    # Optional per-crop economic shocks (price / subsidy multipliers). Absent => no-op,
    # so the baseline economics are unchanged. Used by scenario batches (scenarios.yaml)
    # to model targeted price / subsidy changes without new data tables.
    econ_cfg: dict[str, Any] = config.get("economic_overrides") or {}
    price_multipliers = econ_cfg.get("price_multipliers")
    subsidy_multipliers = econ_cfg.get("subsidy_multipliers")
    yield_multipliers = econ_cfg.get("yield_multipliers")
    cost_multipliers = econ_cfg.get("cost_multipliers")
    variance_multipliers = econ_cfg.get("variance_multipliers")

    # Carbon->CO2 conversion for the GES indicator (GAMS COEFF_C_CO2 = 0.272).
    env_cfg: dict[str, Any] = (config.get("reporting") or {}).get("environment") or {}
    coeff_c_co2 = float(env_cfg.get("coeff_c_co2", DEFAULT_COEFF_C_CO2))

    sets = {
        "crops": read_flat_set(SETS_DIR / "CULT_2017.set"),
        "soils": read_flat_set(SETS_DIR / "SOL.set"),
        "otk": read_flat_set(SETS_DIR / "OTK.set"),
        "watersheds": read_flat_set(SETS_DIR / "BV_2017.set"),
        "catchments": read_flat_set(SETS_DIR / "CPT_2017.set"),
    }

    expl_parc = read_mapping_set(SETS_DIR / "EXPL_PARC_2017.set", "farm", "plot")
    bv_parc = read_mapping_set(SETS_DIR / "BV_PARC_2017.set", "watershed", "plot")
    reg_parc = read_mapping_set(SETS_DIR / "REG_PARC_2017.set", "region", "plot")
    cpt_parc = read_mapping_set(SETS_DIR / "CPT_PARC_2017.set", "catchment", "plot")

    data_parc = read_wide_table(TABLES_DIR / "Data_Parc_Gwad_2017.txt")
    data_rpg = read_wide_table(TABLES_DIR / "Data_RPG_Gwad_2017.txt")
    data_cult = read_wide_table(TABLES_DIR / "Data_Cult.txt")
    data_otk = read_wide_table(TABLES_DIR / "Data_OTK.txt")
    data_sol = read_wide_table(TABLES_DIR / "Data_Sol.txt")
    matrice_otk_cult = read_wide_table(TABLES_DIR / f"Matrice_OTK_Cult_{scenario}.txt")
    # Nutrition tables for the food self-sufficiency indicators (per-tonne content by crop;
    # per-individual annual needs + population + fishing contribution).
    nutri_cult = read_wide_table(TABLES_DIR / "Nutri_Cult.txt")
    nutri_alim = read_wide_table(TABLES_DIR / "Nutri_Alim.txt")
    # GAMS parity: DONNEES.txt:283-289 fills TABLE Prix_Cult(C,H) / Rdt_Cult(C,H) from the
    # *_CF_<scenario> files, NOT from Prix_Cult.txt / Rdt_Cult.txt (which sit unused in the
    # same directory). Reading the plain files diverged on 23 of 84 crops -- plantain at
    # 26 t/ha & 800 EUR/t instead of 20 & 700, pasture at 5 000 EUR/t instead of 5 400,
    # melon at 1 200 instead of 1 455, fodder cane priced instead of self-consumed at 0 --
    # and that alone drove the territorial PAD to 48% where GAMS reaches 3.8%.
    prix_cult = apply_crop_multipliers(
        read_wide_table(INDICE_H_DIR / f"Prix_Cult_CF_{scenario}.txt")[year], price_multipliers
    )
    # yield_multipliers (climate shock) scale rdt at source so the shock propagates to
    # variable cost, subsidy (POSEI_Q), sales, GES, and the yield-based territory quotas.
    rdt_cult = apply_crop_multipliers(
        read_wide_table(INDICE_H_DIR / f"Rdt_Cult_CF_{scenario}.txt")[year], yield_multipliers
    )
    # variance_multipliers scale the yield variance Var_Rdt_Cult, which is what the Markowitz
    # objective weighs against margin. It is the lever for climate INSTABILITY as distinct
    # from a yield LOSS: a hotter, more erratic climate raises the variance of a crop without
    # necessarily lowering its mean, and under the risk-adjusted objective that alone shifts
    # risk-averse farms towards low-variance activities. Deliberately kept on the `init`
    # column like the unshocked series -- the shock is a scenario assumption, not a year.
    var_rdt_cult = apply_crop_multipliers(
        read_wide_table(INDICE_H_DIR / "Var_Rdt_Cult.txt")["init"], variance_multipliers
    )
    bagasse_cult = read_wide_table(INDICE_H_DIR / "Bagasse_Cult.txt")[year]
    duree_plant_cult = read_wide_table(INDICE_H_DIR / "Duree_Plant_Cult.txt")[year]
    duree_cycle_cult = read_wide_table(INDICE_H_DIR / "Duree_Cycle_Cult.txt")[year]
    cout_recolte_cult = read_wide_table(INDICE_H_DIR / "Cout_Recolte_Cult.txt")[year]
    # GAMS parity: DONNEES.txt:228 includes Cout_Transp_Cult_LAM.txt, not Cout_Transp_Cult.txt.
    # The two tables differ on the ten CF_* (fodder cane) rows only -- 0.98 to 4.50 EUR/t --
    # and since CV carries a (Cout_Recolte + Cout_Transp) * Rdt term, that fed a 71 to 290
    # EUR/ha margin gap on exactly those ten crops.
    cout_transp_cult = read_wide_table(INDICE_H_DIR / "Cout_Transp_Cult_LAM.txt")[year]
    posei_surf_cult = read_wide_table(INDICE_H_DIR / "POSEI_Surf_Cult.txt")[year]
    posei_q_cult = read_wide_table(INDICE_H_DIR / "POSEI_Q_Cult.txt")[year]
    aide_indus_cult = read_wide_table(INDICE_H_DIR / "Aide_Indus_Cult.txt")[year]
    aide_replant_cult = read_wide_table(INDICE_H_DIR / "Aide_Replant_Cult.txt")[year]
    aide_transp_cult = read_wide_table(INDICE_H_DIR / "Aide_Transp_Cult.txt")[year]
    aide_garantie_prix_cult = read_wide_table(INDICE_H_DIR / "Aide_Garantie_Prix_Cult.txt")[year]
    mae_recolte_vert_cult = read_wide_table(INDICE_H_DIR / "MAE_Recolte_Vert_Cult.txt")[year]
    mae_jachere_sol_nu_cult = read_wide_table(INDICE_H_DIR / "MAE_Jachere_Sol_Nu_Cult.txt")[year]
    mae_compost_cult = read_wide_table(INDICE_H_DIR / f"MAE_Compost_Cult_{scenario}.txt")[year]
    mb_add_cult = read_wide_table(INDICE_H_DIR / "MB_ADD_Cult.txt")[year]

    data_parc = data_parc.assign(
        REGION_CODE=data_parc.index.map(reg_parc.set_index("plot")["region"])
    )
    data_parc = data_parc.join(data_rpg[["cult_2015", "cult_2016", "cult_2017"]])

    plot_to_farm = expl_parc.set_index("plot")["farm"].reindex(data_parc.index)
    kept_plots = resolve_kept_plots(
        data_parc.index,
        {
            "islands": data_parc["ILE"],
            "regions": data_parc["REGION_CODE"],
            "farms": plot_to_farm,
            "plots": pd.Series(data_parc.index, index=data_parc.index),
        },
        config,
    )
    # Share of the territory's hectares the filter retains, measured BEFORE the cut. It is
    # what `zone_filter.scale_territorial_bounds` multiplies the territorial thresholds by,
    # so a reduced run is a miniature of the real one instead of an infeasible fragment.
    full_surface_ha = float(data_parc["SURF_HA"].sum())
    data_parc = data_parc.loc[kept_plots]
    zone_surface_fraction = (
        float(data_parc["SURF_HA"].sum()) / full_surface_ha if full_surface_ha else 1.0
    )
    expl_parc = expl_parc[expl_parc["plot"].isin(kept_plots)]
    bv_parc = bv_parc[bv_parc["plot"].isin(kept_plots)]
    reg_parc = reg_parc[reg_parc["plot"].isin(kept_plots)]
    cpt_parc = cpt_parc[cpt_parc["plot"].isin(kept_plots)]

    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)
    farm_plots = expl_parc.groupby("farm")["plot"].apply(list).to_dict()
    farm_gfa_surface_ha = compute_farm_surface_ha(
        plot_surface * data_parc["GFA_PARC"], expl_parc
    )

    # Eq_AN_PA (MODELE.txt:243) forbids AN_PA on any plot whose FARM total surface
    # (Surf_Expl_init = sum of the farm's plot SURF_HA, ENTREES.txt:116) is below
    # AN_SURF_EXPL_MIN = 10 ha (DONNEES.txt:135). Expose that per-plot farm surface as a
    # data_parc column so the config's generic attribute_forbidden rule can express the ban,
    # exactly like the geographic ITK bans -- no farm-indexed rule type needed.
    plot_farm_surface = pd.Series(
        expl_parc["farm"].map(farm_surface_ha).to_numpy(), index=expl_parc["plot"]
    )
    data_parc = data_parc.assign(
        SURF_EXPL_PARC=plot_farm_surface.reindex(data_parc.index)
    )

    base_crop_group = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])
    type_expl, type_expl_bis = compute_type_expl(farm_plots, base_crop_group, plot_surface)
    farm_risk_aversion = compute_avers(type_expl, type_expl_bis)

    attribute_bounds = attribute_bounds_from_config(config["eligibility_criteria"])
    plot_attributes = data_parc[list(attribute_bounds.keys())]
    crop_bounds = data_cult.T
    eligibility_mask = compute_eligibility_mask(plot_attributes, crop_bounds, attribute_bounds)
    for build_rule, args in resolve_enabled(
        config["categorical_rules"], CATEGORICAL_RULE_REGISTRY
    ):
        crops, condition = build_rule(data_parc, **args)
        eligibility_mask = forbid_where(eligibility_mask, condition, crops)
    eligible_pairs = eligible_pairs_from_mask(eligibility_mask)

    variable_cost_per_ha_cult = compute_variable_cost_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
        cout_recolte_cult=cout_recolte_cult,
        cout_transp_cult=cout_transp_cult,
        rdt_cult=rdt_cult,
    )
    # cost_multipliers (input/fuel shock) scale the variable cost only -- margin moves,
    # production/tonnage does not.
    variable_cost_per_ha_cult = apply_crop_multipliers(variable_cost_per_ha_cult, cost_multipliers)
    subsidy_per_ha_cult = compute_subsidy_per_ha_cult(
        posei_surf_cult=posei_surf_cult,
        posei_q_cult=posei_q_cult,
        aide_indus_cult=aide_indus_cult,
        aide_replant_cult=aide_replant_cult,
        aide_transp_cult=aide_transp_cult,
        aide_garantie_prix_cult=aide_garantie_prix_cult,
        mae_recolte_vert_cult=mae_recolte_vert_cult,
        mae_jachere_sol_nu_cult=mae_jachere_sol_nu_cult,
        mae_compost_cult=mae_compost_cult,
        mb_add_cult=mb_add_cult,
        rdt_cult=rdt_cult,
        duree_cycle_cult=duree_cycle_cult,
        duree_plant_cult=duree_plant_cult,
    )
    subsidy_per_ha_cult = apply_crop_multipliers(subsidy_per_ha_cult, subsidy_multipliers)
    # The agri-environmental component on its own. Folded into the subsidy total above, but
    # a scenario that wants to steer agroecology needs to see it apart from POSEI and
    # national aid -- see domain/agroecology.py on what it does and does not identify.
    mae_per_ha_cult = agroecology.compute_mae_per_ha_cult(
        mae_recolte_vert_cult, mae_jachere_sol_nu_cult, mae_compost_cult
    )
    under_mae_cult = agroecology.compute_under_mae_cult(mae_per_ha_cult)
    organic_cult = agroecology.compute_organic_cult(matrice_otk_cult)
    sales_per_ha_cult = compute_sales_per_ha_cult(
        rdt_cult=rdt_cult,
        prix_cult=prix_cult,
        bagasse_cult=bagasse_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    subsidy_per_ha_cult_annualized = subsidy_per_ha_cult / duree_cycle_cult * 12
    gross_product_per_ha_cult = compute_gross_product_per_ha_cult(
        rdt_cult=rdt_cult,
        prix_cult=prix_cult,
        bagasse_cult=bagasse_cult,
        subsidy_per_ha_cult=subsidy_per_ha_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    margin_per_ha_cult = compute_gross_margin_per_ha_cult(
        gross_product_per_ha_cult=gross_product_per_ha_cult,
        variable_cost_per_ha_cult=variable_cost_per_ha_cult,
    )
    labor_hours_per_ha_cult = compute_labor_hours_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    farm_baseline_production_t = compute_farm_baseline_production_t(
        base_crop_group=base_crop_group,
        plot_surface=plot_surface,
        expl_parc=expl_parc,
        rdt_cult=rdt_cult,
        representative_crops=config.get("baseline_representative_crops") or {},
    )
    # Opt-in: compute the farm labour budget on the OBSERVED FINE cropping plan rather than
    # on the representative-crop stand-in. `data.fine_baseline_allocation` names a GAMS-style
    # plot x crop table (context/SORTIES/ASSOL_PARC_INIT.TXT is the one the GAMS run wrote).
    # Left unset the behaviour is unchanged, so this cannot move a past result silently.
    fine_baseline_path = data_cfg.get("fine_baseline_allocation")
    farm_labor_capacity_hours = compute_farm_labor_capacity_hours(
        base_crop_group=base_crop_group,
        plot_surface=plot_surface,
        expl_parc=expl_parc,
        labor_hours_per_ha_cult=labor_hours_per_ha_cult,
        representative_crops=config.get("baseline_representative_crops") or {},
    )
    if fine_baseline_path:
        farm_labor_capacity_hours = (
            compute_farm_labor_capacity_hours_from_fine_baseline(
                fine_baseline=read_fine_baseline_allocation(fine_baseline_path),
                expl_parc=expl_parc,
                labor_hours_per_ha_cult=labor_hours_per_ha_cult,
            )
            .reindex(farm_labor_capacity_hours.index)
            .fillna(0.0)
        )
    azote_per_ha_cult = compute_azote_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    ges_per_ha_cult = compute_ges_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
        rdt_cult=rdt_cult,
        coeff_c_co2=coeff_c_co2,
    )
    phosphore_per_ha_cult = compute_phosphore_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    potasse_per_ha_cult = compute_potasse_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    ift_per_ha_cult = compute_ift_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
    )
    # Rpest (Tixier): pesticide risk to water, per (plot, crop) -- it needs the plot's runoff
    # and drainage as well as the crop's products, so unlike every other environmental rate
    # it cannot be a per-crop series. See domain/rpest.py.
    r_tixier = read_wide_table(TABLES_DIR / "R_Tixier.txt")
    rpest_crop_properties = rpest.compute_crop_properties(
        data_otk, matrice_otk_cult, duree_plant_cult, duree_cycle_cult
    )
    rpest_by_pair = rpest.compute_rpest_by_pair(
        rpest_crop_properties, data_parc, r_tixier, list(matrice_otk_cult.columns)
    )
    water_need_per_ha_cult = water.compute_water_need_per_ha_cult(data_cult)
    monthly_water_need_per_ha_cult = water.compute_monthly_water_need_per_ha_cult(data_cult)
    carbon_input_per_ha_cult = soil_carbon.compute_carbon_input_per_ha_cult(
        data_cult, data_otk, matrice_otk_cult
    )
    # Chlordécone uptake class per crop (Data_Cult["CLD"], 1=high..4=none), for the crop x
    # soil at-risk-surface indicator in reporting.
    cld_uptake_cult = data_cult.loc["CLD"]

    parameters = {
        "expl_parc": expl_parc,
        "bv_parc": bv_parc,
        "reg_parc": reg_parc,
        "cpt_parc": cpt_parc,
        "data_parc": data_parc,
        "data_cult": data_cult,
        "data_otk": data_otk,
        "matrice_otk_cult": matrice_otk_cult,
        "prix_cult": prix_cult,
        "rdt_cult": rdt_cult,
        "duree_cycle_cult": duree_cycle_cult,
        "crop_variance_per_ha": var_rdt_cult,
        # Each plot's OBSERVED 2017 use, folded onto the 12 RPG groups. Already computed for
        # the farm typology; exposed because the inertia constraint and the calibration
        # reporting both need to know what a plot was before the solver touched it.
        "base_crop_group": base_crop_group,
        "farm_risk_aversion": farm_risk_aversion,
        "farm_surface_ha": farm_surface_ha,
        "farm_plots": farm_plots,
        "farm_gfa_surface_ha": farm_gfa_surface_ha,
        "farm_labor_capacity_hours": farm_labor_capacity_hours,
        "farm_baseline_production_t": farm_baseline_production_t,
        "eligibility_mask": eligibility_mask,
        "eligible_pairs": eligible_pairs,
        "margin_per_ha_cult": margin_per_ha_cult,
        "variable_cost_per_ha_cult": variable_cost_per_ha_cult,
        "sales_per_ha_cult": sales_per_ha_cult,
        "subsidy_per_ha_cult_annualized": subsidy_per_ha_cult_annualized,
        "labor_hours_per_ha_cult": labor_hours_per_ha_cult,
        "azote_per_ha_cult": azote_per_ha_cult,
        # Mineral P/K, read off the fertiliser names (domain/environment.nutrient_grades).
        "phosphore_per_ha_cult": phosphore_per_ha_cult,
        "potasse_per_ha_cult": potasse_per_ha_cult,
        # Agroecology as the data defines it: MAE payments (a policy's reach) and organic
        # itineraries (a production method). Kept apart on purpose -- see domain/agroecology.
        "rpest_by_pair": rpest_by_pair,
        "rpest_crop_properties": rpest_crop_properties,
        "mae_per_ha_cult": mae_per_ha_cult,
        "under_mae_cult": under_mae_cult,
        "organic_cult": organic_cult,
        "ges_per_ha_cult": ges_per_ha_cult,
        "ift_per_ha_cult": ift_per_ha_cult,
        "data_sol": data_sol,
        "water_need_per_ha_cult": water_need_per_ha_cult,
        "monthly_water_need_per_ha_cult": monthly_water_need_per_ha_cult,
        "carbon_input_per_ha_cult": carbon_input_per_ha_cult,
        "cld_uptake_cult": cld_uptake_cult,
        "nutri_cult": nutri_cult,
        "nutri_alim": nutri_alim,
    }

    return Dataset(
        sets=sets,
        parameters=parameters,
        scalars={"zone_surface_fraction": zone_surface_fraction},
    )


if __name__ == "__main__":
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    print(f"crops: {len(dataset.sets['crops'])}")
    print(f"soils: {len(dataset.sets['soils'])}")
    print(f"otk: {len(dataset.sets['otk'])}")
    print(f"plots (expl_parc rows): {len(dataset.parameters['expl_parc'])}")
    print(f"farms: {dataset.parameters['expl_parc']['farm'].nunique()}")
    print(f"farm_surface_ha sample:\n{dataset.parameters['farm_surface_ha'].head()}")
