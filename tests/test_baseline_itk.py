"""Unit tests for the fine ITK of the observed 2017 baseline (GAMS Matrice_Parc_Cult,
ENTREES.txt:299-457) and for the two farm references computed on it: the labour budget
MO_Expl_init (466-469) and the banana reference REF_BAN_EXPL_init (477-483).

Data-free: every plot is hand-built so that exactly one GAMS rule fires on it.
"""

import numpy as np
import pandas as pd
import pytest

from case_studies.guadeloupe.domain.baseline_itk import AGGREGATE_GROUPS, assign_baseline_itk
from case_studies.guadeloupe.pipeline.data_pipeline import (
    compute_farm_baseline_production_t,
    compute_farm_labor_capacity_hours,
)


def _plot(group, *, region=1, island=1, slope=0.0, irrigated=1, skeletal=0, surface=1.0,
          farm_surface=20.0):
    return {
        "group": group, "REGION": region, "ILE": island, "PENTE": slope,
        "IRRIG_PARC": irrigated, "SOL_COURT": skeletal, "SURF_HA": surface,
        "SURF_EXPL_PARC": farm_surface,
    }


def _assign(**plots):
    frame = pd.DataFrame.from_dict(plots, orient="index")
    return assign_baseline_itk(frame.drop(columns="group"), frame["group"])


# (plot description, expected ITK) -- one row per branch of ENTREES.txt:304-458.
_CASES = {
    # Orchards: South-East Basse-Terre (region 5) is the rain-fed system.
    "ve_sebt": (_plot("VE", region=5), "VE_PLUIE"),
    "ve_other": (_plot("VE", region=3), "VE_BTGT"),
    # Pineapple: plastic mulch from a 10 ha farm up (AN_SURF_EXPL_MIN), boundary included.
    "an_large": (_plot("AN", farm_surface=10.0), "AN_PA"),
    "an_small": (_plot("AN", farm_surface=9.99), "AN_NU"),
    # Export banana.
    "ba_int": (_plot("BA", island=1, slope=25.0, farm_surface=10.0), "BA_INT"),
    "ba_sint": (_plot("BA", island=1, slope=10.0, farm_surface=5.0), "BA_SINT"),
    "ba_per": (_plot("BA", island=1, slope=25.1, farm_surface=50.0), "BA_PER"),
    "ba_irr": (_plot("BA", island=2, slope=40.0, farm_surface=50.0), "BA_IRR"),
    # Plantain and yam: Basse-Terre systems vs the others.
    "bc_bt": (_plot("BC", island=1), "BC_BT"),
    "bc_gtmg": (_plot("BC", island=3), "BC_GTMG"),
    "ig_tut": (_plot("IG", island=1), "IG_TUT"),
    "ig_pla": (_plot("IG", island=2), "IG_PLA"),
    # Market gardening: rain-fed Basse-Terre runs the tomato-cabbage-fallow rotation.
    "ma_bt_rainfed": (_plot("MA", island=1, irrigated=0), "MA_TO_CO_JA"),
    "ma_bt_irrigated": (_plot("MA", island=1, irrigated=1), "MA_ROTA"),
    "ma_gt_rainfed": (_plot("MA", island=2, irrigated=0), "MA_ROTA"),
    # Grassland: always tethered livestock.
    "pn": (_plot("PN"), "PN_PIQ"),
    # Sugarcane.
    "cs_nbt_small": (_plot("CS", region=4, surface=0.19), "CS_BT_NISM"),
    "cs_sobt_large": (_plot("CS", region=6, surface=0.2), "CS_BT_NIM"),
    "cs_sebt": (_plot("CS", region=5, skeletal=1), "CS_SBT_NIM"),
    "cs_ngt_deep": (_plot("CS", region=3, skeletal=0), "CS_NGT_NIM"),
    "cs_ngt_skeletal": (_plot("CS", region=3, skeletal=1), "CS_NGT_NISM"),
    "cs_egt_deep": (_plot("CS", region=2, skeletal=0), "CS_EGT_NIM"),
    "cs_egt_skeletal": (_plot("CS", region=2, skeletal=1), "CS_EGT_NISM"),
    "cs_cgt_deep": (_plot("CS", region=1, skeletal=0), "CS_CGT_NIM"),
    "cs_cgt_skeletal": (_plot("CS", region=1, skeletal=1), "CS_CGT_NISM"),
    "cs_mg": (_plot("CS", region=7, skeletal=0), "CS_MG_NISM"),
    # Single crops stand for themselves.
    "ag": (_plot("AG"), "AG"),
    "ja": (_plot("JA"), "JA"),
    "me": (_plot("ME"), "ME"),
    "nc": (_plot("NC"), "NC"),
}


@pytest.mark.parametrize("name", sorted(_CASES))
def test_each_gams_rule_assigns_its_itk(name):
    plot, expected = _CASES[name]

    assert _assign(P=plot)["P"] == expected


def test_all_rules_together_on_one_table():
    """Same cases in a single call: a rule must not overwrite a plot another one assigned."""
    result = _assign(**{name: plot for name, (plot, _) in _CASES.items()})

    assert result.to_dict() == {name: expected for name, (_, expected) in _CASES.items()}


