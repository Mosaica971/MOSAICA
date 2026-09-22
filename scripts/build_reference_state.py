"""Build the 2017 reference state of Guadeloupe -- the observed situation every run is
scored against.

    python scripts/build_reference_state.py            # -> outputs/reference_2017/
    python scripts/build_reference_state.py --dir <path>

No solve: the reference is read straight out of the RPG land-use history in
Data_Parc_Gwad_2017.txt (~5 s). It is deliberately built with the SAME functions the model
and the calibration use -- decode_baseline_allocation, compute_base_crop_group,
compute_farm_type, indicators.* -- so the reference folder and a run's "input" side are the
same numbers by construction, not two parallel reconstructions that could drift apart.

Four things make this more than a group-by, and each has its own CSV:

1. RAW vs RESOLVED land use. GAMS forces cult_2017 to NC when cult_2016 AND cult_2017 are
   both fallow (ENTREES.txt:49-57). That moves ~1200 ha from JA to NC before anything else
   happens. Both readings are written out, so the reclassification is visible rather than
   implicit.
2. THE OBSERVED SIDE HAS NO FINE CROPS. The 12 RPG groups say "sugarcane", never which
   technical system. Every economic/environmental figure of the reference therefore rests on
   config's baseline_representative_crops. The central estimate uses exactly that assumption
   (so it matches the runs); a low/high bracket over the fine variants each plot could
   actually carry says how much the assumption is worth.
3. THE REPRODUCIBILITY CEILING. Part of the observed acreage sits on plots where no fine
   variant of the observed family is eligible -- the model cannot reproduce it whatever the
   objective does. That share is a floor under the PAD, and it belongs to the reference, not
   to the run.
4. THE FARM TYPOLOGY. The observed TYPE_EXPL distribution is the row-marginal of every
   confusion matrix, and it also fixes each farm's risk aversion, so it is part of the
   reference state and not a result.

The column and key names were translated to English on 2026-09-22. A copy of the last
French-keyed folder is kept in outputs/_legacy_reference_2017_fr/ for the thesis tooling.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.domain.farm_typology import (
    FARM_TYPE_LABELS,
    compute_risk_aversion,
    compute_base_crop_group,
    compute_farm_type,
)
from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import indicators
from core.config import load_config
from core.data.dataset import Dataset

from scripts._common import CONFIG_PATH, OUTPUTS_ROOT, format_number as _n

DEFAULT_DIR_NAME = "reference_2017"

# Readable names for the 12 observed RPG groups (ENTREES.txt:62-103).
GROUP_LABELS: dict[str, str] = {
    "AG": "Citrus",
    "AN": "Pineapple",
    "BA": "Export banana",
    "BC": "Plantain",
    "CS": "Sugarcane",
    "IG": "Yam and tubers",
    "JA": "Fallow",
    "MA": "Market gardening",
    "ME": "Melon",
    "NC": "Not cultivated",
    "PN": "Grassland and savannah",
    "VE": "Orchards excluding citrus",
}

# Per-ha rates bracketed below (see _metric_rates for where each comes from).
_BRACKETED_METRICS = (
    "production_tonnes",
    "sales",
    "subsidy",
    "revenue",
    "gross_margin",
    "labor_hours",
    "nitrogen",
    "ghg",
    "tfi",
)


def _raw_groups(plot_data: pd.DataFrame) -> pd.Series:
    """plot -> RPG group read from cult_2017 alone, WITHOUT the fallow-continuity rule.

    Obtained by handing compute_base_crop_group a cult_2016 that is never fallow, so the
    rule cannot fire -- rather than duplicating the code->group table here, which would be
    one more place to keep in sync with ENTREES.txt.
    """
    never_fallow = pd.Series(1, index=plot_data.index)
    return compute_base_crop_group(never_fallow, plot_data["cult_2017"])


def _resolved_groups(plot_data: pd.DataFrame) -> pd.Series:
    """plot -> RPG group as the model reads it: the fallow-continuity rule applied, NC kept."""
    return compute_base_crop_group(plot_data["cult_2016"], plot_data["cult_2017"])


def _surface_and_count(surface: pd.Series, groups: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "surface_ha": surface.reindex(groups.index).groupby(groups).sum(),
            "plots": groups.groupby(groups).size(),
        }
    )


def land_use_table(dataset: Dataset) -> pd.DataFrame:
    """Observed acreage per RPG group, in the two readings plus the cultivated reference.

    `reference_ha` is what the PAD is computed against: the resolved reading minus NC, since
    a non-cultivated plot is not part of any crop's acreage on either side.
    """
    plot_data = dataset.parameters["plot_data"]
    surface = plot_data["SURF_HA"]
    raw = _surface_and_count(surface, _raw_groups(plot_data))
    resolved = _surface_and_count(surface, _resolved_groups(plot_data))

    frame = pd.DataFrame(
        {
            "label": pd.Series(GROUP_LABELS),
            "raw_ha": raw["surface_ha"],
            "raw_plots": raw["plots"],
            "resolved_ha": resolved["surface_ha"],
            "resolved_plots": resolved["plots"],
        }
    ).fillna({"raw_ha": 0.0, "raw_plots": 0, "resolved_ha": 0.0, "resolved_plots": 0})
    frame["resolution_gap_ha"] = frame["resolved_ha"] - frame["raw_ha"]
    frame["reference_ha"] = frame["resolved_ha"].where(
        frame.index != crop_families.NON_CULTIVATED, 0.0
    )
    cultivated = float(frame["reference_ha"].sum())
    frame["cultivated_share_pct"] = 100.0 * frame["reference_ha"] / cultivated
    frame.index.name = "group"
    return frame.sort_index()


def surface_by_group_and_key(
    dataset: Dataset, groups: pd.Series, key: pd.Series, key_name: str
) -> pd.DataFrame:
    """Cultivated reference acreage pivoted as key x group, with row and column totals."""
    surface = dataset.parameters["plot_data"]["SURF_HA"].reindex(groups.index)
    frame = pd.DataFrame(
        {key_name: key.reindex(groups.index), "group": groups, "surface_ha": surface}
    )
    pivot = frame.pivot_table(
        index=key_name, columns="group", values="surface_ha", aggfunc="sum", fill_value=0.0
    )
    pivot["TOTAL"] = pivot.sum(axis=1)
    pivot.loc["TOTAL"] = pivot.sum(axis=0)
    return pivot.round(2)


def farm_typology_table(dataset: Dataset) -> pd.DataFrame:
    """Observed farm-type distribution: the row-marginal of every confusion matrix, and the
    table that fixes each farm's risk aversion (AVERS) in the Markowitz objective."""
    plot_data = dataset.parameters["plot_data"]
    farm_type, type_bis = compute_farm_type(
        dataset.parameters["farm_plots"], _resolved_groups(plot_data), plot_data["SURF_HA"]
    )
    aversion = compute_risk_aversion(farm_type, type_bis)
    farm_surface = dataset.parameters["farm_surface_ha"]

    frame = pd.DataFrame(
        {
            "farms": farm_type.groupby(farm_type).size(),
            "surface_ha": farm_surface.reindex(farm_type.index).groupby(farm_type).sum(),
            "aversion_min": aversion.groupby(farm_type).min(),
            "aversion_max": aversion.groupby(farm_type).max(),
        }
    )
    frame.insert(0, "label", pd.Series({code: FARM_TYPE_LABELS[code] for code in frame.index}))
    frame["farm_share_pct"] = 100.0 * frame["farms"] / frame["farms"].sum()
    frame.index.name = "farm_type"
    return frame


