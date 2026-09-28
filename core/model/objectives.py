import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_objective


@register_objective("maximize_gross_margin")
def build_maximize_gross_margin_objective(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    """Maximise total gross margin: sum over pairs of Y * plot area * crop margin per ha."""
    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * inputs.crop_margin_per_ha[crop]
            for plot, crop in inputs.eligible_pairs
        ),
        sense=pyo.maximize,
    )


@register_objective("maximize_risk_adjusted_gross_margin")
def build_maximize_risk_adjusted_gross_margin_objective(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    """Maximise margin weighted by (1 - farm risk aversion x crop yield variance).

    The Markowitz-style objective GAMS solves in both its CALIB and SCENARIO blocks: a
    risk-averse farm discounts a high-variance crop. Missing aversion or variance counts as
    0, i.e. no discount.
    """
    plot_to_farm = {
        plot: farm for farm, plots in inputs.farm_plots.items() for plot in plots
    }
    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop]
            * inputs.plot_surface_ha[plot]
            * inputs.crop_margin_per_ha[crop]
            * (
                1
                - inputs.farm_risk_aversion.get(plot_to_farm.get(plot), 0.0)
                * inputs.crop_variance_per_ha.get(crop, 0.0)
            )
            for plot, crop in inputs.eligible_pairs
        ),
        sense=pyo.maximize,
    )
