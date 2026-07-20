import pandas as pd
import pytest

from case_studies.guadeloupe import soil_carbon


def _data_cult() -> pd.DataFrame:
    """CROP_HIGH: gros producteur de résidus. CROP_LOW: quasi rien."""
    return pd.DataFrame(
        {
            "BIOM_AER": [10.0, 1.0],
            "RAC": [0.5, 0.0],
            "CARB": [0.4, 0.4],
            "HRES": [0.5, 0.5],
            "KCROP": [1.0, 1.0],
        },
        index=["CROP_HIGH", "CROP_LOW"],
    ).T


def _data_sol() -> pd.DataFrame:
    """Colonnes dans l'ordre de la vraie table, DIFFERENT de l'ordre TYPE_SOL 1..5.
    DENS reprend les vraies valeurs de data/tables/Data_Sol.txt (elles different toutes
    d'un sol a l'autre) precisement pour qu'une indexation par position -- au lieu de
    par nom -- fasse echouer les tests qui en dependent."""
    return pd.DataFrame(
        {
            "NITISOL": [0.10, 0.9, 0.25, 3.0],
            "ANDOSOL": [0.20, 0.8, 0.25, 17.5],
            "FERRALSOL": [0.30, 1.05, 0.25, 10.0],
            "AUTRES": [0.40, 1.0, 0.25, 0.0],
            "VERTISOL": [0.50, 1.1, 0.25, 0.0],
        },
        index=["KAER", "DENS", "PROF", "KOC"],
    )


def _data_parc() -> pd.DataFrame:
    return pd.DataFrame(
        {"PART_C_INIT": [4.0, 4.0], "TYPE_SOL": [1, 4], "SURF_HA": [2.0, 3.0]},
        index=["P1", "P2"],
    )


def _data_otk() -> pd.DataFrame:
    return pd.DataFrame(
        {"DOSE": [2.0, 1.0], "HUM": [0.5, 0.0], "CARB": [0.3, 0.0], "FHUM": [1.0, 0.0]},
        index=["COMPOST", "UREE"],
    )


def _matrice() -> pd.DataFrame:
    """Lignes = opérations ITK, colonnes = cultures."""
    return pd.DataFrame(
        {"CROP_HIGH": [1.0, 1.0], "CROP_LOW": [0.0, 1.0]}, index=["COMPOST", "UREE"]
    )


def test_type_sol_mapping_matches_gams_order_not_table_order():
    """OPTIMISATION.txt:2880-2896. L'ordre des colonnes de Data_Sol est DIFFERENT --
    indexer par position donnerait des coefficients faux mais plausibles."""
    assert soil_carbon.TYPE_SOL_TO_SOIL_NAME == {
        1: "VERTISOL", 2: "FERRALSOL", 3: "ANDOSOL", 4: "NITISOL", 5: "AUTRES",
    }
    # Garde-fou explicite: la position 1 de Data_Sol est NITISOL, pas VERTISOL.
    assert list(_data_sol().columns)[0] == "NITISOL"
    assert soil_carbon.TYPE_SOL_TO_SOIL_NAME[1] == "VERTISOL"


def test_residue_carbon_uses_aerial_plus_root_biomass():
    # BIOM_AER * (1 + RAC) * CARB * HRES = 10 * 1.5 * 0.4 * 0.5 = 3.0
    residue = soil_carbon.compute_residue_carbon_per_ha_cult(_data_cult())
    assert residue["CROP_HIGH"] == pytest.approx(3.0)
    # 1 * 1.0 * 0.4 * 0.5 = 0.2
    assert residue["CROP_LOW"] == pytest.approx(0.2)


def test_amendment_carbon_sums_over_itk_operations():
    # COMPOST: DOSE 2 * HUM 0.5 * CARB 0.3 * FHUM 1 * matrice 1 = 0.3 ; UREE contribue 0.
    amendment = soil_carbon.compute_amendment_carbon_per_ha_cult(_data_otk(), _matrice())
    assert amendment["CROP_HIGH"] == pytest.approx(0.3)
    assert amendment["CROP_LOW"] == pytest.approx(0.0)


def test_initial_soil_carbon_maps_soil_type_by_name():
    # P1: TYPE_SOL 1 -> VERTISOL. 4/100 * DENS 1.1 * PROF 0.25 * 10000 = 110.
    # P2: TYPE_SOL 4 -> NITISOL.  4/100 * DENS 0.9 * PROF 0.25 * 10000 = 90.
    # DENS differs per soil here, so a regression to positional indexing (which would
    # grab NITISOL's DENS 0.9 for P1's TYPE_SOL=1 and AUTRES's DENS 1.0 for P2's
    # TYPE_SOL=4, giving 90/100 instead) is caught by this test.
    initial = soil_carbon.compute_initial_soil_carbon_per_ha_plot(_data_parc(), _data_sol())
    assert initial["P1"] == pytest.approx(110.0)
    assert initial["P2"] == pytest.approx(90.0)


def test_mineralization_uses_the_plot_soil_kaer_not_a_fixed_one():
    """Le test qui attrape un mapping par position: P1 (VERTISOL, KAER .50) et
    P2 (NITISOL, KAER .10) doivent differer d'un facteur 5."""
    allocation = pd.Series(["CROP_HIGH", "CROP_HIGH"], index=["P1", "P2"])
    initial = pd.Series([100.0, 100.0], index=["P1", "P2"])
    mineralization = soil_carbon.compute_mineralization_per_ha_plot(
        allocation, _data_parc(), _data_sol(), _data_cult(), initial
    )
    # C_ORG 100 * KAER * KCROP 1.0
    assert mineralization["P1"] == pytest.approx(50.0)
    assert mineralization["P2"] == pytest.approx(10.0)


def test_carbon_balance_drops_when_switching_to_a_low_residue_crop():
    """Entrees - sorties. Meme parcelle, meme sol: seule la culture change."""
    data_parc, data_sol, data_cult = _data_parc(), _data_sol(), _data_cult()
    data_otk, matrice = _data_otk(), _matrice()

    high = soil_carbon.compute_carbon_balance_per_ha_plot(
        pd.Series(["CROP_HIGH"], index=["P2"]),
        data_parc, data_sol, data_cult, data_otk, matrice,
    )
    low = soil_carbon.compute_carbon_balance_per_ha_plot(
        pd.Series(["CROP_LOW"], index=["P2"]),
        data_parc, data_sol, data_cult, data_otk, matrice,
    )
    # P2 = NITISOL: initial carbon 4/100 * DENS 0.9 * PROF 0.25 * 10000 = 90.
    # HIGH: entrees 3.0 + 0.3 = 3.3, sorties 90 * KAER 0.10 * KCROP 1.0 = 9 -> -5.7
    assert high["P2"] == pytest.approx(-5.7)
    # LOW: entrees 0.2 + 0.0 = 0.2, sorties 9 -> -8.8
    assert low["P2"] == pytest.approx(-8.8)
    assert low["P2"] < high["P2"]


def test_carbon_balance_on_empty_allocation_is_empty():
    balance = soil_carbon.compute_carbon_balance_per_ha_plot(
        pd.Series(dtype=object), _data_parc(), _data_sol(), _data_cult(),
        _data_otk(), _matrice(),
    )
    assert balance.empty
