from typing import Any

import pandas as pd
import pyomo.environ as pyo

from case_studies.guadeloupe.domain.crop_families import base_group_for
from case_studies.guadeloupe.model import constraints as _guadeloupe_constraints  # noqa: F401
from core.config import scale_territorial_bounds
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs

# Per-hectare rates a config-declared bound may target, mapped to the dataset parameter
# holding them. The name on the left is what config.yaml / scenarios write as `indicator:`;
# the unit on the right is what the threshold must then be expressed in.
#   azote      kg N / ha / an          ift      indice de frequence de traitement / ha / an
#   ges        u GES / ha / an         eau      mm / ha / an  (x10 -> m3, cf. domain/water.py)
#   carbone    entrees de C / ha / an  travail  h / ha / an   (/1607 -> ETP)
#   subvention EUR / ha / an           marge / vente / cout    EUR / ha / an
#   rendement  t / ha / an
# `subvention` is the annualized subsidy, i.e. what a public-spending envelope must count.
# Two rates are narrower than the indicator of the same name in the run report, and a
# threshold must be set in the constraint's own terms, not read off recap.json:
#   * `eau` counts every hectare unless the bound passes plot_weight: irrigable (which is
#     what the report counts) -- 5.6 Mmm.ha over all land, i.e. 56 Mm3, against 35 Mm3;
#   * `carbone` is the crop's carbon INPUT only. The reported soil-carbon BALANCE also
#     depends on the plot's soil type (Data_Sol), which a per-crop rate cannot carry.
# `ges` is in the model's own unit -- its scale is an open question (see TODO.md) -- so GHG
# thresholds here are calibrated as a share of the run's own baseline, not in t CO2.
_INDICATOR_PARAMETERS: dict[str, str] = {
    "azote": "azote_per_ha_cult",
    "phosphore": "phosphore_per_ha_cult",
    "potasse": "potasse_per_ha_cult",
    "ift": "ift_per_ha_cult",
    "ges": "ges_per_ha_cult",
    "eau": "water_need_per_ha_cult",
    "carbone": "carbon_input_per_ha_cult",
    "travail": "labor_hours_per_ha_cult",
    "subvention": "subsidy_per_ha_cult_annualized",
    # Agroecology, as the data actually encodes it. `surface_mae` and `surface_bio` are 0/1
    # rates, so multiplied by plot surface they sum to HECTARES -- which is how a scenario
    # writes "at least N ha under an agri-environmental measure" with an ordinary bound.
    "mae": "mae_per_ha_cult",
    "surface_mae": "under_mae_cult",
    "surface_bio": "organic_cult",
    "marge": "margin_per_ha_cult",
    "cout": "variable_cost_per_ha_cult",
    "vente": "sales_per_ha_cult",
    "rendement": "rdt_cult",
}


def _crop_indicator_rates(dataset: Dataset) -> dict[str, dict[str, float]]:
    rates: dict[str, dict[str, float]] = {}
    for indicator, parameter in _INDICATOR_PARAMETERS.items():
        series = dataset.parameters.get(parameter)
        if series is None:
            continue
        rates[indicator] = {
            crop: float(value) for crop, value in series.items() if pd.notna(value)
        }
    return rates


def _plot_weights(dataset: Dataset) -> dict[str, dict[str, float]]:
    """Per-plot multipliers a bound may weight its hectares by.

    `irrigable` is the one that matters: the water indicator is a per-crop rate, but only a
    plot connected to the network actually draws from the resource (OPTIMISATION.txt:2540,
    and reporting/indicators._irrigable_surface does the same). Without this weight a water
    ceiling would count rain-fed hectares and would not be the same quantity the run reports
    as total_water_need_m3 -- 56 Mm3 against 35 -- so a threshold read off one would be
    wrong against the other.
    """
    data_parc = dataset.parameters["data_parc"]
    weights: dict[str, dict[str, float]] = {}
    if "IRRIG_PARC" in data_parc.columns:
        weights["irrigable"] = (data_parc["IRRIG_PARC"] == 1).astype(float).to_dict()
    if "GFA_PARC" in data_parc.columns:
        weights["gfa"] = data_parc["GFA_PARC"].fillna(0).astype(float).to_dict()
    # Plots at the highest chlordecone risk class, for a health-driven scenario that bounds
    # what may be grown on contaminated land.
    if "RISQUE_CLD" in data_parc.columns:
        weights["sol_contamine"] = (data_parc["RISQUE_CLD"] == 1).astype(float).to_dict()
    return weights


