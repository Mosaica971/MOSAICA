"""Prospective page: read a policy x forcing grid rather than a flat list of runs.

A crossed batch produces up to 110 runs, which the Comparison page cannot show -- it asks
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
st.title("Prospective: policies × forcings")


@st.cache_data(show_spinner="Reading runs…")
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
        "No grid run found in `outputs/`. This page reads the runs produced by a policy × "
        "forcing plan:\n\n"
        "```\npython scripts/run_scenarios.py --scenarios "
        "case_studies/guadeloupe/plan.yaml\n```\n\n"
        "A run is recognised if its recap carries `run_policy` / `run_forcing`, or if its "
        "name follows the `Policy__Forcing` convention."
    )
    st.stop()

all_policies = sorted({e["policy"] for e in entries})
all_forcings = sorted({e["forcing"] for e in entries})

# ------------------------------------------------------------------ Controls
with st.sidebar:
    st.header("Grid")
    policies = st.multiselect("Policies", all_policies, default=all_policies)
    forcings = st.multiselect("Forcings", all_forcings, default=all_forcings)
    side = st.radio("Side", ("output", "input"), horizontal=True,
                    format_func=lambda s: comparison.SIDE_LABELS[s])
    indicator = st.selectbox(
        "Indicator", list(comparison.INDICATOR_LABELS),
        index=list(comparison.INDICATOR_LABELS).index("total_gross_margin"),
        format_func=lambda i: comparison.INDICATOR_LABELS[i],
    )
    nominal = st.selectbox(
        "Reference forcing", forcings or all_forcings,
        index=(forcings or all_forcings).index("F0_nominal")
        if "F0_nominal" in (forcings or all_forcings) else 0,
        help="The neutral forcing, denominator of the retention and origin of the tornado.",
    )

if not policies or not forcings:
    st.warning("Select at least one policy and one forcing.")
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
        f"\"{label}\" is available in no run of the grid — the runs probably predate the "
        "recap block that carries it. Rerun the batch."
    )
    st.stop()

st.caption(
    f"**{len(kept)} runs** · indicator: {label} · direction: "
    + ("higher = better" if higher_is_better else "lower = better")
    + f" · reference: {nominal}"
)

# A cell that a constraint pins is the scenario's hypothesis, not its result.
_pinned = {
    e["policy"] for e in kept if indicator in comparison.bound_indicators(e["recap"])
}
if _pinned:
    st.warning(
        f"\"{label}\" is **fixed by a constraint** in: {', '.join(sorted(_pinned))}. For those "
        "policies the value is an imposed hypothesis, not a result — their robustness on this "
        "indicator says nothing about their robustness overall."
    )

# ------------------------------------------------------------------ Heatmap
st.header("Policy × forcing grid")
mode_label = st.radio(
    "Reading",
    ("Raw value", "% of the policy's nominal", "Regret (% of the forcing's best)"),
    horizontal=True,
)
mode = {
    "Raw value": "absolute",
    "% of the policy's nominal": "vs_nominal",
    "Regret (% of the forcing's best)": "regret",
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
        "Values as they are. Columns are not comparable with one another if the forcings "
        "change the indicator's scale — to compare policies *with each other* under one "
        "forcing, prefer the regret."
    )
else:
    st.pyplot(prospective.build_heatmap_figure(
        display_frame * 100, title=label, colorbar_label="%",
        higher_is_better=True, centre=100.0, value_format="{:,.0f}",
    ))
    st.caption(
        "Share kept of **each policy's** unforced value: 100 % = the forcing costs nothing, "
        "60 % = the policy loses 40 % of its own promise. Says nothing about the level — a "
        "mediocre, stable policy sits at 100 % here."
        if mode == "vs_nominal" else
        "Gap to the **best result obtained by any policy under that same forcing** (Savage "
        "criterion): 100 % = it was the right choice for that forcing, 70 % = 30 % is left "
        "on the table. Every column holds at least one 100 %."
    )
st.caption("Hatched \"n/a\" cell = no solution (infeasible), not missing data.")

# ------------------------------------------------------------------ Robustness
st.header("Performance and robustness")
threshold_help = (
    "Viability threshold, in the indicator's unit. The \"Viability\" column counts the share "
    "of forcings under which the policy holds it; an infeasible forcing counts as a failure."
)
default_threshold = float(pd.Series(frame.to_numpy().ravel()).dropna().median())
viability_threshold = st.number_input(
    "Viability threshold", value=default_threshold, help=threshold_help
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
    "X axis: the value under the reference forcing. Y axis: the share of that value still "
    "obtained under the worst forcing. The quadrant that matters is bottom right — "
    "performant as long as nothing moves. A cross = a policy infeasible under at least one "
    "forcing, hence with no defined retention."
)

st.subheader("Robustness table")
table = prospective.robustness_frame(summaries)
st.dataframe(
    table.style.format({
        "Nominal": "{:,.1f}", "Worst case": "{:,.1f}", "Median": "{:,.1f}",
        "Best": "{:,.1f}", "Retention": "{:.0%}", "Instability (CV)": "{:.1%}",
        "Max regret": "{:,.1f}", "Viability": "{:.0%}",
    }, na_rep="—"),
    width="stretch",
)
st.caption(
    "**Worst case** and **Max regret** are empty when the policy is infeasible under at "
    "least one forcing: its worst case is not a number, it is an absence of solution, and "
    "showing the worst of its survivors would make it look robust. "
    "**Retention** = worst case / nominal. **Instability** = standard deviation / mean over "
    "the forcings. **Max regret** = the largest gap to the best choice possible in hindsight."
)
st.info(
    "These measures are **not** a run's \"exposure\" block. That one applies a price shock "
    "after the solve to a frozen allocation (what is lost if nobody reacts); here the model "
    "**re-optimises** under each forcing, within the limits the policy leaves it. This is "
    "adaptive capacity under policy constraint. Do not add the two into one score."
)

# ------------------------------------------------------------------ Tornado
st.header("Sensitivity of one policy")
focus = st.selectbox("Policy", policies)
st.pyplot(prospective.build_tornado_figure(
    frame, focus, nominal, value_label=label, higher_is_better=higher_is_better
))
st.caption(
    "Gap of each forcing to this policy's unforced value, sorted by size. Green = the "
    "forcing benefits it, red = it hurts it, in the indicator's own direction."
)

with st.expander("Raw grid data"):
    st.dataframe(frame.style.format("{:,.2f}", na_rep="infeasible"), width="stretch")
