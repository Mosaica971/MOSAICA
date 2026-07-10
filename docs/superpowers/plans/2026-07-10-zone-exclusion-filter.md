# Zone Exclusion/Inclusion Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user restrict, via `config.yaml` only, which plots enter the optimization at all — by island, region, farm, or plot id — before the dataset is built.

**Architecture:** A generic `core/data/zone_filter.py::resolve_kept_plots` computes the set of plot ids to keep from an `include`/`exclude` spec in `config.yaml`. `case_studies/guadeloupe/data_pipeline.py::build_dataset` calls it right after `REGION_CODE` is attached to `data_parc`, then filters `data_parc`/`expl_parc`/`bv_parc`/`reg_parc`/`cpt_parc` before any farm-level or eligibility computation runs — so every downstream aggregate is automatically consistent with the filtered universe.

**Tech Stack:** Python, pandas, pytest (existing stack — no new dependencies).

## Global Constraints

- `config.yaml` only — no CLI override (spec non-goal).
- No automatic rescaling of `territory_production_bound` thresholds (spec non-goal) — document the caveat instead.
- `zone_filter` section is optional; absent or all-empty means no filtering (today's behavior unchanged).
- `include`: a plot is kept only if it matches **every** non-empty criterion (AND). `exclude`: a plot is removed if it matches **any** non-empty criterion (OR), applied after `include`.
- Reference spec: `docs/superpowers/specs/2026-07-10-zone-exclusion-filter-design.md`.

---

### Task 1: `core/data/zone_filter.py` — generic filter resolution

**Files:**
- Create: `core/data/zone_filter.py`
- Test: `tests/test_zone_filter.py`

**Interfaces:**
- Produces: `resolve_kept_plots(plot_index: pd.Index, criteria: dict[str, pd.Series], config: dict) -> pd.Index`. `criteria` maps a criterion name (e.g. `"islands"`, `"regions"`, `"farms"`, `"plots"`) to a `pd.Series` aligned to `plot_index` giving the value to compare against the matching `zone_filter.include`/`.exclude` list. Raises `KeyError` for an unknown key inside `include`/`exclude`, `ValueError` if the result would be empty, and emits a `UserWarning` for any listed value that matches nothing in its series.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_zone_filter.py`:

```python
import pandas as pd
import pytest

from core.data.zone_filter import resolve_kept_plots

PLOT_INDEX = pd.Index(["P1", "P2", "P3", "P4"])
CRITERIA = {
    "islands": pd.Series({"P1": 1, "P2": 2, "P3": 1, "P4": 3}),
    "regions": pd.Series({"P1": "R1", "P2": "R1", "P3": "R2", "P4": "R2"}),
    "farms": pd.Series({"P1": "E1", "P2": "E1", "P3": "E2", "P4": "E2"}),
    "plots": pd.Series(PLOT_INDEX, index=PLOT_INDEX),
}


def test_resolve_kept_plots_no_zone_filter_key_returns_full_index():
    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, {})

    assert list(result) == ["P1", "P2", "P3", "P4"]


def test_resolve_kept_plots_empty_lists_return_full_index():
    config = {
        "zone_filter": {
            "include": {"islands": [], "regions": [], "farms": [], "plots": []},
            "exclude": {"islands": [], "regions": [], "farms": [], "plots": []},
        }
    }

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    assert list(result) == ["P1", "P2", "P3", "P4"]


def test_resolve_kept_plots_include_combines_criteria_with_and():
    config = {"zone_filter": {"include": {"islands": [1], "regions": ["R1"]}}}

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    # P1: island 1 AND region R1 -- matches both. P3: island 1 but region R2 -- fails.
    assert list(result) == ["P1"]


def test_resolve_kept_plots_exclude_combines_criteria_with_or():
    config = {"zone_filter": {"exclude": {"islands": [1], "regions": ["R2"]}}}

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    # Removes P1,P3 (island 1) union P3,P4 (region R2) -- only P2 survives.
    assert list(result) == ["P2"]


