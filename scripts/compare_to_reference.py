"""Put a run side by side with the 2017 reference state.

    python scripts/compare_to_reference.py outputs/output_1

Reads the reference folder written by scripts/build_reference_state.py and the CSV/recap
files the run already wrote -- no dataset rebuild, no solve, ~1 s. Writes
`comparaison_reference.md` into the run folder and prints the headline block.

Two readings the run's own recap does not give:

* the deviation per crop is confronted with the REPRODUCIBILITY FLOOR of the reference, so a
  crop the model structurally cannot place (orchards, citrus) is not read as a modelling
  failure;
* every indicator gap is confronted with the reference's OWN BRACKET. The observed side has
  no fine crops, so its economics is an assumption with a range; a gap smaller than that
  range says nothing about the model. This is the difference between "the model loses 970
  ETP" and "the model lands inside the uncertainty of the observed figure".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import yaml

from case_studies.guadeloupe.domain.farm_typology import TYPE_EXPL_LABELS

from scripts._common import OUTPUTS_ROOT, ROOT

REFERENCE_DIR_NAME = "reference_2017"
TOTAL_KEY = "TOTAL"

# Reference indicator -> where the same quantity lives in a run's recap.json. The reference
# is built with the very same indicators.* functions, so these are the same computations on
# two allocations, not two definitions of one word.
_RECAP_KEYS: dict[str, tuple[str, str]] = {
    "production_tonnes": ("economics", "total_production_tonnes"),
    "subsidy": ("economics", "total_subsidy"),
    "revenue": ("economics", "total_revenue"),
    "gross_margin": ("economics", "total_gross_margin"),
    "labor_cost": ("economics", "total_labor_cost"),
    "net_revenue": ("economics", "total_net_revenue"),
    "etp": ("economics", "total_etp"),
    "azote": ("environment", "total_azote"),
    "ges": ("environment", "total_ges"),
    "ift": ("environment", "total_ift"),
    "surface_cld": ("environment", "surface_cld"),
    "water_need_m3": ("environment", "total_water_need_m3"),
    "soil_carbon_balance": ("environment", "soil_carbon_balance"),
}


def _relative(path: Path) -> str:
    """Repo-relative path when the folder sits inside the repo, so the markdown stays
    readable (and copy-pasteable) whatever the absolute location is."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _n(value: Any, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}".replace(",", " ")


def _run_side(recap: dict[str, Any], name: str) -> float | None:
    """The run's output-side value for a reference indicator, None when it has none."""
    if name == "sales":
        economics = recap["economics"]["output"]
        return economics["total_revenue"] - economics["total_subsidy"]
    if name == "labor_hours":
        return None  # compared through etp, which the recap carries directly
    block, key = _RECAP_KEYS.get(name, (None, None))
    if block is None:
        return None
    return recap[block]["output"][key]


def _reference_bracket(reference: dict[str, Any], name: str) -> tuple[float | None, float | None]:
    entry = reference["indicateurs"].get(name) or {}
    return entry.get("bas"), entry.get("haut")


def _within_bracket(value: float, low: float | None, high: float | None) -> bool | None:
    """True when the run's figure falls inside the reference's own uncertainty -- i.e. the
    gap is not evidence of anything. None when the indicator has no bracket."""
    if low is None or high is None:
        return None
    return min(low, high) <= value <= max(low, high)


