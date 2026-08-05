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


def test_matrix_can_sweep_a_constraint_argument():
    # The epsilon-constraint case: trace a Pareto front by varying a ceiling's threshold,
    # which lives in a constraint's args and at no dotted path.
    runs = [{"name": "front", "matrix": {"args:plafond_azote.threshold": [1.0e6, 1.5e6]}}]
    expanded = expand_runs(runs)
    assert [r["name"] for r in expanded] == [
        "front__threshold=1000000.0",
        "front__threshold=1500000.0",
    ]
    assert expanded[0]["set_args"] == [
        {"label": "plafond_azote", "args": {"threshold": 1.0e6}}
    ]
    assert "overrides" not in expanded[0]


def test_matrix_argument_sweep_wins_over_a_static_set_args():
    runs = [{
        "name": "front",
        "set_args": [{"label": "plafond_azote", "args": {"threshold": 999.0, "sense": "le"}}],
        "matrix": {"args:plafond_azote.threshold": [1.0e6]},
    }]
    (only,) = expand_runs(runs)
    # Applied in order, so the swept value lands last and wins -- while `sense` survives.
    config = apply_overrides(
        {"constraints": [{
            "name": "territory_indicator_bound", "enable": True,
            "args": {"label": "plafond_azote", "threshold": 0.0, "sense": "le"},
        }]},
        only,
    )
    args = config["constraints"][0]["args"]
    assert args["threshold"] == 1.0e6
    assert args["sense"] == "le"


def test_matrix_can_mix_dotted_paths_and_constraint_arguments():
    runs = [{
        "name": "mix",
        "matrix": {"data.scenario": ["SMART"], "args:plafond_ift.threshold": [40000]},
    }]
    (only,) = expand_runs(runs)
    assert only["overrides"] == {"data.scenario": "SMART"}
    assert only["set_args"] == [{"label": "plafond_ift", "args": {"threshold": 40000}}]


def test_a_malformed_args_matrix_key_raises():
    with pytest.raises(ValueError, match="args:<label>"):
        expand_runs([{"name": "x", "matrix": {"args:no_dot_here": [1]}}])


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


def test_set_args_can_patch_an_entry_added_by_enable_add():
    # The composition an epsilon-constraint front needs: the policy POSES the bound through
    # enable_add (it is nowhere in config.yaml), the sweep MOVES it through set_args. Applying
    # set_args first raised "label matched no entry" on every point of pareto_subventions.
    from core.config import apply_overrides, merge_run_specs

    policy = {
        "enable_add": [
            {
                "name": "territory_indicator_bound",
                "args": {"label": "budget", "indicator": "subvention",
                         "sense": "le", "threshold": 72_000_000},
            }
        ]
    }
    sweep = {"set_args": [{"label": "budget", "args": {"threshold": 43_000_000}}]}

    merged = apply_overrides({"constraints": []}, merge_run_specs(policy, sweep))
    assert merged["constraints"] == [
        {
            "name": "territory_indicator_bound",
            "enable": True,
            "args": {"label": "budget", "indicator": "subvention",
                     "sense": "le", "threshold": 43_000_000},
        }
    ]


def test_disable_can_switch_off_an_entry_added_by_enable_add():
    # Same ordering, other channel: what one spec adds, another can still switch off.
    from core.config import apply_overrides

    run = {
        "enable_add": [{"name": "territory_indicator_bound", "args": {"label": "budget"}}],
        "disable": ["budget"],
    }
    merged = apply_overrides({"constraints": []}, run)
    assert merged["constraints"][0]["enable"] is False


