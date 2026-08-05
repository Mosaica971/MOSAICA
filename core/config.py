import copy
import itertools
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


# --- Crop groups shared across spec files -------------------------------------
# YAML anchors do not cross files. As long as policies and forcings lived in one file they
# could share a `_crop_groups` block; splitting them would have meant copying every crop list
# into both, and copies drift. A NAMED CATALOGUE does the same job without the copy: a spec
# writes `crops: {group: canne}` and the loader substitutes the list.
#
# The catalogue is `crop_families` from the case-study config PLUS whatever the spec's own
# crop_groups file adds, the latter winning on a name collision. So a group the MODEL already
# knows (cs, ban_ex, ma...) is never restated in a scenario file -- which removes the
# hand-synchronisation that the old `_crop_groups` header warned about.

GROUP_KEY = "group"
GROUP_REF = "@"


def expand_group_refs(groups: dict[str, Any]) -> dict[str, list[str]]:
    """Resolve `@other_group` members so the catalogue can build groups out of groups.

    ``vivrier: ["@plantain", "@igname", ME]`` becomes the flat union. Duplicates are dropped
    (first occurrence wins) and a reference cycle raises instead of recursing forever.
    """
    resolved: dict[str, list[str]] = {}

    def resolve(name: str, seen: tuple[str, ...]) -> list[str]:
        if name in resolved:
            return resolved[name]
        if name in seen:
            raise ValueError(f"Crop group reference cycle: {' -> '.join([*seen, name])}")
        if name not in groups:
            available = ", ".join(sorted(groups)) or "(none)"
            raise KeyError(f"Unknown crop group '@{name}'. Available: {available}")
        members: list[str] = []
        for member in groups[name] or []:
            if isinstance(member, str) and member.startswith(GROUP_REF):
                members.extend(resolve(member[len(GROUP_REF):], (*seen, name)))
            else:
                members.append(member)
        resolved[name] = list(dict.fromkeys(members))
        return resolved[name]

    for name in groups:
        resolve(name, ())
    return resolved


def resolve_crop_groups(node: Any, groups: dict[str, list[str]]) -> Any:
    """Copy of `node` with every ``{group: <name>}`` replaced by that group's crop list.

    Matched on the EXACT one-key dict, which is narrow on purpose: the args of
    `territory_production_bound` already carry a key literally named `groups`, and a looser
    match would swallow it.
    """
    if isinstance(node, dict):
        if set(node) == {GROUP_KEY} and isinstance(node[GROUP_KEY], str):
            name = node[GROUP_KEY]
            if name not in groups:
                available = ", ".join(sorted(groups)) or "(none)"
                raise KeyError(f"Unknown crop group '{name}'. Available: {available}")
            return list(groups[name])
        return {key: resolve_crop_groups(value, groups) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve_crop_groups(item, groups) for item in node]
    return node


# Sections a batch spec may pull in from another file, and which are concatenated rather
# than replaced when both the including file and the included one declare them.
_INCLUDABLE_SECTIONS = ("policies", "forcings", "sweeps", "runs")


