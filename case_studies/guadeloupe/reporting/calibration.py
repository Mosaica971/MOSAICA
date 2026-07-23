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

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.domain.farm_typology import (
    TYPE_EXPL_LABELS,
    compute_base_crop_group,
    compute_type_expl,
)
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


def _surface_by_group_and_key(
    dataset: Dataset, groups: pd.Series, key: pd.Series
) -> pd.Series:
    """Allocated surface totalled by (key, group), for a plot-keyed grouping Series."""
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(groups.index)
    keys = key.reindex(groups.index)
    return surface.groupby([keys, groups]).sum()


def pad_by_crop_and_region(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Sub-regional scale, Chopin et al. Fig. 5: acreage per crop within each of the seven
    areas of homogeneous soil and climate conditions. One TOTAL row per region; the
    territory-wide total lives in pad_by_crop."""
    region = indicators.plot_to_region(dataset)
    observed = _surface_by_group_and_key(dataset, observed_groups(dataset), region)
    simulated = _surface_by_group_and_key(
        dataset, simulated_groups(dataset, output_allocation), region
    )
    # .unique() before .union(): both level-value Indexes carry one entry per (region, crop)
    # pair, and Index.union over duplicated inputs is a multiset union -- it would yield a
    # region as many times as its busiest side has crops, and emit that many blocks.
    regions = (
        observed.index.get_level_values(0)
        .unique()
        .union(simulated.index.get_level_values(0).unique())
    )

    def slice_for(totals: pd.Series, region_key: Any) -> pd.Series:
        """The (crop -> hectares) sub-series of one region, empty when it has none.
        Series.get on a MultiIndex is ambiguous, hence the explicit cross-section."""
        if region_key not in totals.index.get_level_values(0):
            return pd.Series(dtype=float)
        return totals.xs(region_key, level=0)

    blocks = []
    for region_key in sorted(regions, key=str):
        frame = _pad_frame(
            slice_for(observed, region_key),
            slice_for(simulated, region_key),
            thresholds.subregional_pad_max,
        )
        frame.index = pd.MultiIndex.from_product(
            [[region_key], frame.index], names=["region", "crop"]
        )
        blocks.append(frame)
    return pd.concat(blocks)


def _pad_totals_by_key(
    dataset: Dataset, output_allocation: pd.Series, key: pd.Series, threshold: float
) -> pd.DataFrame:
    """One row per value of `key` (farm, island, ...), the deviation summed over the crops
    of that group. Same PAD convention as _pad_frame -- undefined where nothing was observed
    -- but aggregated to a single figure per key rather than kept per crop."""
    observed = _surface_by_group_and_key(dataset, observed_groups(dataset), key)
    simulated = _surface_by_group_and_key(
        dataset, simulated_groups(dataset, output_allocation), key
    )
    keys = observed.index.union(simulated.index)
    observed = observed.reindex(keys, fill_value=0.0)
    simulated = simulated.reindex(keys, fill_value=0.0)

    frame = pd.DataFrame(
        {
            "observed_ha": observed.groupby(level=0).sum(),
            "simulated_ha": simulated.groupby(level=0).sum(),
            "abs_deviation_ha": (simulated - observed).abs().groupby(level=0).sum(),
        }
    )
    pad = 100.0 * frame["abs_deviation_ha"] / frame["observed_ha"].where(
        frame["observed_ha"] > 0
    )
    frame["pad_pct"] = pad
    frame["within_threshold"] = pad.le(threshold).where(pad.notna()).astype("boolean")
    return frame


def pad_by_farm(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Farm scale: the article states a 20% threshold "in the sub-regions and farms"
    without publishing the table. One row per farm, the deviation summed over its crops."""
    farm = indicators.plot_to_farm(dataset)
    by_farm = _pad_totals_by_key(dataset, output_allocation, farm, thresholds.farm_pad_max)
    by_farm.index.name = "farm"
    return by_farm


def pad_by_island(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Island scale: one row per island, the deviation summed over its crops. Not a Chopin
    scale (the article stops at the seven sub-regions), reported for the Guadeloupe
    archipelago where the islands are a natural aggregation coarser than the sub-regions.
    Read against the sub-regional 20% threshold for want of a published island figure."""
    island = indicators.plot_to_island(dataset)
    by_island = _pad_totals_by_key(
        dataset, output_allocation, island, thresholds.subregional_pad_max
    )
    by_island.index.name = "island"
    return by_island


def field_match_rate(dataset: Dataset, output_allocation: pd.Series) -> pd.DataFrame:
    """Field scale, Chopin et al. Table 5: share of plots -- and of hectares -- where the
    simulated crop equals the observed one, per sub-region and overall.

    The universe is the union of the two sides: a plot cultivated on one side only counts
    as a miss, but a plot non-cultivated on both is outside the comparison entirely.
    """
    observed = observed_groups(dataset)
    simulated = simulated_groups(dataset, output_allocation)
    plots = observed.index.union(simulated.index)

    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"].reindex(plots).astype(float)
    region = indicators.plot_to_region(dataset).reindex(plots)
    matched = observed.reindex(plots).eq(simulated.reindex(plots))

    frame = pd.DataFrame(
        {
            "matched_plots": matched.groupby(region).sum().astype(int),
            "total_plots": matched.groupby(region).size().astype(int),
            "matched_ha": surface.where(matched, 0.0).groupby(region).sum(),
            "total_ha": surface.groupby(region).sum(),
        }
    )
    frame.loc[TOTAL_KEY] = {
        "matched_plots": int(matched.sum()),
        "total_plots": int(len(plots)),
        "matched_ha": float(surface.where(matched, 0.0).sum()),
        "total_ha": float(surface.sum()),
    }
    frame["plot_match_pct"] = 100.0 * frame["matched_plots"] / frame["total_plots"]
    frame["area_match_pct"] = 100.0 * frame["matched_ha"] / frame["total_ha"]
    frame.index.name = "region"
    return frame[
        [
            "matched_plots",
            "total_plots",
            "plot_match_pct",
            "matched_ha",
            "total_ha",
            "area_match_pct",
        ]
    ]


def _type_expl(dataset: Dataset, groups: pd.Series) -> pd.Series:
    """farm -> TYPE_EXPL, for a plot -> base-group Series covering the full plot universe."""
    plot_surface = dataset.parameters["data_parc"]["SURF_HA"]
    type_expl, _bis = compute_type_expl(
        dataset.parameters["farm_plots"], groups, plot_surface
    )
    return type_expl


def farm_type_confusion(dataset: Dataset, output_allocation: pd.Series) -> pd.DataFrame:
    """Farm scale, Chopin et al. Table 4: observed farm type x simulated farm type.

    Both sides go through compute_type_expl, which needs the FULL plot universe: NC plots
    feed surf_non, which is subtracted from the denominator of every PART_* share. Dropping
    them -- as the NC-free baseline allocation does -- would shift the shares and could flip
    a farm's type, so the observed side is recomputed here from data_parc and a plot the
    solver left unallocated counts as NC, its agronomic meaning.

    One asymmetry is deliberate: compute_base_crop_group returns NaN for an RPG code it
    does not map, and compute_type_expl drops those rows. That is what the pipeline already
    does for the observed side, so it is reproduced rather than "fixed" here.
    """
    data_parc = dataset.parameters["data_parc"]
    observed = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])

    simulated = pd.Series(crop_families.NON_CULTIVATED, index=data_parc.index)
    simulated.update(crop_families.base_groups_for(output_allocation))

    codes = sorted(TYPE_EXPL_LABELS)
    confusion = pd.crosstab(_type_expl(dataset, observed), _type_expl(dataset, simulated))
    confusion = confusion.reindex(index=codes, columns=codes, fill_value=0).astype(int)
    confusion.index.name = "type_observe"
    confusion.columns.name = "type_simule"
    return confusion


def farm_type_match_summary(confusion: pd.DataFrame) -> dict[str, Any]:
    """Diagonal share of a confusion matrix, plus per-type recall for the types actually
    present in the observed data (a type nobody starts in has no recall to report)."""
    total = int(confusion.to_numpy().sum())
    matched = int(sum(confusion.loc[code, code] for code in confusion.index))
    observed_totals = confusion.sum(axis=1)
    return {
        "total_farms": total,
        "matched_farms": matched,
        "match_pct": 100.0 * matched / total if total else float("nan"),
        "recall_by_type": {
            TYPE_EXPL_LABELS[code]: 100.0 * float(confusion.loc[code, code]) / float(count)
            for code, count in observed_totals.items()
            if count > 0
        },
    }


def _optional_float(value: Any) -> float | None:
    """JSON has no NaN: an undefined metric is None, not a float that json.dumps emits as
    the invalid literal NaN."""
    if value is None or pd.isna(value):
        return None
    return float(value)


@dataclass(frozen=True)
class CalibrationResult:
    """Every block of Chopin et al. §2.6 for one run, plus the thresholds they are read
    against. Frames are for CSV and figures; summary() is what goes into recap.json."""

    thresholds: CalibrationThresholds
    pad_by_crop: pd.DataFrame
    pad_by_crop_and_region: pd.DataFrame
    pad_by_farm: pd.DataFrame
    farm_type_confusion: pd.DataFrame
    field_match: pd.DataFrame

    def summary(self) -> dict[str, Any]:
        crops = self.pad_by_crop.drop(index=TOTAL_KEY)
        total = self.pad_by_crop.loc[TOTAL_KEY]
        subregional = self.pad_by_crop_and_region[
            self.pad_by_crop_and_region.index.get_level_values("crop") != TOTAL_KEY
        ]
        farms = self.pad_by_farm
        field_total = self.field_match.loc[TOTAL_KEY]
        farm_type = farm_type_match_summary(self.farm_type_confusion)

        # Verdicts are recomputed from the numeric PAD rather than read off the
        # within_threshold column: that column is a nullable BooleanDtype whose scalars do
        # not compare cleanly with `is True`, and bool(pd.NA) raises outright.
        regional_pad = _optional_float(total["pad_pct"])
        farm_type_pct = _optional_float(farm_type["match_pct"])

        def _count_true(column: pd.Series) -> int:
            return int(column.fillna(False).astype(bool).sum())

        return {
            "thresholds": asdict(self.thresholds),
            "regional_pad_pct": regional_pad,
            "regional_within_threshold": (
                regional_pad is not None and regional_pad <= self.thresholds.regional_pad_max
            ),
            "crops_evaluated": int(crops["within_threshold"].notna().sum()),
            "crops_within_threshold": _count_true(crops["within_threshold"]),
            "subregional_cells_evaluated": int(subregional["within_threshold"].notna().sum()),
            "subregional_cells_within_threshold": _count_true(subregional["within_threshold"]),
            "farms_evaluated": int(farms["within_threshold"].notna().sum()),
            "farms_within_threshold": _count_true(farms["within_threshold"]),
            "farm_type_match_pct": farm_type_pct,
            "farm_type_within_threshold": (
                farm_type_pct is not None
                and farm_type_pct >= self.thresholds.farm_type_match_min
            ),
            "farm_type_recall_by_type": {
                label: float(value) for label, value in farm_type["recall_by_type"].items()
            },
            "matched_plots": int(field_total["matched_plots"]),
            "total_plots": int(field_total["total_plots"]),
            "plot_match_pct": _optional_float(field_total["plot_match_pct"]),
            "matched_ha": float(field_total["matched_ha"]),
            "total_ha": float(field_total["total_ha"]),
            "area_match_pct": _optional_float(field_total["area_match_pct"]),
        }


def evaluate(
    dataset: Dataset, output_allocation: pd.Series, config: dict[str, Any]
) -> CalibrationResult:
    """Every calibration metric for one solved allocation. No solve, no file written."""
    thresholds = thresholds_from_config(config)
    return CalibrationResult(
        thresholds=thresholds,
        pad_by_crop=pad_by_crop(dataset, output_allocation, thresholds),
        pad_by_crop_and_region=pad_by_crop_and_region(dataset, output_allocation, thresholds),
        pad_by_farm=pad_by_farm(dataset, output_allocation, thresholds),
        farm_type_confusion=farm_type_confusion(dataset, output_allocation),
        field_match=field_match_rate(dataset, output_allocation),
    )