def test_merge_run_specs_concatenates_overlapping_multiplier_lists():
    # The case the whole composer exists for: a policy and a forcing both shock subsidies.
    # A plain dict update would drop the policy's entry and the run would silently model
    # something else than what was written.
    from core.config import merge_run_specs

    policy = {
        "overrides": {
            "economic_overrides.subsidy_multipliers": [{"crops": ["CS"], "factor": 1.5}]
        }
    }
    forcing = {
        "overrides": {
            "economic_overrides.subsidy_multipliers": [{"crops": "*", "factor": 0.4}]
        }
    }
    merged = merge_run_specs(policy, forcing)
    assert merged["overrides"]["economic_overrides.subsidy_multipliers"] == [
        {"crops": ["CS"], "factor": 1.5},
        {"crops": "*", "factor": 0.4},
    ]


def test_merge_run_specs_replaces_scalar_overrides_with_the_forcing_value():
    from core.config import merge_run_specs

    merged = merge_run_specs(
        {"overrides": {"data.scenario": "SMART"}}, {"overrides": {"data.scenario": "RESTIT"}}
    )
    assert merged["overrides"]["data.scenario"] == "RESTIT"


def test_merge_run_specs_concatenates_every_edit_channel():
    from core.config import merge_run_specs

    policy = {
        "enable": ["a"],
        "disable": ["b"],
        "set_args": [{"label": "l", "args": {"x": 1}}],
        "enable_add": [{"name": "n1", "args": {}}],
    }
    forcing = {
        "enable": ["c"],
        "disable": ["d"],
        "set_args": [{"label": "l", "args": {"y": 2}}],
        "enable_add": [{"name": "n2", "args": {}}],
    }
    merged = merge_run_specs(policy, forcing)
    assert merged["enable"] == ["a", "c"]
    assert merged["disable"] == ["b", "d"]
    assert [p["args"] for p in merged["set_args"]] == [{"x": 1}, {"y": 2}]
    assert [e["name"] for e in merged["enable_add"]] == ["n1", "n2"]


def test_merge_run_specs_does_not_mutate_either_side():
    from core.config import merge_run_specs

    policy = {"overrides": {"economic_overrides.price_multipliers": [{"crops": ["BA"], "factor": 1.2}]}}
    forcing = {"overrides": {"economic_overrides.price_multipliers": [{"crops": ["CS"], "factor": 0.8}]}}
    merge_run_specs(policy, forcing)
    assert policy["overrides"]["economic_overrides.price_multipliers"] == [
        {"crops": ["BA"], "factor": 1.2}
    ]
    assert forcing["overrides"]["economic_overrides.price_multipliers"] == [
        {"crops": ["CS"], "factor": 0.8}
    ]


def test_compose_runs_defaults_to_policies_only():
    from core.config import compose_runs

    spec = {
        "policies": [{"name": "P1"}, {"name": "P2"}],
        "forcings": [{"name": "F0"}, {"name": "F1"}],
    }
    assert [r["name"] for r in compose_runs(spec)] == ["P1", "P2"]


def test_compose_runs_crosses_policies_with_forcings():
    from core.config import compose_runs

    spec = {
        "policies": [{"name": "P1"}, {"name": "P2"}],
        "forcings": [{"name": "F0"}, {"name": "F1"}],
    }
    assert [r["name"] for r in compose_runs(spec, cross=True)] == [
        "P1__F0",
        "P1__F1",
        "P2__F0",
        "P2__F1",
    ]


def test_compose_runs_selects_named_subsets():
    from core.config import compose_runs

    spec = {
        "policies": [{"name": "P1"}, {"name": "P2"}],
        "forcings": [{"name": "F0"}, {"name": "F1"}],
    }
    runs = compose_runs(spec, cross=True, policies=["P2"], forcings=["F1"])
    assert [r["name"] for r in runs] == ["P2__F1"]


def test_compose_runs_rejects_an_unknown_name():
    from core.config import compose_runs

    with pytest.raises(KeyError, match="Unknown policy"):
        compose_runs({"policies": [{"name": "P1"}]}, policies=["P9"])


# --- Crop group catalogue -----------------------------------------------------


