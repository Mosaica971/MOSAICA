"""Manual investigation tool for brique D (solver performance).

Not run by the test suite -- times data-pipeline/model-build/solve phases
separately on a zone_filter-reduced subset, so perf work doesn't require a
full-dataset solve. See docs/superpowers/specs/2026-07-10-solver-performance-design.md.

Usage:
    python scripts/profile_solver.py --island 1
    python scripts/profile_solver.py --farm E1471 --farm E2
"""

import argparse
from pathlib import Path

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from core.config import load_config
from core.model.solver import solve_model
from core.model.timing import time_phases

CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "case_studies" / "guadeloupe" / "config.yaml"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--island", type=int, action="append", default=[])
    parser.add_argument("--region", action="append", default=[])
    parser.add_argument("--farm", action="append", default=[])
    parser.add_argument("--plot", action="append", default=[])
    return parser.parse_args(argv)


def build_zone_filter_from_args(args: argparse.Namespace) -> dict | None:
    include = {
        "islands": args.island,
        "regions": args.region,
        "farms": args.farm,
        "plots": args.plot,
    }
    include = {name: values for name, values in include.items() if values}
    if not include:
        return None
    return {"include": include}


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_config(CONFIG_PATH)
    zone_filter = build_zone_filter_from_args(args)
    if zone_filter is not None:
        config = {**config, "zone_filter": zone_filter}

    _dataset, _model, _results, timings = time_phases(
        lambda: build_dataset(config),
        lambda dataset: build_model(dataset, config),
        lambda model: solve_model(model, config),
    )

    total = sum(timings.values())
    print(f"zone_filter: {zone_filter}")
    for phase, duration in timings.items():
        print(f"  {phase:>13}: {duration:7.2f}s")
    print(f"  {'total':>13}: {total:7.2f}s")


if __name__ == "__main__":
    main()
