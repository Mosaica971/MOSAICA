"""Comparison page: put several runs (and their input/output sides) side by side.

Read-only, like the single-run home page. Every data operation goes through the tested pure
helpers in dashboard/comparison.py; this file only wires them to Streamlit widgets. Run the
dashboard from the repo root with:  streamlit run case_studies/guadeloupe/dashboard/app.py
(the pages/ folder is discovered automatically).
"""

import sys
from functools import partial
from pathlib import Path

# Streamlit runs each page as its own top-level script, so (like app.py) the repo root must
# be on sys.path before importing `case_studies...`.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from case_studies.guadeloupe.domain.crop_labels import CROP_LABELS
from case_studies.guadeloupe.dashboard import comparison, loaders

OUTPUTS_ROOT = _REPO_ROOT / "outputs"
SIDES = ("output", "input")

# Per-run scalar indicators for the development profile: economics totals (per side), the
# run's Gini (output-based, same for every side), and environmental totals (per side).
_ECON_INDICATORS = {
    "total_production_tonnes": "Production (t)",
    "total_revenue": "Revenu (€)",
    "total_gross_margin": "Marge brute (€)",
    "total_net_revenue": "Revenu net (€)",
    "total_subsidy": "Subvention (€)",
    "total_labor_cost": "Coût MO (€)",
    "total_etp": "Emploi (ETP)",
}
_ENV_INDICATORS = {
    "total_ges": "GES (t CO₂)",
    "total_ift": "IFT (total)",
    "total_azote": "Azote (kg N)",
    "surface_cld": "Surface chlordécone (ha)",
    "total_water_need_m3": "Besoin en eau (m³)",
    # These two are strongly correlated (balance = inputs - mineralization, and inputs are
    # near-constant), so selecting both roughly doubles soil carbon's weight in the score.
    "soil_carbon_balance": "Bilan carbone du sol (t C)",
    "soil_carbon_mineralization": "Minéralisation du carbone (t C)",
}
# Food self-sufficiency ratios (crop-only variant), all benefit (higher = more autonomous).
# The limiting nutrient is the headline autonomy score; per-nutrient keys map to
# recap['food_autonomy'][side]['crop_only'][<nutrient>].
_AUTONOMY_INDICATORS = {
    "autonomy_limiting": "Autonomie (nutriment limitant)",
    "autonomy_kcal": "Autonomie énergie (Kcal)",
    "autonomy_prot": "Autonomie protéines",
    "autonomy_lip": "Autonomie lipides",
    "autonomy_glu": "Autonomie glucides",
    "autonomy_fibres": "Autonomie fibres",
    "autonomy_ca": "Autonomie calcium",
    "autonomy_p": "Autonomie phosphore",
    "autonomy_mg": "Autonomie magnésium",
    "autonomy_k": "Autonomie potassium",
    "autonomy_fe": "Autonomie fer",
}
# Exposure of a fixed allocation to shocks -- nothing is re-optimized, so this is exposure,
# not adaptive capacity. Note: each absolute value and its ratio are near-collinear
# (same numerator), so selecting both roughly doubles that axis's weight in the composite
# score. Same trap that got the water peak-month indicator dropped in spec 1.
_RESILIENCE_INDICATORS = {
    "climate_margin_at_risk": "Marge à risque climatique (€)",
    "climate_margin_at_risk_ratio": "Marge à risque climatique (part)",
    "revenue_concentration_hhi": "Concentration du revenu (HHI)",
    "price_shock_margin_loss": "Perte sous choc de prix (€)",
    "price_shock_margin_loss_ratio": "Perte sous choc de prix (part)",
}
_GINI_KEY = "gini_revenue_by_farm"
_INDICATOR_LABELS = {
    **_ECON_INDICATORS, **_ENV_INDICATORS, **_AUTONOMY_INDICATORS,
    **_RESILIENCE_INDICATORS,
    _GINI_KEY: "Gini (revenu/exploit.)",
}


def _indicator_value(recap: dict, side: str, indicator: str):
    """Scalar value of an indicator for one (run, side): Gini from the run root,
    environmental totals from recap['environment'][side], food-autonomy ratios (crop-only)
    from recap['food_autonomy'][side], exposure indicators from recap['resilience'][side],
    everything else from recap['economics'][side]. Missing blocks (older runs) yield None."""
    if indicator == _GINI_KEY:
        return recap.get(_GINI_KEY)
    if indicator in _ENV_INDICATORS:
        return (recap.get("environment") or {}).get(side, {}).get(indicator)
    if indicator in _RESILIENCE_INDICATORS:
        return (recap.get("resilience") or {}).get(side, {}).get(indicator)
    if indicator in _AUTONOMY_INDICATORS:
        auto = (recap.get("food_autonomy") or {}).get(side, {})
        if indicator == "autonomy_limiting":
            return auto.get("limiting_crop_only")
        return auto.get("crop_only", {}).get(indicator[len("autonomy_"):])
    return (recap.get("economics") or {}).get(side, {}).get(indicator)

