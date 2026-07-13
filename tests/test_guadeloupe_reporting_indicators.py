import pandas as pd
import pytest

from case_studies.guadeloupe.reporting import indicators
from core.data.dataset import Dataset
from core.model.builder import build_crop_allocation_model

_MINIMAL_CONFIG = {
    "solver": {"name": "appsi_highs", "args": {}},
    "constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}],
    "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
}


def _small_dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0, 1.0, 4.0, 3.0, 1.0],
            "REGION": ["R1", "R1", "R2", "R2", "R1", "R2"],
            "ILE": [1, 1, 2, 2, 1, 2],
            "cult_2016": [6, 6, 13, 14, 6, 13],
            "cult_2017": [6, 6, 13, 14, 6, 13],
        },
        index=["P1", "P2", "P3", "P4", "P5", "P6"],
    )
    expl_parc = pd.DataFrame(
        {
            "farm": ["E1", "E1", "E2", "E2", "E3", "E3"],
            "plot": ["P1", "P2", "P3", "P4", "P5", "P6"],
        }
    )
    rdt_cult = pd.Series({"CS": 80.0, "ME": 20.0})
    sales_per_ha_cult = pd.Series({"CS": 3000.0, "ME": 5000.0})
    subsidy_per_ha_cult_annualized = pd.Series({"CS": 500.0, "ME": 200.0})
    labor_hours_per_ha_cult = pd.Series({"CS": 400.0, "ME": 800.0})
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "rdt_cult": rdt_cult,
            "sales_per_ha_cult": sales_per_ha_cult,
            "subsidy_per_ha_cult_annualized": subsidy_per_ha_cult_annualized,
            "labor_hours_per_ha_cult": labor_hours_per_ha_cult,
        },
        scalars={},
    )


def test_decode_baseline_allocation_maps_rpg_codes_to_groups_and_drops_non_cultivated():
    dataset = _small_dataset()

    allocation = indicators.decode_baseline_allocation(dataset)

    assert allocation.to_dict() == {
        "P1": "CS", "P2": "CS", "P3": "ME", "P5": "CS", "P6": "ME",
    }


def test_decode_output_allocation_reads_selected_pairs_from_solved_model():
    model = build_crop_allocation_model(
        plot_surface_ha={"P1": 1.0, "P2": 1.0},
        crop_margin_per_ha={"C1": 10.0, "C2": 20.0},
        eligible_pairs=[("P1", "C1"), ("P1", "C2"), ("P2", "C1")],
        config=_MINIMAL_CONFIG,
    )
    model.Y["P1", "C1"].set_value(0)
    model.Y["P1", "C2"].set_value(1)
    model.Y["P2", "C1"].set_value(1)

    allocation = indicators.decode_output_allocation(model)

    assert allocation.to_dict() == {"P1": "C2", "P2": "C1"}


def test_compute_surface_by_key_sums_surface_per_crop():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_surface_by_key(dataset, allocation)

    assert result["CS"] == pytest.approx(5.0)
    assert result["ME"] == pytest.approx(1.0)


def test_compute_plot_count_by_key_counts_plots_per_crop():
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "CS", "P6": "ME"})

    result = indicators.compute_plot_count_by_key(allocation)

    assert result["CS"] == 3
    assert result["ME"] == 2


def test_compute_aggregate_summary_totals_surface_plots_and_farms():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)

    summary = indicators.compute_aggregate_summary(dataset, allocation)

    assert summary == {"total_surface_ha": 10.0, "active_plot_count": 5, "farm_count": 3}


def test_compute_production_tonnes_by_crop_multiplies_surface_by_yield():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_production_tonnes_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(400.0)
    assert result["ME"] == pytest.approx(20.0)


def test_compute_sales_by_crop_multiplies_surface_by_sales_rate():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_sales_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(15000.0)
    assert result["ME"] == pytest.approx(5000.0)


def test_compute_subsidy_by_crop_multiplies_surface_by_subsidy_rate():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_subsidy_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(2500.0)
    assert result["ME"] == pytest.approx(200.0)


def test_compute_total_revenue_by_crop_sums_sales_and_subsidy():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_total_revenue_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(17500.0)
    assert result["ME"] == pytest.approx(5200.0)


def test_compute_subsidy_per_tonne_by_crop_divides_subsidy_by_production():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_subsidy_per_tonne_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(6.25)
    assert result["ME"] == pytest.approx(10.0)


def test_compute_subsidy_per_euro_sold_by_crop_divides_subsidy_by_sales():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_subsidy_per_euro_sold_by_crop(dataset, allocation)

    assert result["CS"] == pytest.approx(2500.0 / 15000.0)
    assert result["ME"] == pytest.approx(200.0 / 5000.0)


def test_compute_revenue_by_farm_sums_sales_plus_subsidy_weighted_by_surface():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_revenue_by_farm(dataset, allocation)

    assert result["E1"] == pytest.approx(17500.0)
    assert result["E2"] == pytest.approx(5200.0)


