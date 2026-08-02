"""Taking farmland out of production: the land-take (urbanisation) rule. Data-free."""

import pandas as pd
import pytest

from core.data.eligibility import forbid_where, rule_land_take


def _attributes():
    return pd.DataFrame(
        {"SURF_HA": [10.0, 10.0, 10.0, 10.0], "ALTITUDE": [5.0, 200.0, 1.0, 100.0]},
        index=["P1", "P2", "P3", "P4"],
    )


def test_land_take_removes_the_requested_share_of_surface():
    crops, condition = rule_land_take(
        _attributes(), crops="*", share=0.5, order_by="ALTITUDE"
    )
    assert crops == "*"
    # 50 % of 40 ha = 20 ha, taken from the lowest ground first: P3 (1 m) then P1 (5 m).
    assert sorted(condition[condition].index) == ["P1", "P3"]


def test_the_target_is_met_in_hectares_not_in_plot_count():
    attributes = pd.DataFrame(
        {"SURF_HA": [1.0, 1.0, 50.0], "ALTITUDE": [1.0, 2.0, 3.0]},
        index=["small_a", "small_b", "big"],
    )
    _, condition = rule_land_take(attributes, crops="*", share=0.05, order_by="ALTITUDE")
    # 5 % of 52 ha = 2.6 ha: the two small low plots fit, the big one would overshoot.
    assert sorted(condition[condition].index) == ["small_a", "small_b"]


def test_land_take_orders_by_the_named_attribute():
    _, condition = rule_land_take(
        _attributes(), crops="*", share=0.25, order_by="ALTITUDE", ascending=False
    )
    assert list(condition[condition].index) == ["P2"]  # highest ground first


def test_ordering_by_size_models_fragmentation_instead_of_urbanisation():
    attributes = pd.DataFrame(
        {"SURF_HA": [0.5, 0.5, 20.0], "ALTITUDE": [300.0, 300.0, 1.0]},
        index=["tiny_a", "tiny_b", "large"],
    )
    _, condition = rule_land_take(attributes, crops="*", share=0.05, order_by="SURF_HA")
    assert sorted(condition[condition].index) == ["tiny_a", "tiny_b"]


def test_land_take_of_nothing_removes_nothing():
    _, condition = rule_land_take(_attributes(), crops="*", share=0.0, order_by="ALTITUDE")
    assert not condition.any()


def test_selection_is_deterministic_across_calls():
    # A forcing that shifted between runs could not be compared with anything.
    first = rule_land_take(_attributes(), crops="*", share=0.5, order_by="ALTITUDE")[1]
    second = rule_land_take(_attributes(), crops="*", share=0.5, order_by="ALTITUDE")[1]
    assert first.equals(second)


def test_land_take_rejects_an_impossible_share_or_column():
    with pytest.raises(ValueError, match="share"):
        rule_land_take(_attributes(), crops="*", share=1.5, order_by="ALTITUDE")
    with pytest.raises(KeyError, match="order_by"):
        rule_land_take(_attributes(), crops="*", share=0.1, order_by="NOPE")


def test_forbid_where_star_clears_every_crop():
    mask = pd.DataFrame(True, index=["P1", "P2"], columns=["CS", "BA"])
    condition = pd.Series({"P1": True, "P2": False})
    result = forbid_where(mask, condition, "*")
    assert not result.loc["P1"].any()
    assert result.loc["P2"].all()


def test_forbid_where_with_a_list_still_targets_only_those_crops():
    mask = pd.DataFrame(True, index=["P1"], columns=["CS", "BA"])
    result = forbid_where(mask, pd.Series({"P1": True}), ["CS"])
    assert not result.loc["P1", "CS"]
    assert result.loc["P1", "BA"]
