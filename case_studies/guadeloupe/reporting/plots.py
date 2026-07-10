from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _save_bar_chart(series: pd.Series, *, title: str, ylabel: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    series.sort_values(ascending=False).plot.bar(ax=ax)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path


def plot_production_by_crop(production_tonnes_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        production_tonnes_by_crop,
        title="Production par culture",
        ylabel="Tonnes",
        output_path=output_path,
    )


def plot_subsidy_by_crop(subsidy_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        subsidy_by_crop,
        title="Subvention par culture",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_revenue_by_crop(total_revenue_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        total_revenue_by_crop,
        title="Revenu total par culture (vente + subvention)",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_surface_by_region(surface_by_region_and_key: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    surface_by_region_and_key.plot.bar(stacked=True, ax=ax)
    ax.set_title("Surface par region et par culture")
    ax.set_ylabel("Hectares")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
