from core.reporting.run_folder import create_output_folder


def test_create_output_folder_starts_at_1_for_empty_directory(tmp_path):
    result = create_output_folder(tmp_path)

    assert result == tmp_path / "output_1"
    assert result.is_dir()


def test_create_output_folder_increments_past_existing_runs(tmp_path):
    (tmp_path / "output_1").mkdir()
    (tmp_path / "output_3").mkdir()

    result = create_output_folder(tmp_path)

    assert result == tmp_path / "output_4"


def test_create_output_folder_ignores_non_matching_entries(tmp_path):
    (tmp_path / "output_1").mkdir()
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "output_backup").mkdir()

    result = create_output_folder(tmp_path)

    assert result == tmp_path / "output_2"


def test_create_output_folder_creates_missing_root(tmp_path):
    root = tmp_path / "outputs"

    result = create_output_folder(root)

    assert result == root / "output_1"
