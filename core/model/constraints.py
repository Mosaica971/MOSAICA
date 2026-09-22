from collections import defaultdict
from collections.abc import Mapping
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


@register_constraint("crop_share_bound")
def build_crop_share_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    numerator_crops: list[str],
    denominator_crops: list[str],
    sense: str,
    share: float,
    **_args: Any,
) -> None:
    """Territory-wide share bound: area(numerator) {ge|le} share * area(denominator),
    summed over all plots. Used for a minimum bio share (numerator = bio variants,
    denominator = whole filiere, ge) or a maximum intensification share (numerator =
    intensive variants, le)."""
    if sense not in ("le", "ge"):
        raise ValueError(f"Unknown sense {sense!r}, expected 'le' or 'ge'")

    numerator_set = set(numerator_crops)
    denominator_set = set(denominator_crops)
    numerator_area = 0
    denominator_area = 0
    for plot, crop in inputs.eligible_pairs:
        if crop in numerator_set:
            numerator_area += model.Y[plot, crop] * inputs.plot_surface_ha[plot]
        if crop in denominator_set:
            denominator_area += model.Y[plot, crop] * inputs.plot_surface_ha[plot]

    # Both sides may be a plain 0 (no eligible pairs) -- guard the trivial Boolean, as in
    # territory_production_bound.
    if isinstance(numerator_area, (int, float)) and isinstance(denominator_area, (int, float)):
        satisfied = (
            numerator_area >= share * denominator_area
            if sense == "ge"
            else numerator_area <= share * denominator_area
        )
        setattr(
            model,
            label,
            pyo.Constraint(
                expr=pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible
            ),
        )
        return

    expr = (
        numerator_area >= share * denominator_area
        if sense == "ge"
        else numerator_area <= share * denominator_area
    )
    setattr(model, label, pyo.Constraint(expr=expr))


def _indicator_rates(inputs: ModelInputs, indicator: str) -> Mapping[str, float]:
    """The per-hectare rate mapping the case study exposed under `indicator`.

    Fails loudly on an unknown name rather than defaulting to zero: a silently empty rate
    mapping turns every bound below into a vacuous `0 <= threshold`, i.e. a scenario that
    looks regulated and is not.
    """
    try:
        return inputs.crop_indicator_rates[indicator]
    except KeyError:
        available = ", ".join(sorted(inputs.crop_indicator_rates)) or "(none)"
        raise KeyError(
            f"Unknown indicator {indicator!r}. Exposed by this case study: {available}"
        ) from None


def _plot_weights(inputs: ModelInputs, plot_weight: str | None) -> Mapping[str, float] | None:
    if plot_weight is None:
        return None
    try:
        return inputs.plot_weights[plot_weight]
    except KeyError:
        available = ", ".join(sorted(inputs.plot_weights)) or "(none)"
        raise KeyError(
            f"Unknown plot_weight {plot_weight!r}. Exposed by this case study: {available}"
        ) from None


def _bounded(expr, sense: str, threshold: float):
    """`expr {le|ge} threshold`, guarding the trivial-Boolean case (see the note in
    territory_production_bound: an empty sum is a plain 0, not a Pyomo expression)."""
    if isinstance(expr, (int, float)):
        satisfied = expr <= threshold if sense == "le" else expr >= threshold
        return pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible
    return expr <= threshold if sense == "le" else expr >= threshold


@register_constraint("territory_indicator_bound")
def build_territory_indicator_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    indicator: str,
    sense: str,
    threshold: float,
    crops: list[str] | None = None,
    scale: float = 1.0,
    plot_weight: str | None = None,
    **_args: Any,
) -> None:
    """Territory-wide ceiling or floor on any exposed per-hectare indicator:
    sum(surface x weight[plot] x rate[crop]) x scale {<=|>=} threshold.

    This is the regulatory counterpart of territory_production_bound, which can only bound
    physical output. The same builder expresses a nitrogen ceiling, a pesticide-index (IFT)
    ceiling, a GHG budget, a water-withdrawal cap, an organic-carbon floor, a public-spending
    envelope (indicator = the subsidy rate) or an employment floor (indicator = labour
    hours) -- whichever mappings the case study put in crop_indicator_rates.

    `crops` restricts the bound to one filiere (e.g. an IFT ceiling on export banana only);
    absent, every allocated crop counts. `scale` converts units at the last moment (e.g.
    labour hours -> full-time equivalents) so the threshold can be written in the unit a
    policy is actually stated in. `plot_weight` names a per-plot multiplier, for the
    quantities that depend on the plot and not only on the crop.
    """
    if sense not in ("le", "ge"):
        raise ValueError(f"Unknown sense {sense!r}, expected 'le' or 'ge'")
    rates = _indicator_rates(inputs, indicator)
    weights = _plot_weights(inputs, plot_weight)
    crop_set = set(crops) if crops is not None else None

    total = 0
    for plot, crop in inputs.eligible_pairs:
        if crop_set is not None and crop not in crop_set:
            continue
        rate = rates.get(crop, 0.0)
        if not rate:
            continue
        weight = 1.0 if weights is None else weights.get(plot, 0.0)
        if not weight:
            continue
        total += model.Y[plot, crop] * inputs.plot_surface_ha[plot] * weight * rate * scale

    setattr(model, label, pyo.Constraint(expr=_bounded(total, sense, threshold)))


