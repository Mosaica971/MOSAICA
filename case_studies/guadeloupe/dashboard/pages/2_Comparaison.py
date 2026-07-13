"""Comparison page: put several runs (and their input/output sides) side by side.

Read-only, like the single-run home page. Every data operation goes through the tested pure
helpers in dashboard/comparison.py; this file only wires them to Streamlit widgets. Run the
dashboard from the repo root with:  streamlit run case_studies/guadeloupe/dashboard/app.py
(the pages/ folder is discovered automatically).
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from case_studies.guadeloupe.crop_labels import label_for
from case_studies.guadeloupe.dashboard import comparison, loaders

OUTPUTS_ROOT = Path(__file__).resolve().parents[4] / "outputs"
SIDES = ("output", "input")

# Per-run scalar indicators for the development profile: economics totals (per side) plus the
# run's Gini (output-based, same for every side of a run).
_ECON_INDICATORS = {
    "total_production_tonnes": "Production (t)",
    "total_revenue": "Revenu (€)",
    "total_gross_margin": "Marge brute (€)",
    "total_net_revenue": "Revenu net (€)",
    "total_subsidy": "Subvention (€)",
    "total_labor_cost": "Coût MO (€)",
    "total_etp": "Emploi (ETP)",
}
_GINI_KEY = "gini_revenue_by_farm"
_INDICATOR_LABELS = {**_ECON_INDICATORS, _GINI_KEY: "Gini (revenu/exploit.)"}

st.set_page_config(page_title="MOSAICA -- Comparaison", layout="wide")
st.title("Comparaison de scénarios")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run trouvé dans `outputs/` -- lancez `python main.py` d'abord.")
    st.stop()


def _discover_series() -> dict[str, dict]:
    """Label -> {run_dir, side, recap} for every (run, side) that has a facts table."""
    found: dict[str, dict] = {}
    for run_dir in runs:
        try:
            recap = loaders.load_recap(run_dir)
        except (OSError, ValueError):
            recap = {}
        data = recap.get("data", {})
        for side in SIDES:
            if loaders.load_facts(run_dir, side) is None:
                continue
            label = comparison.series_label(
                run_dir.name, side, data.get("year", "?"), data.get("scenario", "?")
            )
            found[label] = {"run_dir": run_dir, "side": side, "recap": recap}
    return found


series_catalog = _discover_series()
if not series_catalog:
    st.warning(
        "Les runs présents n'ont pas de table `facts_*.csv` (antérieurs à cette fonctionnalité). "
        "Relancez `python main.py` pour un run comparable."
    )
    st.stop()

default = [lbl for lbl in series_catalog if "sortie" in lbl] or list(series_catalog)
selected = st.multiselect(
    "Séries à comparer (run × côté)", list(series_catalog), default=default
)
if not selected:
    st.info("Sélectionnez au moins une série.")
    st.stop()

# ---------------------------------------------------------------- Bar comparison
st.header("Barres comparées")
ctrl = st.columns(4)
x_dim = ctrl[0].selectbox(
    "Axe des abscisses", comparison.X_DIMENSIONS,
    format_func=lambda d: comparison.X_DIMENSION_LABELS[d],
)
measure = ctrl[1].selectbox(
    "Mesure (ordonnées)", list(comparison.MEASURE_LABELS),
    format_func=lambda m: comparison.MEASURE_LABELS[m],
)
stack_options = ["none"] + [d for d in ("subculture", "region", "island", "culture") if d != x_dim]
stack_by = ctrl[2].selectbox(
    "Empiler par", stack_options,
    format_func=lambda s: "— aucun —" if s == "none" else comparison.X_DIMENSION_LABELS.get(s, s),
)
stacked = stack_by != "none"
log = ctrl[3].checkbox("Échelle log (mode groupé)", value=False, disabled=stacked)

pivots = [
    (lbl, comparison.pivot_measure(loaders.load_facts(
        series_catalog[lbl]["run_dir"], series_catalog[lbl]["side"]), x_dim, measure, stack_by))
    for lbl in selected
]
ceiling = comparison.shared_bar_ceiling([p for _, p in pivots])
floor = comparison.positive_floor([p for _, p in pivots])
format_x = (lambda c: label_for(str(c))) if x_dim in ("culture", "subculture") else str

fig = comparison.build_grouped_bar_figure(
    pivots,
    measure_label=comparison.MEASURE_LABELS[measure],
    x_axis_label=comparison.X_DIMENSION_LABELS[x_dim],
    stacked=stacked, log=log, ceiling=ceiling, floor=floor, format_x=format_x,
)
st.pyplot(fig)
if stacked:
    st.caption("Ordre des barres dans chaque groupe : " + " · ".join(selected))

# ---------------------------------------------------- Development-indicator profile
st.header("Profil des indicateurs de développement")
chosen = st.multiselect(
    "Indicateurs", list(_INDICATOR_LABELS),
    default=["total_net_revenue", "total_etp", "total_production_tonnes", _GINI_KEY],
    format_func=lambda i: _INDICATOR_LABELS[i],
)
if len(chosen) < 2:
    st.info("Choisissez au moins deux indicateurs pour tracer le profil.")
else:
    rows = {}
    for lbl in selected:
        recap = series_catalog[lbl]["recap"]
        side = series_catalog[lbl]["side"]
        econ = (recap.get("economics") or {}).get(side, {})
        rows[lbl] = {
            ind: (recap.get(_GINI_KEY) if ind == _GINI_KEY else econ.get(ind))
            for ind in chosen
        }
    raw = pd.DataFrame.from_dict(rows, orient="index")[chosen].dropna(axis=1, how="any")
    if raw.shape[1] < 2:
        st.warning("Indicateurs indisponibles pour ces séries (runs trop anciens ?).")
    else:
        normalized = comparison.normalize_columns(raw)
        st.pyplot(
            comparison.build_parallel_coordinates_figure(normalized, raw, _INDICATOR_LABELS)
        )