def test_resolve_kept_plots_exclude_wins_over_include_on_conflict():
    config = {
        "zone_filter": {
            "include": {"farms": ["E1"]},
            "exclude": {"islands": [2]},
        }
    }

    result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    # include keeps P1,P2 (farm E1); exclude then removes P2 (island 2).
    assert list(result) == ["P1"]


def test_resolve_kept_plots_raises_when_result_is_empty():
    config = {"zone_filter": {"include": {"farms": ["E999"]}}}

    with pytest.raises(ValueError, match="zone_filter excludes every plot"):
        resolve_kept_plots(PLOT_INDEX, CRITERIA, config)


def test_resolve_kept_plots_warns_on_unmatched_value_without_changing_result():
    config = {"zone_filter": {"exclude": {"islands": [99]}}}

    with pytest.warns(UserWarning, match="99"):
        result = resolve_kept_plots(PLOT_INDEX, CRITERIA, config)

    assert list(result) == ["P1", "P2", "P3", "P4"]


def test_resolve_kept_plots_raises_keyerror_on_unknown_criterion_key():
    config = {"zone_filter": {"include": {"region": ["R1"]}}}

    with pytest.raises(KeyError):
        resolve_kept_plots(PLOT_INDEX, CRITERIA, config)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_zone_filter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.data.zone_filter'`

- [ ] **Step 3: Write the implementation**

Create `core/data/zone_filter.py`:

```python
import warnings

import pandas as pd


def resolve_kept_plots(
    plot_index: pd.Index,
    criteria: dict[str, pd.Series],
    config: dict,
) -> pd.Index:
    zone_filter = config.get("zone_filter")
    if not zone_filter:
        return plot_index

    include = zone_filter.get("include") or {}
    exclude = zone_filter.get("exclude") or {}
    _check_unknown_keys(include, criteria, "include")
    _check_unknown_keys(exclude, criteria, "exclude")

    include_mask = pd.Series(True, index=plot_index)
    for name, series in criteria.items():
        values = include.get(name) or []
        if not values:
            continue
        include_mask &= series.isin(values)
        _warn_unmatched(name, values, series, "include")

    exclude_mask = pd.Series(False, index=plot_index)
    for name, series in criteria.items():
        values = exclude.get(name) or []
        if not values:
            continue
        exclude_mask |= series.isin(values)
        _warn_unmatched(name, values, series, "exclude")

    kept = plot_index[include_mask & ~exclude_mask]
    if kept.empty:
        raise ValueError(
            "zone_filter excludes every plot -- check config.yaml's zone_filter section"
        )
    return kept


def _check_unknown_keys(spec: dict, criteria: dict, section: str) -> None:
    unknown = set(spec) - set(criteria)
    if unknown:
        available = ", ".join(sorted(criteria))
        raise KeyError(
            f"Unknown zone_filter.{section} key(s) {sorted(unknown)}. Available: {available}"
        )


def _warn_unmatched(name: str, values: list, series: pd.Series, section: str) -> None:
    unmatched = set(values) - set(series.unique())
    if unmatched:
        warnings.warn(
            f"zone_filter.{section}.{name}: value(s) {sorted(unmatched)} match no plot",
            stacklevel=2,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_zone_filter.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add core/data/zone_filter.py tests/test_zone_filter.py
git commit -m "Add config-driven zone include/exclude filter"
```

---

### Task 2: Wire the filter into `build_dataset`

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py:43-106`
- Test: `tests/test_guadeloupe_pipeline.py`

**Interfaces:**
- Consumes: `resolve_kept_plots(plot_index, criteria, config)` from Task 1.
- Produces: `build_dataset` behavior unchanged when `config` has no `zone_filter` key (all existing tests in `tests/test_guadeloupe_pipeline.py` must keep passing unmodified); when `zone_filter` is present, every value in `dataset.parameters` (`data_parc`, `expl_parc`, `bv_parc`, `reg_parc`, `cpt_parc`, and everything derived from them) reflects only the kept plots.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_guadeloupe_pipeline.py` (add `import pytest` is already present):

