"""Status page: what is implemented, at which resolution, on which choices, and what is left.

The same four tables as docs/status/STATUS.md (scripts/build_status_board.py), built live
from the catalogues and from config.yaml -- see case_studies/guadeloupe/reporting/status.py.
Reads no run and solves nothing.

Run from the repo root:  streamlit run apps/dashboard/app.py
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from case_studies.guadeloupe.domain.crop_labels import label_for
from case_studies.guadeloupe.reporting import status
from core.config import load_config

CONFIG_PATH = _REPO_ROOT / "case_studies" / "guadeloupe" / "config.yaml"
CROP_SET = _REPO_ROOT / "data" / "sets" / "CULT_2017.set"

st.set_page_config(page_title="MOSAICA -- Status", layout="wide")
st.title("Status: what is implemented")

config = load_config(CONFIG_PATH)
levels, catalog = status.load_indicator_catalog()
constraints = status.constraint_table(config, config_text=CONFIG_PATH.read_text(encoding="utf-8"))
if CROP_SET.exists():
    from core.data.readers import read_flat_set

    crops = read_flat_set(CROP_SET)
else:
    crops = sorted({c for cs in constraints["crops"] if cs != "*" for c in cs})

tab_indicators, tab_constraints, tab_parameters, tab_roadmap = st.tabs(
    ["Indicators x levels", "Constraints x crops", "Parameter choices", "Roadmap"]
)

with tab_indicators:
    matrix = status.indicator_level_matrix(levels, catalog)
    families = sorted(matrix["family"].unique())
    chosen = st.multiselect("Families", families, default=families)
    shown = matrix[matrix["family"].isin(chosen)]
    colours = {
        status.REPORTED: "background-color: #2e7d32; color: white",
        status.COMPUTABLE: "background-color: #c8e6c9",
        status.NEEDS_DEFINITION: "background-color: #fff3c4",
        status.NOT_APPLICABLE: "color: #9e9e9e",
    }
    st.dataframe(
        shown.style.map(lambda value: colours.get(value, ""), subset=levels),
        width="stretch",
    )
    st.caption(
        "**reported**: every run writes it at that level today · **computable**: the data "
        "allows it (additive or ratio indicator, a plot -> zone mapping exists), the reporting "
        "does not do it yet · **needs definition**: a non-additive statistic (Shannon, Gini, a "
        "maximum) must be defined per level first · **n/a**: not meaningful (the 2017 "
        "observation has no fine crops; self-sufficiency needs a population per zone). "
        "Source: `case_studies/guadeloupe/status/indicator_catalog.yaml`."
    )

with tab_constraints:
    enabled_only = st.checkbox("Enabled rules only", value=True)
    table = constraints[constraints["enabled"]] if enabled_only else constraints
    display = table.assign(
        crops=table["crops"].map(lambda c: "all" if c == "*" else ", ".join(c))
    )
    st.dataframe(
        display[["section", "name", "label", "enabled", "role", "gams_equation", "threshold",
                 "crops"]],
        width="stretch", hide_index=True,
    )
    st.subheader("Enabled rules x RPG crop groups")
    st.dataframe(status.constraint_group_matrix(constraints, crops), width="stretch")
    st.subheader("Everything that applies to one crop")
    crop = st.selectbox("Crop", crops, format_func=lambda code: f"{code} -- {label_for(code)}")
    hits = status.rules_for_crop(constraints[constraints["enabled"]], crop)
    st.dataframe(
        hits[["section", "name", "label", "role", "gams_equation", "threshold"]],
        width="stretch", hide_index=True,
    )
    st.caption(
        "Derived from config.yaml. Rules touching every crop (the assignment rule, the labour "
        "cap, the numeric eligibility bounds) are listed for every crop. The number of "
        "(plot, crop) pairs each ban removes needs the data: "
        "`python scripts/build_status_board.py --with-data`."
    )

with tab_parameters:
    parameters = status.parameter_table(config)
    drift = parameters[parameters["check"].isin(["DRIFT", "path not found"])]
    if not drift.empty:
        st.error(
            "The retained value differs from config.yaml for: "
            + ", ".join(drift["parameter"]) + ". Update the config or parameter_choices.yaml."
        )
    st.dataframe(
        parameters[["parameter", "retained", "in_config", "check", "status", "candidates",
                    "reason", "vigilance"]],
        width="stretch", hide_index=True,
    )
    st.caption(
        "`check` compares the retained value with config.yaml; `-` = the choice lives in code "
        "or in the data, not in the config. `vigilance` = entry of docs/04-vigilance.md. "
        "Source: `case_studies/guadeloupe/status/parameter_choices.yaml`."
    )

with tab_roadmap:
    roadmap = status.roadmap_table()
    st.dataframe(status.roadmap_summary(roadmap), width="stretch")
    statuses = [s for s in status.ROADMAP_STATUSES if s in set(roadmap["status"])]
    wanted = st.multiselect("Status", statuses, default=[s for s in statuses if s != "done"])
    st.dataframe(
        roadmap[roadmap["status"].isin(wanted)][
            ["id", "status", "area", "title", "left", "blocked_by", "spec"]
        ],
        width="stretch", hide_index=True,
    )
    st.caption("Source: `docs/status/roadmap.yaml` (replaces the former docs/TODO.md).")
