from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass
class ModelInputs:
    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