def test_expand_group_refs_flattens_references_and_drops_duplicates():
    from core.config import expand_group_refs

    groups = expand_group_refs({
        "bc": ["BC", "BC_BT"],
        "ig": ["IG"],
        "vivrier": ["@bc", "@ig", "ME", "BC"],
    })
    assert groups["vivrier"] == ["BC", "BC_BT", "IG", "ME"]


def test_expand_group_refs_rejects_a_cycle():
    from core.config import expand_group_refs

    with pytest.raises(ValueError, match="cycle"):
        expand_group_refs({"a": ["@b"], "b": ["@a"]})


def test_resolve_crop_groups_substitutes_lists_wherever_they_appear():
    from core.config import resolve_crop_groups

    spec = {
        "overrides": {"economic_overrides.price_multipliers": [
            {"crops": {"group": "canne"}, "factor": 0.75},
            {"crops": "*", "factor": 1.0},
        ]},
        "enable_add": [{"name": "crop_share_bound",
                        "args": {"numerator_crops": {"group": "bio"}}}],
    }
    resolved = resolve_crop_groups(spec, {"canne": ["CS", "CS_BT"], "bio": ["MA_PLBIO"]})
    multipliers = resolved["overrides"]["economic_overrides.price_multipliers"]
    assert multipliers[0]["crops"] == ["CS", "CS_BT"]
    assert multipliers[1]["crops"] == "*"  # the wildcard is not a group
    assert resolved["enable_add"][0]["args"]["numerator_crops"] == ["MA_PLBIO"]


def test_resolve_crop_groups_leaves_a_constraints_own_groups_argument_alone():
    # territory_production_bound's args carry a key literally named `groups`, holding dicts
    # with several keys. A looser match than "the exact one-key {group: name}" would eat it.
    from core.config import resolve_crop_groups

    args = {"groups": [{"crops": {"group": "arbo"}, "use_yield": False}], "threshold": 200}
    resolved = resolve_crop_groups({"args": args}, {"arbo": ["AG", "VE"]})
    assert resolved["args"]["groups"] == [{"crops": ["AG", "VE"], "use_yield": False}]
    assert resolved["args"]["threshold"] == 200


def test_resolve_crop_groups_names_the_available_groups_on_a_typo():
    from core.config import resolve_crop_groups

    with pytest.raises(KeyError, match="canne"):
        resolve_crop_groups({"crops": {"group": "cannne"}}, {"canne": ["CS"]})


def test_load_batch_spec_assembles_catalogues_and_resolves_groups(tmp_path):
    import yaml

    from core.config import load_batch_spec

    (tmp_path / "crop_groups.yaml").write_text(
        yaml.safe_dump({"canne": ["@cs"], "vivrier": ["@canne", "ME"]}), encoding="utf-8"
    )
    (tmp_path / "politiques.yaml").write_text(
        yaml.safe_dump({"policies": [
            {"name": "P1", "overrides": {"economic_overrides.price_multipliers": [
                {"crops": {"group": "vivrier"}, "factor": 1.4}
            ]}}
        ]}),
        encoding="utf-8",
    )
    (tmp_path / "forcages.yaml").write_text(
        yaml.safe_dump({"forcings": [{"name": "F0"}]}), encoding="utf-8"
    )
    (tmp_path / "plan.yaml").write_text(
        yaml.safe_dump({
            "include": {"crop_groups": "crop_groups.yaml", "policies": "politiques.yaml",
                        "forcings": "forcages.yaml"},
            "scenarios": {"P1": ["F0"]},
        }),
        encoding="utf-8",
    )

    # `cs` comes from the base config's crop_families -- the catalogue never restates what
    # the model already knows.
    spec = load_batch_spec(tmp_path / "plan.yaml", {"crop_families": {"cs": ["CS", "CS_BT"]}})
    assert [p["name"] for p in spec["policies"]] == ["P1"]
    multiplier = spec["policies"][0]["overrides"]["economic_overrides.price_multipliers"][0]
    assert multiplier["crops"] == ["CS", "CS_BT", "ME"]


