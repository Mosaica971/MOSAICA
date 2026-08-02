from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from case_studies.guadeloupe.domain import resilience, soil_carbon, water
from case_studies.guadeloupe.domain.crop_families import base_group_for
from case_studies.guadeloupe.domain.farm_typology import compute_base_crop_group
from core.data.dataset import Dataset

_NON_CULTIVATED_GROUP = "NC"


def decode_output_allocation(model: pyo.ConcreteModel) -> pd.Series:
    """plot -> fine crop, read from the solved model's Y variable."""
    allocated = {
        plot: crop
        for plot, crop in model.PAIRS
        if pyo.value(model.Y[plot, crop]) > 0.5
    }
    return pd.Series(allocated, name="crop")


def decode_baseline_allocation(dataset: Dataset) -> pd.Series:
    """plot -> RPG base crop group (12 groups), from the observed 2017 land use."""
    data_parc = dataset.parameters["data_parc"]
    groups = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])
    return groups[groups != _NON_CULTIVATED_GROUP].dropna()


def decode_baseline_representative_allocation(dataset: Dataset, config: dict[str, Any]) -> pd.Series:
    """Baseline 2017 allocation remapped from aggregate families to representative fine
    crops, so the fine-crop economics indicators (production/subsidy/revenue/ETP) apply to
    the input side. The observed baseline is only known at aggregate/RPG resolution and the
    aggregate codes carry no economics of their own; `config['baseline_representative_crops']`
    substitutes a representative fine variant per family (an assumption -- see docs/04-vigilance.md
    "point 4"). Real single-crop families (AG/ME/JA) map to themselves; NC is already
    dropped by decode_baseline_allocation."""
    baseline = decode_baseline_allocation(dataset)
    mapping = config.get("baseline_representative_crops") or {}
    return baseline.map(lambda family: mapping.get(family, family)).rename("crop")


def plot_to_farm(dataset: Dataset) -> pd.Series:
    expl_parc = dataset.parameters["expl_parc"]
    return expl_parc.set_index("plot")["farm"]


def plot_to_region(dataset: Dataset) -> pd.Series:
    return dataset.parameters["data_parc"]["REGION"]


def plot_to_island(dataset: Dataset) -> pd.Series:
    return dataset.parameters["data_parc"]["ILE"]


