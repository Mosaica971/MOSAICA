import numpy as np
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


def test_series_label_is_run_name_plus_side():
    assert comparison.series_label("baseline", "output") == "baseline · sortie"
    assert comparison.series_label("baseline", "input") == "baseline · entrée"


def test_series_labels_leaves_unique_base_labels_untouched():
    rows = [("baseline · sortie", "output_3"), ("melon_libre · sortie", "output_11")]
    assert comparison.series_labels(rows) == [
        "baseline · sortie",
        "melon_libre · sortie",
    ]


def test_series_labels_suffixes_only_colliding_labels_with_folder():
    rows = [
        ("baseline · sortie", "output_3"),
        ("baseline · sortie", "output_9"),
        ("melon_libre · sortie", "output_11"),
    ]
    assert comparison.series_labels(rows) == [
        "baseline · sortie (output_3)",
        "baseline · sortie (output_9)",
        "melon_libre · sortie",
    ]


def test_composite_score_normalizes_benefit_and_cost_indicators():
    raw = pd.DataFrame(
        {"total_revenue": [100.0, 200.0], "total_ges": [5.0, 1.0]},
        index=["S1", "S2"],
    )
    # revenue (benefit): S1=0, S2=1 ; ges (cost, inverted): S1=0, S2=1 ; equal weights
    scores = comparison.compute_composite_scores(
        raw, {"total_revenue": 1.0, "total_ges": 1.0}
    )
    assert scores["S1"] == pytest.approx(0.0)
    assert scores["S2"] == pytest.approx(1.0)


def test_composite_score_constant_column_scores_half():
    raw = pd.DataFrame(
        {"total_revenue": [100.0, 200.0], "total_ges": [3.0, 3.0]},
        index=["S1", "S2"],
    )
    scores = comparison.compute_composite_scores(
        raw, {"total_revenue": 1.0, "total_ges": 1.0}
    )
    assert scores["S1"] == pytest.approx(0.25)  # (0 + 0.5) / 2
    assert scores["S2"] == pytest.approx(0.75)  # (1 + 0.5) / 2


def test_composite_score_ignores_zero_weight_columns():
    raw = pd.DataFrame(
        {"total_revenue": [100.0, 200.0], "total_ges": [5.0, 1.0]},
        index=["S1", "S2"],
    )
    scores = comparison.compute_composite_scores(
        raw, {"total_revenue": 1.0, "total_ges": 0.0}
    )
    assert scores["S1"] == pytest.approx(0.0)  # only revenue counts
    assert scores["S2"] == pytest.approx(1.0)


def test_composite_score_single_scenario_is_half():
    raw = pd.DataFrame({"total_revenue": [100.0], "total_ges": [5.0]}, index=["S1"])
    scores = comparison.compute_composite_scores(
        raw, {"total_revenue": 1.0, "total_ges": 1.0}
    )
    assert scores["S1"] == pytest.approx(0.5)


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


def test_format_dim_value_maps_region_and_island_codes_to_names():
    assert comparison.format_dim_value("region", 4).startswith("NBT")
    assert comparison.format_dim_value("region", "7").startswith("MG")
    assert comparison.format_dim_value("island", 1) == "Basse-Terre"
    # crop dims go through label_for; unknown region code falls back to str
    assert comparison.format_dim_value("culture", "CS") == "Canne à sucre"
    assert comparison.format_dim_value("region", "BT") == "BT"


def test_ordered_categories_zeros_and_sorting():
    pivot = comparison.pivot_measure(_facts(), "culture", "revenue", "none")  # CS=150, MA=50
    series = [("s1", pivot)]

    # zeros excluded -> only non-zero categories, biggest first
    assert comparison.ordered_categories(series, ["CS", "MA", "AG"], False, True) == ["CS", "MA"]
    # zeros included -> full universe kept, still value-ranked (AG at 0 goes last)
    assert comparison.ordered_categories(series, ["CS", "MA", "AG"], True, True) == ["CS", "MA", "AG"]
    # lexicographic when not ranking by value
    assert comparison.ordered_categories(series, ["CS", "MA", "AG"], True, False) == ["AG", "CS", "MA"]


def test_build_grouped_bar_figure_horizontal_relative_and_forced_categories():
    import matplotlib

    facts = _facts()
    pivot = comparison.pivot_measure(facts, "culture", "revenue", "subculture")
    fig = comparison.build_grouped_bar_figure(
        [("run · sortie", pivot)],
        measure_label="Revenu (€)", x_axis_label="Culture",
        stacked=True, log=False, ceiling=150.0, floor=20.0,
        categories=["CS", "MA", "AG"],  # AG absent from data -> zero bar
        horizontal=True, relative=True,
        series_colors={"run · sortie": "#123456"},
        format_x=lambda c: comparison.format_dim_value("culture", c),
        format_stack=lambda s: comparison.format_dim_value("subculture", s),
    )
    assert isinstance(fig, matplotlib.figure.Figure)


def test_build_indicator_parallel_axes_figure_returns_figure_with_native_axes():
    import matplotlib

    raw = pd.DataFrame(
        {"total_revenue": [1000.0, 1500.0], "gini_revenue_by_farm": [0.3, 0.42]},
        index=["run_1 · sortie", "run_2 · sortie"],
    )
    fig = comparison.build_indicator_parallel_axes_figure(
        raw, {"total_revenue": "Revenu (€)", "gini_revenue_by_farm": "Gini"},
        {"run_1 · sortie": "#1f77b4"},
    )
    assert isinstance(fig, matplotlib.figure.Figure)
    # one broken line per scenario on the host axes
    host = fig.axes[0]
    assert len(host.lines) >= 2
    # constant column keeps a non-degenerate axis range
    assert comparison._axis_range(np.array([5.0, 5.0]))[0] < 5.0


def test_recap_carries_crop_universe(tmp_path):
    """generate_report persists the full crop set so the dashboard axis can show zero crops."""
    dataset = _dataset()
    dataset.sets["crops"] = ["ME", "CS"]
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 2.0, "P2": 3.0},
        crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
        eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        config=_CONFIG,
    )
    results = solve_model(model, _CONFIG)
    run_dir = report.generate_report(dataset, _CONFIG, model, results, duration=1.0, outputs_root=tmp_path)

    assert loaders.load_recap(run_dir)["crop_universe"] == ["CS", "ME"]


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
            "RISQUE_CLD": [2, 5],
            "TYPE_SOL": [4, 1],
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
            "azote_per_ha_cult": pd.Series({"CS": 100.0, "ME": 50.0}),
            "ges_per_ha_cult": pd.Series({"CS": 2.0, "ME": 1.0}),
            "ift_per_ha_cult": pd.Series({"CS": 3.0, "ME": 6.0}),
            "cld_uptake_cult": pd.Series({"CS": 4, "ME": 3}),
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
