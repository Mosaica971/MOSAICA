"""Paths shared by the scripts in this folder.

The sys.path bootstrap stays duplicated in each script on purpose: it has to run *before*
the first project import, so it cannot live behind an import of this module.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE_STUDY_DIR = ROOT / "case_studies" / "guadeloupe"
CONFIG_PATH = CASE_STUDY_DIR / "config.yaml"
SCENARIOS_PATH = CASE_STUDY_DIR / "scenarios.yaml"
OUTPUTS_ROOT = ROOT / "outputs"
