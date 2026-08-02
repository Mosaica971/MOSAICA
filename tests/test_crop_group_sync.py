"""Crop groups: that they mean what they say, and that nobody's copy has drifted.

The prospective specs no longer hold a copy at all -- `crop_groups.yaml` is a catalogue
resolved against `config.yaml`'s `crop_families` at load time (`core.config.load_batch_spec`),
so `{group: canne}` cannot diverge from the family it aliases. What remains to guard:

  * `scenarios.yaml` still carries a hand-copied `_crop_groups` block, because its YAML
    anchors live inside one file and never needed a catalogue. That copy CAN drift;
  * every crop code cited anywhere must actually exist. A typo is silent -- the crop simply
    never matches, so a subsidy shock lands on four crops instead of five and the run looks
    fine. `apply_crop_multipliers` and the constraint builders both ignore unknown codes
    rather than complaining.
"""

from pathlib import Path

import pytest

from case_studies.guadeloupe.domain.crop_families import base_group_for
from core.config import expand_group_refs, load_config

CONFIG = Path("case_studies/guadeloupe/config.yaml")
SCENARIOS = Path("case_studies/guadeloupe/scenarios.yaml")
CATALOGUE = Path("case_studies/guadeloupe/crop_groups.yaml")

# Scenario group name -> the config.yaml crop_families key it must mirror. Only the groups
# that genuinely duplicate a config family are listed; a scenario is free to define groups
# of its own (bio_maraichage, vivrier, intensif_canne) that have no config counterpart.
_MIRRORED = {
    "banane_export": "ban_ex",
    "canne": "cs",
    "maraichage": "ma",
    "plantain": "bc",
    "igname": "ig",
    "ananas": "an",
    "arboriculture": "plu",
}


def _groups(path: Path, key: str) -> dict[str, list[str]]:
    return (load_config(path) or {}).get(key) or {}


def _resolved_catalogue() -> dict[str, list[str]]:
    """crop_groups.yaml as the loader sees it: `@refs` expanded against the config families."""
    families = _groups(CONFIG, "crop_families")
    catalogue = load_config(CATALOGUE) or {}
    resolved = expand_group_refs({**families, **catalogue})
    return {name: resolved[name] for name in catalogue}


def test_scenario_crop_groups_match_the_config_families():
    """scenarios.yaml keeps a hand copy -- this is the only thing holding it to the original."""
    families = _groups(CONFIG, "crop_families")
    scenario_groups = _groups(SCENARIOS, "_crop_groups")
    for scenario_name, config_name in _MIRRORED.items():
        if scenario_name not in scenario_groups:
            continue
        assert scenario_groups[scenario_name] == families[config_name], (
            f"scenarios.yaml : le groupe '{scenario_name}' a divergé de "
            f"crop_families.{config_name} dans config.yaml"
        )


def test_catalogue_aliases_resolve_to_the_config_family_they_name():
    """The catalogue's aliases are `["@family"]`, so they cannot drift -- but they could name
    the WRONG family, which no amount of indirection would catch."""
    families = _groups(CONFIG, "crop_families")
    catalogue = _resolved_catalogue()
    for alias, family in _MIRRORED.items():
        if alias in catalogue:
            assert catalogue[alias] == families[family], (
                f"crop_groups.yaml : l'alias '{alias}' ne pointe pas sur "
                f"crop_families.{family}"
            )


@pytest.mark.parametrize("spec_path", [CONFIG, SCENARIOS])
def test_every_declared_crop_code_belongs_to_a_known_family(spec_path):
    key = "crop_families" if spec_path == CONFIG else "_crop_groups"
    for group_name, crops in _groups(spec_path, key).items():
        for crop in crops:
            try:
                base_group_for(crop)
            except KeyError:  # pragma: no cover - the assertion carries the message
                pytest.fail(f"{spec_path.name}: '{crop}' ({group_name}) n'a pas de famille connue")


def test_every_catalogue_crop_code_belongs_to_a_known_family():
    for group_name, crops in _resolved_catalogue().items():
        for crop in crops:
            try:
                base_group_for(crop)
            except KeyError:  # pragma: no cover - the assertion carries the message
                pytest.fail(f"crop_groups.yaml: '{crop}' ({group_name}) n'a pas de famille connue")


def test_scenario_crop_codes_exist_in_the_crop_universe():
    """Codes referenced by a scenario must exist in CULT_2017.set, otherwise the group is
    quietly narrower than written."""
    from case_studies.guadeloupe.pipeline.data_pipeline import SETS_DIR
    from core.data.readers import read_flat_set

    universe = set(read_flat_set(SETS_DIR / "CULT_2017.set"))
    checked = {
        "scenarios.yaml": _groups(SCENARIOS, "_crop_groups"),
        "crop_groups.yaml": _resolved_catalogue(),
    }
    for origin, groups in checked.items():
        for group_name, crops in groups.items():
            unknown = [c for c in crops if c not in universe]
            assert not unknown, f"{origin} / {group_name}: codes inconnus {unknown}"