def compare(run_dir: Path, reference_dir: Path) -> str:
    recap = json.loads((run_dir / "recap.json").read_text(encoding="utf-8"))
    reference = json.loads((reference_dir / "reference.json").read_text(encoding="utf-8"))
    pad_by_crop = pd.read_csv(run_dir / "csv" / "calibration_pad_by_crop.csv", index_col=0)
    field_match = pd.read_csv(run_dir / "csv" / "calibration_field_match.csv", index_col=0)
    confusion = pd.read_csv(
        run_dir / "csv" / "calibration_farm_type_confusion.csv", index_col=0
    )
    repro = pd.read_csv(
        reference_dir / "csv" / "reference_reproducibility.csv", index_col=0
    )
    run_config = yaml.safe_load((run_dir / "config_used.yaml").read_text(encoding="utf-8"))
    hours_per_etp = float((run_config.get("labor") or {}).get("hours_per_etp", 1607.0))

    calib = recap["calibration"]
    universe = reference["univers"]
    total = pad_by_crop.loc[TOTAL_KEY]
    field_total = field_match.loc[TOTAL_KEY]

    lines = [
        f"# {run_dir.name} vs situation de reference 2017",
        "",
        f"- Reference : `{reference_dir.name}` "
        f"({_n(universe['surface_cultivee_ha'])} ha cultives, "
        f"{_n(universe['parcelles_cultivees'])} parcelles, "
        f"{_n(universe['exploitations'])} exploitations)",
        f"- Run : objectif `{recap['objective']['name']}` = "
        f"{_n(recap['objective']['value'])}, resolu en "
        f"{recap['solve_duration_seconds']:.0f} s ({recap['termination_condition']})",
        f"- Annee / scenario : {recap['data']['year']} / {recap['data']['scenario']}",
        "",
        "## 1. Verdict de calibration",
        "",
        "| Metrique | Valeur | Seuil (Chopin et al. 2015) | Verdict |",
        "|---|---:|---:|---|",
        f"| PAD territorial | {calib['regional_pad_pct']:.1f} % | "
        f"{calib['thresholds']['regional_pad_max']:.0f} % | "
        f"{'OK' if calib['regional_within_threshold'] else 'HORS SEUIL'} |",
        f"| Cultures sous seuil | {calib['crops_within_threshold']} / "
        f"{calib['crops_evaluated']} | 8 / 10 | "
        f"{'OK' if calib['crops_within_threshold'] >= 8 else 'HORS SEUIL'} |",
        f"| Types d'exploitation reproduits | {calib['farm_type_match_pct']:.1f} % | "
        f"{calib['thresholds']['farm_type_match_min']:.0f} % | "
        f"{'OK' if calib['farm_type_within_threshold'] else 'HORS SEUIL'} |",
        f"| Exploitations sous seuil | {calib['farms_within_threshold']} / "
        f"{calib['farms_evaluated']} | - | - |",
        f"| Parcelles bien simulees | {calib['plot_match_pct']:.1f} % | 66 % (article) | "
        f"{'OK' if calib['plot_match_pct'] >= 66 else 'HORS SEUIL'} |",
        f"| Surface bien simulee | {calib['area_match_pct']:.1f} % | 77 % (article) | "
        f"{'OK' if calib['area_match_pct'] >= 77 else 'HORS SEUIL'} |",
        "",
        f"Plancher de PAD induit par l'eligibilite seule : "
        f"{reference['plancher_pad_pct']:.1f} % "
        f"({_n(reference['surface_irreproductible_ha'])} ha irreproductibles). L'ecart",
        "constate est donc tres majoritairement un choix du modele, pas une impossibilite.",
        "",
        "## 2. Assolement : observe vs simule",
        "",
        "`irreprod.` rappelle la part de l'observe qu'aucune variante fine ne pouvait porter.",
        "",
        "| Groupe | Observe (ha) | Simule (ha) | Ecart (ha) | PAD | Irreprod. (ha) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for group, row in pad_by_crop.drop(index=TOTAL_KEY).iterrows():
        pad = "-" if pd.isna(row["pad_pct"]) else f"{row['pad_pct']:.0f} %"
        irreproducible = (
            _n(repro.loc[group, "irreproductible_ha"]) if group in repro.index else "-"
        )
        lines.append(
            f"| {group} | {_n(row['observed_ha'])} | {_n(row['simulated_ha'])} | "
            f"{row['simulated_ha'] - row['observed_ha']:+,.0f} | {pad} | {irreproducible} |".replace(
                ",", " "
            )
        )
    lines += [
        f"| **TOTAL** | {_n(total['observed_ha'])} | {_n(total['simulated_ha'])} | "
        f"{total['simulated_ha'] - total['observed_ha']:+,.0f} | "
        f"{total['pad_pct']:.1f} % | "
        f"{_n(repro['irreproductible_ha'].sum())} |".replace(",", " "),
        "",
        "## 3. Indicateurs : reference vs run",
        "",
        "La colonne « dans la fourchette » compare l'ecart a l'incertitude de la reference",
        "elle-meme (cf. REFERENCE.md section 4.1). « oui » = le run tombe dans le domaine des",
        "assolements observes plausibles : l'ecart au central ne demontre rien.",
        "",
        "| Indicateur | Reference (central) | Fourchette | Run | Ecart | Dans la fourchette |",
        "|---|---:|---:|---:|---:|:--:|",
    ]

    verdicts: list[tuple[str, bool | None]] = []
    for name, entry in reference["indicateurs"].items():
        central = entry.get("central")
        run_value = _run_side(recap, name)
        if run_value is None or central is None:
            continue
        low, high = _reference_bracket(reference, name)
        # ETP has no bracket of its own; it is labor_hours / hours_per_etp, so it inherits it.
        if name == "etp":
            hours = reference["indicateurs"].get("labor_hours") or {}
            low = (hours.get("bas") or 0) / hours_per_etp or None
            high = (hours.get("haut") or 0) / hours_per_etp or None
        inside = _within_bracket(run_value, low, high)
        verdicts.append((name, inside))
        bracket = "-" if low is None or high is None else f"{_n(low)} - {_n(high)}"
        gap = f"{100.0 * (run_value - central) / central:+.0f} %" if central else "-"
        flag = {True: "oui", False: "non", None: "-"}[inside]
        lines.append(
            f"| {name} | {_n(central)} | {bracket} | {_n(run_value)} | {gap} | {flag} |"
        )

    inside_count = sum(1 for _, value in verdicts if value is True)
    bracketed = sum(1 for _, value in verdicts if value is not None)

    lines += [
        "",
        f"{inside_count} indicateur(s) sur {bracketed} encadres tombent dans la fourchette de",
        "la reference.",
        "",
        "## 4. Types d'exploitation",
        "",
        "Rappel de lecture : la diagonale est le taux de reproduction. La marge-ligne est la",
        "reference (typologie observee), la marge-colonne ce que le run produit.",
        "",
        "| Type | Observees | Simulees | Reproduites (rappel) |",
        "|---|---:|---:|---:|",
    ]
    recall = calib.get("farm_type_recall_by_type", {})
    observed_totals = confusion.sum(axis=1)
    simulated_totals = confusion.sum(axis=0)
    for code in confusion.index:
        diagonal = confusion.loc[code, str(code)] if str(code) in confusion.columns else 0
        observed = observed_totals.loc[code]
        share = f"{100.0 * diagonal / observed:.0f} %" if observed else "-"
        lines.append(
            f"| {code} {TYPE_EXPL_LABELS.get(int(code), '')} | {_n(observed)} | "
            f"{_n(simulated_totals.get(str(code), 0))} | {share} |"
        )
    if recall:
        worst = sorted(recall.items(), key=lambda item: item[1])[:3]
        lines += [
            "",
            "Types les moins bien reproduits : "
            + ", ".join(f"{label} ({value:.0f} %)" for label, value in worst)
            + ".",
        ]

    lines += [
        "",
        "## 5. Pour aller plus loin",
        "",
        f"- `python scripts/pad_all_scales.py {_relative(run_dir)}` : le PAD aux cinq",
        "  echelles, ile par ile comprise (reconstruit le dataset, ~7 s).",
        "- `csv/calibration_pad_by_crop_and_region.csv` : le detail sous-regional.",
        f"- `{_relative(reference_dir)}/REFERENCE.md` : comment la reference est construite",
        "  et ce qu'elle ne peut pas dire.",
        "",
        f"Correspondance parcellaire : {int(field_total['matched_plots'])} parcelles sur "
        f"{int(field_total['total_plots'])} portent la culture observee "
        f"({field_total['area_match_pct']:.1f} % de la surface).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="An outputs/output_N folder.")
    parser.add_argument(
        "--reference",
        type=Path,
        default=OUTPUTS_ROOT / REFERENCE_DIR_NAME,
        help=f"Reference folder (default outputs/{REFERENCE_DIR_NAME}).",
    )
    args = parser.parse_args(argv)

    if not (args.reference / "reference.json").exists():
        parser.error(
            f"{args.reference} has no reference.json -- run scripts/build_reference_state.py first"
        )

    markdown = compare(args.run_dir, args.reference)
    destination = args.run_dir / "comparaison_reference.md"
    destination.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"\nEcrit dans {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
