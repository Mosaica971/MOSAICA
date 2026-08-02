"""One full solve: build the dataset, build the model, solve it, write a run folder.

Everything else is configuration. Which case study runs comes from `--case-study` (or
$MOSAICA_CASE_STUDY, default `guadeloupe`); what it does comes from that case study's
`config.yaml`. There are no other options on purpose -- a run must be reproducible from its
`config_used.yaml` alone.

    .venv/Scripts/python main.py
    .venv/Scripts/python main.py --case-study guadeloupe

SLOW: 30-55 min on the full Guadeloupe dataset, with large run-to-run variance (the
bottleneck is the branch-and-bound search). Use `zone_filter` in the config, or
`scripts/profile_solver.py`, to iterate.
"""

import argparse
from pathlib import Path

import pyomo.environ as pyo

from core.case_study import CaseStudy, add_argument, load
from core.config import load_config
from core.reporting.run_folder import read_allocation
from core.solve.progress import solve_with_progress
from core.solve.warm_start import apply_allocation, constraint_violations, objective_value

OUTPUTS_ROOT = Path(__file__).resolve().parent / "outputs"

_MAX_VIOLATIONS_SHOWN = 5


def _apply_warm_start(model, config: dict, outputs_root: Path) -> bool:
    """Seed the solve from a past run if `solver.warm_start_from` names one.

    Reports what it placed and, crucially, whether the result is feasible: an infeasible
    start is silently discarded by HiGHS, so without this check the run would look
    warm-started and behave exactly like a cold one. Returns whether to pass warmstart.
    """
    source = (config.get("solver") or {}).get("warm_start_from")
    if not source:
        return False

    run_dir = Path(source)
    if not run_dir.is_absolute():
        run_dir = outputs_root.parent / run_dir
    report = apply_allocation(model, read_allocation(run_dir))
    print(f"Warm start depuis {run_dir.name} : {report.summary()}")

    violations = constraint_violations(model)
    if violations:
        shown = ", ".join(f"{name} ({amount:.4g})" for name, amount in violations[:_MAX_VIOLATIONS_SHOWN])
        more = f" (+{len(violations) - _MAX_VIOLATIONS_SHOWN} autres)" if len(violations) > _MAX_VIOLATIONS_SHOWN else ""
        print(
            f"  ATTENTION : depart INFAISABLE, {len(violations)} contrainte(s) violee(s) : "
            f"{shown}{more}\n"
            f"  HiGHS l'ignorera -- le solve sera aussi lent qu'a froid. Reparez l'allocation "
            f"ou changez de source."
        )
        return False

    print(f"  depart faisable, objectif {objective_value(model):,.2f}")
    return True


def main(outputs_root: Path = OUTPUTS_ROOT, case_study: CaseStudy | str | None = None) -> None:
    case = case_study if isinstance(case_study, CaseStudy) else load(case_study)
    config = load_config(case.config_path)
    dataset = case.build_dataset(config)
    model = case.build_model(dataset, config)
    warm_start = _apply_warm_start(model, config, outputs_root)
    results, duration = solve_with_progress(
        model, config, case_study=case.name, warm_start=warm_start
    )

    output_dir = case.generate_report(
        dataset, config, model, results, duration, outputs_root=outputs_root
    )

    total_revenue = pyo.value(model.objective)
    allocated_plots = sum(1 for index in model.Y if pyo.value(model.Y[index]) > 0.5)
    total_plots = len(dataset.parameters["data_parc"])

    print(f"Total revenue (gross margin, MB_Ha_Cult): {total_revenue:,.2f}")
    print(f"Plots allocated to a crop: {allocated_plots} / {total_plots}")
    print(f"Report written to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_argument(parser)
    main(case_study=parser.parse_args().case_study)