def reference_allocation(dataset: Dataset, config: dict[str, Any]) -> pd.DataFrame:
    """The canonical per-plot reference: what was observed there in 2017, and which fine
    crop stands in for it when a per-ha rate is needed."""
    plot_data = dataset.parameters["plot_data"]
    resolved = _resolved_groups(plot_data)
    representative = indicators.decode_baseline_representative_allocation(dataset, config)
    farm = indicators.plot_to_farm(dataset)

    frame = pd.DataFrame(
        {
            "plot": plot_data.index,
            "farm": farm.reindex(plot_data.index).to_numpy(),
            "region": plot_data["REGION"].to_numpy(),
            "island": plot_data["ILE"].to_numpy(),
            "commune": plot_data["COMMUNE"].to_numpy(),
            "surface_ha": plot_data["SURF_HA"].to_numpy(),
            "cult_2016_code": plot_data["cult_2016"].to_numpy(),
            "cult_2017_code": plot_data["cult_2017"].to_numpy(),
            "raw_group": _raw_groups(plot_data).to_numpy(),
            "resolved_group": resolved.to_numpy(),
            "representative_crop": representative.reindex(plot_data.index).to_numpy(),
        }
    )
    frame["cultivated"] = frame["resolved_group"] != crop_families.NON_CULTIVATED
    return frame


