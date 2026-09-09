"""Unit tests for the fine-baseline labour budget (GAMS MO_Expl_init, ENTREES.txt:466-469).

Data-free: the plot x crop table is written to tmp_path in the exact layout GAMS's `put`
writer produces, including the header quirk that costs one field.
"""

import pandas as pd
import pytest

from case_studies.guadeloupe.pipeline.data_pipeline import (
    compute_farm_labor_capacity_hours_from_fine_baseline,
    read_fine_baseline_allocation,
)

# GAMS writes the last two crop names glued together with no separator, so the header line
# carries one field FEWER than each data row. Reproduced verbatim on the last column.
_TABLE = (
    '"Parcelle","CS_NGT_NIM","MA_ROTA","JA","MA_PAI_NON_I"MA_PAI_NON_****\n'
    '"P1",3.68,0.00,0.00,0.00,0.00\n'
    '"P2",0.00,2.00,0.00,0.00,0.00\n'
    '"P3",0.00,0.00,5.00,0.00,0.00\n'
    '"P4",0.00,0.00,0.00,0.00,0.00\n'
)

_RATES = pd.Series(
    {"CS_NGT_NIM": 12.7, "MA_ROTA": 1653.0, "JA": 6.0,
     "MA_PAI_NON_I": 1128.0, "MA_PAI_NON_NI": 1128.0}
)


@pytest.fixture
def table(tmp_path):
    path = tmp_path / "ASSOL_PARC_INIT.TXT"
    path.write_text(_TABLE, encoding="latin-1")
    return path


def test_reader_returns_only_planted_pairs(table):
    allocation = read_fine_baseline_allocation(table)

    assert allocation == {
        "P1": {"CS_NGT_NIM": 3.68},
        "P2": {"MA_ROTA": 2.0},
        "P3": {"JA": 5.0},
    }
    # P4 grows nothing and is dropped rather than kept as an empty entry.
    assert "P4" not in allocation


def test_reader_restores_the_two_glued_trailing_crop_names(table):
    """The header is one field short; trusting it would silently shift every column."""
    allocation = read_fine_baseline_allocation(table)

    # P1's 3.68 landed on CS_NGT_NIM, the first crop -- not on a shifted neighbour.
    assert allocation["P1"] == {"CS_NGT_NIM": 3.68}


def test_labour_is_summed_per_farm_over_the_fine_plan(table):
    expl_parc = pd.DataFrame(
        {"farm": ["E1", "E1", "E2", "E2"], "plot": ["P1", "P2", "P3", "P4"]}
    )

    hours = compute_farm_labor_capacity_hours_from_fine_baseline(
        fine_baseline=read_fine_baseline_allocation(table),
        expl_parc=expl_parc,
        labor_hours_per_ha_cult=_RATES,
    )

    # E1 = 3.68 x 12.7 + 2.0 x 1653 = 46.736 + 3306 ; E2 = 5.0 x 6 = 30.
    assert hours["E1"] == pytest.approx(3352.736)
    assert hours["E2"] == pytest.approx(30.0)


def test_plots_of_no_known_farm_are_ignored(table):
    expl_parc = pd.DataFrame({"farm": ["E1"], "plot": ["P1"]})

    hours = compute_farm_labor_capacity_hours_from_fine_baseline(
        fine_baseline=read_fine_baseline_allocation(table),
        expl_parc=expl_parc,
        labor_hours_per_ha_cult=_RATES,
    )

    assert list(hours.index) == ["E1"]
    assert hours["E1"] == pytest.approx(3.68 * 12.7)


def test_crop_absent_from_the_rate_table_contributes_nothing(table):
    expl_parc = pd.DataFrame({"farm": ["E1", "E1"], "plot": ["P1", "P2"]})

    hours = compute_farm_labor_capacity_hours_from_fine_baseline(
        fine_baseline=read_fine_baseline_allocation(table),
        expl_parc=expl_parc,
        labor_hours_per_ha_cult=_RATES.drop("MA_ROTA"),
    )

    # MA_ROTA drops out; only P1's cane remains. A missing rate must not raise.
    assert hours["E1"] == pytest.approx(3.68 * 12.7)