def test_no_aggregate_code_survives():
    """GAMS zeroes the aggregate column once split (Matrice_Parc_Cult(SP,"CS")=0): no plot
    may keep an aggregate code, which has no rate of its own."""
    result = _assign(**{name: plot for name, (plot, _) in _CASES.items()})

    assert not set(result.dropna()) & set(AGGREGATE_GROUPS)


def test_cane_in_a_region_no_rule_covers_gets_no_itk():
    """GAMS leaves such a plot with no ITK at all, so it contributes nothing downstream."""
    result = _assign(P=_plot("CS", region=9))

    assert np.isnan(result["P"])


def test_a_flag_that_is_neither_0_nor_1_fires_no_rule():
    """GAMS tests SOL_COURT = 0 and SOL_COURT = 1 separately: a missing value must not fall
    into the mechanised branch by default."""
    result = _assign(P=_plot("CS", region=3, skeletal=np.nan))

    assert np.isnan(result["P"])


def test_missing_column_is_named():
    frame = pd.DataFrame({"REGION": [1]}, index=["P"])

    with pytest.raises(KeyError, match="PENTE"):
        assign_baseline_itk(frame, pd.Series({"P": "CS"}))


_RATES = pd.Series({"BA_INT": 1558.0, "BA_PER": 565.0, "CS_NGT_NIM": 12.7, "JA": 6.0, "NC": 0.0})


def test_labour_budget_sums_surface_times_itk_rate_per_farm():
    fine = pd.Series({"P1": "BA_INT", "P2": "BA_PER", "P3": "CS_NGT_NIM", "P4": "NC"})
    surface = pd.Series({"P1": 2.0, "P2": 1.0, "P3": 10.0, "P4": 5.0})
    farms = pd.DataFrame({"farm": ["E1", "E1", "E2", "E3"], "plot": ["P1", "P2", "P3", "P4"]})

    hours = compute_farm_labor_capacity_hours(
        baseline_fine_crop=fine, plot_surface=surface, farm_plot_map=farms,
        crop_labor_hours_per_ha=_RATES,
    )

    assert hours["E1"] == pytest.approx(2 * 1558.0 + 565.0)
    assert hours["E2"] == pytest.approx(127.0)
    # An all-NC farm keeps a zero budget -- it is frozen, as in GAMS -- rather than vanishing.
    assert hours["E3"] == 0.0


def test_labour_budget_ignores_unassigned_plots_and_missing_rates():
    fine = pd.Series({"P1": "BA_INT", "P2": np.nan, "P3": "UNKNOWN"})
    surface = pd.Series({"P1": 1.0, "P2": 4.0, "P3": 3.0})
    farms = pd.DataFrame({"farm": ["E1", "E1", "E1"], "plot": ["P1", "P2", "P3"]})

    hours = compute_farm_labor_capacity_hours(
        baseline_fine_crop=fine, plot_surface=surface, farm_plot_map=farms,
        crop_labor_hours_per_ha=_RATES,
    )

    assert hours["E1"] == pytest.approx(1558.0)


def test_banana_reference_prices_each_plot_through_its_own_itk():
    """REF_BAN_EXPL_init sums surface x yield over BA_INT/SINT/PER/IRR: a steep plot counts at
    BA_PER's yield, not at the intensive one."""
    groups = pd.Series({"P1": "BA", "P2": "BA", "P3": "CS"})
    fine = pd.Series({"P1": "BA_INT", "P2": "BA_PER", "P3": "CS_NGT_NIM"})
    surface = pd.Series({"P1": 2.0, "P2": 1.0, "P3": 10.0})
    farms = pd.DataFrame({"farm": ["E1", "E1", "E2"], "plot": ["P1", "P2", "P3"]})
    yields = pd.Series({"BA_INT": 45.0, "BA_PER": 18.0, "CS_NGT_NIM": 70.0})

    tonnes = compute_farm_baseline_production_t(
        base_crop_group=groups, baseline_fine_crop=fine, plot_surface=surface,
        farm_plot_map=farms, crop_yield=yields,
    )

    assert tonnes["BA"]["E1"] == pytest.approx(2 * 45.0 + 18.0)
    assert tonnes["CS"]["E2"] == pytest.approx(700.0)


def test_a_farm_without_the_group_in_2017_gets_a_zero_reference_not_none():
    """GAMS indexes Eq_BA_QUOTA_Expl over every farm, so REF_BAN_EXPL_init = 0 forbids banana
    on a farm that grew none in 2017. core's farm_production_bound leaves a farm with no
    entry unconstrained, so the zero must be written out -- including for a farm whose plots
    are all NC."""
    groups = pd.Series({"P1": "BA", "P2": "CS", "P3": "NC"})
    fine = pd.Series({"P1": "BA_INT", "P2": "CS_NGT_NIM", "P3": "NC"})
    surface = pd.Series({"P1": 2.0, "P2": 10.0, "P3": 1.0})
    farms = pd.DataFrame({"farm": ["E1", "E2", "E3"], "plot": ["P1", "P2", "P3"]})
    yields = pd.Series({"BA_INT": 45.0, "CS_NGT_NIM": 70.0, "NC": 0.0})

    tonnes = compute_farm_baseline_production_t(
        base_crop_group=groups, baseline_fine_crop=fine, plot_surface=surface,
        farm_plot_map=farms, crop_yield=yields,
    )

    assert tonnes["BA"] == {"E1": pytest.approx(90.0), "E2": 0.0, "E3": 0.0}
