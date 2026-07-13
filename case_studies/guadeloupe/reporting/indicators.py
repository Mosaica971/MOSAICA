from __future__ import annotations

import numpy as np
import pandas as pd
import pyomo.environ as pyo

from case_studies.guadeloupe.farm_typology import compute_base_crop_group
from core.data.dataset import Dataset

_NON_CULTIVATED_GROUP = "NC"


def decode_output_allocation(model: pyo.ConcreteModel) -> pd.Series:
    """plot -> fine crop, read from the solved model's Y variable."""
    allocated = {
        plot: crop
        for plot, crop in model.PAIRS
        if pyo.value(model.Y[plot, crop]) > 0.5
    }
    return pd.Series(allocated, name="crop")


def decode_baseline_allocation(dataset: Dataset) -> pd.Series:
    """plot -> RPG base crop group (12 groups), from the observed 2017 land use."""
    data_parc = dataset.parameters["data_parc"]
    groups = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])
    return groups[groups != _NON_CULTIVATED_GROUP].dropna()


def decode_baseline_representative_allocation(dataset: Dataset, config: dict) -> pd.Series:
    """Baseline 2017 allocation remapped from aggregate families to representative fine
    crops, so the fine-crop economics indicators (production/subsidy/revenue/ETP) apply to
    the input side. The observed baseline is only known at aggregate/RPG resolution and the
    aggregate codes carry no economics of their own; `config['baseline_representative_crops']`
    substitutes a representative fine variant per family (an assumption -- see VIGILANCE.md
    "point 4"). Real single-crop families (AG/ME/JA) map to themselves; NC is already
    dropped by decode_baseline_allocation."""
    baseline = decode_baseline_allocation(dataset)
    mapping = config.get("baseline_representative_crops") or {}
    return baseline.map(lambda family: mapping.get(family, family)).rename("crop")


def crop_family(code: str) -> str:
    """Aggregate family of a crop code -- the token before the first underscore:
    CS_BT_NISM -> CS, AN_NU -> AN, MA_ROTA -> MA, AG -> AG."""
    return str(code).split("_")[0]


def plot_to_farm(dataset: Dataset) -> pd.Series:
    expl_parc = dataset.parameters["expl_parc"]
    return expl_parc.set_index("plot")["farm"]


def plot_to_region(dataset: Dataset) -> pd.Series:
    return dataset.parameters["data_parc"]["REGION"]


def plot_to_island(dataset: Dataset) -> pd.Series:
    return dataset.parameters["data_parc"]["ILE"]


