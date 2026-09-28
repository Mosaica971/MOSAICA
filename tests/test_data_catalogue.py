"""The data catalogue, its validator and its Excel workbook -- on a tiny hand-built catalogue.

Data-free like the rest of the suite: the repository catalogue is only checked for coherence
(every file the pipeline reads is catalogued, every field is well formed), never against data/.
"""

import re
from pathlib import Path

import pandas as pd
import pytest

from core.data.catalogue import (
    Catalogue,
    diff_tables,
    load_catalogue,
    read_table,
    table_text,
    validate,
    write_table,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

RAW = {
    "version": 1,
    "levels": {0: {"name": "public"}, 2: {"name": "restricted"}},
    "referentials": {
        "crops": {"set": "sets/CROPS.set"},
        "plots": {"index_of": "plots"},
        "periods": {"values": ["init", "2017"]},
    },
    "tables": {
        "crops": {"file": "sets/CROPS.set", "layout": "set", "level": 0},
        "farm_plot_map": {
            "file": "sets/FARM_PLOT.set", "layout": "mapping", "level": 2,
            "parent": {"name": "farm"},
            "child": {"name": "plot", "referential": "plots", "unique": True},
        },
        "plots": {
            "file": "tables/Plots.txt", "layout": "records", "level": 2,
            "rows": {"name": "plot", "defines": "plots"},
            "fields": {
                "AREA": {"type": "float", "min": 0.01, "max": 100},
                "PERIM": {"type": "float", "min": 0},
                "SHAPE": {"type": "float", "computed": {"expr": "PERIM / AREA", "round": 0,
                                                         "tolerance": 0.5}},
                "ISLAND": {"type": "code", "values": {1: "a", 2: "b"}},
                "IRRIG": {"type": "binary"},
                "N_PLOTS": {"type": "int", "derived": {"siblings_in": "farm_plot_map"}},
            },
        },
        "crop_data": {
            "file": "tables/Crops.txt", "layout": "matrix", "level": 1,
            "rows": {"name": "variable"},
            "columns": {"name": "crop", "referential": "crops"},
            "row_fields": {
                "ALT_MAX": {"type": "float", "min": 0},
                "SENSITIVITY": {"type": "code", "values": {1: "low", 2: "high"}},
            },
        },
        "yield": {
            "file": "tables/Yield_{scenario}.txt", "layout": "matrix", "level": 1,
            "variants": {"scenario": ["A", "B"]},
            "rows": {"name": "crop", "referential": "crops"},
            "columns": {"name": "period", "referential": "periods"},
            "value": {"type": "float", "min": 0},
        },
    },
}


def good_frames() -> dict[str, pd.DataFrame]:
    plots = pd.DataFrame(
        {"AREA": [1.0, 2.0, 0.5], "PERIM": [400.0, 500.0, 300.0], "SHAPE": [400.0, 250.0, 600.0],
         "ISLAND": [1, 2, 1], "IRRIG": [0, 1, 1], "N_PLOTS": [2, 2, 1]},
        index=pd.Index(["P1", "P2", "P3"], name="plot"),
    )
    crop_data = pd.DataFrame({"AG": [500.0, 1], "BC": [5000.0, 2]}, index=["ALT_MAX", "SENSITIVITY"])
    yield_ = pd.DataFrame({"init": [20.0, 70.0], "2017": [21.0, 72.5]}, index=["AG", "BC"])
    return {
        "crops": pd.DataFrame({"id": ["AG", "BC"]}),
        "farm_plot_map": pd.DataFrame({"farm": ["E1", "E1", "E2"], "plot": ["P1", "P2", "P3"]}),
        "plots": plots,
        "crop_data": crop_data,
        "yield_A": yield_,
        "yield_B": yield_.copy(),
    }


@pytest.fixture
def catalogue() -> Catalogue:
    return Catalogue(RAW)


def errors(issues):
    return [i for i in issues if i.severity == "error"]


def test_variants_expand_into_one_sheet_each(catalogue):
    assert catalogue.tables["yield_A"].file == "tables/Yield_A.txt"
    assert catalogue.tables["yield_B"].file == "tables/Yield_B.txt"
    assert catalogue.table("yield").sheet == "yield_A"


def test_clean_tables_validate_without_errors(catalogue):
    issues, clean = validate(catalogue, good_frames())
    assert errors(issues) == []
    assert clean["plots"].loc["P2", "SHAPE"] == 250.0


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda f: f["plots"].__setitem__("ISLAND", [1, 3, 1]), "not an allowed code"),
        (lambda f: f["plots"].__setitem__("AREA", [1.0, 200.0, 0.5]), "> maximum 100"),
        (lambda f: f["plots"].__setitem__("IRRIG", [0, 1, 0.5]), "not a whole number"),
        (lambda f: f["plots"].__setitem__("AREA", [1.0, "two", 0.5]), "is not a number"),
        (lambda f: f["plots"].__setitem__("AREA", [1.0, None, 0.5]), "empty cell"),
        (lambda f: f["plots"].__setitem__("SHAPE", [400.0, 260.0, 600.0]), "differs from PERIM / AREA"),
        (lambda f: f["plots"].__setitem__("N_PLOTS", [2, 2, 5]), "farm_plot_map gives 1"),
        (lambda f: f.__setitem__("plots", f["plots"].drop(columns="IRRIG")), "'IRRIG' is missing"),
        (lambda f: f.__setitem__("farm_plot_map", pd.DataFrame(
            {"farm": ["E1", "E2", "E2"], "plot": ["P1", "P1", "P9"]})), "has several farms"),
        (lambda f: f.__setitem__("farm_plot_map", pd.DataFrame(
            {"farm": ["E1", "E1", "E2"], "plot": ["P1", "P2", "P9"]})), "'P9' is not an id of plots"),
        (lambda f: f.__setitem__("crops", pd.DataFrame({"id": ["AG", "BC", "AG"]})), "duplicate id"),
        (lambda f: f.__setitem__("yield_A", f["yield_A"].rename(index={"BC": "ZZ"})),
         "row 'ZZ' is not an id of crops"),
        (lambda f: f.__setitem__("yield_A", f["yield_A"].drop(columns="2017")),
         "column '2017' of periods is missing"),
        (lambda f: f["crop_data"].__setitem__("BC", [5000.0, 7]), "not an allowed code"),
        (lambda f: f.__setitem__("crop_data", f["crop_data"].drop(index="ALT_MAX")),
         "row 'ALT_MAX' is missing"),
    ],
)
def test_each_rule_is_enforced(catalogue, mutate, expected):
    frames = good_frames()
    mutate(frames)
    issues, _ = validate(catalogue, frames)
    messages = [str(i) for i in errors(issues)]
    assert any(expected in m for m in messages), messages


