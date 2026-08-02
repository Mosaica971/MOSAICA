"""What separates two runs at their starting configuration, not at their results.

Every run folder carries the exact `config_used.yaml` it was solved with. Two runs of this
model differ in results because they differ in *hypotheses*, and the honest way to read a
gap between, say, the strict-GAMS calibration and the retained one is to look at the four
lines of YAML that separate them -- not to guess from the output.

The config is two very different kinds of thing, and this module keeps them apart:

* **Component lists** (`objectives`, `constraints`, `eligibility_criteria`,
  `categorical_rules`) -- registry entries selected by name, each `{name, enable, args}`.
  What matters here is *which are on* and *with what thresholds*. A component that flips
  from disabled to enabled is the headline; a threshold that moves is the fine print.
* **Scalars** -- everything else (`data.year`, `solver.mip_rel_gap`, `labor.cost_per_hour`,
  the representative-crop mapping...). Compared as a flat dotted-key mapping.

Pure and Streamlit-free so it can be unit-tested without a browser and without `data/`.

ONE THING THIS DOES NOT CLAIM. A configuration diff explains what was *asked* of the two
models, never what the difference *cost*. Two configs can differ on a constraint that never
binds (its shadow price is zero) and be identical in every result; conversely an identical
config solved at a different MIP gap gives different allocations. Read this next to the
results, not instead of them.
"""

from __future__ import annotations

from typing import Any, Iterable

# The config keys that hold registry component lists rather than plain values. Order is the
# order they are displayed in: what the model optimises, then what constrains it, then what
# it is even allowed to consider.
COMPONENT_SECTIONS: tuple[str, ...] = (
    "objectives",
    "constraints",
    "eligibility_criteria",
    "categorical_rules",
)

SECTION_LABELS: dict[str, str] = {
    "objectives": "Objectif",
    "constraints": "Contraintes",
    "eligibility_criteria": "Critères d'éligibilité",
    "categorical_rules": "Règles catégorielles",
}

# Component states, in the order a reader cares about them.
ENABLED = "activé"
DISABLED = "désactivé"
ABSENT = "absent"


def component_key(entry: dict[str, Any], seen: dict[str, int]) -> str:
    """Stable identity of a component entry across two configs.

    `args.label` when the entry carries one -- that is the name the builder gives the Pyomo
    constraint, so it is what a reader recognises -- otherwise the registry `name`. Several
    entries can share a key (three unlabelled `attribute_forbidden` rules, say); the
    occurrence number is appended so the nth of one config is compared with the nth of the
    other. Imperfect by nature: reordering unlabelled rules would mis-pair them. Labelling
    them in `config.yaml` is the fix, and every constraint already is.
    """
    args = entry.get("args") or {}
    base = str(args.get("label") or entry.get("name") or "?")
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base} #{seen[base]}"


def index_components(entries: Iterable[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """One config section as {component key -> entry}, preserving declaration order."""
    seen: dict[str, int] = {}
    return {component_key(entry, seen): entry for entry in (entries or [])}


def _state(entry: dict[str, Any] | None) -> str:
    if entry is None:
        return ABSENT
    return ENABLED if entry.get("enable") else DISABLED


def diff_args(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, tuple]:
    """Argument-by-argument differences between two component entries, as
    {argument -> (left value, right value)}. A missing argument reads as None."""
    left_args = (left or {}).get("args") or {}
    right_args = (right or {}).get("args") or {}
    return {
        key: (left_args.get(key), right_args.get(key))
        for key in sorted(set(left_args) | set(right_args))
        if left_args.get(key) != right_args.get(key)
    }


def diff_components(
    left_config: dict[str, Any],
    right_config: dict[str, Any],
    section: str,
    *,
    changes_only: bool = True,
) -> list[dict[str, Any]]:
    """Component-level diff of one section, as rows ready for a table.

    Each row is {section, component, left, right, args, verdict}. `verdict` names the change
    in the terms that matter for reading a result gap:
      * "activé à droite" / "désactivé à droite" -- the model itself changed;
      * "seuils modifiés"                        -- same rule, different numbers;
      * "identique"                              -- kept only when changes_only is False.
    """
    left_index = index_components(left_config.get(section))
    right_index = index_components(right_config.get(section))

    rows: list[dict[str, Any]] = []
    for key in list(left_index) + [k for k in right_index if k not in left_index]:
        left, right = left_index.get(key), right_index.get(key)
        left_state, right_state = _state(left), _state(right)
        args = diff_args(left, right)

        if left_state != right_state:
            became_active = right_state == ENABLED
            verdict = "activé à droite" if became_active else (
                "désactivé à droite" if left_state == ENABLED else "présence différente"
            )
        elif args and left_state == ENABLED:
            verdict = "seuils modifiés"
        elif args:
            # Both sides disabled: an argument change cannot affect either run.
            verdict = "seuils modifiés (inactif des deux côtés)"
        else:
            verdict = "identique"

        if changes_only and verdict == "identique":
            continue
        rows.append(
            {
                "section": section,
                "component": key,
                "left": left_state,
                "right": right_state,
                "args": args,
                "verdict": verdict,
            }
        )
    return rows


def flatten_scalars(config: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Everything that is not a component list, as a flat {dotted key -> value} mapping.

    Nested dicts recurse; lists are left whole (a list of crop codes reads better as one
    value than as `crop_families.cs.3`).
    """
    flat: dict[str, Any] = {}
    for key, value in (config or {}).items():
        if not prefix and key in COMPONENT_SECTIONS:
            continue
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten_scalars(value, prefix=f"{dotted}."))
        else:
            flat[dotted] = value
    return flat


def diff_scalars(
    left_config: dict[str, Any], right_config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Rows {key, left, right} for every non-component setting whose value differs."""
    left_flat = flatten_scalars(left_config)
    right_flat = flatten_scalars(right_config)
    return [
        {"key": key, "left": left_flat.get(key), "right": right_flat.get(key)}
        for key in sorted(set(left_flat) | set(right_flat))
        if left_flat.get(key) != right_flat.get(key)
    ]


def summarise(left_config: dict[str, Any], right_config: dict[str, Any]) -> dict[str, Any]:
    """Whole diff in one call: {components: {section -> rows}, scalars: rows, headline}.

    `headline` is the short sentence a reader wants first -- which constraints one side
    activates that the other does not -- because in this model that is nearly always the
    explanation of a result gap (the plantain ceiling and the pasture floor between the
    strict-GAMS calibration and the retained one, for instance).
    """
    components = {
        section: diff_components(left_config, right_config, section)
        for section in COMPONENT_SECTIONS
    }
    activated = [
        row["component"]
        for rows in components.values()
        for row in rows
        if row["verdict"] == "activé à droite"
    ]
    deactivated = [
        row["component"]
        for rows in components.values()
        for row in rows
        if row["verdict"] == "désactivé à droite"
    ]
    retuned = [
        row["component"]
        for rows in components.values()
        for row in rows
        if row["verdict"] == "seuils modifiés"
    ]
    return {
        "components": components,
        "scalars": diff_scalars(left_config, right_config),
        "headline": {
            "activated": activated,
            "deactivated": deactivated,
            "retuned": retuned,
        },
    }
