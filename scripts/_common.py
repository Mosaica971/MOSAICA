"""Paths and formatting shared by the scripts in this folder.

The sys.path bootstrap stays duplicated in each script on purpose: it has to run *before*
the first project import, so it cannot live behind an import of this module.

Deliberately free of project imports (and of pandas): every script imports this, and paying
for the data pipeline just to learn where `config.yaml` lives would slow down `--help`.
`CONFIG_PATH` therefore restates the path that `data_pipeline` also computes for itself --
`tests/test_scripts_common.py` asserts the two agree, so the restatement cannot drift.

These are DEFAULTS for the default case study, not the only possible paths. A script that
can run on any case study takes `--case-study` and reads `CaseStudy.config_path` instead
(`core/case_study.py`); the constants below follow $MOSAICA_CASE_STUDY so that even the
Guadeloupe-specific scripts point at the right directory when it is set.
"""

import os
from math import isnan
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CASE_STUDY = os.environ.get("MOSAICA_CASE_STUDY") or "guadeloupe"
CASE_STUDY_DIR = ROOT / "case_studies" / CASE_STUDY
CONFIG_PATH = CASE_STUDY_DIR / "config.yaml"
SCENARIOS_PATH = CASE_STUDY_DIR / "scenarios.yaml"
REFERENCES_PATH = CASE_STUDY_DIR / "references.yaml"
OUTPUTS_ROOT = ROOT / "outputs"


def format_number(value: Any, decimals: int = 0) -> str:
    """Thousands separated by spaces, French style; "-" for a missing value.

    Apply to ONE number, never to a whole sentence: running `.replace(",", " ")` over a
    rendered sentence eats its punctuation.
    """
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if isnan(number):
        return "-"
    return f"{number:,.{decimals}f}".replace(",", " ")
