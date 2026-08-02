"""Deterministic invariance check for the data pipeline and the reporting layer.

Builds the full real dataset and every indicator block on a real allocation, then
serialises numeric checksums. No MILP is solved, so the result is exactly reproducible:
any difference between two runs is a genuine behaviour change, not solver degeneracy.

Meant as a safety net around refactors. Compare the two modes:

    python scripts/golden_snapshot.py --write   # record the current behaviour
    python scripts/golden_snapshot.py --check   # fail if anything drifted

The reference lands in .golden/snapshot.json, which is gitignored: it is derived from
data/, which stays local. Regenerate it from a known-good revision before starting work.

The allocation used is the representative baseline (decode_baseline_representative_allocation),
which needs no solve. It is not the optimum -- that is irrelevant here, since both sides of
the comparison use the same allocation.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import calibration, indicators
from core.config import load_config
from core.data.dataset import Dataset

from scripts._common import CONFIG_PATH, ROOT

SNAPSHOT_PATH = ROOT / ".golden" / "snapshot.json"

# Enough decimals to catch a real change, few enough to absorb float re-association
# (summing in a different order can move the last bits).
_PRECISION = 6


def _round(value: Any) -> Any:
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return None
    return round(float(value), _PRECISION)


def _summarise_frame(value: pd.DataFrame | pd.Series) -> dict[str, Any]:
    """Shape plus numeric checksums, over numeric columns only (tables mix dtypes)."""
    numeric = value.select_dtypes("number") if isinstance(value, pd.DataFrame) else value
    if isinstance(numeric, pd.DataFrame):
        totals = {str(col): _round(numeric[col].sum()) for col in numeric.columns}
    else:
        totals = {"sum": _round(pd.to_numeric(numeric, errors="coerce").sum())}
    return {"shape": list(getattr(value, "shape", (len(value),))), "totals": totals}


def _snapshot_parameters(dataset: Dataset) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, value in sorted(dataset.parameters.items()):
        if isinstance(value, (pd.DataFrame, pd.Series)):
            out[name] = _summarise_frame(value)
        elif isinstance(value, (list, tuple, set)):
            # eligible_pairs and friends: order-independent identity of the collection.
            # hashlib, not hash(): PYTHONHASHSEED randomises str hashing per process.
            items = sorted(str(item) for item in value)
            digest = hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()[:16]
            out[name] = {"count": len(items), "sha256": digest}
        else:
            out[name] = {"value": _round(value) if isinstance(value, (int, float)) else str(value)}
    return out


def _snapshot_indicators(dataset: Dataset, config: dict[str, Any]) -> dict[str, Any]:
    allocation = indicators.decode_baseline_representative_allocation(dataset, config)
    hours_per_etp = indicators.hours_per_etp_from_config(config)
    cost_per_hour = indicators.labor_cost_per_hour_from_config(config)
    price_shock = (config.get("resilience") or {}).get("price_shock_delta", 0.20)

    def flatten(prefix: str, block: dict[str, Any]) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in block.items():
            if isinstance(value, dict):
                flat.update(flatten(f"{prefix}.{key}", value))
            else:
                flat[f"{prefix}.{key}"] = _round(value)
        return flat

    snapshot = {"allocation_plots": len(allocation), "distinct_crops": int(allocation.nunique())}
    snapshot.update(
        flatten("econ", indicators.compute_economic_totals(
            dataset, allocation, hours_per_etp, cost_per_hour))
    )
    snapshot.update(flatten("env", indicators.compute_environmental_totals(dataset, allocation)))
    snapshot.update(
        flatten("res", indicators.compute_resilience_totals(dataset, allocation, price_shock))
    )
    snapshot.update(flatten("auto", indicators.compute_food_autonomy_totals(dataset, allocation)))

    facts = indicators.compute_facts_table(dataset, allocation, hours_per_etp, cost_per_hour)
    snapshot["facts"] = _summarise_frame(facts)

    # Calibration blocks. The allocation here is the representative baseline, which folds
    # back onto its own observed families, so every PAD is 0 and the confusion matrix is
    # diagonal. That is the point: this checksum guards the round-trip between config's
    # baseline_representative_crops and crop_families.base_group_for. Drift in the
    # arithmetic is caught by tests/test_guadeloupe_reporting_calibration.py instead.
    calib = calibration.evaluate(dataset, allocation, config)
    snapshot.update(flatten("calib", calib.summary()))
    snapshot["calib_pad_by_crop"] = _summarise_frame(calib.pad_by_crop)
    snapshot["calib_pad_by_region"] = _summarise_frame(calib.pad_by_crop_and_region)
    snapshot["calib_pad_by_farm"] = _summarise_frame(calib.pad_by_farm)
    snapshot["calib_confusion"] = _summarise_frame(calib.farm_type_confusion)
    snapshot["calib_field_match"] = _summarise_frame(calib.field_match)
    return snapshot


def _snapshot_model(config: dict[str, Any]) -> dict[str, Any]:
    """Signature of the built (never solved) model on a reduced zone: variable and
    constraint counts, which constraints were registered, and a checksum of the objective's
    linear coefficients. Catches a lost registry import or a mis-wired ModelInputs field,
    neither of which shows up in the indicator checksums.

    Territory quotas are dropped: they are sized for the whole territory and a subset
    cannot satisfy them (see docs/04-vigilance.md).
    """
    import pyomo.environ as pyo
    from pyomo.core.expr import decompose_term

    from case_studies.guadeloupe.model.model import build_model

    zone_config = {
        **config,
        "zone_filter": {"include": {"islands": [2]}},
        "constraints": [
            c for c in config["constraints"] if c["name"] != "territory_production_bound"
        ],
    }
    model = build_model(build_dataset(zone_config), zone_config)
    _ok, terms = decompose_term(model.objective.expr)
    coeffs = sorted((str(var), _round(coeff)) for coeff, var in terms if var is not None)
    return {
        "variables": sum(1 for _ in model.Y),
        "constraint_rows": sum(len(c) for c in model.component_objects(pyo.Constraint)),
        "constraint_names": sorted(c.name for c in model.component_objects(pyo.Constraint)),
        "objective_terms": len(coeffs),
        "objective_sha256": hashlib.sha256(repr(coeffs).encode("utf-8")).hexdigest()[:16],
    }


def build_snapshot(include_model: bool = False) -> dict[str, Any]:
    config = load_config(CONFIG_PATH)
    dataset = build_dataset(config)
    snapshot = {
        "sets": {name: len(value) for name, value in sorted(dataset.sets.items())},
        "scalars": {name: _round(value) for name, value in sorted(dataset.scalars.items())},
        "parameters": _snapshot_parameters(dataset),
        "indicators": _snapshot_indicators(dataset, config),
    }
    if include_model:
        snapshot["model"] = _snapshot_model(config)
    return snapshot


def _flatten_for_diff(node: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(node, dict):
        flat: dict[str, Any] = {}
        for key, value in node.items():
            flat.update(_flatten_for_diff(value, f"{prefix}.{key}" if prefix else str(key)))
        return flat
    return {prefix: node}


def check(reference: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Human-readable differences between two snapshots, empty when identical."""
    old, new = _flatten_for_diff(reference), _flatten_for_diff(current)
    diffs = [f"  MISSING  {key} (was {old[key]!r})" for key in sorted(old.keys() - new.keys())]
    diffs += [f"  NEW      {key} = {new[key]!r}" for key in sorted(new.keys() - old.keys())]
    diffs += [
        f"  CHANGED  {key}: {old[key]!r} -> {new[key]!r}"
        for key in sorted(old.keys() & new.keys())
        if old[key] != new[key]
    ]
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Record the current behaviour.")
    parser.add_argument("--check", action="store_true", help="Fail on any drift.")
    parser.add_argument(
        "--model",
        action="store_true",
        help="Also build the model on a reduced zone (~1 min) and check its signature.",
    )
    args = parser.parse_args(argv)
    if args.write == args.check:
        parser.error("pass exactly one of --write / --check")

    snapshot = build_snapshot(include_model=args.model)

    if args.write:
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
        print(f"wrote {SNAPSHOT_PATH} ({len(_flatten_for_diff(snapshot))} checksums)")
        return 0

    if not SNAPSHOT_PATH.exists():
        print(f"no reference at {SNAPSHOT_PATH}; run --write first", file=sys.stderr)
        return 2
    reference = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if not args.model:
        # Reference may carry a model block we deliberately did not recompute.
        reference.pop("model", None)
    elif "model" not in reference:
        print("reference has no model block; re-run --write --model", file=sys.stderr)
        return 2
    diffs = check(reference, snapshot)
    if diffs:
        print(f"DRIFT: {len(diffs)} difference(s)", file=sys.stderr)
        print("\n".join(diffs[:40]), file=sys.stderr)
        if len(diffs) > 40:
            print(f"  ... and {len(diffs) - 40} more", file=sys.stderr)
        return 1
    print(f"OK ({len(_flatten_for_diff(snapshot))} checksums unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
