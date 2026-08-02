"""Named run folders, and how named and numbered runs are discovered together."""

import json

from core.reporting.run_folder import create_output_folder, list_run_folders, slugify


def _run(root, name, recap=None):
    run_dir = root / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "recap.json").write_text(json.dumps(recap or {}))
    return run_dir


def test_a_named_run_gets_a_folder_named_after_itself(tmp_path):
    assert create_output_folder(tmp_path, "Calib parité GAMS") == tmp_path / "calib_parite_gams"


def test_slugify_folds_accents_and_collapses_punctuation():
    assert slugify("Calib parité GAMS") == "calib_parite_gams"
    assert slugify("P8 -- budget 80 M€") == "p8_budget_80_m"
    assert slugify("déjà__vu!!") == "deja_vu"


def test_a_name_that_slugifies_to_nothing_falls_back_to_the_counter(tmp_path):
    assert create_output_folder(tmp_path, "!!!") == tmp_path / "output_1"
    assert create_output_folder(tmp_path, None) == tmp_path / "output_2"


def test_a_repeated_name_is_suffixed_rather_than_overwritten(tmp_path):
    """Overwriting a past run in place would destroy the very thing this project
    compares against."""
    first = create_output_folder(tmp_path, "calib_retenu")
    second = create_output_folder(tmp_path, "calib_retenu")
    third = create_output_folder(tmp_path, "calib_retenu")

    assert [p.name for p in (first, second, third)] == [
        "calib_retenu", "calib_retenu_2", "calib_retenu_3"
    ]


def test_numbered_runs_keep_counting_from_the_highest_index(tmp_path):
    (tmp_path / "output_1").mkdir()
    (tmp_path / "output_3").mkdir()
    (tmp_path / "calib_retenu").mkdir()  # a named run must not shift the counter

    assert create_output_folder(tmp_path) == tmp_path / "output_4"


def test_discovery_finds_named_and_numbered_runs_alike(tmp_path):
    _run(tmp_path, "output_1")
    _run(tmp_path, "calib_retenu")

    assert {p.name for p in list_run_folders(tmp_path)} == {"output_1", "calib_retenu"}


def test_named_runs_come_first_then_numbered_by_index(tmp_path):
    """Deterministic whatever the filesystem's timestamp resolution: numbered runs are
    ordered by index, which is already their creation order."""
    _run(tmp_path, "output_1")
    _run(tmp_path, "output_3")
    _run(tmp_path, "output_2")
    _run(tmp_path, "calib_retenu")

    assert [p.name for p in list_run_folders(tmp_path)] == [
        "calib_retenu", "output_3", "output_2", "output_1"
    ]


def test_a_folder_without_a_recap_is_not_a_run(tmp_path):
    """`reference_2017/` writes reference.json, not recap.json: it is an artefact ABOUT
    the observed state, not a solve, and must never appear in a run picker."""
    _run(tmp_path, "output_1")
    (tmp_path / "reference_2017").mkdir()
    (tmp_path / "reference_2017" / "reference.json").write_text("{}")
    (tmp_path / "notes").mkdir()

    assert [p.name for p in list_run_folders(tmp_path)] == ["output_1"]


def test_a_missing_root_yields_no_runs(tmp_path):
    assert list_run_folders(tmp_path / "missing") == []
