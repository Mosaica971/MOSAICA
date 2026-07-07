from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import pyomo.environ as pyo

from core.config import resolve_enabled
from core.model import constraints as _constraints  # noqa: F401 (registers builders)
from core.model import objectives as _objectives  # noqa: F401 (registers builders)
from core.model.model_inputs import ModelInputs
from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY


def build_crop_allocation_model(
    plot_surface_ha: Mapping[str, float],
    crop_margin_per_ha: Mapping[str, float],
    eligible_pairs: Sequence[tuple[str, str]],
    config: dict[str, Any],
    farm_plots: Mapping[str, Sequence[str]] | None = None,
    farm_surface_ha: Mapping[str, float] | None = None,
    farm_gfa_surface_ha: Mapping[str, float] | None = None,
    crop_yield_per_ha: Mapping[str, float] | None = None,
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()
    farm_plots = {} if farm_plots is None else farm_plots
    farm_surface_ha = {} if farm_surface_ha is None else farm_surface_ha
    farm_gfa_surface_ha = {} if farm_gfa_surface_ha is None else farm_gfa_surface_ha
    crop_yield_per_ha = {} if crop_yield_per_ha is None else crop_yield_per_ha

    plots_to_crops = defaultdict(list)
    for plot, crop in eligible_pairs:
        plots_to_crops[plot].append(crop)

    model.PAIRS = pyo.Set(initialize=list(eligible_pairs), dimen=2)
    model.PLOTS = pyo.Set(initialize=list(plots_to_crops.keys()))
    model.FARMS = pyo.Set(initialize=list(farm_plots.keys()))
    model.Y = pyo.Var(model.PAIRS, within=pyo.Binary)

    inputs = ModelInputs(
        plot_surface_ha=plot_surface_ha,
        crop_margin_per_ha=crop_margin_per_ha,
        eligible_pairs=eligible_pairs,
        farm_plots=farm_plots,
        farm_surface_ha=farm_surface_ha,
        farm_gfa_surface_ha=farm_gfa_surface_ha,
        crop_yield_per_ha=crop_yield_per_ha,
    )

    for build_constraint, args in resolve_enabled(config["constraints"], CONSTRAINT_REGISTRY):
        build_constraint(model, inputs, **args)

    enabled_objectives = resolve_enabled(config["objectives"], OBJECTIVE_REGISTRY)
    if len(enabled_objectives) != 1:
        raise ValueError(
            f"Expected exactly one enabled objective, got {len(enabled_objectives)}"
        )
    build_objective, args = enabled_objectives[0]
    build_objective(model, inputs, **args)

    return model