def load_batch_spec(
    path: str | Path, base_config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Load a batch spec, following its `include:` and resolving `{group: ...}` references.

    A spec may now be spread over several files -- one catalogue of policies, one of
    forcings, one of Pareto sweeps -- and assembled by a small plan file:

        include:
          crop_groups: crop_groups.yaml
          policies:    scenarios_politiques.yaml
          forcings:    scenarios_forcages.yaml
          sweeps:      scenarios_pareto.yaml

    Paths are relative to the including file. Each value is one path or a list of paths; the
    entries found are APPENDED to whatever the including file declares inline, so a plan can
    add a one-off policy without touching the catalogue. Includes are not recursive -- a spec
    that includes a spec that includes a spec is a dependency graph nobody wants to debug at
    3 a.m. -- with ONE exception: a catalogue's own `crop_groups` include is honoured. Without
    it a catalogue could not be run on its own (`--scenarios scenarios_politiques.yaml
    --policies P8`), which is how a single policy is re-run.

    Returns a plain spec dict, ready for `compose_runs` -- every `{group: x}` already
    replaced by a crop list, so nothing downstream needs to know groups exist.
    """
    path = Path(path)
    spec = load_config(path) or {}
    includes = spec.pop("include", None) or {}

    # Lowest to highest precedence: the model's own families, then whatever a catalogue
    # brings, then what the including file declares. A plan can thus override a group for
    # one batch without editing the catalogue.
    groups: dict[str, Any] = dict((base_config or {}).get("crop_families") or {})
    inherited: dict[str, Any] = {}
    own: dict[str, Any] = {}
    for group_path in _include_paths(includes.get("crop_groups"), path.parent):
        own.update(load_config(group_path) or {})

    for section in _INCLUDABLE_SECTIONS:
        entries = list(spec.get(section) or [])
        for section_path in _include_paths(includes.get(section), path.parent):
            document = load_config(section_path) or {}
            # A catalogue may be written as `policies: [...]` or as a bare top-level list.
            found = document if isinstance(document, list) else document.get(section)
            if found is None:
                raise KeyError(
                    f"{section_path} was included as '{section}' but declares no such key"
                )
            entries.extend(found)
            if isinstance(document, dict):
                nested = (document.get("include") or {}).get("crop_groups")
                for group_path in _include_paths(nested, section_path.parent):
                    inherited.update(load_config(group_path) or {})
        if entries:
            spec[section] = entries

    groups.update(inherited)
    groups.update(own)

    unknown = set(includes) - {"crop_groups", *_INCLUDABLE_SECTIONS}
    if unknown:
        raise KeyError(
            f"{path.name}: cannot include section(s) {', '.join(sorted(unknown))}. "
            f"Includable: crop_groups, {', '.join(_INCLUDABLE_SECTIONS)}"
        )

    return resolve_crop_groups(spec, expand_group_refs(groups))


def _include_paths(value: Any, base_dir: Path) -> list[Path]:
    if not value:
        return []
    paths = [value] if isinstance(value, str) else list(value)
    return [base_dir / p for p in paths]


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

    A matrix key is either a dotted config path (folded into `overrides`) or, written as
    ``args:<label>.<argument>``, one ARGUMENT of the constraint carrying that label (folded
    into `set_args`). The second form is what an epsilon-constraint sweep needs: tracing the
    trade-off between margin and, say, the nitrogen ceiling means varying that ceiling's
    `threshold`, which lives in a constraint's args and not at any dotted path. Without it a
    Pareto front had to be written as N hand-copied scenarios.

    The product yields one run per combination; the run name gets one `__key=value` suffix
    per dimension, and the combination itself is recorded on the run as `matrix_values` so
    later steps (`order_sweep_points`) can read what was swept without parsing the name back.
    Runs without a matrix pass through unchanged.
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
            new_run["matrix_values"] = dict(zip(keys, combo))
            overrides = dict(new_run.get("overrides") or {})
            set_args = list(new_run.get("set_args") or [])
            suffix = []
            for key, value in zip(keys, combo):
                label, argument = _parse_args_key(key)
                if label is None:
                    overrides[key] = value
                else:
                    # Appended last so the swept value wins over a statically-listed one,
                    # matching how a matrix override wins over a static override.
                    set_args.append({"label": label, "args": {argument: value}})
                suffix.append(f"{key.split('.')[-1]}={value}")
            if overrides:
                new_run["overrides"] = overrides
            if set_args:
                new_run["set_args"] = set_args
            new_run["name"] = "__".join([run.get("name", "run"), *suffix])
            expanded.append(new_run)
    return expanded


# --- Ordering a sweep so its points can warm-start one another ----------------
# A Pareto front is N solves of the same model under N settings of one bound, and consecutive
# points sit very close together -- exactly the situation a warm start is for. But a seed is
# only usable if it is FEASIBLE for the run it seeds, and that holds in one direction only:
#
#   sense: le (a ceiling)   feasible at threshold T  =>  feasible at every T' >= T
#   sense: ge (a floor)     feasible at threshold T  =>  feasible at every T' <= T
#
# Both read "solve the TIGHTEST point first, then walk towards the loosest". Run in the
# natural reading order of the YAML (100 % down to 55 %) every seed is infeasible and the
# whole chain silently degrades to seven cold solves -- HiGHS discards an infeasible MIP start
# without saying so. Hence this reordering: it is the difference between the chain working and
# the chain looking like it works.
#
# The tightest point still solves cold. That is unavoidable -- nothing precedes it -- and it is
# also the slowest of the seven, so the win is 6 warm out of 7 rather than 7 out of 7.

# Arguments that ARE the level of the bound, so that ordering them orders feasibility. The
# allowlist is the point: `scale` also lives in a bounded constraint's args and multiplies the
# indicator, which INVERTS the direction -- inferring from `sense` alone would then order the
# sweep exactly backwards, which is worse than not chaining at all.
_BOUND_LEVEL_ARGUMENTS = frozenset(
    {"threshold", "threshold_per_ha", "share", "min_share", "max_share"}
)


def order_sweep_points(
    runs: list[dict[str, Any]], base_config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Reorder the points of each sweep tightest-first, so each solve can seed the next.

    Only contiguous runs sharing the same (policy, forcing, sweep) are touched, and only
    when the chain is provably valid:

      * the sweep varies exactly ONE dimension (a 2-D matrix has no single tightening axis);
      * that dimension is an `args:<label>.<argument>` key whose argument is the level of a
        bound (see `_BOUND_LEVEL_ARGUMENTS`);
      * the constraint carrying that label declares a `sense`, and every swept value is a
        number.

    Anything else is left in the order it was written. Reordering is a heuristic on which
    correctness does not depend -- a wrong order costs speed, never a wrong answer, because
    every seed is audited against the model before it is used.
    """
    senses = _bound_senses(base_config)
    ordered: list[dict[str, Any]] = []
    for _, group in itertools.groupby(runs, key=_sweep_key):
        block = list(group)
        ordered.extend(_sorted_sweep_block(block, senses))
    return ordered


def _sweep_key(run: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (run.get("policy"), run.get("forcing"), run.get("sweep"))


def _bound_senses(base_config: dict[str, Any]) -> dict[str, str]:
    """label -> `sense`, for every config entry that declares one."""
    return {
        (entry.get("args") or {}).get("label"): (entry.get("args") or {}).get("sense")
        for entry in _iter_named_entries(base_config)
        if (entry.get("args") or {}).get("label") and (entry.get("args") or {}).get("sense")
    }


def _sorted_sweep_block(
    block: list[dict[str, Any]], senses: dict[str, str]
) -> list[dict[str, Any]]:
    if len(block) < 2 or not block[0].get("sweep"):
        return block

    dimensions = {key for run in block for key in (run.get("matrix_values") or {})}
    if len(dimensions) != 1:
        return block
    key = dimensions.pop()

    label, argument = _parse_args_key(key)
    if label is None or argument not in _BOUND_LEVEL_ARGUMENTS:
        return block
    sense = senses.get(label)
    if sense not in ("le", "ge"):
        return block

    values = [(run.get("matrix_values") or {}).get(key) for run in block]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return block

    # A ceiling loosens as it rises, a floor loosens as it falls. Tightest first, either way.
    return sorted(block, key=lambda run: run["matrix_values"][key], reverse=(sense == "ge"))


_ARGS_PREFIX = "args:"


def _parse_args_key(key: str) -> tuple[str | None, str]:
    """('label', 'argument') for an ``args:<label>.<argument>`` matrix key, else (None, key)."""
    if not key.startswith(_ARGS_PREFIX):
        return None, key
    remainder = key[len(_ARGS_PREFIX):]
    label, separator, argument = remainder.partition(".")
    if not separator or not label or not argument:
        raise ValueError(
            f"matrix key {key!r}: expected 'args:<label>.<argument>', e.g. "
            f"'args:plafond_azote.threshold'"
        )
    return label, argument


# --- Composing two run specs (policy x forcing) -------------------------------
# A prospective batch is a small set of POLICY specs (what a government decides) crossed
# with a small set of FORCING specs (what the climate and the markets do to it). Both are
# ordinary run specs, so composing them is a merge -- but a naive dict update would lose
# half of each: two specs that both shock economics write the same dotted path, and the
# second would silently drop the first's multipliers.


def merge_run_specs(base: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """Merge `other` on top of `base`, keeping what stacks rather than replacing it.

    * `overrides`: when both specs set the same dotted path AND both values are lists, the
      lists are concatenated -- which is exactly the semantics the economic_overrides
      multiplier lists need (entries stack when crop lists overlap). Anything else is a
      replacement, `other` winning.
    * `enable` / `disable` / `set_args` / `enable_add`: concatenated, `other`'s entries last.
      For set_args that yields last-wins per argument key, since apply_overrides merges each
      patch in order.
    * `matrix`: merged key by key, `other` winning -- this is how a Pareto sweep composes
      with a policy. The product is taken later, by expand_runs, on the merged run.

    One asymmetry to know about: apply_overrides always applies `enable` before `disable`,
    so a token disabled by either spec stays disabled whatever the other says. A forcing
    that must re-enable something a policy switched off cannot do it this way -- express it
    as a fresh entry through enable_add instead.
    """
    merged = copy.deepcopy(base)

    overrides = dict(merged.get("overrides") or {})
    for path, value in (other.get("overrides") or {}).items():
        existing = overrides.get(path)
        if isinstance(existing, list) and isinstance(value, list):
            overrides[path] = copy.deepcopy(existing) + copy.deepcopy(value)
        else:
            overrides[path] = copy.deepcopy(value)
    if overrides:
        merged["overrides"] = overrides

    for channel in ("enable", "disable", "set_args", "enable_add"):
        combined = list(merged.get(channel) or []) + copy.deepcopy(list(other.get(channel) or []))
        if combined:
            merged[channel] = combined

    matrix = dict(merged.get("matrix") or {})
    matrix.update(copy.deepcopy(other.get("matrix") or {}))
    if matrix:
        merged["matrix"] = matrix

    return merged


def compose_runs(
    spec: dict[str, Any],
    *,
    cross: bool = False,
    policies: list[str] | None = None,
    forcings: list[str] | None = None,
    sweeps: bool = True,
) -> list[dict[str, Any]]:
    """Turn a batch spec into the list of runs to solve. Three forms, checked in order.

    `scenarios:` -- a PLAN, and the form to write new work in. It names, per policy, exactly
    which forcings it is put through and which Pareto sweeps are traced under it, so the
    batch is what was asked for rather than a full product minus what you remembered to
    exclude. See `_compose_plan` for the entry grammar.

    `runs:` -- a flat list, passed straight through with its matrices expanded.

    `policies:` + `forcings:` without a plan -- the legacy staged form: policies alone by
    default, every pair under `cross=True`. Kept because a catalogue file is a valid spec on
    its own, which is what makes `--policies P8 --forcings F9` work against the catalogues
    directly, with no plan in the way.

    `policies` / `forcings` restrict the batch to named subsets, for re-running one cell.
    `sweeps=False` drops every Pareto sweep -- a front is seven solves, and staging a batch
    without them is the common case.

    `cross=True` OVERRIDES a plan rather than being ignored by it: it means "never mind what
    is planned, take the whole product", which is what a completeness check wants (and what
    someone typing --cross means). A plan is a curated subset; asking for the product is
    asking to leave the curation aside.
    """
    if spec.get("scenarios") and not cross:
        return _compose_plan(spec, policies=policies, forcings=forcings, sweeps=sweeps)

    if spec.get("runs"):
        return expand_runs(spec["runs"])

    # A sweep catalogue with no policy to attach to is still runnable: the fronts are then
    # traced against the reference config itself, which is what tracing a front on the
    # current model means and how scenarios_pareto.yaml was used before plans existed. Each
    # run is still tagged with its `sweep`, so a standalone front gets the same tightest-first
    # ordering and the same point-to-point warm-start chain as a planned one.
    if spec.get("sweeps") and not spec.get("policies"):
        standalone = []
        for sweep in spec["sweeps"]:
            run = copy.deepcopy(sweep)
            run["sweep"] = sweep.get("name")
            standalone.append(run)
        return expand_runs(standalone)

    policy_specs = _select_named(spec.get("policies") or [], policies, "policy")
    forcing_specs = _select_named(spec.get("forcings") or [], forcings, "forcing")

    if not cross:
        return expand_runs(policy_specs)
    if not forcing_specs:
        raise ValueError("cross=True but the spec declares no forcings")

    composed: list[dict[str, Any]] = []
    for policy in policy_specs:
        for forcing in forcing_specs:
            composed.append(_compose_one(policy, forcing, None))
    return expand_runs(composed)


def _compose_one(
    policy: dict[str, Any],
    forcing: dict[str, Any] | None,
    sweep: dict[str, Any] | None,
) -> dict[str, Any]:
    """One run out of up to three specs: what is decided, what is imposed, what is swept.

    The three coordinates are carried on the run (and from there into its recap) so the grid
    can be reassembled by GROUPING rather than by splitting the name on "__" -- which breaks
    on the first scenario name containing the separator, and every sweep name contains one.
    """
    run = copy.deepcopy(policy)
    parts = [policy.get("name", "policy")]
    for other in (forcing, sweep):
        if other is not None:
            run = merge_run_specs(run, other)
            parts.append(other.get("name", "?"))
    run["name"] = "__".join(parts)
    run["description"] = " | ".join(
        part
        for part in (
            policy.get("description"),
            forcing.get("description") if forcing else None,
            sweep.get("description") if sweep else None,
        )
        if part
    )
    run["policy"] = policy.get("name")
    run["forcing"] = forcing.get("name") if forcing else None
    run["sweep"] = sweep.get("name") if sweep else None
    return run


def _compose_plan(
    spec: dict[str, Any],
    *,
    policies: list[str] | None,
    forcings: list[str] | None,
    sweeps: bool,
) -> list[dict[str, Any]]:
    """Expand a `scenarios:` plan into runs.

    Each key is a policy name from the catalogue; its value says what that policy is put
    through. Four equivalent ways to write a cell, from terse to explicit::

        P1_deregulation_totale:                      # the policy alone, unforced
        P4_statu_quo: [F0_nominal, F9_crise]         # shorthand for `forcings:`
        P5_austerite: {forcings: "*"}                # every forcing in the catalogue
        P8_transition:
          forcings: [F0_nominal]
          sweeps:
            - pareto_azote                           # front traced on the policy alone
            - {name: pareto_azote, forcings: [F9_crise]}   # ... and again under a shock

    A sweep is deliberately NOT crossed with the cell's forcings by default: a front is one
    solve per point, and multiplying it by a forcing list is how an afternoon becomes a week.
    Naming it a forcing explicitly is the way to pay for that.
    """
    policy_by_name = {entry.get("name"): entry for entry in spec.get("policies") or []}
    forcing_by_name = {entry.get("name"): entry for entry in spec.get("forcings") or []}
    sweep_by_name = {entry.get("name"): entry for entry in spec.get("sweeps") or []}

    plan = spec["scenarios"]
    if not isinstance(plan, dict):
        raise ValueError("`scenarios:` must be a mapping of policy name -> what it goes through")

    wanted_policies = _select_named(
        [{"name": name} for name in plan], policies, "policy"
    )
    composed: list[dict[str, Any]] = []
    for stub in wanted_policies:
        policy_name = stub["name"]
        if policy_name not in policy_by_name:
            available = ", ".join(sorted(n for n in policy_by_name if n)) or "(none)"
            raise KeyError(
                f"`scenarios:` names policy '{policy_name}', which no catalogue declares. "
                f"Available: {available}"
            )
        policy = policy_by_name[policy_name]
        entry = _normalise_plan_entry(plan[policy_name], policy_name)

        cell_forcings = _plan_forcings(entry.get("forcings"), forcing_by_name, policy_name)
        if forcings is not None:
            cell_forcings = [name for name in cell_forcings if name in forcings]
        if not cell_forcings:
            # An unforced cell is a run in its own right, not an empty one -- it is the
            # policy's nominal result, and the one every forced cell is read against.
            if forcings is None:
                composed.append(_compose_one(policy, None, None))
        for name in cell_forcings:
            composed.append(_compose_one(policy, forcing_by_name[name], None))

        if not sweeps:
            continue
        for raw in entry.get("sweeps") or []:
            sweep_name, sweep_forcings = _normalise_sweep_entry(raw, policy_name)
            if sweep_name not in sweep_by_name:
                available = ", ".join(sorted(n for n in sweep_by_name if n)) or "(none)"
                raise KeyError(
                    f"{policy_name}: unknown sweep '{sweep_name}'. Available: {available}"
                )
            sweep = sweep_by_name[sweep_name]
            names = _plan_forcings(sweep_forcings, forcing_by_name, policy_name)
            if forcings is not None:
                names = [name for name in names if name in forcings]
                if not names:
                    continue
            if not names:
                composed.append(_compose_one(policy, None, sweep))
            for name in names:
                composed.append(_compose_one(policy, forcing_by_name[name], sweep))

    return expand_runs(composed)


def _normalise_plan_entry(value: Any, policy_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        return {"forcings": [value]}
    if isinstance(value, list):
        return {"forcings": value}
    if isinstance(value, dict):
        unknown = set(value) - {"forcings", "sweeps"}
        if unknown:
            raise KeyError(
                f"{policy_name}: unknown plan key(s) {', '.join(sorted(unknown))}. "
                f"A cell accepts `forcings:` and `sweeps:`."
            )
        return value
    raise ValueError(f"{policy_name}: cannot read plan entry {value!r}")


def _normalise_sweep_entry(value: Any, policy_name: str) -> tuple[str, Any]:
    if isinstance(value, str):
        return value, None
    if isinstance(value, dict) and "name" in value:
        return value["name"], value.get("forcings")
    raise ValueError(
        f"{policy_name}: a sweep is a name or {{name: ..., forcings: [...]}}, got {value!r}"
    )


def _plan_forcings(
    value: Any, forcing_by_name: dict[str, Any], policy_name: str
) -> list[str]:
    """Forcing names a cell asks for. `"*"` means the whole catalogue; absent means none."""
    if value is None:
        return []
    names = list(forcing_by_name) if value == "*" else list(value)
    missing = [name for name in names if name not in forcing_by_name]
    if missing:
        available = ", ".join(sorted(n for n in forcing_by_name if n)) or "(none)"
        raise KeyError(
            f"{policy_name}: unknown forcing(s) {', '.join(missing)}. Available: {available}"
        )
    return names


def _select_named(
    entries: list[dict[str, Any]], wanted: list[str] | None, kind: str
) -> list[dict[str, Any]]:
    if not wanted:
        return entries
    by_name = {entry.get("name"): entry for entry in entries}
    missing = [name for name in wanted if name not in by_name]
    if missing:
        available = ", ".join(sorted(n for n in by_name if n)) or "(none)"
        raise KeyError(f"Unknown {kind} name(s): {', '.join(missing)}. Available: {available}")
    return [by_name[name] for name in wanted]


def apply_overrides(base_config: dict[str, Any], run_spec: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base_config)

    for path, value in (run_spec.get("overrides") or {}).items():
        _set_dotted(config, path, value)

    # enable_add appends a brand-new entry that does not exist in the base config; the
    # enable/disable/set_args channels can only touch entries ALREADY declared. It therefore
    # runs FIRST, so that what one spec adds another can still patch -- which is exactly what
    # a Pareto sweep needs: `budget_subventions` is posed by the policy's enable_add, and the
    # front's `matrix: {args:budget_subventions.threshold: [...]}` becomes a set_args on it.
    # Patch-then-add would raise "set_args label matched no entry" on every point.
    # `section` says which config list to append to (default: constraints); a scenario
    # adding an eligibility cut passes section: categorical_rules.
    for entry in run_spec.get("enable_add") or []:
        entry = copy.deepcopy(entry)
        section = entry.pop("section", "constraints")
        entry["enable"] = True
        config.setdefault(section, []).append(entry)

    for token in run_spec.get("enable") or []:
        _set_enable(config, token, True)
    for token in run_spec.get("disable") or []:
        _set_enable(config, token, False)

    for patch in run_spec.get("set_args") or []:
        _patch_args(config, patch["label"], patch.get("args") or {})

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


# Which constraint builders carry an ABSOLUTE territorial quantity, and under which argument.
# Ratios (crop_share_bound.share, farm_area_share_max.max_share, baseline_inertia_min
# .min_share), per-farm budgets (farm_labor_hours_max.slack) and per-hectare limits
# (zone_indicator_bound.threshold_per_ha) are deliberately absent: they are already
# scale-free, and multiplying them would change what the scenario says.
_TERRITORIAL_THRESHOLDS: dict[str, tuple[str, ...]] = {
    "territory_production_bound": ("threshold",),
    "territory_indicator_bound": ("threshold",),
    "zone_indicator_bound": ("threshold", "thresholds"),
}


def scale_territorial_bounds(config: dict[str, Any], factor: float) -> dict[str, Any]:
    """Return a copy of `config` with every absolute territorial threshold multiplied.

    A `zone_filter` keeps a slice of the territory but leaves the territorial constraints
    stated for the whole of it, which is why a one-island test run is infeasible on contact:
    the 6 096 ha pasture floor cannot be met by Marie-Galante alone. Scaling the thresholds
    by the retained share of surface is what makes a reduced run a miniature of the real one
    rather than an impossible one.

    Deliberately opt-in (`zone_filter.scale_territorial_bounds: true`): a threshold is a
    policy statement, and rewriting one silently would change what a run means.
    """
    scaled = copy.deepcopy(config)
    for entry in _iter_named_entries(scaled):
        arguments = _TERRITORIAL_THRESHOLDS.get(entry.get("name"))
        if not arguments:
            continue
        args = entry.get("args") or {}
        for argument in arguments:
            value = args.get(argument)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                args[argument] = value * factor
            elif isinstance(value, dict):  # zone_indicator_bound's per-zone thresholds
                args[argument] = {k: v * factor for k, v in value.items()}
    return scaled


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
