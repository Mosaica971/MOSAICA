"""Read-only Streamlit dashboard over outputs/output_N/ run folders (brique B).

Never triggers a solve or writes anything -- pure visualization over what
brique A's generate_report already persisted. Run with:
    streamlit run case_studies/guadeloupe/dashboard/app.py

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

from case_studies.guadeloupe.dashboard import loaders

OUTPUTS_ROOT = _REPO_ROOT / "outputs"

st.set_page_config(page_title="MOSAICA Guadeloupe -- Dashboard", layout="wide")
st.title("MOSAICA Guadeloupe -- Dashboard")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run trouve dans `outputs/` -- lancez `python main.py` d'abord.")
    st.stop()

run_dir = st.selectbox("Run", runs, format_func=lambda path: path.name)
recap = loaders.load_recap(run_dir)

st.header("Recap")
col1, col2, col3 = st.columns(3)
col1.metric("Objectif", recap["objective"]["name"])
col1.metric("Valeur", f"{recap['objective']['value']:,.0f}")
col2.metric("Duree de resolution", f"{recap['solve_duration_seconds']:.2f}s")
col2.metric("Condition de terminaison", recap["termination_condition"])
col3.metric("Parcelles (total)", recap["total_plots"])
col3.metric("Exploitations (total)", recap["total_farms"])
economics = recap.get("economics")
if economics:
    col1.metric("Emploi estimé (ETP, sortie)", f"{economics['output']['total_etp']:,.1f}")
    output_econ = economics["output"]
    # total_net_revenue / total_labor_cost are absent from runs made before the labor-cost
    # feature; guard so the dashboard still opens on older output folders.
    if "total_net_revenue" in output_econ:
        col2.metric(
            "Revenu net (marge - coût MO, sortie)", f"{output_econ['total_net_revenue']:,.0f} €"
        )
        col3.metric("Coût main d'œuvre (sortie)", f"{output_econ['total_labor_cost']:,.0f} €")

with st.expander("Contraintes activees"):
    for constraint in recap["constraints"]:
        st.write(f"- **{constraint['name']}** {constraint['args']}")

st.subheader("Entree vs sortie (surface)")
delta_cols = st.columns(3)
for col, key, label in zip(
    delta_cols,
    ("total_surface_ha", "active_plot_count", "farm_count"),
    ("Surface cultivee (ha)", "Parcelles actives", "Exploitations actives"),
):
    col.metric(
        label,
        f"{recap['output'][key]:,.2f}" if isinstance(recap["output"][key], float) else recap["output"][key],
        delta=f"{recap['delta'][key]:+,.2f}" if isinstance(recap["delta"][key], float) else f"{recap['delta'][key]:+d}",
    )

if economics:
    st.subheader("Entree vs sortie (economie)")
    econ_cols = st.columns(4)
    for col, key, label, fmt in zip(
        econ_cols,
        ("total_production_tonnes", "total_subsidy", "total_revenue", "total_etp"),
        ("Production (t)", "Subvention (€)", "Revenu (€)", "Emploi (ETP)"),
        ("{:,.0f}", "{:,.0f}", "{:,.0f}", "{:,.1f}"),
    ):
        col.metric(label, fmt.format(economics["output"][key]), delta=fmt.format(economics["delta"][key]))
    st.caption(
        "Entree = baseline 2017 a economie representative par famille : chaque famille "
        "(canne, banane...) est evaluee via une variante fine representante assignee dans "
        "config `baseline_representative_crops` (hypothese -- voir VIGILANCE.md point 4). "
        "L'allocation fine de 2017 n'a jamais ete observee."
    )

input_tab, output_tab = st.tabs(["Entree (baseline 2017)", "Sortie (allocation optimisee)"])

for tab, side in ((input_tab, "input"), (output_tab, "output")):
    with tab:
        allocation = loaders.load_csv(run_dir, f"allocation_{side}.csv")
        if allocation is not None:
            st.write(f"{len(allocation)} parcelles allouees")
            st.dataframe(allocation, width="stretch")

        surface_region = loaders.load_csv(run_dir, f"surface_by_region_{side}.csv")
        surface_island = loaders.load_csv(run_dir, f"surface_by_island_{side}.csv")
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Surface par region et par culture (ha)")
            if surface_region is not None:
                st.bar_chart(surface_region.set_index(surface_region.columns[0]))
            else:
                st.info("non disponible pour ce run")
        with col_b:
            st.caption("Surface par ile et par culture (ha)")
            if surface_island is not None:
                st.bar_chart(surface_island.set_index(surface_island.columns[0]))
            else:
                st.info("non disponible pour ce run")

        shannon_region = loaders.load_csv(run_dir, f"shannon_diversity_by_region_{side}.csv")
        if shannon_region is not None:
            st.caption("Diversite de Shannon par region")
            st.bar_chart(shannon_region.set_index(shannon_region.columns[0]))

        # Per-crop economics + employment, now available on both sides (input uses the
        # representative baseline crops -- see the "economie" caption above).
        if side == "input":
            st.caption(
                "Cote entree : chaque famille est evaluee via sa variante fine representante "
                "(config `baseline_representative_crops`), l'allocation fine 2017 n'ayant "
                "jamais ete observee (VIGILANCE.md point 4)."
            )
        for name, label in (
            (f"production_by_crop_{side}.csv", "Production par culture (t)"),
            (f"subsidy_by_crop_{side}.csv", "Subvention par culture (€)"),
            (f"revenue_by_crop_{side}.csv", "Revenu par culture (€)"),
            (f"etp_by_region_{side}.csv", "Emploi par region (ETP)"),
        ):
            df = loaders.load_csv(run_dir, name)
            if df is not None:
                st.caption(label)
                st.bar_chart(df.set_index(df.columns[0]))

        if side == "output":
            for name, label in (
                ("subsidy_per_tonne_by_crop.csv", "Subvention par tonne (€/t)"),
                ("subsidy_per_euro_sold_by_crop.csv", "Subvention par euro vendu (€/€)"),
            ):
                df = loaders.load_csv(run_dir, name)
                if df is not None:
                    st.caption(label)
                    st.bar_chart(df.set_index(df.columns[0]))

            revenue_by_farm = loaders.load_csv(run_dir, "revenue_by_farm.csv")
            st.caption(
                f"Revenu par exploitation (Gini = {recap.get('gini_revenue_by_farm', float('nan')):.3f})"
            )
            if revenue_by_farm is not None:
                st.bar_chart(revenue_by_farm.set_index(revenue_by_farm.columns[0]))

        st.caption(
            "Carte des cultures par parcelle : non disponible (pas de donnees "
            "geographiques dans le repo) -- repartition ILE/REGION affichee plus haut. "
            "Voir VIGILANCE.md."
        )
