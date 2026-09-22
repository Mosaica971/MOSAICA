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
st.title("Pareto front: what the next step costs")

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
        "No sweep found. This page reads the runs of an ε-constraint sweep, traced either "
        "against the reference config or under a policy declared in `plan.yaml`:\n\n"
        "```\npython scripts/run_scenarios.py --scenarios "
        "case_studies/guadeloupe/scenarios_pareto.yaml\n```\n\n"
        "Each point is a real MILP solve, and the nitrogen sweep shipped has seven — do not "
        "launch it without meaning to. A run joins a sweep through its recap's `run_sweep` "
        "(failing that, through the prefix of its `run_name` before `__`)."
    )
    st.stop()

controls = st.columns(4)
sweep = controls[0].selectbox("Sweep", sweeps)
x_indicator = controls[1].selectbox(
    "Constrained axis (x)", list(comparison.INDICATOR_LABELS),
    index=list(comparison.INDICATOR_LABELS).index("total_nitrogen"),
    format_func=lambda i: comparison.INDICATOR_LABELS[i],
)
y_indicator = controls[2].selectbox(
    "Objective (y)", list(comparison.INDICATOR_LABELS),
    index=list(comparison.INDICATOR_LABELS).index("total_gross_margin"),
    format_func=lambda i: comparison.INDICATOR_LABELS[i],
)
side = controls[3].radio("Side", ("output", "input"), horizontal=True,
                         format_func=lambda s: comparison.SIDE_LABELS[s])

points = pareto.collect_points(recaps, sweep, x_indicator, y_indicator, side)
if len(points) < 2:
    st.warning(
        f"\"{sweep}\" has only {len(points)} point(s) carrying both indicators. A front needs "
        "at least two solves; check that every run of the sweep is present and carries the "
        "relevant recap block."
    )
    st.stop()

points = pareto.mark_dominated(points, x_indicator, y_indicator)
st.pyplot(pareto.build_front_figure(points, x_indicator, y_indicator))
st.caption(
    "Each point is a solve under a different ceiling. The first point of the sweep has its "
    "ceiling set at the achieved total, so the constraint is **inactive** there: its value "
    "must equal that of the selected calibration. If it differs, the front is not wrong — "
    "that solve did not converge to the same place."
)

dominated = [p for p in points if p.dominated]
if dominated:
    st.warning(
        "**Dominated points** (grey crosses): "
        + ", ".join(p.label.rsplit(pareto.SWEEP_SEPARATOR, 1)[-1] for p in dominated)
        + ". A trade-off does not double back — tightening a constraint cannot improve the "
        "objective. A dominated point therefore almost always signals a solve that did not "
        "converge (time limit, sub-optimal incumbent), not a discovery. Check its termination "
        "before drawing anything from it."
    )

st.header("Marginal cost")
rates = pareto.marginal_rates(points)
if not rates:
    st.info("Not enough non-dominated points to compute a slope.")
else:
    table = pd.DataFrame([
        {
            "From": r["from"].rsplit(pareto.SWEEP_SEPARATOR, 1)[-1],
            "To": r["to"].rsplit(pareto.SWEEP_SEPARATOR, 1)[-1],
            f"Δ {comparison.INDICATOR_LABELS[x_indicator]}": r["delta_x"],
            f"Δ {comparison.INDICATOR_LABELS[y_indicator]}": r["delta_y"],
            "Marginal cost (Δy/Δx)": r["rate"],
        }
        for r in rates
    ])
    st.dataframe(table.style.format(precision=2), width="stretch", hide_index=True)
    st.caption(
        "This is the figure the front exists to produce: \"the last hundred thousand kg of "
        "nitrogen cost X € of margin\". Compare it with the **dual price** of the same "
        "constraint (`core/solve/shadow_prices.py`), its local version: a large gap between "
        "the two means the dual is read outside its neighbourhood of validity — it prices an "
        "infinitesimal relaxation, not the whole step."
    )

st.info(
    "**A ceiling can also be met by farming less.** A policy that allocates fewer hectares "
    "shows less total nitrogen without producing more cleanly. To tell the two apart, redraw "
    "the front with \"Nitrogen / tonne produced\" on the x axis: that is the intensity, and it "
    "is what describes a practice."
)
