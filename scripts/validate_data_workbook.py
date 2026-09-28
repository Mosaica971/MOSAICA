"""Read a filled data workbook back, check it against the catalogue, export the tables.

Checks types, bounds, allowed codes, row and column keys against the referentials (taken from
the workbook, else from data/), duplicates, missing rows or columns, computed and derived
columns. Prints a report; exits 1 if there is any error.

With --export the tables are written in the GAMS text formats of data/ to a new dated staging
folder, with a manifest giving each file's SHA-256, row count and access level. Staging, not
data/: a new table version is reviewed (--compare) and then copied in by hand. A version is
never edited in place -- the manifest is what a run's recap can later cite.

    python scripts/validate_data_workbook.py outputs/data_workbooks/<file>.xlsx
    python scripts/validate_data_workbook.py <file>.xlsx --report report.md --export --compare
    python scripts/validate_data_workbook.py --check-data     # data/ itself against the catalogue
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.data.catalogue import (  # noqa: E402
    diff_tables,
    load_catalogue,
    read_table,
    sha256_of,
    validate,
    write_table,
)

DEFAULT_CATALOGUE = REPO_ROOT / "docs" / "data" / "catalogue.yaml"
DEFAULT_STAGING = REPO_ROOT / "outputs" / "data_staging"
MAX_ISSUES_PER_SHEET = 200


def render_report(source: str, issues, sheets, diffs=None) -> str:
    errors = Counter(i.sheet for i in issues if i.severity == "error")
    warnings = Counter(i.sheet for i in issues if i.severity == "warning")
    lines = [f"# Data validation -- {source}", "",
             f"{sum(errors.values())} error(s), {sum(warnings.values())} warning(s) "
             f"over {len(sheets)} table(s).", "",
             "| table | errors | warnings |" + (" rows added | removed | cells changed |" if diffs else ""),
             "|---|---|---|" + ("---|---|---|" if diffs else "")]
    for sheet in sheets:
        row = f"| {sheet} | {errors.get(sheet, 0)} | {warnings.get(sheet, 0)} |"
        if diffs:
            d = diffs.get(sheet)
            row += (f" {d['added']} | {d['removed']} | {d['changed_cells']} |" if d else " new | | |")
        lines.append(row)
    for sheet in sheets:
        found = [i for i in issues if i.sheet == sheet]
        if not found:
            continue
        lines += ["", f"## {sheet}", ""]
        for issue in found[:MAX_ISSUES_PER_SHEET]:
            location = " ".join(p for p in (issue.cell, issue.where) if p)
            lines.append(f"- **{issue.severity}**{' `' + location + '`' if location else ''}: {issue.message}")
        if len(found) > MAX_ISSUES_PER_SHEET:
            lines.append(f"- ... and {len(found) - MAX_ISSUES_PER_SHEET} more")
    return "\n".join(lines) + "\n"


def export(catalogue, clean, out_dir: Path, source: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=False)
    files = {}
    for sheet, frame in clean.items():
        spec = catalogue.tables[sheet]
        path = write_table(spec, frame, out_dir)
        files[spec.file] = {"table": sheet, "sha256": sha256_of(path), "rows": int(len(frame)),
                            "level": spec.level}
    manifest = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "catalogue": str(catalogue.path.relative_to(REPO_ROOT)) if catalogue.path else None,
        "catalogue_version": catalogue.version,
        "highest_level": max((f["level"] for f in files.values()), default=0),
        "files": files,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("workbook", type=Path, nargs="?")
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data",
                        help="where referentials missing from the workbook are read (default data/)")
    parser.add_argument("--check-data", action="store_true",
                        help="validate the tables of --data-dir instead of a workbook")
    parser.add_argument("--report", type=Path, help="also write the report to this Markdown file")
    parser.add_argument("--export", nargs="?", const=True, type=Path, metavar="DIR",
                        help="write the tables (default outputs/data_staging/<timestamp>/)")
    parser.add_argument("--compare", action="store_true",
                        help="count rows added / removed and cells changed against --data-dir")
    parser.add_argument("--force", action="store_true", help="export even if there are errors")
    args = parser.parse_args(argv)

    catalogue = load_catalogue(args.catalogue)
    data_dir = args.data_dir if args.data_dir.exists() else None
    if args.check_data:
        if data_dir is None:
            raise SystemExit(f"{args.data_dir} does not exist")
        frames = {s: read_table(spec, data_dir) for s, spec in catalogue.tables.items()
                  if (data_dir / spec.file).exists()}
        cells = {}
        source = str(args.data_dir)
    elif args.workbook:
        from core.data.workbook import read_workbook

        frames, cells = read_workbook(args.workbook, catalogue)
        source = args.workbook.name
    else:
        parser.error("give a workbook, or --check-data")

    issues, clean = validate(catalogue, frames, data_dir, cells)
    diffs = None
    if args.compare and data_dir is not None:
        diffs = {s: diff_tables(catalogue.tables[s], read_table(catalogue.tables[s], data_dir), frame)
                 for s, frame in clean.items() if (data_dir / catalogue.tables[s].file).exists()}
    report = render_report(source, issues, list(frames), diffs)
    print(report)
    if args.report:
        args.report.write_text(report, encoding="utf-8")

    has_errors = any(i.severity == "error" for i in issues)
    if args.export:
        if has_errors and not args.force:
            print("not exported: fix the errors first (or --force)")
        else:
            out_dir = (args.export if isinstance(args.export, Path)
                       else DEFAULT_STAGING / datetime.now().strftime("%Y%m%d-%H%M%S"))
            print(f"exported -> {export(catalogue, clean, out_dir, source)}")
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