def _fine_variants_by_group(dataset: Dataset, config: dict[str, Any]) -> dict[str, list[str]]:
    """Observed RPG group -> the fine crops that can stand for it.

    The eight aggregate codes (AN, BA, ... -- exactly the keys of
    baseline_representative_crops) are excluded: they exist only to encode the observed
    baseline, carry no technical itinerary and no economics, and would drag any bracket to
    zero. NC is excluded for the same reason.
    """
    aggregates = set(config.get("baseline_representative_crops") or {})
    variants: dict[str, list[str]] = {}
    for crop in sorted(dataset.sets["crops"]):
        if crop in aggregates or crop == crop_families.NON_CULTIVATED:
            continue
        variants.setdefault(crop_families.base_group_for(crop), []).append(crop)
    return variants


def reproducibility_table(dataset: Dataset, config: dict[str, Any]) -> pd.DataFrame:
    """Per observed group: how much of its acreage the model could even place back.

    A plot counts as reproducible when at least one fine variant of its observed family is
    eligible on it. What is not reproducible is a deviation no objective function can avoid,
    so it is a floor under the PAD -- and it belongs to the reference, since it is a property
    of the data and the eligibility mask alone.

    Caveat kept explicit in the doc: eligibility embeds the GAMS suppressions (Eq_*_SUPP,
    Eq_VE_PLUIE banned everywhere by the ported GAMS bug), not just agronomy.
    """
    plot_data = dataset.parameters["plot_data"]
    surface = plot_data["SURF_HA"]
    mask = dataset.parameters["eligibility_mask"]
    groups = _resolved_groups(plot_data)
    variants = _fine_variants_by_group(dataset, config)

    rows = []
    for group in sorted(groups.dropna().unique()):
        if group == crop_families.NON_CULTIVATED:
            continue
        plots = groups.index[groups == group]
        candidates = variants.get(group, [])
        if candidates:
            reproducible = mask.loc[plots, candidates].any(axis=1)
        else:
            reproducible = pd.Series(False, index=plots)
        rows.append(
            {
                "group": group,
                "label": GROUP_LABELS.get(group, group),
                "fine_variants": len(candidates),
                "observed_ha": float(surface[plots].sum()),
                "observed_plots": int(len(plots)),
                "reproducible_ha": float(surface[plots][reproducible].sum()),
                "reproducible_plots": int(reproducible.sum()),
            }
        )

    frame = pd.DataFrame(rows).set_index("group")
    frame["irreproducible_ha"] = frame["observed_ha"] - frame["reproducible_ha"]
    frame["reproducible_share_pct"] = 100.0 * frame["reproducible_ha"] / frame["observed_ha"]
    return frame


def representative_eligibility_table(
    dataset: Dataset, config: dict[str, Any]
) -> pd.DataFrame:
    """Per observed family: how much of its acreage the representative crop is actually
    ELIGIBLE on.

    The representative is a reporting convention, so nothing forces it to be a crop the
    model would allow on the plot -- and on this data it often is not (CS_NGT_NISM is the
    North-Grande-Terre cane system, confined to three communes, while it stands for every
    observed cane hectare). That matters twice: the reference's own economics is valued with
    a system that could not be grown there, and farm_labor_hours_max derives each farm's cap
    from those same crops, so the mismatch reaches the optimum.
    """
    plot_data = dataset.parameters["plot_data"]
    surface = plot_data["SURF_HA"]
    mask = dataset.parameters["eligibility_mask"]
    groups = _resolved_groups(plot_data)
    mapping = config.get("baseline_representative_crops") or {}

    rows = []
    for group in sorted(groups.dropna().unique()):
        if group == crop_families.NON_CULTIVATED:
            continue
        # Families with no fine variant (AG, ME, JA) stand for themselves.
        representative = mapping.get(group, group)
        plots = groups.index[groups == group]
        eligible = mask.loc[plots, representative] if representative in mask.columns else False
        rows.append(
            {
                "group": group,
                "representative": representative,
                "observed_ha": float(surface[plots].sum()),
                "representative_eligible_ha": float(surface[plots][eligible].sum()),
                "representative_margin_eur_ha": float(
                    dataset.parameters["crop_margin_per_ha"].get(representative, float("nan"))
                ),
            }
        )

    frame = pd.DataFrame(rows).set_index("group")
    frame["eligible_share_pct"] = (
        100.0 * frame["representative_eligible_ha"] / frame["observed_ha"]
    )
    return frame


