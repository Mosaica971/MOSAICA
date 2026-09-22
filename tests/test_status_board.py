"""The status board must stay in step with the code it describes.

Two of its four tables are declarations (the indicator catalogue, the roadmap); these tests
are what keeps them from silently falling behind. Data-free except where noted.
"""

from pathlib import Path

import pandas as pd
import pytest

from apps.dashboard.comparison import INDICATOR_LABELS
from case_studies.guadeloupe.reporting import status
from core.config import load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "case_studies" / "guadeloupe" / "config.yaml"


def test_every_dashboard_indicator_is_in_the_catalogue():
    _, catalog = status.load_indicator_catalog()
    missing = set(INDICATOR_LABELS) - set(catalog["key"])
    assert not missing, f"add to status/indicator_catalog.yaml: {sorted(missing)}"


def test_catalogue_entries_are_well_formed():
    levels, catalog = status.load_indicator_catalog()
    assert catalog["key"].is_unique
    assert set(catalog["class"]) <= set(status.INDICATOR_CLASSES)
    for _, entry in catalog.iterrows():
        unknown = set(entry["reported"]) - set(levels)
        assert not unknown, f"{entry['key']}: unknown levels {unknown}"
        assert "territory" in entry["reported"], f"{entry['key']} is not reported at all"


def test_level_cells_follow_the_indicator_class():
    levels = ["territory", "farm", "crop"]
    catalog = pd.DataFrame(
        [
            {"key": "a", "label": "A", "family": "f", "class": "additive", "reported": ["territory"]},
            {"key": "n", "label": "N", "family": "f", "class": "non_additive", "reported": ["territory"]},
            {"key": "o", "label": "O", "family": "f", "class": "observed", "reported": ["territory"]},
            {"key": "t", "label": "T", "family": "f", "class": "territorial", "reported": ["territory"]},
        ]
    )
    matrix = status.indicator_level_matrix(levels, catalog)
    assert matrix.loc["a", "farm"] == status.COMPUTABLE
    assert matrix.loc["n", "farm"] == status.NEEDS_DEFINITION
    assert matrix.loc["o", "crop"] == status.NOT_APPLICABLE
    assert matrix.loc["o", "farm"] == status.COMPUTABLE
    assert matrix.loc["t", "farm"] == status.NOT_APPLICABLE
    assert (matrix["territory"] == status.REPORTED).all()


def test_roadmap_items_have_a_known_status_and_existing_specs():
    roadmap = status.roadmap_table()
    assert roadmap["id"].is_unique
    assert set(roadmap["status"]) <= set(status.ROADMAP_STATUSES)
    for spec in roadmap["spec"]:
        if spec:
            assert (ROOT / spec).exists(), f"roadmap cites a missing spec: {spec}"


def test_every_parameter_choice_matches_the_config():
    table = status.parameter_table(load_config(CONFIG_PATH))
    bad = table[~table["check"].isin(["ok", "-"])]
    assert bad.empty, bad[["parameter", "retained", "in_config", "check"]].to_string()


def test_config_paths_resolve_labels_names_and_positions():
    config = {
        "constraints": [{"name": "x", "args": {"label": "cap", "threshold": 3}}],
        "objectives": [{"name": "obj", "enable": True}],
        "rules": [{"args": {"conditions": [{"column": "RISK"}]}}],
    }
    assert status.resolve_config_path(config, "constraints[label=cap].args.threshold") == 3
    assert status.resolve_config_path(config, "objectives[name=obj].enable") is True
    assert status.resolve_config_path(config, "rules[0].args.conditions[0].column") == "RISK"
    with pytest.raises(KeyError):
        status.resolve_config_path(config, "constraints[label=nope].args")


def test_constraint_table_covers_every_config_entry():
    config = load_config(CONFIG_PATH)
    table = status.constraint_table(config)
    expected = sum(len(config.get(section) or []) for section in
                   ("constraints", "eligibility_criteria", "categorical_rules"))
    assert len(table) == expected


def test_gams_equation_found_from_the_label_or_the_comment():
    known = {"EQ_BC_QUOTA_MAX": "Eq_BC_QUOTA_MAX", "EQ_MO_MAX_EXPL": "Eq_MO_MAX_Expl",
             "EQ_CS_BT": "Eq_CS_BT"}
    assert status.gams_equation_for("bc_quota_max", known) == "Eq_BC_QUOTA_MAX"
    assert status.gams_equation_for("labor_max_farm", known) == "Eq_MO_MAX_Expl"
    assert status.gams_equation_for("unknown_label", known) is None

    text = (
        "categorical_rules:\n"
        "  # Eq_CS_BT: Basse-Terre sugarcane forbidden outside Basse-Terre.\n"
        "  - name: attribute_forbidden\n"
        "    enable: true\n"
        "  - name: forbid_crops           # Eq_TH_SUPP inline\n"
    )
    found = status.gams_equations_from_comments(text)
    assert found[("categorical_rules", 0)] == ["Eq_CS_BT"]
    assert found[("categorical_rules", 1)] == ["Eq_TH_SUPP"]


def test_group_matrix_counts_fine_crops_per_rpg_group():
    table = pd.DataFrame(
        [
            {"section": "constraints", "position": 0, "name": "n", "label": "cane_cap",
             "enabled": True, "crops": ["CS_MG_NISM", "CS_BT_NIM"]},
            {"section": "constraints", "position": 1, "name": "at_most_one_crop_per_plot",
             "label": "", "enabled": True, "crops": "*"},
        ]
    )
    matrix = status.constraint_group_matrix(table, ["CS_MG_NISM", "CS_BT_NIM", "ME"])
    assert matrix.loc["cane_cap", "CS"] == 2
    assert matrix.loc["at_most_one_crop_per_plot #1", "ME"] == "all"