def test_decode_baseline_representative_allocation_substitutes_aggregates():
    dataset = _small_dataset()
    config = {"baseline_representative_crops": {"CS": "CS_BT_NISM"}}

    result = indicators.decode_baseline_representative_allocation(dataset, config)

    # baseline groups P1/P2/P5=CS, P3/P6=ME, P4=NC(dropped); CS -> rep, ME kept (unmapped)
    assert result.to_dict() == {
        "P1": "CS_BT_NISM", "P2": "CS_BT_NISM", "P3": "ME", "P5": "CS_BT_NISM", "P6": "ME",
    }


def test_decode_baseline_representative_allocation_keeps_unmapped_families():
    result = indicators.decode_baseline_representative_allocation(_small_dataset(), {})

    assert set(result.unique()) == {"CS", "ME"}  # no mapping -> aggregates unchanged


def test_crop_family_is_token_before_first_underscore():
    assert indicators.crop_family("CS_BT_NISM") == "CS"
    assert indicators.crop_family("AN_NU") == "AN"
    assert indicators.crop_family("AG") == "AG"


def test_compute_economic_totals_sums_production_subsidy_revenue_and_etp():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    totals = indicators.compute_economic_totals(dataset, allocation, hours_per_etp=1000.0)

    assert totals["total_production_tonnes"] == pytest.approx(420.0)   # 5ha*80 + 1ha*20
    assert totals["total_subsidy"] == pytest.approx(2700.0)            # 5*500 + 1*200
    assert totals["total_revenue"] == pytest.approx(22700.0)           # sales 20000 + subsidy 2700
    assert totals["total_etp"] == pytest.approx(2.8)                   # (800+1200+800)/1000


def test_compute_labor_hours_by_plot_multiplies_surface_by_labor_rate():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_labor_hours_by_plot(dataset, allocation)

    assert result["P1"] == pytest.approx(800.0)   # 2.0 ha * 400 h/ha
    assert result["P2"] == pytest.approx(1200.0)  # 3.0 ha * 400 h/ha
    assert result["P3"] == pytest.approx(800.0)   # 1.0 ha * 800 h/ha


def test_compute_total_etp_divides_total_hours_by_hours_per_etp():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})

    result = indicators.compute_total_etp(dataset, allocation, hours_per_etp=1000.0)

    assert result == pytest.approx(2.8)  # (800 + 1200 + 800) / 1000


def test_compute_etp_by_key_groups_hours_then_divides():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME"})
    farms = indicators.plot_to_farm(dataset)

    result = indicators.compute_etp_by_key(dataset, allocation, farms, hours_per_etp=1000.0)

    assert result["E1"] == pytest.approx(2.0)  # (800 + 1200) / 1000
    assert result["E2"] == pytest.approx(0.8)  # 800 / 1000


def test_hours_per_etp_from_config_reads_value_or_defaults():
    assert indicators.hours_per_etp_from_config({"labor": {"hours_per_etp": 1800}}) == 1800.0
    assert indicators.hours_per_etp_from_config({}) == indicators.DEFAULT_HOURS_PER_ETP


def test_compute_gini_matches_hand_computed_value_for_two_farms():
    values = pd.Series({"E1": 17500.0, "E2": 5200.0})

    result = indicators.compute_gini(values)

    assert result == pytest.approx(0.270925, abs=1e-4)


def test_compute_gini_is_zero_for_equal_distribution():
    values = pd.Series({"E1": 50.0, "E2": 50.0})

    assert indicators.compute_gini(values) == pytest.approx(0.0)


def test_compute_gini_is_zero_for_empty_series():
    assert indicators.compute_gini(pd.Series(dtype=float)) == 0.0


def test_compute_shannon_diversity_is_zero_for_single_crop_farms_and_positive_for_mixed():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)
    farms = indicators.plot_to_farm(dataset)

    result = indicators.compute_shannon_diversity(dataset, allocation, farms)

    assert result["E1"] == pytest.approx(0.0)
    assert result["E2"] == pytest.approx(0.0)
    assert result["E3"] == pytest.approx(0.5623, abs=1e-3)


def test_compute_surface_by_region_and_key_pivots_surface_by_region_and_crop():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)

    result = indicators.compute_surface_by_region_and_key(dataset, allocation)

    assert result.loc["R1", "CS"] == pytest.approx(8.0)
    assert result.loc["R2", "ME"] == pytest.approx(2.0)
    assert result.loc["R1", "ME"] == pytest.approx(0.0)


def test_compute_surface_by_island_and_key_pivots_surface_by_island_and_crop():
    dataset = _small_dataset()
    allocation = indicators.decode_baseline_allocation(dataset)

    result = indicators.compute_surface_by_island_and_key(dataset, allocation)

    assert result.loc[1, "CS"] == pytest.approx(8.0)
    assert result.loc[2, "ME"] == pytest.approx(2.0)