@register_constraint("zone_indicator_bound")
def build_zone_indicator_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    zone: str,
    indicator: str,
    sense: str,
    threshold: float | None = None,
    threshold_per_ha: float | None = None,
    thresholds: dict[Any, float] | None = None,
    crops: list[str] | None = None,
    scale: float = 1.0,
    plot_weight: str | None = None,
    **_args: Any,
) -> None:
    """The same bound, held separately inside each zone of a grouping (`zone` names a key of
    ModelInputs.plot_zones -- islands, regions, watersheds, farms, ...).

    Three ways to state the limit, in decreasing priority: `thresholds` gives an explicit
    value per zone (zones absent from it are left unconstrained); `threshold_per_ha`
    multiplies each zone's own hectares, which is how a per-hectare regulation is written
    (a nitrogen directive at 170 kgN/ha of farmland, say); `threshold` applies the same
    absolute value to every zone.

    Grouping by farms is deliberately allowed: a per-farm environmental cap is the same
    algebra as a per-catchment one, and farms are just another partition of the plots.
    """
    if sense not in ("le", "ge"):
        raise ValueError(f"Unknown sense {sense!r}, expected 'le' or 'ge'")
    if threshold is None and threshold_per_ha is None and thresholds is None:
        raise ValueError(
            f"{label}: give one of threshold, threshold_per_ha or thresholds"
        )
    try:
        plot_zone = inputs.plot_zones[zone]
    except KeyError:
        available = ", ".join(sorted(inputs.plot_zones)) or "(none)"
        raise KeyError(f"Unknown zone {zone!r}. Exposed by this case study: {available}") from None

    rates = _indicator_rates(inputs, indicator)
    weights = _plot_weights(inputs, plot_weight)
    crop_set = set(crops) if crops is not None else None

    zone_terms: dict[Any, Any] = defaultdict(int)
    for plot, crop in inputs.eligible_pairs:
        if crop_set is not None and crop not in crop_set:
            continue
        zone_id = plot_zone.get(plot)
        if zone_id is None:
            continue
        rate = rates.get(crop, 0.0)
        if not rate:
            continue
        weight = 1.0 if weights is None else weights.get(plot, 0.0)
        if not weight:
            continue
        zone_terms[zone_id] += (
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * weight * rate * scale
        )

    # Zone hectares are summed over the zone's plots rather than read from a surface
    # mapping, so any grouping works without the case study supplying a second table.
    # threshold_per_ha counts the same hectares the bound itself counts -- weighted when a
    # plot_weight applies -- so a per-hectare limit stays a limit on the regulated hectares.
    zone_surface: dict[Any, float] = defaultdict(float)
    for plot, zone_id in plot_zone.items():
        if zone_id is None or plot not in inputs.plot_surface_ha:
            continue
        weight = 1.0 if weights is None else weights.get(plot, 0.0)
        zone_surface[zone_id] += inputs.plot_surface_ha[plot] * weight

    # A zone contributing no term at all -- no eligible (plot, crop) pair carrying a non-zero
    # rate -- is left UNCONSTRAINED rather than given `0 {<=|>=} threshold`. Harmless for a
    # ceiling (zero is under any positive cap) but worth knowing for a FLOOR: such a zone is
    # silently exempt instead of making the run infeasible. That is the same trade the case
    # study makes explicitly in `cs_gfa_minimum_share` (losing 3 farms out of 4 588 rather
    # than the whole constraint); the difference is that here it is the only behaviour on
    # offer. If a scenario needs a floor that no zone may escape, count the zones it produced
    # against the zones the grouping declares before trusting it.
    zone_ids = sorted(zone_terms if thresholds is None else set(zone_terms) & set(thresholds))

    def _rule(model, zone_id):
        if thresholds is not None:
            limit = thresholds[zone_id]
        elif threshold_per_ha is not None:
            limit = threshold_per_ha * zone_surface.get(zone_id, 0.0)
        else:
            limit = threshold
        return _bounded(zone_terms[zone_id], sense, limit)

    setattr(model, label, pyo.Constraint(zone_ids, rule=_rule))