def _plot_surface(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Surface (ha) of each allocated plot, aligned on the allocation index."""
    return dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)


def _by_crop(dataset: Dataset, allocation: pd.Series, param_name: str) -> pd.Series:
    """Allocated surface times a crop-indexed per-ha rate, totalled by crop."""
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    rate = dataset.parameters[param_name]
    return surface_by_crop * rate.reindex(surface_by_crop.index)


def _per_plot_rate(dataset: Dataset, allocation: pd.Series, param_name: str) -> pd.Series:
    """Broadcast a crop-indexed per-ha rate onto an allocation's plot index."""
    return _broadcast_rate(dataset.parameters[param_name], allocation)


def _broadcast_rate(rate: pd.Series, allocation: pd.Series) -> pd.Series:
    """Look a crop-indexed rate up per allocated plot, keeping the plot index."""
    return pd.Series(rate.reindex(allocation.to_numpy()).to_numpy(), index=allocation.index)


def compute_surface_by_key(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return _plot_surface(dataset, allocation).groupby(allocation).sum()


def compute_aggregate_summary(dataset: Dataset, allocation: pd.Series) -> dict[str, float]:
    surface = _plot_surface(dataset, allocation)
    farms = plot_to_farm(dataset).reindex(allocation.index)
    return {
        "total_surface_ha": float(surface.sum()),
        "active_plot_count": int(len(allocation)),
        "farm_count": int(farms.nunique()),
    }


def compute_production_tonnes_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return _by_crop(dataset, allocation, "rdt_cult")


def compute_sales_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return _by_crop(dataset, allocation, "sales_per_ha_cult")


def compute_subsidy_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return _by_crop(dataset, allocation, "subsidy_per_ha_cult_annualized")


def compute_total_revenue_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return compute_sales_by_crop(dataset, allocation) + compute_subsidy_by_crop(dataset, allocation)


def compute_gross_margin_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Gross margin (EUR) by crop: surface x margin_per_ha_cult (gross product minus variable
    input costs, the same per-ha margin the objective maximizes). Labor is NOT priced in here
    -- that is compute_labor_cost_by_crop, subtracted separately for the net revenue."""
    return _by_crop(dataset, allocation, "margin_per_ha_cult")


def compute_azote_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Nitrogen applied (kg N) by crop: surface x azote_per_ha_cult."""
    return _by_crop(dataset, allocation, "azote_per_ha_cult")


def compute_rpest_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Rpest score (0-10) of each allocated plot, for the crop it carries."""
    table = dataset.parameters.get("rpest_by_pair")
    if table is None or allocation.empty:
        return pd.Series(dtype=float)
    plots = [p for p in allocation.index if p in table.index]
    crops = allocation.reindex(plots)
    valid = crops[crops.isin(table.columns)]
    if valid.empty:
        return pd.Series(dtype=float)
    values = table.reindex(index=valid.index).to_numpy()[
        range(len(valid)), [table.columns.get_loc(c) for c in valid]
    ]
    return pd.Series(values, index=valid.index)


def compute_rpest_totals(dataset: Dataset, allocation: pd.Series) -> dict[str, float]:
    """Territorial pesticide-risk summary.

    The headline is GAMS's own: the SURFACE whose score exceeds 6, i.e. the land where the
    risk is judged high. A mean score would hide it -- a few very exposed hectares matter
    more to a catchment than a slightly raised average everywhere.
    """
    scores = compute_rpest_by_plot(dataset, allocation)
    if scores.empty:
        return {"rpest_mean": 0.0, "rpest_surface_at_risk_ha": 0.0,
                "rpest_surface_at_risk_share": 0.0, "rpest_max": 0.0}
    surface = _plot_surface(dataset, allocation).reindex(scores.index)
    total = float(surface.sum())
    at_risk = float(surface[scores > 6.0].sum())
    weighted_mean = float((scores * surface).sum() / total) if total else 0.0
    return {
        "rpest_mean": weighted_mean,
        "rpest_surface_at_risk_ha": at_risk,
        "rpest_surface_at_risk_share": at_risk / total if total else 0.0,
        "rpest_max": float(scores.max()),
    }


def compute_agroecology_totals(dataset: Dataset, allocation: pd.Series) -> dict[str, float]:
    """Reach of the agri-environmental measures, and organic area.

    Reported apart from one another on purpose: an MAE pays for a named practice (green
    harvest, sanitary fallow, compost) and covers conventional crops doing it, while the
    organic figure counts itineraries that use an organic-only operation. Adding the two
    would file green-harvest cane as organic. See domain/agroecology.py.
    """
    surface = _plot_surface(dataset, allocation)
    total_surface = float(surface.sum())

    def area_where(parameter: str) -> float:
        if parameter not in dataset.parameters:
            return 0.0
        rate = _broadcast_rate(dataset.parameters[parameter], allocation)
        return float((surface * rate).sum())

    mae_area = area_where("under_mae_cult")
    organic_area = area_where("organic_cult")
    mae_spend = float(_optional_by_crop(dataset, allocation, "mae_per_ha_cult").sum())

    # Pasture qualifies as organic through the PROC_BIO_BOVIN operation of its itinerary,
    # which is faithful to the data but swamps the figure: on output_3 the whole 6 096 ha of
    # organic area IS the pasture floor. Reported separately so "organic share" is never read
    # as a statement about cropland when it is a statement about grass.
    if "organic_cult" in dataset.parameters and not allocation.empty:
        organic_rate = _broadcast_rate(dataset.parameters["organic_cult"], allocation)
        is_pasture = allocation.map(
            lambda crop: _safe_base_group(crop) == "PN"
        ).astype(float)
        organic_cropland = float((surface * organic_rate * (1.0 - is_pasture)).sum())
    else:
        organic_cropland = 0.0

    def share(value: float) -> float:
        return value / total_surface if total_surface else 0.0

    return {
        "surface_mae_ha": mae_area,
        "surface_mae_share": share(mae_area),
        "mae_spending": mae_spend,
        "surface_bio_ha": organic_area,
        "surface_bio_share": share(organic_area),
        "surface_bio_hors_prairie_ha": organic_cropland,
        "surface_bio_hors_prairie_share": share(organic_cropland),
    }


def _safe_base_group(crop: str) -> str | None:
    try:
        return base_group_for(crop)
    except KeyError:
        return None


def _optional_by_crop(dataset: Dataset, allocation: pd.Series, parameter: str) -> pd.Series:
    """`_by_crop`, but yielding nothing when the parameter is absent.

    Reporting runs against datasets built by older code and by tests that supply only the
    parameters they exercise; a newly added rate must not make the whole environmental block
    unavailable.
    """
    if parameter not in dataset.parameters:
        return pd.Series(dtype=float)
    return _by_crop(dataset, allocation, parameter)


def compute_phosphore_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return _optional_by_crop(dataset, allocation, "phosphore_per_ha_cult")


def compute_potasse_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return _optional_by_crop(dataset, allocation, "potasse_per_ha_cult")


def compute_ges_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Greenhouse-gas emissions (t CO2) by crop: surface x ges_per_ha_cult."""
    return _by_crop(dataset, allocation, "ges_per_ha_cult")


def compute_ift_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Pesticide treatment-frequency index (IFT, summed over ha) by crop:
    surface x ift_per_ha_cult."""
    return _by_crop(dataset, allocation, "ift_per_ha_cult")


def _cld_at_risk_mask(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Boolean per allocated plot: True where the assigned crop, the parcel's chlordécone
    soil-risk level (RISQUE_CLD, 1=worst..5=none) and its soil type (TYPE_SOL) trigger
    at-risk food production. Faithful to OPTIMISATION.txt indicator n°10 (NV_CLD_parc),
    with c = crop uptake class (Data_Cult["CLD"], 1=high..4=none)."""
    data_parc = dataset.parameters["data_parc"]
    r = data_parc["RISQUE_CLD"].reindex(allocation.index)
    s = data_parc["TYPE_SOL"].reindex(allocation.index)
    c = _per_plot_rate(dataset, allocation, "cld_uptake_cult")
    return (
        ((c == 1) & (r <= 3))
        | ((c == 2) & (r <= 2))
        | ((c == 3) & (r <= 2) & s.isin([2, 4]))
        | ((c == 3) & (r == 1) & s.isin([1, 3, 5]))
    )


def compute_cld_at_risk_surface(dataset: Dataset, allocation: pd.Series) -> float:
    """Cultivated surface (ha) flagged at chlordécone risk by the crop x soil rule."""
    mask = _cld_at_risk_mask(dataset, allocation)
    return float(_plot_surface(dataset, allocation)[mask].sum())


def _irrigable_surface(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Plot surface (ha), zeroed on plots that cannot be irrigated (IRRIG_PARC = 0) and
    therefore draw nothing from the resource. Faithful to OPTIMISATION.txt:2540-2542."""
    irrigable = dataset.parameters["data_parc"]["IRRIG_PARC"].reindex(allocation.index) == 1
    return _plot_surface(dataset, allocation).where(irrigable, 0.0)


def compute_water_need_m3_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Annual gross crop water need (m3) per allocated plot. Gross, not net of rainfall --
    the monthly PLUVIO_*_PARC columns do not exist in the data (see docs/04-vigilance.md)."""
    if allocation.empty:
        return pd.Series(dtype=float)
    per_ha = _per_plot_rate(dataset, allocation, "water_need_per_ha_cult")
    return per_ha * _irrigable_surface(dataset, allocation) * water.M3_PER_MM_PER_HA


def compute_monthly_water_need_m3(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Territory-wide water need (m3) for each of the 12 months, in calendar order.

    Currently only consumed internally, to derive the (degenerate) peak-month scalar in
    compute_environmental_totals -- not exported as a report CSV, because BESOIN_EAU_01..12
    are flat across all 12 months for every crop in the real data, so the 12-row series would
    read as a genuine seasonal curve when it carries no seasonal information at all. Kept as-is
    (and still tested) for when a real monthly profile is supplied."""
    monthly_rate = dataset.parameters["monthly_water_need_per_ha_cult"]
    surface = _irrigable_surface(dataset, allocation)
    if allocation.empty:
        return pd.Series(0.0, index=monthly_rate.index)
    per_month = {}
    for month in monthly_rate.index:
        per_ha = _broadcast_rate(monthly_rate.loc[month], allocation)
        per_month[month] = float((per_ha * surface * water.M3_PER_MM_PER_HA).sum())
    return pd.Series(per_month)


def compute_soil_carbon_mineralization_by_plot(
    dataset: Dataset, allocation: pd.Series
) -> pd.Series:
    """Carbon mineralized (t C) per allocated plot: per-ha rate times plot surface."""
    if allocation.empty:
        return pd.Series(dtype=float)
    data_parc = dataset.parameters["data_parc"]
    initial = soil_carbon.compute_initial_soil_carbon_per_ha_plot(
        data_parc, dataset.parameters["data_sol"]
    )
    per_ha = soil_carbon.compute_mineralization_per_ha_plot(
        allocation, data_parc, dataset.parameters["data_sol"],
        dataset.parameters["data_cult"], initial,
    )
    return per_ha * _plot_surface(dataset, allocation)


def compute_soil_carbon_balance_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Net annual carbon balance (t C) per allocated plot. Negative = soil depletion."""
    if allocation.empty:
        return pd.Series(dtype=float)
    inputs_per_ha = _per_plot_rate(dataset, allocation, "carbon_input_per_ha_cult")
    inputs = inputs_per_ha * _plot_surface(dataset, allocation)
    return inputs - compute_soil_carbon_mineralization_by_plot(dataset, allocation)


def compute_environmental_totals(dataset: Dataset, allocation: pd.Series) -> dict[str, float]:
    """Headline environmental totals for one allocation: nitrogen (kg N), GES (t CO2), IFT,
    chlordécone-exposed surface (ha), plus per-ha averages over the cultivated surface.
    Also: gross annual water need (m3, not net of rainfall) both territory-wide and for the
    single peak month, and the net annual soil organic carbon balance and mineralization
    flux (t C, see soil_carbon.py)."""
    total_surface = float(_plot_surface(dataset, allocation).sum())
    total_azote = float(compute_azote_by_crop(dataset, allocation).sum())
    total_ges = float(compute_ges_by_crop(dataset, allocation).sum())
    total_ift = float(compute_ift_by_crop(dataset, allocation).sum())

    def per_ha(value: float) -> float:
        return value / total_surface if total_surface else 0.0

    monthly_water = compute_monthly_water_need_m3(dataset, allocation)
    total_water = float(compute_water_need_m3_by_plot(dataset, allocation).sum())

    return {
        **compute_rpest_totals(dataset, allocation),
        "total_azote": total_azote,
        # Mineral P/K only -- organic amendments declare no grade, see
        # domain/environment.nutrient_grades.
        "total_phosphore": float(compute_phosphore_by_crop(dataset, allocation).sum()),
        "total_potasse": float(compute_potasse_by_crop(dataset, allocation).sum()),
        "total_ges": total_ges,
        "total_ift": total_ift,
        "surface_cld": compute_cld_at_risk_surface(dataset, allocation),
        "azote_per_ha": per_ha(total_azote),
        "ges_per_ha": per_ha(total_ges),
        "ift_per_ha": per_ha(total_ift),
        "total_water_need_m3": total_water,
        # Degenerate on the real dataset: BESOIN_EAU_01..12 are identical across all 12
        # months for every crop (see docs/04-vigilance.md), so the peak month is always exactly
        # total_water / 12 -- it carries no information beyond the annual total and is
        # deliberately excluded from the dashboard's composite score (comparison.py). Kept
        # in the recap; will become meaningful once a genuine monthly profile is supplied.
        "water_need_peak_month_m3": float(monthly_water.max()) if len(monthly_water) else 0.0,
        "soil_carbon_balance": float(
            compute_soil_carbon_balance_by_plot(dataset, allocation).sum()
        ),
        "soil_carbon_mineralization": float(
            compute_soil_carbon_mineralization_by_plot(dataset, allocation).sum()
        ),
    }


def compute_resilience_totals(
    dataset: Dataset, allocation: pd.Series, price_shock_delta: float
) -> dict[str, float]:
    """Exposure of one allocation to climatic and economic shocks: gross margin at risk in a
    bad year, revenue concentration, and margin lost under a relative price shock.

    These measure a *fixed* allocation's exposure -- nothing is re-optimized, so this is not
    adaptive capacity. See the design spec and docs/04-vigilance.md.
    """
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    total_margin = float(compute_gross_margin_by_crop(dataset, allocation).sum())

    at_risk_rate = resilience.compute_climate_margin_at_risk_per_ha_cult(
        dataset.parameters["margin_per_ha_cult"], dataset.parameters["crop_variance_per_ha"]
    )
    shock_rate = resilience.compute_price_shock_loss_per_ha_cult(
        dataset.parameters["rdt_cult"],
        dataset.parameters["prix_cult"],
        dataset.parameters["duree_cycle_cult"],
        price_shock_delta,
    )

    at_risk = float((surface_by_crop * at_risk_rate.reindex(surface_by_crop.index)).sum())
    shock_loss = float((surface_by_crop * shock_rate.reindex(surface_by_crop.index)).sum())
    hhi = resilience.compute_revenue_concentration_hhi(
        compute_total_revenue_by_crop(dataset, allocation)
    )

    def ratio(value: float) -> float:
        return value / total_margin if total_margin else 0.0

    return {
        "climate_margin_at_risk": at_risk,
        "climate_margin_at_risk_ratio": ratio(at_risk),
        "revenue_concentration_hhi": hhi,
        "price_shock_margin_loss": shock_loss,
        "price_shock_margin_loss_ratio": ratio(shock_loss),
    }


def _nutrients(dataset: Dataset) -> list[str]:
    """Nutrient row labels of nutri_alim, excluding the Q_Tot (quantity/population) row."""
    return [n for n in dataset.parameters["nutri_alim"].index if n != "Q_Tot"]


def compute_nutrient_production(
    dataset: Dataset, allocation: pd.Series, include_fishing: bool
) -> pd.Series:
    """Nutrients produced territory-wide for one allocation (index = nutrient): crop
    production in tonnes x per-tonne content (Nutri_Cult), optionally plus the fixed fishing
    contribution (Nutri_Alim[nutrient, 'peche'] x tonnage Nutri_Alim['Q_Tot', 'peche']).
    Faithful to OPTIMISATION.txt:1953-1959 (NUTRI_Gwad)."""
    nutri_cult = dataset.parameters["nutri_cult"]
    nutri_alim = dataset.parameters["nutri_alim"]
    nutrients = _nutrients(dataset)
    production_tonnes = compute_production_tonnes_by_crop(dataset, allocation)
    content = nutri_cult.reindex(index=nutrients, columns=production_tonnes.index).fillna(0.0)
    result = content.dot(production_tonnes)
    if include_fishing:
        fishing = nutri_alim.loc[nutrients, "peche"] * nutri_alim.loc["Q_Tot", "peche"]
        result = result + fishing
    return result


def compute_self_sufficiency_ratios(
    dataset: Dataset, allocation: pd.Series, include_fishing: bool
) -> pd.Series:
    """Food self-sufficiency ratio per nutrient (production / population need). 1.0 means the
    territory produces exactly the population's annual need of that nutrient. Need =
    Nutri_Alim[nutrient, 'Ind_Moy'] x population (Nutri_Alim['Q_Tot', 'Ind_Moy']). Faithful to
    RATIO_PROD_BESOIN, OPTIMISATION.txt:1962-1975."""
    nutri_alim = dataset.parameters["nutri_alim"]
    nutrients = _nutrients(dataset)
    production = compute_nutrient_production(dataset, allocation, include_fishing)
    population = nutri_alim.loc["Q_Tot", "Ind_Moy"]
    need = nutri_alim.loc[nutrients, "Ind_Moy"] * population
    return (production / need).replace([np.inf, -np.inf], np.nan)


def compute_food_autonomy_totals(dataset: Dataset, allocation: pd.Series) -> dict[str, Any]:
    """Food self-sufficiency summary for one allocation: per-nutrient ratios in two variants
    (crop-only and with the fishing contribution), each variant's limiting (minimum) ratio,
    and the population. Nutrient keys are lower-cased for stable recap keys."""
    nutri_alim = dataset.parameters["nutri_alim"]
    crop = compute_self_sufficiency_ratios(dataset, allocation, include_fishing=False)
    fish = compute_self_sufficiency_ratios(dataset, allocation, include_fishing=True)

    def by_nutrient(ratios: pd.Series) -> dict[str, float]:
        return {str(k).lower(): float(v) for k, v in ratios.items()}

    return {
        "population": float(nutri_alim.loc["Q_Tot", "Ind_Moy"]),
        "crop_only": by_nutrient(crop),
        "with_fishing": by_nutrient(fish),
        "limiting_crop_only": float(crop.min()),
        "limiting_with_fishing": float(fish.min()),
    }


def compute_subsidy_per_tonne_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    subsidy = compute_subsidy_by_crop(dataset, allocation)
    production = compute_production_tonnes_by_crop(dataset, allocation)
    return (subsidy / production).replace([np.inf, -np.inf], np.nan)


def compute_subsidy_per_euro_sold_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    subsidy = compute_subsidy_by_crop(dataset, allocation)
    sales = compute_sales_by_crop(dataset, allocation)
    return (subsidy / sales).replace([np.inf, -np.inf], np.nan)


def compute_revenue_by_farm(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    revenue_per_ha = _per_plot_rate(dataset, allocation, "sales_per_ha_cult") + _per_plot_rate(
        dataset, allocation, "subsidy_per_ha_cult_annualized"
    )
    revenue_per_plot = _plot_surface(dataset, allocation) * revenue_per_ha
    farms = plot_to_farm(dataset).reindex(allocation.index)
    return revenue_per_plot.groupby(farms).sum()


DEFAULT_HOURS_PER_ETP = 1607.0
# No labor cost unless config sets one: net revenue then equals gross margin (current view).
DEFAULT_COST_PER_HOUR = 0.0


def hours_per_etp_from_config(config: dict[str, Any]) -> float:
    """Annual working hours per full-time-equivalent (ETP), from config['labor']."""
    return float((config.get("labor") or {}).get("hours_per_etp", DEFAULT_HOURS_PER_ETP))


def labor_cost_per_hour_from_config(config: dict[str, Any]) -> float:
    """Labor cost per worked hour (EUR/h), from config['labor']. Used to value the labor
    embedded in each crop's itinerary; see compute_labor_cost_by_crop."""
    return float((config.get("labor") or {}).get("cost_per_hour", DEFAULT_COST_PER_HOUR))


def compute_labor_hours_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Estimated annual labor hours per plot: surface x labor_hours_per_ha[crop].

    Only meaningful for a fine-crop allocation (the solver output): the 12-RPG-group
    baseline has no labor rate at that resolution, so ETP is an output-only indicator
    (see docs/04-vigilance.md, same limitation as the other per-crop indicators)."""
    return _plot_surface(dataset, allocation) * _per_plot_rate(
        dataset, allocation, "labor_hours_per_ha_cult"
    )


def compute_total_etp(dataset: Dataset, allocation: pd.Series, hours_per_etp: float) -> float:
    """Total full-time-equivalent jobs across all plots (labor hours / hours_per_etp)."""
    return float(compute_labor_hours_by_plot(dataset, allocation).sum() / hours_per_etp)


def compute_etp_by_key(
    dataset: Dataset, allocation: pd.Series, grouping: pd.Series, hours_per_etp: float
) -> pd.Series:
    """ETP grouped by a plot-keyed Series (farm / region / island)."""
    hours = compute_labor_hours_by_plot(dataset, allocation)
    key = grouping.reindex(allocation.index)
    return hours.groupby(key).sum() / hours_per_etp


def compute_labor_cost_by_crop(
    dataset: Dataset, allocation: pd.Series, cost_per_hour: float
) -> pd.Series:
    """Labor cost (EUR) by crop: labor hours per plot x cost_per_hour, grouped by crop.
    Values the family/hired labor the gross margin leaves unpriced (labor is tracked in
    hours, not monetized, in the GAMS variable cost -- see economics.py)."""
    hours = compute_labor_hours_by_plot(dataset, allocation)
    return hours.groupby(allocation).sum() * cost_per_hour


def compute_total_labor_cost(
    dataset: Dataset, allocation: pd.Series, cost_per_hour: float
) -> float:
    """Total labor cost across all plots (labor hours x cost_per_hour)."""
    return float(compute_labor_hours_by_plot(dataset, allocation).sum() * cost_per_hour)


def compute_economic_totals(
    dataset: Dataset, allocation: pd.Series, hours_per_etp: float, cost_per_hour: float
) -> dict[str, float]:
    """Headline totals for one allocation: production (tonnes), subsidy (EUR), revenue
    (=gross product: sales+subsidy, EUR), gross margin (EUR, after variable input costs),
    variable cost (EUR, derived = revenue - gross margin), labor cost (EUR), net revenue
    (EUR, = gross margin - labor cost), and employment (ETP). Valid for both the output
    (fine crops) and the representative baseline (see
    decode_baseline_representative_allocation)."""
    revenue = float(compute_total_revenue_by_crop(dataset, allocation).sum())
    gross_margin = float(compute_gross_margin_by_crop(dataset, allocation).sum())
    labor_cost = compute_total_labor_cost(dataset, allocation, cost_per_hour)
    return {
        "total_production_tonnes": float(compute_production_tonnes_by_crop(dataset, allocation).sum()),
        "total_subsidy": float(compute_subsidy_by_crop(dataset, allocation).sum()),
        "total_revenue": revenue,
        "total_gross_margin": gross_margin,
        "total_variable_cost": revenue - gross_margin,
        "total_labor_cost": labor_cost,
        "total_net_revenue": gross_margin - labor_cost,
        "total_etp": compute_total_etp(dataset, allocation, hours_per_etp),
    }


_FACT_MEASURES = [
    "surface", "production", "sales", "subsidy", "revenue",
    "gross_margin", "labor_hours", "labor_cost", "etp",
    "ges", "ift", "azote", "surface_cld",
    "water_need_m3", "soil_carbon_balance",
]


def compute_facts_table(
    dataset: Dataset, allocation: pd.Series, hours_per_etp: float, cost_per_hour: float
) -> pd.DataFrame:
    """Tidy fact table for one allocation: every plot rolled up by (crop, region), with all
    additive economic/labor measures plus its island. Backs the comparison dashboard's free
    pivoting (x in culture/sous-culture/region/island, any measure, stacked by the other
    dimension). ETP is labor_hours / hours_per_etp, which stays additive across rows."""
    data_parc = dataset.parameters["data_parc"]
    crops = allocation.to_numpy()
    surface = _plot_surface(dataset, allocation).to_numpy()

    def rate(name: str) -> "np.ndarray":
        return dataset.parameters[name].reindex(crops).to_numpy()

    per_plot = pd.DataFrame(
        {
            "crop": crops,
            "region": data_parc["REGION"].reindex(allocation.index).to_numpy(),
            "island": data_parc["ILE"].reindex(allocation.index).to_numpy(),
            "surface": surface,
            "production": surface * rate("rdt_cult"),
            "sales": surface * rate("sales_per_ha_cult"),
            "subsidy": surface * rate("subsidy_per_ha_cult_annualized"),
            "gross_margin": surface * rate("margin_per_ha_cult"),
            "labor_hours": surface * rate("labor_hours_per_ha_cult"),
            "ges": surface * rate("ges_per_ha_cult"),
            "ift": surface * rate("ift_per_ha_cult"),
            "azote": surface * rate("azote_per_ha_cult"),
        }
    )
    per_plot["revenue"] = per_plot["sales"] + per_plot["subsidy"]
    per_plot["labor_cost"] = per_plot["labor_hours"] * cost_per_hour
    per_plot["etp"] = per_plot["labor_hours"] / hours_per_etp
    # Chlordécone-exposed surface: the plot's own surface when the crop x soil rule flags it.
    per_plot["surface_cld"] = surface * _cld_at_risk_mask(dataset, allocation).to_numpy()
    # Water is a per-crop rate, but soil carbon depends on the plot's soil type: it cannot
    # go through rate() and comes from the per-plot functions instead.
    per_plot["water_need_m3"] = compute_water_need_m3_by_plot(dataset, allocation).to_numpy()
    per_plot["soil_carbon_balance"] = compute_soil_carbon_balance_by_plot(
        dataset, allocation
    ).to_numpy()

    grouped = per_plot.groupby(["crop", "region"], as_index=False).agg(
        {"island": "first", **{measure: "sum" for measure in _FACT_MEASURES}}
    )
    return grouped[["crop", "region", "island", *_FACT_MEASURES]]


def compute_gini(values: pd.Series) -> float:
    x = np.sort(values.to_numpy(dtype=float))
    n = len(x)
    total = x.sum()
    if n == 0 or total == 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * x)) / (n * total) - (n + 1) / n)


def compute_shannon_diversity(
    dataset: Dataset, allocation: pd.Series, grouping: pd.Series
) -> pd.Series:
    frame = pd.DataFrame(
        {
            "group_key": grouping.reindex(allocation.index),
            "crop": allocation,
            "surface": _plot_surface(dataset, allocation),
        }
    )

    def _shannon(rows: pd.DataFrame) -> float:
        shares = rows.groupby("crop")["surface"].sum()
        shares = shares[shares > 0] / shares.sum()
        return float(-(shares * np.log(shares)).sum())

    return frame.groupby("group_key").apply(_shannon)


def compute_shannon_total(dataset: Dataset, allocation: pd.Series) -> float:
    """Shannon diversity of the whole allocated area, over crops.

    compute_shannon_diversity already does this per region and per island, but a territorial
    scalar is what a scenario comparison needs: cropping diversity is an agroecological
    outcome in its own right, and a per-region series cannot be put on a comparison axis.
    """
    surface = _plot_surface(dataset, allocation)
    shares = surface.groupby(allocation).sum()
    shares = shares[shares > 0]
    total = shares.sum()
    if total <= 0:
        return 0.0
    shares = shares / total
    return float(-(shares * np.log(shares)).sum())


def _ratio(numerator: float, denominator: float) -> float | None:
    """numerator/denominator, or None when the denominator is zero.

    None rather than 0.0 on purpose: "no hectares allocated" is not "zero euros per hectare",
    and a 0 would be averaged into a composite score as if it were a measurement.
    """
    if not denominator:
        return None
    return float(numerator) / float(denominator)


def compute_intensity_totals(
    economics: dict[str, float], environment: dict[str, float], surface_ha: float
) -> dict[str, float | None]:
    """Intensity and public-spending-efficiency ratios, derived from totals already computed.

    Two reasons these matter more than the totals in a scenario comparison:

    * scenarios do not allocate the same number of hectares (a policy that leaves land idle
      shows a lower nitrogen TOTAL while being no cleaner per hectare), so a comparison on
      totals alone confuses scale with intensity;
    * the spending-efficiency ratios are the evaluation metric a public policy is actually
      judged on -- euros of subsidy per tonne, per full-time job, per euro of margin. They
      are what separates paying for a result from paying for an activity, which is exactly
      the question P6 (incentive only) and P7 (regulation only) were written to pose.

    Pure arithmetic on the two totals dicts, so it needs no dataset and is trivially testable.
    """
    production = economics.get("total_production_tonnes") or 0.0
    subsidy = economics.get("total_subsidy") or 0.0
    margin = economics.get("total_gross_margin") or 0.0
    etp = economics.get("total_etp") or 0.0
    azote = environment.get("total_azote") or 0.0
    ift = environment.get("total_ift") or 0.0

    return {
        # Land intensity
        "gross_margin_per_ha": _ratio(margin, surface_ha),
        "etp_per_ha": _ratio(etp, surface_ha),
        "production_per_ha": _ratio(production, surface_ha),
        # Labour productivity -- the other side of etp_per_ha: a policy can raise employment
        # by making each job less productive, and only this ratio shows it.
        "gross_margin_per_etp": _ratio(margin, etp),
        # Environmental intensity per unit produced, not per hectare: feeding the territory
        # with less nitrogen per tonne is a different claim from farming fewer hectares.
        "azote_per_tonne": _ratio(azote, production),
        "ift_per_tonne": _ratio(ift, production),
        # Public spending efficiency
        "subsidy_per_tonne": _ratio(subsidy, production),
        "subsidy_per_etp": _ratio(subsidy, etp),
        "subsidy_per_euro_margin": _ratio(subsidy, margin),
        "subsidy_per_ha": _ratio(subsidy, surface_ha),
    }


def _surface_by_dimension_and_key(
    dataset: Dataset, allocation: pd.Series, dimension: pd.Series, name: str
) -> pd.DataFrame:
    """Allocated surface (ha) pivoted as `name` (rows) x crop (columns)."""
    frame = pd.DataFrame({
        name: dimension.reindex(allocation.index),
        "crop": allocation,
        "surface": _plot_surface(dataset, allocation),
    })
    return frame.pivot_table(
        index=name, columns="crop", values="surface", aggfunc="sum", fill_value=0.0
    )


def compute_surface_by_region_and_key(dataset: Dataset, allocation: pd.Series) -> pd.DataFrame:
    return _surface_by_dimension_and_key(
        dataset, allocation, plot_to_region(dataset), "region"
    )


def compute_surface_by_island_and_key(dataset: Dataset, allocation: pd.Series) -> pd.DataFrame:
    return _surface_by_dimension_and_key(
        dataset, allocation, plot_to_island(dataset), "island"
    )
