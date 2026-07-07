from typing import Any

import pyomo.environ as pyo

from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model


def build_model(dataset: Dataset, config: dict[str, Any]) -> pyo.ConcreteModel:
    return build_crop_allocation_model(
        plot_surface_ha=dataset.parameters["data_parc"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["margin_per_ha_cult"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        config=config,
    )
