import pandas as pd
import pytest

from core.data.dataset import Dataset
from case_studies.guadeloupe.reporting import indicators


def _dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "PART_C_INIT": [4.0, 4.0],
            "TYPE_SOL": [1, 4],
            "SURF_HA": [2.0, 3.0],
            "IRRIG_PARC": [1, 0],  # P2 non irrigable -> 0 en eau
            "RISQUE_CLD": [5, 5],  # requis par compute_environmental_totals (aucun risque)
        },
        index=["P1", "P2"],
    )
    data_sol = pd.DataFrame(
        {
            "NITISOL": [0.10, 1.0, 0.25, 3.0],
            "ANDOSOL": [0.20, 1.0, 0.25, 17.5],
            "FERRALSOL": [0.30, 1.0, 0.25, 10.0],
            "AUTRES": [0.40, 1.0, 0.25, 0.0],
            "VERTISOL": [0.50, 1.0, 0.25, 0.0],
        },
        index=["KAER", "DENS", "PROF", "KOC"],
    )
    data_cult = pd.DataFrame(
        {
            **{f"BESOIN_EAU_{m:02d}": [5.0, 5.0] for m in range(1, 13)},
            "BIOM_AER": [10.0, 10.0],
            "RAC": [0.5, 0.5],
            "CARB": [0.4, 0.4],
            "HRES": [0.5, 0.5],
            "KCROP": [1.0, 1.0],
        },
        index=["CROP_A", "CROP_B"],
    ).T
    # Un mois de pointe marqué: juillet à 50 mm pour CROP_A.
    data_cult.loc["BESOIN_EAU_07", "CROP_A"] = 50.0

    monthly = data_cult.loc[[f"BESOIN_EAU_{m:02d}" for m in range(1, 13)]]
    parameters = {
        "data_parc": data_parc,
        "data_sol": data_sol,
        "data_cult": data_cult,
        "data_otk": pd.DataFrame(
            {"DOSE": [0.0], "HUM": [0.0], "CARB": [0.0], "FHUM": [0.0]}, index=["NONE"]
        ),
        "matrice_otk_cult": pd.DataFrame(
            {"CROP_A": [0.0], "CROP_B": [0.0]}, index=["NONE"]
        ),
        "water_need_per_ha_cult": monthly.sum(axis=0),
        "monthly_water_need_per_ha_cult": monthly,
        "carbon_input_per_ha_cult": pd.Series({"CROP_A": 3.0, "CROP_B": 3.0}),
        # Requis par compute_environmental_totals, neutralisés à 0 : ce test porte sur
        # l'eau et le carbone, pas sur les indicateurs préexistants.
        "azote_per_ha_cult": pd.Series({"CROP_A": 0.0, "CROP_B": 0.0}),
        "ges_per_ha_cult": pd.Series({"CROP_A": 0.0, "CROP_B": 0.0}),
        "ift_per_ha_cult": pd.Series({"CROP_A": 0.0, "CROP_B": 0.0}),
        "cld_uptake_cult": pd.Series({"CROP_A": 4.0, "CROP_B": 4.0}),
    }
    return Dataset(sets={}, parameters=parameters, scalars={})


def _allocation() -> pd.Series:
    return pd.Series(["CROP_A", "CROP_A"], index=["P1", "P2"])


def test_non_irrigable_plot_contributes_no_water():
    by_plot = indicators.compute_water_need_m3_by_plot(_dataset(), _allocation())
    # P1: (11 mois x 5 + 50) x 2 ha x 10 m3 = 105 x 20 = 2100
    assert by_plot["P1"] == pytest.approx(2100.0)
    assert by_plot["P2"] == pytest.approx(0.0)


def test_peak_month_is_higher_than_the_average_month():
    totals = indicators.compute_environmental_totals(_dataset(), _allocation())
    assert totals["total_water_need_m3"] == pytest.approx(2100.0)
    # Juillet: 50 mm x 2 ha x 10 = 1000
    assert totals["water_need_peak_month_m3"] == pytest.approx(1000.0)
    assert totals["water_need_peak_month_m3"] > totals["total_water_need_m3"] / 12


def test_carbon_balance_and_mineralization_scale_with_surface():
    totals = indicators.compute_environmental_totals(_dataset(), _allocation())
    # Mineralisation/ha: P1 (VERTISOL, KAER .50) 100 x .50 = 50 ; P2 (NITISOL) 100 x .10 = 10.
    # Pondere par surface: 50 x 2 + 10 x 3 = 130.
    assert totals["soil_carbon_mineralization"] == pytest.approx(130.0)
    # Bilan/ha: P1 3 - 50 = -47 ; P2 3 - 10 = -7. Pondere: -47 x 2 + -7 x 3 = -115.
    assert totals["soil_carbon_balance"] == pytest.approx(-115.0)


def test_existing_environmental_keys_are_preserved():
    """Le lot ne doit rien retirer des indicateurs existants."""
    totals = indicators.compute_environmental_totals(_dataset(), _allocation())
    for key in ("total_water_need_m3", "water_need_peak_month_m3",
                "soil_carbon_balance", "soil_carbon_mineralization"):
        assert key in totals


def test_facts_table_carries_water_and_carbon_measures():
    dataset = _dataset()
    dataset.parameters["data_parc"]["REGION"] = [1, 1]
    dataset.parameters["data_parc"]["ILE"] = [1, 1]
    for name in ("rdt_cult", "sales_per_ha_cult", "subsidy_per_ha_cult_annualized",
                 "margin_per_ha_cult", "labor_hours_per_ha_cult"):
        dataset.parameters[name] = pd.Series({"CROP_A": 0.0, "CROP_B": 0.0})

    facts = indicators.compute_facts_table(
        dataset, _allocation(), hours_per_etp=1607.0, cost_per_hour=0.0
    )
    assert "water_need_m3" in facts.columns
    assert "soil_carbon_balance" in facts.columns
    # Les deux parcelles sont dans la meme (culture, region) -> une ligne agregee.
    assert facts["water_need_m3"].sum() == pytest.approx(2100.0)
    assert facts["soil_carbon_balance"].sum() == pytest.approx(-115.0)


def test_monthly_water_csv_series_has_twelve_calendar_rows():
    monthly = indicators.compute_monthly_water_need_m3(_dataset(), _allocation())
    assert len(monthly) == 12
    assert list(monthly.index)[0] == "BESOIN_EAU_01"
    assert list(monthly.index)[-1] == "BESOIN_EAU_12"
