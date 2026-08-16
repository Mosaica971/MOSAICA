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
TABLES = Path(__file__).resolve().parent / "tables"

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
    # 681, verifie par `golden_snapshot.py --check` le 2026-08-12. La valeur 570 qui figurait
    # ici etait PERIMEE : elle datait du refactor du 2026-07-21, avant l'ajout des blocs
    # intensity / agroecology / P-K / Rpest. Cas d'ecole de MET-14 -- un chiffre de
    # documentation qui derive sans que rien ne le signale, dans le fichier meme dont la
    # raison d'etre est d'empecher les chiffres de deriver.
    "mesChecksums":       ("681",     "checksums du golden snapshot (verifie 2026-08-12)"),
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
    # LE PLANCHER DE PRAIRIE EST-IL UNE VARIABLE D'AJUSTEMENT ? -- balayage du 2026-07-28
    # (config.yaml:450-473, spec 2026-07-28-plancher-prairie-design.md).
    # Il faut le dire franchement : 6 096 EST l'observe. Le GAMS le documente lui-meme
    # ("QUOTA_PN_PIQ_MIN ... = surface 2017 PN_PIQ", DONNEES.txt:66), il tombe a 13 ha de
    # notre propre prairie de reference (6 109), et le livre blanc CALALOU releve 6 096 ha de
    # surface bovine observee. La regle du chapitre 3 -- une deviation se source HORS du
    # modele ET hors de l'observe -- l'interdirait donc. Ce qui autorise malgre tout la
    # deviation est le balayage : sur toute la plage exogene 6 096 -> 9 595 ha, les trois
    # metriques que le plancher NE TOUCHE PAS restent au-dessus des seuils publies, et le PAD
    # hors prairie EMPIRE quand on remonte vers la statistique. La conclusion ne depend pas
    # du seuil ; c'est le meme argument que le palier plat du plafond plantain.
    "mesPrairieExogene":  ("8341",    "prairie Agreste ramenee a notre couverture de 87 %, ha"),
    "mesPrairieHautTypes": ("82,0",   "types reproduits avec un plancher a 9 595 ha, en %"),
    "mesPrairieHautParcelles": ("65,2", "parcelles bien simulees, meme plancher, en %"),
    "mesPrairieHautSurface": ("72,2",  "surface bien simulee, meme plancher, en %"),
    "mesPadHorsPrairieBas": ("14,9",  "PAD hors prairie a un plancher de 7 218 ha, en %"),
    "mesPadHorsPrairieHaut": ("24,0", "le meme a 9 595 ha -- il EMPIRE quand le seuil monte, en %"),
    "mesCalalouBovins":   ("6096",    "surface bovine observee par CALALOU (Livre blanc, tab. 3), ha"),
    # Calibration : les seuils de l'article -- Chopin et al. (2015)
    # DEUX seuils, et le memoire les confondait. §2.6, p. 16 du manuscrit HAL : « less than
    # 15% for the primary crops at the regional scale, and 20% in the sub-regions and farms ».
    "mesArtPad":          ("15",      "seuil de PAD de l'article a l'echelle du territoire, en %"),
    "mesArtPadZone":      ("20",      "le meme seuil a l'echelle sous-regionale et a la ferme, en %"),
    "mesArtTypes":        ("81",      "types d'exploitation reproduits par l'article, en %"),
    "mesArtParcelles":    ("66",      "parcelles bien simulees par l'article, en %"),
    "mesArtSurface":      ("77",      "surface bien simulee par l'article, en %"),
    "mesArtFermes":       ("5336",    "exploitations de l'article (base 2010)"),
    "mesArtParcellesN":   ("25057",   "parcelles de l'article (base 2010)"),
    # Eligibilite et representantes -- 04-vigilance C.2 et REFERENCE.md
    "mesRepCanne":        ("31",      "part de la canne observee ou sa representante est eligible, en %"),
    "mesPlancherPad":     ("1,5",     "plancher de PAD impose par l'eligibilite, en %"),
    # LE PLAN OBSERVE, VALORISE SOUS NOTRE PROPRE OBJECTIF (journal 2026-07-27). Chaque
    # parcelle recoit la meilleure variante fine eligible de sa famille observee -- c'est donc
    # une BORNE HAUTE de ce que l'assolement reel vaut, les contraintes de ferme etant ignorees.
    "mesPlanObserveM":    ("72,2",    "plan observe 2017 valorise sous notre objectif, en M EUR"),
    "mesPlanOptimumM":    ("85,0",    "l'optimum du meme modele, en M EUR"),
    "mesPlanEcart":       ("15",      "de combien le plan observe est en dessous, en %"),
    "mesMoObserve":       ("5,68",    "heures demandees par le plan observe, en millions"),
    "mesMoPlafond":       ("6,25",    "plafond de main d'oeuvre du territoire, en millions d'heures"),
    # Le dispositif prospectif -- denombrements des catalogues au 2026-08-10
    "mesPolitiques":      ("10",      "politiques declarees dans scenarios_politiques.yaml"),
    "mesForcages":        ("12",      "forcages declares dans scenarios_forcages.yaml"),
    "mesBalayages":       ("2",       "fronts declares dans scenarios_pareto.yaml"),
    "mesPolitiquesVues":  ("7",       "politiques ayant au moins une cellule resolue"),
    "mesForcagesVus":     ("5",       "forcages ayant au moins une cellule resolue"),
    "mesSolvesProspectifs": ("33",    "dossiers de run prospectifs sur le disque"),
    "mesCellulesGrille":  ("14",      "cellules politique x forcage resolues (hors fronts)"),
    "mesCellulesTotal":   ("120",     "cellules du produit cartesien complet 10 x 12"),
    # P10 -- audit du 2026-08-09 (scripts/audit_warm_start_seed.py)
    "mesPdixBorneLp":     ("46311985", "borne de la relaxation LP de P10, en EUR"),
    "mesPdixViolationsP": ("407",     "contraintes violees par la graine P8 sous P10"),
    "mesPdixViolationsA": ("124",     "contraintes violees par la graine azote la plus serree"),
    # LE MEME PROBLEME RESOLU TROIS FOIS -- 04-vigilance B.8, mesures des 2026-08-10/11.
    # Trois solves de P8 non forcee, ensemble faisable IDENTIQUE a chaque fois, amorces en
    # chaine l'un sur l'autre. Le troisieme est prouve optimal, donc les deux premiers sont
    # faux d'un ecart connu -- c'est ce qui fait la demonstration du chapitre 4.
    "mesHuitUneHeure":    ("68445374", "P8 nue, 1 h de solve, en EUR (maxTimeLimit)"),
    "mesHuitTroisHeures": ("68644754", "la meme, 3 h, amorcee sur la precedente (maxTimeLimit)"),
    "mesHuitOptimum":     ("69088438", "la meme, +2,2 h, PROUVEE OPTIMALE"),
    "mesHuitEcartPct":    ("0,93",     "ecart du premier a l'optimum, en %"),
    "mesHuitPreuveDuree": ("8981",     "s pour PROUVER l'optimum en partant deja de lui (B.8)"),
    # La borne LP racine surestime ce qu'un solve a laisse -- 04-vigilance B.8
    "mesHuitBorneLp":     ("71065297", "borne de la relaxation LP de P8, en EUR"),
    "mesHuitSautInt":     ("2,78",     "saut d'integralite seul, en % de la borne LP"),
    "mesHuitEcartApparent": ("3,41",   "ecart du run de 3 h a la BORNE LP, en %"),
    "mesHuitEcartReel":   ("0,64",     "son ecart a l'optimum reel, en % -- cinq fois moins"),
    # LE CYCLE DE L'ANANAS. `Rdt_Cult` est un rendement PAR CYCLE ; l'economie l'annualise
    # (`/Duree_Cycle_Cult*12`, OPTIMISATION.txt:22-41), les TONNAGES non (PROD_*, TONNE_*,
    # NUTRI_* lisent Rdt_Cult brut). Sur 84 cultures, `Duree_Cycle_Cult.txt` ne porte qu'une
    # seule valeur differente de 12 : l'ananas, a 18 mois. C'est la seule culture pour
    # laquelle un tonnage du modele n'est PAS un tonnage annuel.
    "mesCycleAnanas":     ("18",       "duree de cycle de l'ananas, en mois (Duree_Cycle_Cult.txt)"),
}


