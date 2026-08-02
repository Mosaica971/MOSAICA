"""One screen's worth of verdict on a run, and the caveats that go with it.

Everything here is derived from `recap.json` alone -- no CSV, no dataset rebuild, no solve --
so the landing page opens instantly on any run folder.

WHY THE ALERTS EXIST. This model has a handful of readings that are wrong in a way no chart
reveals: a territorial PAD of 6.6 % looks like a triumph until you notice a constraint pins
the crop that carries it; an objective value looks converged until you notice the solve hit
its time limit and VIGILANCE records a hand-built solution beating that incumbent by 5.5 %.
Each alert below encodes one such trap, keyed off what the recap itself says, so the caveat
travels with the number instead of living only in a markdown file nobody opens.

Pure and Streamlit-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.dashboard.comparison import INDICATOR_LABELS, bound_indicators

# Severity levels, mapped to a Streamlit call by the page.
ERROR = "error"
WARNING = "warning"
INFO = "info"


@dataclass(frozen=True)
class Alert:
    """One caveat about reading this run. `title` is the claim, `body` the reason."""

    severity: str
    title: str
    body: str


# Recap blocks a modern run carries, and the page each one feeds. A run predating a block is
# not broken -- but a reader who opens the matching page and finds it empty deserves to know
# why, rather than concluding the feature is broken.
_EXPECTED_BLOCKS: dict[str, str] = {
    "environment": "indicateurs environnementaux",
    "food_autonomy": "autonomie alimentaire",
    "resilience": "exposition aux chocs",
    "calibration": "page Calibration",
    "intensity": "ratios d'intensité (page Prospective)",
    "agroecology": "surfaces MAE et bio",
}

# Constraint labels whose presence changes how a calibration score must be read: each PINS
# the crop group that dominates the territorial PAD, so that headline number stops being a
# result and becomes an assumption. Value = what to quote instead.
_PAD_PINNING_CONSTRAINTS: dict[str, str] = {
    "pn_prod_min": "le plancher de surface fourragère épingle la prairie",
    "bc_quota_max": "le plafond de marché borne le plantain",
}

_TERMINATION_OK = ("optimal", "globallyoptimal", "locallyoptimal")


def constraint_labels(recap: dict[str, Any]) -> set[str]:
    """Labels of every constraint this run enabled (recap lists only the enabled ones)."""
    labels: set[str] = set()
    for entry in recap.get("constraints") or []:
        label = (entry.get("args") or {}).get("label")
        if label:
            labels.add(str(label))
    return labels


def calibration_verdicts(recap: dict[str, Any]) -> list[dict[str, Any]]:
    """The four calibration metrics as {label, value, threshold, passed, unit} rows.

    `passed` is None when the metric has no threshold in the article (plot and area match
    rates are reported, never gated) or when the run was not scored at all.
    """
    calibration = recap.get("calibration") or {}
    if not calibration:
        return []
    thresholds = calibration.get("thresholds") or {}
    return [
        {
            "label": "PAD territorial",
            "value": calibration.get("regional_pad_pct"),
            "threshold": thresholds.get("regional_pad_max"),
            "passed": calibration.get("regional_within_threshold"),
            "better": "lower",
        },
        {
            "label": "Types d'exploitation reproduits",
            "value": calibration.get("farm_type_match_pct"),
            "threshold": thresholds.get("farm_type_match_min"),
            "passed": calibration.get("farm_type_within_threshold"),
            "better": "higher",
        },
        {
            "label": "Parcelles bien simulées",
            "value": calibration.get("plot_match_pct"),
            "threshold": None,
            "passed": None,
            "better": "higher",
        },
        {
            "label": "Surface bien simulée",
            "value": calibration.get("area_match_pct"),
            "threshold": None,
            "passed": None,
            "better": "higher",
        },
    ]


def run_alerts(recap: dict[str, Any]) -> list[Alert]:
    """Every caveat that applies to reading THIS run, most severe first."""
    alerts: list[Alert] = []
    labels = constraint_labels(recap)

    termination = str(recap.get("termination_condition") or "").lower()
    if termination and termination not in _TERMINATION_OK:
        alerts.append(
            Alert(
                ERROR,
                f"Solve non prouvé optimal (`{recap.get('termination_condition')}`)",
                "L'objectif affiché est un *incumbent*, pas un optimum démontré. Sur ce "
                "modèle ce n'est pas une nuance : une solution faisable construite à la main "
                "en quelques secondes a déjà battu de 5,5 % un incumbent obtenu en une heure "
                "(docs/04-vigilance.md, entrée « PAD résiduel »). Réamorcez le run avec un warm "
                "start (`solver.warm_start_from`) avant d'en tirer une conclusion.",
            )
        )

    pinning = sorted(labels & set(_PAD_PINNING_CONSTRAINTS))
    if pinning:
        reasons = " ; ".join(_PAD_PINNING_CONSTRAINTS[label] for label in pinning)
        alerts.append(
            Alert(
                WARNING,
                "Le PAD territorial n'est pas citable tel quel",
                f"Ce run active {', '.join(f'`{c}`' for c in pinning)} — {reasons}. Le PAD "
                "de la culture contrainte est nul par construction, ce qui tire le total "
                "vers le bas sans rien démontrer. Les chiffres à citer sont **types "
                "d'exploitation**, **parcelles** et **surface bien simulées**, qu'aucune de "
                "ces contraintes ne borne.",
            )
        )

    pinned = sorted(bound_indicators(recap))
    if pinned:
        named = ", ".join(INDICATOR_LABELS.get(key, key) for key in pinned)
        alerts.append(
            Alert(
                WARNING,
                "Des indicateurs sont fixés par une contrainte",
                f"{named} — ce sont les **hypothèses** du scénario, pas ses résultats. Noter "
                "une politique sur le plafond qu'elle s'est elle-même donné est circulaire.",
            )
        )

    objective = (recap.get("objective") or {}).get("name")
    if objective == "maximize_gross_margin":
        alerts.append(
            Alert(
                WARNING,
                "Objectif de marge brute pure",
                "Cet objectif ignore `Var_Rdt`, or c'est la seule chose qui sépare les "
                "cultures : il abandonne totalement la canne à sucre et la banane export, et "
                "porte le PAD territorial à ~193 %. L'objectif calibré est "
                "`maximize_risk_adjusted_gross_margin` (Markowitz).",
            )
        )

    stale = [name for name in _EXPECTED_BLOCKS if not recap.get(name)]
    if stale:
        pages = ", ".join(_EXPECTED_BLOCKS[name] for name in stale)
        alerts.append(
            Alert(
                INFO,
                "Run antérieur à certains blocs de reporting",
                f"Blocs absents du recap : {', '.join(f'`{n}`' for n in stale)}. "
                f"Conséquence : {pages} — ces vues resteront vides pour ce run. Un "
                "`python main.py` sur la config actuelle les remplit.",
            )
        )

    return alerts


def headline_gaps(
    pad_by_crop: "Any", *, top: int = 6, total_key: str = "TOTAL"
) -> "Any":
    """The `top` crop groups where simulated area departs most from observed, biggest first.

    Takes the `calibration_pad_by_crop` table and returns the same columns, minus the TOTAL
    row. Ranked by absolute hectares rather than by PAD percentage on purpose: a group of
    4 ha at 100 % PAD is arithmetically dramatic and agronomically irrelevant, and ranking by
    percentage puts it above a 3 000 ha miss on cane.
    """
    if pad_by_crop is None or "abs_deviation_ha" not in getattr(pad_by_crop, "columns", []):
        return None
    rows = pad_by_crop[pad_by_crop["crop"] != total_key]
    return rows.nlargest(top, "abs_deviation_ha")
