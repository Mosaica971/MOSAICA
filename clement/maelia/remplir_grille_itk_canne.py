"""Remplit la grille d'entretien experts ITK de MAELIA pour la canne à sucre (exercice).

    .venv/Scripts/python clement/maelia/remplir_grille_itk_canne.py

Lit `clement/maelia/grille_itk_template.xlsx` (copie de « Grille entretien experts
ITK_mai2025.xlsx », version MAELIA 1.4.22) et écrit
`clement/maelia/grille_itk_canne_guadeloupe.xlsx`.

Chaque valeur porte sa source entre crochets dans la colonne Commentaire :
    [MOSAICA]   tables GAMS de MOSAICA (Matrice_OTK_Cult_RESTIT, Data_OTK, indice_H), 2017
    [Agreste14] enquête Agreste « pratiques culturales canne à sucre » 2014 (DAAF, 2018)
    [RA2020]    fiche DAAF « exploitations cultivant de la canne » (recensement agricole)
    [Presse]    dates des campagnes sucrières 2023-2026 (RCI, Outremers360)
    [Martinique] fiche Chambre d'agriculture de Martinique (à transposer)
    [HYPOTHÈSE] valeur proposée sans source : à faire valider par un expert
Les conditions de déclenchement (pluie, humidité du sol, stade) sont laissées vides : aucune
source n'en donne, c'est l'objet de l'entretien.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import column_index_from_string, get_column_letter

ICI = Path(__file__).resolve().parent
SOURCE = ICI / "grille_itk_template.xlsx"
SORTIE = ICI / "grille_itk_canne_guadeloupe.xlsx"

AN = 2017  # année de référence des dates (seuls jour et mois comptent)


def d(jour: int, mois: int, an: int = AN) -> dt.date:
    return dt.date(an, mois, jour)


# Colonnes d'un bloc d'opération, relatives à la colonne « Date début » du bloc.
CHAMPS = ["debut", "fin", "nb_jours", "outil", "profondeur", "dose", "nature", "debit",
          "pluie", "dependance", "tmin", "stade_min", "stade_max", "humidite", "autres",
          "commentaire"]
DEBUT_BLOC = {1: "B", 2: "T", 3: "AL"}  # ITK n°1, 2, 3


def cellule(itk: int, champ: str, ligne: int) -> str:
    col = column_index_from_string(DEBUT_BLOC[itk]) + CHAMPS.index(champ)
    return f"{get_column_letter(col)}{ligne}"


def operation(ws, itk: int, ligne: int, **valeurs) -> None:
    for champ, valeur in valeurs.items():
        c = ws[cellule(itk, champ, ligne)]
        c.value = valeur
        if isinstance(valeur, dt.date):
            c.number_format = "dd/mm"


def entete(ws, itk: int, ligne: int, valeur: str) -> None:
    ws[f"{DEBUT_BLOC[itk]}{ligne}"] = valeur


# --- données ----------------------------------------------------------------------------------

# Opérations de la matrice MOSAICA communes aux 18 variantes de canne à sucre (passages par
# cycle ; AMORTI=1 = une fois par plantation de 7 ans, 3 ans en Sud-Est Basse-Terre).
ENGRAIS = ("18-09-28, 400 kg/ha/an (800 kg × 0,5) = 72 N, 36 P2O5, 112 K2O [MOSAICA]. "
           "Agreste 2014 : 135 kg N/ha en moyenne, en un passage, sur 95 % des surfaces ; "
           "plus en Basse-Terre, moins à Marie-Galante [Agreste14]. Écart à trancher.")
DEBIT_PULVE = round(1 / 3, 2)  # PULVE_MECA_ENG_PHYTO : 3 h/ha de main-d'œuvre [MOSAICA]


def remplir_canne(ws) -> None:
    ws["B11"] = "Canne à sucre"
    ws["B12"] = ("R570 et R579 en Basse-Terre ; B80689 en Grande-Terre et à Marie-Galante "
                 "[Agreste14]")
    ws["B14"] = (
        "Culture pluriannuelle : une année de plantation (canne vierge) puis des repousses ; "
        "replantation tous les 7 ans en moyenne [Agreste14, MOSAICA ; 3 ans en Sud-Est "
        "Basse-Terre]. Cycle moyen de 370 jours pour une repousse, 330 jours pour une canne "
        "plantée [Agreste14]. 12 417 ha et 3 087 exploitations en 2020, 966 ha irrigués "
        "[RA2020]. Dans MAELIA : séquence plantation puis 6 repousses (« canneP_canneR_… »), "
        "à valider avec l'équipe. Légende des sources : voir l'en-tête du script "
        "remplir_grille_itk_canne.py.")

    # Tableau récapitulatif des ITK (lignes 12 à 14, colonnes F à L).
    recap = [
        ("canneR_pluvial_recolteMeca", "Nord, Est et Centre Grande-Terre (sols profonds) ; "
         "Basse-Terre (parcelles ≥ 0,2 ha) ; Sud-Est Basse-Terre", "Canne (repousse)",
         "Tous (vertisols 68 %, ferralsols 27 % des surfaces en canne)", "Toutes", "Non",
         "Récolte mécanisée"),
        ("canneP_plantation", "Toutes", "Canne en fin de cycle, jachère", "Tous", "Toutes",
         "Non", "Année de replantation"),
        ("canneR_pluvial_recolteSemiMeca", "Marie-Galante ; Grande-Terre (sols courts) ; "
         "Basse-Terre (parcelles < 0,2 ha)", "Canne (repousse)", "Tous", "Toutes", "Non",
         "Récolte semi-mécanisée"),
    ]
    for i, valeurs in enumerate(recap):
        for col, v in zip("FGHIJKL", valeurs):
            ws[f"{col}{12 + i}"] = v

    criteres = {
        1: ["Repousse de canne, pluviale, récolte mécanisée",
            "Nord, Est, Centre Grande-Terre ; Basse-Terre ; Sud-Est Basse-Terre",
            "Canne (repousse)", "Tous ; MOSAICA ne distingue pas l'ITK selon le sol",
            "Toutes ; 96 % des planteurs se disent spécialisés canne [Agreste14]",
            "Non", "Sucrerie (Gardel) ou distillerie",
            "Parcelle mécanisable : pente ≤ 20 % ; en Grande-Terre sol non squelettique ; en "
            "Basse-Terre parcelle ≥ 0,2 ha [MOSAICA, règles GAMS ENTREES.txt]",
            "ITK principal (≈ 76 % des surfaces en canne en 2017 d'après les règles GAMS)."],
        2: ["Année de plantation (canne vierge)", "Toutes", "Canne en fin de cycle ; jachère",
            "Tous", "Toutes", "Non", "Sucrerie ou distillerie",
            "Une parcelle sur 7 chaque année ; 94 % des surfaces labourées avant plantation "
            "[Agreste14]",
            "Opérations amorties sur la plantation dans MOSAICA ; la première récolte a lieu "
            "à la campagne suivante (cycle de 330 jours)."],
        3: ["Repousse de canne, pluviale, récolte semi-mécanisée",
            "Marie-Galante ; Grande-Terre ; Basse-Terre", "Canne (repousse)", "Tous", "Toutes",
            "Non", "Sucrerie (Gardel, SRMG à Marie-Galante) ou distillerie",
            "Marie-Galante (toutes les parcelles) ; Grande-Terre sur sol court ; Basse-Terre "
            "si parcelle < 0,2 ha [MOSAICA, règles GAMS]",
            "Coupe manuelle, chargement mécanique. Rendement MOSAICA 20 % plus bas que la "
            "variante mécanisée de la même région."],
    }
    for itk, v in criteres.items():
        for ligne, valeur in zip((29, 31, 32, 33, 34, 35, 36, 37, 39), v):
            entete(ws, itk, ligne, valeur)

    # --- 1) travail du sol, plantation, récolte ---------------------------------------------
    recolte_meca = dict(
        debut=d(15, 2), fin=d(30, 6), outil="Coupeuse-chargeuse (prestataire, SICA)",
        commentaire="Campagne sucrière : broyage 12/04-14/08 en 2023, ~24/03-20/07 en 2024, "
                    "coupe dès février et arrêt le 11/07 en 2025, 10/03-08/07 en 2026 "
                    "[Presse]. Récolte prestée : 11 €/t, pas de temps exploitant [MOSAICA]. "
                    "Rendement 73 t/ha en 2014 [Agreste14], 59 t/ha en 2021 (Agreste) ; "
                    "MOSAICA 54-97 t/ha selon la région (surestimé, vigilance C.1).")
    for itk, outil, cout in ((1, "Coupeuse-chargeuse (prestataire)", "11 €/t"),
                             (3, "Coupe manuelle, chargement mécanique", "18 €/t, 11 €/t à "
                                 "Marie-Galante")):
        operation(ws, itk, 57, **{**recolte_meca, "outil": outil,
                                  "commentaire": recolte_meca["commentaire"].replace(
                                      "11 €/t", cout)})
        operation(ws, itk, 58, debut=d(1, 7), fin=d(15, 8),
                  commentaire="Prolongation de fin de campagne (2023 : jusqu'au 14/08) "
                              "[Presse]. Fenêtre à valider.")
        entete(ws, itk, 60, "Repousse : pas de travail du sol ni de plantation. Pailles "
                            "(feuilles) laissées au champ : pratique à confirmer. Désherbage "
                            "manuel sur 65 % des surfaces, mécanique sur 25 % (1,1 passage "
                            "en repousse) [Agreste14] : pas de ligne dans cette grille.")

    # ITK 2 : plantation.
    operation(ws, 2, 47, debut=d(1, 5), fin=d(31, 7), outil="Charrue (prestation)",
              commentaire="Labour avant plantation sur 94 % des surfaces [Agreste14] ; "
                          "prestation 250 €/ha [MOSAICA]. Profondeur non renseignée (outil "
                          "et profondeur absents de la liste MAELIA). Dates [HYPOTHÈSE].")
    operation(ws, 2, 49, debut=d(15, 5), fin=d(15, 8), outil="Pulvériseur à disques",
              debit=round(1 / 6, 2),
              commentaire="6 h/ha [MOSAICA]. Dates [HYPOTHÈSE].")
    operation(ws, 2, 51, debut=d(1, 6), fin=d(31, 8), outil="Sillonneur", profondeur=45,
              debit=round(1 / 6, 2),
              commentaire="6 h/ha ; sillons de 45 cm (PROF_SILLONS) [MOSAICA]. Dates "
                          "[HYPOTHÈSE].")
    operation(ws, 2, 55, debut=d(1, 6), fin=d(30, 9),
              outil="Plantation de boutures (prestation)",
              dose="11 unités de plants/ha", nature="Boutures",
              commentaire="Plantation 437 €/ha + plants 11 × 50 € [MOSAICA]. Juin à "
                          "septembre, interlignes 1,60-1,80 m [Martinique]. Double rang sur 3 % "
                          "des surfaces [Agreste14]. Recourage (remplacement des manquants) "
                          "≈ 1 mois après, 11 h/ha [MOSAICA, Martinique].")
    operation(ws, 2, 56, debut=d(1, 10), fin=d(30, 11),
              commentaire="Plantation tardive : fenêtre de repli [HYPOTHÈSE]. La période de "
                          "plantation est un facteur majeur du rendement en Nord Grande-Terre "
                          "(CIRAD).")
    operation(ws, 2, 57, debut=d(15, 2, AN + 1), fin=d(30, 6, AN + 1),
              outil="Coupeuse-chargeuse ou coupe manuelle",
              commentaire="Première récolte à la campagne suivante, ~330 jours après la "
                          "plantation [Agreste14]. Une fenêtre qui chevauche deux années : "
                          "à représenter avec l'équipe MAELIA.")
    entete(ws, 2, 60, "Opérations de plantation amorties sur 7 ans dans MOSAICA (LABOUR, "
                      "PULVERISEUR, SILLONNAGE, PLANTATION_CS, RECCOURAGE_CS, plants).")

    # --- 2) irrigation : ITK pluviaux ---------------------------------------------------------
    for itk in (1, 2, 3):
        entete(ws, itk, 72, "ITK pluvial. 966 ha de canne irrigués en 2020 [RA2020] : ITK "
                            "irrigué à décrire à part (MOSAICA : pose 24 h/ha, eau en forfait "
                            "250 €/ha, sans dose ni calendrier).")

    # --- 3) fertilisation ---------------------------------------------------------------------
    for itk in (1, 3):
        operation(ws, itk, 84, debut=d(1, 3), fin=d(31, 8),
                  outil="Épandeur d'engrais minéraux", dose=72, nature="NPK 18-09-28",
                  debit=DEBIT_PULVE,
                  commentaire=ENGRAIS + " Un apport après la coupe : fenêtre [HYPOTHÈSE] "
                              "calée sur la campagne de récolte.")
        entete(ws, itk, 113, "Une seule stratégie, minérale. Engrais organiques (écumes, "
                             "vinasse, compost) : pratique non renseignée.")
    operation(ws, 2, 84, debut=d(1, 6), fin=d(30, 9), outil="Épandage au fond du sillon",
              dose=72, nature="NPK 18-09-28", debit=DEBIT_PULVE,
              commentaire=ENGRAIS + " Fumure de fond au fond du sillon à la plantation, "
                                    "2e apport possible 21 jours après [Martinique].")
    entete(ws, 2, 113, "Une seule stratégie, minérale.")

    # --- 4) P et K ----------------------------------------------------------------------------
    for itk in (1, 2, 3):
        operation(ws, itk, 121, dose="36 P2O5 + 112 K2O", nature="Dans le NPK 18-09-28",
                  commentaire="Même passage que l'azote [MOSAICA].")

    # --- 5) phytosanitaires --------------------------------------------------------------------
    for itk in (1, 2, 3):
        operation(ws, itk, 138, debut=d(15, 3), fin=d(30, 9), outil="Pulvérisateur",
                  dose=9, nature="Herbicide anti-graminées post-levée : Asulox (asulame)",
                  debit=DEBIT_PULVE,
                  commentaire="9 L/ha [MOSAICA]. Asulame retiré de l'UE fin 2012, sous "
                              "dérogations de 120 jours ensuite (2015 : 20/05-20/09) : statut "
                              "actuel à vérifier. Post-levée précoce, avant BBCH 30. Fenêtre "
                              "après la coupe [HYPOTHÈSE].")
        operation(ws, itk, 140, debut=d(15, 3), fin=d(30, 9), outil="Pulvérisateur",
                  dose=2, nature="Herbicide anti-dicotylédones : Dicopur 600 (2,4-D)",
                  debit=DEBIT_PULVE,
                  commentaire="2 L/ha, en association avec l'Asulox [MOSAICA]. Agreste14 : "
                              "2,9 traitements en 2,2 passages, IFT herbicide 2,4.")
        operation(ws, itk, 142, outil="Pulvérisateur", dose=6.4,
                  nature="Herbicide total : Round Up Flash (glyphosate)",
                  commentaire="6,4 L/ha une année sur cinq en moyenne (0,2 passage/an) "
                              "[MOSAICA] : traitement localisé ou occasionnel, sans date.")
    operation(ws, 2, 144, debut=d(1, 6), fin=d(15, 10), outil="Pulvérisateur", dose=3,
              nature="Herbicide de pré-levée : Prowl 400 (pendiméthaline)",
              commentaire="3 L/ha sur sol nu juste après plantation [MOSAICA, Martinique].")
    operation(ws, 2, 146, debut=d(1, 6), fin=d(15, 10), outil="Pulvérisateur",
              dose="0,133 kg/ha", nature="Herbicide de pré-levée : Merlin (isoxaflutole)",
              commentaire="0,133 kg/ha à la plantation [MOSAICA]. Homologation actuelle à "
                          "vérifier.")
    ws["B163"] = ("Traitements antirongeurs sur un quart des surfaces [Agreste14], absents de "
                  "MOSAICA. Déclenchement : observation de la parcelle (56 %) ou habitude "
                  "(33 %) [Agreste14].")


def remplir_territoire(ws) -> None:
    ws["B8"] = "Guadeloupe (Basse-Terre, Grande-Terre, Marie-Galante)"
    ws["B9"] = 26137
    ws["C9"] = "Surface déclarée au RPG 2017 (MOSAICA), non cultivé compris"
    ws["B10"] = "à renseigner"
    ws["C10"] = "Canne : 966 ha irrigués sur 12 417 (8 %) en 2020 [RA2020]"
    ws["B11"] = 4638
    ws["C11"] = "Exploitations du RPG 2017 (MOSAICA) ; 3 087 cultivent de la canne en 2020"
    cultures = [
        ("Canne à sucre", 12813, "Canne (repousses), jachère",
         "Vertisols 68 %, ferralsols 27 %", "à extraire (meilleur rendement Agreste sur 15 "
         "ans)", None, 73, "Rendement moyen 73 t/ha en 2014 [Agreste14], 59 t/ha en 2021 ; "
         "voir l'onglet Canne à sucre."),
        ("Prairies", 6109, None, None, None, None, None, None),
        ("Banane dessert", 1921, None, None, None, None, None, None),
        ("Maraîchage", 1087, None, None, None, None, None, None),
        ("Jachère", 621, None, None, None, None, None, None),
        ("Vergers", 311, None, None, None, None, None, None),
        ("Melon", 189, None, None, None, None, None, None),
        ("Banane plantain", 147, None, None, None, None, None, None),
        ("Igname", 145, None, None, None, None, None, None),
        ("Ananas", 133, None, None, None, None, None, None),
    ]
    for i, ligne in enumerate(cultures):
        for col, v in zip("ABCDEFGH", ligne):
            if v is not None:
                ws[f"{col}{21 + i}"] = v
    ws["A33"] = ("Surfaces : RPG 2017 ventilé par les règles GAMS (MOSAICA). Seule la canne "
                 "est décrite dans cet exercice. Non cultivé : 2 559 ha ; agrumes : 101 ha.")

    regions = [("Canne à sucre", "Basse-Terre (Nord et Sud-Ouest)", "3 362 ha ; récolte "
                "mécanisée si parcelle ≥ 0,2 ha ; rendement MOSAICA 74 t/ha"),
               ("Canne à sucre", "Sud-Est Basse-Terre", "319 ha ; replantation tous les 3 "
                "ans ; 97,5 t/ha"),
               ("Canne à sucre", "Nord Grande-Terre", "4 020 ha ; 54 t/ha"),
               ("Canne à sucre", "Centre Grande-Terre", "776 ha ; 63 t/ha"),
               ("Canne à sucre", "Est Grande-Terre", "2 151 ha ; 57 t/ha"),
               ("Canne à sucre", "Marie-Galante", "2 186 ha ; récolte semi-mécanisée ; "
                "45,6 t/ha ; sucrerie SRMG")]
    for i, (c, r, e) in enumerate(regions):
        ws[f"A{48 + i}"], ws[f"B{48 + i}"], ws[f"C{48 + i}"] = c, r, e
    ws["A54"] = None
    ws["B54"] = None
    ws["B57"] = "Champ REGION de la parcelle (7 sous-régions MOSAICA)"
    ws["A59"] = ("Commentaire : les rendements MOSAICA sont 1 à 4 fois ceux du territoire "
                 "(vigilance C.1) ; ils servent ici à comparer les régions entre elles.")

    precedents = [("Canne à sucre", "Canne", "Repousse : cas général (monoculture "
                   "pluriannuelle)"),
                  ("Canne à sucre", "Jachère", "Avant replantation : 131 à 212 parcelles "
                   "(sur ~10 000) déclarées en jachère en 2015 ou 2016 (RPG)"),
                  ("Canne à sucre", "Autre culture", "Rare")]
    for i, (c, p, e) in enumerate(precedents):
        ws[f"A{63 + i}"], ws[f"B{63 + i}"], ws[f"C{63 + i}"] = c, p, e
    sols = [("Canne à sucre", "Vertisols", "68 % des surfaces en canne (Grande-Terre, "
             "Marie-Galante)"),
            ("Canne à sucre", "Ferralsols", "27 % (Basse-Terre)"),
            ("Canne à sucre", "Andosols, nitisols, autres", "5 %")]
    for i, (c, s, e) in enumerate(sols):
        ws[f"A{75 + i}"], ws[f"B{75 + i}"], ws[f"C{75 + i}"] = c, s, e
    ws["A83"] = ("Commentaire : MOSAICA ne différencie pas l'ITK de la canne selon le sol ; "
                 "seul le sol squelettique (SOL_COURT) impose la récolte semi-mécanisée.")
    ws["A89"], ws["B89"], ws["C89"] = ("Canne à sucre", "Pas de distinction",
                                       "96 % des planteurs spécialisés [Agreste14]")
    ws["A106"], ws["B106"], ws["C106"] = ("Canne à sucre", "Inconnu",
                                          "966 ha irrigués [RA2020] ; matériel non renseigné")
    debouches = [("Canne à sucre", "Sucrerie Gardel (Le Moule)", "445 614 t broyées en 2016 "
                  "(CTCS)"),
                 ("Canne à sucre", "Sucrerie SRMG (Marie-Galante)", "73 596 t en 2016 (CTCS)"),
                 ("Canne à sucre", "Distilleries (rhum agricole)", "73 536 t en 2015, "
                  "9 distilleries agricoles (CTCS)")]
    for i, (c, t, e) in enumerate(debouches):
        ws[f"A{124 + i}"], ws[f"B{124 + i}"], ws[f"C{124 + i}"] = c, t, e
    autres = [("Canne à sucre", "Récolte mécanisée", "Parcelle mécanisable"),
              ("Canne à sucre", "Récolte semi-mécanisée", "Marie-Galante, sols courts, "
               "parcelles < 0,2 ha en Basse-Terre"),
              ("Canne à sucre", "Canne fibre", "Variante énergie de MOSAICA, sans surface "
               "observée")]
    for i, (c, a, e) in enumerate(autres):
        ws[f"A{139 + i}"], ws[f"B{139 + i}"], ws[f"C{139 + i}"] = c, a, e
    ws["B148"] = ("Règles GAMS (ENTREES.txt) : région, surface de la parcelle (0,2 ha), sol "
                  "squelettique (SOL_COURT)")
    ws["B154"] = 0.22
    ws["C154"] = "Canne : 2 752 ETP pour 12 417 ha en 2020 [RA2020]"


def remplir_prix(ws) -> None:
    ws["B13"], ws["C13"] = "MOSAICA 2017", "Prix de 2017 des tables MOSAICA (RESTIT)"
    lignes = {
        24: ("Plants de canne (€/ha)", 550, "11 × 50 € par plantation (tous les 7 ans)"),
        27: ("NPK 18-09-28 (€/kg de produit)", 0.74, "≈ 4,1 €/kg N si tout le coût est "
             "imputé à l'azote"),
        36: ("Asulox, herbicide monocot (€/L)", 10.40, None),
        37: ("Dicopur 600, herbicide dicot (€/L)", 6.07, None),
        38: ("Round Up Flash, herbicide systémique (€/L)", 13.82, None),
        42: ("Prowl 400 (€/L) ; Merlin 401 €/kg", 23.52, None),
        44: ("Eau d'irrigation (€/ha, forfait)", 250, "Forfait par hectare, pas un prix "
             "au m³"),
        51: ("Canne à sucre (€/t)", 15.79, "Nord Grande-Terre ; 10,57 à 16,41 €/t selon la "
             "région ; le guide MAELIA attend des €/ha"),
    }
    for ligne, (lib, val, com) in lignes.items():
        ws[f"A{ligne}"] = lib
        ws[f"B{ligne}"] = val
        if com:
            ws[f"E{ligne}"] = com
    ws["A72"] = "Aides canne (€/ha)"
    ws["B72"] = 2840
    ws["E72"] = ("Nord Grande-Terre, aides à la tonne converties ; 2 300 à 5 300 €/ha selon "
                 "l'ITK [MOSAICA]")


def listes_deroulantes(chemin: Path) -> dict[str, list[tuple[str, str]]]:
    """Les listes déroulantes du modèle, par onglet : (formule, plage).

    Elles sont écrites dans l'extension x14 du format, qu'openpyxl ne relit pas : sans ce
    report, la copie perd toutes ses listes (outils, profondeurs, natures de traitement).
    """
    import re
    import zipfile
    z = zipfile.ZipFile(chemin)
    classeur = z.read("xl/workbook.xml").decode("utf-8")
    liens = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    cibles = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', liens))
    cibles.update({k: v for v, k in re.findall(r'Target="([^"]+)"[^>]*Id="(rId\d+)"', liens)})
    resultat: dict[str, list[tuple[str, str]]] = {}
    for nom, rid in re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="(rId\d+)"', classeur):
        xml = z.read("xl/" + cibles[rid].lstrip("/").removeprefix("xl/")).decode("utf-8")
        resultat[nom.replace("&amp;", "&")] = [
            (f.replace("&amp;", "&").replace("&apos;", "'"), plage) for f, plage in re.findall(
                r'<x14:dataValidation type="list".*?<xm:f>(.*?)</xm:f>.*?<xm:sqref>(.*?)'
                r'</xm:sqref>', xml, re.S)]
    return resultat


def main() -> None:
    wb = openpyxl.load_workbook(SOURCE)
    modele = wb["CULTURE N (GC)"]
    canne = wb.copy_worksheet(modele)
    canne.title = "Canne à sucre"
    wb.move_sheet(canne, offset=-(len(wb.sheetnames) - 1 - wb.sheetnames.index(modele.title)))
    remplir_canne(canne)
    remplir_territoire(wb["Récapitulatif Territoire"])
    remplir_prix(wb["Prix intrants et cultures"])
    note = wb["NOTICE"]
    note["D2"] = ("Exercice rempli pour la canne à sucre (onglet « Canne à sucre ») à partir "
                  "de MOSAICA et de sources publiques ; chaque valeur porte sa source entre "
                  "crochets. Les conditions de déclenchement restent à recueillir auprès des "
                  "experts.")
    note["D2"].font = Font(bold=True, color="C00000")
    from openpyxl.worksheet.datavalidation import DataValidation
    listes = listes_deroulantes(SOURCE)
    listes["Canne à sucre"] = listes.get("CULTURE N (GC)", [])
    for nom, regles in listes.items():
        if nom not in wb.sheetnames:
            continue
        for formule, plage in regles:
            dv = DataValidation(type="list", formula1=formule, allow_blank=True,
                                showErrorMessage=False)  # outils tropicaux hors liste
            for morceau in plage.split():
                dv.add(morceau)
            wb[nom].add_data_validation(dv)
    wb.save(SORTIE)
    print(f"Écrit : {SORTIE}")


if __name__ == "__main__":
    main()
