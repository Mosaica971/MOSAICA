from display_datasets import main


def test_main_prints_a_registry_row_for_each_dataset_entry(capsys):
    main()

    captured = capsys.readouterr()

    assert "sets" in captured.out
    assert "crops" in captured.out
    assert "parameters" in captured.out
    assert "farm_surface_ha" in captured.out