def test_load_batch_spec_honours_a_catalogues_own_crop_groups_include(tmp_path):
    # A catalogue must stay runnable on its own (--scenarios scenarios_politiques.yaml),
    # which means it declares where its groups come from -- and a plan including it must not
    # have to repeat that declaration.
    import yaml

    from core.config import load_batch_spec

    (tmp_path / "groups.yaml").write_text(yaml.safe_dump({"bio": ["MA_PLBIO"]}), encoding="utf-8")
    (tmp_path / "politiques.yaml").write_text(
        yaml.safe_dump({
            "include": {"crop_groups": "groups.yaml"},
            "policies": [{"name": "P1", "enable_add": [
                {"name": "crop_share_bound", "args": {"numerator_crops": {"group": "bio"}}}
            ]}],
        }),
        encoding="utf-8",
    )
    (tmp_path / "plan.yaml").write_text(
        yaml.safe_dump({"include": {"policies": "politiques.yaml"}, "scenarios": {"P1": None}}),
        encoding="utf-8",
    )

    spec = load_batch_spec(tmp_path / "plan.yaml")
    assert spec["policies"][0]["enable_add"][0]["args"]["numerator_crops"] == ["MA_PLBIO"]


def test_load_batch_spec_rejects_an_unincludable_section(tmp_path):
    import yaml

    from core.config import load_batch_spec

    (tmp_path / "plan.yaml").write_text(
        yaml.safe_dump({"include": {"constraints": "nope.yaml"}}), encoding="utf-8"
    )
    with pytest.raises(KeyError, match="constraints"):
        load_batch_spec(tmp_path / "plan.yaml")


# --- Plans --------------------------------------------------------------------


def _plan_spec():
    return {
        "policies": [{"name": "P1"}, {"name": "P2"}, {"name": "P3"}],
        "forcings": [{"name": "F0"}, {"name": "F1"}, {"name": "F2"}],
        "sweeps": [{"name": "S", "matrix": {"data.year": ["2017", "2020"]}}],
        "scenarios": {
            "P1": None,                                   # unforced
            "P2": ["F0", "F1"],                           # shorthand
            "P3": {"forcings": "*", "sweeps": ["S"]},     # every forcing + a front
        },
    }


def test_a_plan_runs_exactly_the_cells_it_names():
    from core.config import compose_runs

    names = [r["name"] for r in compose_runs(_plan_spec())]
    assert names == [
        "P1",
        "P2__F0", "P2__F1",
        "P3__F0", "P3__F1", "P3__F2",
        "P3__S__year=2017", "P3__S__year=2020",
    ]


def test_a_sweep_is_not_crossed_with_the_cells_forcings_unless_asked():
    # The cost argument: P3 goes through three forcings, and its front is still traced ONCE.
    from core.config import compose_runs

    spec = _plan_spec()
    sweep_runs = [r for r in compose_runs(spec) if r["sweep"]]
    assert {r["forcing"] for r in sweep_runs} == {None}

    spec["scenarios"]["P3"]["sweeps"] = [{"name": "S", "forcings": ["F2"]}]
    forced = [r for r in compose_runs(spec) if r["sweep"]]
    assert [r["name"] for r in forced] == ["P3__F2__S__year=2017", "P3__F2__S__year=2020"]


def test_a_plan_carries_the_three_coordinates_on_every_run():
    from core.config import compose_runs

    by_name = {r["name"]: r for r in compose_runs(_plan_spec())}
    assert (by_name["P1"]["policy"], by_name["P1"]["forcing"], by_name["P1"]["sweep"]) == (
        "P1", None, None
    )
    point = by_name["P3__S__year=2017"]
    assert (point["policy"], point["forcing"], point["sweep"]) == ("P3", None, "S")


def test_sweeps_false_drops_the_fronts_and_keeps_the_cells():
    from core.config import compose_runs

    names = [r["name"] for r in compose_runs(_plan_spec(), sweeps=False)]
    assert names == ["P1", "P2__F0", "P2__F1", "P3__F0", "P3__F1", "P3__F2"]