def test_a_computed_value_is_kept_when_within_tolerance(catalogue):
    # The source rounds the unrounded quotient; recomputing from rounded inputs may land one
    # unit away, and rewriting it could move a plot across a threshold.
    frames = good_frames()
    frames["plots"].loc["P1", "SHAPE"] = 400.4
    issues, clean = validate(catalogue, frames)
    assert errors(issues) == []
    assert clean["plots"].loc["P1", "SHAPE"] == 400.4


def test_padded_keys_are_stripped_with_a_warning(catalogue):
    frames = good_frames()
    frames["yield_A"].index = ["AG  ", "BC"]
    issues, clean = validate(catalogue, frames)
    assert errors(issues) == []
    assert any("surrounding spaces" in i.message for i in issues)
    assert list(clean["yield_A"].index) == ["AG", "BC"]


def test_missing_referential_is_a_warning_not_an_error(catalogue):
    frames = good_frames()
    del frames["crops"]
    issues, _ = validate(catalogue, frames)
    assert errors(issues) == []
    assert any("referential crops unavailable" in i.message for i in issues)


def test_text_export_round_trips(catalogue, tmp_path):
    frames = good_frames()
    _, clean = validate(catalogue, frames)
    for sheet, frame in clean.items():
        write_table(catalogue.tables[sheet], frame, tmp_path)
    assert (tmp_path / "sets" / "FARM_PLOT.set").read_text() == "E1.P1\nE1.P2\nE2.P3\n"
    header = (tmp_path / "tables" / "Plots.txt").read_text().splitlines()[0]
    assert header.split("\t")[:3] == ["ident", "AREA", "PERIM"]
    for sheet, frame in clean.items():
        spec = catalogue.tables[sheet]
        diff = diff_tables(spec, frame, read_table(spec, tmp_path))
        assert diff["changed_cells"] == 0 and diff["added"] == 0 and diff["removed"] == 0, sheet


def test_integers_are_written_without_a_decimal_point(catalogue):
    text = table_text(catalogue.tables["yield_A"], good_frames()["yield_A"])
    assert text.splitlines()[1] == "AG\t20\t21"


