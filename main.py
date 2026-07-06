from case_studies.guadeloupe.data_pipeline import build_dataset
from core.data.dataset import build_registry


def main() -> None:
    dataset = build_dataset()
    registry = build_registry(dataset)

    for row in registry:
        print(f"{row['category']:<12} {row['name']:<20} {row['type']:<12} {row['size']}")


if __name__ == "__main__":
    main()
