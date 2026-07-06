from core.data.readers import read_flat_set, read_mapping_set, read_wide_table


def test_read_flat_set_returns_one_label_per_line(tmp_path):
    set_file = tmp_path / "SOL.set"
    set_file.write_text("NITISOL\nANDOSOL\nFERRALSOL\nAUTRES\nVERTISOL\n", encoding="utf-8")

    result = read_flat_set(set_file)

    assert result == ["NITISOL", "ANDOSOL", "FERRALSOL", "AUTRES", "VERTISOL"]


def test_read_mapping_set_returns_parent_child_pairs(tmp_path):
    set_file = tmp_path / "EXPL_PARC_2017.set"
    set_file.write_text("E1.P1\nE1.P2\nE2.P3\n", encoding="utf-8")

    result = read_mapping_set(set_file, parent_name="farm", child_name="plot")

    assert list(result.columns) == ["farm", "plot"]
    assert result.to_records(index=False).tolist() == [
        ("E1", "P1"),
        ("E1", "P2"),
        ("E2", "P3"),
    ]


def test_read_wide_table_indexes_rows_by_ident(tmp_path):
    table_file = tmp_path / "Data_Cult.txt"
    table_file.write_text(
        "ident\tAG\tAN\nSURF_PARC_MIN\t0\t0\nALTI_MIN\t-100\t-100\n",
        encoding="utf-8",
    )

    result = read_wide_table(table_file)

    assert result.index.name == "ident"
    assert list(result.index) == ["SURF_PARC_MIN", "ALTI_MIN"]
    assert list(result.columns) == ["AG", "AN"]
    assert result.loc["ALTI_MIN", "AG"] == -100