```python
def test_build_dataset_zone_filter_include_restricts_to_one_island():
    config = {**CONFIG, "zone_filter": {"include": {"islands": [1]}}}

    dataset = build_dataset(config)

    data_parc = dataset.parameters["data_parc"]
    assert len(data_parc) == 8376  # real count of island-1 plots in Data_Parc_Gwad_2017.txt
    assert (data_parc["ILE"] == 1).all()
    # E1's plots (P1,P2,P3) are on island 2 -- must be gone.
    assert "E1" not in dataset.parameters["farm_plots"]
    # Every plot-mapping table must be filtered consistently, not just data_parc/expl_parc.
    assert dataset.parameters["reg_parc"]["plot"].isin(data_parc.index).all()
    assert len(dataset.parameters["reg_parc"]) == len(data_parc)
    assert dataset.parameters["bv_parc"]["plot"].isin(data_parc.index).all()
    assert dataset.parameters["cpt_parc"]["plot"].isin(data_parc.index).all()


def test_build_dataset_zone_filter_exclude_removes_one_farm():
    config = {**CONFIG, "zone_filter": {"exclude": {"farms": ["E1"]}}}

    dataset = build_dataset(config)

    data_parc = dataset.parameters["data_parc"]
    assert len(data_parc) == 24734 - 3  # E1 has exactly 3 plots: P1, P2, P3
    assert "P1" not in data_parc.index
    assert "E1" not in dataset.parameters["expl_parc"]["farm"].values


def test_build_dataset_zone_filter_raises_when_selection_is_empty():
    config = {**CONFIG, "zone_filter": {"include": {"farms": ["NONEXISTENT_FARM"]}}}

    with pytest.raises(ValueError, match="zone_filter excludes every plot"):
        build_dataset(config)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py -v -k zone_filter`
Expected: FAIL — `build_dataset` doesn't accept/apply `zone_filter` yet (either `KeyError`/`AssertionError` since nothing is filtered).

- [ ] **Step 3: Modify `build_dataset`**

In `case_studies/guadeloupe/data_pipeline.py`, add the import:

```python
from core.data.zone_filter import resolve_kept_plots
```

Then reorder lines 81-90 (today: `plot_surface`/`farm_surface_ha`/`farm_plots`/`farm_gfa_surface_ha` computed *before* `REGION_CODE` is attached) so `REGION_CODE` is attached first, the filter runs, and only then are the farm-level aggregates computed. Replace the block currently spanning lines 81-90:

```python
    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)
    farm_plots = expl_parc.groupby("farm")["plot"].apply(list).to_dict()
    farm_gfa_surface_ha = compute_farm_surface_ha(
        plot_surface * data_parc["GFA_PARC"], expl_parc
    )

    data_parc = data_parc.assign(
        REGION_CODE=data_parc.index.map(reg_parc.set_index("plot")["region"])
    )
    data_parc = data_parc.join(data_rpg[["cult_2015", "cult_2016", "cult_2017"]])
```

with:

```python
    data_parc = data_parc.assign(
        REGION_CODE=data_parc.index.map(reg_parc.set_index("plot")["region"])
    )
    data_parc = data_parc.join(data_rpg[["cult_2015", "cult_2016", "cult_2017"]])

    plot_to_farm = expl_parc.set_index("plot")["farm"].reindex(data_parc.index)
    kept_plots = resolve_kept_plots(
        data_parc.index,
        {
            "islands": data_parc["ILE"],
            "regions": data_parc["REGION_CODE"],
            "farms": plot_to_farm,
            "plots": pd.Series(data_parc.index, index=data_parc.index),
        },
        config,
    )
    data_parc = data_parc.loc[kept_plots]
    expl_parc = expl_parc[expl_parc["plot"].isin(kept_plots)]
    bv_parc = bv_parc[bv_parc["plot"].isin(kept_plots)]
    reg_parc = reg_parc[reg_parc["plot"].isin(kept_plots)]
    cpt_parc = cpt_parc[cpt_parc["plot"].isin(kept_plots)]

    plot_surface = data_parc["SURF_HA"]
    farm_surface_ha = compute_farm_surface_ha(plot_surface, expl_parc)
    farm_plots = expl_parc.groupby("farm")["plot"].apply(list).to_dict()
    farm_gfa_surface_ha = compute_farm_surface_ha(
        plot_surface * data_parc["GFA_PARC"], expl_parc
    )
```

