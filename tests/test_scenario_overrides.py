import pytest

from core.config import apply_overrides, expand_runs


def _base_config():
    return {
        "data": {"year": "2017", "scenario": "RESTIT"},
        "solver": {"name": "appsi_highs", "args": {}},
        "objectives": [
            {"name": "maximize_gross_margin", "enable": True, "args": {}},
            {"name": "maximize_risk_adjusted_gross_margin", "enable": False, "args": {}},
        ],
        "constraints": [
            {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}},
            {
                "name": "territory_production_bound",
                "enable": True,
                "args": {"label": "cs_quota_max", "sense": "le", "threshold": 107000},
            },
        ],
    }


def test_dotted_override_sets_scalar():
    result = apply_overrides(_base_config(), {"overrides": {"data.year": "2020"}})
    assert result["data"]["year"] == "2020"


def test_dotted_override_creates_missing_nested_key():
    result = apply_overrides(_base_config(), {"overrides": {"solver.args.mip_rel_gap": 0.01}})
    assert result["solver"]["args"]["mip_rel_gap"] == 0.01


def test_dotted_override_replaces_whole_dict_key():
    spec = {"overrides": {"zone_filter": {"include": {"islands": [1]}}}}
    result = apply_overrides(_base_config(), spec)
    assert result["zone_filter"] == {"include": {"islands": [1]}}


def test_does_not_mutate_base_config():
    base = _base_config()
    apply_overrides(base, {"overrides": {"data.year": "2099"}})
    assert base["data"]["year"] == "2017"


def test_enable_disable_swaps_objective_by_name():
    spec = {
        "enable": ["maximize_risk_adjusted_gross_margin"],
        "disable": ["maximize_gross_margin"],
    }
    result = apply_overrides(_base_config(), spec)
    by_name = {o["name"]: o["enable"] for o in result["objectives"]}
    assert by_name == {
        "maximize_gross_margin": False,
        "maximize_risk_adjusted_gross_margin": True,
    }


def test_enable_matches_constraint_by_label():
    result = apply_overrides(_base_config(), {"disable": ["cs_quota_max"]})
    cs = next(c for c in result["constraints"] if c["args"].get("label") == "cs_quota_max")
    assert cs["enable"] is False


def test_set_args_patches_by_label_and_merges():
    spec = {"set_args": [{"label": "cs_quota_max", "args": {"threshold": 130000}}]}
    result = apply_overrides(_base_config(), spec)
    cs = next(c for c in result["constraints"] if c["args"].get("label") == "cs_quota_max")
    assert cs["args"]["threshold"] == 130000
    assert cs["args"]["sense"] == "le"  # untouched keys survive


def test_unknown_enable_token_raises():
    with pytest.raises(KeyError):
        apply_overrides(_base_config(), {"enable": ["nope"]})


def test_unknown_set_args_label_raises():
    with pytest.raises(KeyError):
        apply_overrides(_base_config(), {"set_args": [{"label": "nope", "args": {}}]})


def test_expand_runs_passes_through_without_matrix():
    runs = [{"name": "solo", "overrides": {"data.year": "2020"}}]
    assert expand_runs(runs) == runs


def test_expand_runs_cartesian_product_and_naming():
    runs = [{"name": "scan", "matrix": {"data.year": ["2017", "2020"], "data.scenario": ["RESTIT", "SMART"]}}]
    expanded = expand_runs(runs)
    assert len(expanded) == 4
    names = [r["name"] for r in expanded]
    assert names == [
        "scan__year=2017__scenario=RESTIT",
        "scan__year=2017__scenario=SMART",
        "scan__year=2020__scenario=RESTIT",
        "scan__year=2020__scenario=SMART",
    ]
    assert expanded[0]["overrides"] == {"data.year": "2017", "data.scenario": "RESTIT"}
    assert "matrix" not in expanded[0]


def test_expand_runs_folds_matrix_over_static_overrides():
    runs = [{
        "name": "mix",
        "overrides": {"solver.args.threads": 4},
        "matrix": {"data.year": ["2017"]},
    }]
    (only,) = expand_runs(runs)
    assert only["overrides"] == {"solver.args.threads": 4, "data.year": "2017"}


def test_apply_overrides_can_add_a_new_constraint_entry():
    from core.config import apply_overrides

    base = {"constraints": [{"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}]}
    run = {
        "name": "x",
        "enable_add": [
            {
                "name": "crop_share_bound",
                "args": {
                    "label": "bio_min",
                    "numerator_crops": ["MA_PLBIO"],
                    "denominator_crops": ["MA_PLBIO", "MA_ROTA"],
                    "sense": "ge",
                    "share": 0.3,
                },
            }
        ],
    }
    merged = apply_overrides(base, run)
    labels = [e["args"].get("label") for e in merged["constraints"] if e.get("enable")]
    assert "bio_min" in labels
    assert base["constraints"] == [  # base config untouched (deep copy)
        {"name": "at_most_one_crop_per_plot", "enable": True, "args": {}}
    ]


def test_apply_overrides_enable_add_routes_to_an_explicit_section():
    from core.config import apply_overrides

    base = {"constraints": [], "categorical_rules": []}
    run = {
        "name": "secheresse",
        "enable_add": [
            {"name": "forbid_crops", "section": "categorical_rules", "args": {"crops": ["ME"]}}
        ],
    }
    merged = apply_overrides(base, run)
    assert merged["constraints"] == []
    assert merged["categorical_rules"] == [
        {"name": "forbid_crops", "enable": True, "args": {"crops": ["ME"]}}
    ]


def test_every_scenario_resolves_without_solving():
    from pathlib import Path

    import case_studies.guadeloupe.model.model  # noqa: F401 -- registers case constraints/rules
    from core.config import apply_overrides, expand_runs, load_config, resolve_enabled
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY
    from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY

    base = load_config(Path("case_studies/guadeloupe/config.yaml"))
    runs = expand_runs(
        (load_config(Path("case_studies/guadeloupe/scenarios.yaml")) or {}).get("runs") or []
    )
    assert len(runs) >= 20

    for run in runs:
        cfg = apply_overrides(base, run)
        # Exactly one objective enabled, and every enabled constraint/rule name is registered.
        objs = resolve_enabled(cfg["objectives"], OBJECTIVE_REGISTRY)
        assert len(objs) == 1, run.get("name")
        resolve_enabled(cfg["constraints"], CONSTRAINT_REGISTRY)  # KeyError if name unknown
        resolve_enabled(cfg["categorical_rules"], CATEGORICAL_RULE_REGISTRY)
