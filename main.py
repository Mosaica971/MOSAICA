from pathlib import Path

import pyomo.environ as pyo

from case_studies.guadeloupe.data_pipeline import build_dataset
from case_studies.guadeloupe.model import build_model
from case_studies.guadeloupe.reporting.report import generate_report
from core.config import load_config
from core.model.progress import solve_with_progress

CONFIG_PATH = Path(__file__).resolve().parent / "case_studies" / "guadeloupe" / "config.yaml"
OUTPUTS_ROOT = Path(__file__).resolve().parent / "outputs"


def main(outputs_root: Path = OUTPUTS_ROOT) -> None:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    model = build_model(dataset, config)
    results, duration = solve_with_progress(model, config, case_study=CONFIG_PATH.parent.name)

    output_dir = generate_report(dataset, config, model, results, duration, outputs_root=outputs_root)

    total_revenue = pyo.value(model.objective)
    allocated_plots = sum(1 for index in model.Y if pyo.value(model.Y[index]) > 0.5)
    total_plots = len(dataset.parameters["data_parc"])

    print(f"Total revenue (gross margin, MB_Ha_Cult): {total_revenue:,.2f}")
    print(f"Plots allocated to a crop: {allocated_plots} / {total_plots}")
    print(f"Report written to: {output_dir}")


if __name__ == "__main__":
    main()