def compute_surface_by_key(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    return surface.groupby(allocation).sum()


def compute_plot_count_by_key(allocation: pd.Series) -> pd.Series:
    return allocation.value_counts()


def compute_aggregate_summary(dataset: Dataset, allocation: pd.Series) -> dict:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    farms = plot_to_farm(dataset).reindex(allocation.index)
    return {
        "total_surface_ha": float(surface.sum()),
        "active_plot_count": int(len(allocation)),
        "farm_count": int(farms.nunique()),
    }


def compute_production_tonnes_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    rdt_cult = dataset.parameters["rdt_cult"]
    return surface_by_crop * rdt_cult.reindex(surface_by_crop.index)


def compute_sales_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    sales_per_ha_cult = dataset.parameters["sales_per_ha_cult"]
    return surface_by_crop * sales_per_ha_cult.reindex(surface_by_crop.index)


def compute_subsidy_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface_by_crop = compute_surface_by_key(dataset, allocation)
    subsidy_per_ha_cult = dataset.parameters["subsidy_per_ha_cult_annualized"]
    return surface_by_crop * subsidy_per_ha_cult.reindex(surface_by_crop.index)


def compute_total_revenue_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    return compute_sales_by_crop(dataset, allocation) + compute_subsidy_by_crop(dataset, allocation)


def compute_subsidy_per_tonne_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    subsidy = compute_subsidy_by_crop(dataset, allocation)
    production = compute_production_tonnes_by_crop(dataset, allocation)
    return (subsidy / production).replace([np.inf, -np.inf], np.nan)


def compute_subsidy_per_euro_sold_by_crop(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    subsidy = compute_subsidy_by_crop(dataset, allocation)
    sales = compute_sales_by_crop(dataset, allocation)
    return (subsidy / sales).replace([np.inf, -np.inf], np.nan)


def compute_revenue_by_farm(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    sales_per_ha = dataset.parameters["sales_per_ha_cult"].reindex(allocation.values)
    subsidy_per_ha = dataset.parameters["subsidy_per_ha_cult_annualized"].reindex(allocation.values)
    revenue_per_plot = pd.Series(
        surface.to_numpy() * (sales_per_ha.to_numpy() + subsidy_per_ha.to_numpy()),
        index=allocation.index,
    )
    farms = plot_to_farm(dataset).reindex(allocation.index)
    return revenue_per_plot.groupby(farms).sum()


DEFAULT_HOURS_PER_ETP = 1607.0


def hours_per_etp_from_config(config: dict) -> float:
    """Annual working hours per full-time-equivalent (ETP), from config['labor']."""
    return float((config.get("labor") or {}).get("hours_per_etp", DEFAULT_HOURS_PER_ETP))


def compute_labor_hours_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Estimated annual labor hours per plot: surface x labor_hours_per_ha[crop].

    Only meaningful for a fine-crop allocation (the solver output): the 12-RPG-group
    baseline has no labor rate at that resolution, so ETP is an output-only indicator
    (see VIGILANCE.md, same limitation as the other per-crop indicators)."""
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    labor_per_ha = dataset.parameters["labor_hours_per_ha_cult"].reindex(allocation.to_numpy())
    return pd.Series(surface.to_numpy() * labor_per_ha.to_numpy(), index=allocation.index)


def compute_total_etp(dataset: Dataset, allocation: pd.Series, hours_per_etp: float) -> float:
    """Total full-time-equivalent jobs across all plots (labor hours / hours_per_etp)."""
    return float(compute_labor_hours_by_plot(dataset, allocation).sum() / hours_per_etp)


def compute_etp_by_key(
    dataset: Dataset, allocation: pd.Series, grouping: pd.Series, hours_per_etp: float
) -> pd.Series:
    """ETP grouped by a plot-keyed Series (farm / region / island)."""
    hours = compute_labor_hours_by_plot(dataset, allocation)
    key = grouping.reindex(allocation.index)
    return hours.groupby(key).sum() / hours_per_etp


def compute_economic_totals(
    dataset: Dataset, allocation: pd.Series, hours_per_etp: float
) -> dict:
    """Headline totals for one allocation: production (tonnes), subsidy (EUR),
    revenue (EUR), employment (ETP). Valid for both the output (fine crops) and the
    representative baseline (see decode_baseline_representative_allocation)."""
    return {
        "total_production_tonnes": float(compute_production_tonnes_by_crop(dataset, allocation).sum()),
        "total_subsidy": float(compute_subsidy_by_crop(dataset, allocation).sum()),
        "total_revenue": float(compute_total_revenue_by_crop(dataset, allocation).sum()),
        "total_etp": compute_total_etp(dataset, allocation, hours_per_etp),
    }


def compute_gini(values: pd.Series) -> float:
    x = np.sort(values.to_numpy(dtype=float))
    n = len(x)
    total = x.sum()
    if n == 0 or total == 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * x)) / (n * total) - (n + 1) / n)


def compute_shannon_diversity(
    dataset: Dataset, allocation: pd.Series, grouping: pd.Series
) -> pd.Series:
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    frame = pd.DataFrame(
        {
            "group_key": grouping.reindex(allocation.index),
            "crop": allocation,
            "surface": surface,
        }
    )

    def _shannon(rows: pd.DataFrame) -> float:
        shares = rows.groupby("crop")["surface"].sum()
        shares = shares[shares > 0] / shares.sum()
        return float(-(shares * np.log(shares)).sum())

    return frame.groupby("group_key").apply(_shannon)


def compute_surface_by_region_and_key(dataset: Dataset, allocation: pd.Series) -> pd.DataFrame:
    region = plot_to_region(dataset).reindex(allocation.index)
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    frame = pd.DataFrame({"region": region, "crop": allocation, "surface": surface})
    return frame.pivot_table(
        index="region", columns="crop", values="surface", aggfunc="sum", fill_value=0.0
    )


def compute_surface_by_island_and_key(dataset: Dataset, allocation: pd.Series) -> pd.DataFrame:
    island = plot_to_island(dataset).reindex(allocation.index)
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(allocation.index)
    frame = pd.DataFrame({"island": island, "crop": allocation, "surface": surface})
    return frame.pivot_table(
        index="island", columns="crop", values="surface", aggfunc="sum", fill_value=0.0
    )
