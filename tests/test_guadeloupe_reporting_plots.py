import pandas as pd

from case_studies.guadeloupe.reporting import plots


def test_plot_production_by_crop_writes_a_non_empty_png(tmp_path):
    series = pd.Series({"CS": 400.0, "ME": 20.0})

    result = plots.plot_production_by_crop(series, tmp_path / "production.png")

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_subsidy_by_crop_writes_a_non_empty_png(tmp_path):
    series = pd.Series({"CS": 2500.0, "ME": 200.0})

    result = plots.plot_subsidy_by_crop(series, tmp_path / "subsidy.png")

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_revenue_by_crop_writes_a_non_empty_png(tmp_path):
    series = pd.Series({"CS": 17500.0, "ME": 5200.0})

    result = plots.plot_revenue_by_crop(series, tmp_path / "revenue.png")

    assert result.exists()
    assert result.stat().st_size > 0


def test_plot_surface_by_region_writes_a_non_empty_png(tmp_path):
    frame = pd.DataFrame({"CS": [8.0, 0.0], "ME": [0.0, 2.0]}, index=["R1", "R2"])

    result = plots.plot_surface_by_region(frame, tmp_path / "surface_by_region.png")

    assert result.exists()
    assert result.stat().st_size > 0
