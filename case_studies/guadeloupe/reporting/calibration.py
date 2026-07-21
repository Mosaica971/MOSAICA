"""Observed-vs-simulated calibration metrics, after Chopin et al. (2015) §2.6.

The article evaluates MOSAICA with the percentage of absolute deviation (PAD, Eq. 7)
between the observed acreage X_init(a) of a crop and the simulated acreage X(a), read at
four nested scales: region, sub-region, farm and field. This module computes those, plus
the per-farm PAD the article states a threshold for without publishing its table.

Everything is compared at the resolution of the 12 observed RPG groups: the observed 2017
land use has no finer resolution (see VIGILANCE.md on the aggregate baseline), so the
simulated fine crops are folded back with domain/crop_families.

Reporting only -- nothing here influences the allocation, and no solve is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.reporting import indicators
from core.data.dataset import Dataset

TOTAL_KEY = "TOTAL"

# Chopin et al. (2015) §2.6: PAD below 15% regionally and 20% in sub-regions and farms,
# 80% of farms in the right type. The article takes these from Kanellopoulos et al. (2010),
# Hazell and Norton (1986) and Janssen and van Ittersum (2007) -- they are conventions, not
# physical limits, hence configurable.
DEFAULT_REGIONAL_PAD_MAX = 15.0
DEFAULT_SUBREGIONAL_PAD_MAX = 20.0
DEFAULT_FARM_PAD_MAX = 20.0
DEFAULT_FARM_TYPE_MATCH_MIN = 80.0


@dataclass(frozen=True)
class CalibrationThresholds:
    regional_pad_max: float = DEFAULT_REGIONAL_PAD_MAX
    subregional_pad_max: float = DEFAULT_SUBREGIONAL_PAD_MAX
    farm_pad_max: float = DEFAULT_FARM_PAD_MAX
    farm_type_match_min: float = DEFAULT_FARM_TYPE_MATCH_MIN


def thresholds_from_config(config: dict[str, Any]) -> CalibrationThresholds:
    section = (config.get("reporting") or {}).get("calibration") or {}
    return CalibrationThresholds(
        regional_pad_max=float(section.get("regional_pad_max", DEFAULT_REGIONAL_PAD_MAX)),
        subregional_pad_max=float(
            section.get("subregional_pad_max", DEFAULT_SUBREGIONAL_PAD_MAX)
        ),
        farm_pad_max=float(section.get("farm_pad_max", DEFAULT_FARM_PAD_MAX)),
        farm_type_match_min=float(
            section.get("farm_type_match_min", DEFAULT_FARM_TYPE_MATCH_MIN)
        ),
    )


def observed_groups(dataset: Dataset) -> pd.Series:
    """plot -> observed RPG group, NC and unmapped codes already dropped. Identical to the
    baseline the rest of the reporting uses, so both sides tell the same story."""
    return indicators.decode_baseline_allocation(dataset)


def simulated_groups(dataset: Dataset, output_allocation: pd.Series) -> pd.Series:
    """plot -> simulated RPG group. NC is dropped, symmetrically with the observed side:
    a plot the solver leaves non-cultivated is not part of any crop's acreage."""
    groups = crop_families.base_groups_for(output_allocation)
    return groups[groups != crop_families.NON_CULTIVATED]


def _surface_by_group(dataset: Dataset, groups: pd.Series) -> pd.Series:
    return indicators.compute_surface_by_key(dataset, groups)


def _pad_frame(observed: pd.Series, simulated: pd.Series, threshold: float) -> pd.DataFrame:
    """PAD table over the union of the two indexes, plus a TOTAL row.

    Per-entry PAD is 100*|obs-sim|/obs, undefined (NaN) when nothing was observed -- that is
    a crop the model invented, whose deviation cannot be expressed as a share of zero. The
    TOTAL row is the ratio of the sums, Eq. 7 proper; the two verdicts are independent.
    """
    keys = observed.index.union(simulated.index)
    observed = observed.reindex(keys, fill_value=0.0).astype(float)
    simulated = simulated.reindex(keys, fill_value=0.0).astype(float)
    deviation = (simulated - observed).abs()
    pad = 100.0 * deviation / observed.where(observed > 0)

    frame = pd.DataFrame(
        {
            "observed_ha": observed,
            "simulated_ha": simulated,
            "abs_deviation_ha": deviation,
            "pad_pct": pad,
            "within_threshold": pad.le(threshold).where(pad.notna()).astype("boolean"),
        }
    )

    total_observed = float(observed.sum())
    total_deviation = float(deviation.sum())
    total_pad = 100.0 * total_deviation / total_observed if total_observed > 0 else float("nan")
    frame.loc[TOTAL_KEY] = {
        "observed_ha": total_observed,
        "simulated_ha": float(simulated.sum()),
        "abs_deviation_ha": total_deviation,
        "pad_pct": total_pad,
        "within_threshold": pd.NA if pd.isna(total_pad) else bool(total_pad <= threshold),
    }
    frame["within_threshold"] = frame["within_threshold"].astype("boolean")
    return frame


def pad_by_crop(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Regional scale, Chopin et al. Fig. 4: acreage per crop over the whole territory."""
    observed = _surface_by_group(dataset, observed_groups(dataset))
    simulated = _surface_by_group(dataset, simulated_groups(dataset, output_allocation))
    frame = _pad_frame(observed, simulated, thresholds.regional_pad_max)
    frame.index.name = "crop"
    return frame