# --- Rendements : le modele contre la statistique agricole ------------------
# POURQUOI CE TABLEAU. L'ecart residuel de calibration se concentre sur les petits postes,
# et sa cause commune est la meme partout : `Rdt_Cult` decrit des itineraires techniques
# SPECIFIES, la statistique agricole moyenne TOUS les producteurs et rapporte la production
# a la surface DECLAREE (jeunes vergers non entres en production compris). Les deux
# grandeurs ne mesurent pas la meme chose, et l'ecart se lit directement en marge a
# l'hectare : une culture dont le rendement est surevalue couvre l'ile des qu'aucun
# debouche ne la borne.
#
# COLONNE AGRESTE : *Memento de la statistique agricole -- Guadeloupe*, edition 2019
# (Statistique agricole annuelle 2017), p. 16-17. Agreste publie lui-meme une colonne
# `Rendement (t/ha)` -- ce n'est donc pas une division de notre fait. Recoupe contre le
# Memento 2020 (donnees 2019), qui donne les memes ordres de grandeur : ananas 12,91,
# plantain 9,3, igname 10,0, melon 19,3, agrumes 5,1, autres fruits 5,9.
#
# COLONNE MODELE : calculee ci-dessous sur le run retenu (production / surface par groupe),
# donc c'est le rendement effectivement porte par l'assolement simule, mixte de variantes
# fines compris -- pas une ligne de table choisie a la main.
_RDT_AGRESTE: dict[str, float] = {
    "AN": 12.3, "BC": 9.0, "MA": 10.8, "AG": 5.2, "IG": 10.0, "ME": 19.9, "VE": 6.4,
}
# Mois de cycle par groupe, quand ce n'est pas 12 (cf. `mesCycleAnanas`).
_CYCLE_MOIS: dict[str, int] = {"AN": 18}


