"""Genere `memoire/chiffres.tex` : une macro LaTeX par nombre cite dans le memoire.

POURQUOI. Un memoire qui cite deux cents valeurs issues d'une vingtaine de runs et recopiees
a la main contient des erreurs de transcription, et personne ne les trouve a la relecture --
un chiffre faux est aussi lisible qu'un chiffre juste. Ici chaque nombre est lu dans le
`recap.json` du run qui l'a produit et emis comme `\newcommand`. Consequence directe : si un
run est relance, il suffit de regenerer ce fichier pour que le memoire dise la verite, et une
valeur qu'aucun run ne porte plus provoque une ERREUR de generation au lieu de survivre
silencieusement dans le texte.

DEUX SOURCES, DEUX REGIMES.
  * EXTRACTIONS -- lues dans les recaps. C'est le cas normal, et il est verifie.
  * MESURES -- des chiffres qui ne vivent dans aucun recap : durees de solve comparees,
    denombrements du depot, valeurs relevees dans le journal d'enquetes ou dans une source
    externe (Agreste). Elles sont ecrites a la main ICI, chacune avec sa source, plutot que
    dispersees dans les chapitres. Une seule place a corriger.

    .venv/Scripts/python memoire/build_chiffres.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
TARGET = Path(__file__).resolve().parent / "chiffres.tex"

# --- Les runs cites, et le prefixe de macro de chacun -----------------------
# Les trois runs de calibration sont ceux que `references.yaml` declare ; l'etat observe
# 2017 est un artefact a part (il ecrit `reference.json`, pas `recap.json`).
RUNS: dict[str, str] = {
    "Parite": "calib_gams_parite",
    "BcSeul": "calib_bc_seul",
    "Retenu": "calib_retenu",
}

# (chemin dans le JSON, suffixe de macro, decimales)
# Les noms de macro ne contiennent QUE des lettres : LaTeX refuse les chiffres et les
# soulignes dans un nom de commande definie par \newcommand.
EXTRACTIONS: list[tuple[tuple[str, ...], str, int]] = [
    (("objective", "value"), "Objectif", 0),
    (("solve_duration_seconds",), "Duree", 0),
    (("calibration", "regional_pad_pct"), "Pad", 2),
    (("calibration", "farm_type_match_pct"), "Types", 1),
    (("calibration", "plot_match_pct"), "Parcelles", 1),
    (("calibration", "area_match_pct"), "Surface", 1),
    (("calibration", "crops_within_threshold"), "CulturesOk", 0),
    (("calibration", "crops_evaluated"), "CulturesTotal", 0),
    (("calibration", "subregional_cells_within_threshold"), "CellulesOk", 0),
    (("calibration", "farms_within_threshold"), "FermesOk", 0),
    (("calibration", "farms_evaluated"), "FermesTotal", 0),
    (("economics", "output", "total_gross_margin"), "Marge", 0),
    (("economics", "output", "total_subsidy"), "Subvention", 0),
    (("economics", "output", "total_etp"), "Etp", 0),
    (("economics", "output", "total_production_tonnes"), "Production", 0),
    (("economics", "output", "total_net_revenue"), "RevenuNet", 0),
    (("environment", "output", "total_azote"), "Azote", 0),
    (("environment", "output", "azote_per_ha"), "AzoteHa", 1),
    (("environment", "output", "total_ift"), "Ift", 0),
    (("environment", "output", "total_ges"), "Ges", 0),
    (("environment", "output", "total_water_need_m3"), "Eau", 0),
    (("output", "total_surface_ha"), "SurfaceHa", 0),
    (("input", "farm_count"), "Fermes", 0),
    (("input", "active_plot_count"), "Parcelles" + "Actives", 0),
]

# --- Chiffres qui ne vivent dans aucun recap --------------------------------
# Chacun porte sa source. Ne rien ajouter ici sans dire d'ou ca vient.
MEASUREMENTS: dict[str, tuple[str, str]] = {
    # Taille et tractabilite -- docs/04-vigilance.md B.1 et B.3
    "mesBinaires":        ("308847",  "variables binaires, configuration de calibration (04-vigilance B.1)"),
    "mesBinairesKarus":   ("879162",  "binaires si les 25 variantes Karusmart sont rouvertes (B.3)"),
    "mesBinairesRef":     ("331044",  "binaires sans elles (B.3)"),
    "mesSolveMin":        ("155",     "solve le plus rapide des 20 enregistres, en s (B.1)"),
    "mesSolveMax":        ("1007",    "solve le plus lent des 20 enregistres, en s (B.1)"),
    "mesSolveCV":         ("64",      "coefficient de variation des durees, en % (B.1)"),
    "mesWarmAvant":       ("720",     "solve a froid, en s (CLAUDE.md, journal 2026-07-29)"),
    "mesWarmApres":       ("209",     "meme solve avec warm start, en s"),
    "mesIncumbentEcart":  ("5,5",     "ecart de l'incumbent a une solution construite a la main, en % (B.2)"),
    "mesIncumbentGain":   ("4,45",    "le meme ecart en M EUR (B.2)"),
    # Garde-fous -- denombrements du depot au 2026-08-09
    "mesTests":           ("613",     "fonctions de test"),
    "mesTestsFichiers":   ("58",      "fichiers de test"),
    "mesChecksums":       ("570",     "checksums du golden snapshot"),
    "mesLignesCode":      ("18377",   "lignes de Python hors .venv"),
    # Solveur hors de cause -- 04-vigilance E.3
    "mesGraineA":         ("48,44",   "PAD territorial, graine HiGHS 1 (E.3)"),
    "mesGraineB":         ("48,29",   "graine 2"),
    "mesGraineC":         ("48,31",   "graine 3"),
    "mesBruitPad":        ("0,15",    "amplitude du bruit de branch-and-bound, en points de PAD"),
    "mesGapMip":          ("1",       "ecart d'optimalite relatif impose au solveur, en %"),
    # Territoire -- outputs/reference_2017/REFERENCE.md et Agreste
    "mesSauAgreste":      ("30066",   "SAU 2017 Guadeloupe, ha (Agreste SAA 2017)"),
    "mesCouvertureSau":   ("87",      "part de la SAU couverte par le jeu parcellaire, en %"),
    "mesBovins":          ("40449",   "bovins recenses en 2017 (Agreste)"),
    "mesUgb":             ("29771",   "UGB correspondantes"),
    "mesUgbHaSansPlancher": ("9,99",  "UGB/ha sans plancher de prairie -- agronomiquement impossible (C.3)"),
    "mesUgbHaAgreste":    ("3,10",    "UGB/ha sur les 9 595 ha d'Agreste"),
    "mesPrairieAgreste":  ("9595",    "prairie Agreste 2017, ha"),
    "mesPrairieRpg":      ("6109",    "prairie observee dans notre jeu parcellaire, ha"),
    # Calibration : les seuils de l'article -- Chopin et al. (2015)
    "mesArtPad":          ("15",      "seuil de PAD de l'article, en %"),
    "mesArtTypes":        ("81",      "types d'exploitation reproduits par l'article, en %"),
    "mesArtParcelles":    ("66",      "parcelles bien simulees par l'article, en %"),
    "mesArtSurface":      ("77",      "surface bien simulee par l'article, en %"),
    "mesArtFermes":       ("5336",    "exploitations de l'article (base 2010)"),
    "mesArtParcellesN":   ("25057",   "parcelles de l'article (base 2010)"),
    # Eligibilite et representantes -- 04-vigilance C.2 et REFERENCE.md
    "mesRepCanne":        ("31",      "part de la canne observee ou sa representante est eligible, en %"),
    "mesPlancherPad":     ("1,5",     "plancher de PAD impose par l'eligibilite, en %"),
    # P10 -- audit du 2026-08-09 (scripts/audit_warm_start_seed.py)
    "mesPdixBorneLp":     ("46311985", "borne de la relaxation LP de P10, en EUR"),
    "mesPdixViolationsP": ("407",     "contraintes violees par la graine P8 sous P10"),
    "mesPdixViolationsA": ("124",     "contraintes violees par la graine azote la plus serree"),
}


def _dig(data: dict, path: tuple[str, ...]) -> float | int | None:
    node = data
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node if isinstance(node, (int, float)) else None


def _fmt(value: float, decimals: int) -> str:
    """Format pour `\\num{}` : point decimal, aucun separateur de milliers.

    C'est siunitx qui francise a l'impression (virgule decimale, espace fine aux milliers),
    reglage fait une fois dans le preambule. Emettre deja francise ici casserait `\\num`.
    """
    if decimals == 0:
        return str(int(round(value)))
    return f"{value:.{decimals}f}"


def main() -> int:
    lines: list[str] = [
        "% " + "=" * 74,
        "% FICHIER GENERE par memoire/build_chiffres.py -- NE PAS EDITER A LA MAIN.",
        "%",
        "% Chaque nombre cite dans le memoire est ici, lu dans le recap.json du run qui l'a",
        "% produit. Les valeurs sont brutes (point decimal, pas de separateur) : c'est siunitx",
        "% qui francise a l'impression, via \\num{}.",
        "% " + "=" * 74,
        "",
    ]

    missing: list[str] = []
    for prefix, folder in RUNS.items():
        recap = OUTPUTS / folder / "recap.json"
        if not recap.exists():
            missing.append(f"{folder}/recap.json est absent")
            continue
        data = json.loads(recap.read_text(encoding="utf8"))
        lines.append(f"% --- {folder} " + "-" * (66 - len(folder)))
        for path, suffix, decimals in EXTRACTIONS:
            value = _dig(data, path)
            name = f"calib{prefix}{suffix}"
            if value is None:
                missing.append(f"{folder} : {'.'.join(path)} introuvable (macro \\{name})")
                continue
            lines.append(f"\\newcommand{{\\{name}}}{{{_fmt(value, decimals)}}}")

        # Variante en millions pour les montants qu'on cite dans le fil du texte : "81,2 M EUR"
        # se lit, "81 222 224 EUR" interrompt la phrase. La valeur reste derivee du recap, donc
        # elle ne peut pas diverger de la version longue utilisee dans les tableaux.
        for path, suffix in (
            (("objective", "value"), "Objectif"),
            (("economics", "output", "total_gross_margin"), "Marge"),
            (("economics", "output", "total_subsidy"), "Subvention"),
        ):
            value = _dig(data, path)
            if value is not None:
                lines.append(
                    f"\\newcommand{{\\calib{prefix}{suffix}M}}{{{_fmt(value / 1e6, 1)}}}"
                )

        # Le detail par culture : la surface simulee et le PAD, culture par culture. C'est le
        # tableau central du chapitre 3, et le seul endroit ou l'on voit que la canne revient
        # a sa surface observee sans qu'aucune contrainte ne la nomme.
        per_crop = OUTPUTS / folder / "csv" / "calibration_pad_by_crop.csv"
        if not per_crop.exists():
            missing.append(f"{folder}/csv/calibration_pad_by_crop.csv est absent")
            continue
        with per_crop.open(encoding="utf8", newline="") as handle:
            for row in csv.DictReader(handle):
                code = row["crop"]
                if code == "TOTAL":
                    continue
                lines.append(
                    f"\\newcommand{{\\sim{prefix}{code}}}"
                    f"{{{_fmt(float(row['simulated_ha']), 0)}}}"
                )
                lines.append(
                    f"\\newcommand{{\\pad{prefix}{code}}}"
                    f"{{{_fmt(float(row['pad_pct']), 1)}}}"
                )
        lines.append("")

    # L'etat observe 2017 n'est pas un run : il ecrit `reference.json`, dont le schema est
    # different (pas d'objectif, pas de calibration -- il EST la reference). D'ou sa propre
    # liste d'extractions. Ses indicateurs portent une fourchette basse/centrale/haute :
    # l'assolement 2017 n'etant connu qu'au niveau des 12 groupes RPG, la valeur "centrale"
    # repose sur l'hypothese `baseline_representative_crops` et n'est pas une observation.
    reference = OUTPUTS / "reference_2017" / "reference.json"
    if not reference.exists():
        missing.append("outputs/reference_2017/reference.json est absent")
    else:
        data = json.loads(reference.read_text(encoding="utf8"))
        lines.append("% --- reference_2017 (etat observe) " + "-" * 40)
        observed: list[tuple[tuple[str, ...], str, int]] = [
            (("univers", "parcelles"), "Parcelles", 0),
            (("univers", "exploitations"), "Exploitations", 0),
            (("univers", "surface_totale_ha"), "SurfaceTotale", 0),
            (("univers", "surface_cultivee_ha"), "SurfaceCultivee", 0),
            (("univers", "surface_non_cultivee_ha"), "SurfaceNonCultivee", 0),
            (("univers", "parcelles_cultivees"), "ParcellesCultivees", 0),
            (("plancher_pad_pct",), "PlancherPad", 1),
            (("surface_irreproductible_ha",), "SurfaceIrreproductible", 0),
            (("reclassement_jachere_vers_nc_ha",), "ReclassementNc", 0),
        ]
        for path, suffix, decimals in observed:
            value = _dig(data, path)
            name = f"obs{suffix}"
            if value is None:
                missing.append(f"reference.json : {'.'.join(path)} introuvable (\\{name})")
                continue
            lines.append(f"\\newcommand{{\\{name}}}{{{_fmt(value, decimals)}}}")
        # L'assolement observe, culture par culture : c'est la colonne de gauche de toute
        # comparaison du chapitre 3.
        for code, surface in (data.get("assolement_observe_ha") or {}).items():
            lines.append(f"\\newcommand{{\\obsHa{code}}}{{{_fmt(float(surface), 0)}}}")
        lines.append("")

    lines.append("% --- mesures hors recap (voir build_chiffres.py pour les sources) -----")
    for name, (value, source) in MEASUREMENTS.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}  % {source}")
    lines.append("")

    TARGET.write_text("\n".join(lines) + "\n", encoding="utf8")

    macros = sum(1 for line in lines if line.startswith("\\newcommand"))
    print(f"{TARGET.relative_to(ROOT)} : {macros} macros ecrites")
    if missing:
        print(f"\n{len(missing)} valeur(s) manquante(s) -- le memoire ne peut pas les citer :")
        for item in missing:
            print(f"  {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
