from collections import defaultdict
from typing import Any

import pyomo.environ as pyo

from core.config import resolve_enabled
from core.model import constraints as _constraints  # noqa: F401 (registers builders)
from core.model import objectives as _objectives  # noqa: F401 (registers builders)
from core.model.model_inputs import ModelInputs
from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY


def build_crop_allocation_model(
    inputs: ModelInputs, config: dict[str, Any]
) -> pyo.ConcreteModel:
    """Binary crop-allocation model: Y[plot, crop] over the eligible pairs, plus every
    constraint and the single objective enabled in `config`.

    Optional inputs default to empty mappings via ModelInputs' field defaults; a builder
    that needs one it was not given will simply find nothing to constrain.
    """
    model = pyo.ConcreteModel()

    plots_to_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        plots_to_crops[plot].append(crop)

    model.PAIRS = pyo.Set(initialize=list(inputs.eligible_pairs), dimen=2)
    model.PLOTS = pyo.Set(initialize=list(plots_to_crops.keys()))
    model.FARMS = pyo.Set(initialize=list(inputs.farm_plots.keys()))
    model.Y = pyo.Var(model.PAIRS, within=pyo.Binary)

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
