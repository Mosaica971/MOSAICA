"""Write the fill-in Excel workbook of the data catalogue (docs/data/catalogue.yaml).

One sheet per table: yellow cells to fill, grey locked headers and computed cells, units,
allowed values, drop-down lists from the referentials, an example row, a Read me and a Sources
sheet. Prefilled from data/ by default, so a partner corrects or extends the current tables
rather than retyping them; --blank writes empty sheets.

A prefilled workbook carries the level of its most sensitive table. The default output folder,
outputs/data_workbooks/, is gitignored for that reason; --max-level 1 writes a workbook without
any plot or farm table, which is the one to send to a partner.

    python scripts/build_data_templates.py                        # every table, prefilled
    python scripts/build_data_templates.py --max-level 1          # nothing at plot/farm level
    python scripts/build_data_templates.py --tables crop_data operation_data --blank
    python scripts/validate_data_workbook.py <workbook>           # then read it back
"""

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.data.catalogue import load_catalogue, read_table, resolve_referentials  # noqa: E402
from core.data.workbook import build_workbook  # noqa: E402

DEFAULT_CATALOGUE = REPO_ROOT / "docs" / "data" / "catalogue.yaml"
DEFAULT_OUT_DIR = REPO_ROOT / "outputs" / "data_workbooks"


def select_sheets(catalogue, tables=None, max_level=None, include_unused=False) -> list[str]:
    """Sheet names to write: by catalogue id or sheet name, capped by level."""
    sheets = []
    for sheet, spec in catalogue.tables.items():
        if tables and sheet not in tables and spec.id not in tables:
            continue
        if max_level is not None and spec.level > max_level:
            continue
        if spec.entry.get("unused") and not include_unused and not tables:
            continue
        sheets.append(sheet)
    if tables:
        known = set(catalogue.tables) | {s.id for s in catalogue.tables.values()}
        unknown = [t for t in tables if t not in known]
        if unknown:
            raise SystemExit(f"unknown table(s): {', '.join(unknown)}")
    return sheets


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--tables", nargs="+", help="catalogue ids or sheet names (default: all)")
    parser.add_argument("--max-level", type=int, help="leave out tables above this access level")
    parser.add_argument("--blank", action="store_true", help="empty sheets, not prefilled")
    parser.add_argument("--include-unused", action="store_true",
                        help="also write the tables the pipeline does not read")
    parser.add_argument("--spare-rows", type=int, default=50,
                        help="empty input rows after the data (default 50)")
    parser.add_argument("--out", type=Path, help="workbook path (default outputs/data_workbooks/...)")
    args = parser.parse_args(argv)

    catalogue = load_catalogue(args.catalogue)
    sheets = select_sheets(catalogue, args.tables, args.max_level, args.include_unused)
    if not sheets:
        raise SystemExit("no table selected")

    readable = {s: catalogue.tables[s] for s in catalogue.tables
                if (args.data_dir / catalogue.tables[s].file).exists()}
    missing = [s for s in sheets if s not in readable]
    if missing and not args.blank:
        print(f"not in {args.data_dir}, written empty: {', '.join(missing)}")
    # Referentials come from every readable table, including the ones not written: the drop-down
    # of a crop sheet needs the crop list even in a workbook without the crops sheet.
    frames_all = {s: read_table(spec, args.data_dir) for s, spec in readable.items()}
    referentials = resolve_referentials(catalogue, frames_all, args.data_dir)
    frames = {} if args.blank else {s: frames_all[s] for s in sheets if s in frames_all}

    top = max(catalogue.tables[s].level for s in sheets)
    out = args.out or DEFAULT_OUT_DIR / (
        f"mosaica_data_L{top}_{'blank' if args.blank else 'prefilled'}_{date.today().isoformat()}.xlsx")
    print(f"writing {len(sheets)} sheet(s), highest level {top} ({catalogue.level_name(top)}) ...")
    build_workbook(catalogue, sheets, frames, referentials, out, spare_rows=args.spare_rows)
    print(f"-> {out}")
    if top >= 2 and not args.blank:
        print(f"   level {top}: plot or farm data. Keep it out of the repository and share it only "
              "with people entitled to that level (docs/data/README.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
