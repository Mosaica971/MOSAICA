from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from case_studies.guadeloupe.domain.crop_labels import label_for
from case_studies.guadeloupe.domain.zones import region_label

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
        title="Production by crop",
        ylabel="Tonnes",
        output_path=output_path,
    )


def plot_subsidy_by_crop(subsidy_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        subsidy_by_crop,
        title="Subsidy by crop",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_revenue_by_crop(total_revenue_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        total_revenue_by_crop,
        title="Total revenue by crop (sales + subsidy)",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_gross_margin_by_crop(gross_margin_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        gross_margin_by_crop,
        title="Gross margin by crop",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_labor_cost_by_crop(labor_cost_by_crop: pd.Series, output_path: Path) -> Path:
    return _save_bar_chart(
        labor_cost_by_crop,
        title="Labour cost by crop",
        ylabel="Euros",
        output_path=output_path,
    )


def plot_fte_by_region(fte_by_region: pd.Series, output_path: Path) -> Path:
    """ETP (full-time-equivalent jobs) per region -- region keys, not crop codes."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    series = fte_by_region.sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar([str(key) for key in series.index], series.to_numpy(), color=_BAR_COLOR)
    _style_axes(ax, title="Estimated employment by region (FTE)", ylabel="FTE")
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path


def plot_surface_by_region(surface_by_region_and_key: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = surface_by_region_and_key.rename(columns=lambda code: label_for(str(code)))
    fig, ax = plt.subplots(figsize=_FIGSIZE)
    frame.plot.bar(stacked=True, ax=ax, colormap="tab20", width=0.8)
    _style_axes(ax, title="Area by region and crop", ylabel="Hectares")
    ax.legend(title="Culture", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path


_OBSERVED_COLOR = "#8C8C8C"
_SIMULATED_COLOR = _BAR_COLOR
_TOTAL_KEY = "TOTAL"


def plot_calibration_regional(pad_by_crop: pd.DataFrame, output_path: Path) -> Path:
    """Observed vs simulated acreage per crop, Chopin et al. (2015) Fig. 4. The TOTAL row
    is dropped: it is a different quantity from the per-crop bars and would dwarf them."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pad_by_crop.drop(index=_TOTAL_KEY, errors="ignore").sort_values(
        "observed_ha", ascending=False
    )
    positions = np.arange(len(frame))
    width = 0.4

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar(
        positions - width / 2, frame["observed_ha"].to_numpy(),
        width, label="Observed 2017", color=_OBSERVED_COLOR,
    )
    ax.bar(
        positions + width / 2, frame["simulated_ha"].to_numpy(),
        width, label="Simulated", color=_SIMULATED_COLOR,
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(_relabel_crops(frame.index))
    _style_axes(ax, title="Calibration: observed vs simulated area", ylabel="Hectares")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path


def plot_calibration_pad_heatmap(
    pad_by_crop_and_region: pd.DataFrame, output_path: Path
) -> Path:
    """PAD per (sub-region, crop), Chopin et al. (2015) Fig. 5 read as a heatmap: the point
    of the figure is which cells breach the threshold, which reads faster than seven
    side-by-side bar panels. Per-region TOTAL rows are dropped."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pad_by_crop_and_region[
        pad_by_crop_and_region.index.get_level_values("crop") != _TOTAL_KEY
    ]
    grid = frame["pad_pct"].unstack("crop")

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    # Clipped at 100: beyond a full deviation the exact value carries no extra meaning, and
    # letting it run makes every other cell washed out.
    image = ax.imshow(
        grid.to_numpy(dtype=float), cmap="RdYlGn_r", vmin=0.0, vmax=100.0, aspect="auto"
    )
    ax.set_xticks(np.arange(len(grid.columns)))
    ax.set_xticklabels(_relabel_crops(grid.columns))
    ax.set_yticks(np.arange(len(grid.index)))
    ax.set_yticklabels([region_label(key) for key in grid.index])
    ax.set_title("Calibration: PAD (%) by sub-region and crop", fontweight="bold")
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)
        tick.set_horizontalalignment("right")
    fig.colorbar(image, ax=ax, label="PAD (%)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path