@register_constraint("baseline_inertia_min")
def build_baseline_inertia_min_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    min_share: float,
    **_args: Any,
) -> None:
    """At least `min_share` of the allocated area must stay in its observed baseline use.

    Without this the model may replant the whole territory at once, which is the strongest
    unstated assumption in a one-shot allocation: it prices no conversion cost, no learning
    curve, no plantation still standing. A scenario that keeps 80% of hectares in their 2017
    group is describing a decade of transition; one that keeps 20% is describing a rupture.

    A plot counts as unchanged when the assigned crop's group (ModelInputs.crop_group) equals
    the plot's baseline group. Both sides are variable -- the requirement is a share of the
    area actually allocated, not of the territory -- which keeps it linear and keeps it from
    forcing land into production just to satisfy a ratio.
    """
    if not 0.0 <= min_share <= 1.0:
        raise ValueError(f"{label}: min_share must be within [0, 1], got {min_share}")

    unchanged_area = 0
    allocated_area = 0
    for plot, crop in inputs.eligible_pairs:
        term = model.Y[plot, crop] * inputs.plot_surface_ha[plot]
        allocated_area += term
        baseline = inputs.plot_baseline_group.get(plot)
        if baseline is not None and inputs.crop_group.get(crop) == baseline:
            unchanged_area += term

    if isinstance(unchanged_area, (int, float)) and isinstance(allocated_area, (int, float)):
        satisfied = unchanged_area >= min_share * allocated_area
        setattr(
            model,
            label,
            pyo.Constraint(
                expr=pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible
            ),
        )
        return
    setattr(model, label, pyo.Constraint(expr=unchanged_area >= min_share * allocated_area))


@register_constraint("farm_labor_hours_max")
def build_farm_labor_hours_max_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    slack: float = 1.0,
    **_args,
) -> None:
    """Each farm's allocation may not demand more labour than the farm is assumed to have.

    The capacity is a stock supplied by the case study -- typically derived from the farm's
    observed baseline cropping plan, which is what makes this an anchor to reality rather
    than a generic resource limit. `slack` scales every cap uniformly (1.0 = the cap as
    given); it exists so the assumption can be relaxed from config without touching code.

    A farm with no capacity entry is left unconstrained: the mapping is optional like every
    other ModelInputs field, and defaulting a missing farm to zero would silently freeze it.
    """
    rates = inputs.crop_labor_hours_per_ha
    capacities = inputs.farm_labor_capacity_hours
    plot_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if rates.get(crop, 0.0):
            plot_crops[plot].append(crop)

    def _rule(model, farm):
        if farm not in capacities:
            return pyo.Constraint.Feasible
        hours = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * rates[crop]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_crops.get(plot, [])
        )
        limit = slack * capacities[farm]
        # A farm whose eligible crops all have a zero labour rate sums to a plain 0, not a
        # Pyomo expression -- see the note in territory_production_bound above.
        if isinstance(hours, (int, float)):
            return pyo.Constraint.Feasible if hours <= limit else pyo.Constraint.Infeasible
        return hours <= limit

    setattr(model, label, pyo.Constraint(model.FARMS, rule=_rule))


@register_constraint("farm_production_bound")
def build_farm_production_bound_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    crops: list[str],
    reference: str,
    sense: str = "le",
    scale: float = 1.0,
    **_args,
) -> None:
    """Bound each farm's own production of a crop group against a per-farm reference.

    The territory-wide `territory_production_bound` says how much the whole island may
    produce; this says how much EACH farm may. The two are not interchangeable: a single
    territorial ceiling lets the model concentrate the whole quota on the few farms where
    the crop pays best, which is exactly what a delivery right attached to the holding
    forbids. GAMS Eq_BA_QUOTA_Expl (MODELE.txt:361-366) is that case -- export-banana
    tonnage capped, farm by farm, at what the farm produced in the reference year.

    `reference` names an entry of ModelInputs.farm_production_capacity, so several quotas
    (one per market) can coexist without a builder each. `scale` multiplies every cap
    uniformly, so the strictness of the assumption is a config question, not a code change.

    A farm with no entry under `reference` is left unconstrained -- defaulting a missing
    farm to zero would silently freeze it, the same reasoning as farm_labor_hours_max.
    """
    if sense not in ("le", "ge"):
        raise ValueError(f"farm_production_bound[{label}]: sense must be 'le' or 'ge'")
    yields = inputs.crop_yield_per_ha
    capacities = inputs.farm_production_capacity.get(reference, {})
    wanted = set(crops)
    plot_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in wanted and yields.get(crop, 0.0):
            plot_crops[plot].append(crop)

    def _rule(model, farm):
        if farm not in capacities:
            return pyo.Constraint.Feasible
        produced = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * yields[crop]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_crops.get(plot, [])
        )
        limit = scale * capacities[farm]
        # No eligible pair on this farm carries the group: the sum is a plain 0, not a
        # Pyomo expression -- see the note in territory_production_bound above.
        if isinstance(produced, (int, float)):
            satisfied = produced <= limit if sense == "le" else produced >= limit
            return pyo.Constraint.Feasible if satisfied else pyo.Constraint.Infeasible
        return produced <= limit if sense == "le" else produced >= limit

    setattr(model, label, pyo.Constraint(model.FARMS, rule=_rule))
