"""Comparison page: put several runs (and their input/output sides) side by side.

Read-only, like the single-run home page. Every data operation goes through the tested pure
helpers in dashboard/comparison.py; this file only wires them to Streamlit widgets. Run the
dashboard from the repo root with:  streamlit run apps/dashboard/app.py
(the pages/ folder is discovered automatically).
"""

import sys
from functools import partial
from pathlib import Path

# Streamlit runs each page as its own top-level script, so (like app.py) the repo root must
# be on sys.path before importing `case_studies...`.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from case_studies.guadeloupe.domain.crop_labels import CROP_LABELS
from apps.dashboard import allocation_diff, comparison, config_diff, loaders, references

OUTPUTS_ROOT = _REPO_ROOT / "outputs"
SIDES = ("output", "input")
MANIFEST = _REPO_ROOT / references.DEFAULT_MANIFEST

# Session-state key of the series multiselect. Held explicitly so the "load the references"
# button can rewrite the selection before the widget is instantiated.
_SELECTION_KEY = "comparison_series"

# The scalar-indicator catalogue lives in dashboard/comparison.py: two pages need it
# (this one and Prospective), and a Streamlit page must never be imported by another.
# Aliased here under the names the rest of this page already uses.
_ECON_INDICATORS = comparison.ECON_INDICATORS
_ENV_INDICATORS = comparison.ENV_INDICATORS
_INTENSITY_INDICATORS = comparison.INTENSITY_INDICATORS
_AUTONOMY_INDICATORS = comparison.AUTONOMY_INDICATORS
_RESILIENCE_INDICATORS = comparison.RESILIENCE_INDICATORS
_GINI_KEY = comparison.GINI_KEY
_INDICATOR_LABELS = comparison.INDICATOR_LABELS
_indicator_value = comparison.indicator_value


st.set_page_config(page_title="MOSAICA -- Comparison", layout="wide")
st.title("Scenario comparison")

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("No run found in `outputs/` -- run `python main.py` first.")
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