def _plot_zones(dataset: Dataset) -> dict[str, dict[str, Any]]:
    """Groupings a bound may hold within. The four geographic columns come from the plot
    table; watersheds and catchments from their own plot-mapping sets; `farms` makes a
    per-farm environmental cap expressible with the same generic builder."""
    data_parc = dataset.parameters["data_parc"]
    zones: dict[str, dict[str, Any]] = {
        column.lower(): data_parc[column].dropna().to_dict()
        for column in ("ILE", "REGION", "REGION_CODE", "COMMUNE")
        if column in data_parc.columns
    }
    for name, (parameter, key) in {
        "watersheds": ("bv_parc", "watershed"),
        "catchments": ("cpt_parc", "catchment"),
        "farms": ("expl_parc", "farm"),
    }.items():
        table = dataset.parameters.get(parameter)
        if table is not None:
            zones[name] = table.set_index("plot")[key].to_dict()
    return zones


def build_model(dataset: Dataset, config: dict[str, Any]) -> pyo.ConcreteModel:
    # Observed 2017 group per plot, and the group each fine crop folds onto -- the pair the
    # inertia rule compares. base_crop_group already carries the 12 RPG groups, so only the
    # crop side needs folding.
    base_crop_group = dataset.parameters.get("base_crop_group")
    plot_baseline_group = (
        base_crop_group.dropna().to_dict() if base_crop_group is not None else {}
    )
    # A crop whose family token is unknown is skipped rather than raising: crop_group only
    # feeds baseline_inertia_min, which is optional, so an unrecognised code must not sink
    # model building. Such a crop simply never counts as "unchanged".
    crop_group = {}
    for crop in dataset.parameters["margin_per_ha_cult"].index:
        try:
            crop_group[crop] = base_group_for(crop)
        except KeyError:
            continue

    inputs = ModelInputs(
        plot_surface_ha=dataset.parameters["data_parc"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["margin_per_ha_cult"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        farm_plots=dataset.parameters.get("farm_plots", {}),
        farm_surface_ha=dataset.parameters.get("farm_surface_ha", {}),
        farm_restricted_surface_ha=dataset.parameters.get("farm_gfa_surface_ha", {}),
        crop_yield_per_ha=dataset.parameters.get("rdt_cult", {}),
        crop_variance_per_ha=dataset.parameters.get("crop_variance_per_ha", {}),
        farm_risk_aversion=dataset.parameters.get("farm_risk_aversion", {}),
        crop_labor_hours_per_ha=dataset.parameters.get("labor_hours_per_ha_cult", {}),
        # GAMS MO_Expl_init (ENTREES.txt:466-469): the labour the farm's OBSERVED 2017
        # cropping plan required, which Eq_MO_MAX_Expl then treats as its budget.
        farm_labor_capacity_hours=dataset.parameters.get("farm_labor_capacity_hours", {}),
        crop_indicator_rates=_crop_indicator_rates(dataset),
        plot_zones=_plot_zones(dataset),
        plot_weights=_plot_weights(dataset),
        crop_group=crop_group,
        plot_baseline_group=plot_baseline_group,
    )

    # Opt-in: bring the territorial thresholds down to the slice of territory the zone
    # filter kept, so a one-island run is a miniature of the real problem rather than an
    # infeasible fragment of it (the 6 096 ha pasture floor alone sinks Marie-Galante).
    if (config.get("zone_filter") or {}).get("scale_territorial_bounds"):
        fraction = float(dataset.scalars.get("zone_surface_fraction", 1.0))
        print(
            f"zone_filter : seuils territoriaux mis a l'echelle x{fraction:.4f} "
            f"({100 * fraction:.1f} % de la surface)"
        )
        config = scale_territorial_bounds(config, fraction)

    return build_crop_allocation_model(inputs, config)
