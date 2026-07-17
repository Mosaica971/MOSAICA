import json

import pandas as pd

from case_studies.guadeloupe.dashboard import loaders


def _make_run(outputs_root, number, recap: dict | None = None) -> None:
    run_dir = outputs_root / f"output_{number}"
    run_dir.mkdir(parents=True)
    (run_dir / "recap.json").write_text(json.dumps(recap or {"total_plots": number}))


def test_list_output_runs_returns_most_recent_first(tmp_path):
    _make_run(tmp_path, 1)
    _make_run(tmp_path, 3)
    _make_run(tmp_path, 2)

    runs = loaders.list_output_runs(tmp_path)

    assert [run.name for run in runs] == ["output_3", "output_2", "output_1"]


def test_list_output_runs_ignores_non_output_dirs_and_missing_root(tmp_path):
    (tmp_path / "not_an_output").mkdir()
    _make_run(tmp_path, 1)

    assert [run.name for run in loaders.list_output_runs(tmp_path)] == ["output_1"]
    assert loaders.list_output_runs(tmp_path / "missing") == []


def test_load_recap_reads_json(tmp_path):
    _make_run(tmp_path, 1, recap={"total_plots": 42})

    recap = loaders.load_recap(tmp_path / "output_1")

    assert recap == {"total_plots": 42}


def test_load_csv_returns_dataframe_when_present(tmp_path):
    run_dir = tmp_path / "output_1"
    run_dir.mkdir()
    pd.DataFrame({"crop": ["AG"], "value": [1.0]}).to_csv(run_dir / "foo.csv", index=False)

    result = loaders.load_csv(run_dir, "foo.csv")

    assert result is not None
    assert list(result.columns) == ["crop", "value"]


def test_load_csv_returns_none_when_missing(tmp_path):
    run_dir = tmp_path / "output_1"
    run_dir.mkdir()

    assert loaders.load_csv(run_dir, "missing.csv") is None


def test_run_display_name_prefers_run_name(tmp_path):
    run_dir = tmp_path / "output_7"
    assert loaders.run_display_name(run_dir, {"run_name": "choc_prix"}) == "choc_prix"


def test_run_display_name_falls_back_to_folder_when_absent_or_empty(tmp_path):
    run_dir = tmp_path / "output_1"
    assert loaders.run_display_name(run_dir, {}) == "output_1"
    assert loaders.run_display_name(run_dir, {"run_name": ""}) == "output_1"
    assert loaders.run_display_name(run_dir, {"run_name": None}) == "output_1"
