from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from case_studies.guadeloupe.crop_labels import label_for

_BAR_COLOR = "#4C72B0"
_FIGSIZE = (11, 6.5)
_DPI = 110
_THOUSANDS = FuncFormatter(lambda value, _pos: f"{value:,.0f}")


def _relabel_crops(index: pd.Index) -> list[str]:
    """Map crop codes to explicit names for axis/legend display."""
    return [label_for(str(code)) for code in index]


def _style_axes(ax, *, title: str, ylabel: str) -> None:
    ax.set_title(title, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(_THOUSANDS)
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)
        tick.set_horizontalalignment("right")


def _save_bar_chart(series: pd.Series, *, title: str, ylabel: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    series = series.sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar(_relabel_crops(series.index), series.to_numpy(), color=_BAR_COLOR)
    _style_axes(ax, title=title, ylabel=ylabel)
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
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


def plot_gross_margin_by_crop(gross_margin_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        gross_margin_by_crop,
        title="Marge brute par culture",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_labor_cost_by_crop(labor_cost_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        labor_cost_by_crop,
        title="Coût main d'œuvre par culture",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_etp_by_region(etp_by_region: pd.Series, output_path: Path) -> Path:
    """ETP (full-time-equivalent jobs) per region -- region keys, not crop codes."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    series = etp_by_region.sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar([str(key) for key in series.index], series.to_numpy(), color=_BAR_COLOR)
    _style_axes(ax, title="Emploi estimé par région (ETP)", ylabel="ETP")
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path


def plot_surface_by_region(surface_by_region_and_key: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = surface_by_region_and_key.rename(columns=lambda code: label_for(str(code)))
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    frame.plot.bar(stacked=True, ax=ax, colormap="tab20", width=0.8)
    _style_axes(ax, title="Surface par région et par culture", ylabel="Hectares")
    ax.legend(title="Culture", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path
