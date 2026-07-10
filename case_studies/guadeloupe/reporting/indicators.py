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


def compute_gini(values: pd.Series) -> float:
    x = np.sort(values.to_numpy(dtype=float))
    n = len(x)
    total = x.sum()
    if n == 0 or total == 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * x)) / (n * total) - (n + 1) / n)
