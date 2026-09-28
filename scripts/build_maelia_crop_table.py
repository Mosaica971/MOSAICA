"""Regenerate the per-crop table of docs/maelia/crop-parameters.md (~7 s, no solve).

    python scripts/build_maelia_crop_table.py

Builds the dataset (data/ must be present) and rewrites only the part of the page between
its GENERATED markers: per fine crop, which MAELIA parameters the GAMS tables already give.
The rest of the page -- the parameter-by-parameter mapping -- is written by hand. See
case_studies/guadeloupe/reporting/maelia_crops.py for how each cell is decided.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import load_config

from scripts._common import CONFIG_PATH, ROOT

PAGE = ROOT / "docs" / "maelia" / "crop-parameters.md"
BEGIN, END = "<!-- BEGIN GENERATED: scripts/build_maelia_crop_table.py -->", "<!-- END GENERATED -->"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--page", type=Path, default=PAGE)
    args = parser.parse_args(argv)

    from case_studies.guadeloupe.pipeline.data_pipeline import (
        DEFAULT_YEAR, INDICE_H_DIR, build_dataset,
    )
    from case_studies.guadeloupe.reporting import maelia_crops
    from core.data.readers import read_wide_table

    config = load_config(CONFIG_PATH)
    year = (config.get("data") or {}).get("year", DEFAULT_YEAR)
    p = build_dataset(config).parameters
    coverage, left_out = maelia_crops.crop_coverage(
        crop_data=p["crop_data"],
        operation_data=p["operation_data"],
        crop_operation_matrix=p["crop_operation_matrix"],
        crop_yield=p["crop_yield"],
        crop_price=p["crop_price"],
        crop_subsidy_per_ha=p["crop_subsidy_per_ha_annualized"],
        crop_variable_cost_per_ha=p["crop_variable_cost_per_ha"],
        crop_plantation_duration=read_wide_table(INDICE_H_DIR / "Duree_Plant_Cult.txt")[year],
        crop_cycle_duration=p["crop_cycle_duration"],
    )
    generated = "\n\n".join([
        BEGIN,
        f"*Generated on {dt.date.today().isoformat()} from the tables of year {year}, scenario "
        f"{(config.get('data') or {}).get('scenario', 'RESTIT')}; {len(coverage)} crops. "
        f"Left out, no operation at all: {', '.join(f'`{c}`' for c in left_out)}.*",
        "### How many crops each block is covered for",
        maelia_crops.render_summary(coverage),
        maelia_crops.render_table(coverage),
        END,
    ])

    page = args.page.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(BEGIN) + ".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(page):
        print(f"{args.page}: markers not found", file=sys.stderr)
        return 1
    args.page.write_text(pattern.sub(lambda _: generated, page), encoding="utf-8")
    print(f"Written to {args.page}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
