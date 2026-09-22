"""Map page: the observed 2017 land use against the simulated one, on the real parcels.

The geometry comes from data/gis/01_RPG 2017/, joined to the model's synthetic plot ids by
farm signature -- see case_studies/guadeloupe/domain/geometry.py, which documents both how
the join is established (99.4 % of plots) and what it cannot claim.

Read-only. Run from the repo root:
    streamlit run apps/dashboard/app.py
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import streamlit as st

from apps.dashboard import loaders, maps
from case_studies.guadeloupe.domain.geometry import RPG_LAYER, build_geometry_join
from case_studies.guadeloupe.domain.zones import ISLAND_LABELS, REGION_LABELS

OUTPUTS_ROOT = _REPO_ROOT / "outputs"
LAYER = _REPO_ROOT / RPG_LAYER
ALL = "All"

st.set_page_config(page_title="MOSAICA -- Map", layout="wide")
st.title("Crop map")

if not LAYER.exists():
    st.error(
        f"Plot layer missing: `{RPG_LAYER}`.\n\n"
        "This page needs the `data/gis/` folder, which, like all of `data/`, is not "
        "versioned. Copy it to the repository root."
    )
    st.stop()


@st.cache_resource(show_spinner="Reading the plot layer…")
def _geometry():
    """Polygons keyed by plot id, plus the plot attribute table.

    cache_resource, not cache_data: the join is ~25 000 polygon objects, rebuilt in about a
    second but not worth copying on every widget change.
    """
    from case_studies.guadeloupe.pipeline.data_pipeline import SETS_DIR, TABLES_DIR
    from core.data.readers import read_mapping_set, read_wide_table

    plots = read_wide_table(TABLES_DIR / "Data_Parc_Gwad_2017.txt")
    farms = read_mapping_set(SETS_DIR / "EXPL_PARC_2017.set", "farm", "plot")
    join = build_geometry_join(plots, farms.set_index("plot")["farm"], LAYER)
    return join, plots


join, plots = _geometry()

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("No run in `outputs/` — run `python main.py` first.")
    st.stop()

with st.sidebar:
    st.header("Map")
    labels: dict[str, Path] = {}
    for run_dir_candidate in runs:
        try:
            recap = loaders.load_recap(run_dir_candidate)
        except (OSError, ValueError):
            recap = {}
        name = loaders.run_display_name(run_dir_candidate, recap)
        # Two runs may share a run_name; the folder disambiguates.
        labels[name if name not in labels else f"{name} ({run_dir_candidate.name})"] = (
            run_dir_candidate
        )
    chosen_name = st.selectbox("Run", list(labels), index=0)
    run_dir = labels[chosen_name]

    island_codes = sorted(plots["ILE"].dropna().unique().tolist())
    island = st.selectbox(
        "Island", [ALL, *island_codes],
        format_func=lambda v: v if v == ALL else ISLAND_LABELS.get(str(int(v)), str(v)),
    )
    region_codes = sorted(plots["REGION"].dropna().unique().tolist())
    region = st.selectbox(
        "Region", [ALL, *region_codes],
        format_func=lambda v: v if v == ALL else REGION_LABELS.get(str(int(v)), str(v)),
    )
    view = st.radio(
        "View", ("Observed vs simulated", "What changed"), index=0,
        help="The second view answers a question two mosaics side by side cannot: which "
        "plots changed use.",
    )
    outlines = st.checkbox("Plot outlines", value=False)

st.caption(f"Plot join: {join.summary(len(plots))}")

selected = set(plots.index)
if island != ALL:
    selected &= set(plots.index[plots["ILE"] == island])
if region != ALL:
    selected &= set(plots.index[plots["REGION"] == region])

polygons = maps.filter_polygons(join.polygons, selected)
if not polygons:
    st.warning("No located plot for this selection.")
    st.stop()
bounds = maps.shared_bounds(polygons)


def _allocation(side: str) -> dict[str, str]:
    frame = loaders.load_csv(run_dir, f"allocation_{side}.csv")
    if frame is None:
        return {}
    return dict(zip(frame["plot"].astype(str), frame["crop"].astype(str)))


observed, simulated = _allocation("input"), _allocation("output")
if not observed and not simulated:
    st.warning(f"{run_dir.name} holds no usable allocation.")
    st.stop()

if view == "Observed vs simulated":
    left, right = st.columns(2)
    with left:
        st.pyplot(maps.build_map_figure(
            polygons, observed, title="Observed 2017",
            bounds=bounds, edge_width=0.15 if outlines else 0.0,
        ))
    with right:
        st.pyplot(maps.build_map_figure(
            polygons, simulated, title=f"Simulated — {chosen_name}",
            bounds=bounds, edge_width=0.15 if outlines else 0.0,
        ))
    st.caption(
        "Same frame and same palette on both sides: a colour means the same crop group on "
        "both maps. Light grey is unallocated land."
    )
else:
    st.pyplot(maps.build_change_figure(
        polygons, observed, simulated,
        title=f"Land-use change — {chosen_name}", bounds=bounds,
    ))
    st.caption(
        "Compared at the level of the 12 observed RPG groups: a plot moving from one technical "
        "variant to another within the same group counts as unchanged, for lack of a finer "
        "resolution on the observed side."
    )

st.warning(
    "**What this map does not say.** The model's plot set and the GIS layer share no "
    "identifier: the join is rebuilt from a farm signature (commune + area). It places 99.4 % "
    "of plots, but about 1 557 of them share commune AND area with a neighbour of the same "
    "farm and may have been swapped. Territorial and regional readings are reliable; **a "
    "single plot proves nothing**."
)

with st.expander("Breakdown of located areas"):
    surface = plots.loc[list(polygons), "SURF_HA"]
    table = pd.DataFrame({
        "plots": [len(polygons)],
        "area (ha)": [round(float(surface.sum()), 1)],
        "median area (ha)": [round(float(surface.median()), 2)],
    })
    st.dataframe(table, width="stretch", hide_index=True)
