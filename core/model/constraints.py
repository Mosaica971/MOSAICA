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


@register_constraint("territory_production_bound")
def build_territory_production_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    groups: list[dict],
    sense: str,
    threshold: float,
    **_args,
) -> None:
    if sense not in ("le", "ge"):
        raise ValueError(f"Unknown sense {sense!r}, expected 'le' or 'ge'")

    total = 0
    for group in groups:
        crops = set(group["crops"])
        use_yield = group.get("use_yield", True)
        rate_multiplier = group.get("rate_multiplier", 1.0)
        for plot, crop in inputs.eligible_pairs:
            if crop not in crops:
                continue
            rate = inputs.crop_yield_per_ha[crop] if use_yield else 1.0
            total += model.Y[plot, crop] * inputs.plot_surface_ha[plot] * rate * rate_multiplier

    # sum() over zero matching (plot, crop) pairs returns a plain Python 0, not a
    # Pyomo expression -- comparing two plain numbers below would produce a bare
    # Python bool, which Pyomo's Constraint rejects ("trivial Boolean") instead of
    # treating as an always-true/always-false constraint. Guard for it explicitly.
    if isinstance(total, (int, float)):
        satisfied = total <= threshold if sense == "le" else total >= threshold
        setattr(
            model,
            label,
            pyo.Constraint(expr=pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible),
        )
        return

    expr = total <= threshold if sense == "le" else total >= threshold
    setattr(model, label, pyo.Constraint(expr=expr))
