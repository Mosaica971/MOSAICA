from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Dataset:
    sets: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, pd.DataFrame | pd.Series] = field(default_factory=dict)
    scalars: dict[str, float] = field(default_factory=dict)