def _metric_rates(dataset: Dataset) -> dict[str, pd.Series]:
    """Crop-indexed per-ha rates behind the bracketed metrics. `revenue` is bracketed on the
    combined rate, not as min(sales)+min(subsidy), which no single crop would realise."""
    parameters = dataset.parameters
    sales = parameters["crop_sales_per_ha"]
    subsidy = parameters["crop_subsidy_per_ha_annualized"]
    return {
        "production_tonnes": parameters["crop_yield"],
        "sales": sales,
        "subsidy": subsidy,
        "revenue": sales + subsidy,
        "gross_margin": parameters["crop_margin_per_ha"],
        "labor_hours": parameters["crop_labor_hours_per_ha"],
        "nitrogen": parameters["crop_nitrogen_per_ha"],
        "ghg": parameters["crop_ghg_per_ha"],
        "tfi": parameters["crop_tfi_per_ha"],
    }


def _bracket_totals(
    dataset: Dataset, config: dict[str, Any]
) -> tuple[dict[str, dict[str, float]], int]:
    """Territory totals of each metric when every observed plot carries the cheapest, then
    the dearest, fine variant of its own family that it could actually carry.

    Returns (totals, fallback_plots): the number of plots where the eligibility mask leaves
    no variant of the observed family, and the bracket falls back to the family's full fine
    set (an over-estimate of the choice really available there).
    """
    plot_data = dataset.parameters["plot_data"]
    surface = plot_data["SURF_HA"]
    mask = dataset.parameters["eligibility_mask"]
    groups = _resolved_groups(plot_data)
    variants = _fine_variants_by_group(dataset, config)
    rates = _metric_rates(dataset)

    low = {metric: 0.0 for metric in _BRACKETED_METRICS}
    high = {metric: 0.0 for metric in _BRACKETED_METRICS}
    fallback_plots = 0

    for group in sorted(groups.dropna().unique()):
        if group == crop_families.NON_CULTIVATED:
            continue
        plots = groups.index[groups == group]
        candidates = variants.get(group, [])
        if not candidates:
            continue
        # .copy(): to_numpy may hand back a read-only view of the mask's block, and the
        # fallback below writes into it.
        eligible = mask.loc[plots, candidates].to_numpy(dtype=bool).copy()
        # A plot with no eligible variant keeps the whole family as its choice set: the
        # reference has to value it somehow, and pretending the choice is empty would drop
        # its hectares from the bracket entirely.
        empty = ~eligible.any(axis=1)
        fallback_plots += int(empty.sum())
        eligible[empty, :] = True
        plot_surface = surface[plots].to_numpy(dtype=float)

        for metric in _BRACKETED_METRICS:
            rate = rates[metric].reindex(candidates).to_numpy(dtype=float)
            values = np.where(eligible, rate[None, :], np.nan)
            low[metric] += float(np.nansum(np.nanmin(values, axis=1) * plot_surface))
            high[metric] += float(np.nansum(np.nanmax(values, axis=1) * plot_surface))

    return {"low": low, "high": high}, fallback_plots


