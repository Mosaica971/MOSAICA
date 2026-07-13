from collections import defaultdict
from typing import Any

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
    groups: list[dict[str, Any]],
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


@register_constraint("farm_area_share_max")
def build_farm_area_share_max_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    crops: list[str],
    max_share: float,
    **_args,
) -> None:
    crop_set = set(crops)
    plot_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in crop_set:
            plot_crops[plot].append(crop)

    def _rule(model, farm):
        area = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_crops.get(plot, [])
        )
        limit = max_share * inputs.farm_surface_ha[farm]
        # A farm with zero eligible plots for these crops sums to a plain 0, not a
        # Pyomo expression -- see the note in territory_production_bound above.
        if isinstance(area, (int, float)):
            return pyo.Constraint.Feasible if area <= limit else pyo.Constraint.Infeasible
        return area <= limit

    setattr(model, label, pyo.Constraint(model.FARMS, rule=_rule))


@register_constraint("farm_area_ratio_min")
def build_farm_area_ratio_min_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    numerator_crops: list[str],
    denominator_crops: list[str],
    ratio: float,
    **_args,
) -> None:
    numerator_set = set(numerator_crops)
    denominator_set = set(denominator_crops)
    plot_numerator_crops = defaultdict(list)
    plot_denominator_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in numerator_set:
            plot_numerator_crops[plot].append(crop)
        if crop in denominator_set:
            plot_denominator_crops[plot].append(crop)

    def _rule(model, farm, denom_crop):
        numerator_area = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_numerator_crops.get(plot, [])
        )
        denominator_area = sum(
            model.Y[plot, denom_crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            if denom_crop in plot_denominator_crops.get(plot, [])
        )
        # Both sides trivially 0 (no eligible plots for either side, on this farm)
        # -- see the note in territory_production_bound above.
        if isinstance(numerator_area, (int, float)) and isinstance(denominator_area, (int, float)):
            satisfied = numerator_area >= ratio * denominator_area
            return pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible
        return numerator_area >= ratio * denominator_area

    setattr(model, label, pyo.Constraint(model.FARMS, denominator_crops, rule=_rule))
