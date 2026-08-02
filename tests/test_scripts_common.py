"""The paths and formatting every script shares. Data-free."""

import math

from scripts import _common


def test_the_declared_paths_point_where_they_claim():
    assert _common.CONFIG_PATH.name == "config.yaml"
    assert _common.CONFIG_PATH.parent == _common.CASE_STUDY_DIR
    assert _common.SCENARIOS_PATH.parent == _common.CASE_STUDY_DIR
    assert _common.REFERENCES_PATH.parent == _common.CASE_STUDY_DIR
    assert _common.OUTPUTS_ROOT.parent == _common.ROOT


def test_the_scripts_config_path_agrees_with_the_pipelines_own():
    """`_common` restates this path rather than importing the pipeline (which would pull
    pandas in just to answer `--help`). The restatement must not drift."""
    from case_studies.guadeloupe.pipeline import data_pipeline

    assert _common.CONFIG_PATH == data_pipeline.CONFIG_PATH


def test_numbers_are_grouped_french_style():
    assert _common.format_number(1234567) == "1 234 567"
    assert _common.format_number(1234.5678, 2) == "1 234.57"
    assert _common.format_number(0) == "0"
    assert _common.format_number(-1500) == "-1 500"


def test_missing_values_render_as_a_dash_whatever_their_flavour():
    """The two scripts sharing this used to guard with pd.isna; None, NaN and a
    non-numeric string must all land on the same dash."""
    assert _common.format_number(None) == "-"
    assert _common.format_number(float("nan")) == "-"
    assert _common.format_number(math.nan) == "-"
    assert _common.format_number("n/a") == "-"


def test_the_two_scripts_share_one_implementation_rather_than_copying_it():
    from scripts import build_reference_state, compare_to_reference

    assert build_reference_state._n is _common.format_number
    assert compare_to_reference._n is _common.format_number