def _table_rendements(run: str) -> list[str]:
    """Rendement simule (t/ha) par groupe RPG, confronte a la statistique agricole.

    Le rendement simule est `production / surface` sur le run, ce qui integre le melange de
    variantes fines que l'optimisation a retenu. Il est ensuite ANNUALISE (x 12 / cycle) :
    sans cette correction l'ananas serait compare a 18 mois contre 12, et le rapport
    surestime de moitie. C'est exactement l'erreur que l'entree C.1 de `docs/04-vigilance.md`
    a portee jusqu'au 2026-08-16.
    """
    def _somme(fichier: str, cle: str, valeur: str) -> dict[str, float]:
        chemin = OUTPUTS / run / "csv" / fichier
        total: dict[str, float] = {}
        with chemin.open(encoding="utf8", newline="") as f:
            for r in csv.DictReader(f):
                total[r[cle]] = total.get(r[cle], 0.0) + float(r[valeur])
        return total

    surfaces = _somme("calibration_pad_by_crop.csv", "crop", "simulated_ha")
    # production_by_crop est indexe par variante FINE ; on le replie sur les groupes RPG en
    # reutilisant le repli du depot plutot qu'une table recopiee ici.
    import sys

    sys.path.insert(0, str(ROOT))
    from case_studies.guadeloupe.domain.crop_families import base_group_for

    productions: dict[str, float] = {}
    chemin = OUTPUTS / run / "csv" / "production_by_crop_output.csv"
    with chemin.open(encoding="utf8", newline="") as f:
        for r in csv.DictReader(f):
            groupe = base_group_for(r["crop"])
            productions[groupe] = productions.get(groupe, 0.0) + float(r["production_tonnes"])

    lignes = []
    for code, agreste in _RDT_AGRESTE.items():
        ha = surfaces.get(code, 0.0)
        if ha <= 0:
            continue
        cycle = _CYCLE_MOIS.get(code, 12)
        par_cycle = productions.get(code, 0.0) / ha
        lignes.append((code, agreste, cycle, par_cycle, par_cycle * 12 / cycle))

    corps, macros = [], []
    # Trie par RAPPORT decroissant : c'est le rapport qui porte l'argument, et le melon --
    # seule culture ou les deux chiffres coincident -- doit se lire en dernier.
    for code, agreste, cycle, par_cycle, annuel in sorted(lignes, key=lambda t: -t[4] / t[1]):
        note = f" ({cycle} mois)" if cycle != 12 else ""
        corps.append(
            f"  {_NOMS_GROUPES.get(code, code)}{note} & \\num{{{_fmt(agreste, 1)}}} & "
            f"\\num{{{_fmt(par_cycle, 1)}}} & \\num{{{_fmt(annuel, 1)}}} & "
            f"$\\times$\\num{{{_fmt(annuel / agreste, 1)}}} \\\\"
        )
        macros += [
            f"\\newcommand{{\\rdtAgreste{code}}}{{{_fmt(agreste, 1)}}}",
            f"\\newcommand{{\\rdtModele{code}}}{{{_fmt(annuel, 1)}}}",
            f"\\newcommand{{\\rdtRapport{code}}}{{{_fmt(annuel / agreste, 1)}}}",
        ]
    _ecrire_tabular(
        "rendements", "@{}lrrrr@{}",
        ["Groupe", "Agreste 2017", "Modèle, par cycle", "Modèle, annualisé", "Rapport"],
        corps,
    )
    return macros