def indicator_table(dataset: Dataset, config: dict[str, Any]) -> tuple[pd.DataFrame, int]:
    """Reference indicators: the central estimate (config's representative crops, i.e. the
    exact numbers a run reports on its input side) framed by the low/high bracket."""
    hours_per_fte = indicators.hours_per_fte_from_config(config)
    cost_per_hour = indicators.labor_cost_per_hour_from_config(config)
    representative = indicators.decode_baseline_representative_allocation(dataset, config)

    economics = indicators.compute_economic_totals(
        dataset, representative, hours_per_fte, cost_per_hour
    )
    environment = indicators.compute_environmental_totals(dataset, representative)
    bracket, fallback_plots = _bracket_totals(dataset, config)

    central = {
        "production_tonnes": economics["total_production_tonnes"],
        "sales": economics["total_revenue"] - economics["total_subsidy"],
        "subsidy": economics["total_subsidy"],
        "revenue": economics["total_revenue"],
        "gross_margin": economics["total_gross_margin"],
        "labor_hours": economics["total_fte"] * hours_per_fte,
        "nitrogen": environment["total_nitrogen"],
        "ghg": environment["total_ghg"],
        "tfi": environment["total_tfi"],
    }
    units = {
        "production_tonnes": "t",
        "sales": "EUR",
        "subsidy": "EUR",
        "revenue": "EUR",
        "gross_margin": "EUR",
        "labor_hours": "h",
        "nitrogen": "kg N",
        "ghg": "t CO2 (magnitude, see docs/04-vigilance.md)",
        "tfi": "TFI.ha",
    }

    frame = pd.DataFrame(
        {
            "unit": pd.Series(units),
            "central": pd.Series(central),
            "low": pd.Series(bracket["low"]),
            "high": pd.Series(bracket["high"]),
        }
    )
    frame["range_pct_of_central"] = 100.0 * (frame["high"] - frame["low"]) / frame["central"]
    frame.index.name = "indicator"

    # Metrics with no bracket (they do not reduce to a per-crop per-ha rate, or the observed
    # side has no variant choice at all) still belong in the reference.
    extra = pd.DataFrame(
        {
            "unit": ["FTE", "EUR", "EUR", "ha", "m3", "t C"],
            "central": [
                economics["total_fte"],
                economics["total_labor_cost"],
                economics["total_net_revenue"],
                environment["chlordecone_risk_area"],
                environment["total_water_need_m3"],
                environment["soil_carbon_balance"],
            ],
        },
        index=[
            "fte",
            "labor_cost",
            "net_revenue",
            "chlordecone_risk_area",
            "water_need_m3",
            "soil_carbon_balance",
        ],
    )
    extra.index.name = "indicator"
    return pd.concat([frame, extra]), fallback_plots


@dataclass(frozen=True)
class Reference:
    config: dict[str, Any]
    land_use: pd.DataFrame
    by_region: pd.DataFrame
    by_island: pd.DataFrame
    by_commune: pd.DataFrame
    farm_types: pd.DataFrame
    allocation: pd.DataFrame
    reproducibility: pd.DataFrame
    representative_eligibility: pd.DataFrame
    indicators: pd.DataFrame
    bracket_fallback_plots: int
    universe: dict[str, Any]


def build_reference(config: dict[str, Any]) -> Reference:
    dataset = build_dataset(config)
    plot_data = dataset.parameters["plot_data"]
    cultivated = indicators.decode_baseline_allocation(dataset)

    land_use = land_use_table(dataset)
    indicator_frame, fallback_plots = indicator_table(dataset, config)

    universe = {
        "plots": int(len(plot_data)),
        "farms": int(dataset.parameters["farm_plot_map"]["farm"].nunique()),
        "total_area_ha": float(plot_data["SURF_HA"].sum()),
        "cultivated_area_ha": float(land_use["reference_ha"].sum()),
        "uncultivated_area_ha": float(
            land_use.loc[crop_families.NON_CULTIVATED, "resolved_ha"]
        ),
        "cultivated_plots": int(len(cultivated)),
        "cultivated_farms": int(
            indicators.plot_to_farm(dataset).reindex(cultivated.index).nunique()
        ),
        "economic_year": (config.get("data") or {}).get("year"),
        "economic_scenario": (config.get("data") or {}).get("scenario"),
        "zone_filter": config.get("zone_filter"),
        "representative_crops": config.get("baseline_representative_crops"),
    }

    return Reference(
        config=config,
        land_use=land_use,
        by_region=surface_by_group_and_key(
            dataset, cultivated, indicators.plot_to_region(dataset), "region"
        ),
        by_island=surface_by_group_and_key(
            dataset, cultivated, indicators.plot_to_island(dataset), "island"
        ),
        by_commune=surface_by_group_and_key(
            dataset, cultivated, plot_data["COMMUNE"], "commune"
        ),
        farm_types=farm_typology_table(dataset),
        allocation=reference_allocation(dataset, config),
        reproducibility=reproducibility_table(dataset, config),
        representative_eligibility=representative_eligibility_table(dataset, config),
        indicators=indicator_frame,
        bracket_fallback_plots=fallback_plots,
        universe=universe,
    )