# The rendering body is guarded by the presence of data. With no run (an empty outputs/
# folder -- it is gitignored -- or the page imported outside the Streamlit runtime by the
# tests) the data-dependent part is skipped: st.stop() does not halt on a bare import.
if series_catalog:
    # ------------------------------------------------------------ Reference runs
    # Three series are not scenarios among others: the observed 2017 land use, the strict
    # GAMS-parity calibration, and the selected one. They are declared in a versioned
    # manifest (case_studies/guadeloupe/references.yaml) with the reason for each choice.
    resolved_references = references.resolve(
        references.load_references(MANIFEST), OUTPUTS_ROOT
    )
    reference_labels = references.series_labels_for(resolved_references, series_catalog)

    if resolved_references:
        with st.container(border=True):
            st.subheader("References")
            head, action = st.columns([4, 1])
            head.caption(
                "The three fixed points everything else is read against, declared in "
                "`case_studies/guadeloupe/references.yaml`. The button replaces the series "
                "selection below with these references, in this order."
            )
            ordered = [
                reference_labels[item.reference.id]
                for item in resolved_references
                if item.reference.id in reference_labels
            ]
            if action.button(
                "Load the references",
                disabled=not ordered,
                width="stretch",
            ):
                st.session_state[_SELECTION_KEY] = ordered
                st.rerun()

            for item in resolved_references:
                reference = item.reference
                folder = item.run_dir.name if item.run_dir else reference.run
                if item.missing:
                    st.error(
                        f"**{reference.label}** — folder `{reference.run}` missing from "
                        "`outputs/`. Rerun it, or fix the manifest."
                    )
                elif reference.id not in reference_labels:
                    st.warning(
                        f"**{reference.label}** — `{folder}` exists but has no "
                        f"`facts_{reference.side}.csv` table: the run predates the facts "
                        "table and cannot be compared here."
                    )
                else:
                    with st.expander(f"{reference.label} — `{folder}`"):
                        st.write(reference.note or "_(no justification declared)_")

    # The declared references make the best default: they are what this page exists to
    # compare. Falls back to every "output" series when no manifest matches.
    default = (
        [reference_labels[item.reference.id]
         for item in resolved_references
         if item.reference.id in reference_labels]
        or [lbl for lbl in series_catalog if comparison.SIDE_LABELS["output"] in lbl]
        or list(series_catalog)
    )
    # `default` AND `key`, on purpose: session state carries the reference button's rewrite
    # between reruns, and `default` is what the widget falls back on when there is no session
    # state at all -- which is the case on the first render, and when this module is imported
    # bare by the tests (session state is inert outside `streamlit run`).
    if _SELECTION_KEY in st.session_state:
        # A run folder removed between two visits would leave a stale label the widget
        # cannot render.
        st.session_state[_SELECTION_KEY] = [
            lbl for lbl in st.session_state[_SELECTION_KEY] if lbl in series_catalog
        ]

    selected = st.multiselect(
        "Series to compare (run × side)",
        list(series_catalog),
        default=default,
        key=_SELECTION_KEY,
    )
    if not selected:
        st.info("Select at least one series.")
        st.stop()

    # ------------------------------------------------- Starting-configuration diff
    # What separates two runs at their hypotheses, not at their results. In this model the
    # explanation of a calibration gap is nearly always two lines of YAML.
    st.header("Starting configuration")
    st.caption(
        "What separates two runs **before** the solve. A result gap between two calibrations "
        "is explained first by the constraints one enables and the other does not — not by "
        "the solver."
    )
    run_by_folder = {
        entry["run_dir"].name: entry["run_dir"] for entry in series_catalog.values()
    }
    folders = sorted(run_by_folder)
    _default_left = next(
        (i.run_dir.name for i in resolved_references
         if i.reference.id == "gams_parity" and i.run_dir is not None),
        folders[0],
    )
    _default_right = next(
        (i.run_dir.name for i in resolved_references
         if i.reference.id == "retained" and i.run_dir is not None),
        folders[-1],
    )
    diff_cols = st.columns(2)
    left_folder = diff_cols[0].selectbox(
        "Reference (left)", folders, index=folders.index(_default_left)
    )
    right_folder = diff_cols[1].selectbox(
        "Compared with (right)", folders, index=folders.index(_default_right)
    )

    left_config = loaders.load_config_used(run_by_folder[left_folder])
    right_config = loaders.load_config_used(run_by_folder[right_folder])
    if left_config is None or right_config is None:
        missing = left_folder if left_config is None else right_folder
        st.info(
            f"`{missing}` carries no `config_used.yaml` (the run predates that record): "
            "the configuration diff cannot be computed."
        )
    elif left_folder == right_folder:
        st.info("Pick two different runs to see a configuration gap.")
    else:
        summary = config_diff.summarise(left_config, right_config)
        headline = summary["headline"]
        if not any(headline.values()) and not summary["scalars"]:
            st.success(
                f"`{left_folder}` and `{right_folder}` were solved with **exactly the same "
                "configuration**. Any result gap therefore comes from the solver (branching "
                "seed, incumbent at the time limit), not from the model."
            )
        else:
            bullets = []
            if headline["activated"]:
                bullets.append(
                    f"`{right_folder}` **enables**: "
                    + ", ".join(f"`{c}`" for c in headline["activated"])
                )
            if headline["deactivated"]:
                bullets.append(
                    f"`{right_folder}` **disables**: "
                    + ", ".join(f"`{c}`" for c in headline["deactivated"])
                )
            if headline["retuned"]:
                bullets.append(
                    "**thresholds changed** on: "
                    + ", ".join(f"`{c}`" for c in headline["retuned"])
                )
            if bullets:
                st.markdown("\n".join(f"- {b}" for b in bullets))

            for section, rows in summary["components"].items():
                if not rows:
                    continue
                st.markdown(f"**{config_diff.SECTION_LABELS[section]}**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Component": row["component"],
                                left_folder: row["left"],
                                right_folder: row["right"],
                                "Gap": row["verdict"],
                                "Changed arguments": " · ".join(
                                    f"{k}: {a} → {b}" for k, (a, b) in row["args"].items()
                                ),
                            }
                            for row in rows
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )

            if summary["scalars"]:
                st.markdown("**Parameters**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Parameter": row["key"],
                                left_folder: str(row["left"]),
                                right_folder: str(row["right"]),
                            }
                            for row in summary["scalars"]
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )

        st.caption(
            "This diff says what was **asked** of the two models, never what the gap **cost**: "
            "a constraint that does not bind changes no result, and two identical configs "
            "solved to the same gap can differ by the solver's branching arbitrariness "
            "(measured here: 0.15 point of PAD)."
        )

    # ------------------------------------------------- What the config diff actually moved
    st.subheader("What it moved on the ground")
    left_alloc = loaders.load_csv(run_by_folder[left_folder], "allocation_output.csv")
    right_alloc = loaders.load_csv(run_by_folder[right_folder], "allocation_output.csv")
    if left_alloc is None or right_alloc is None:
        st.info("One of the two runs has no usable `allocation_output.csv`.")
    elif left_folder == right_folder:
        st.info("Pick two different runs.")
    else:
        opts = st.columns(3)
        resolution = opts[0].radio(
            "Resolution", allocation_diff.RESOLUTIONS, horizontal=True,
            format_func=lambda r: {"fine": "Fine crop (84)",
                                   "base": "RPG group (12)"}[r],
            help="Comparing two SIMULATED runs is the only case where the fine resolution "
            "makes sense: both sides come from the same universe of 84 codes. The RPG group "
            "is the resolution the calibration is scored at.",
        )
        region_choice = opts[1].selectbox(
            "Region", ["All", *comparison.REGION_CODES],
            format_func=lambda v: v if v == "All" else comparison.label_region(v),
        )
        top_n = opts[2].slider("Moves shown", 5, 30, 12)

        aligned = allocation_diff.align(
            left_alloc, right_alloc,
            resolution=resolution,
            region=None if region_choice == "All" else region_choice,
        )
        stats = allocation_diff.stability(aligned)
        stat_cols = st.columns(3)
        stat_cols[0].metric("Unchanged area", f"{stats['share_ha']:.1%}",
                            f"{stats['same_ha']:,.0f} / {stats['total_ha']:,.0f} ha",
                            delta_color="off")
        stat_cols[1].metric("Unchanged plots", f"{stats['share_plots']:.1%}",
                            f"{stats['same_plots']:,} / {stats['total_plots']:,}",
                            delta_color="off")
        stat_cols[2].metric("Area moved",
                            f"{stats['total_ha'] - stats['same_ha']:,.0f} ha")

        moves = allocation_diff.top_moves(aligned, top=top_n)
        if moves.empty:
            st.success("The two runs allocate exactly the same thing.")
        else:
            shown = moves.copy()
            shown["From"] = [comparison.format_dim_value("subculture", c) for c in shown["left"]]
            shown["To"] = [comparison.format_dim_value("subculture", c) for c in shown["right"]]
            st.dataframe(
                shown[["From", "To", "surface_ha", "plots"]].rename(
                    columns={"surface_ha": "Area (ha)", "plots": "Plots"}
                ).style.format({"Area (ha)": "{:,.0f}", "Plots": "{:,.0f}"}),
                width="stretch", hide_index=True,
            )
            st.caption(
                "The largest flows from one crop to another, unchanged plots excluded. A "
                f"single line often carries the whole gap. `{allocation_diff.UNALLOCATED}` "
                "= land this run leaves out of production — that is not \"unchanged\"."
            )

            change = allocation_diff.net_change(aligned).head(top_n)
            change["Crop"] = [
                comparison.format_dim_value("subculture", c) for c in change["crop"]
            ]
            st.dataframe(
                change[["Crop", "left_ha", "right_ha", "delta_ha"]].rename(
                    columns={"left_ha": f"{left_folder} (ha)",
                             "right_ha": f"{right_folder} (ha)",
                             "delta_ha": "Gap (ha)"}
                ).style.format(precision=0),
                width="stretch", hide_index=True,
            )
            st.caption("Net balance per crop, ranked by size of the move.")

    # Per-scenario color, chosen freely and reused across every chart on the page (grouped bars +
    # indicator panels). Keyed by series label so a choice sticks as long as the series is shown.
    with st.expander("Scenario colours"):
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
    st.header("Compared bars")
    ctrl = st.columns(4)
    x_dim = ctrl[0].selectbox(
        "X axis", comparison.X_DIMENSIONS,
        format_func=lambda d: comparison.X_DIMENSION_LABELS[d],
    )
    measure = ctrl[1].selectbox(
        "Measure (y axis)", list(comparison.MEASURE_LABELS),
        format_func=lambda m: comparison.MEASURE_LABELS[m],
    )
    stack_options = ["none"] + [d for d in ("subculture", "region", "island", "culture") if d != x_dim]
    stack_by = ctrl[2].selectbox(
        "Stack by", stack_options,
        format_func=lambda s: "— none —" if s == "none" else comparison.X_DIMENSION_LABELS.get(s, s),
    )
    stacked = stack_by != "none"

    opt = st.columns(3)
    include_zeros = opt[0].checkbox("Include zero values", value=False)
    relative = opt[1].checkbox("Relative share (%)", value=False, disabled=not stacked)
    log = opt[2].checkbox("Log scale (grouped mode)", value=False, disabled=stacked)

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
            "Zero values taken from the crop catalogue (this run predates the recap's "
            "`crop_universe` field): the list may differ from the model's exact set. Rerun "
            "`python main.py` for an exhaustive axis faithful to the run."
        )
    if stacked:
        st.caption("Bar order within each group: " + " · ".join(selected))

    # ---------------------------------------------------- Development-indicator profile
    st.header("Development-indicator profile")
    chosen = st.multiselect(
        "Indicators", list(_INDICATOR_LABELS),
        default=["total_revenue", _GINI_KEY],
        format_func=lambda i: _INDICATOR_LABELS[i],
    )
    if not chosen:
        st.info("Pick at least one indicator.")
    else:
        rows = {}
        for lbl in selected:
            recap = series_catalog[lbl]["recap"]
            side = series_catalog[lbl]["side"]
            rows[lbl] = {ind: _indicator_value(recap, side, ind) for ind in chosen}
        raw = pd.DataFrame.from_dict(rows, orient="index")[chosen].dropna(axis=1, how="any")
        if raw.shape[1] < 1:
            st.warning("Indicators unavailable for these series (runs too old?).")
        else:
            st.pyplot(
                comparison.build_indicator_parallel_axes_figure(
                    raw, _INDICATOR_LABELS, series_colors
                )
            )
            st.caption(
                "Parallel coordinates: one vertical axis per indicator, each on its native "
                "scale (no normalisation). One line = one scenario (colour chosen above)."
            )

            # -------------------------------------------------- Composite score
            st.subheader("Composite score")
            st.caption(
                "Each indicator is min-max normalised over the displayed series, 1 = best of "
                "the lot; \"cost\" indicators (GHG, TFI, nitrogen, chlordecone, subsidy, labour "
                "cost, Gini) are inverted. Score = weighted mean. Set the weights below."
            )
            balance = st.checkbox(
                "Balance by family", value=True,
                help="Each family (economy, environment, self-sufficiency, exposure, "
                "intensity, equity) weighs the same whatever the number of indicators ticked "
                "in it. Without this, ticking the 11 self-sufficiency ratios gives them 11 "
                "times the weight of GHG — the score then measures how finely the list is "
                "cut, not performance.",
            )

            # An indicator a scenario PINS with a constraint is its hypothesis, not its
            # result. Warn rather than silently drop it: the user may want it on screen.
            pinned = {
                lbl: comparison.bound_indicators(series_catalog[lbl]["recap"]) & set(raw.columns)
                for lbl in raw.index
            }
            flagged = sorted({ind for inds in pinned.values() for ind in inds})
            if flagged:
                detail = "; ".join(
                    f"**{lbl}**: " + ", ".join(_INDICATOR_LABELS[i] for i in sorted(inds))
                    for lbl, inds in pinned.items()
                    if inds
                )
                st.warning(
                    "Some indicators are **fixed by a constraint** of the scenario, so they are "
                    "its hypotheses and not its results — scoring them measures what was "
                    "imposed on it. " + detail
                )

            weights: dict[str, float] = {}
            weight_cols = st.columns(min(len(raw.columns), 4))
            for idx, ind in enumerate(raw.columns):
                marker = " ⚠" if ind in flagged else ""
                weights[ind] = weight_cols[idx % len(weight_cols)].slider(
                    _INDICATOR_LABELS[ind] + marker,
                    min_value=0.0, max_value=1.0, value=1.0, step=0.05,
                    key=f"weight_{ind}",
                )
            scores = comparison.compute_composite_scores(
                raw, weights, balance_families=balance
            ).sort_values()
            score_colors = [series_colors.get(lbl) for lbl in scores.index]
            fig, ax = plt.subplots(figsize=(7, 0.5 * len(scores) + 1))
            ax.barh(range(len(scores)), scores.to_numpy(), color=score_colors)
            ax.set_yticks(range(len(scores)))
            ax.set_yticklabels(list(scores.index))
            ax.set_xlim(0, 1)
            ax.set_xlabel("Composite score (0–1)")
            for y, value in enumerate(scores.to_numpy()):
                ax.text(min(value + 0.01, 0.98), y, f"{value:.2f}", va="center", fontsize=8)
            fig.tight_layout()
            st.pyplot(fig)

    # ---------------------------------------------------- Food self-sufficiency panel
    st.header("Food self-sufficiency")
    _autonomy = {
        lbl: (series_catalog[lbl]["recap"].get("food_autonomy") or {}).get(
            series_catalog[lbl]["side"], {}
        )
        for lbl in selected
    }
    _autonomy = {lbl: auto for lbl, auto in _autonomy.items() if auto}
    if not _autonomy:
        st.info(
            "No selected series carries the `food_autonomy` block (runs predating that "
            "feature). Rerun `python main.py` for a comparable run."
        )
    else:
        variant_label = st.radio(
            "Variant", ["Crops only", "With fishing"], horizontal=True
        )
        variant = "with_fishing" if variant_label == "With fishing" else "crop_only"
        frame = comparison.autonomy_ratios_frame(_autonomy, variant)
        st.caption(
            "Ratio of local production to the population's need, per nutrient. A value ≥ 1 "
            "(dotted line) = self-sufficiency for that nutrient. The lowest nutrient bounds "
            "overall self-sufficiency."
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
        ax_auto.set_ylabel("Production / need ratio")
        ax_auto.legend(fontsize=8)
        fig_auto.tight_layout()
        st.pyplot(fig_auto)
else:
    st.warning("No run with a facts_*.csv table in outputs/. Run python main.py for a comparable run.")