st.set_page_config(page_title="MOSAICA -- Comparaison", layout="wide")
st.title("Comparaison de scénarios")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run trouvé dans `outputs/` -- lancez `python main.py` d'abord.")
    st.stop()


def _discover_series() -> dict[str, dict]:
    """Label -> {run_dir, side, recap} for every (run, side) that has a facts table.
    Runs are labelled by their recap `run_name` (folder name as fallback); a base label
    shared by two runs (same run_name and side) is disambiguated with the folder name."""
    entries: list[dict] = []
    base_rows: list[tuple[str, str]] = []
    for run_dir in runs:
        try:
            recap = loaders.load_recap(run_dir)
        except (OSError, ValueError):
            recap = {}
        display_name = loaders.run_display_name(run_dir, recap)
        for side in SIDES:
            if loaders.load_facts(run_dir, side) is None:
                continue
            entries.append({"run_dir": run_dir, "side": side, "recap": recap})
            base_rows.append((comparison.series_label(display_name, side), run_dir.name))
    labels = comparison.series_labels(base_rows)
    return {label: entry for label, entry in zip(labels, entries)}


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

# Per-scenario color, chosen freely and reused across every chart on the page (grouped bars +
# indicator panels). Keyed by series label so a choice sticks as long as the series is shown.
with st.expander("Couleurs des scénarios"):
    series_colors: dict[str, str] = {}
    picker_cols = st.columns(min(len(selected), 4))
    for idx, lbl in enumerate(selected):
        default_hex = comparison.SERIES_PALETTE_HEX[idx % len(comparison.SERIES_PALETTE_HEX)]
        series_colors[lbl] = picker_cols[idx % len(picker_cols)].color_picker(
            lbl, value=default_hex, key=f"color_{lbl}"
        )


def _crop_universe() -> tuple[list[str], bool]:
    """Full CULT_2017 crop list and whether it came from a run recap. Prefers any selected run's
    recap (authoritative for that run); for runs predating the `crop_universe` recap field, falls
    back to the crop-label catalogue so the zeros toggle still works (may not match that run's
    exact model set)."""
    for lbl in selected:
        universe = series_catalog[lbl]["recap"].get("crop_universe")
        if universe:
            return list(universe), True
    return list(CROP_LABELS), False


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

opt = st.columns(3)
include_zeros = opt[0].checkbox("Inclure les valeurs nulles", value=False)
relative = opt[1].checkbox("Part relative (%)", value=False, disabled=not stacked)
log = opt[2].checkbox("Échelle log (mode groupé)", value=False, disabled=stacked)

pivots = [
    (lbl, comparison.pivot_measure(loaders.load_facts(
        series_catalog[lbl]["run_dir"], series_catalog[lbl]["side"]), x_dim, measure, stack_by))
    for lbl in selected
]

# Full x-axis universe for exhaustive (zeros-included) axes. Crops come from the recap (or the
# label-catalogue fallback for old runs); region/island from their fixed code sets.
crop_universe, universe_from_recap = _crop_universe()
if x_dim == "culture":
    universe: list = sorted({comparison.culture_of(c) for c in crop_universe})
elif x_dim == "subculture":
    universe = list(crop_universe)
elif x_dim == "region":
    universe = list(comparison.REGION_CODES)
else:
    universe = list(comparison.ISLAND_CODES)

# Sort crop axes by value (biggest crops first); keep region/island in code order.
sort_by_value = x_dim in ("culture", "subculture")
categories = comparison.ordered_categories(pivots, universe, include_zeros, sort_by_value)

ceiling = comparison.shared_bar_ceiling([p for _, p in pivots])
floor = comparison.positive_floor([p for _, p in pivots])
horizontal = x_dim == "subculture"  # ~70 long codes read far better as horizontal bars

fig = comparison.build_grouped_bar_figure(
    pivots,
    measure_label=comparison.MEASURE_LABELS[measure],
    x_axis_label=comparison.X_DIMENSION_LABELS[x_dim],
    stacked=stacked, log=log, ceiling=ceiling, floor=floor,
    categories=categories, horizontal=horizontal, relative=(relative and stacked),
    series_colors=series_colors,
    format_x=partial(comparison.format_dim_value, x_dim),
    format_stack=partial(comparison.format_dim_value, stack_by),
)
st.pyplot(fig)
if include_zeros and x_dim in ("culture", "subculture") and not universe_from_recap:
    st.caption(
        "Valeurs nulles issues du catalogue de cultures (ce run est antérieur au champ "
        "`crop_universe` du recap) : la liste peut différer du jeu exact du modèle. "
        "Relancez `python main.py` pour l'axe exhaustif fidèle au run."
    )
if stacked:
    st.caption("Ordre des barres dans chaque groupe : " + " · ".join(selected))