def _summary(reference: Reference) -> dict[str, Any]:
    repro = reference.reproducibility
    observed = float(repro["observed_ha"].sum())
    irreproducible = float(repro["irreproducible_ha"].sum())
    return {
        "universe": reference.universe,
        "observed_land_use_ha": {
            group: float(value)
            for group, value in reference.land_use["reference_ha"].items()
            if value > 0
        },
        "fallow_reclassified_to_nc_ha": float(
            -reference.land_use.loc["JA", "resolution_gap_ha"]
        ),
        "farm_types": {
            FARM_TYPE_LABELS[code]: int(count)
            for code, count in reference.farm_types["farms"].items()
        },
        "pad_floor_pct": 100.0 * irreproducible / observed if observed else float("nan"),
        "irreproducible_area_ha": irreproducible,
        "plots_without_eligible_variant": reference.bracket_fallback_plots,
        "representative_eligible_pct": {
            group: float(value)
            for group, value in reference.representative_eligibility[
                "eligible_share_pct"
            ].items()
        },
        "indicators": {
            name: {
                key: (None if pd.isna(row[key]) else float(row[key]))
                for key in ("central", "low", "high")
            }
            for name, row in reference.indicators.iterrows()
        },
    }


def _above_bracket(indicator_frame: pd.DataFrame) -> str:
    """Names the indicators whose central estimate sits above the high bound -- the visible
    symptom of a representative crop that is not itself eligible on the plots it stands for.
    Written from the numbers rather than by hand, so the sentence cannot go stale."""
    above = [
        f"{name} (+{100.0 * (row['central'] - row['high']) / row['high']:.0f} %)"
        for name, row in indicator_frame.iterrows()
        if not pd.isna(row.get("high")) and row["central"] > row["high"]
    ]
    return ", ".join(above) if above else "no indicator in this run"


