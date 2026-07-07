from pathlib import Path

import pyomo.environ as pyo

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from core.config import load_config
from core.model.progress import solve_with_progress

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"


def main() -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)

    total_revenue = pyo.value(model.objective)
    allocated_plots = sum(1 for index in model.Y if pyo.value(model.Y[index]) > 0.5)
    total_plots = len(dataset.parameters["data_parc"])

    print(f"Total revenue (gross margin, MB_Ha_Cult): {total_revenue:,.2f}")
    print(f"Plots allocated to a crop: {allocated_plots} / {total_plots}")


if __name__ == "__main__":
    main()
