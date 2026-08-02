"""The reference-runs manifest. Data-free; the only filesystem use is tmp_path."""

from pathlib import Path

import yaml

from apps.dashboard import references

_MANIFEST = {
    "references": [
        {"id": "observed", "run": "output_3", "side": "input", "label": "Observé 2017"},
        {"id": "gams_parity", "run": "output_1", "side": "output", "label": "Parité GAMS",
         "note": "CALIB strict"},
        {"id": "retained", "run": "output_3", "side": "output", "label": "Calib retenu"},
    ]
}


def test_parses_declaration_order_and_defaults():
    parsed = references.parse_references(
        {"references": [{"id": "retained", "run": "output_3"}]}
    )

    assert [r.id for r in parsed] == ["retained"]
    assert parsed[0].side == "output"   # the allocation, not the baseline
    assert parsed[0].label == "retained"


def test_malformed_entries_are_skipped_not_raised():
    """A typo in one entry must not blank the whole page."""
    parsed = references.parse_references(
        {"references": [
            {"id": "ok", "run": "output_1"},
            {"id": "no_run"},
            {"run": "no_id"},
            {"id": "bad_side", "run": "output_2", "side": "middle"},
            "not a mapping",
        ]}
    )

    assert [r.id for r in parsed] == ["ok"]


def test_an_absent_manifest_is_a_normal_state():
    assert references.load_references(Path("does/not/exist.yaml")) == []


def test_loads_from_disk(tmp_path):
    path = tmp_path / "references.yaml"
    path.write_text(yaml.safe_dump(_MANIFEST), encoding="utf-8")

    loaded = references.load_references(path)

    assert [r.id for r in loaded] == ["observed", "gams_parity", "retained"]
    assert loaded[1].note == "CALIB strict"


def test_a_declared_run_missing_from_outputs_is_reported_not_dropped(tmp_path):
    (tmp_path / "output_3").mkdir()

    resolved = references.resolve(references.parse_references(_MANIFEST), tmp_path)

    assert [item.missing for item in resolved] == [False, True, False]
    assert resolved[1].reference.run == "output_1"


def test_series_labels_match_the_pages_catalog_by_folder_and_side(tmp_path):
    for name in ("output_1", "output_3"):
        (tmp_path / name).mkdir()
    catalog = {
        "run A · entrée": {"run_dir": tmp_path / "output_3", "side": "input"},
        "run A · sortie": {"run_dir": tmp_path / "output_3", "side": "output"},
        "run B · sortie": {"run_dir": tmp_path / "output_1", "side": "output"},
    }

    resolved = references.resolve(references.parse_references(_MANIFEST), tmp_path)
    labels = references.series_labels_for(resolved, catalog)

    assert labels == {
        "observed": "run A · entrée",
        "gams_parity": "run B · sortie",
        "retained": "run A · sortie",
    }


def test_a_reference_whose_side_has_no_facts_table_is_absent_from_the_labels(tmp_path):
    """A run can exist yet carry no facts table for that side -- it is then not comparable
    on this page, which is different from the folder being missing."""
    (tmp_path / "output_1").mkdir()
    (tmp_path / "output_3").mkdir()
    catalog = {"run B · sortie": {"run_dir": tmp_path / "output_1", "side": "output"}}

    resolved = references.resolve(references.parse_references(_MANIFEST), tmp_path)
    labels = references.series_labels_for(resolved, catalog)

    assert set(labels) == {"gams_parity"}
    assert not resolved[0].missing   # output_3 exists...
    assert "observed" not in labels  # ...but has no facts_input.csv


def test_the_shipped_manifest_is_valid():
    """The real file must parse and declare the three roles the dashboard looks up by id."""
    declared = references.load_references(references.DEFAULT_MANIFEST)

    assert {r.id for r in declared} == {"observed", "gams_parity", "retained"}
    assert all(r.note for r in declared), "chaque référence doit porter sa justification"
