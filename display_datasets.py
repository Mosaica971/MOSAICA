from pathlib import Path

from case_studies.guadeloupe.data_pipeline import build_dataset
from core.config import load_config
from core.data.dataset import build_registry

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"


def main() -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    registry = build_registry(dataset)

    for row in registry:
        print(f"{row['category']:<12} {row['name']:<20} {row['type']:<12} {row['size']}")


if __name__ == "__main__":
    main()
