import pandas as pd
import pytest

from core.data.zone_filter import resolve_kept_plots

PLOT_INDEX = pd.Index(["P1", "P2", "P3", "P4"])
CRITERIA = {
    "islands": pd.Series({"P1": 1, "P2": 2, "P3": 1, "P4": 3}),
    "regions": pd.Series({"P1": "R1", "P2": "R1", "P3": "R2", "P4": "R2"}),
    "farms": pd.Series({"P1": "E1", "P2": "E1", "P3": "E2", "P4": "E2"}),
    "plots": pd.Series(PLOT_INDEX, index=PLOT_INDEX),
}


def test_resolve_kept_plots_no_zone_filter_key_returns_full_index():
    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, {})

    assert list(result) == ["P1", "P2", "P3", "P4"]


def test_resolve_kept_plots_empty_lists_return_full_index():
    config = {
        "zone_filter": {
            "include": {"islands": [], "regions": [], "farms": [], "plots": []},
            "exclude": {"islands": [], "regions": [], "farms": [], "plots": []},
        }
    }

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    assert list(result) == ["P1", "P2", "P3", "P4"]


def test_resolve_kept_plots_include_combines_criteria_with_and():
    config = {"zone_filter": {"include": {"islands": [1], "regions": ["R1"]}}}

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    # P1: island 1 AND region R1 -- matches both. P3: island 1 but region R2 -- fails.
    assert list(result) == ["P1"]


def test_resolve_kept_plots_exclude_combines_criteria_with_or():
    config = {"zone_filter": {"exclude": {"islands": [1], "regions": ["R2"]}}}

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    # Removes P1,P3 (island 1) union P3,P4 (region R2) -- only P2 survives.
    assert list(result) == ["P2"]


def test_resolve_kept_plots_exclude_wins_over_include_on_conflict():
    config = {
        "zone_filter": {
            "include": {"farms": ["E1"]},
            "exclude": {"islands": [2]},
        }
    }

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    # include keeps P1,P2 (farm E1); exclude then removes P2 (island 2).
    assert list(result) == ["P1"]


def test_resolve_kept_plots_raises_when_result_is_empty():
    config = {"zone_filter": {"include": {"farms": ["E999"]}}}

    with pytest.raises(ValueError, match="zone_filter excludes every plot"):
        resolve_kept_plots(PLOT_INDEX, CRITERIA, config)


def test_resolve_kept_plots_warns_on_unmatched_value_without_changing_result():
    config = {"zone_filter": {"exclude": {"islands": [99]}}}

    with pytest.warns(UserWarning, match="99"):
        result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    assert list(result) == ["P1", "P2", "P3", "P4"]


def test_resolve_kept_plots_raises_keyerror_on_unknown_criterion_key():
    config = {"zone_filter": {"include": {"region": ["R1"]}}}

    with pytest.raises(KeyError):
        resolve_kept_plots(PLOT_INDEX, CRITERIA, config)
