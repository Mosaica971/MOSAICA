"""Run detail page: every table and chart of one run folder.

Never triggers a solve or writes anything -- pure visualisation over what generate_report
already persisted. Run with:
    streamlit run apps/dashboard/app.py

See docs/superpowers/specs/2026-07-10-dashboard-design.md.
"""

import sys
from pathlib import Path

# `streamlit run app.py` executes this file as a top-level script, so the repo root is not
# on sys.path and `import case_studies...` fails. Put it there before any such import.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st

from apps.dashboard import loaders

OUTPUTS_ROOT = _REPO_ROOT / "outputs"

st.set_page_config(page_title="MOSAICA Guadeloupe -- Run detail", layout="wide")
st.title("MOSAICA Guadeloupe -- Run detail")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("No run found in `outputs/` -- run `python main.py` first.")
    st.stop()

# Preload recaps so the selectbox can label each run by its recap `run_name` (folder name
# as fallback). An unreadable recap degrades to {} -> folder-name fallback.
_recaps: dict[Path, dict] = {}
for _run in runs:
    try:
        _recaps[_run] = loaders.load_recap(_run)
    except (OSError, ValueError):
        _recaps[_run] = {}

run_dir = st.selectbox(
    "Run", runs, format_func=lambda path: loaders.run_display_name(path, _recaps[path])
)
recap = _recaps[run_dir]

st.header("Recap")
col1, col2, col3 = st.columns(3)
col1.metric("Objective", recap["objective"]["name"])
col1.metric("Value", f"{recap['objective']['value']:,.0f}")
col2.metric("Solve duration", f"{recap['solve_duration_seconds']:.2f}s")
col2.metric("Termination condition", recap["termination_condition"])
col3.metric("Plots (total)", recap["total_plots"])
col3.metric("Farms (total)", recap["total_farms"])
economics = recap.get("economics")
if economics:
    col1.metric("Estimated employment (FTE, output)", f"{economics['output']['total_fte']:,.1f}")
    output_econ = economics["output"]
    # total_net_revenue / total_labor_cost are absent from runs made before the labor-cost
    # feature; guard so the dashboard still opens on older output folders.
    if "total_net_revenue" in output_econ:
        col2.metric(
            "Net revenue (margin - labour cost, output)", f"{output_econ['total_net_revenue']:,.0f} €"
        )
        col3.metric("Labour cost (output)", f"{output_econ['total_labor_cost']:,.0f} €")

with st.expander("Enabled constraints"):
    for constraint in recap["constraints"]:
        st.write(f"- **{constraint['name']}** {constraint['args']}")

st.subheader("Input vs output (area)")
delta_cols = st.columns(3)
for col, key, label in zip(
    delta_cols,
    ("total_surface_ha", "active_plot_count", "farm_count"),
    ("Cultivated area (ha)", "Active plots", "Active farms"),
):
    col.metric(
        label,
        f"{recap['output'][key]:,.2f}" if isinstance(recap["output"][key], float) else recap["output"][key],
        delta=f"{recap['delta'][key]:+,.2f}" if isinstance(recap["delta"][key], float) else f"{recap['delta'][key]:+d}",
    )

if economics:
    st.subheader("Input vs output (economics)")
    econ_cols = st.columns(4)
    for col, key, label, fmt in zip(
        econ_cols,
        ("total_production_tonnes", "total_subsidy", "total_revenue", "total_fte"),
        ("Production (t)", "Subsidy (€)", "Revenue (€)", "Employment (FTE)"),
        ("{:,.0f}", "{:,.0f}", "{:,.0f}", "{:,.1f}"),
    ):
        col.metric(label, fmt.format(economics["output"][key]), delta=fmt.format(economics["delta"][key]))
    st.caption(
        "Input = 2017 baseline priced per family: each family (cane, banana...) is valued "
        "through a representative fine variant set in config `baseline_representative_crops` "
        "(an assumption -- see docs/04-vigilance.md). The fine 2017 allocation was never "
        "observed."
    )

input_tab, output_tab = st.tabs(["Input (2017 baseline)", "Output (optimised allocation)"])

for tab, side in ((input_tab, "input"), (output_tab, "output")):
    with tab:
        allocation = loaders.load_csv(run_dir, f"allocation_{side}.csv")
        if allocation is not None:
            st.write(f"{len(allocation)} plots allocated")
            st.dataframe(allocation, width="stretch")

        surface_region = loaders.load_csv(run_dir, f"surface_by_region_{side}.csv")
        surface_island = loaders.load_csv(run_dir, f"surface_by_island_{side}.csv")
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Area by region and crop (ha)")
            if surface_region is not None:
                st.bar_chart(surface_region.set_index(surface_region.columns[0]))
            else:
                st.info("not available for this run")
        with col_b:
            st.caption("Area by island and crop (ha)")
            if surface_island is not None:
                st.bar_chart(surface_island.set_index(surface_island.columns[0]))
            else:
                st.info("not available for this run")

        shannon_region = loaders.load_csv(run_dir, f"shannon_diversity_by_region_{side}.csv")
        if shannon_region is not None:
            st.caption("Shannon diversity by region")
            st.bar_chart(shannon_region.set_index(shannon_region.columns[0]))

        # Per-crop economics + employment, available on both sides (input uses the
        # representative baseline crops -- see the "economics" caption above).
        if side == "input":
            st.caption(
                "Input side: each family is valued through its representative fine variant "
                "(config `baseline_representative_crops`), the fine 2017 allocation never "
                "having been observed (docs/04-vigilance.md)."
            )
        for name, label in (
            (f"production_by_crop_{side}.csv", "Production by crop (t)"),
            (f"subsidy_by_crop_{side}.csv", "Subsidy by crop (€)"),
            (f"revenue_by_crop_{side}.csv", "Revenue by crop (€)"),
            (f"fte_by_region_{side}.csv", "Employment by region (FTE)"),
        ):
            df = loaders.load_csv(run_dir, name)
            if df is not None:
                st.caption(label)
                st.bar_chart(df.set_index(df.columns[0]))

        if side == "output":
            for name, label in (
                ("subsidy_per_tonne_by_crop.csv", "Subsidy per tonne (€/t)"),
                ("subsidy_per_euro_sold_by_crop.csv", "Subsidy per euro sold (€/€)"),
            ):
                df = loaders.load_csv(run_dir, name)
                if df is not None:
                    st.caption(label)
                    st.bar_chart(df.set_index(df.columns[0]))

            revenue_by_farm = loaders.load_csv(run_dir, "revenue_by_farm.csv")
            st.caption(
                f"Revenue by farm (Gini = {recap.get('gini_revenue_by_farm', float('nan')):.3f})"
            )
            if revenue_by_farm is not None:
                st.bar_chart(revenue_by_farm.set_index(revenue_by_farm.columns[0]))

        st.caption(
            "Crops by plot on a map: see the **Map** page (RPG 2017 geometry from data/gis/)."
        )