- [ ] **Step 4: Run the full pipeline test file to verify everything passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_guadeloupe_pipeline.py -v`
Expected: PASS (all tests, including the 3 new ones and every pre-existing one — pre-existing tests pass `CONFIG` unchanged, which has no `zone_filter` key, so `resolve_kept_plots` returns the full index and behavior is identical to before).

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `./.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (no regressions in `test_guadeloupe_model.py`, `test_main.py`, etc., since they also use the real `config.yaml` with no `zone_filter` key).

- [ ] **Step 6: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py tests/test_guadeloupe_pipeline.py
git commit -m "Wire config-driven zone filter into build_dataset"
```

---

### Task 3: Document the feature and its territory-quota caveat

**Files:**
- Modify: `VIGILANCE.md`
- Modify: `case_studies/guadeloupe/config.yaml`

**Interfaces:**
- Consumes: nothing new (documentation only).
- Produces: nothing consumed by other tasks — this is the last task.

- [ ] **Step 1: Update `VIGILANCE.md`**

In the `## Roadmap` section, change the line:

```markdown
- [ ] **C. Exclusion de zones** (parcelles/exploitations/régions/îles) avant optimisation, pour tests à petite échelle et scénarios de transition locale.
```

to:

```markdown
- [x] **C. Exclusion de zones** (parcelles/exploitations/régions/îles) avant optimisation, pour tests à petite échelle et scénarios de transition locale — voir `zone_filter` dans `config.yaml` (`core/data/zone_filter.py`).
```

Then add a new entry under `## Points ouverts` (after the existing `Mineur — REGION vs REGION_CODE` entry):

```markdown
### Mineur — `zone_filter` ne redimensionne pas les quotas territoriaux
`territory_production_bound` (quotas min/max sur toute la Guadeloupe, dans
`config.yaml`) n'est pas recalculé quand `zone_filter` restreint les parcelles : un
sous-ensemble (ex: une seule île) peut devenir infaisable vis-à-vis de seuils pensés
pour tout le territoire. C'est un choix assumé (voir la section "Non-goals" de
`docs/superpowers/specs/2026-07-10-zone-exclusion-filter-design.md`), pas un bug.
**Prochain fix possible** : si ça devient génant en pratique, désactiver
manuellement (`enable: false`) les `territory_production_bound` concernées dans
`config.yaml` pour les runs à petite échelle.
_Constaté le 2026-07-10._
```

- [ ] **Step 2: Add a commented-out usage example to `config.yaml`**

In `case_studies/guadeloupe/config.yaml`, after the `solver:` block and before `crop_families:`, add:

```yaml
# Optional: restrict the optimization to a subset of plots (island/region/farm/plot),
# for faster small-scale test runs or local policy-transition scenarios. See
# docs/superpowers/specs/2026-07-10-zone-exclusion-filter-design.md. Absent (as here)
# means no restriction -- every plot is in play.
# zone_filter:
#   include:
#     islands: [1]
#   exclude:
#     farms: [E1471]
```

- [ ] **Step 3: Run the full test suite one more time**

Run: `./.venv/Scripts/python.exe -m pytest -v`
Expected: PASS (docs-only change, no behavior touched)

- [ ] **Step 4: Commit**

```bash
git add VIGILANCE.md case_studies/guadeloupe/config.yaml
git commit -m "Document zone_filter in VIGILANCE.md and config.yaml"
```
