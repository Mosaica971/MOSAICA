from typing import Any

import pyomo.environ as pyo

from case_studies.guadeloupe.model import constraints as _guadeloupe_constraints  # noqa: F401
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model


def build_model(dataset: Dataset, config: dict[str, Any]) -> pyo.ConcreteModel:
    return build_crop_allocation_model(
        plot_surface_ha=dataset.parameters["data_parc"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["margin_per_ha_cult"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        config=config,
        farm_plots=dataset.parameters.get("farm_plots", {}),
        farm_surface_ha=dataset.parameters.get("farm_surface_ha", {}),
        farm_gfa_surface_ha=dataset.parameters.get("farm_gfa_surface_ha", {}),
        crop_yield_per_ha=dataset.parameters.get("rdt_cult", {}),
        crop_variance_per_ha=dataset.parameters.get("crop_variance_per_ha", {}),
        farm_risk_aversion=dataset.parameters.get("farm_risk_aversion", {}),
    )
