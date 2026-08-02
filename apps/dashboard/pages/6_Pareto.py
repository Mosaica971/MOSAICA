"""Pareto page: the trade-off curve between the objective and a bounded indicator.

Reads the runs of an epsilon-constraint sweep (case_studies/guadeloupe/scenarios_pareto.yaml)
and draws the front. This answers a question no single scenario can: not "what is the margin
under this ceiling" but "what does the next kilogram cost", across the whole range.

Read-only. Run from the repo root:  streamlit run apps/dashboard/app.py
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import streamlit as st

from apps.dashboard import comparison, loaders, pareto

OUTPUTS_ROOT = _REPO_ROOT / "outputs"

st.set_page_config(page_title="MOSAICA — Pareto", layout="wide")
st.title("Front de Pareto : ce que coûte le cran suivant")

recaps: dict[str, dict] = {}
for run_dir in loaders.list_output_runs(OUTPUTS_ROOT):
    try:
        recaps[run_dir.name] = loaders.load_recap(run_dir)
    except (OSError, ValueError):
        continue

# A sweep identifier is `<sweep>` on its own, or `<policy>[__<forcing>]__<sweep>` for a front
# traced under a policy -- hence the test on the LAST segment, not on the prefix.
sweeps = [
    s for s in pareto.sweeps_in(recaps)
    if s.rsplit(pareto.SWEEP_SEPARATOR, 1)[-1].startswith("pareto")
]
if not sweeps:
    st.info(
        "Aucun balayage trouvé. Cette page lit les runs d'un balayage par ε-contrainte, "
        "tracé soit contre la config de référence, soit sous une politique déclarée dans "
        "`plan.yaml` :\n\n"
        "```\npython scripts/run_scenarios.py --scenarios "
        "case_studies/guadeloupe/scenarios_pareto.yaml\n```\n\n"
        "Chaque point est un vrai solve MILP (~3 min), et le balayage azote livré en compte "
        "sept — à ne pas lancer sans intention. Un run rejoint un balayage par le `run_sweep` "
        "de son recap (à défaut, par le préfixe de son `run_name` avant `__`)."
    )
    st.stop()

controls = st.columns(4)
sweep = controls[0].selectbox("Balayage", sweeps)
x_indicator = controls[1].selectbox(
    "Axe contraint (x)", list(comparison.INDICATOR_LABELS),
    index=list(comparison.INDICATOR_LABELS).index("total_azote"),
    format_func=lambda i: comparison.INDICATOR_LABELS[i],
)
y_indicator = controls[2].selectbox(
    "Objectif (y)", list(comparison.INDICATOR_LABELS),
    index=list(comparison.INDICATOR_LABELS).index("total_gross_margin"),
    format_func=lambda i: comparison.INDICATOR_LABELS[i],
)
side = controls[3].radio("Côté", ("output", "input"), horizontal=True,
                         format_func=lambda s: {"output": "sortie", "input": "entrée"}[s])

points = pareto.collect_points(recaps, sweep, x_indicator, y_indicator, side)
if len(points) < 2:
    st.warning(
        f"« {sweep} » n'a que {len(points)} point(s) portant ces deux indicateurs. Un front "
        "demande au moins deux solves ; vérifiez que les runs du balayage sont bien tous "
        "présents et qu'ils portent le bloc de recap concerné."
    )
    st.stop()

points = pareto.mark_dominated(points, x_indicator, y_indicator)
st.pyplot(pareto.build_front_figure(points, x_indicator, y_indicator))
st.caption(
    "Chaque point est un solve sous un plafond différent. Le premier point du balayage a "
    "son plafond calé sur le total réalisé, donc la contrainte y est **inactive** : sa "
    "valeur doit égaler celle de la calibration retenue. Si elle en diffère, ce n'est pas le "
    "front qui est faux — c'est que ce solve n'a pas convergé au même endroit."
)

dominated = [p for p in points if p.dominated]
if dominated:
    st.warning(
        "**Points dominés** (croix grises) : "
        + ", ".join(p.label.rsplit(pareto.SWEEP_SEPARATOR, 1)[-1] for p in dominated)
        + ". Un arbitrage ne revient pas en arrière — serrer une contrainte ne peut pas "
        "améliorer l'objectif. Un point dominé signale donc presque toujours un solve qui "
        "n'a pas convergé (limite de temps, incumbent sous-optimal), pas une découverte. "
        "Vérifier sa terminaison avant d'en tirer quoi que ce soit."
    )

st.header("Coût marginal")
rates = pareto.marginal_rates(points)
if not rates:
    st.info("Pas assez de points non dominés pour calculer une pente.")
else:
    table = pd.DataFrame([
        {
            "De": r["from"].rsplit(pareto.SWEEP_SEPARATOR, 1)[-1],
            "Vers": r["to"].rsplit(pareto.SWEEP_SEPARATOR, 1)[-1],
            f"Δ {comparison.INDICATOR_LABELS[x_indicator]}": r["delta_x"],
            f"Δ {comparison.INDICATOR_LABELS[y_indicator]}": r["delta_y"],
            "Coût marginal (Δy/Δx)": r["rate"],
        }
        for r in rates
    ])
    st.dataframe(table.style.format(precision=2), width="stretch", hide_index=True)
    st.caption(
        "C'est le chiffre que le front existe pour produire : « les cent derniers milliers "
        "de kg d'azote coûtent X € de marge ». À comparer au **prix dual** de la même "
        "contrainte (`core/solve/shadow_prices.py`), qui en est la version locale : un écart "
        "important entre les deux signifie que le dual est lu hors de son voisinage de "
        "validité — il price une relaxation infinitésimale, pas le cran entier."
    )

st.info(
    "**Un plafond se satisfait aussi en cultivant moins.** Une politique qui alloue moins "
    "d'hectares affiche moins d'azote total sans produire plus proprement. Pour distinguer "
    "les deux, refaire le front avec « Azote / tonne produite » en abscisse : c'est "
    "l'intensité, et c'est elle qui décrit une pratique."
)
