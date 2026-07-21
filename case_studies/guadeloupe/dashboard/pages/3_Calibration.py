"""Calibration page: how close a run's allocation is to the observed 2017 land use.

Read-only, like every other page. Displays what generate_report (or
scripts/evaluate_calibration.py) already wrote; computes nothing. Run the dashboard from
the repo root with:  streamlit run case_studies/guadeloupe/dashboard/app.py
"""

import sys
from pathlib import Path

# Streamlit runs each page as its own top-level script, so (like app.py) the repo root must
# be on sys.path before importing `case_studies...`.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from case_studies.guadeloupe.dashboard import loaders
from case_studies.guadeloupe.domain.crop_labels import label_for
from case_studies.guadeloupe.domain.farm_typology import TYPE_EXPL_LABELS
from case_studies.guadeloupe.domain.zones import region_label

OUTPUTS_ROOT = _REPO_ROOT / "outputs"
TOTAL_KEY = "TOTAL"

st.set_page_config(page_title="MOSAICA -- Calibration", layout="wide")
st.title("Calibration : observé 2017 vs simulé")
st.caption(
    "Écart mesuré au niveau des 12 groupes RPG observés, d'après Chopin et al. (2015) "
    "section 2.6. Le PAD est le pourcentage d'écart absolu entre la surface observée et la "
    "surface simulée ; il vaut 0 quand la simulation reproduit exactement l'observé."
)

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run trouvé dans `outputs/`.")
    st.stop()

labels = {loaders.run_display_name(run, loaders.load_recap(run)): run for run in runs}
selected = st.selectbox("Run", list(labels))
run_dir = labels[selected]

pad_by_crop = loaders.load_calibration(run_dir, "pad_by_crop")
if pad_by_crop is None:
    st.warning(
        "Ce run n'a pas encore été scoré. Lancez :\n\n"
        f"```\npython scripts/evaluate_calibration.py {run_dir.as_posix()}\n```"
    )
    st.stop()

recap = loaders.load_recap(run_dir)
calib = recap.get("calibration", {})
thresholds = calib.get("thresholds", {})


def _pct(value) -> str:
    """Percentages come from recap.json, where an undefined metric is null."""
    return "n/a" if value is None else f"{value:.1f} %"


def _verdict(passed: bool) -> str:
    return "OK" if passed else "hors seuil"


st.subheader("Verdicts")
left, middle, right = st.columns(3)
left.metric(
    f"PAD territorial (seuil {thresholds.get('regional_pad_max', 15):.0f} %)",
    _pct(calib.get("regional_pad_pct")),
    _verdict(calib.get("regional_within_threshold", False)),
    delta_color="off",
)
middle.metric(
    f"Types d'exploitation (seuil {thresholds.get('farm_type_match_min', 80):.0f} %)",
    _pct(calib.get("farm_type_match_pct")),
    _verdict(calib.get("farm_type_within_threshold", False)),
    delta_color="off",
)
right.metric(
    "Parcelles bien simulées",
    _pct(calib.get("plot_match_pct")),
    f"{_pct(calib.get('area_match_pct'))} de la surface",
    delta_color="off",
)

st.subheader("Échelle régionale — surface par culture")
regional = pad_by_crop.copy()
regional["culture"] = [
    key if key == TOTAL_KEY else label_for(str(key)) for key in regional["crop"]
]
st.dataframe(
    regional[["culture", "observed_ha", "simulated_ha", "abs_deviation_ha", "pad_pct"]]
    .style.background_gradient(subset=["pad_pct"], cmap="RdYlGn_r", vmin=0, vmax=100)
    .format(precision=1),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Échelle sous-régionale — PAD (%) par région et culture")
subregional = loaders.load_calibration(run_dir, "pad_by_crop_and_region")
if subregional is not None:
    grid = subregional[subregional["crop"] != TOTAL_KEY].pivot(
        index="region", columns="crop", values="pad_pct"
    )
    grid.index = [region_label(key) for key in grid.index]
    grid.columns = [label_for(str(key)) for key in grid.columns]
    st.dataframe(
        grid.style.background_gradient(cmap="RdYlGn_r", vmin=0, vmax=100).format(precision=1),
        use_container_width=True,
    )

st.subheader("Échelle exploitation — types observés vs simulés")
confusion = loaders.load_calibration(run_dir, "farm_type_confusion")
if confusion is not None:
    matrix = confusion.set_index("type_observe")
    matrix.index = [TYPE_EXPL_LABELS.get(int(key), key) for key in matrix.index]
    matrix.columns = [TYPE_EXPL_LABELS.get(int(key), key) for key in matrix.columns]
    # Hide the types nobody starts in and nobody lands in, so the 10x10 universe does not
    # drown the handful of rows that carry farms.
    matrix = matrix.loc[matrix.sum(axis=1) > 0, matrix.sum(axis=0) > 0]
    st.dataframe(matrix.style.background_gradient(cmap="Blues"), use_container_width=True)
    st.caption(
        "Lignes : type observé en 2017. Colonnes : type après simulation. La diagonale est "
        "la part correctement reproduite (Chopin et al. 2015, Table 4)."
    )

st.subheader("Échelle parcelle — concordance par sous-région")
field = loaders.load_calibration(run_dir, "field_match")
if field is not None:
    shown = field.copy()
    shown["sous-région"] = [
        key if key == TOTAL_KEY else region_label(key) for key in shown["region"]
    ]
    st.dataframe(
        shown[
            [
                "sous-région",
                "matched_plots",
                "total_plots",
                "plot_match_pct",
                "matched_ha",
                "total_ha",
                "area_match_pct",
            ]
        ].style.format(precision=1),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Échelle exploitation — distribution du PAD")
by_farm = loaders.load_calibration(run_dir, "pad_by_farm")
if by_farm is not None:
    threshold = thresholds.get("farm_pad_max", 20)
    within = int((by_farm["pad_pct"] <= threshold).sum())
    st.write(
        f"{within} exploitations sur {len(by_farm)} sous le seuil de {threshold:.0f} %."
    )
    # Clipped at 200%: a handful of farms deviate by far more, and their tail would flatten
    # the bulk of the distribution into a single bar.
    st.bar_chart(
        by_farm["pad_pct"]
        .clip(upper=200)
        .value_counts(bins=20)
        .sort_index()
        .rename("exploitations")
    )
