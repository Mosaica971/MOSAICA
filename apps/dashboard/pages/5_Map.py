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

st.set_page_config(page_title="MOSAICA -- Carte", layout="wide")
st.title("Carte des cultures")

if not LAYER.exists():
    st.error(
        f"Couche parcellaire absente : `{RPG_LAYER}`.\n\n"
        "Cette page a besoin du dossier `data/gis/`, non versionné comme tout `data/`. "
        "Copiez-le à la racine du dépôt."
    )
    st.stop()


@st.cache_resource(show_spinner="Lecture du parcellaire…")
def _geometry():
    """Polygons keyed by plot id, plus the plot attribute table.

    cache_resource, not cache_data: the join is ~25 000 polygon objects, rebuilt in about a
    second but not worth copying on every widget change.
    """
    from case_studies.guadeloupe.pipeline.data_pipeline import SETS_DIR, TABLES_DIR
    from core.data.readers import read_mapping_set, read_wide_table

    parc = read_wide_table(TABLES_DIR / "Data_Parc_Gwad_2017.txt")
    expl = read_mapping_set(SETS_DIR / "EXPL_PARC_2017.set", "farm", "plot")
    join = build_geometry_join(parc, expl.set_index("plot")["farm"], LAYER)
    return join, parc


join, parc = _geometry()

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run dans `outputs/` — lancez `python main.py` d'abord.")
    st.stop()

with st.sidebar:
    st.header("Carte")
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

    island_codes = sorted(parc["ILE"].dropna().unique().tolist())
    island = st.selectbox(
        "Île", ["Toutes", *island_codes],
        format_func=lambda v: v if v == "Toutes" else ISLAND_LABELS.get(str(int(v)), str(v)),
    )
    region_codes = sorted(parc["REGION"].dropna().unique().tolist())
    region = st.selectbox(
        "Région", ["Toutes", *region_codes],
        format_func=lambda v: v if v == "Toutes" else REGION_LABELS.get(str(int(v)), str(v)),
    )
    view = st.radio(
        "Vue", ("Observé vs simulé", "Ce qui a changé"), index=0,
        help="La seconde vue répond à une question que deux mosaïques côte à côte ne "
        "permettent pas de lire : quelles parcelles ont changé d'usage.",
    )
    outlines = st.checkbox("Contours des parcelles", value=False)

st.caption(f"Jointure parcellaire : {join.summary(len(parc))}")

selected = set(parc.index)
if island != "Toutes":
    selected &= set(parc.index[parc["ILE"] == island])
if region != "Toutes":
    selected &= set(parc.index[parc["REGION"] == region])

polygons = maps.filter_polygons(join.polygons, selected)
if not polygons:
    st.warning("Aucune parcelle localisée pour cette sélection.")
    st.stop()
bounds = maps.shared_bounds(polygons)


def _allocation(side: str) -> dict[str, str]:
    frame = loaders.load_csv(run_dir, f"allocation_{side}.csv")
    if frame is None:
        return {}
    return dict(zip(frame["plot"].astype(str), frame["crop"].astype(str)))


observed, simulated = _allocation("input"), _allocation("output")
if not observed and not simulated:
    st.warning(f"{run_dir.name} ne contient pas d'allocation exploitable.")
    st.stop()

if view == "Observé vs simulé":
    left, right = st.columns(2)
    with left:
        st.pyplot(maps.build_map_figure(
            polygons, observed, title="Observé 2017",
            bounds=bounds, edge_width=0.15 if outlines else 0.0,
        ))
    with right:
        st.pyplot(maps.build_map_figure(
            polygons, simulated, title=f"Simulé — {chosen_name}",
            bounds=bounds, edge_width=0.15 if outlines else 0.0,
        ))
    st.caption(
        "Même cadre et même palette des deux côtés : une couleur désigne le même groupe de "
        "cultures sur les deux cartes. Le gris clair est la terre non allouée."
    )
else:
    st.pyplot(maps.build_change_figure(
        polygons, observed, simulated,
        title=f"Changement d'usage — {chosen_name}", bounds=bounds,
    ))
    st.caption(
        "Comparaison au niveau des 12 groupes RPG observés : une parcelle qui passe d'une "
        "variante technique à une autre du même groupe compte comme inchangée, faute de "
        "résolution plus fine côté observé."
    )

st.warning(
    "**Ce que cette carte ne dit pas.** Le jeu parcellaire du modèle et la couche SIG n'ont "
    "pas d'identifiant commun : la jointure est reconstruite par signature d'exploitation "
    "(commune + surface). Elle place 99,4 % des parcelles, mais environ 1 557 d'entre elles "
    "partagent commune ET surface avec une voisine de la même exploitation et peuvent avoir "
    "été interverties. Les lectures territoriales et régionales sont fiables ; **une parcelle "
    "isolée ne fait pas preuve**."
)

with st.expander("Répartition des surfaces localisées"):
    surface = parc.loc[list(polygons), "SURF_HA"]
    table = pd.DataFrame({
        "parcelles": [len(polygons)],
        "surface (ha)": [round(float(surface.sum()), 1)],
        "surface médiane (ha)": [round(float(surface.median()), 2)],
    })
    st.dataframe(table, width="stretch", hide_index=True)
