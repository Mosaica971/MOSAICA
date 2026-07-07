from collections import defaultdict

import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_constraint


@register_constraint("at_most_one_crop_per_plot")
def build_at_most_one_crop_per_plot_constraint(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    plots_to_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        plots_to_crops[plot].append(crop)

    def _rule(model, plot):
        return sum(model.Y[plot, crop] for crop in plots_to_crops[plot]) <= 1

    model.at_most_one_crop_per_plot = pyo.Constraint(model.PLOTS, rule=_rule)
