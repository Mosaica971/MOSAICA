"""Landing page of the MOSAICA dashboard: one screen that answers "is this run readable,
and what does it say?".

The four other pages each answer a narrow question well and none of them answers that one.
A reader opening the dashboard on a fresh run should see, without clicking: whether the
solve converged, how far the allocation is from the observed 2017 land use, where the gap
sits, and which of this model's known reading traps apply to THIS run.

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

st.set_page_config(page_title="MOSAICA Guadeloupe — Synthèse", layout="wide")
st.title("MOSAICA Guadeloupe — Synthèse")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run trouvé dans `outputs/` — lancez `python main.py` d'abord.")
    st.stop()

recaps: dict[Path, dict] = {}
for run in runs:
    try:
        recaps[run] = loaders.load_recap(run)
    except (OSError, ValueError):
        recaps[run] = {}

# The retained reference is the sensible landing default: it is the run the project
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
    st.error(f"`{run_dir.name}` n'a pas de `recap.json` lisible.")
    st.stop()

role = next(
    (item.reference.label for item in resolved if item.run_dir == run_dir), None
)
if role:
    st.caption(f"Ce dossier est déclaré comme référence : **{role}**.")

# ------------------------------------------------------------------ Solve state
objective = recap.get("objective") or {}
head = st.columns(4)
head[0].metric("Objectif", f"{objective.get('value', float('nan')):,.0f} €")
head[1].metric("Fonction", objective.get("name", "—"))
head[2].metric("Durée", f"{recap.get('solve_duration_seconds', float('nan')):,.0f} s")
head[3].metric("Terminaison", recap.get("termination_condition", "—"))

# ------------------------------------------------------------------ Calibration
st.header("Écart à l'observé 2017")
verdicts = synthesis.calibration_verdicts(recap)
if not verdicts:
    st.warning(
        "Ce run n'a pas été scoré contre l'observé. Lancez :\n\n"
        f"```\npython scripts/evaluate_calibration.py {run_dir.as_posix()}\n```"
    )
else:
    cols = st.columns(len(verdicts))
    for col, verdict in zip(cols, verdicts):
        value = verdict["value"]
        threshold = verdict["threshold"]
        if threshold is None:
            note = "pas de seuil publié"
        else:
            direction = "≤" if verdict["better"] == "lower" else "≥"
            note = f"seuil {direction} {threshold:.0f} % — " + (
                "OK" if verdict["passed"] else "hors seuil"
            )
        col.metric(
            verdict["label"],
            "n/a" if value is None else f"{value:.1f} %",
            note,
            delta_color="off",
        )
    st.caption(
        "D'après Chopin et al. (2015) §2.6, au niveau des 12 groupes RPG observés — la "
        "résolution la plus fine dont l'observé 2017 dispose. Le PAD est le pourcentage "
        "d'écart absolu : 0 % = l'assolement simulé reproduit exactement l'observé."
    )

# ------------------------------------------------------------------ Where the gap is
pad_by_crop = loaders.load_calibration(run_dir, "pad_by_crop")
gaps = synthesis.headline_gaps(pad_by_crop)
if gaps is not None and not gaps.empty:
    st.subheader("Où se concentre l'écart")
    shown = gaps.copy()
    shown["Culture"] = [label_for(str(key)) for key in shown["crop"]]
    shown = shown.rename(
        columns={
            "observed_ha": "Observé (ha)",
            "simulated_ha": "Simulé (ha)",
            "abs_deviation_ha": "Écart (ha)",
            "pad_pct": "PAD (%)",
        }
    )
    st.dataframe(
        shown[["Culture", "Observé (ha)", "Simulé (ha)", "Écart (ha)", "PAD (%)"]]
        .style.format(precision=0, subset=["Observé (ha)", "Simulé (ha)", "Écart (ha)"])
        .format(precision=1, subset=["PAD (%)"]),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Classé par **hectares** d'écart, pas par PAD : un groupe de 4 ha à 100 % de PAD est "
        "arithmétiquement spectaculaire et agronomiquement sans portée, alors qu'un écart de "
        "3 000 ha sur la canne compte. Détail complet : page **Calibration**."
    )

# ------------------------------------------------------------------ What it produces
economics = recap.get("economics") or {}
if economics.get("output"):
    st.header("Ce que produit l'allocation")
    output, delta = economics["output"], economics.get("delta") or {}
    tiles = (
        ("total_production_tonnes", "Production", "{:,.0f} t"),
        ("total_gross_margin", "Marge brute", "{:,.0f} €"),
        ("total_subsidy", "Subvention", "{:,.0f} €"),
        ("total_etp", "Emploi", "{:,.0f} ETP"),
    )
    econ_cols = st.columns(len(tiles) + 1)
    surface = recap.get("output", {}).get("total_surface_ha")
    econ_cols[0].metric(
        "Surface cultivée",
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
        "Écart au côté **entrée** (baseline 2017). Celle-ci valorise chaque famille observée "
        "par une variante fine représentante (`baseline_representative_crops`), l'allocation "
        "fine de 2017 n'ayant jamais été observée : l'écart économique porte cette hypothèse, "
        "les surfaces non."
    )

# ------------------------------------------------------------------ Reading traps
st.header("À savoir avant de citer ces chiffres")
alerts = synthesis.run_alerts(recap)
if not alerts:
    st.success(
        "Aucun piège de lecture connu ne s'applique à ce run : solve prouvé optimal, aucun "
        "indicateur fixé par une contrainte, tous les blocs de reporting présents."
    )
for alert in alerts:
    render = {"error": st.error, "warning": st.warning, "info": st.info}[alert.severity]
    render(f"**{alert.title}** — {alert.body}")

st.divider()
st.caption(
    "Pages : **Détail du run** (tous les tableaux et graphiques d'un run) · "
    "**Comparaison** (plusieurs runs côte à côte, et le diff de leur configuration de "
    "départ) · **Calibration** (les quatre échelles de l'écart à l'observé) · "
    "**Prospective** (grille politique × forçage) · **Carte** (parcellaire observé, simulé, "
    "changements). Le fond méthodologique et les limites assumées sont dans `docs/04-vigilance.md`."
)
