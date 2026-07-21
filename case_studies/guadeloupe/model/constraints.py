from collections import defaultdict

import pyomo.environ as pyo

from core.model.model_inputs import ModelInputs
from core.model.registry import register_constraint


@register_constraint("cs_gfa_minimum_share")
def build_cs_gfa_minimum_share_constraint(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,
    crops: list[str],
    min_share: float,
    skip_when_no_eligible_area: bool = False,
    **_args,
) -> None:
    """Sugarcane must cover at least `min_share` of each farm's land-tenure-restricted area
    (GAMS Eq_CS_GFA, MODELE.txt:349).

    `skip_when_no_eligible_area` is a DELIBERATE DEVIATION from GAMS, off by default. On the
    real 2017 data three farms (E1471, E273, E3955) have every plot fallow-locked by
    friche_lock, so no plot can carry sugarcane while the rule demands 60% of it: genuinely
    infeasible, and GAMS would be infeasible too. With the flag on, such a farm is skipped
    instead of sinking the whole solve. Scope: 3 farms out of 4588. See VIGILANCE.md.
    """
    crop_set = set(crops)
    plot_crops = defaultdict(list)
    for plot, crop in inputs.eligible_pairs:
        if crop in crop_set:
            plot_crops[plot].append(crop)

    eligible_farms = [
        farm for farm in inputs.farm_plots if inputs.farm_restricted_surface_ha.get(farm, 0.0) > 0
    ]

    def _rule(model, farm):
        area = sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot]
            for plot in inputs.farm_plots.get(farm, [])
            for crop in plot_crops.get(plot, [])
        )
        requirement = min_share * inputs.farm_restricted_surface_ha[farm]
        # A GFA farm with zero eligible SC crop plots sums to a plain 0 -- see the
        # note in territory_production_bound above. Note this can legitimately
        # resolve to Constraint.Infeasible (not just Feasible): a farm required to
        # keep 60% of its GFA land in sugarcane but with zero sugarcane-eligible
        # plots really is infeasible under this rule, matching GAMS's algebraic
        # infeasibility for the same equation -- that should surface as a solver
        # infeasibility, not a Python crash, which is exactly what this achieves.
        if isinstance(area, (int, float)):
            if area >= requirement:
                return pyo.Constraint.Feasible
            return (
                pyo.Constraint.Feasible
                if skip_when_no_eligible_area
                else pyo.Constraint.Infeasible
            )
        return area >= requirement

    setattr(model, label, pyo.Constraint(eligible_farms, rule=_rule))
