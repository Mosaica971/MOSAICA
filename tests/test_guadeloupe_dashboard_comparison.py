import pandas as pd
import pytest

from case_studies.guadeloupe.dashboard import comparison, loaders
from case_studies.guadeloupe.reporting import report
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model
from core.model.solver import solve_model


def _facts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "crop": ["CS_BT_NISM", "CS_BT_IM", "MA_PLBIO", "MA_MOBIO"],
            "region": ["BT", "BT", "NGT", "NGT"],
            "island": [1, 1, 2, 2],
            "revenue": [100.0, 50.0, 30.0, 20.0],
            "surface": [10.0, 5.0, 3.0, 2.0],
        }
    )


def test_culture_of_takes_prefix_before_first_underscore():
    assert comparison.culture_of("CS_BT_NISM") == "CS"
    assert comparison.culture_of("MA_PLBIO") == "MA"
    assert comparison.culture_of("ME") == "ME"


def test_cane_combo_of_parses_the_three_real_combos_and_ignores_non_cane():
    assert comparison.cane_combo_of("CS_BT_NISM") == "Non irrigué · récolte semi-mécanisée"
    assert comparison.cane_combo_of("CS_NGT_NIM") == "Non irrigué · récolte mécanisée"
    assert comparison.cane_combo_of("CS_NGT_IM") == "Irrigué · récolte mécanisée"
    assert comparison.cane_combo_of("CF_NBT_NISM") == "Non irrigué · récolte semi-mécanisée"
    assert comparison.cane_combo_of("MA_PLBIO") is None
    assert comparison.cane_combo_of("ME") is None


def test_x_key_selects_the_right_dimension():
    assert comparison.x_key("CS_BT_NISM", "BT", 1, "culture") == "CS"
    assert comparison.x_key("CS_BT_NISM", "BT", 1, "subculture") == "CS_BT_NISM"
    assert comparison.x_key("CS_BT_NISM", "BT", 1, "region") == "BT"
    assert comparison.x_key("CS_BT_NISM", "BT", 1, "island") == 1


def test_stack_key_none_collapses_and_subculture_colors_cane_by_combo():
    assert comparison.stack_key("CS_BT_NISM", "BT", 1, "none") == "total"
    assert comparison.stack_key("CS_BT_IM", "BT", 1, "subculture") == "Irrigué · récolte mécanisée"
    # non-cane keeps its own code as the stratum
    assert comparison.stack_key("MA_PLBIO", "NGT", 2, "subculture") == "MA_PLBIO"
    assert comparison.stack_key("MA_PLBIO", "NGT", 2, "region") == "NGT"


def test_pivot_measure_by_culture_stacked_by_subculture_colors_cane_by_combo():
    pivot = comparison.pivot_measure(_facts(), "culture", "revenue", "subculture")

    assert set(pivot.index) == {"CS", "MA"}
    assert pivot.loc["CS", "Irrigué · récolte mécanisée"] == pytest.approx(50.0)
    assert pivot.loc["CS", "Non irrigué · récolte semi-mécanisée"] == pytest.approx(100.0)
    assert pivot.loc["CS"].sum() == pytest.approx(150.0)
    assert pivot.loc["MA", "MA_PLBIO"] == pytest.approx(30.0)
    assert pivot.loc["MA", "MA_MOBIO"] == pytest.approx(20.0)


def test_pivot_measure_by_region_unstacked_sums_surface():
    pivot = comparison.pivot_measure(_facts(), "region", "surface", "none")

    assert pivot.loc["BT", "total"] == pytest.approx(15.0)
    assert pivot.loc["NGT", "total"] == pytest.approx(5.0)


def test_shared_bar_ceiling_is_max_total_bar_height_across_series():
    a = comparison.pivot_measure(_facts(), "culture", "revenue", "subculture")  # CS bar = 150
    b = comparison.pivot_measure(_facts(), "region", "revenue", "none")         # BT bar = 150

    assert comparison.shared_bar_ceiling([a, b]) == pytest.approx(150.0)
    assert comparison.shared_bar_ceiling([]) == 0.0


def test_positive_floor_is_smallest_strictly_positive_stratum():
    pivot = comparison.pivot_measure(_facts(), "culture", "revenue", "subculture")

    # strata values are 100, 50, 30, 20 (plus fill zeros, ignored)
    assert comparison.positive_floor([pivot]) == pytest.approx(20.0)
    assert comparison.positive_floor([]) == 1.0