def test_a_plan_can_be_restricted_to_one_policy_or_one_forcing():
    from core.config import compose_runs

    assert [r["name"] for r in compose_runs(_plan_spec(), policies=["P2"])] == [
        "P2__F0", "P2__F1"
    ]
    # Restricting to a forcing keeps only the cells that were planned under it -- P1 is
    # unforced, so it is not silently forced into the selection.
    assert [r["name"] for r in compose_runs(_plan_spec(), forcings=["F1"])] == [
        "P2__F1", "P3__F1"
    ]


def test_cross_overrides_a_plan_rather_than_being_ignored_by_it():
    from core.config import compose_runs

    runs = compose_runs(_plan_spec(), cross=True)
    assert len(runs) == 3 * 3  # every policy x every forcing, the plan set aside
    assert "P1__F2" in {r["name"] for r in runs}  # a pair the plan does not ask for


def test_a_plan_naming_an_undeclared_policy_raises_with_the_available_names():
    from core.config import compose_runs

    spec = _plan_spec()
    spec["scenarios"]["P9"] = None
    with pytest.raises(KeyError, match="P9"):
        compose_runs(spec)


def test_a_plan_naming_an_undeclared_forcing_or_sweep_raises():
    from core.config import compose_runs

    spec = _plan_spec()
    spec["scenarios"]["P1"] = ["F9"]
    with pytest.raises(KeyError, match="F9"):
        compose_runs(spec)

    spec = _plan_spec()
    spec["scenarios"]["P1"] = {"sweeps": ["nope"]}
    with pytest.raises(KeyError, match="nope"):
        compose_runs(spec)


def test_a_plan_rejects_an_unknown_cell_key():
    from core.config import compose_runs

    spec = _plan_spec()
    spec["scenarios"]["P1"] = {"forcages": ["F0"]}  # French, and therefore not the key
    with pytest.raises(KeyError, match="forcages"):
        compose_runs(spec)


# --- Warm-start chain along a sweep -------------------------------------------


def _sweep_config():
    return {"constraints": [
        {"name": "territory_indicator_bound", "enable": False,
         "args": {"label": "azote_max", "indicator": "azote", "sense": "le",
                  "threshold": 1930903}},
        {"name": "territory_indicator_bound", "enable": False,
         "args": {"label": "emploi_min", "indicator": "travail", "sense": "ge",
                  "threshold": 5629321, "scale": 0.00062228}},
    ]}


def _sweep_runs(label, argument, values, sweep="S", policy="P", forcing=None):
    from core.config import expand_runs

    runs = expand_runs([{
        "name": sweep,
        "policy": policy,
        "forcing": forcing,
        "sweep": sweep,
        "matrix": {f"args:{label}.{argument}": values},
    }])
    return runs


def _thresholds(runs, label, argument):
    return [r["matrix_values"][f"args:{label}.{argument}"] for r in runs]


def test_expand_runs_records_what_it_swept():
    from core.config import expand_runs

    (only,) = expand_runs([{"name": "s", "matrix": {"args:azote_max.threshold": [1.0e6]}}])
    assert only["matrix_values"] == {"args:azote_max.threshold": 1.0e6}


def test_a_ceiling_sweep_is_ordered_tightest_first_so_each_point_seeds_the_next():
    # sense: le -- a solution feasible under the LOW ceiling is still feasible under a high
    # one, so ascending order makes every seed valid. Written 100 % -> 55 % in the YAML,
    # which is the order that would make every seed infeasible.
    from core.config import order_sweep_points

    runs = _sweep_runs("azote_max", "threshold", [1930903, 1544722, 1061997])
    ordered = order_sweep_points(runs, _sweep_config())
    assert _thresholds(ordered, "azote_max", "threshold") == [1061997, 1544722, 1930903]