def _echelles_calibration(prefixe: str, run: str) -> list[str]:
    """Les deux echelles que le `recap.json` ne resume pas : exploitation et sous-region.

    Ces chiffres etaient SAISIS A LA MAIN dans le chapitre 3 et l'annexe E, et ils y etaient
    FAUX : la mediane de 18,5 % et la moyenne de 51,5 % sont celles du run de PARITE, citees
    comme si elles etaient celles de la calibration retenue (qui donne 0,0 et 26,4). Les
    generer supprime la classe d'erreur entiere.
    """
    def _colonne(fichier: str) -> list[dict[str, str]]:
        with (OUTPUTS / run / "csv" / fichier).open(encoding="utf8", newline="") as f:
            return list(csv.DictReader(f))

    fermes = sorted(float(r["pad_pct"]) for r in _colonne("calibration_pad_by_farm.csv"))
    n = len(fermes)
    mediane = fermes[n // 2] if n % 2 else (fermes[n // 2 - 1] + fermes[n // 2]) / 2
    moyenne = sum(fermes) / n

    # PAD agrege par sous-region : somme des ecarts absolus / somme des observes, c'est-a-dire
    # la meme convention "rapport de sommes" que le PAD territorial.
    obs: dict[str, float] = {}
    dev: dict[str, float] = {}
    for r in _colonne("calibration_pad_by_crop_and_region.csv"):
        obs[r["region"]] = obs.get(r["region"], 0.0) + float(r["observed_ha"])
        dev[r["region"]] = dev.get(r["region"], 0.0) + float(r["abs_deviation_ha"])
    pads = sorted(100 * dev[k] / obs[k] for k in obs if obs[k] > 0)
    seuil = 20.0  # seuil sous-regional de Chopin et al. (2015) -- ce n'est PAS le 15 % regional

    return [
        f"\\newcommand{{\\{prefixe}FermesPadMediane}}{{{_fmt(mediane, 1)}}}",
        f"\\newcommand{{\\{prefixe}FermesPadMoyenne}}{{{_fmt(moyenne, 1)}}}",
        f"\\newcommand{{\\{prefixe}FermesOkPct}}"
        f"{{{_fmt(100 * sum(1 for p in fermes if p <= seuil) / n, 1)}}}",
        f"\\newcommand{{\\{prefixe}RegionsTotal}}{{{len(pads)}}}",
        f"\\newcommand{{\\{prefixe}RegionsOk}}{{{sum(1 for p in pads if p <= seuil)}}}",
        f"\\newcommand{{\\{prefixe}RegionsPadMin}}{{{_fmt(pads[0], 1)}}}",
        f"\\newcommand{{\\{prefixe}RegionsPadMax}}{{{_fmt(pads[-1], 1)}}}",
        f"\\newcommand{{\\{prefixe}RegionsPadOkMax}}"
        f"{{{_fmt(max([p for p in pads if p <= seuil], default=0.0), 1)}}}",
        f"\\newcommand{{\\{prefixe}RegionsPadHorsMin}}"
        f"{{{_fmt(min([p for p in pads if p > seuil], default=0.0), 1)}}}",
    ]


# --- Les politiques citees au chapitre 4 ------------------------------------
# Prefixe de macro (LETTRES SEULEMENT : \newcommand refuse chiffres et soulignes) -> dossier.
# On prend la cellule NON FORCEE quand elle existe -- c'est la politique elle-meme, sans
# hypothese de contexte -- et la cellule F0_nominal sinon. Les deux devraient coincider, F0
# etant l'absence de forcage ; la ou elles different, c'est un defaut de convergence et non un
# resultat, et le chapitre le dit (cf. \prosEcartFzero).
PROSPECTIVE: dict[str, str] = {
    "Pun":     "p1_deregulation_totale",
    "Pquatre": "p4_statu_quo",
    "Pcinq":   "p5_austerite_budgetaire",
    "Psix":    "p6_verdissement_incitatif_f0_nominal",
    "Psept":   "p7_ecophyto_reglementaire_f0_nominal",
    "Phuit":   "p8_transition_agroecologique",
    "Pneuf":   "p9_souverainete_alimentaire_f0_nominal",
}

# Le sous-ensemble d'indicateurs qu'un scenario expose. On n'emet PAS le bloc `calibration`
# d'un run prospectif : le PAD y mesure l'ecart a 2017, or un scenario est fait pour s'en
# ecarter. Un PAD de scenario n'est pas un mauvais score, c'est une lecture interdite
# (docs/04-vigilance.md, et section \ref{sec:lectures}).
PROS_EXTRACTIONS: list[tuple[tuple[str, ...], str, int]] = [
    (("objective", "value"), "Objectif", 0),
    (("solve_duration_seconds",), "Duree", 0),
    (("economics", "output", "total_gross_margin"), "Marge", 0),
    (("economics", "output", "total_subsidy"), "Subvention", 0),
    (("economics", "output", "total_etp"), "Etp", 0),
    (("environment", "output", "total_azote"), "Azote", 0),
    (("environment", "output", "total_ift"), "Ift", 0),
    (("environment", "output", "total_ges"), "Ges", 0),
    (("environment", "output", "total_water_need_m3"), "Eau", 0),
    (("output", "total_surface_ha"), "SurfaceHa", 0),
    (("resilience", "output", "revenue_concentration_hhi"), "Hhi", 3),
]

# --- La grille politiques x forcages ----------------------------------------
# Les colonnes sont les forcages effectivement couverts. La grille est CREUSE : ni les dix
# politiques ni les douze forcages n'ont tourne, et c'est une limite du travail, pas un
# choix -- une cellule coute une heure de solve.
#
# LA COLONNE DE COMPARAISON EST LA MARGE BRUTE, PAS L'OBJECTIF. P1 est la seule politique a
# changer de fonction objectif (`maximize_gross_margin`, sans aversion au risque -- son
# libelle le dit : un exploitant suppose neutre au risque), donc sa valeur d'objectif n'est
# pas du meme genre que les autres et un tableau qui les alignerait serait faux.
# `scenarios_politiques.yaml` porte deja l'avertissement ; on l'applique ici.
GRILLE_INDICATEUR = ("economics", "output", "total_gross_margin")
GRILLE: dict[str, dict[str, str]] = {
    "Fzero": {
        "Pquatre": "p4_statu_quo_f0_nominal",
        "Psix":    "p6_verdissement_incitatif_f0_nominal",
        "Psept":   "p7_ecophyto_reglementaire_f0_nominal",
        "Phuit":   "p8_transition_agroecologique_f0_nominal",
        "Pneuf":   "p9_souverainete_alimentaire_f0_nominal",
    },
    "Fsix": {
        "Pquatre": "p4_statu_quo_f6_choc_intrants",
        "Psix":    "p6_verdissement_incitatif_f6_choc_intrants",
        "Psept":   "p7_ecophyto_reglementaire_f6_choc_intrants",
    },
    "Fneuf": {
        "Pquatre": "p4_statu_quo_f9_crise_systemique",
        "Phuit":   "p8_transition_agroecologique_f9_crise_systemique",
        "Pneuf":   "p9_souverainete_alimentaire_f9_crise_systemique",
    },
}

# --- Les fronts de Pareto ---------------------------------------------------
# (prefixe de macro, balayage, politique hote ou None, label de la contrainte balayee,
#  chemin de l'indicateur reellement atteint, dossier du run NON BALAYE de reference)
# La politique hote compte : le cout marginal de l'azote n'est pas le meme sous P8 que contre
# la configuration de reference, et c'est precisement ce que le chapitre compare.
#
# Le SEUIL est lu dans la contrainte du recap, pas dans le nom du dossier ; l'indicateur
# ATTEINT est lu dans le bloc environnement ou economie.
#
# LE RUN NON BALAYE sert de TEMOIN DE PLATEAU. Un point dont l'objectif retombe exactement sur
# le sien est un point ou le seuil ne contraint rien : il n'appartient pas au front, il le
# prolonge par une horizontale. C'est le controle que les specs designent, et le defaut que
# 04-vigilance A.7 documente -- un front peut etre entierement inactif si ses seuils sont
# calibres sur une autre configuration que celle qui l'heberge. On ne teste PAS "atteint <
# seuil" : avec des variables binaires par parcelle, l'atteint reste toujours un peu sous le
# plafond (ici 0,5 %) sans que la contrainte cesse de mordre pour autant.
FRONTS: list[tuple[str, str, str | None, str, tuple[str, ...], str]] = [
    ("azoteHuit", "pareto_azote", "P8_transition_agroecologique", "azote_max",
     ("environment", "output", "total_azote"), "p8_transition_agroecologique"),
    ("azoteRef", "pareto_azote", None, "azote_max",
     ("environment", "output", "total_azote"), "calib_retenu"),
    ("subvQuatre", "pareto_subventions", "P4_statu_quo", "budget_subventions",
     ("economics", "output", "total_subsidy"), "p4_statu_quo"),
]


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


_ENTIERS = ("zero", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
            "dix", "onze", "douze")


def _mot(n: int) -> str:
    """Un entier en lettres -- un nom de macro LaTeX ne peut pas contenir de chiffre."""
    return _ENTIERS[n] if n < len(_ENTIERS) else f"pt{'x' * n}"


def _ecrire_tabular(cible: str, colspec: str, entetes: list[str], corps: list[str]) -> None:
    """Ecrit un `tabular` COMPLET dans tables/<cible>.tex, entete et filets compris.

    POURQUOI LE TABLEAU ENTIER ET PAS SEULEMENT SES LIGNES. Le `\\input` de LaTeX n'est pas
    celui de TeX : il passe par `\\InputIfFileExists` et ses crochets de fichier, qui emettent
    du materiel non extensible. Dans un alignement, ce materiel OUVRE UNE CELLULE -- et le
    `\\bottomrule` qui suit devient alors un `\\noalign` egare, erreur fatale. Le contournement
    n'est pas de ruser avec la primitive : c'est de sortir le `\\input` de l'alignement. Le
    fichier porte donc l'environnement complet, et le chapitre ne l'entoure plus que d'un
    `table` avec sa legende et son label -- qui restent, eux, du texte a ecrire a la main.
    """
    TABLES.mkdir(exist_ok=True)
    lignes = [
        "% Genere par memoire/build_chiffres.py -- ne pas editer.",
        f"\\begin{{tabular}}{{{colspec}}}",
        "  \\toprule",
        "  " + " & ".join(f"\\textbf{{{e}}}" for e in entetes) + " \\\\",
        "  \\midrule",
        *corps,
        "  \\bottomrule",
        "\\end{tabular}",
    ]
    (TABLES / f"{cible}.tex").write_text("\n".join(lignes) + "\n", encoding="utf8")


def _tous_les_recaps() -> list[tuple[str, dict]]:
    """Tous les runs du disque. La decouverte se fait sur la presence d'un `recap.json`,
    comme dans le depot : cela met sur le meme plan dossiers nommes et numerotes, et exclut
    `reference_2017/` qui ecrit `reference.json`."""
    trouves = []
    for recap in sorted(OUTPUTS.glob("*/recap.json")):
        try:
            trouves.append((recap.parent.name, json.loads(recap.read_text(encoding="utf8"))))
        except json.JSONDecodeError:
            continue  # run tue en cours d'ecriture -- il n'a rien a dire
    return trouves


def _seuil(data: dict, label: str) -> float | None:
    for entry in data.get("constraints") or []:
        args = entry.get("args") or {}
        if args.get("label") == label and "threshold" in args:
            return float(args["threshold"])
    return None


def _points_du_front(recaps, sweep, policy, label, indicateur) -> list[dict]:
    """Les points d'un front, ordonnes par seuil croissant.

    Le rattachement se fait sur le TRIPLET (balayage, politique, forcage) porte par le recap,
    jamais sur le nom du dossier -- c'est ce qui permet a un point relance depuis un fichier
    d'etape separe de rejoindre le front des autres.
    """
    points = []
    for nom, data in recaps:
        if data.get("run_sweep") != sweep or data.get("run_policy") != policy:
            continue
        if data.get("run_forcing") is not None:
            continue  # un front force est un autre objet ; il se declare a part
        seuil = _seuil(data, label)
        objectif = _dig(data, ("objective", "value"))
        if seuil is None or objectif is None:
            continue
        points.append({
            "dossier": nom,
            "seuil": seuil,
            "atteint": _dig(data, indicateur),
            "objectif": objectif,
            "marge": _dig(data, ("economics", "output", "total_gross_margin")),
            "etp": _dig(data, ("economics", "output", "total_etp")),
            # Le prix dual de la contrainte BALAYEE, lu dans la relaxation lineaire. C'est une
            # pente LOCALE : elle ne vaut qu'au voisinage de ce point, alors que le front donne
            # la pente MOYENNE sur tout l'intervalle. Emettre les deux permet de montrer leur
            # ecart au lieu de l'affirmer.
            "dual": _dig(data, ("shadow_prices", label, "dual")),
            "prouve": data.get("termination_condition") == "optimal",
        })
    return sorted(points, key=lambda p: p["seuil"])


def _emettre_front(prefixe: str, points: list[dict], temoin: float | None) -> list[str]:
    """Ecrit `tables/front-<prefixe>.tex` (le corps du tableau) et rend les macros de synthese.

    POURQUOI UN CORPS DE TABLEAU GENERE PLUTOT QUE DES MACROS PAR POINT. Un front n'a pas un
    nombre de lignes connu d'avance : il en gagne quand un point manquant est relance. Un
    tableau ecrit a la main dans le chapitre aurait a etre re-edite a chaque fois, et c'est
    exactement le geste que ce fichier existe pour supprimer. Le chapitre fait
    `\\input{tables/front-azoteHuit}` et ne connait pas le nombre de points.
    """
    corps = []
    for point in points:
        # La dague marque un solve non prouve optimal. Elle est POSEE PAR LE GENERATEUR, donc
        # elle disparait d'elle-meme le jour ou le point est repris et converge -- une mise en
        # garde qu'on ne peut pas oublier de retirer, ni oublier de mettre.
        dague = "" if point["prouve"] else r"\dag"
        point["plateau"] = temoin is not None and point["objectif"] >= temoin * (1 - 1e-6)
        # Asterisque et non petit rond : accole a un nombre, un rond en exposant se lit degre.
        plat = r"\textsuperscript{*}" if point["plateau"] else ""
        corps.append(
            f"  \\num{{{_fmt(point['seuil'], 0)}}} & "
            f"\\num{{{_fmt(point['atteint'] or 0, 0)}}} & "
            f"\\num{{{_fmt(point['objectif'] / 1e6, 2)}}}{dague}{plat} \\\\"
        )
    _ecrire_tabular(
        f"front-{prefixe}", "@{}lrr@{}",
        ["Plafond", "Niveau atteint", "Objectif (M\\eur)"], corps,
    )

    macros = [f"\\newcommand{{\\front{prefixe}Points}}{{{len(points)}}}"]
    if not points:
        return macros
    bas, haut = points[0], points[-1]
    macros += [
        f"\\newcommand{{\\front{prefixe}SeuilBas}}{{{_fmt(bas['seuil'], 0)}}}",
        f"\\newcommand{{\\front{prefixe}SeuilHaut}}{{{_fmt(haut['seuil'], 0)}}}",
        f"\\newcommand{{\\front{prefixe}ObjBas}}{{{_fmt(bas['objectif'] / 1e6, 2)}}}",
        f"\\newcommand{{\\front{prefixe}ObjHaut}}{{{_fmt(haut['objectif'] / 1e6, 2)}}}",
        f"\\newcommand{{\\front{prefixe}Prouves}}"
        f"{{{sum(1 for p in points if p['prouve'])}}}",
    ]
    # La PENTE MOYENNE. C'est la grandeur que le front donne et que le prix dual ne donne pas :
    # le dual est une pente locale, valable au voisinage d'un point.
    # Elle se calcule sur la PARTIE MORDANTE du front seulement -- inclure un point de plateau
    # y melerait un segment horizontal et diluerait le cout marginal vers zero. Et elle est un
    # MINORANT des que l'une des deux extremites n'est pas prouvee optimale : son objectif est
    # alors sous-estime, donc l'ecart entre extremites aussi.
    mordants = [p for p in points if not p.get("plateau")]
    macros.append(f"\\newcommand{{\\front{prefixe}Plateau}}{{{len(points) - len(mordants)}}}")
    if len(mordants) >= 2 and mordants[-1]["seuil"] > mordants[0]["seuil"]:
        gauche, droite = mordants[0], mordants[-1]
        pente = ((droite["objectif"] - gauche["objectif"])
                 / (droite["seuil"] - gauche["seuil"]))
        macros += [
            f"\\newcommand{{\\front{prefixe}Pente}}{{{_fmt(pente, 2)}}}",
            f"\\newcommand{{\\front{prefixe}PenteBas}}{{{_fmt(gauche['seuil'], 0)}}}",
            f"\\newcommand{{\\front{prefixe}PenteHaut}}{{{_fmt(droite['seuil'], 0)}}}",
            f"\\newcommand{{\\front{prefixe}PenteExacte}}"
            f"{{{'oui' if gauche['prouve'] and droite['prouve'] else 'non'}}}",
        ]
    # Le dual du point le plus serre : la pente LOCALE, a confronter a \front...Pente qui est
    # la pente MOYENNE. Un ecart important entre les deux signifie que le front est convexe et
    # qu'extrapoler le dual serait faux -- c'est l'argument que le chapitre 4 fait tenir.
    if bas.get("dual") is not None:
        macros.append(f"\\newcommand{{\\front{prefixe}DualBas}}{{{_fmt(abs(bas['dual']), 2)}}}")

    # Point par point, pour les phrases qui en citent un seul.
    for i, point in enumerate(points, start=1):
        rang = _mot(i)
        macros += [
            f"\\newcommand{{\\front{prefixe}{rang}Seuil}}{{{_fmt(point['seuil'], 0)}}}",
            f"\\newcommand{{\\front{prefixe}{rang}Obj}}{{{_fmt(point['objectif'], 0)}}}",
            f"\\newcommand{{\\front{prefixe}{rang}ObjM}}{{{_fmt(point['objectif'] / 1e6, 2)}}}",
        ]
        if point.get("marge") is not None:
            macros.append(
                f"\\newcommand{{\\front{prefixe}{rang}MargeM}}"
                f"{{{_fmt(point['marge'] / 1e6, 2)}}}"
            )
        if point.get("etp") is not None:
            macros.append(
                f"\\newcommand{{\\front{prefixe}{rang}Etp}}{{{_fmt(point['etp'], 0)}}}"
            )
    return macros


_NOMS_GROUPES = {
    "AG": "Agrumes", "AN": "Ananas", "BA": "Banane export", "BC": "Banane plantain",
    "CS": "Canne à sucre", "IG": "Igname", "JA": "Jachère", "MA": "Maraîchage",
    "ME": "Melon", "PN": "Prairie", "VE": "Vergers",
}


def _table_realloc(cible: str, avant: str, apres: str, seuil_ha: float = 50.0) -> list[str]:
    """Ce que deux allocations deplacent, groupe par groupe, en hectares.

    Un tableau d'ecarts et non deux colonnes de niveaux : la question n'est pas ce que chaque
    scenario cultive, c'est ce que le passage de l'un a l'autre DEPLACE. Les groupes qui
    bougent de moins de `seuil_ha` sont replies dans une ligne "autres" -- les afficher
    donnerait a du bruit d'arrondi le meme poids visuel qu'a une filiere qui disparait.
    """
    def _lire(run: str) -> dict[str, float]:
        chemin = OUTPUTS / run / "csv" / "calibration_pad_by_crop.csv"
        with chemin.open(encoding="utf8", newline="") as f:
            return {r["crop"]: float(r["simulated_ha"])
                    for r in csv.DictReader(f) if r["crop"] != "TOTAL"}

    a, b = _lire(avant), _lire(apres)
    ecarts = sorted(((c, b.get(c, 0.0) - v) for c, v in a.items()),
                    key=lambda t: t[1], reverse=True)
    corps, reste = [], 0.0
    for code, delta in ecarts:
        if abs(delta) < seuil_ha:
            reste += delta
            continue
        corps.append(
            f"  {_NOMS_GROUPES.get(code, code)} & \\num{{{_fmt(a[code], 0)}}} & "
            f"\\num{{{_fmt(b.get(code, 0.0), 0)}}} & \\num{{{_fmt(delta, 0)}}} \\\\"
        )
    if abs(reste) >= 1:
        corps.append(f"  \\emph{{autres groupes}} & --- & --- & \\num{{{_fmt(reste, 0)}}} \\\\")
    _ecrire_tabular(
        cible, "@{}lrrr@{}",
        ["Groupe", "Avant (ha)", "Après (ha)", "Écart (ha)"], corps,
    )
    return [f"\\newcommand{{\\realloc{cible.title().replace('-', '')}Lignes}}{{{len(corps)}}}"]


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
        # Les deux echelles que le recap ne resume pas -- exploitation et sous-region. Elles
        # etaient saisies a la main, et a la main elles etaient fausses (cf. la docstring).
        lines += _echelles_calibration(f"calib{prefix}", folder)
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

    # --- Les politiques du chapitre 4 --------------------------------------
    recaps = _tous_les_recaps()
    par_dossier = dict(recaps)
    lines.append("% --- politiques prospectives " + "-" * 46)
    for prefixe, dossier in PROSPECTIVE.items():
        data = par_dossier.get(dossier)
        if data is None:
            missing.append(f"{dossier}/recap.json est absent (politique \\pros{prefixe}*)")
            continue
        for path, suffix, decimals in PROS_EXTRACTIONS:
            value = _dig(data, path)
            name = f"pros{prefixe}{suffix}"
            if value is None:
                missing.append(f"{dossier} : {'.'.join(path)} introuvable (\\{name})")
                continue
            lines.append(f"\\newcommand{{\\{name}}}{{{_fmt(value, decimals)}}}")
        objectif = _dig(data, ("objective", "value"))
        if objectif is not None:
            lines.append(f"\\newcommand{{\\pros{prefixe}ObjectifM}}{{{_fmt(objectif / 1e6, 2)}}}")
        # La dague de non-convergence, posee par le generateur pour la meme raison que sur les
        # fronts : elle doit disparaitre toute seule quand le run est repris.
        prouve = data.get("termination_condition") == "optimal"
        lines.append(f"\\newcommand{{\\pros{prefixe}Flag}}{{{'' if prouve else r'\dag'}}}")
        lines.append(f"\\newcommand{{\\pros{prefixe}Prouve}}{{{'oui' if prouve else 'non'}}}")
    lines.append("")

    # LE TEMOIN DE NON-CONVERGENCE. F0_nominal est le forcage NUL : il ne change aucun
    # coefficient. P4 nue et P4 x F0 devraient donc rendre le meme optimum. L'ecart entre les
    # deux ne mesure aucun effet de scenario -- il mesure ce qu'un solve arrete a la limite de
    # temps a laisse sur la table. C'est le chiffre qui justifie la reprise du lot D, et il
    # vaut mieux qu'un discours sur la convergence.
    #
    # AVANT / APRES. Le temoin ne vaut que tant que la cellule forcee n'a pas ete reprise :
    # une fois les deux runs converges, l'ecart tombe a zero et le chiffre disparait -- alors
    # que c'est justement la demonstration qu'on veut garder. On lit donc AUSSI la version
    # ecartee dans `outputs/_non_converges/`, ce qui transforme le temoin en avant/apres :
    # l'ecart valait tant, il etait entierement imputable au branch-and-bound, une graine
    # correcte l'annule. Rien a editer le jour de la reprise, les macros suivent.
    # `\prosEcartFzeroRepris` vaut oui/non : le chapitre choisit sa phrase dessus.
    nue = _dig(par_dossier.get("p4_statu_quo") or {}, ("objective", "value"))
    cellule = par_dossier.get("p4_statu_quo_f0_nominal") or {}
    forcee = _dig(cellule, ("objective", "value"))
    repris = cellule.get("termination_condition") == "optimal"
    # `_tous_les_recaps` ne descend que d'un niveau (`outputs/*/recap.json`), donc la
    # quarantaine n'entre jamais dans `par_dossier` ni dans la grille -- il faut la lire ici.
    ecarte = OUTPUTS / "_non_converges" / "p4_statu_quo_f0_nominal" / "recap.json"
    avant = None
    if ecarte.exists():
        try:
            avant = _dig(json.loads(ecarte.read_text(encoding="utf8")), ("objective", "value"))
        except json.JSONDecodeError:
            pass
    if avant is None:
        avant = forcee  # pas encore reprise : l'ecart courant EST l'ecart d'avant
    if nue is not None and avant is not None:
        lines.append("% --- temoin : F0 est le forcage nul, l'ecart est du solveur seul -----")
        lines.append(f"\\newcommand{{\\prosEcartFzero}}{{{_fmt(nue - avant, 0)}}}")
        lines.append(
            f"\\newcommand{{\\prosEcartFzeroPct}}{{{_fmt(100 * (nue - avant) / nue, 2)}}}"
        )
        lines.append(
            f"\\newcommand{{\\prosEcartFzeroRepris}}{{{'oui' if repris else 'non'}}}"
        )
        if forcee is not None:
            lines.append(
                f"\\newcommand{{\\prosEcartFzeroApres}}{{{_fmt(abs(nue - forcee), 0)}}}"
            )
        # Le prix de la reparation. C'est la moitie de la demonstration : l'ecart n'etait pas
        # une fatalite de taille du probleme, il tenait a une graine -- et il s'est ferme en
        # quelques minutes la ou le run initial avait consomme son heure entiere.
        duree = _dig(cellule, ("solve_duration_seconds",))
        if duree is not None:
            lines.append(f"\\newcommand{{\\prosEcartFzeroDuree}}{{{_fmt(duree, 0)}}}")
        lines.append("")

    # --- La grille et le regret ---------------------------------------------
    # Le REGRET DE SAVAGE se calcule contre la meilleure politique DU MEME FORCAGE, jamais
    # contre un optimum global : la question est "qu'aurais-je perdu a avoir choisi celle-ci
    # plutot que la bonne, sachant que ce contexte-la est survenu". La convention est celle
    # de core/reporting/robustness.py, reprise ici pour que le memoire cite exactement ce que
    # le tableau de bord affiche.
    lines.append("% --- grille politiques x forcages (MARGE BRUTE -- voir GRILLE) --------")
    for forcage, cellules in GRILLE.items():
        valeurs: dict[str, float] = {}
        nettes: dict[str, float] = {}
        for politique, dossier in cellules.items():
            data = par_dossier.get(dossier)
            if data is None:
                missing.append(f"{dossier}/recap.json est absent (cellule {politique}x{forcage})")
                continue
            valeur = _dig(data, GRILLE_INDICATEUR)
            if valeur is None:
                missing.append(f"{dossier} : marge brute introuvable")
                continue
            valeurs[politique] = valeur
            lines.append(
                f"\\newcommand{{\\grille{politique}{forcage}}}{{{_fmt(valeur / 1e6, 2)}}}"
            )
            # LA MEME GRILLE, TRANSFERT DEDUIT. La marge brute contient la subvention
            # (PB = ventes + aides, MB = PB - charges), or ces politiques deplacent
            # justement les aides : classer P9 devant P4 sur la marge brute, c'est en partie
            # constater que P9 subventionne davantage. Ventes moins charges isole ce que
            # l'assolement PRODUIT, independamment de ce que la collectivite y met. Les deux
            # lectures sont legitimes et ne donnent pas le meme classement -- le chapitre
            # montre l'ecart plutot que d'en choisir une en silence.
            aide = _dig(data, ("economics", "output", "total_subsidy"))
            if aide is not None:
                nettes[politique] = valeur - aide
                lines.append(
                    f"\\newcommand{{\\grilleNet{politique}{forcage}}}"
                    f"{{{_fmt((valeur - aide) / 1e6, 2)}}}"
                )
            prouve = data.get("termination_condition") == "optimal"
            lines.append(
                f"\\newcommand{{\\grille{politique}{forcage}Flag}}"
                f"{{{'' if prouve else r'\dag'}}}"
            )
        for etiquette, table in (("", valeurs), ("Net", nettes)):
            if not table:
                continue
            meilleure = max(table, key=lambda k: table[k])
            lines.append(
                f"\\newcommand{{\\grilleMeilleure{etiquette}{forcage}}}{{{meilleure}}}"
            )
            for politique, valeur in table.items():
                lines.append(
                    f"\\newcommand{{\\regret{etiquette}{politique}{forcage}}}"
                    f"{{{_fmt((table[meilleure] - valeur) / 1e6, 2)}}}"
                )
    lines.append("")

    # --- Les fronts ---------------------------------------------------------
    lines.append("% --- fronts de Pareto " + "-" * 53)
    for prefixe, sweep, policy, label, indicateur, hote in FRONTS:
        points = _points_du_front(recaps, sweep, policy, label, indicateur)
        if not points:
            missing.append(f"front {prefixe} : aucun point sur le disque")
        temoin = _dig(par_dossier.get(hote) or {}, ("objective", "value"))
        if temoin is None:
            missing.append(f"front {prefixe} : temoin non balaye `{hote}` absent")
        else:
            lines.append(f"\\newcommand{{\\front{prefixe}Temoin}}{{{_fmt(temoin / 1e6, 2)}}}")
        lines += _emettre_front(prefixe, points, temoin)
    lines.append("")

    # Ce que le serrage de l'enveloppe publique deplace sur le terrain.
    lines.append("% --- reallocation sous plafond de subventions " + "-" * 30)
    lines += _table_realloc(
        "realloc-budget", "p4_statu_quo",
        "p4_statu_quo_pareto_subventions_threshold_35900000",
    )
    lines.append("")

    # Le rendement du modele contre celui du territoire : la cause commune de l'ecart
    # residuel du chapitre 3, et la raison pour laquelle les plafonds de marche ne sont pas
    # des bequilles.
    lines.append("% --- rendements : modele contre statistique agricole " + "-" * 21)
    lines += _table_rendements("calib_retenu")
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
