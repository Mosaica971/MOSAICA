"""The landing page's verdicts and reading traps. Data-free: hand-built recap dicts."""

import pandas as pd

from apps.dashboard import synthesis


def _recap(**overrides):
    base = {
        "termination_condition": "optimal",
        "objective": {"name": "maximize_risk_adjusted_gross_margin", "value": 8.1e7},
        "constraints": [],
        "environment": {"output": {}},
        "food_autonomy": {"output": {}},
        "resilience": {"output": {}},
        "calibration": {"thresholds": {}},
        "intensity": {"output": {}},
        "agroecology": {"output": {}},
    }
    base.update(overrides)
    return base


def _severities(recap):
    return [alert.severity for alert in synthesis.run_alerts(recap)]


def test_a_clean_run_raises_no_alert():
    assert synthesis.run_alerts(_recap()) == []


def test_a_solve_that_did_not_prove_optimality_is_an_error():
    """VIGILANCE records a hand-built solution beating a one-hour incumbent by 5.5 %, so a
    non-converged run is not a nuance."""
    alerts = synthesis.run_alerts(_recap(termination_condition="maxTimeLimit"))

    assert [a.severity for a in alerts] == [synthesis.ERROR]
    assert "warm start" in alerts[0].body


def test_the_pasture_floor_makes_the_territorial_pad_uncitable():
    recap = _recap(constraints=[
        {"name": "territory_production_bound", "args": {"label": "pn_prod_min"}}
    ])

    alerts = synthesis.run_alerts(recap)

    assert any("PAD territorial" in a.title for a in alerts)
    assert any("types" in a.body for a in alerts)


def test_the_plantain_ceiling_triggers_the_same_caveat():
    recap = _recap(constraints=[
        {"name": "territory_production_bound", "args": {"label": "bc_quota_max"}}
    ])

    assert any("PAD territorial" in a.title for a in synthesis.run_alerts(recap))


def test_an_indicator_pinned_by_a_bound_is_flagged_as_a_hypothesis():
    recap = _recap(constraints=[
        {"name": "territory_indicator_bound",
         "args": {"label": "budget", "indicator": "subvention"}}
    ])

    alerts = synthesis.run_alerts(recap)

    assert any("fixés par une contrainte" in a.title for a in alerts)


def test_the_pure_gross_margin_objective_is_flagged():
    recap = _recap(objective={"name": "maximize_gross_margin", "value": 1.0})

    assert any("marge brute pure" in a.title for a in synthesis.run_alerts(recap))


def test_a_run_predating_a_recap_block_says_which_page_will_be_empty():
    recap = _recap()
    del recap["intensity"]

    alerts = synthesis.run_alerts(recap)

    assert [a.severity for a in alerts] == [synthesis.INFO]
    assert "intensity" in alerts[0].body


def test_alerts_are_ordered_most_severe_first():
    recap = _recap(
        termination_condition="maxTimeLimit",
        objective={"name": "maximize_gross_margin", "value": 1.0},
    )
    del recap["resilience"]

    assert _severities(recap) == [synthesis.ERROR, synthesis.WARNING, synthesis.INFO]


def test_calibration_verdicts_carry_thresholds_and_pass_state():
    recap = _recap(calibration={
        "thresholds": {"regional_pad_max": 15.0, "farm_type_match_min": 80.0},
        "regional_pad_pct": 6.6, "regional_within_threshold": True,
        "farm_type_match_pct": 86.9, "farm_type_within_threshold": True,
        "plot_match_pct": 67.6, "area_match_pct": 77.1,
    })

    verdicts = synthesis.calibration_verdicts(recap)

    assert [v["value"] for v in verdicts] == [6.6, 86.9, 67.6, 77.1]
    assert [v["threshold"] for v in verdicts] == [15.0, 80.0, None, None]
    # The two rates the article reports without gating carry no verdict.
    assert [v["passed"] for v in verdicts] == [True, True, None, None]


def test_an_unscored_run_yields_no_verdicts():
    recap = _recap()
    del recap["calibration"]

    assert synthesis.calibration_verdicts(recap) == []


def test_headline_gaps_rank_by_hectares_not_by_percentage():
    """A 4 ha group at 100 % PAD is arithmetically dramatic and agronomically irrelevant."""
    table = pd.DataFrame({
        "crop": ["CS", "ME", "PN", "TOTAL"],
        "observed_ha": [12813.0, 189.0, 6109.0, 19111.0],
        "simulated_ha": [12782.0, 0.0, 6096.0, 18878.0],
        "abs_deviation_ha": [31.0, 189.0, 13.0, 233.0],
        "pad_pct": [0.24, 100.0, 0.21, 1.2],
    })

    top = synthesis.headline_gaps(table, top=2)

    assert list(top["crop"]) == ["ME", "CS"]
    assert "TOTAL" not in list(top["crop"])


def test_headline_gaps_tolerates_a_run_without_the_calibration_table():
    assert synthesis.headline_gaps(None) is None
    assert synthesis.headline_gaps(pd.DataFrame({"crop": ["CS"]})) is None


def test_constraint_labels_reads_only_enabled_entries_the_recap_lists():
    recap = _recap(constraints=[
        {"name": "at_most_one_crop_per_plot", "args": {}},
        {"name": "territory_production_bound", "args": {"label": "pn_prod_min"}},
    ])

    assert synthesis.constraint_labels(recap) == {"pn_prod_min"}
