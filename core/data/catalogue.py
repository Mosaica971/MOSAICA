"""A data catalogue: the schema of every input table, and the checks that follow from it.

The catalogue is a YAML file (the case study's lives in docs/data/catalogue.yaml; its header
documents the format). This module reads it, reads and writes the tables it describes in the
GAMS text formats of data/, and validates a table against its entry: required keys, types,
bounds, allowed codes, foreign keys, computed and derived columns. It knows nothing of Excel
(core/data/workbook.py) nor of any territory.

Every table is held as a DataFrame:
  set      one column, `id`
  mapping  two columns, the parent and child names
  records  index = the row key, one column per field
  matrix   index = the row keys, columns = the column keys
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from core.data.readers import read_flat_set, read_mapping_set, read_wide_table

LAYOUTS = ("set", "mapping", "records", "matrix")
INDEX_LABEL = "ident"  # first header cell of every GAMS wide table in data/tables
_IDENTIFIER = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


@dataclass(frozen=True)
class TableSpec:
    """One table of the catalogue, with any `{variant}` of its file name already expanded."""

    id: str  # catalogue id, e.g. crop_price
    sheet: str  # id, suffixed by the variant: crop_price_SMART (also the workbook sheet name)
    file: str  # path relative to the data directory
    layout: str
    entry: dict = field(repr=False)  # the raw catalogue entry

    def __getattr__(self, name):  # title, description, source, level... read from the entry
        entry = object.__getattribute__(self, "entry")
        if name in entry:
            return entry[name]
        raise AttributeError(name)

    @property
    def level(self) -> int:
        return int(self.entry.get("level", 2))

    @property
    def fields(self) -> dict:
        return self.entry.get("fields") or {}

    @property
    def row_fields(self) -> dict:
        return self.entry.get("row_fields") or {}

    @property
    def rows(self) -> dict:
        return self.entry.get("rows") or {}

    @property
    def columns(self) -> dict:
        return self.entry.get("columns") or {}

    @property
    def value(self) -> dict:
        return self.entry.get("value") or {"type": "float"}

    @property
    def key_names(self) -> tuple[str, ...]:
        """Column names of a set / mapping table."""
        if self.layout == "set":
            return ("id",)
        if self.layout == "mapping":
            return (self.entry["parent"]["name"], self.entry["child"]["name"])
        return ()


@dataclass(frozen=True)
class Issue:
    """A problem found in a table. `where` names the row / column, `cell` the sheet cell if known."""

    sheet: str
    message: str
    where: str = ""
    cell: str = ""
    severity: str = "error"  # error | warning

    def __str__(self) -> str:
        location = " ".join(part for part in (self.cell, self.where) if part)
        return f"[{self.severity}] {self.sheet}{' ' + location if location else ''}: {self.message}"


class Catalogue:
    """The parsed catalogue: levels, referentials, tables (variants expanded) and outputs."""

    def __init__(self, raw: dict, path: Path | None = None):
        self.raw = raw
        self.path = path
        self.version = raw.get("version")
        self.levels: dict[int, dict] = {int(k): v for k, v in (raw.get("levels") or {}).items()}
        self.referentials: dict[str, dict] = raw.get("referentials") or {}
        self.outputs: dict[str, dict] = raw.get("outputs") or {}
        self.tables: dict[str, TableSpec] = {}
        for table_id, entry in (raw.get("tables") or {}).items():
            layout = entry.get("layout")
            if layout not in LAYOUTS:
                raise ValueError(f"table {table_id}: layout must be one of {LAYOUTS}, got {layout!r}")
            for sheet, file in _expand_variants(table_id, entry):
                if len(sheet) > 31:
                    raise ValueError(f"table {sheet}: a sheet name is limited to 31 characters")
                self.tables[sheet] = TableSpec(table_id, sheet, file, layout, entry)

    def table(self, table_id: str) -> TableSpec:
        """The spec of `table_id`, or of its first variant when the id has several."""
        if table_id in self.tables:
            return self.tables[table_id]
        for spec in self.tables.values():
            if spec.id == table_id:
                return spec
        raise KeyError(table_id)

    def level_name(self, level: int) -> str:
        return self.levels.get(level, {}).get("name", str(level))


def load_catalogue(path: Path) -> Catalogue:
    path = Path(path)
    return Catalogue(yaml.safe_load(path.read_text(encoding="utf-8")), path)


def _expand_variants(table_id: str, entry: dict) -> list[tuple[str, str]]:
    variants = entry.get("variants") or {}
    if not variants:
        return [(table_id, entry["file"])]
    if len(variants) != 1:
        raise ValueError(f"table {table_id}: one variant dimension is supported")
    (name, values), = variants.items()
    return [(f"{table_id}_{value}", entry["file"].replace("{" + name + "}", str(value)))
            for value in values]


# --- reading and writing the GAMS text formats -------------------------------------------------

def read_table(spec: TableSpec, data_dir: Path) -> pd.DataFrame:
    path = Path(data_dir) / spec.file
    if spec.layout == "set":
        return pd.DataFrame({"id": read_flat_set(path)})
    if spec.layout == "mapping":
        return read_mapping_set(path, *spec.key_names)
    frame = read_wide_table(path)
    frame.index = frame.index.astype(str)
    frame.columns = [str(c) for c in frame.columns]
    return frame


def format_number(value) -> str:
    """The shortest faithful text for a cell: 12.0 -> '12', 0.1 -> '0.1'."""
    if isinstance(value, str):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    number = float(value)
    if number.is_integer() and abs(number) < 1e15:
        return str(int(number))
    return repr(number)


def table_text(spec: TableSpec, frame: pd.DataFrame) -> str:
    """The table serialised in the format data/ uses (tab-separated wide table or .set lines)."""
    if spec.layout == "set":
        return "".join(f"{value}\n" for value in frame["id"])
    if spec.layout == "mapping":
        parent, child = spec.key_names
        return "".join(f"{p}.{c}\n" for p, c in zip(frame[parent], frame[child]))
    lines = ["\t".join([INDEX_LABEL, *map(str, frame.columns)])]
    for key, row in frame.iterrows():
        lines.append("\t".join([str(key), *(format_number(v) for v in row.tolist())]))
    return "\n".join(lines) + "\n"


def write_table(spec: TableSpec, frame: pd.DataFrame, out_dir: Path) -> Path:
    path = Path(out_dir) / spec.file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(table_text(spec, frame).encode("utf-8"))
    return path


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- referentials ------------------------------------------------------------------------------

def resolve_referentials(
    catalogue: Catalogue, frames: dict[str, pd.DataFrame], data_dir: Path | None = None
) -> dict[str, list[str]]:
    """The id list of every referential, from `frames` first, else from data_dir.

    A referential whose source is neither in `frames` nor readable is left out: checks against
    it are then skipped, with a warning from `validate`.
    """
    resolved: dict[str, list[str]] = {}
    for name, ref in catalogue.referentials.items():
        values = None
        if "values" in ref:
            values = [str(v) for v in ref["values"]]
        elif "set" in ref:
            sheet = next((s.sheet for s in catalogue.tables.values() if s.file == ref["set"]), None)
            if sheet in frames:
                values = [str(v) for v in frames[sheet]["id"]]
            elif data_dir is not None and (Path(data_dir) / ref["set"]).exists():
                values = read_flat_set(Path(data_dir) / ref["set"])
        elif "index_of" in ref or "column_of" in ref:
            table_id, column = (ref["index_of"], None) if "index_of" in ref else ref["column_of"]
            spec = catalogue.table(table_id)
            frame = frames.get(spec.sheet)
            if frame is None and data_dir is not None and (Path(data_dir) / spec.file).exists():
                frame = read_table(spec, data_dir)
            if frame is not None:
                series = frame.index.to_series() if column is None else frame[column]
                values = list(dict.fromkeys(str(v) for v in series))
        if values is not None:
            resolved[name] = values
    return resolved


# --- validation --------------------------------------------------------------------------------

def rule_text(spec: dict) -> str:
    """What a field accepts, in words (the workbook's 'allowed' row)."""
    kind = spec.get("type", "float")
    if "computed" in spec:
        return f"computed: {spec['computed']['expr']}"
    if "derived" in spec:
        return "derived: " + ", ".join(f"{k} {v}" for k, v in spec["derived"].items())
    if kind == "binary":
        return "0 or 1"
    if kind == "code":
        return "one of " + ", ".join(f"{k}={v}" for k, v in spec["values"].items())
    if kind == "key":
        return f"an id of {spec.get('referential', '?')}"
    bounds = []
    if "min" in spec:
        bounds.append(f">= {format_number(spec['min'])}")
    if "max" in spec:
        bounds.append(f"<= {format_number(spec['max'])}")
    text = "whole number" if kind == "int" else "number"
    return text + (" " + ", ".join(bounds) if bounds else "")




def _check_values(sheet: str, values: pd.Series, spec: dict, referentials: dict[str, list[str]],
                  issues: list[Issue], locate) -> pd.Series:
    """Check one column (or one matrix row) against a field spec; return it as numbers.

    `locate(key)` gives the (where, cell) of the value at index `key`, for the messages.
    """

    def report(key, message):
        where, cell = locate(key)
        issues.append(Issue(sheet, message, where, cell))

    kind = spec.get("type", "float")
    if kind == "key":
        ref = spec.get("referential")
        if ref in referentials:
            known = set(referentials[ref])
            for key, value in values.items():
                if str(value) not in known:
                    report(key, f"{value!r} is not an id of {ref}")
        return values
    empty = values.isna() | values.astype(str).str.strip().eq("")
    numbers = pd.to_numeric(values.where(~empty), errors="coerce")
    if not spec.get("optional"):
        for key in values.index[empty]:
            report(key, "empty cell")
    for key in values.index[numbers.isna() & ~empty]:
        report(key, f"{values[key]!r} is not a number")
    present = numbers.dropna()
    if kind in ("int", "code", "binary"):
        for key in present.index[present.apply(lambda v: not float(v).is_integer())]:
            report(key, f"{format_number(present[key])} is not a whole number")
    allowed = None
    if kind == "binary":
        allowed = {0, 1}
    elif kind == "code":
        allowed = {int(k) for k in spec["values"]}
    if allowed is not None:
        for key in present.index[~present.isin(allowed)]:
            report(key, f"{format_number(present[key])} is not an allowed code ({rule_text(spec)})")
    if "min" in spec:
        for key in present.index[present < spec["min"]]:
            report(key, f"{format_number(present[key])} < minimum {format_number(spec['min'])}")
    if "max" in spec:
        for key in present.index[present > spec["max"]]:
            report(key, f"{format_number(present[key])} > maximum {format_number(spec['max'])}")
    return numbers


def evaluate_computed(frame: pd.DataFrame, computed: dict, rounded: bool = True) -> pd.Series:
    """A computed column from the other columns of the same row."""
    names = [n for n in dict.fromkeys(_IDENTIFIER.findall(computed["expr"])) if n in frame.columns]
    numeric = frame[names].apply(pd.to_numeric, errors="coerce")
    result = numeric.eval(computed["expr"])
    if rounded and "round" in computed:  # half away from zero, as Excel's ROUND and GAMS round() do
        scale = 10.0 ** int(computed["round"])
        result = np.floor(result.abs() * scale + 0.5) / scale * np.sign(result).replace(0, 1)
    return result


def excel_formula(computed: dict, cell_of: dict[str, str]) -> str:
    """The computed column as an Excel formula, `cell_of` mapping a column name to its cell."""
    expression = _IDENTIFIER.sub(lambda m: cell_of.get(m.group(0), m.group(0)), computed["expr"])
    if "round" in computed:
        expression = f"ROUND({expression},{int(computed['round'])})"
    return "=" + expression


def _siblings(catalogue: Catalogue, frames: dict[str, pd.DataFrame], data_dir: Path | None,
              mapping_id: str) -> pd.Series | None:
    """For each child of a mapping, how many children share its parent."""
    spec = catalogue.table(mapping_id)
    frame = frames.get(spec.sheet)
    if frame is None and data_dir is not None and (Path(data_dir) / spec.file).exists():
        frame = read_table(spec, data_dir)
    if frame is None:
        return None
    parent, child = spec.key_names
    counts = frame[parent].map(frame[parent].value_counts())
    series = pd.Series(counts.values, index=frame[child].astype(str))
    return series[~series.index.duplicated()]  # a child listed twice is reported by the mapping


def _is_formula(value) -> bool:
    return isinstance(value, str) and value.startswith("=")


def validate_table(
    catalogue: Catalogue,
    spec: TableSpec,
    frame: pd.DataFrame,
    referentials: dict[str, list[str]],
    frames: dict[str, pd.DataFrame] | None = None,
    data_dir: Path | None = None,
    cells: dict | None = None,
) -> tuple[list[Issue], pd.DataFrame]:
    """Check one table; return the issues and the table cleaned for export.

    `cells` maps (row key, column) to the sheet cell, for the report (read_workbook gives it).
    It is not kept in `frame.attrs`: pandas deep-copies attrs on every operation, which made
    validating a 25 000-row sheet take twenty minutes.

    The cleaned table has numeric cells as numbers, and computed / derived columns recomputed
    (a workbook read without Excel holds formulas, not values).
    """
    frames = frames or {}
    cells = cells or {}
    issues: list[Issue] = []
    sheet = spec.sheet

    def _cell(_frame, key, column) -> str:
        return cells.get((str(key), str(column)), "")

    def need(ref_name: str | None) -> bool:
        if ref_name and ref_name not in referentials:
            issues.append(Issue(sheet, f"referential {ref_name} unavailable: its ids are not checked",
                                severity="warning"))
            return False
        return bool(ref_name)

    if spec.layout == "set":
        ids = frame["id"].astype(str).str.strip()
        for value in ids[ids.duplicated()].unique():
            issues.append(Issue(sheet, f"duplicate id {value!r}"))
        if ids.eq("").any():
            issues.append(Issue(sheet, "empty id"))
        return issues, pd.DataFrame({"id": ids[ids.ne("")].tolist()})

    if spec.layout == "mapping":
        parent, child = spec.key_names
        clean = frame[[parent, child]].astype(str).apply(lambda s: s.str.strip())
        for role, name in (("parent", parent), ("child", child)):
            ref = spec.entry[role].get("referential")
            if need(ref):
                known = set(referentials[ref])
                for value in clean.loc[~clean[name].isin(known), name].unique():
                    issues.append(Issue(sheet, f"{value!r} is not an id of {ref}", f"column {name}"))
        pairs = clean[clean.duplicated()]
        for _, row in pairs.drop_duplicates().iterrows():
            issues.append(Issue(sheet, f"duplicate pair {row[parent]}.{row[child]}"))
        if spec.entry["child"].get("unique"):
            twice = clean.drop_duplicates()[child]
            for value in twice[twice.duplicated()].unique():
                issues.append(Issue(sheet, f"{child} {value!r} has several {parent}s"))
        return issues, clean.reset_index(drop=True)

    frame = frame.copy()
    padded = [k for k in frame.index if str(k) != str(k).strip()]
    for key in padded:
        issues.append(Issue(sheet, f"row key {str(key)!r} has surrounding spaces (stripped)",
                            severity="warning"))
    frame.index = frame.index.map(lambda k: str(k).strip())
    for key in frame.index[frame.index.duplicated()].unique():
        issues.append(Issue(sheet, f"duplicate row key {key!r}"))
    if (frame.index == "").any():
        issues.append(Issue(sheet, "empty row key"))

    row_spec = spec.rows
    row_ref = row_spec.get("referential")
    if need(row_ref):
        known = set(referentials[row_ref])
        for key in frame.index[~frame.index.isin(known)]:
            issues.append(Issue(sheet, f"row {key!r} is not an id of {row_ref}"))

    def locate_in(column):  # records: the value of `column` on row `key`
        return lambda key: (f"row {key}, column {column}", _cell(frame, key, column))

    def locate_row(row):  # matrix: the value of row `row` in column `key`
        return lambda key: (f"row {row}, column {key}", _cell(frame, row, key))

    clean = pd.DataFrame(index=frame.index)
    if spec.layout == "records":
        expected = list(spec.fields)
        _header_issues(sheet, expected, list(frame.columns), issues)
        for name, field_spec in spec.fields.items():
            if name not in frame.columns:
                continue
            column = frame[name]
            if "computed" in field_spec:
                # A value typed in is kept when it agrees with the formula: recomputing would
                # move stored values by float noise (CONFORM sits on a 1500 threshold). The
                # tolerance is read against the unrounded expression.
                computed = field_spec["computed"]
                exact = evaluate_computed(frame, computed, rounded=False)
                given = pd.to_numeric(column.where(~column.map(_is_formula)), errors="coerce")
                tolerance = float(computed.get("tolerance", 0)) + 1e-6
                off = given.notna() & exact.notna() & ((given - exact).abs() > tolerance)
                for key in frame.index[off]:
                    issues.append(Issue(sheet, f"{format_number(given[key])} differs from "
                                        f"{computed['expr']} = {exact[key]:.6g}",
                                        f"row {key}, column {name}", _cell(frame, key, name)))
                clean[name] = given.where(given.notna() & ~off, evaluate_computed(frame, computed))
                continue
            if "derived" in field_spec:
                mapping_id = field_spec["derived"].get("siblings_in")
                expected_counts = _siblings(catalogue, frames, data_dir, mapping_id) if mapping_id else None
                if expected_counts is None:
                    issues.append(Issue(sheet, f"column {name}: {mapping_id} unavailable, derived "
                                        "values kept as given", severity="warning"))
                    clean[name] = _check_values(sheet, column, field_spec, referentials, issues,
                                                locate_in(name))
                    continue
                recomputed = expected_counts.reindex(frame.index)
                given = pd.to_numeric(column, errors="coerce")
                off = given.notna() & recomputed.notna() & (given != recomputed)
                for key in frame.index[off]:
                    issues.append(Issue(sheet, f"{format_number(given[key])} but {mapping_id} gives "
                                        f"{format_number(recomputed[key])}", f"row {key}, column {name}",
                                        _cell(frame, key, name)))
                for key in frame.index[recomputed.isna()]:
                    issues.append(Issue(sheet, f"row {key!r} is missing from {mapping_id}",
                                        f"column {name}"))
                clean[name] = recomputed.where(recomputed.notna(), given)
                continue
            clean[name] = _check_values(sheet, column, field_spec, referentials, issues,
                                        locate_in(name))
        return issues, clean

    # matrix
    col_spec = spec.columns
    columns = [str(c) for c in frame.columns]
    col_ref = col_spec.get("referential")
    if need(col_ref):
        known = referentials[col_ref]
        unknown = [c for c in columns if c not in set(known)]
        for c in unknown:
            issues.append(Issue(sheet, f"column {c!r} is not an id of {col_ref}"))
        if not col_spec.get("subset"):
            for c in known:
                if c not in columns:
                    issues.append(Issue(sheet, f"column {c!r} of {col_ref} is missing"))
    for c in pd.Index(columns)[pd.Index(columns).duplicated()].unique():
        issues.append(Issue(sheet, f"duplicate column {c!r}"))
    if spec.row_fields:
        _header_issues(sheet, list(spec.row_fields), list(frame.index), issues, what="row")
    rows_out = {}
    for key in frame.index:
        field_spec = spec.row_fields.get(key, spec.value) if spec.row_fields else spec.value
        if spec.row_fields and key not in spec.row_fields:
            continue
        values = frame.loc[key]
        if isinstance(values, pd.DataFrame):  # duplicated key, already reported
            values = values.iloc[0]
        rows_out[key] = _check_values(sheet, values, field_spec, referentials, issues,
                                      locate_row(key))
    clean = pd.DataFrame.from_dict(rows_out, orient="index").astype(float)
    return issues, clean


def _header_issues(sheet: str, expected: list[str], given: list[str], issues: list[Issue],
                   what: str = "column") -> None:
    for name in expected:
        if name not in given:
            issues.append(Issue(sheet, f"{what} {name!r} is missing"))
    for name in given:
        if name not in expected:
            issues.append(Issue(sheet, f"unexpected {what} {name!r} (not in the catalogue)",
                                severity="warning"))


def validate(
    catalogue: Catalogue,
    frames: dict[str, pd.DataFrame],
    data_dir: Path | None = None,
    cells: dict[str, dict] | None = None,
) -> tuple[list[Issue], dict[str, pd.DataFrame]]:
    """Validate every table in `frames` (keyed by sheet name); return issues and clean tables.

    `cells[sheet]` optionally locates each value in a workbook (see validate_table).
    """
    referentials = resolve_referentials(catalogue, frames, data_dir)
    issues: list[Issue] = []
    clean: dict[str, pd.DataFrame] = {}
    for sheet, frame in frames.items():
        spec = catalogue.tables.get(sheet)
        if spec is None:
            issues.append(Issue(sheet, "sheet not in the catalogue, ignored", severity="warning"))
            continue
        table_issues, clean[sheet] = validate_table(catalogue, spec, frame, referentials, frames,
                                                    data_dir, (cells or {}).get(sheet))
        issues.extend(table_issues)
    return issues, clean


def diff_tables(spec: TableSpec, old: pd.DataFrame, new: pd.DataFrame) -> dict:
    """What changed between two versions of a table: keys added / removed, cells changed."""
    if spec.layout in ("set", "mapping"):
        old_rows = set(map(tuple, old.astype(str).values))
        new_rows = set(map(tuple, new.astype(str).values))
        return {"added": len(new_rows - old_rows), "removed": len(old_rows - new_rows),
                "changed_cells": 0}
    old = old.copy()
    new = new.copy()
    old.index, new.index = old.index.astype(str), new.index.astype(str)
    old.columns, new.columns = [str(c) for c in old.columns], [str(c) for c in new.columns]
    common_rows = old.index.intersection(new.index)
    common_cols = [c for c in old.columns if c in set(new.columns)]
    a = old.loc[common_rows, common_cols].apply(pd.to_numeric, errors="coerce")
    b = new.loc[common_rows, common_cols].apply(pd.to_numeric, errors="coerce")
    changed = ~((a - b).abs().le(1e-9 * (1 + a.abs())) | (a.isna() & b.isna()))
    return {
        "added": int(len(new.index.difference(old.index))),
        "removed": int(len(old.index.difference(new.index))),
        "added_columns": [c for c in new.columns if c not in set(old.columns)],
        "removed_columns": [c for c in old.columns if c not in set(new.columns)],
        "changed_cells": int(changed.values.sum()),
    }
