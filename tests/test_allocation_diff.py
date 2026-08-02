"""What two runs did differently on the ground. Data-free: hand-built allocation frames."""

import pandas as pd
import pytest

from apps.dashboard import allocation_diff


def _allocation(pairs, surfaces=None, regions=None):
    """pairs = {plot: crop}; surfaces default to 1 ha, regions to 1."""
    plots = list(pairs)
    return pd.DataFrame({
        "plot": plots,
        "crop": [pairs[p] for p in plots],
        "farm": ["E1"] * len(plots),
        "region": [(regions or {}).get(p, 1) for p in plots],
        "island": [2] * len(plots),
        "surface_ha": [(surfaces or {}).get(p, 1.0) for p in plots],
    })


def test_align_pairs_plots_and_keeps_their_surface():
    left = _allocation({"P1": "CS_MG_NISM", "P2": "PN_PIQ"}, surfaces={"P1": 3.0, "P2": 5.0})
    right = _allocation({"P1": "PN_PIQ", "P2": "PN_PIQ"}, surfaces={"P1": 3.0, "P2": 5.0})

    aligned = allocation_diff.align(left, right)

    assert list(aligned["plot"]) == ["P1", "P2"]
    assert list(aligned["left"]) == ["CS_MG_NISM", "PN_PIQ"]
    assert list(aligned["surface_ha"]) == [3.0, 5.0]


def test_base_resolution_folds_fine_codes_onto_the_observed_groups():
    left = _allocation({"P1": "CS_MG_NISM"})
    right = _allocation({"P1": "CS_NGT_IM"})

    fine = allocation_diff.align(left, right, resolution="fine")
    base = allocation_diff.align(left, right, resolution="base")

    # Two cane systems are a real change at fine resolution, and no change at all against
    # the 12 observed groups -- which is the resolution the calibration is scored at.
    assert fine.loc[0, "left"] != fine.loc[0, "right"]
    assert base.loc[0, "left"] == base.loc[0, "right"] == "CS"


def test_a_plot_only_one_run_allocated_is_reported_not_dropped():
    """A silent inner join would erase land the model idled, which is real signal."""
    left = _allocation({"P1": "CS_MG_NISM", "P2": "PN_PIQ"}, surfaces={"P1": 3.0, "P2": 5.0})
    right = _allocation({"P1": "CS_MG_NISM"}, surfaces={"P1": 3.0})

    aligned = allocation_diff.align(left, right)

    assert len(aligned) == 2
    idled = aligned[aligned["plot"] == "P2"].iloc[0]
    assert idled["right"] == allocation_diff.UNALLOCATED
    assert idled["surface_ha"] == 5.0  # surface recovered from the side that has it


def test_a_plot_appearing_only_on_the_right_keeps_its_surface_too():
    left = _allocation({"P1": "CS_MG_NISM"})
    right = _allocation({"P1": "CS_MG_NISM", "P9": "MA_ROTA"}, surfaces={"P9": 7.0})

    aligned = allocation_diff.align(left, right)
    entered = aligned[aligned["plot"] == "P9"].iloc[0]

    assert entered["left"] == allocation_diff.UNALLOCATED
    assert entered["surface_ha"] == 7.0
    assert entered["region"] == 1


def test_transition_matrix_puts_what_did_not_move_on_the_diagonal():
    left = _allocation({"P1": "PN_PIQ", "P2": "PN_PIQ", "P3": "CS_MG_NISM"},
                       surfaces={"P1": 2.0, "P2": 4.0, "P3": 1.0})
    right = _allocation({"P1": "CS_MG_NISM", "P2": "PN_PIQ", "P3": "CS_MG_NISM"},
                        surfaces={"P1": 2.0, "P2": 4.0, "P3": 1.0})

    matrix = allocation_diff.transition_matrix(allocation_diff.align(left, right))

    assert matrix.loc["PN_PIQ", "CS_MG_NISM"] == 2.0   # the 2 ha that leaked
    assert matrix.loc["PN_PIQ", "PN_PIQ"] == 4.0       # the 4 ha that held
    assert matrix.loc["CS_MG_NISM", "CS_MG_NISM"] == 1.0


def test_net_change_is_signed_and_ranked_by_magnitude():
    left = _allocation({"P1": "PN_PIQ", "P2": "PN_PIQ", "P3": "MA_ROTA"},
                       surfaces={"P1": 10.0, "P2": 10.0, "P3": 1.0})
    right = _allocation({"P1": "CS_MG_NISM", "P2": "CS_MG_NISM", "P3": "MA_ROTA"},
                        surfaces={"P1": 10.0, "P2": 10.0, "P3": 1.0})

    change = allocation_diff.net_change(allocation_diff.align(left, right))
    by_crop = change.set_index("crop")["delta_ha"]

    assert by_crop["PN_PIQ"] == -20.0
    assert by_crop["CS_MG_NISM"] == 20.0
    assert by_crop["MA_ROTA"] == 0.0
    assert change.iloc[0]["crop"] in {"PN_PIQ", "CS_MG_NISM"}  # biggest mover first


def test_top_moves_excludes_plots_that_did_not_change():
    left = _allocation({"P1": "BA_INT", "P2": "BA_INT", "P3": "CS_MG_NISM"})
    right = _allocation({"P1": "BC_BT", "P2": "BC_BT", "P3": "CS_MG_NISM"})

    moves = allocation_diff.top_moves(allocation_diff.align(left, right))

    assert len(moves) == 1
    assert (moves.iloc[0]["left"], moves.iloc[0]["right"]) == ("BA_INT", "BC_BT")
    assert moves.iloc[0]["surface_ha"] == 2.0
    assert moves.iloc[0]["plots"] == 2


def test_region_filter_localises_the_diff():
    left = _allocation({"P1": "BA_INT", "P2": "BA_INT"}, regions={"P1": 5, "P2": 3})
    right = _allocation({"P1": "BC_BT", "P2": "BC_BT"}, regions={"P1": 5, "P2": 3})

    aligned = allocation_diff.align(left, right, region=5)

    assert list(aligned["plot"]) == ["P1"]


def test_stability_reports_agreement_in_hectares_and_in_plots():
    left = _allocation({"P1": "PN_PIQ", "P2": "CS_MG_NISM"}, surfaces={"P1": 9.0, "P2": 1.0})
    right = _allocation({"P1": "CS_MG_NISM", "P2": "CS_MG_NISM"},
                        surfaces={"P1": 9.0, "P2": 1.0})

    stats = allocation_diff.stability(allocation_diff.align(left, right))

    # Half the plots agree but only a tenth of the area: the two readings differ, which is
    # exactly why both are reported.
    assert stats["share_plots"] == 0.5
    assert stats["share_ha"] == pytest.approx(0.1)


def test_identical_runs_are_fully_stable_and_have_no_moves():
    same = _allocation({"P1": "CS_MG_NISM", "P2": "PN_PIQ"})
    aligned = allocation_diff.align(same, same)

    assert allocation_diff.stability(aligned)["share_ha"] == 1.0
    assert allocation_diff.top_moves(aligned).empty


def test_an_unknown_resolution_is_rejected():
    with pytest.raises(ValueError, match="unknown resolution"):
        allocation_diff.align(_allocation({"P1": "CS"}), _allocation({"P1": "CS"}),
                              resolution="medium")
