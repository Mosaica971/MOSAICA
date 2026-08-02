"""Manual inspection tool: print the dataset registry (every set/parameter/scalar with
its category, type and size) for a quick sanity check of what build_dataset produces.

    python scripts/display_datasets.py
    python scripts/display_datasets.py --case-study guadeloupe
"""

import argparse
import sys
from pathlib import Path

# Running this file directly puts scripts/ on sys.path, not the repo root, so the
# case_studies/core imports below would fail. Prepend the repo root ourselves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.case_study import add_argument, load
from core.config import load_config
from core.data.dataset import build_registry


def main(case_study: str | None = None) -> None:
    case = load(case_study)
    config = load_config(case.config_path)
    dataset = case.build_dataset(config)
    registry = build_registry(dataset)

    for row in registry:
        print(f"{row['category']:<12} {row['name']:<20} {row['type']:<12} {row['size']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_argument(parser)
    main(parser.parse_args().case_study)
