import pandas as pd
import pytest

from case_studies.guadeloupe.economics import (
    apply_crop_multipliers,
    compute_gross_margin_per_ha_cult,
    compute_gross_product_per_ha_cult,
    compute_labor_hours_per_ha_cult,
    compute_subsidy_per_ha_cult,
    compute_variable_cost_per_ha_cult,
)


def test_apply_crop_multipliers_none_is_noop():
    series = pd.Series({"BA": 100.0, "CS": 50.0})
    result = apply_crop_multipliers(series, None)
    pd.testing.assert_series_equal(result, series)


def test_apply_crop_multipliers_scales_only_listed_crops():
    series = pd.Series({"BA": 100.0, "CS": 50.0, "IG": 30.0})
    result = apply_crop_multipliers(series, [{"crops": ["BA"], "factor": 1.2}])
    assert result["BA"] == pytest.approx(120.0)
    assert result["CS"] == pytest.approx(50.0)  # untouched
    assert result["IG"] == pytest.approx(30.0)


def test_apply_crop_multipliers_stacks_overlapping_rules_cumulatively():
    series = pd.Series({"BA": 100.0})
    result = apply_crop_multipliers(
        series, [{"crops": ["BA"], "factor": 1.2}, {"crops": ["BA"], "factor": 0.5}]
    )
    assert result["BA"] == pytest.approx(60.0)  # 100 * 1.2 * 0.5


def test_apply_crop_multipliers_ignores_unknown_crops():
    series = pd.Series({"BA": 100.0})
    result = apply_crop_multipliers(series, [{"crops": ["NOPE", "BA"], "factor": 0.0}])
    assert result["BA"] == pytest.approx(0.0)  # BA scaled, unknown NOPE silently skipped


def test_compute_labor_hours_per_ha_cult_weights_otk_by_mo_expl():
    # OP1 one-off (AMORTI=0): 3 applications/cycle at DOSE*MO_EXPL = 2*3 = 6 -> 18.
    # OP2 amortized (AMORTI=1): 1 application at 5*4 = 20, spread over Duree_Plant=5 -> 4.
    data_otk = pd.DataFrame(
        {"DOSE": [2, 5], "MO_EXPL": [3, 4], "AMORTI": [0, 1]},
        index=["OP1", "OP2"],
    )
    matrice_otk_cult = pd.DataFrame({"C1": [3, 1]}, index=["OP1", "OP2"])
    duree_plant_cult = pd.Series({"C1": 5})
    duree_cycle_cult = pd.Series({"C1": 24})

    result = compute_labor_hours_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
    )

    # (3*6 + (1*20)/5) / 24 * 12 = 11.0 hours/ha/year
    assert result["C1"] == pytest.approx(11.0)


def test_compute_variable_cost_per_ha_cult_combines_otk_and_harvest_transport_costs():
    # OP1 is a one-off cost (AMORTI=0): applied 3 times/cycle at 2*10=20 per application.
    # OP2 is amortized over the plantation lifetime (AMORTI=1): applied once at 5*4=20.
    data_otk = pd.DataFrame(
        {"DOSE": [2, 5], "PRIX_UNIT": [10, 4], "AMORTI": [0, 1]},
        index=["OP1", "OP2"],
    )
    matrice_otk_cult = pd.DataFrame({"C1": [3, 1]}, index=["OP1", "OP2"])
    duree_plant_cult = pd.Series({"C1": 5})
    duree_cycle_cult = pd.Series({"C1": 24})
    cout_recolte_cult = pd.Series({"C1": 2})
    cout_transp_cult = pd.Series({"C1": 1})
    rdt_cult = pd.Series({"C1": 10})

    result = compute_variable_cost_per_ha_cult(
        data_otk=data_otk,
        matrice_otk_cult=matrice_otk_cult,
        duree_plant_cult=duree_plant_cult,
        duree_cycle_cult=duree_cycle_cult,
        cout_recolte_cult=cout_recolte_cult,
        cout_transp_cult=cout_transp_cult,
        rdt_cult=rdt_cult,
    )

    # OTK cost: (3*20 + (1*20)/5) / 24 * 12 = 32.0
    # Harvest+transport: (2+1)*10 = 30.0
    assert result["C1"] == pytest.approx(62.0)