# ---------------------------------------------------- Development-indicator profile
st.header("Profil des indicateurs de développement")
chosen = st.multiselect(
    "Indicateurs", list(_INDICATOR_LABELS),
    default=["total_revenue", _GINI_KEY],
    format_func=lambda i: _INDICATOR_LABELS[i],
)
if not chosen:
    st.info("Choisissez au moins un indicateur.")
else:
    rows = {}
    for lbl in selected:
        recap = series_catalog[lbl]["recap"]
        side = series_catalog[lbl]["side"]
        rows[lbl] = {ind: _indicator_value(recap, side, ind) for ind in chosen}
    raw = pd.DataFrame.from_dict(rows, orient="index")[chosen].dropna(axis=1, how="any")
    if raw.shape[1] < 1:
        st.warning("Indicateurs indisponibles pour ces séries (runs trop anciens ?).")
    else:
        st.pyplot(
            comparison.build_indicator_parallel_axes_figure(
                raw, _INDICATOR_LABELS, series_colors
            )
        )
        st.caption(
            "Coordonnées parallèles : un axe vertical par indicateur, chacun à son échelle "
            "native (pas de normalisation). Une ligne = un scénario (couleur choisie ci-dessus)."
        )

        # -------------------------------------------------- Composite score
        st.subheader("Score agrégé")
        st.caption(
            "Chaque indicateur est normalisé (min-max) sur les séries affichées, 1 = meilleur "
            "du lot ; les indicateurs « coût » (GES, IFT, azote, chlordécone, subvention, coût "
            "MO, Gini) sont inversés. Score = moyenne pondérée. Réglez les poids ci-dessous."
        )
        weights: dict[str, float] = {}
        weight_cols = st.columns(min(len(raw.columns), 4))
        for idx, ind in enumerate(raw.columns):
            weights[ind] = weight_cols[idx % len(weight_cols)].slider(
                _INDICATOR_LABELS[ind], min_value=0.0, max_value=1.0, value=1.0, step=0.05,
                key=f"weight_{ind}",
            )
        scores = comparison.compute_composite_scores(raw, weights).sort_values()
        score_colors = [series_colors.get(lbl) for lbl in scores.index]
        fig, ax = plt.subplots(figsize=(7, 0.5 * len(scores) + 1))
        ax.barh(range(len(scores)), scores.to_numpy(), color=score_colors)
        ax.set_yticks(range(len(scores)))
        ax.set_yticklabels(list(scores.index))
        ax.set_xlim(0, 1)
        ax.set_xlabel("Score agrégé (0–1)")
        for y, value in enumerate(scores.to_numpy()):
            ax.text(min(value + 0.01, 0.98), y, f"{value:.2f}", va="center", fontsize=8)
        fig.tight_layout()
        st.pyplot(fig)

# ---------------------------------------------------- Food self-sufficiency panel
st.header("Autonomie alimentaire")
_autonomy = {
    lbl: (series_catalog[lbl]["recap"].get("food_autonomy") or {}).get(
        series_catalog[lbl]["side"], {}
    )
    for lbl in selected
}
_autonomy = {lbl: auto for lbl, auto in _autonomy.items() if auto}
if not _autonomy:
    st.info(
        "Aucune série sélectionnée ne porte le bloc `food_autonomy` (runs antérieurs à cette "
        "fonctionnalité). Relancez `python main.py` pour un run comparable."
    )
else:
    variant_label = st.radio(
        "Variante", ["Cultures seules", "Avec pêche"], horizontal=True
    )
    variant = "with_fishing" if variant_label == "Avec pêche" else "crop_only"
    frame = comparison.autonomy_ratios_frame(_autonomy, variant)
    st.caption(
        "Ratio production locale / besoin de la population, par nutriment. Une valeur ≥ 1 "
        "(ligne pointillée) = auto-suffisance pour ce nutriment. Le nutriment le plus bas "
        "borne l'autonomie globale."
    )
    fig_auto, ax_auto = plt.subplots(figsize=(9, 4))
    nutrients = list(frame.index)
    x = range(len(nutrients))
    n_series = max(len(frame.columns), 1)
    width = 0.8 / n_series
    for s_idx, lbl in enumerate(frame.columns):
        offsets = [i + (s_idx - (n_series - 1) / 2) * width for i in x]
        ax_auto.bar(
            offsets, frame[lbl].to_numpy(), width=width,
            color=series_colors.get(lbl), label=lbl,
        )
    ax_auto.axhline(1.0, color="grey", linestyle="--", linewidth=1)
    ax_auto.set_xticks(list(x))
    ax_auto.set_xticklabels(nutrients, rotation=45, ha="right")
    ax_auto.set_ylabel("Ratio production / besoin")
    ax_auto.legend(fontsize=8)
    fig_auto.tight_layout()
    st.pyplot(fig_auto)
