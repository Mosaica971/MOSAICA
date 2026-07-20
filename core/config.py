import copy
import itertools
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


# --- Scenario batch overrides -------------------------------------------------
# A batch spec (see scripts/run_scenarios.py + case_studies/guadeloupe/scenarios.yaml)
# describes several runs, each a small set of edits applied on top of the reference
# config.yaml. apply_overrides returns a fresh deep-copied config -- it never mutates
# `base_config`, so runs never leak into one another. Three edit channels:
#   overrides: {dotted.path: value}   scalar / dict / whole-key replacement
#   enable / disable: [token, ...]    flip enable: on entries matched by label or name
#   set_args:  [{label, args}, ...]   shallow-merge args into the entry with that label


def expand_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expand any run carrying a `matrix:` into the cartesian product of its dimensions.

    matrix maps dotted paths to lists of values; the product yields one run per
    combination, each combination folded into that run's `overrides` (matrix wins over a
    statically-listed override of the same path). The run name gets one `__key=value`
    suffix per matrix dimension. Runs without a matrix pass through unchanged.
    """
    expanded: list[dict[str, Any]] = []
    for run in runs:
        matrix = run.get("matrix")
        if not matrix:
            expanded.append(run)
            continue
        keys = list(matrix.keys())
        for combo in itertools.product(*(matrix[k] for k in keys)):
            new_run = copy.deepcopy(run)
            new_run.pop("matrix")
            overrides = dict(new_run.get("overrides") or {})
            suffix = []
            for key, value in zip(keys, combo):
                overrides[key] = value
                suffix.append(f"{key.split('.')[-1]}={value}")
            new_run["overrides"] = overrides
            new_run["name"] = "__".join([run.get("name", "run"), *suffix])
            expanded.append(new_run)
    return expanded


def apply_overrides(base_config: dict[str, Any], run_spec: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base_config)

    for path, value in (run_spec.get("overrides") or {}).items():
        _set_dotted(config, path, value)

    for token in run_spec.get("enable") or []:
        _set_enable(config, token, True)
    for token in run_spec.get("disable") or []:
        _set_enable(config, token, False)

    for patch in run_spec.get("set_args") or []:
        _patch_args(config, patch["label"], patch.get("args") or {})

    # enable_add appends a brand-new entry that does not exist in the base config -- the
    # enable/disable/set_args channels can only touch entries already declared there.
    # `section` says which config list to append to (default: constraints); a scenario
    # adding an eligibility cut passes section: categorical_rules.
    for entry in run_spec.get("enable_add") or []:
        entry = copy.deepcopy(entry)
        section = entry.pop("section", "constraints")
        entry["enable"] = True
        config.setdefault(section, []).append(entry)

    return config


def _set_dotted(config: dict[str, Any], path: str, value: Any) -> None:
    keys = path.split(".")
    node: Any = config
    for key in keys[:-1]:
        node = node.setdefault(key, {})
        if not isinstance(node, dict):
            raise ValueError(
                f"Override path '{path}' traverses non-dict value at '{key}'"
            )
    node[keys[-1]] = value


def _iter_named_entries(config: dict[str, Any]):
    """Yield every {name, ...} dict living in a top-level list (constraints,
    objectives, eligibility_criteria, categorical_rules, ...)."""
    for value in config.values():
        if not isinstance(value, list):
            continue
        for entry in value:
            if isinstance(entry, dict) and "name" in entry:
                yield entry


def _entry_matches(entry: dict[str, Any], token: str) -> bool:
    label = (entry.get("args") or {}).get("label")
    return label == token or entry.get("name") == token


def _set_enable(config: dict[str, Any], token: str, value: bool) -> None:
    matched = [e for e in _iter_named_entries(config) if _entry_matches(e, token)]
    if not matched:
        raise KeyError(f"enable/disable token '{token}' matched no entry (by label or name)")
    for entry in matched:
        entry["enable"] = value


def _patch_args(config: dict[str, Any], label: str, args: dict[str, Any]) -> None:
    matched = [
        e for e in _iter_named_entries(config)
        if (e.get("args") or {}).get("label") == label
    ]
    if not matched:
        raise KeyError(f"set_args label '{label}' matched no entry")
    for entry in matched:
        entry.setdefault("args", {}).update(args)


def resolve_enabled(
    entries: list[dict[str, Any]], registry: dict[str, Callable]
) -> list[tuple[Callable, dict[str, Any]]]:
    resolved = []
    for entry in entries:
        if not entry.get("enable", False):
            continue
        name = entry["name"]
        if name not in registry:
            available = ", ".join(sorted(registry))
            raise KeyError(f"Unknown component '{name}'. Available: {available}")
        resolved.append((registry[name], entry.get("args") or {}))
    return resolved