def test_a_floor_sweep_is_ordered_the_other_way_round():
    # sense: ge -- a floor tightens as it RISES, so the tightest point is the highest one.
    from core.config import order_sweep_points

    runs = _sweep_runs("emploi_min", "threshold", [5629321, 6027000, 6428000])
    ordered = order_sweep_points(runs, _sweep_config())
    assert _thresholds(ordered, "emploi_min", "threshold") == [6428000, 6027000, 5629321]


def test_two_fronts_are_ordered_independently_of_one_another():
    from core.config import order_sweep_points

    runs = (
        _sweep_runs("azote_max", "threshold", [1930903, 1061997], forcing=None)
        + _sweep_runs("azote_max", "threshold", [1930903, 1061997], forcing="F9")
    )
    ordered = order_sweep_points(runs, _sweep_config())
    assert [r["forcing"] for r in ordered] == [None, None, "F9", "F9"]
    assert _thresholds(ordered, "azote_max", "threshold") == [
        1061997, 1930903, 1061997, 1930903
    ]


def test_ordering_never_moves_a_run_out_of_its_sweep_block():
    # The cells must keep their place: `policy_seeds` takes the FIRST solved run of a policy
    # as its nominal seed, and that is only the unforced cell if nothing jumps ahead of it.
    from core.config import order_sweep_points

    cells = [{"name": "P", "policy": "P", "forcing": None, "sweep": None}]
    ordered = order_sweep_points(
        cells + _sweep_runs("azote_max", "threshold", [1930903, 1061997]), _sweep_config()
    )
    assert ordered[0]["name"] == "P"


def test_a_sweep_over_something_that_is_not_a_bound_level_is_left_alone():
    # `scale` multiplies the indicator, so under `sense: le` a HIGHER scale is TIGHTER --
    # the opposite of `threshold`. Inferring from `sense` alone would order it backwards,
    # which is worse than not chaining.
    from core.config import order_sweep_points

    runs = _sweep_runs("azote_max", "scale", [10.0, 1.0])
    assert _thresholds(order_sweep_points(runs, _sweep_config()), "azote_max", "scale") == [
        10.0, 1.0
    ]


def test_a_sweep_over_a_constraint_with_no_declared_sense_is_left_alone():
    from core.config import order_sweep_points

    config = {"constraints": [
        {"name": "baseline_inertia_min", "enable": True,
         "args": {"label": "inertie", "min_share": 0.4}},
    ]}
    runs = _sweep_runs("inertie", "min_share", [0.7, 0.3])
    assert _thresholds(order_sweep_points(runs, config), "inertie", "min_share") == [0.7, 0.3]


def test_a_two_dimensional_sweep_is_left_alone():
    # There is no single tightening axis, so no order makes every seed valid.
    from core.config import expand_runs, order_sweep_points

    runs = expand_runs([{
        "name": "S", "policy": "P", "forcing": None, "sweep": "S",
        "matrix": {"args:azote_max.threshold": [1930903, 1061997], "data.year": ["2017"]},
    }])
    ordered = order_sweep_points(runs, _sweep_config())
    assert _thresholds(ordered, "azote_max", "threshold") == [1930903, 1061997]


def test_ordering_leaves_a_plain_batch_untouched():
    from core.config import compose_runs, order_sweep_points

    spec = {"runs": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}
    runs = compose_runs(spec)
    assert [r["name"] for r in order_sweep_points(runs, {})] == ["a", "b", "c"]


def test_seed_candidates_tries_the_previous_point_of_the_front_first():
    from scripts.run_scenarios import seed_candidates

    run = {"policy": "P8", "forcing": None, "sweep": "pareto_azote"}
    previous = {"P1": "CS"}
    nominal = {"P1": "BA"}
    global_seed = ({"P1": "MA"}, "outputs/calib_retenu")

    candidates = seed_candidates(
        run, {("P8", None, "pareto_azote"): (previous, "point_1")}, {"P8": nominal},
        global_seed,
    )
    assert [alloc for alloc, _ in candidates] == [previous, nominal, global_seed[0]]
    assert "point precedent" in candidates[0][1]


