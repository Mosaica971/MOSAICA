import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_objective


@register_objective("maximize_gross_margin")
def build_maximize_gross_margin_objective(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * inputs.crop_margin_per_ha[crop]
            for plot, crop in inputs.eligible_pairs
        ),
        sense=pyo.maximize,
    )
