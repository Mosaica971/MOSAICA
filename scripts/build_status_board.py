"""Write the status board: docs/status/STATUS.md.

    python scripts/build_status_board.py             # config and catalogues only, ~1 s
    python scripts/build_status_board.py --with-data # + pairs each eligibility rule removes (~7 s)

What is implemented, at which resolution, on which parameter choices, and what is left --
see case_studies/guadeloupe/reporting/status.py for how each table is built. The same tables
are on the dashboard's Status page. No solve. Exits non-zero when a parameter choice has
drifted from config.yaml, so the board can serve as a check.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from case_studies.guadeloupe.reporting import status
from core.config import load_config
from core.data.readers import read_flat_set

from scripts._common import CONFIG_PATH, ROOT

OUTPUT = ROOT / "docs" / "status" / "STATUS.md"
CROP_SET = ROOT / "data" / "sets" / "CULT_2017.set"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--with-data", action="store_true",
                        help="Build the dataset to count the pairs each eligibility rule removes.")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    config = load_config(CONFIG_PATH)
    levels, catalog = status.load_indicator_catalog()
    constraints = status.constraint_table(
        config, config_text=CONFIG_PATH.read_text(encoding="utf-8")
    )
    if CROP_SET.exists():
        crops = read_flat_set(CROP_SET)
    else:  # fresh clone without data/: fall back to the crops the config names
        crops = sorted({c for cs in constraints["crops"] if cs != "*" for c in cs})
    removals = None
    if args.with_data:
        from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset

        removals = status.eligibility_removals(build_dataset(config), config)

    parameters = status.parameter_table(config)
    markdown = status.render_markdown(
        levels=levels,
        indicator_matrix=status.indicator_level_matrix(levels, catalog),
        constraints=constraints,
        group_matrix=status.constraint_group_matrix(constraints, crops),
        parameters=parameters,
        roadmap=status.roadmap_table(),
        removals=removals,
        generated_on=dt.date.today().isoformat(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown, encoding="utf-8")
    print(f"Written to {args.out}")

    drifted = parameters[parameters["check"] != "ok"]
    drifted = drifted[drifted["check"] != "-"]
    for _, row in drifted.iterrows():
        print(f"  {row['check']}: {row['parameter']} -- retained {row['retained']!r}, "
              f"config {row['in_config']!r}", file=sys.stderr)
    return 1 if len(drifted) else 0


if __name__ == "__main__":
    raise SystemExit(main())