def test_normalize_columns_min_max_scales_and_maps_constants_to_half():
    frame = pd.DataFrame(
        {"gini": [0.2, 0.4, 0.6], "const": [5.0, 5.0, 5.0]}, index=["A", "B", "C"]
    )

    out = comparison.normalize_columns(frame)

    assert list(out["gini"]) == pytest.approx([0.0, 0.5, 1.0])
    assert list(out["const"]) == pytest.approx([0.5, 0.5, 0.5])


def test_series_label_is_human_readable():
    assert comparison.series_label("output_4", "output", 2017, "RESTIT") == (
        "output_4 · sortie (2017/RESTIT)"
    )
    assert comparison.series_label("output_4", "input", 2020, "SMART") == (
        "output_4 · entrée (2020/SMART)"
    )


def test_build_grouped_bar_figure_stacked_and_unstacked_return_figures():
    import matplotlib

    facts = _facts()
    p1 = comparison.pivot_measure(facts, "culture", "revenue", "subculture")
    p2 = comparison.pivot_measure(facts, "culture", "revenue", "subculture")
    series = [("run_1 · sortie", p1), ("run_2 · sortie", p2)]

    stacked = comparison.build_grouped_bar_figure(
        series, measure_label="Revenu (€)", x_axis_label="Culture",
        stacked=True, log=False, ceiling=150.0, floor=20.0,
    )
    assert isinstance(stacked, matplotlib.figure.Figure)

    u1 = comparison.pivot_measure(facts, "region", "surface", "none")
    unstacked = comparison.build_grouped_bar_figure(
        [("run_1 · sortie", u1)], measure_label="Surface (ha)", x_axis_label="Région",
        stacked=False, log=True, ceiling=15.0, floor=5.0,
    )
    assert isinstance(unstacked, matplotlib.figure.Figure)


def test_build_parallel_coordinates_figure_returns_figure():
    import matplotlib

    raw = pd.DataFrame(
        {"gini": [0.2, 0.4], "total_etp": [100.0, 130.0]}, index=["run_1", "run_2"]
    )
    normalized = comparison.normalize_columns(raw)

    fig = comparison.build_parallel_coordinates_figure(
        normalized, raw, {"gini": "Gini", "total_etp": "ETP total"}
    )
    assert isinstance(fig, matplotlib.figure.Figure)


_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    "labor": {"hours_per_etp": 1000.0, "cost_per_hour": 10.0},
}


def _dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0],
            "REGION": ["R1", "R2"],
            "ILE": [1, 2],
            "cult_2016": [6, 6],
            "cult_2017": [6, 6],
        },
        index=["P1", "P2"],
    )
    expl_parc = pd.DataFrame({"farm": ["E1", "E2"], "plot": ["P1", "P2"]})
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "rdt_cult": pd.Series({"CS": 80.0, "ME": 20.0}),
            "sales_per_ha_cult": pd.Series({"CS": 3000.0, "ME": 5000.0}),
            "subsidy_per_ha_cult_annualized": pd.Series({"CS": 500.0, "ME": 200.0}),
            "labor_hours_per_ha_cult": pd.Series({"CS": 400.0, "ME": 800.0}),
            "margin_per_ha_cult": pd.Series({"CS": 1500.0, "ME": 2000.0}),
        },
        scalars={},
    )


def test_facts_csv_written_by_report_round_trips_through_comparison_helpers(tmp_path):
    """End-to-end: a real run's facts_output.csv is consumable by the dashboard helpers
    (column names match, pivots/figures build)."""
    dataset = _dataset()
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0, "P2": 3.0},
        crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
        eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        config=_CONFIG,
    )
    results = solve_model(model, _CONFIG)
    run_dir = report.generate_report(dataset, _CONFIG, model, results, duration=1.0, outputs_root=tmp_path)

    facts = loaders.load_facts(run_dir, "output")
    assert facts is not None
    assert set(facts.columns) >= {"crop", "region", "island", "revenue", "etp"}

    pivot = comparison.pivot_measure(facts, "region", "revenue", "none")
    assert pivot.sum().sum() > 0
    fig = comparison.build_grouped_bar_figure(
        [("run · sortie", pivot)],
        measure_label="Revenu (€)", x_axis_label="Région",
        stacked=False, log=False,
        ceiling=comparison.shared_bar_ceiling([pivot]),
        floor=comparison.positive_floor([pivot]),
    )
    import matplotlib

    assert isinstance(fig, matplotlib.figure.Figure)
