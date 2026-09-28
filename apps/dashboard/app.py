"""Landing page of the MOSAICA dashboard: one screen that answers "is this run readable,
and what does it say?".

The other pages each answer a narrow question well and none of them answers that one. A
reader opening the dashboard on a fresh run should see, without clicking: whether the solve
converged, how far the allocation is from the observed 2017 land use, where the gap sits, and
which of this model's known reading traps apply to THIS run.

Read-only, like every page here: it displays what generate_report already persisted and
computes nothing. Run from the repo root:
    streamlit run apps/dashboard/app.py
"""

import sys
from pathlib import Path

# `streamlit run app.py` executes this file as a top-level script, so the repo root is not
# on sys.path and `import apps...` fails. Put it there before any such import.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from apps.dashboard import loaders, references, synthesis
from case_studies.guadeloupe.domain.crop_labels import label_for

OUTPUTS_ROOT = _REPO_ROOT / "outputs"
MANIFEST = _REPO_ROOT / references.DEFAULT_MANIFEST

st.set_page_config(page_title="MOSAICA Guadeloupe — Summary", layout="wide")
st.title("MOSAICA Guadeloupe — Summary")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("No run found in `outputs/` — run `python main.py` first.")
    st.stop()

recaps: dict[Path, dict] = {}
for run in runs:
    try:
        recaps[run] = loaders.load_recap(run)
    except (OSError, ValueError):
        recaps[run] = {}

# The selected reference is the sensible landing default: it is the run the project
# considers current. Falls back to the most recent folder when no manifest declares one.
resolved = references.resolve(references.load_references(MANIFEST), OUTPUTS_ROOT)
default_run = next(
    (item.run_dir for item in resolved
     if item.reference.id == "retained" and item.run_dir in recaps),
    runs[0],
)

run_dir = st.selectbox(
    "Run",
    runs,
    index=runs.index(default_run),
    format_func=lambda path: loaders.run_display_name(path, recaps[path]),
)
recap = recaps[run_dir]
if not recap:
    st.error(f"`{run_dir.name}` has no readable `recap.json`.")
    st.stop()

role = next(
    (item.reference.label for item in resolved if item.run_dir == run_dir), None
)
if role:
    st.caption(f"This folder is declared as a reference: **{role}**.")

# ------------------------------------------------------------------ Solve state
objective = recap.get("objective") or {}
head = st.columns(4)
head[0].metric("Objective", f"{objective.get('value', float('nan')):,.0f} €")
head[1].metric("Function", objective.get("name", "—"))
head[2].metric("Duration", f"{recap.get('solve_duration_seconds', float('nan')):,.0f} s")
head[3].metric("Termination", recap.get("termination_condition", "—"))

# ------------------------------------------------------------------ Calibration
st.header("Gap to the 2017 observation")
verdicts = synthesis.calibration_verdicts(recap)
if not verdicts:
    st.warning(
        "This run was not scored against the observation. Run:\n\n"
        f"```\npython scripts/evaluate_calibration.py {run_dir.as_posix()}\n```"
    )
else:
    cols = st.columns(len(verdicts))
    for col, verdict in zip(cols, verdicts):
        value = verdict["value"]
        threshold = verdict["threshold"]
        if threshold is None:
            note = "no published threshold"
        else:
            direction = "≤" if verdict["better"] == "lower" else "≥"
            note = f"threshold {direction} {threshold:.0f} % — " + (
                "OK" if verdict["passed"] else "outside threshold"
            )
        col.metric(
            verdict["label"],
            "n/a" if value is None else f"{value:.1f} %",
            note,
            delta_color="off",
        )
    st.caption(
        "After Chopin et al. (2015) §2.6, at the level of the 12 observed RPG groups — the "
        "finest resolution the 2017 observation has. The PAD is the percentage absolute "
        "deviation: 0 % = the simulated cropping plan reproduces the observation exactly."
    )

# ------------------------------------------------------------------ Where the gap is
pad_by_crop = loaders.load_calibration(run_dir, "pad_by_crop")
gaps = synthesis.headline_gaps(pad_by_crop)
if gaps is not None and not gaps.empty:
    st.subheader("Where the gap concentrates")
    shown = gaps.copy()
    shown["Crop"] = [label_for(str(key)) for key in shown["crop"]]
    shown = shown.rename(
        columns={
            "observed_ha": "Observed (ha)",
            "simulated_ha": "Simulated (ha)",
            "abs_deviation_ha": "Gap (ha)",
            "pad_pct": "PAD (%)",
        }
    )
    st.dataframe(
        shown[["Crop", "Observed (ha)", "Simulated (ha)", "Gap (ha)", "PAD (%)"]]
        .style.format(precision=0, subset=["Observed (ha)", "Simulated (ha)", "Gap (ha)"])
        .format(precision=1, subset=["PAD (%)"]),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Ranked by **hectares** of gap, not by PAD: a 4 ha group at 100 % PAD is "
        "arithmetically dramatic and agronomically irrelevant, whereas a 3 000 ha gap on cane "
        "matters. Full detail: **Calibration** page."
    )

# ------------------------------------------------------------------ What it produces
economics = recap.get("economics") or {}
if economics.get("output"):
    st.header("What the allocation produces")
    output, delta = economics["output"], economics.get("delta") or {}
    tiles = (
        ("total_production_tonnes", "Production", "{:,.0f} t"),
        ("total_gross_margin", "Gross margin", "{:,.0f} €"),
        ("total_subsidy", "Subsidy", "{:,.0f} €"),
        ("total_fte", "Employment", "{:,.0f} FTE"),
    )
    econ_cols = st.columns(len(tiles) + 1)
    surface = recap.get("output", {}).get("total_surface_ha")
    econ_cols[0].metric(
        "Cultivated area",
        "—" if surface is None else f"{surface:,.0f} ha",
        None if recap.get("delta", {}).get("total_surface_ha") is None
        else f"{recap['delta']['total_surface_ha']:+,.0f} ha",
    )
    for col, (key, label, fmt) in zip(econ_cols[1:], tiles):
        if key not in output:
            continue
        col.metric(
            label,
            fmt.format(output[key]),
            fmt.format(delta[key]) if key in delta else None,
        )
    st.caption(
        "Gap to the **input** side (2017 baseline). The baseline prices each observed family "
        "through a representative fine variant (`baseline_representative_crops`), since the "
        "fine 2017 allocation was never observed: the economic gap carries that assumption, "
        "the areas do not."
    )

# ------------------------------------------------------------------ Reading traps
st.header("Know this before quoting these figures")
alerts = synthesis.run_alerts(recap)
if not alerts:
    st.success(
        "No known reading trap applies to this run: solve proven optimal, no indicator fixed "
        "by a constraint, every reporting block present."
    )
for alert in alerts:
    render = {"error": st.error, "warning": st.warning, "info": st.info}[alert.severity]
    render(f"**{alert.title}** — {alert.body}")

st.divider()
st.caption(
    "Pages: **Run detail** (every table and chart of one run) · **Comparison** (several runs "
    "side by side, and the diff of their starting configuration) · **Calibration** (the four "
    "scales of the gap to the observation) · **Prospective** (policy × forcing grid) · "
    "**Map** (observed and simulated plots, changes) · **Pareto** (epsilon-constraint "
    "fronts) · **Status** (what is implemented, what is not). The methodological background "
    "and the accepted limitations are in `docs/04-vigilance.md`."
)