def test_compute_subsidy_per_ha_cult_sums_posei_national_pdrg_and_additional_margin():
    result = compute_subsidy_per_ha_cult(
        posei_surf_cult=pd.Series({"C1": 100.0}),
        posei_q_cult=pd.Series({"C1": 5.0}),
        aide_indus_cult=pd.Series({"C1": 3.0}),
        aide_replant_cult=pd.Series({"C1": 50.0}),
        aide_transp_cult=pd.Series({"C1": 2.0}),
        aide_garantie_prix_cult=pd.Series({"C1": 1.0}),
        mae_recolte_vert_cult=pd.Series({"C1": 10.0}),
        mae_jachere_sol_nu_cult=pd.Series({"C1": 20.0}),
        mae_compost_cult=pd.Series({"C1": 30.0}),
        mb_add_cult=pd.Series({"C1": 5.0}),
        rdt_cult=pd.Series({"C1": 10.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
        duree_plant_cult=pd.Series({"C1": 5.0}),
    )

    # POSEI: 100 + (5+3)*10/24*12 + 50/5 = 150.0
    # National: (2+1)*10/24*12 = 15.0
    # PDRG: 10+20+30 = 60.0
    # Total: 150 + 15 + 60 + 5 = 230.0
    assert result["C1"] == pytest.approx(230.0)


def test_compute_gross_product_per_ha_cult_annualizes_price_and_subsidy_income():
    result = compute_gross_product_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        subsidy_per_ha_cult=pd.Series({"C1": 230.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )

    # (10*(700+50) + 230) / 24 * 12 = 3865.0
    assert result["C1"] == pytest.approx(3865.0)


def test_compute_sales_per_ha_cult_excludes_subsidy():
    from case_studies.guadeloupe.economics import compute_sales_per_ha_cult

    result = compute_sales_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )

    # 10*(700+50) / 24 * 12 = 3750.0
    assert result["C1"] == pytest.approx(3750.0)


def test_sales_plus_annualized_subsidy_equals_gross_product():
    from case_studies.guadeloupe.economics import (
        compute_gross_product_per_ha_cult,
        compute_sales_per_ha_cult,
    )

    sales = compute_sales_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )
    subsidy_annualized = pd.Series({"C1": 230.0}) / pd.Series({"C1": 24.0}) * 12
    gross_product = compute_gross_product_per_ha_cult(
        rdt_cult=pd.Series({"C1": 10.0}),
        prix_cult=pd.Series({"C1": 700.0}),
        bagasse_cult=pd.Series({"C1": 50.0}),
        subsidy_per_ha_cult=pd.Series({"C1": 230.0}),
        duree_cycle_cult=pd.Series({"C1": 24.0}),
    )

    assert (sales + subsidy_annualized)["C1"] == pytest.approx(gross_product["C1"])


def test_compute_gross_margin_per_ha_cult_subtracts_variable_cost_from_gross_product():
    result = compute_gross_margin_per_ha_cult(
        gross_product_per_ha_cult=pd.Series({"C1": 3865.0}),
        variable_cost_per_ha_cult=pd.Series({"C1": 62.0}),
    )

    assert result["C1"] == pytest.approx(3803.0)


def test_apply_crop_multipliers_scales_yield_for_a_climate_shock():
    import pandas as pd
    from case_studies.guadeloupe.economics import apply_crop_multipliers

    rdt = pd.Series({"BA_INT": 100.0, "CS_NGT_NISM": 80.0, "ME": 40.0})
    shocked = apply_crop_multipliers(rdt, [{"crops": ["BA_INT", "CS_NGT_NISM"], "factor": 0.6}])

    assert shocked["BA_INT"] == 60.0
    assert shocked["CS_NGT_NISM"] == 48.0
    assert shocked["ME"] == 40.0  # untouched