def test_workbook_round_trip_recomputes_formulas(catalogue, tmp_path):
    pytest.importorskip("openpyxl")
    from core.data.catalogue import resolve_referentials
    from core.data.workbook import build_workbook, read_workbook

    frames = good_frames()
    path = tmp_path / "book.xlsx"
    build_workbook(catalogue, list(catalogue.tables), frames,
                   resolve_referentials(catalogue, frames), path, spare_rows=3)
    back, cells = read_workbook(path, catalogue)
    assert set(back) == set(catalogue.tables)
    # prefilled computed cells keep their value; spare rows and the example row are skipped
    assert back["plots"]["SHAPE"].tolist() == [400, 250, 600]
    assert list(back["plots"].index) == ["P1", "P2", "P3"]
    issues, clean = validate(catalogue, back, cells=cells)
    assert errors(issues) == []
    assert clean["plots"]["SHAPE"].tolist() == [400.0, 250.0, 600.0]
    for sheet, frame in validate(catalogue, frames)[1].items():
        assert diff_tables(catalogue.tables[sheet], frame, clean[sheet])["changed_cells"] == 0, sheet
    # the report points at the cell
    back["plots"].loc["P2", "ISLAND"] = 9
    bad = [i for i in validate(catalogue, back, cells=cells)[0] if "allowed code" in i.message]
    assert bad and bad[0].cell == "E11"


def test_workbook_carries_validations_and_protection(catalogue, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from core.data.catalogue import resolve_referentials
    from core.data.workbook import build_workbook

    frames = good_frames()
    path = tmp_path / "book.xlsx"
    build_workbook(catalogue, ["plots", "yield_A"], frames, resolve_referentials(catalogue, frames),
                   path, spare_rows=2)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames[0] == "Read me" and "Sources" in wb.sheetnames
    assert wb["Lists"].sheet_state == "hidden"
    plots = wb["plots"]
    assert plots.protection.sheet
    assert plots["B10"].protection.locked is False  # AREA: input
    assert plots["D10"].protection.locked is True  # SHAPE: computed
    assert str(plots["D13"].value).startswith('=IF($A13="","",ROUND(C13 / B13,0))')  # spare row
    assert plots["A9"].value == "EXAMPLE"
    kinds = {dv.type for dv in plots.data_validations.dataValidation}
    assert {"list", "decimal"} <= kinds
    assert any("Lists" in (dv.formula1 or "") for dv in wb["yield_A"].data_validations.dataValidation)


# --- the repository catalogue ------------------------------------------------------------------

@pytest.fixture(scope="module")
def repo_catalogue() -> Catalogue:
    return load_catalogue(REPO_ROOT / "docs" / "data" / "catalogue.yaml")


def test_every_file_the_pipeline_reads_is_catalogued(repo_catalogue):
    source = (REPO_ROOT / "case_studies" / "guadeloupe" / "pipeline" / "data_pipeline.py").read_text(
        encoding="utf-8")
    read = set(re.findall(r'"([A-Za-z_0-9]+(?:\{scenario\}|\{DEFAULT_SCENARIO\})?\.(?:txt|set))"', source))
    read |= {m.replace("{", "").replace("}", "") for m in re.findall(r'f"([A-Za-z_0-9{}]+\.txt)"', source)}
    names = {Path(spec.file).name for spec in repo_catalogue.tables.values()}
    stems = {n.split("{")[0] for n in (Path(s.entry["file"]).name for s in repo_catalogue.tables.values())}
    missing = sorted(f for f in read if f not in names and not any(
        f.startswith(stem) and stem.endswith("_") for stem in stems))
    assert missing == [], missing


def test_repository_catalogue_is_well_formed(repo_catalogue):
    types = {"int", "float", "code", "binary", "key"}
    referentials = set(repo_catalogue.referentials)
    for sheet, spec in repo_catalogue.tables.items():
        assert spec.level in repo_catalogue.levels, sheet
        for key in ("title", "description", "source", "licence"):
            assert spec.entry.get(key), f"{sheet}: {key}"
        for name, field in {**spec.fields, **spec.row_fields, "value": spec.value}.items():
            assert field.get("type", "float") in types, f"{sheet}.{name}"
            if field.get("type") == "code":
                assert field.get("values"), f"{sheet}.{name}"
        for axis in (spec.rows, spec.columns, spec.entry.get("parent") or {}, spec.entry.get("child") or {}):
            if axis.get("referential"):
                assert axis["referential"] in referentials, f"{sheet}: {axis['referential']}"


def test_max_level_leaves_out_plot_and_farm_tables(repo_catalogue):
    from scripts.build_data_templates import select_sheets

    shareable = select_sheets(repo_catalogue, max_level=1)
    assert shareable and all(repo_catalogue.tables[s].level <= 1 for s in shareable)
    assert "plot_data" not in shareable and "farm_plot_map" not in shareable
    assert "farm_risk_aversion_table" not in select_sheets(repo_catalogue)  # unused: opt-in
