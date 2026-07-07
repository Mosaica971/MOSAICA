from collections import defaultdict
from collections.abc import Mapping, Sequence

import pyomo.environ as pyo


def build_crop_allocation_model(
    plot_surface_ha: Mapping[str, float],
    crop_margin_per_ha: Mapping[str, float],
    eligible_pairs: Sequence[tuple[str, str]],
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()

    plots_to_crops = defaultdict(list)
    for plot, crop in eligible_pairs:
        plots_to_crops[plot].append(crop)

    model.PAIRS = pyo.Set(initialize=list(eligible_pairs), dimen=2)
    model.PLOTS = pyo.Set(initialize=list(plots_to_crops.keys()))
    model.Y = pyo.Var(model.PAIRS, within=pyo.Binary)

    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop] * plot_surface_ha[plot] * crop_margin_per_ha[crop]
            for plot, crop in eligible_pairs
        ),
        sense=pyo.maximize,
    )

    def _at_most_one_crop_per_plot_rule(model, plot):
        return sum(model.Y[plot, crop] for crop in plots_to_crops[plot]) <= 1

    model.at_most_one_crop_per_plot = pyo.Constraint(
        model.PLOTS, rule=_at_most_one_crop_per_plot_rule
    )

    return model
