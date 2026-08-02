"""Guard the reference runs against silent drift.

The calibration of this model is the product of months of investigation, and its headline
figures -- PAD 48.4 % at GAMS parity, 86.9 % of farm types reproduced with the two assumed
deviations -- are quoted in VIGILANCE, in TODO and in the dashboard. Nothing today notices
if a refactor, a config edit or a data change quietly moves them: the unit tests are
deliberately data-free, and `golden_snapshot.py` covers the pipeline and the indicators but
NOT the solve.

This script closes that gap. It reads the expectations declared next to each reference in
`references.yaml` and compares them with what the run folder actually holds. No solve, no
dataset rebuild -- it reads `recap.json`, so it runs in milliseconds and can be a habit.

WHAT THE TOLERANCE IS FOR, AND WHY IT IS NOT ZERO. Three HiGHS seeds on this exact model
give PAD 48.44 / 48.29 / 48.31 and objectives within 0.025 % (VIGILANCE, 2026-07-27): the
arbitrariness of branch-and-bound is worth about 0.15 point of PAD. An exact-match guard
would therefore fail on a re-run that changed nothing. The default 2 % band sits well above
that noise and well below any change worth knowing about.

    python scripts/check_references.py            # all declared references
    python scripts/check_references.py --verbose  # print every metric, not just failures

Exit code 0 when every guarded metric holds, 1 otherwise -- so it fits in a pre-commit hook
or a release check.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.dashboard import loaders, references
from scripts._common import OUTPUTS_ROOT, REFERENCES_PATH


def resolve_metric(recap: dict[str, Any], dotted: str) -> float | None:
    """Value at a dotted path in the recap, or None when any step is missing.

    Missing is distinct from wrong: a run predating a recap block has no value to compare,
    and saying so is more useful than reporting a failure against `None`.
    """
    node: Any = recap
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    try:
        return float(node)
    except (TypeError, ValueError):
        return None


def check_reference(
    reference: references.Reference, run_dir: Path | None
) -> list[dict[str, Any]]:
    """One row per guarded metric: {metric, expected, actual, drift_pct, status}.

    `status` is "ok", "drift" (outside the band), "missing" (the recap has no such value)
    or "no run" (the folder is absent).
    """
    if run_dir is None:
        return [
            {"metric": metric, "expected": expected, "actual": None,
             "drift_pct": None, "status": "no run"}
            for metric, expected in reference.expect.items()
        ]
    try:
        recap = loaders.load_recap(run_dir)
    except (OSError, ValueError):
        recap = {}

    rows = []
    for metric, expected in reference.expect.items():
        actual = resolve_metric(recap, metric)
        if actual is None:
            rows.append({"metric": metric, "expected": expected, "actual": None,
                         "drift_pct": None, "status": "missing"})
            continue
        # Relative drift, so one tolerance serves both a percentage (48.4) and an objective
        # in euros (8.5e7). An expected value of exactly 0 falls back to absolute drift.
        drift = abs(actual - expected) / abs(expected) * 100.0 if expected else abs(actual - expected)
        rows.append({
            "metric": metric, "expected": expected, "actual": actual,
            "drift_pct": drift,
            "status": "ok" if drift <= reference.tolerance_pct else "drift",
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--references", type=Path, default=REFERENCES_PATH)
    parser.add_argument("--outputs", type=Path, default=OUTPUTS_ROOT)
    parser.add_argument("--verbose", action="store_true",
                        help="Print every metric, not just the ones that fail.")
    args = parser.parse_args(argv)

    declared = references.load_references(args.references)
    if not declared:
        print(f"Aucune référence déclarée dans {args.references}.")
        return 1

    resolved = references.resolve(declared, args.outputs)
    failures = 0
    guarded = 0

    for item in resolved:
        reference = item.reference
        if not reference.expect:
            print(f"  {reference.label:<24} (non gardée)")
            continue
        rows = check_reference(reference, item.run_dir)
        guarded += len(rows)
        bad = [row for row in rows if row["status"] != "ok"]
        failures += len(bad)

        state = "OK" if not bad else f"{len(bad)} ÉCART(S)"
        print(f"\n  {reference.label}  ({reference.run}, ±{reference.tolerance_pct:g} %)  -> {state}")
        for row in rows if (args.verbose or bad) else []:
            if row["status"] == "ok" and not args.verbose:
                continue
            actual = "—" if row["actual"] is None else f"{row['actual']:,.3f}"
            drift = "" if row["drift_pct"] is None else f"  (écart {row['drift_pct']:.2f} %)"
            marker = " " if row["status"] == "ok" else "!"
            print(f"    {marker} {row['metric']:<38} attendu {row['expected']:>14,.3f}"
                  f"   obtenu {actual:>14}{drift}   [{row['status']}]")

    print(f"\n{guarded - failures}/{guarded} métriques gardées conformes.")
    if failures:
        print(
            "\nUn écart n'est pas forcément une régression : si le changement est voulu, "
            "mettez à jour `expect:` dans references.yaml ET la ligne correspondante de "
            "docs/04-vigilance.md, pour que le chiffre publié et le chiffre gardé restent les mêmes."
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
