import pandas as pd

from case_studies.guadeloupe.reporting import maelia_crops as mc


def _operation_data():
    columns = ["DOSE", "MO_EXPL", "AMORTI", "AZOTE", "IFT", "DT50", "KOC"]
    rows = {
        "LABOUR": [1, 0, 1, 0, 0, 0, 0],
        "PLANTATION_TO": [80, 1, 0, 0, 0, 0, 0],
        "TUTEURAGE_TO": [130, 1, 0, 0, 0, 0, 0],   # staking: no MAELIA type
        "RECOLTE_TO": [300, 1, 0, 0, 0, 0, 0],
        "15_07_21": [1500, 0, 0, 0.15, 0, 0, 0],   # an NPK grade
        "DECIS_PROTECH": [0.8, 0, 0, 0, 1, 21, 1e7],
        "EAU_IRRIG": [1, 0, 0, 0, 0, 0, 0],
    }
    return pd.DataFrame.from_dict(rows, orient="index", columns=columns)


def test_operation_types_follow_maelia_slots():
    data = _operation_data()
    assert mc.maelia_operation_type("LABOUR", data) == "tillage"
    assert mc.maelia_operation_type("PULVERISEUR", data) == "tillage"  # a disc harrow
    assert mc.maelia_operation_type("PULVE_MANU_PHYTO", data) == "crop_protection"
    assert mc.maelia_operation_type("15_07_21", data) == "fertilisation"
    assert mc.maelia_operation_type("DECIS_PROTECH", data) == "crop_protection"
    assert mc.maelia_operation_type("EAU_IRRIG", data) == "irrigation"
    assert mc.maelia_operation_type("TUTEURAGE_TO", data) is None


def _coverage():
    data = _operation_data()
    matrix = pd.DataFrame(0.0, index=data.index, columns=["TH", "JA", "MA"])
    matrix.loc[["LABOUR", "PLANTATION_TO", "TUTEURAGE_TO", "RECOLTE_TO", "15_07_21",
                "DECIS_PROTECH"], "TH"] = 1
    matrix.loc["LABOUR", "JA"] = 1
    crop_data = pd.DataFrame(0.0, columns=["TH", "JA", "MA"],
                             index=["KCROP", "LONG_RAC", "BIOM_AER", "CARB"]
                             + [f"BESOIN_EAU_{m:02d}" for m in range(1, 13)])
    crop_data.loc[["KCROP", "LONG_RAC", "BIOM_AER", "CARB"], :] = 1.0
    crops = ["TH", "JA", "MA"]
    return mc.crop_coverage(
        crop_data=crop_data,
        operation_data=data,
        crop_operation_matrix=matrix,
        crop_yield=pd.Series([18.0, 0.0, 0.0], index=crops),
        crop_price=pd.Series([1300.0, 0.0, 0.0], index=crops),
        crop_subsidy_per_ha=pd.Series([0.0, 200.0, 0.0], index=crops),
        crop_variable_cost_per_ha=pd.Series([5000.0, 10.0, 0.0], index=crops),
        crop_plantation_duration=pd.Series(1.0, index=crops),
        crop_cycle_duration=pd.Series(12.0, index=crops),
    )


def test_crop_without_operation_is_left_out():
    coverage, left_out = _coverage()
    assert left_out == ["MA"]
    assert list(coverage["crop"]) == ["TH", "JA"]


def test_untyped_labour_share_and_blocks():
    coverage, _ = _coverage()
    tomato = coverage.set_index("crop").loc["TH"]
    # 130 h of staking out of 80 + 130 + 300 h of labour.
    assert tomato["labour_untyped"] == f"{130 / 510:.0%}"
    assert tomato["operations"] == f"{mc.PARTIAL} 5/6"
    assert tomato["fertilisation"] == mc.KNOWN
    assert tomato["crop_protection"] == mc.KNOWN
    assert tomato["irrigation"] == mc.NONE
    assert tomato["phenology"] == mc.MISSING
    assert tomato["subsidies"] == "none"


def test_fallow_needs_no_species():
    coverage, _ = _coverage()
    fallow = coverage.set_index("crop").loc["JA"]
    assert fallow["yield"] == mc.NONE
    assert fallow["maelia_model"].startswith("gel")
    assert fallow["subsidies"] == mc.KNOWN
