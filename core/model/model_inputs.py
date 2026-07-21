from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass
class ModelInputs:
    """Everything the constraint and objective builders may read, in case-study-neutral
    terms. Only the first three are always needed; a builder given nothing for an optional
    field simply finds nothing to constrain.
    """

    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
    farm_plots: Mapping[str, Sequence[str]] = field(default_factory=dict)
    farm_surface_ha: Mapping[str, float] = field(default_factory=dict)
    # Surface of the subset of a farm's plots flagged as subject to a land-tenure scheme,
    # for rules that apply a quota to that subset only rather than the whole farm.
    farm_restricted_surface_ha: Mapping[str, float] = field(default_factory=dict)
    crop_yield_per_ha: Mapping[str, float] = field(default_factory=dict)
    crop_variance_per_ha: Mapping[str, float] = field(default_factory=dict)
    farm_risk_aversion: Mapping[str, float] = field(default_factory=dict)