def test_seed_candidates_does_not_offer_another_fronts_point():
    # The key carries the forcing: the same sweep under F9 is a different curve, and its
    # allocation has no reason to be feasible here.
    from scripts.run_scenarios import seed_candidates

    run = {"policy": "P8", "forcing": None, "sweep": "pareto_azote"}
    other_front = {("P8", "F9", "pareto_azote"): ({"P1": "CS"}, "point_1")}
    assert seed_candidates(run, other_front, {}, None) == []


def test_seed_candidates_offers_nothing_when_the_chain_is_off():
    from scripts.run_scenarios import seed_candidates

    run = {"policy": "P8", "forcing": None, "sweep": "pareto_azote"}
    global_seed = ({"P1": "MA"}, "outputs/calib_retenu")
    candidates = seed_candidates(
        run, {("P8", None, "pareto_azote"): ({"P1": "CS"}, "pt")}, {"P8": {"P1": "BA"}},
        global_seed, chain=False,
    )
    assert candidates == [global_seed]  # the explicit --warm-start-from survives


def test_merge_run_specs_merges_matrices_so_a_sweep_composes_with_a_policy():
    from core.config import merge_run_specs

    merged = merge_run_specs(
        {"matrix": {"data.year": ["2017"]}}, {"matrix": {"args:azote.threshold": [1, 2]}}
    )
    assert merged["matrix"] == {"data.year": ["2017"], "args:azote.threshold": [1, 2]}


def test_a_sweep_catalogue_alone_runs_its_fronts_against_the_base_config():
    from core.config import compose_runs

    spec = {"sweeps": [{"name": "S", "matrix": {"args:azote.threshold": [1, 2]}}]}
    runs = compose_runs(spec)
    assert [r["name"] for r in runs] == ["S__threshold=1", "S__threshold=2"]
    # Tagged even without a policy, so a standalone front still gets ordered and chained.
    assert {r["sweep"] for r in runs} == {"S"}


def test_a_standalone_front_is_ordered_and_chained_like_a_planned_one():
    from core.config import compose_runs, order_sweep_points

    spec = {"sweeps": [{
        "name": "pareto_azote",
        "matrix": {"args:azote_max.threshold": [1930903, 1544722, 1061997]},
    }]}
    ordered = order_sweep_points(compose_runs(spec), _sweep_config())
    assert _thresholds(ordered, "azote_max", "threshold") == [1061997, 1544722, 1930903]


def test_compose_runs_passes_a_legacy_runs_spec_straight_through():
    from core.config import compose_runs

    spec = {"runs": [{"name": "solo", "overrides": {"data.year": "2020"}}]}
    assert compose_runs(spec) == spec["runs"]


def test_every_prospective_scenario_resolves_without_solving():
    from pathlib import Path

    import case_studies.guadeloupe.model.model  # noqa: F401 -- registers case constraints/rules
    from core.config import (
        apply_overrides, compose_runs, load_batch_spec, load_config, resolve_enabled,
    )
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY
    from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY

    base = load_config(Path("case_studies/guadeloupe/config.yaml"))
    spec = load_batch_spec(Path("case_studies/guadeloupe/plan.yaml"), base)
    # Crossed rather than planned: the plan deliberately runs a SUBSET, and what needs
    # checking here is that every catalogue entry still composes with every other -- a policy
    # nobody currently runs is exactly the one whose broken label goes unnoticed. `cross`
    # overrides the plan for exactly this reason.
    runs = compose_runs(spec, cross=True)
    policies = len(spec["policies"])
    forcings = len(spec["forcings"])
    assert len(runs) == policies * forcings
    assert policies == 10

    for run in runs:
        cfg = apply_overrides(base, run)
        objs = resolve_enabled(cfg["objectives"], OBJECTIVE_REGISTRY)
        assert len(objs) == 1, run.get("name")
        resolve_enabled(cfg["constraints"], CONSTRAINT_REGISTRY)  # KeyError if name unknown
        resolve_enabled(cfg["categorical_rules"], CATEGORICAL_RULE_REGISTRY)


