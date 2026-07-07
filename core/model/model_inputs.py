from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass
class ModelInputs:
    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
    farm_plots: Mapping[str, Sequence[str]] = field(default_factory=dict)
    farm_surface_ha: Mapping[str, float] = field(default_factory=dict)
    farm_gfa_surface_ha: Mapping[str, float] = field(default_factory=dict)
    crop_yield_per_ha: Mapping[str, float] = field(default_factory=dict)
