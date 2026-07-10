from scripts.profile_solver import build_zone_filter_from_args, parse_args


def test_build_zone_filter_from_args_returns_none_when_nothing_selected():
    args = parse_args([])

    assert build_zone_filter_from_args(args) is None


def test_build_zone_filter_from_args_builds_include_dict_from_islands():
    args = parse_args(["--island", "1", "--island", "2"])

    assert build_zone_filter_from_args(args) == {"include": {"islands": [1, 2]}}


def test_build_zone_filter_from_args_combines_all_criteria():
    args = parse_args(
        ["--region", "R1", "--farm", "E1471", "--farm", "E2", "--plot", "P1"]
    )

    assert build_zone_filter_from_args(args) == {
        "include": {
            "regions": ["R1"],
            "farms": ["E1471", "E2"],
            "plots": ["P1"],
        }
    }
