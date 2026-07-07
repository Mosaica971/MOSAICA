from main import main


def test_main_runs_full_pipeline_and_prints_solution_summary(capsys):
    main()

    captured = capsys.readouterr()

    assert "Total revenue" in captured.out
    assert "Plots allocated" in captured.out