def test_the_plan_resolves_every_cell_and_every_sweep_point():
    """The plan is what actually gets launched, so a typo in it costs a night of compute.
    This is what `--dry-run` does, minus the printing."""
    from pathlib import Path

    import case_studies.guadeloupe.model.model  # noqa: F401 -- registers case constraints/rules
    from core.config import (
        apply_overrides, compose_runs, load_batch_spec, load_config, resolve_enabled,
    )
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY
    from core.model.registry import CONSTRAINT_REGISTRY, OBJECTIVE_REGISTRY

    base = load_config(Path("case_studies/guadeloupe/config.yaml"))
    spec = load_batch_spec(Path("case_studies/guadeloupe/plan.yaml"), base)
    runs = compose_runs(spec)
    cells = compose_runs(spec, sweeps=False)
    assert len(runs) > len(cells), "the plan declares sweeps but --no-sweeps changes nothing"

    for run in runs:
        cfg = apply_overrides(base, run)
        assert len(resolve_enabled(cfg["objectives"], OBJECTIVE_REGISTRY)) == 1, run["name"]
        resolve_enabled(cfg["constraints"], CONSTRAINT_REGISTRY)
        resolve_enabled(cfg["categorical_rules"], CATEGORICAL_RULE_REGISTRY)
        # Every run carries the coordinates the dashboard groups on and the warm-start chain
        # keys on. Without `policy` a run silently drops out of both.
        assert run["policy"], run["name"]
        assert run["name"].startswith(run["policy"])


def test_prospective_labour_slack_covers_every_employment_floor():
    """An employment floor above the labour cap is infeasible, and the failure only shows
    up after a 30-minute solve. The two are set in different blocks of the same scenario,
    so this check is the only thing keeping them consistent."""
    from pathlib import Path

    from core.config import apply_overrides, compose_runs, load_batch_spec, load_config

    # Territory-wide labour capacity at slack 1.0, measured on the real dataset (see the
    # header of scenarios_politiques.yaml).
    capacity_hours_at_slack_1 = 6_252_740
    hours_per_etp = 1607

    base = load_config(Path("case_studies/guadeloupe/config.yaml"))
    # The catalogue, not the plan: a floor that only becomes infeasible once someone adds
    # its policy to the plan has been broken since it was written.
    spec = load_batch_spec(Path("case_studies/guadeloupe/scenarios_politiques.yaml"), base)
    for run in compose_runs(spec):
        cfg = apply_overrides(base, run)
        floors = [
            entry["args"]
            for entry in cfg["constraints"]
            if entry.get("enable")
            and entry["name"] == "territory_indicator_bound"
            and entry["args"].get("indicator") == "travail"
            and entry["args"].get("sense") == "ge"
        ]
        if not floors:
            continue
        slack = next(
            entry["args"].get("slack", 1.0)
            for entry in cfg["constraints"]
            if entry.get("enable") and entry["name"] == "farm_labor_hours_max"
        )
        cap_etp = capacity_hours_at_slack_1 * slack / hours_per_etp
        for args in floors:
            # The bound reads `hours x scale >= threshold`, so the hours it demands are
            # threshold / scale -- dividing, not multiplying (the two happen to coincide
            # for scale = 1/1607, which is why this is worth writing out).
            required_etp = args["threshold"] / args.get("scale", 1.0) / hours_per_etp
            assert required_etp <= cap_etp, (
                f"{run['name']}: plancher d'emploi {required_etp:,.0f} ETP au-dessus du "
                f"plafond de main d'oeuvre {cap_etp:,.0f} ETP (slack {slack})"
            )


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
