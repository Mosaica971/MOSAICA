from main import main


def test_main_runs_full_pipeline_and_writes_a_report(tmp_path, capsys):
    main(outputs_root=tmp_path)

    captured = capsys.readouterr()

    assert "Total revenue" in captured.out
    assert "Plots allocated" in captured.out
    output_dir = tmp_path / "output_1"
    assert (output_dir / "recap.json").exists()
    assert (output_dir / "recap.md").exists()
