"""Audit a past allocation as the seed of an upcoming run, WITHOUT solving.

WHY. `run_scenarios.py` already audits every seed before using it, but it does so while the
batch runs: one learns the seed is rejected after committing the machine, and the run
restarts cold. When a run has already failed for lack of an incumbent -- HiGHS returning
`maxTimeLimit and no loadable solution` after two hours -- the question "would an existing
seed be accepted, and if not which constraints reject it" must be answered BEFORE paying
for the second attempt. This script answers it in a minute and without a solve.

WHAT IT DOES. It builds the model exactly as the batch would (same scenario overrides, same
dataset), writes each candidate seed's allocation into it, then evaluates every active
constraint. A seed is usable if and only if the list of violations is empty -- the
definition `core/solve/warm_start.py` applies, the point being that HiGHS discards an
infeasible MIP start SILENTLY: without this audit a run looks warm and behaves cold.

    .venv/Scripts/python scripts/audit_warm_start_seed.py \
        --scenarios case_studies/guadeloupe/plan.yaml \
        --run P10_agroecological_bifurcation \
        --seed outputs/p8_transition_agroecologique_f0_nominal \
        --seed outputs/pareto_azote_threshold_1158542

Output: per seed, the number of plots taken over, those the new run's eligibility mask
excludes, and the violated constraints with their magnitude. The verdict is binary; the
detail tells whether a repair is missing or the seed is off-topic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.case_study import add_argument, load
from core.config import apply_overrides, compose_runs, load_batch_spec, load_config
from core.reporting.run_folder import read_allocation
from core.solve.warm_start import apply_allocation, constraint_violations

# Beyond this the list stops being informative: what matters is WHICH constraint families
# block, not enumerating 4 000 per-farm constraints.
_MAX_SHOWN = 20


def _select_run(runs: list[dict], wanted: str) -> dict:
    """The spec's run whose name contains `wanted`, requiring uniqueness.

    Matching is on a substring rather than equality: composed names carry their coordinates
    (`P8__F9__pareto_nitrogen__threshold=...`) and nobody wants to retype them.
    """
    matches = [run for run in runs if wanted in (run.get("name") or "")]
    if not matches:
        available = "\n  ".join(sorted(run.get("name") or "?" for run in runs))
        raise SystemExit(f"No run matches '{wanted}'. Available:\n  {available}")
    if len(matches) > 1:
        found = "\n  ".join(sorted(run.get("name") or "?" for run in matches))
        raise SystemExit(f"'{wanted}' is ambiguous, {len(matches)} runs match:\n  {found}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenarios", type=Path, required=True, help="Batch spec")
    parser.add_argument("--run", required=True, help="Name (or name fragment) of the run to audit")
    parser.add_argument(
        "--seed", type=Path, action="append", required=True,
        help="Run folder to use as a seed. Repeatable: seeds are tried in the given order, "
             "nearest first.",
    )
    parser.add_argument("--config", type=Path, default=None, help="Reference config.yaml")
    add_argument(parser)
    args = parser.parse_args()

    case = load(args.case_study)
    base_config = load_config(args.config or case.config_path)
    spec = load_batch_spec(args.scenarios, base_config)
    run_spec = _select_run(compose_runs(spec), args.run)

    name = run_spec.get("name")
    print(f"Audited run: {name}")
    coordinates = " ".join(
        f"{key}={run_spec[key]}" for key in ("policy", "forcing", "sweep") if run_spec.get(key)
    )
    if coordinates:
        print(f"Coordinates: {coordinates}")

    config = apply_overrides(base_config, run_spec)
    config["run_name"] = name
    print("Building the dataset and the model...", flush=True)
    dataset = case.build_dataset(config)

    usable = []
    for seed_dir in args.seed:
        print(f"\n--- seed: {seed_dir} ---")
        if not seed_dir.exists():
            print("  folder missing -> skipped")
            continue
        allocation = read_allocation(seed_dir)
        if not allocation:
            print("  no readable allocation -> skipped")
            continue

        # The model is rebuilt for every seed: `apply_allocation` writes into `model.Y`, so
        # two seeds evaluated on the same object would contaminate each other.
        model = case.build_model(dataset, config)
        report = apply_allocation(model, allocation)
        print(f"  {len(allocation)} plots read -- {report.summary()}")

        violations = constraint_violations(model)
        if not violations:
            print("  VERDICT: seed USABLE (no constraint violated)")
            usable.append(seed_dir)
            continue

        print(f"  VERDICT: seed REJECTED -- {len(violations)} constraint(s) violated")
        for constraint_name, amount in violations[:_MAX_SHOWN]:
            print(f"    {constraint_name:<60} {amount:.6g}")
        if len(violations) > _MAX_SHOWN:
            print(f"    ... and {len(violations) - _MAX_SHOWN} more")

    print()
    if usable:
        print(f"At least one seed passes: {usable[0]}")
        print("-> launch the batch with --warm-start-from on that folder.")
        return 0
    print("NO seed passes. Launching the run as is would start cold,")
    print("i.e. reproduce the failure. Repair a seed or give up the run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
