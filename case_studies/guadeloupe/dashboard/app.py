"""Read-only Streamlit dashboard over outputs/output_N/ run folders (brique B).

Never triggers a solve or writes anything -- pure visualization over what
brique A's generate_report already persisted. Run with:
    streamlit run case_studies/guadeloupe/dashboard/app.py

See docs/superpowers/specs/2026-07-10-dashboard-design.md.
"""

from pathlib import Path

import streamlit as st

from case_studies.guadeloupe.dashboard import loaders

OUTPUTS_ROOT = Path(__file__).resolve().parents[3] / "outputs"

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

with st.expander("Contraintes activees"):
    for constraint in recap["constraints"]:
        st.write(f"- **{constraint['name']}** {constraint['args']}")

st.subheader("Entree vs sortie")
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
st.caption(
    "Comparaison limitee a la surface/nb de parcelles/nb d'exploitations : la "
    "baseline (entree) n'est connue qu'a la resolution des 12 groupes RPG, sans "
    "rendement/prix propres a cette resolution -- voir VIGILANCE.md."
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
        st.caption(
            "Carte des cultures par parcelle : non disponible (pas de donnees "
            "geographiques dans le repo) -- repartition ILE/REGION affichee a la "
            "place. Voir VIGILANCE.md."
        )

        shannon_region = loaders.load_csv(run_dir, f"shannon_diversity_by_region_{side}.csv")
        if shannon_region is not None:
            st.caption("Diversite de Shannon par region")
            st.bar_chart(shannon_region.set_index(shannon_region.columns[0]))

        if side == "output":
            production = loaders.load_csv(run_dir, "allocation_output.csv")
            for name, label, unit in (
                ("subsidy_per_tonne_by_crop.csv", "Subvention par tonne", "€/t"),
                ("subsidy_per_euro_sold_by_crop.csv", "Subvention par euro vendu", "€/€"),
            ):
                df = loaders.load_csv(run_dir, name)
                st.caption(f"{label} ({unit})")
                if df is not None:
                    st.bar_chart(df.set_index(df.columns[0]))
                else:
                    st.info("non disponible pour ce run")

            revenue_by_farm = loaders.load_csv(run_dir, "revenue_by_farm.csv")
            st.caption(
                f"Revenu par exploitation (Gini = {recap.get('gini_revenue_by_farm', float('nan')):.3f})"
            )
            if revenue_by_farm is not None:
                st.bar_chart(revenue_by_farm.set_index(revenue_by_farm.columns[0]))
        else:
            st.caption("Revenu/ETP de travail : non disponible (donnees de main "
                       "d'oeuvre non portees, voir VIGILANCE.md).")
            st.caption(
                "Production/subvention/revenu par culture : non disponible en "
                "entree (baseline connue a la resolution des 12 groupes RPG, sans "
                "rendement/prix a cette resolution, voir VIGILANCE.md)."
            )
