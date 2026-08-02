"""Prospective page: read a policy x forcing grid rather than a flat list of runs.

A crossed batch produces up to 110 runs, which the Comparaison page cannot show -- it asks
you to tick series one by one. Here the two axes are filters, and the four views answer the
questions the crossing was built for: how much does each forcing hurt each policy (heatmap),
which policies are good AND hold up (scatter), which shock hurts a given policy most
(tornado), and what the numbers are (table).

Read-only, like every other page. All data logic goes through the tested pure helpers in
dashboard/prospective.py and core/reporting/robustness.py; this file only wires widgets.
Run from the repo root:  streamlit run apps/dashboard/app.py
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import streamlit as st

from apps.dashboard import comparison, loaders, prospective
from core.reporting import robustness

OUTPUTS_ROOT = _REPO_ROOT / "outputs"

st.set_page_config(page_title="MOSAICA -- Prospective", layout="wide")
st.title("Prospective : politiques × forçages")


@st.cache_data(show_spinner="Lecture des runs…")
def _load_grid_entries(root_str: str) -> list[dict]:
    """Every run that carries grid coordinates, as [{policy, forcing, recap, folder}].

    Cached: a crossed batch is 110 folders and this page re-runs on every widget change.
    Only recap.json is read -- never the facts tables, which is what makes it fast.
    """
    entries: list[dict] = []
    for run_dir in loaders.list_output_runs(Path(root_str)):
        try:
            recap = loaders.load_recap(run_dir)
        except (OSError, ValueError):
            continue
        coordinates = prospective.grid_coordinates(recap, run_dir.name)
        if coordinates is None:
            continue
        policy, forcing = coordinates
        entries.append(
            {"policy": policy, "forcing": forcing, "recap": recap, "folder": run_dir.name}
        )
    return entries


entries = _load_grid_entries(str(OUTPUTS_ROOT))
if not entries:
    st.info(
        "Aucun run de grille trouvé dans `outputs/`. Cette page lit les runs produits par "
        "un plan politique × forçage :\n\n"
        "```\npython scripts/run_scenarios.py --scenarios "
        "case_studies/guadeloupe/plan.yaml\n```\n\n"
        "Un run est reconnu s'il porte `run_policy` / `run_forcing` dans son recap, ou si "
        "son nom suit la convention `Politique__Forcage`."
    )
    st.stop()

all_policies = sorted({e["policy"] for e in entries})
all_forcings = sorted({e["forcing"] for e in entries})

# ------------------------------------------------------------------ Controls
with st.sidebar:
    st.header("Grille")
    policies = st.multiselect("Politiques", all_policies, default=all_policies)
    forcings = st.multiselect("Forçages", all_forcings, default=all_forcings)
    side = st.radio("Côté", ("output", "input"), horizontal=True,
                    format_func=lambda s: {"output": "sortie", "input": "entrée"}[s])
    indicator = st.selectbox(
        "Indicateur", list(comparison.INDICATOR_LABELS),
        index=list(comparison.INDICATOR_LABELS).index("total_gross_margin"),
        format_func=lambda i: comparison.INDICATOR_LABELS[i],
    )
    nominal = st.selectbox(
        "Forçage de référence", forcings or all_forcings,
        index=(forcings or all_forcings).index("F0_nominal")
        if "F0_nominal" in (forcings or all_forcings) else 0,
        help="Le forçage neutre, dénominateur de la rétention et origine du tornado.",
    )

if not policies or not forcings:
    st.warning("Sélectionnez au moins une politique et un forçage.")
    st.stop()

direction = comparison.INDICATOR_DIRECTION.get(indicator, "benefit")
higher_is_better = direction != "cost"
label = comparison.INDICATOR_LABELS[indicator]

kept = [e for e in entries if e["policy"] in policies and e["forcing"] in forcings]
grid = prospective.build_grid(
    kept, lambda e: comparison.indicator_value(e["recap"], side, indicator)
)
frame = prospective.grid_frame(grid, policies, forcings)

if frame.isna().all().all():
    st.warning(
        f"« {label} » n'est disponible dans aucun run de la grille — les runs sont sans doute "
        "antérieurs au bloc de recap qui le porte. Relancez le batch."
    )
    st.stop()

st.caption(
    f"**{len(kept)} runs** · indicateur : {label} · sens : "
    + ("plus haut = mieux" if higher_is_better else "plus bas = mieux")
    + f" · référence : {nominal}"
)

# A cell that a constraint pins is the scenario's hypothesis, not its result.
_pinned = {
    e["policy"] for e in kept if indicator in comparison.bound_indicators(e["recap"])
}
if _pinned:
    st.warning(
        f"« {label} » est **fixé par une contrainte** dans : {', '.join(sorted(_pinned))}. "
        "Pour ces politiques la valeur est une hypothèse imposée, pas un résultat — leur "
        "robustesse sur cet indicateur ne dit rien de leur robustesse tout court."
    )

# ------------------------------------------------------------------ Heatmap
st.header("Grille politique × forçage")
mode_label = st.radio(
    "Lecture",
    ("Valeur brute", "% du nominal de la politique", "Regret (% du meilleur du forçage)"),
    horizontal=True,
)
mode = {
    "Valeur brute": "absolute",
    "% du nominal de la politique": "vs_nominal",
    "Regret (% du meilleur du forçage)": "regret",
}[mode_label]

normalised = robustness.normalise_grid(
    grid, mode, higher_is_better=higher_is_better, nominal_forcing=nominal
)
display_frame = prospective.grid_frame(normalised, policies, forcings)

if mode == "absolute":
    st.pyplot(prospective.build_heatmap_figure(
        display_frame, title=label, colorbar_label=label,
        higher_is_better=higher_is_better, value_format="{:,.0f}",
    ))
    st.caption(
        "Valeurs telles quelles. Les colonnes ne sont pas comparables entre elles si les "
        "forçages changent l'échelle de l'indicateur — pour comparer les politiques *entre "
        "elles* sous un même forçage, préférez le regret."
    )
else:
    st.pyplot(prospective.build_heatmap_figure(
        display_frame * 100, title=label, colorbar_label="%",
        higher_is_better=True, centre=100.0, value_format="{:,.0f}",
    ))
    st.caption(
        "Part conservée de la valeur non forcée de **chaque politique** : 100 % = le forçage "
        "ne coûte rien, 60 % = la politique perd 40 % de sa propre promesse. Ne dit rien du "
        "niveau — une politique médiocre et stable est ici à 100 %."
        if mode == "vs_nominal" else
        "Écart au **meilleur résultat obtenu par une politique quelconque sous ce même "
        "forçage** (critère de Savage) : 100 % = c'était le bon choix pour ce forçage, 70 % "
        "= on laisse 30 % sur la table. Chaque colonne contient au moins un 100 %."
    )
st.caption("Cellule hachurée « n/a » = pas de solution (infaisable), pas une donnée manquante.")

# ------------------------------------------------------------------ Robustness
st.header("Performance et robustesse")
threshold_help = (
    "Seuil de viabilité, dans l'unité de l'indicateur. La colonne « Viabilité » compte la "
    "part des forçages où la politique le tient ; un forçage infaisable compte comme un échec."
)
default_threshold = float(pd.Series(frame.to_numpy().ravel()).dropna().median())
viability_threshold = st.number_input(
    "Seuil de viabilité", value=default_threshold, help=threshold_help
)

summaries = robustness.summarise_grid(
    grid,
    higher_is_better=higher_is_better,
    nominal_forcing=nominal,
    viability_threshold=viability_threshold,
    policies=policies,
)

st.pyplot(prospective.build_performance_robustness_figure(
    summaries, performance_label=label
))
st.caption(
    "Abscisse : la valeur sous le forçage de référence. Ordonnée : la part de cette valeur "
    "encore obtenue dans le pire forçage. Le quadrant qui compte est en bas à droite — "
    "performant tant que rien ne bouge. Une croix = politique infaisable sous au moins un "
    "forçage, donc sans rétention définie."
)

st.subheader("Tableau de robustesse")
table = prospective.robustness_frame(summaries)
st.dataframe(
    table.style.format({
        "Nominal": "{:,.1f}", "Pire cas": "{:,.1f}", "Médiane": "{:,.1f}",
        "Meilleur": "{:,.1f}", "Rétention": "{:.0%}", "Instabilité (CV)": "{:.1%}",
        "Regret max": "{:,.1f}", "Viabilité": "{:.0%}",
    }, na_rep="—"),
    width="stretch",
)
st.caption(
    "**Pire cas** et **Regret max** sont vides quand la politique est infaisable sous au "
    "moins un forçage : son pire cas n'est pas un nombre, c'est une absence de solution, et "
    "afficher le pire de ses survivants la ferait passer pour robuste. "
    "**Rétention** = pire cas / nominal. **Instabilité** = écart-type / moyenne sur les "
    "forçages. **Regret max** = plus grand écart au meilleur choix possible a posteriori."
)
st.info(
    "Ces mesures ne sont **pas** le bloc « exposition » d'un run. Celui-ci applique un choc "
    "de prix après le solve à une allocation figée (ce qu'on perd si personne ne réagit) ; "
    "ici le modèle **ré-optimise** sous chaque forçage, dans les limites que la politique lui "
    "laisse. C'est de la capacité d'adaptation sous contrainte politique. Ne pas additionner "
    "les deux dans un même score."
)

# ------------------------------------------------------------------ Tornado
st.header("Sensibilité d'une politique")
focus = st.selectbox("Politique", policies)
st.pyplot(prospective.build_tornado_figure(
    frame, focus, nominal, value_label=label, higher_is_better=higher_is_better
))
st.caption(
    "Écart de chaque forçage à la valeur non forcée de cette politique, trié par ampleur. "
    "Vert = le forçage lui profite, rouge = il lui nuit, dans le sens propre à l'indicateur."
)

with st.expander("Données brutes de la grille"):
    st.dataframe(frame.style.format("{:,.2f}", na_rep="infaisable"), width="stretch")
