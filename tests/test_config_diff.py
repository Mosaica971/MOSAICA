"""Diff of two runs' starting configuration. Data-free: tiny hand-built config dicts."""

from apps.dashboard import config_diff


def _config(constraints, **extra):
    base = {
        "data": {"year": "2017", "scenario": "RESTIT"},
        "solver": {"args": {"mip_rel_gap": 0.01}},
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
        "constraints": constraints,
        "eligibility_criteria": [],
        "categorical_rules": [],
    }
    base.update(extra)
    return base


def _constraint(label, *, enable, **args):
    return {"name": "territory_production_bound", "enable": enable,
            "args": {"label": label, **args}}


def test_a_constraint_turned_on_is_the_headline():
    left = _config([_constraint("pn_prod_min", enable=False, threshold=6096)])
    right = _config([_constraint("pn_prod_min", enable=True, threshold=6096)])

    summary = config_diff.summarise(left, right)

    assert summary["headline"]["activated"] == ["pn_prod_min"]
    assert summary["headline"]["deactivated"] == []
    row = summary["components"]["constraints"][0]
    assert (row["left"], row["right"]) == (config_diff.DISABLED, config_diff.ENABLED)


def test_a_constraint_turned_off_is_reported_as_such():
    left = _config([_constraint("cs_gfa", enable=True)])
    right = _config([_constraint("cs_gfa", enable=False)])

    assert config_diff.summarise(left, right)["headline"]["deactivated"] == ["cs_gfa"]


def test_a_threshold_move_on_an_active_constraint_is_retuning_not_activation():
    left = _config([_constraint("bc_quota_max", enable=True, threshold=40000)])
    right = _config([_constraint("bc_quota_max", enable=True, threshold=6440)])

    summary = config_diff.summarise(left, right)

    assert summary["headline"] == {
        "activated": [], "deactivated": [], "retuned": ["bc_quota_max"]
    }
    assert summary["components"]["constraints"][0]["args"] == {"threshold": (40000, 6440)}


def test_a_threshold_move_on_a_constraint_off_both_sides_is_flagged_inert():
    """A number nobody reads changes no result -- saying so keeps the diff honest."""
    left = _config([_constraint("bc_quota_max", enable=False, threshold=40000)])
    right = _config([_constraint("bc_quota_max", enable=False, threshold=6440)])

    summary = config_diff.summarise(left, right)

    assert summary["headline"]["retuned"] == []
    assert "inactif" in summary["components"]["constraints"][0]["verdict"]


def test_a_constraint_present_on_one_side_only_is_not_silently_dropped():
    left = _config([])
    right = _config([_constraint("new_rule", enable=True)])

    rows = config_diff.diff_components(left, right, "constraints")

    assert [row["component"] for row in rows] == ["new_rule"]
    assert rows[0]["left"] == config_diff.ABSENT


def test_identical_configs_produce_an_empty_diff():
    same = _config([_constraint("pn_prod_min", enable=True, threshold=6096)])

    summary = config_diff.summarise(dict(same), dict(same))

    assert summary["scalars"] == []
    assert all(not rows for rows in summary["components"].values())
    assert not any(summary["headline"].values())


def test_unchanged_components_are_kept_when_asked():
    same = _config([_constraint("pn_prod_min", enable=True)])

    rows = config_diff.diff_components(same, same, "constraints", changes_only=False)

    assert [row["verdict"] for row in rows] == ["identique"]


def test_scalars_are_compared_by_dotted_key_and_skip_component_lists():
    left = _config([], solver={"args": {"mip_rel_gap": 0.01, "time_limit": 3600}})
    right = _config([], solver={"args": {"mip_rel_gap": 0.001, "time_limit": 3600}})

    scalars = config_diff.diff_scalars(left, right)

    assert scalars == [{"key": "solver.args.mip_rel_gap", "left": 0.01, "right": 0.001}]


def test_flatten_leaves_lists_whole_rather_than_indexing_them():
    flat = config_diff.flatten_scalars({"crop_families": {"cs": ["CS", "CS_BT"]}})

    assert flat == {"crop_families.cs": ["CS", "CS_BT"]}


def test_unlabelled_entries_of_the_same_name_are_paired_by_occurrence():
    """Categorical rules often carry no label; the nth of one config must be compared with
    the nth of the other rather than collapsing them all onto one key."""
    rule = lambda crops: {"name": "attribute_forbidden", "enable": True,  # noqa: E731
                          "args": {"crops": crops}}
    left = _config([], categorical_rules=[rule(["ME"]), rule(["VE"])])
    right = _config([], categorical_rules=[rule(["ME"]), rule(["AG"])])

    rows = config_diff.diff_components(left, right, "categorical_rules")

    assert [row["component"] for row in rows] == ["attribute_forbidden #2"]
    assert rows[0]["args"] == {"crops": (["VE"], ["AG"])}