def _render_markdown(reference: Reference, summary: dict[str, Any]) -> str:
    universe = reference.universe
    land_use = reference.land_use
    repro = reference.reproducibility
    representative = reference.representative_eligibility

    lines = [
        "# Reference state -- Guadeloupe 2017",
        "",
        "Observed initial state, rebuilt from the RPG history in `Data_Parc_Gwad_2017.txt`.",
        "It is the situation every run is scored against (PAD, confusion matrix, plot",
        "agreement rate). No solve: this folder depends on no run.",
        "",
        "## 1. Universe covered",
        "",
        f"- Plots: {_n(universe['plots'])}",
        f"- Farms: {_n(universe['farms'])}",
        f"- Total area: {_n(universe['total_area_ha'])} ha",
        f"- of which cultivated (PAD reference): {_n(universe['cultivated_area_ha'])} ha "
        f"on {_n(universe['cultivated_plots'])} plots",
        f"- of which not cultivated (NC): {_n(universe['uncultivated_area_ha'])} ha",
        f"- Economic year / scenario: {universe['economic_year']} / "
        f"{universe['economic_scenario']}",
        f"- Zone filter: {universe['zone_filter'] or 'none (whole territory)'}",
        "",
        "**This is not Guadeloupe's UAA.** The universe is that of the plot dataset available",
        "locally. Chopin et al. (2015) work on 5 336 farms, this dataset carries",
        f"{_n(universe['farms'])}: the two do not describe the same perimeter",
        "(see docs/04-vigilance.md). Any observed/simulated comparison must therefore stay",
        "**internal** to this universe -- which is what the PAD does, comparing both sides on",
        "the same plots.",
        "",
        "## 2. Observed land use",
        "",
        "Two readings coexist, and one must know which one is quoted:",
        "",
        "- **raw**: `cult_2017` translated directly into an RPG group;",
        "- **resolved**: the GAMS fallow-continuity rule (ENTREES.txt:49-57) forces NC when",
        "  `cult_2016` AND `cult_2017` are both fallow. This is the reading the model, the",
        "  typology and the PAD use.",
        "",
        "Going from one to the other moves "
        f"**{_n(summary['fallow_reclassified_to_nc_ha'])} ha** from fallow to not cultivated:",
        "it is the only gap between the two readings.",
        "",
        "| Group | Label | Raw (ha) | Resolved (ha) | PAD reference (ha) | Share of cultivated |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for group, row in land_use.iterrows():
        share = "-" if pd.isna(row["cultivated_share_pct"]) else f"{row['cultivated_share_pct']:.1f} %"
        lines.append(
            f"| {group} | {row['label']} | {_n(row['raw_ha'])} | {_n(row['resolved_ha'])} | "
            f"{_n(row['reference_ha'])} | {share} |"
        )
    lines += [
        f"| **TOTAL** | | {_n(land_use['raw_ha'].sum())} | {_n(land_use['resolved_ha'].sum())} | "
        f"{_n(land_use['reference_ha'].sum())} | 100 % |",
        "",
        "Breakdowns: `csv/reference_surface_by_region.csv`, `_by_island.csv`,",
        "`_by_commune.csv`. Plot-by-plot reference: `csv/reference_allocation.csv`.",
        "",
        "## 3. Observed farm typology",
        "",
        "Row-marginal of every confusion matrix, and source of each farm's risk-aversion",
        "coefficient (AVERS) in the Markowitz objective: part of the reference, not a result.",
        "",
        "| Type | Label | Farms | Share | Area (ha) | AVERS |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for code, row in reference.farm_types.iterrows():
        aversion = (
            f"{row['aversion_min']:.2f}"
            if row["aversion_min"] == row["aversion_max"]
            else f"{row['aversion_min']:.2f}-{row['aversion_max']:.2f}"
        )
        lines.append(
            f"| {code} | {row['label']} | {_n(row['farms'])} | "
            f"{row['farm_share_pct']:.1f} % | {_n(row['surface_ha'])} | {aversion} |"
        )

    lines += [
        "",
        "## 4. What the reference cannot say",
        "",
        "### 4.1 No fine crop is observed",
        "",
        "The 12 RPG groups say \"cane\", never which technical system. GAMS had the same limit",
        "(`Matrice_Parc_Cult`). Every economic or environmental indicator of the reference",
        "therefore goes through a **representative crop** per family",
        "(`config.yaml: baseline_representative_crops`) -- an assumption, not an observation.",
        "",
        "**The representative is often a crop the model itself would forbid on the plot it",
        "stands for.** `CS_NGT_NISM` is the North Grande-Terre cane system, confined to three",
        "communes, yet it values every cane hectare of the territory; `MA_ROTA` requires",
        "irrigation and values all of market gardening.",
        "",
        "| Group | Representative | Observed (ha) | Representative eligible (ha) | Share | Margin (EUR/ha) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for group, row in representative.iterrows():
        lines.append(
            f"| {group} | `{row['representative']}` | {_n(row['observed_ha'])} | "
            f"{_n(row['representative_eligible_ha'])} | {row['eligible_share_pct']:.0f} % | "
            f"{_n(row['representative_margin_eur_ha'])} |"
        )

    lines += [
        "",
        "**Consequence not to lose sight of**: this assumption does not stay in the",
        "reporting. `farm_labor_hours_max` (Eq_MO_MAX_Expl) caps each farm at the labour of its",
        "observed plan, computed through these same representatives: changing a representative",
        "changes the cap, hence the optimum. See docs/04-vigilance.md and the",
        "\"region-aware representative crops\" item of docs/status/roadmap.yaml, which this",
        "table quantifies.",
        "",
        "The reference indicators are therefore given with a bracket. The **central** estimate",
        "is that of the `config.yaml` representatives -- exactly the figures a run reports on",
        "its \"input\" side, so the two tell the same story. The **low** and **high** bounds",
        "replay each plot with the least, then the most intensive variant **among those",
        "actually eligible there**.",
        "",
        "Nothing then guarantees that the central estimate falls inside the bracket -- the",
        "representative does not always belong to the set of eligible variants. Where it leaves",
        "it from above, the reference is valued with a technical system the plot could not",
        f"carry: {_above_bracket(reference.indicators)}.",
        "",
        "| Indicator | Unit | Low | Central | High | Range |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, row in reference.indicators.iterrows():
        amplitude = (
            "-"
            if pd.isna(row.get("range_pct_of_central"))
            else f"{row['range_pct_of_central']:.0f} %"
        )
        lines.append(
            f"| {name} | {row['unit']} | {_n(row.get('low'))} | {_n(row['central'])} | "
            f"{_n(row.get('high'))} | {amplitude} |"
        )

    lines += [
        "",
        "The bracket falls back on the whole family for "
        f"{reference.bracket_fallback_plots} plot(s) with no eligible variant at all.",
        "",
        "### 4.2 Part of the observation cannot be reproduced by construction",
        "",
        "A plot is reproducible only if at least one fine variant of its observed family is",
        "eligible there. What is not is a gap no objective can avoid: a **floor under the",
        "PAD**, a property of the data and of the eligibility mask, not of the run.",
        "",
        "| Group | Observed (ha) | Reproducible (ha) | Irreproducible (ha) | Reproducible share |",
        "|---|---:|---:|---:|---:|",
    ]
    for group, row in repro.iterrows():
        lines.append(
            f"| {group} | {_n(row['observed_ha'])} | {_n(row['reproducible_ha'])} | "
            f"{_n(row['irreproducible_ha'])} | {row['reproducible_share_pct']:.0f} % |"
        )
    lines += [
        f"| **TOTAL** | {_n(repro['observed_ha'].sum())} | "
        f"{_n(repro['reproducible_ha'].sum())} | {_n(repro['irreproducible_ha'].sum())} | "
        f"{100.0 * repro['reproducible_ha'].sum() / repro['observed_ha'].sum():.0f} % |",
        "",
        f"Induced PAD floor: **{summary['pad_floor_pct']:.1f} %** "
        f"({_n(summary['irreproducible_area_ha'])} ha out of "
        f"{_n(repro['observed_ha'].sum())} ha), and up to twice that if the excess these",
        "displaced hectares create elsewhere is counted too. It is small:",
        "**the observed/simulated gap is not explained by eligibility.**",
        "",
        "Eligibility also embeds the GAMS suppressions (`Eq_*_SUPP`, and `Eq_VE_PLUIE`",
        "forbidden everywhere by the GAMS bug ported faithfully): orchards and citrus are",
        "therefore irreproducible for a porting reason, not an agronomic one.",
        "",
        "## 5. Files",
        "",
        "| File | Content |",
        "|---|---|",
        "| `csv/reference_land_use.csv` | Observed land use, raw and resolved readings |",
        "| `csv/reference_allocation.csv` | Plot-by-plot reference (the pivot table) |",
        "| `csv/reference_surface_by_region.csv` | Cultivated area by region x group |",
        "| `csv/reference_surface_by_island.csv` | Same by island |",
        "| `csv/reference_surface_by_commune.csv` | Same by commune |",
        "| `csv/reference_farm_types.csv` | Observed typology and AVERS |",
        "| `csv/reference_indicators.csv` | Indicators, central and bracket |",
        "| `csv/reference_reproducibility.csv` | PAD floor by group |",
        "| `csv/reference_representative_eligibility.csv` | Eligibility of the representatives |",
        "| `reference.json` | All of it, readable by a script |",
        "",
        "Regenerate: `python scripts/build_reference_state.py`. Deterministic (no solve).",
        "",
    ]
    return "\n".join(lines)


def write_reference(reference: Reference, output_dir: Path) -> dict[str, Any]:
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    reference.land_use.to_csv(csv_dir / "reference_land_use.csv")
    reference.allocation.to_csv(csv_dir / "reference_allocation.csv", index=False)
    reference.by_region.to_csv(csv_dir / "reference_surface_by_region.csv")
    reference.by_island.to_csv(csv_dir / "reference_surface_by_island.csv")
    reference.by_commune.to_csv(csv_dir / "reference_surface_by_commune.csv")
    reference.farm_types.to_csv(csv_dir / "reference_farm_types.csv")
    reference.indicators.to_csv(csv_dir / "reference_indicators.csv")
    reference.reproducibility.to_csv(csv_dir / "reference_reproducibility.csv")
    reference.representative_eligibility.to_csv(
        csv_dir / "reference_representative_eligibility.csv"
    )

    summary = _summary(reference)
    (output_dir / "reference.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "REFERENCE.md").write_text(
        _render_markdown(reference, summary), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=OUTPUTS_ROOT / DEFAULT_DIR_NAME,
        help=f"Destination folder (default outputs/{DEFAULT_DIR_NAME}).",
    )
    args = parser.parse_args(argv)

    config = load_config(CONFIG_PATH)
    reference = build_reference(config)
    summary = write_reference(reference, args.dir)

    universe = summary["universe"]
    print(f"\n=== 2017 reference state -> {args.dir} ===")
    print(
        f"  Universe                     : {universe['plots']} plots, "
        f"{universe['farms']} farms, "
        f"{universe['total_area_ha']:,.0f} ha"
    )
    print(
        f"  Cultivated area (PAD ref.)   : {universe['cultivated_area_ha']:,.0f} ha "
        f"({universe['cultivated_plots']} plots)"
    )
    print(
        f"  Fallow reclassified to NC    : "
        f"{summary['fallow_reclassified_to_nc_ha']:,.0f} ha"
    )
    print(
        f"  PAD floor (eligibility)      : {summary['pad_floor_pct']:.1f} % "
        f"({summary['irreproducible_area_ha']:,.0f} ha irreproducible)"
    )
    print("\n  Observed land use (ha):")
    for group, value in sorted(
        summary["observed_land_use_ha"].items(), key=lambda item: -item[1]
    ):
        print(f"    {group:<3} {GROUP_LABELS.get(group, ''):<26} {value:>9,.0f}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
