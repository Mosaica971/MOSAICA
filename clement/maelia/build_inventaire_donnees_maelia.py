"""Inventaire de la qualité des données pour instancier MAELIA en Guadeloupe (~10 s, sans solve).

    .venv/Scripts/python clement/maelia/build_inventaire_donnees_maelia.py

Écrit `clement/maelia/inventaire_donnees_maelia_guadeloupe.xlsx`, cinq feuilles :

    Lisez-moi       l'échelle 0-3, la méthode, les réserves
    Synthèse        score moyen par famille de cultures et par thème, verrous hors données
    Cultures        une ligne par culture fine MOSAICA, une colonne par paramètre MAELIA
    Paramètres      le dictionnaire des colonnes de « Cultures » : sens, source, règle de note
    Autres données  climat, sols, parcellaire, exploitations, hydrologie… avec liens

Deux sortes de notes. Celles qui se lisent dans les tables de MOSAICA (rendement, opérations,
doses, prix…) sont calculées ici, culture par culture, à partir du `Dataset`. Celles qui
portent sur une donnée absente (phénologie, Kc, besoins en azote…) disent seulement si la
littérature la donne facilement pour la plante : c'est une appréciation, écrite dans
`PLANTES_DOCUMENTEES`, à faire valider par les agronomes. Le classeur est fait pour être
corrigé à la main ; relancer le script écrase ces corrections (changer `--out`).

Reprend la lecture opération par opération de
`case_studies/guadeloupe/reporting/maelia_crops.py` (docs/maelia/crop-parameters.md).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import xlsxwriter  # noqa: E402
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell  # noqa: E402

OUT = Path(__file__).resolve().parent / "inventaire_donnees_maelia_guadeloupe.xlsx"
SO = "–"  # sans objet : le paramètre ne s'applique pas à cette culture

ECHELLE = (
    (0, "Absente et difficile à obtenir",
     "Ni dans MOSAICA ni dans un référentiel : expérimentation, calibration ou enquête lourde."),
    (1, "Absente mais accessible",
     "Pas dans MOSAICA, mais publiée ou récupérable vite : littérature, base publique, dire d'expert."),
    (2, "Disponible, à retravailler",
     "Une valeur existe : proxy, valeur par famille, autre unité ou définition, niveau discutable."),
    (3, "Disponible et utilisable",
     "Dans les tables de MOSAICA, à la bonne maille : une simple mise en forme suffit."),
)

# --- cultures ---------------------------------------------------------------------------------

FAMILLES = {
    "CS": "Canne à sucre et canne fibre", "BA": "Banane dessert", "BC": "Plantain",
    "PN": "Prairies", "MA": "Maraîchage (dont tomate)", "ME": "Melon", "IG": "Igname",
    "AN": "Ananas", "AG": "Agrumes", "VE": "Vergers", "JA": "Jachère",
}
_REGIONS = {"NBT": "Nord Basse-Terre", "SBT": "Sud Basse-Terre", "BT": "Basse-Terre",
            "NGT": "Nord Grande-Terre", "CGT": "Centre Grande-Terre",
            "EGT": "Est Grande-Terre", "MG": "Marie-Galante"}
_CONDUITE = {"NISM": "pluvial, récolte semi-mécanisée", "NIM": "pluvial, récolte mécanisée",
             "IM": "irrigué, récolte mécanisée"}
_PAILLAGE = {"BAG": "bagasse", "BRF": "BRF", "PAI": "paille"}
_LIBELLES = {
    "AG": "Agrumes", "AN_NU": "Ananas sans paillage plastique",
    "AN_PA": "Ananas avec paillage plastique", "BA_INT": "Banane : intensif de plaine",
    "BA_IRR": "Banane : irrigué", "BA_PER": "Banane : extensif d'altitude",
    "BA_SINT": "Banane : intensif d'altitude", "BC_BT": "Plantain, Basse-Terre",
    "BC_GTMG": "Plantain, Grande-Terre et Marie-Galante", "IG_PLA": "Igname à plat",
    "IG_TUT": "Igname tuteurée", "JA": "Jachère",
    "MA_TO_CHOU_JA": "Maraîchage plein champ (rotation tomate/chou/jachère)",
    "MA_TO_CO_JA": "Maraîchage plein champ (rotation TO/CO/JA)",
    "MA_PLBIO": "Maraîchage bio plurispécifique", "MA_MOBIO": "Maraîchage bio monospécifique",
    "MA_ROTA": "Maraîchage en rotation", "TH": "Tomate", "ME": "Melon",
    "PN_PIQ": "Prairie naturelle, élevage au piquet",
    "PN_TOUR": "Prairie naturelle, pâturage tournant",
    "VE_BTGT": "Vergers, Basse-Terre et Grande-Terre", "VE_PLUIE": "Vergers, zones très pluvieuses",
}


def libelle(code: str) -> str:
    if code in _LIBELLES:
        return _LIBELLES[code]
    parts = code.split("_")
    if parts[0] in ("CS", "CF") and len(parts) == 3:
        nom = "Canne à sucre" if parts[0] == "CS" else "Canne fibre"
        region = _REGIONS.get(parts[1], parts[1])
        if code.startswith("CS_SBT"):
            region = "Sud-Est Basse-Terre"
        return f"{nom} : {region}, {_CONDUITE.get(parts[2], parts[2])}"
    if parts[0] == "MA" and len(parts) == 4 and parts[1] in _PAILLAGE:
        eau = "irrigué" if parts[3] == "I" else "pluvial"
        return f"Maraîchage plein champ (paillage {_PAILLAGE[parts[1]]}, {parts[2]}, {eau})"
    return code


def plante(code: str) -> str:
    """La plante derrière le code : c'est elle que la littérature décrit, pas la variante."""
    for prefix, name in (("CF_", "canne fibre"), ("CS_", "canne"), ("BA_", "banane"),
                         ("BC_", "plantain"), ("AN_", "ananas"), ("IG_", "igname"),
                         ("VE_", "vergers"), ("PN_", "prairie"), ("MA_", "maraîchage")):
        if code.startswith(prefix):
            return name
    return {"AG": "agrumes", "JA": "jachère", "TH": "tomate", "ME": "melon"}[code]


# Pour une donnée absente de MOSAICA : les plantes pour lesquelles une référence publiée la
# donne (note 1) ; les autres sont à 0. APPRÉCIATION à valider -- les mélanges (maraîchage,
# vergers) n'ont pas de plante unique à qui emprunter une valeur.
_MONO = {"canne", "canne fibre", "banane", "plantain", "ananas", "igname", "tomate", "melon"}
PLANTES_DOCUMENTEES = {
    "rendement_potentiel": _MONO | {"agrumes"},
    "phenologie": _MONO,
    "ky_fao33": {"canne", "canne fibre", "banane", "plantain", "agrumes", "tomate", "melon"},
    "besoin_n": _MONO | {"agrumes"},
    "cn_residus": _MONO | {"agrumes"},
    "calendrier": {"canne", "canne fibre", "igname", "melon", "tomate", "ananas", "agrumes",
                   "vergers"},
    "fractionnement": _MONO | {"agrumes"},
}


@dataclass
class Culture:
    """Ce que les tables de MOSAICA disent d'une culture fine, pour la noter."""

    code: str
    famille: str
    plante: str
    surface_2017_ha: float
    rendement: float
    variance: float
    proteines: float
    long_rac: float
    biom_aer: float
    rac: float
    carb: float
    prof_sillons: float
    types_ot: set
    n_ot_types: int
    n_ot: int
    part_heures_hors_types: float
    besoin_eau: float
    prix: float
    primes: float
    charges: float
    duree_plantation: float
    duree_cycle_mois: float
    passages_par_an: dict  # opérations par an, cycles de plus de 12 mois ramenés à l'année

    @property
    def irrigation(self) -> bool:
        return "irrigation" in self.types_ot


def _doc(theme: str, sinon: int = 0) -> Callable[[Culture], int]:
    return lambda c: 1 if c.plante in PLANTES_DOCUMENTEES[theme] else sinon


def _const(note) -> Callable[[Culture], object]:
    return lambda c: note


def _si(type_ot: str, note: Callable[[Culture], object]) -> Callable[[Culture], object]:
    return lambda c: note(c) if type_ot in c.types_ot else SO


def _irrigation_dose(c: Culture):
    if c.irrigation and c.besoin_eau > 0:
        return 2
    return 1 if c.irrigation or c.besoin_eau > 0 else SO


def _ot_presentes(c: Culture) -> int:
    if c.n_ot_types == c.n_ot:
        return 3
    if c.n_ot_types >= 0.5 * c.n_ot:
        return 2
    return 1 if c.n_ot_types else 0


def _temps(c: Culture) -> int:
    return 3 if c.part_heures_hors_types < 0.10 else 2 if c.part_heures_hors_types < 0.50 else 1


@dataclass
class Parametre:
    bloc: str
    nom: str
    sens: str
    unite: str
    necessite: str
    mosaica: str
    regle: str
    pistes: str
    lien: str
    note: Callable[[Culture], object]
    # À quelles cultures il s'applique : "aqyield" (ni prairie ni jachère), "prairie",
    # "itk" (toutes sauf la jachère), "toutes".
    portee: str = "aqyield"


FAO56 = "https://www.fao.org/4/x0490e/x0490e00.htm"
FAO56_KC = "https://www.fao.org/4/x0490e/x0490e0b.htm"
FAO66 = "https://www.fao.org/4/i2800e/i2800e.pdf"
STICS = "https://stics.inrae.fr/"
DOC_ENTREES = "https://maelia.pages-forge.inrae.fr/documentation/04-donnees_entree.html"
APPLI_ITK = "https://analytics.huma-num.fr/Renaud.Misslin/maelia_itk/"
AGRESTE = "https://daaf.guadeloupe.agriculture.gouv.fr/"
CHAMBRE = "https://guadeloupe.chambres-agriculture.fr/"
MODELES_TROPICAUX = ("Modèles publiés à transposer : canne MOSICAS (CIRAD) et STICS "
                     "(paramétrage R570, La Réunion) ; banane SIMBA (CIRAD, Guadeloupe) et "
                     "STICS-banane (Brisson, Ozier-Lafontaine et Dorel, 1998) ; ananas SIMPIÑA "
                     "(CIRAD, Queen Victoria, La Réunion) ; igname : CropSyst adapté (Marcos et "
                     "al., Guadeloupe), dont le développement dépend de la photopériode, "
                     "qu'AqYield ne représente pas ; tomate STICS. Melon : pas de modèle, mais des "
                     "sommes de températures publiées (base 10 °C, ou 11 °C plafonnée à "
                     "25 °C).")

ECO_NECESSITE = "pour les sorties économiques (MAELIA tourne sans)"
B_EAU = "Espèce — AqYield : rendement, phénologie, eau (especesCultivees.csv)"
B_NC = "Espèce — AqYieldNC : azote et carbone (especesCultivees.csv)"
B_ITK = "ITK (reglesDeDecisions.csv)"
B_FERTI = "Fertilisation (reglesDeDecisions_fertilisation.csv)"
B_ECO = "Économie (marcheAgricole/)"
BLOCS = (B_EAU, B_NC, B_ITK, B_FERTI, B_ECO)
BLOCS_COURTS = {B_EAU: "Espèce : eau, phéno", B_NC: "Espèce : N et C", B_ITK: "ITK",
                B_FERTI: "Fertilisation", B_ECO: "Économie"}

PARAMETRES: tuple[Parametre, ...] = (
    # --- espèce, AqYield -----------------------------------------------------------------
    Parametre(B_EAU, "RENDEMENT_OPTIMAL", "Rendement potentiel local, que le modèle réduit "
              "selon les stress hydrique et azoté. À adapter au terrain (obligatoire).",
              "t/ha", "obligatoire",
              "Aucune : Rdt_Cult est un rendement moyen atteint, pas un potentiel.",
              "1 si des essais ou références donnent un potentiel pour la plante, 0 sinon "
              "(mélanges, prairie).",
              "Essais INRAE/CIRAD, CTCS (canne), IT2 (banane, diversification), Agreste "
              "(meilleures années). La grille d'enquête ITK le demande par culture et par "
              "type de sol. En 1.4.31 : parametres/rendements_optimaux.csv.", AGRESTE,
              _doc("rendement_potentiel")),
    Parametre(B_EAU, "RENDEMENT_MOYEN", "Rendement moyen, sert à la validation.", "t/ha",
              "optionnel", "Rdt_Cult_CF_<scénario>.",
              "2 : présent, mais 1 à 4 fois le rendement du territoire (vigilance C.1).",
              "Agreste (statistique agricole annuelle), CTCS, LPG.", AGRESTE,
              lambda c: 2 if c.rendement > 0 else 1),
    Parametre(B_EAU, "RENDEMENT_MIN", "Rendement minimum, sert à la validation.", "t/ha",
              "optionnel", "Var_Rdt_Cult (une variance, pas un minimum).",
              "2 si une variance existe (minimum à en déduire), 1 sinon.",
              "Séries Agreste par culture.", AGRESTE,
              lambda c: 2 if c.variance > 0 else 1),
    Parametre(B_EAU, "Tbase", "Température de base des degrés-jours (un entier).", "°C",
              "obligatoire",
              "Aucune.", "1 si un modèle de culture publié paramètre la plante, 0 sinon.",
              MODELES_TROPICAUX, STICS, _doc("phenologie")),
    Parametre(B_EAU, "Tmax", "Température maximale prise en compte dans les degrés-jours.",
              "°C", "obligatoire", "Aucune.", "Comme Tbase.", MODELES_TROPICAUX, STICS,
              _doc("phenologie")),
    Parametre(B_EAU, "DEGRES_J_LevTbase", "Somme de degrés-jours à la levée.", "°C.j",
              "obligatoire", "Aucune (Duree_Cycle_Cult : 12 mois partout, 18 pour l'ananas).",
              "Comme Tbase. Pour une plantation (canne, banane) : reprise après plantation "
              "ou coupe, à définir avec l'équipe MAELIA.", MODELES_TROPICAUX, STICS,
              _doc("phenologie")),
    Parametre(B_EAU, "DEGRES_J_Flor", "Somme de degrés-jours à la floraison (maximum du Kc).",
              "°C.j", "obligatoire", "Aucune.",
              "Comme Tbase. Sans objet agronomique strict pour la canne (récoltée avant "
              "floraison) : c'est la date du Kc maximal qu'il faut.", MODELES_TROPICAUX, STICS,
              _doc("phenologie")),
    Parametre(B_EAU, "DEGRES_J_matPhyTbase", "Somme de degrés-jours à la maturité (Kc nul). "
              "La récolte n'est déclenchée qu'une fois cette somme atteinte.",
              "°C.j", "obligatoire", "Aucune.",
              "Comme Tbase. Fixe aussi la date de récolte : à caler sur la campagne réelle.",
              MODELES_TROPICAUX, STICS,
              _doc("phenologie")),
    Parametre(B_EAU, "FREIN", "Frein hivernal au développement (1 = pas de frein).", "0-1",
              "obligatoire", "Sans hiver, la valeur est 1.",
              "3 : connue sans mesure (à confirmer : les supports parlent aussi de frein "
              "photopériodique).", "—", "", _const(3)),
    Parametre(B_EAU, "KMAX", "Coefficient cultural maximal.", "—", "obligatoire",
              "Aucune. Attention : KCROP de Data_Cult est le coefficient de minéralisation "
              "de MORGWANIK, pas un Kc.",
              "1 : les tables FAO-56 donnent un Kc pour la plante ou une voisine.",
              "FAO-56, tableau 12 (canne, banane, ananas, agrumes, tomate, melon ; igname "
              "par analogie avec les tubercules tropicaux).", FAO56_KC, _const(1)),
    Parametre(B_EAU, "CVIG", "Vigueur : pente de montée du Kc.", "—", "obligatoire",
              "Aucune.", "0 : propre à AqYield, se cale sur une courbe de Kc ou de LAI.",
              "Calibration avec le référent MAELIA ; LAI par télédétection.", DOC_ENTREES,
              _const(0)),
    Parametre(B_EAU, "CSTO", "Effet de la fermeture stomatique sur le stress hydrique.", "—",
              "obligatoire", "Aucune.",
              "1 : vaut 1 pour toutes les espèces des jeux d'exemple MAELIA.",
              "Valeur par défaut des espèces existantes.", DOC_ENTREES, _const(1)),
    Parametre(B_EAU, "coeff_Fonction_Prod", "Forme de la fonction de production : effet du "
              "stress hydrique sur le rendement.", "—", "obligatoire", "Aucune.",
              "1 si un coefficient de réponse à l'eau (Ky) est publié pour la plante, 0 "
              "sinon. Ky n'est pas le paramètre d'AqYield : point de départ seulement.",
              "FAO-33 (Doorenbos et Kassam 1979), table reprise dans FAO-66 : canne 1,2, "
              "banane 1,2-1,35, tomate 1,05, pastèque 1,1 (pour le melon). Agrumes 1,1-1,3 "
              "d'après une source secondaire. Pas d'ananas ni d'igname.", FAO66,
              _doc("ky_fao33")),
    Parametre(B_EAU, "CRACINE", "Vitesse de croissance racinaire.", "°C.j par mm de RU",
              "obligatoire", "Aucune (LONG_RAC est une profondeur, pas une vitesse).",
              "0 : propre à AqYield.", "Calibration avec le référent MAELIA.", DOC_ENTREES,
              _const(0)),
    Parametre(B_EAU, "PROF_MAX_RACINE", "Profondeur maximale d'enracinement.", "cm",
              "obligatoire", "Data_Cult, ligne LONG_RAC (une valeur par plante).",
              "2 : présente, commune à toutes les variantes d'une plante.",
              "FAO-56, tableau 22.", FAO56, lambda c: 2 if c.long_rac > 0 else 1),
    Parametre(B_EAU, "ZonesClimatiques", "Zones climatiques où l'espèce peut pousser.", "—",
              "optionnel (choix d'assolement par MAELIA seulement)",
              "Bornes d'éligibilité ALTI_MIN/MAX et PLUVIO_MIN/MAX de Data_Cult.",
              "2 : à traduire une fois les zones climatiques de la Guadeloupe définies.",
              "—", "", _const(2)),
    Parametre(B_EAU, "especesHerbSim.csv", "Prairies : la trentaine de paramètres HerbSim "
              "(efficience du rayonnement, durée de vie des feuilles, digestibilité, "
              "dilution de l'azote…).", "—", "obligatoire pour les prairies",
              "Aucune. HerbSim ne connaît que 7 espèces tempérées et 5 types fonctionnels "
              "de graminées (A, B, b, C, D).",
              "0 : aucune graminée tropicale (pangola, herbe de Guinée…) n'est paramétrée.",
              "INRAE Antilles-Guyane (URZ/ASSET, fourrages tropicaux) ; équipe MAELIA.",
              DOC_ENTREES, _const(0), portee="prairie"),
    # --- espèce, AqYieldNC ----------------------------------------------------------------
    Parametre(B_NC, "BESOIN_N", "Besoin en azote par unité produite (ou BESOIN_Ntot, besoin "
              "total).", "kg N/t (ou kg N/ha)", "AqYieldNC",
              "Aucune : l'azote des engrais est un apport, pas un besoin.",
              "1 si les exportations d'azote de la plante sont publiées, 0 sinon.",
              "Canne : 0,8 à 1,4 kg N/t de tiges (1 kg N/t au Brésil) ; banane : 1,3 à 1,9 "
              "kg N/t de fruits (revue Fruits, CIRAD) ; igname (D. alata) : ~2,9 kg N/t de "
              "tubercules frais, sur deux études seulement ; ananas : exportations faibles, "
              "publiées par fruit.", STICS,
              _doc("besoin_n")),
    Parametre(B_NC, "Type_Nacq + courbe", "Type d'acquisition de l'azote et forme de la "
              "demande (DEBUT_, FREIN_, PRE_FLO_, PRE_MAT_BESOIN_N ; coef_500Mat pour le type "
              "500Mat).", "—", "AqYieldNC",
              "Aucune.", "0 : métamodèle propre à AqYield-N, à choisir avec le référent.",
              "Équipe MAELIA ; note AqYieldNC (Data INRAE).", DOC_ENTREES, _const(0)),
    Parametre(B_NC, "adil, bdil, adilmax", "Courbe de dilution critique (et maximale) de "
              "l'azote, comme dans STICS.", "—", "AqYieldNC", "Aucune.",
              "1 : des courbes génériques sont publiées pour les plantes en C3 et en C4 (la "
              "canne est en C4), à défaut d'une courbe propre à l'espèce.",
              "Greenwood et al. (1990) : C3 5,7 W^-0,5, C4 4,1 W^-0,5 (% N) ; courbe propre à "
              "la canne : Oliveira et al. (2013). adilmax apparaît en 1.4.31.", STICS,
              _const(1)),
    Parametre(B_NC, "N_grain", "Teneur en azote du produit récolté.", "% MS", "AqYieldNC",
              "Nutri_Cult, ligne Prot (protéines / 6,25) pour les cultures alimentaires.",
              "2 si les protéines du produit sont dans Nutri_Cult, 1 sinon (tables de "
              "composition).", "Table Ciqual (Anses).", "https://ciqual.anses.fr/",
              lambda c: 2 if c.proteines > 0 else 1),
    Parametre(B_NC, "Tms", "Teneur en matière sèche du produit récolté.", "0-1", "AqYieldNC",
              "Aucune.", "1 : dans les tables de composition.",
              "Table Ciqual (Anses) : igname crue 69,6 g d'eau pour 100 g, soit Tms ≈ 0,30, "
              "et 1,3 à 1,5 g de protéines.",
              "https://ciqual.anses.fr/", _const(1)),
    Parametre(B_NC, "HI", "Indice de récolte : produit / biomasse aérienne totale.", "0-1",
              "AqYieldNC", "À déduire de Rdt_Cult, Tms et BIOM_AER (résidus aériens, t/ha).",
              "2 si BIOM_AER est renseignée (≠ 6, la valeur par défaut), 1 sinon.",
              "MORGWANIK (résidus) ; littérature par plante.", "",
              lambda c: 2 if c.biom_aer != 6 and c.rendement > 0 else 1),
    Parametre(B_NC, "SR_ratio", "Rapport parties aériennes / racines après récolte (ou "
              "RootC_fixed).", "—", "AqYieldNC",
              "Data_Cult, ligne RAC (biomasse racinaire / rendement) : définition voisine.",
              "2 : proxy à convertir ; 1 si RAC vaut 0,1, la valeur mise quand elle est "
              "inconnue.", "MORGWANIK ; littérature par plante.", "",
              lambda c: 2 if c.rac > 0 and c.rac != 0.1 else 1),
    Parametre(B_NC, "beta", "Répartition des racines en profondeur (Gale et Grigal 1987).",
              "—", "AqYieldNC", "Aucune.", "1 : valeurs tabulées par type de plante.",
              "Gale et Grigal (1987) ; valeurs par biome dans Jackson et al. (1996) ; "
              "espèces MAELIA voisines.", DOC_ENTREES,
              _const(1)),
    Parametre(B_NC, "C_aer, C_rac", "Teneur en carbone des résidus aériens et racinaires.",
              "0-1", "AqYieldNC", "Data_Cult, ligne CARB (0,4 par défaut).",
              "2 : une valeur, commune aux deux compartiments ; 1 si CARB vaut 0,4, la valeur "
              "mise quand elle est inconnue.", "MORGWANIK.", "",
              lambda c: 2 if c.carb > 0 and c.carb != 0.4 else 1),
    Parametre(B_NC, "CN_ratio", "Rapport C/N des résidus de culture.", "—", "AqYieldNC",
              "Aucune (HRES est un coefficient d'humification).",
              "1 si la plante est une espèce unique, 0 pour les mélanges.",
              "Paramètres résidus de STICS ; INRAE Antilles-Guyane (ASTRO).", STICS,
              _doc("cn_residus")),
    Parametre(B_NC, "Pse", "Part des résidus aériens laissée au sol quand ils sont exportés.",
              "0-1", "AqYieldNC", "Aucune (le scénario RESTIT/SMART porte la pratique).",
              "1 : à dire d'expert.", "Chambre d'agriculture, instituts techniques.", CHAMBRE,
              _const(1)),
    Parametre(B_NC, "ABSCISSION", "Chute des parties aériennes avant récolte.", "0-1",
              "AqYieldNC", "Aucune.", "1 : 0 par défaut, à valider par plante.",
              "Valeurs des espèces MAELIA voisines.", DOC_ENTREES, _const(1)),
    Parametre(B_NC, "isLEG", "Légumineuse fixatrice.", "vrai/faux", "AqYieldNC",
              "Agronomie : aucune des cultures n'est une légumineuse.", "3.", "—", "",
              _const(3)),
    Parametre(B_NC, "especeRepousse", "Couvert qui simule la repousse après récolte.", "—",
              "optionnel", "Aucune.",
              "0 pour la canne : c'est peut-être le mécanisme des repousses, à confirmer. "
              "Sans objet ailleurs.", "Équipe MAELIA (question n° 1 de la formation).",
              DOC_ENTREES, lambda c: 0 if c.plante in ("canne", "canne fibre") else SO),
    # --- ITK -------------------------------------------------------------------------------
    Parametre(B_ITK, "ID_PREC", "Précédent cultural (critère de spatialisation).", "—",
              "obligatoire (« * » accepté)",
              "Data_RPG_Gwad_2017 : groupe RPG déclaré de 2012 à 2017, par parcelle.",
              "2 : connu au niveau des 12 groupes RPG, pas de la culture fine. La jachère "
              "(« gel ») doit figurer parmi les précédents des ITK qui la suivent.",
              "RPG (IGN/ASP).", "https://geoservices.ign.fr/rpg", _const(2), portee="toutes"),
    Parametre(B_ITK, "ZONE_PEDO, TYPE_EXPL, CLIMAT, IDS_SDCS", "Sol, type d'exploitation, "
              "zone climatique et séquence de référence (IDS_SDCS, face à ID_SDC de "
              "parcelles.shp) auxquels l'ITK s'applique ; en 1.4.31 aussi un critère libre, "
              "CRIT_SPAT_ADHOC.", "—", "obligatoire (« * » accepté)",
              "Règles GAMS qui attribuent l'ITK fin à une parcelle (île, région, pente, "
              "taille d'exploitation, irrigation, sol) : ENTREES.txt:299-457.",
              "2 : les règles existent, à réécrire en critères MAELIA.", "—", "", _const(2),
              portee="itk"),
    Parametre(B_ITK, "MATERIEL", "Matériel d'irrigation.", "—", "si irrigué",
              "Variantes irriguées et drapeau IRRIG_PARC ; le type de matériel est inconnu.",
              "1 pour les ITK irrigués (dire d'expert), sans objet sinon.",
              "Chambre d'agriculture, Conseil départemental (réseau d'irrigation).", CHAMBRE,
              lambda c: 1 if c.irrigation else SO, portee="itk"),
    Parametre(B_ITK, "IS_<OT>", "Quelles opérations techniques existent : TRAVAIL_SOL "
              "(ex-PREPA et REPRISE), SEMIS, DESHERBAGE_MECA (ex-BINAGE), FERTI, PHYTO, "
              "IRRIGATION, RECOLTE ; FAUCHE et PATURE pour les prairies.", "O/N",
              "obligatoire", "Matrice_OTK_Cult_<scénario>, opérations rangées dans les types "
              "MAELIA.",
              "3 si toutes les opérations ont un type MAELIA, 2 si au moins la moitié, "
              "1 si quelques-unes, 0 si aucune. Voir aussi la colonne Dépassements.", "—", "",
              _ot_presentes, portee="itk"),
    Parametre(B_ITK, "<OT>_TEMPS", "Débit de chantier de chaque opération (l'application "
              "ITK le demande en h/ha, le fichier le porte en ha/h).", "ha/h",
              "obligatoire", "Data_OTK : MO_EXPL × DOSE, en h/ha.",
              "Selon la part des heures portée par des opérations sans type MAELIA "
              "(effeuillage, tuteurage, emballage, soins aux animaux…) : 3 sous 10 %, "
              "2 sous 50 %, 1 au-delà.", "—", "", _temps, portee="itk"),
    Parametre(B_ITK, "<OT>_DEBUT / _FIN", "Fenêtres calendaires de chaque opération "
              "(1 à 3 sous-périodes, jours juliens). La récolte attend en plus la maturité.",
              "jour", "obligatoire", "Aucune.",
              "1 si la culture a une campagne datée connue des fiches techniques, 0 si "
              "elle est conduite en continu (banane, plantain, maraîchage, prairie).",
              "Fiches techniques Chambre d'agriculture, CTCS, IT2 ; grille d'entretien ITK "
              "de MAELIA.", CHAMBRE, _doc("calendrier"), portee="itk"),
    Parametre(B_ITK, "Seuils de déclenchement", "Humidité du sol, cumul de pluie, P-ETP, "
              "température, stade (ECHV) qui autorisent l'opération.", "divers",
              "optionnel (NA accepté)", "Aucune.",
              "0 : enquête auprès d'experts. Un ITK tourne sans (NA), mais il est alors "
              "aveugle à la météo, ce qui retire l'intérêt du pas de temps journalier.",
              "Grille d'entretien ITK de MAELIA ; application ITK.", APPLI_ITK, _const(0),
              portee="itk"),
    Parametre(B_ITK, "TRAVAIL_SOL_EFFET_RUs", "Profondeur de travail du sol (ex-PREPA et "
              "REPRISE).", "cm",
              "si travail du sol", "Data_Cult, ligne PROF_SILLONS (profondeur des sillons).",
              "2 si PROF_SILLONS est renseignée, 1 sinon ; sans objet sans travail du sol.",
              "Fiches techniques.", CHAMBRE,
              _si("tillage", lambda c: 2 if c.prof_sillons > 0 else 1), portee="itk"),
    Parametre(B_ITK, "IRRIGATION_DOSE, _TD", "Dose par tour d'eau et délai de retour.",
              "mm, jours", "si irrigué",
              "Opérations d'irrigation de la matrice et BESOIN_EAU_01..12 (besoin brut, "
              "plat sur l'année : vigilance C.4).",
              "2 si opérations et besoin, 1 si l'un des deux seulement, sans objet si "
              "ni l'un ni l'autre.", "FAO-56 ; pratiques locales.", FAO56, _irrigation_dose,
              portee="itk"),
    Parametre(B_ITK, "IRRIGATION fenêtre, stades, seuils", "Période d'irrigation, stades de "
              "début et de fin, pluie qui annule ou reporte un tour.", "jour, mm",
              "si irrigué", "Aucune.", "0 pour les cultures irriguées, sans objet sinon.",
              "Experts ; application ITK.", APPLI_ITK,
              lambda c: 0 if c.irrigation or c.besoin_eau > 0 else SO, portee="itk"),
    Parametre(B_ITK, "PHYTO produits, doses", "Traitements phytosanitaires.", "L/ha",
              "si traité", "Matrice et Data_OTK (IFT, propriétés PPDB).",
              "3 si l'ITK compte des traitements, sans objet sinon.", "—", "",
              _si("crop_protection", _const(3)), portee="itk"),
    Parametre(B_ITK, "FAUCHE, PATURE", "Prairies : FAUCHE (hauteur de coupe, hauteur ou "
              "biomasse minimale) et PATURE (dates, temps de repos, part d'herbe accessible, "
              "hauteurs d'herbe à l'entrée et à la sortie), TYPE_GESTION_PRAIRIE.",
              "cm, t/ha, jours", "pour les prairies",
              "Opérations de déplacement et de soins des ITK PN ; ni hauteur d'herbe ni "
              "chargement.",
              "0. Le pâturage demande en plus les lots d'animaux (feuille Autres données).",
              "INRAE Antilles-Guyane (élevage), Chambre d'agriculture, EDE.", CHAMBRE, _const(0),
              portee="prairie"),
    # --- fertilisation ---------------------------------------------------------------------
    Parametre(B_FERTI, "FERTIALT produit, dose N-P-K", "Produits et doses par apport "
              "(4 apports au plus par stratégie).",
              "kg d'élément/ha (minéral), t brutes/ha (organique)", "AqYieldNC",
              "Lignes engrais de la matrice ; N par la colonne AZOTE, P et K par la formule "
              "dans le nom du produit.",
              "3 si l'ITK fertilise, sans objet sinon.", "—", "",
              _si("fertilisation", _const(3)), portee="itk"),
    Parametre(B_FERTI, "FERTIALT calendrier, alternatives", "Dates des apports, "
              "fractionnement, stratégies de repli selon le stock d'engrais.", "jour",
              "AqYieldNC", "Aucune : la matrice donne un nombre d'apports, pas leur date.",
              "1 si le fractionnement est décrit dans les fiches techniques de la plante, "
              "0 sinon ; sans objet sans fertilisation.",
              "Fiches techniques Chambre d'agriculture, CTCS, IT2.", CHAMBRE,
              _si("fertilisation", _doc("fractionnement")), portee="itk"),
    # --- économie --------------------------------------------------------------------------
    Parametre(B_ECO, "prixVentes.csv", "Prix de vente par espèce et par an.",
              "€/t (le guide imprime €/ha : à confirmer)", ECO_NECESSITE,
              "Prix_Cult_CF_<scénario>.",
              "2 si un prix existe : 2017 seulement, les colonnes 2018-2022 en sont des "
              "copies. 1 sinon (canne fibre : prix nul).",
              "Agreste / DAAF (conjoncture), ODEADOM.", "https://www.odeadom.fr/",
              lambda c: 2 if c.prix > 0 else 1, portee="itk"),
    Parametre(B_ECO, "primes.csv", "Aides couplées par espèce et par département.", "€/ha",
              ECO_NECESSITE,
              "POSEI à l'hectare et à la tonne, aides canne (industrie, replantation, "
              "transport, garantie de prix), MAE.",
              "2 : les aides à la tonne sont à convertir en €/ha avec un rendement.",
              "Programme POSEI France, ODEADOM, DAAF.", "https://www.odeadom.fr/", _const(2),
              portee="toutes"),
    Parametre(B_ECO, "Prix des intrants", "Prix unitaires des semences et plants, engrais, "
              "traitements, carburant et eau : ce que la grille d'enquête demande pour le "
              "module économique, qui calcule à l'opération technique.", "€/kg, €/L, €/m³",
              "pour les sorties économiques (format du fichier à confirmer)",
              "Data_OTK : PRIX_UNIT et DOSE de chaque intrant. Pas de prix du carburant.",
              "2 si les intrants de l'ITK sont chiffrés : le carburant manque et les produits "
              "sont à rapprocher du référentiel MAELIA.", "—", "",
              lambda c: 2 if c.charges > 0 else 1, portee="toutes"),
    Parametre(B_ECO, "chargesOp.csv", "Charges opérationnelles par ITK : coût cumulé des "
              "intrants, hors irrigation.", "€/ha", ECO_NECESSITE,
              "Matrice × PRIX_UNIT, plus coûts de récolte et de transport.",
              "2 si un coût est calculable : celui de MOSAICA mêle intrants, prestations, "
              "récolte, transport et forfait d'irrigation, que MAELIA compte séparément.",
              "—", "", lambda c: 2 if c.charges > 0 else 1, portee="toutes"),
    Parametre(B_ECO, "chargesDePassage.csv", "Charges de mécanisation par ITK (pour la "
              "marge semi-nette).", "€/ha", "pour la marge semi-nette",
              "Aucune : AMORTI ne fait que signaler les opérations amorties.",
              "0 : pas de barème de mécanisation pour la Guadeloupe.",
              "Chambre d'agriculture, CUMA, prestataires de récolte (SICA canne).", CHAMBRE,
              _const(0), portee="toutes"),
)


def noter(parametre: Parametre, culture: Culture):
    hors = {"aqyield": ("prairie", "jachère"), "itk": ("jachère",), "toutes": (),
            "prairie": None}[parametre.portee]
    if hors is None:
        return parametre.note(culture) if culture.plante == "prairie" else SO
    if culture.plante in hors:
        return SO
    return parametre.note(culture)


# --- autres données -----------------------------------------------------------------------------

P1, P2, P3 = "1 — bloquant", "2 — azote, robustesse", "3 — modules optionnels"
METEO_FRANCE = "https://www.data.gouv.fr/datasets/donnees-climatologiques-de-base-quotidiennes"
RRP = "https://www.gissol.fr/donnees/liens-vers-les-referentiels-regionaux-pedologiques-5634"
SOLS_PISTES = ("Carte Colmet-Daage (ORSTOM) et ses notices ; synthèses et analyses INRAE "
               "Antilles-Guyane (UR ASTRO) ; RMQS du GIS Sol (10 sites en Guadeloupe en 2006, "
               "42 points dans la campagne en cours : pH, carbone, azote, granulométrie, pas "
               "d'hydrodynamique) ; SoilGrids en repli")

# (thème, donnée, fichier et champs MAELIA, nécessité, priorité, ce qu'on a, note, sources,
#  lien, accès, action)
AUTRES: tuple[tuple, ...] = (
    ("Climat", "Pluie journalière", "meteo/observee/<année>.csv : RRmm", "obligatoire", P1,
     "Normale annuelle 1981-2010 seulement (raster Météo-France krigé à 10 m, "
     "data/gis/05_Pluviométrie) et une classe par parcelle. Aucune série journalière.", 1,
     "Météo-France, données climatologiques de base quotidiennes (toutes les stations, "
     "outre-mer compris, par département) ; stations INRAE via CLIMATIK (Le Moule – Gardel "
     "y figure ; Duclos et Godet à vérifier).", METEO_FRANCE,
     "Météo-France : Licence Ouverte 2.0. CLIMATIK : identifiants INRAE (intranet)",
     "Télécharger les postes du 971 ; viser 20 ans, comme le demande la formation. Liste "
     "des paramètres par poste à lire dans le descriptif des champs du jeu."),
    ("Climat", "Températures minimale et maximale journalières",
     "meteo/observee/<année>.csv : Tmin, Tmax", "obligatoire", P1, "Rien.", 1,
     "Mêmes sources que la pluie ; moins de postes mesurent la température.", METEO_FRANCE,
     "Licence Ouverte 2.0", "Vérifier la couverture en altitude (Basse-Terre)."),
    ("Climat", "Rayonnement global journalier",
     "meteo/observee/<année>.csv : RGI (MJ/m²/j d'après le guide, W/m² d'après le support "
     "de formation : à confirmer)",
     "obligatoire — une chaîne sans rayonnement est inutilisable", P1, "Rien.", 1,
     "Quelques stations synoptiques et INRAE ; en repli les réanalyses ERA5-Land ou AgERA5 "
     "(Copernicus) et NASA POWER, grossières pour une île à relief.",
     "https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators",
     "Gratuit, compte Copernicus et licence du service ; NASA POWER libre", "Comparer la réanalyse à une station avant de s'y fier."),
    ("Climat", "ETP Penman-Monteith journalière", "meteo/observee/<année>.csv : ETP (mm)",
     "obligatoire", P1, "Rien.", 1,
     "ETP fournie par Météo-France pour certains postes ; sinon à calculer (FAO-56) à "
     "partir de T, humidité, vent et rayonnement (méthode FAO-56).", FAO56,
     "Météo-France : Licence Ouverte 2.0 ; FAO-56 en libre lecture",
     "Choisir une seule méthode pour toute l'île. Le fichier météo n'a pas de colonne "
     "d'humidité de l'air, alors qu'un déclencheur de traitement s'appelle hygrométrie."),
    ("Climat", "Grille climatique", "polygonesMeteoFrance.shp : ID_PDG, POSX, POSY, ALTI_MOY",
     "obligatoire", P1,
     "Pas de maille SAFRAN outre-mer. Le raster des normales de pluie et le MNT "
     "permettent de découper des zones.", 1,
     "À construire : polygones autour des stations, recoupés par classes de pluie et "
     "d'altitude.", DOC_ENTREES, "—",
     "Demander à l'équipe MAELIA le système de coordonnées attendu hors métropole."),
    ("Climat", "Gradient spatial de pluie", "sert à construire la grille", "utile", P1,
     "Pluvio_1981-2010_MF_kriging_spher_10m.tif et PLUVIO_PARC par parcelle.", 2,
     "Météo-France, normales 1981-2010 krigées (couche fournie au projet MOSAICA).", "",
     "Local (data/gis/, non versionné) ; conditions de réutilisation à préciser",
     "Sert à redresser les séries de station par zone ; annuel seulement."),
    ("Climat", "Projections climatiques journalières (20 ans au moins, avec rayonnement)",
     "meteo/simulee/<scénario>/<année>.csv", "pour les scénarios climatiques", P2,
     "Rien en local.", 1,
     "DRIAS diffuse les projections C3AF : quotidiennes, aux stations (69 pluviomètres, 17 "
     "postes thermiques sur les Antilles), RCP 8.5 seul, 1980-2013 et 2031-2080, pluie et "
     "températures seulement. Les projections Outre-mer à 3 km (SocleOM-climat-2025) "
     "arrivent sur DRIAS au cours de 2026. En complément, NEX-GDDP-CMIP6 (0,25°, avec "
     "rayonnement).", "https://www.drias-climat.fr/",
     "DRIAS : gratuit, sur compte ; NEX-GDDP : libre",
     "C3AF n'a ni rayonnement ni ETP : inutilisable seul pour MAELIA. Suivre la mise en "
     "ligne des données à 3 km ; viser deux narratifs contrastés."),
    ("Sols", "Carte des sols et zonage", "typeDeSolParZH.shp : ID_SOL, STU_DOM, ZONE_PEDO",
     "obligatoire", P1,
     "Carte Colmet-Daage–Brossard (26 unités cartographiques, 18 types simplifiés, "
     "data/gis/04_Pédologie), TYPE_SOL (5 groupes) et TYPE_SOL_INIT par parcelle.", 2,
     "Cartes Colmet-Daage numérisées par l'IRD (1/20 000, 1961, GeoTIFF) dans DataSuds-geo ; "
     "la Guadeloupe n'est pas dans la liste des référentiels régionaux du GIS Sol (mail de "
     "l'équipe MAELIA). L'équipe propose d'intégrer les données fournies à son système "
     "d'information.", "https://datasuds-geo.ird.fr/",
     "Copie locale ; DataSuds : licence à vérifier par carte", "Traduire la légende en ZONE_PEDO et en unités de sol."),
    ("Sols", "Lien îlot → sol", "ilots.shp : ID_SOL", "obligatoire", P1,
     "Croisement RPG × pédologie déjà fait (RPG_2017_GC_MG_Pédologie).", 2, "—", "", "Local",
     "Sol dominant par îlot, une fois les ID_SOL définis."),
    ("Sols", "Profondeurs des horizons et profondeur enracinable",
     "P1..P4, PRO, PRO_OC, CSTRU", "obligatoire", P1,
     "SOL_COURT par parcelle (sol squelettique) ; Data_Sol PROF (couche de carbone).", 1,
     SOLS_PISTES, "https://www.gissol.fr/le-gis/programmes/rmqs-34",
     "Publications ; données RMQS sur demande au GIS Sol", "CSTRU vaut 0,9 par défaut."),
    ("Sols", "Texture et cailloux par horizon", "ARG, LIM, SAB, EG (CX)", "obligatoire", P1,
     "Rien.", 1, SOLS_PISTES + " (250 m)", "https://soilgrids.org/",
     "Publications ; RMQS sur demande ; SoilGrids CC-BY 4.0",
     "La granulométrie classique décrit mal les andosols (allophanes)."),
    ("Sols", "Densité apparente", "DAH1..4, DAH_OC", "obligatoire", P1,
     "Data_Sol, ligne DENS : une valeur par groupe de sol.", 2, SOLS_PISTES, "", "Local",
     "Par horizon dans MAELIA, par groupe de sol ici."),
    ("Sols", "Réserve utile, capacité au champ, point de flétrissement",
     "RUPRH1..4, HCC1, HPFP1", "obligatoire", P1, "Rien.", 1,
     "Courbes de rétention publiées par INRAE Antilles-Guyane pour vertisols, ferralsols, "
     "andosols et nitisols.", "", "Publications",
     "Les fonctions de pédotransfert tempérées (Saxton et Rawls) ne valent ni pour les "
     "andosols ni pour les vertisols."),
    ("Sols", "Conductivité à saturation et infiltrabilité", "KSAT1..4, PIRM", "obligatoire",
     P1, "RUI_PARC et DRAI_PARC (ruissellement et drainage annuels par parcelle) : "
     "indices, pas des conductivités.", 0, "Mesures de terrain INRAE ; à défaut valeurs "
     "par type de sol avec l'équipe MAELIA.", "", "—",
     "Les vertisols gonflants sortent du cadre d'un Ksat constant."),
    ("Sols", "Matière organique", "MO1", "AqYieldNC", P2,
     "PART_C_INIT par parcelle (carbone organique initial, %) : MO = C × 1,72.", 2,
     "MORGWANIK ; analyses de terre.", "", "Local",
     "L'azote minéral initial du sol et la fraction stable de la matière organique (0,65 par "
     "défaut, option du lanceur) sont aussi des entrées : où les fournir, à confirmer."),
    ("Sols", "pH, C/N, calcaire", "PH1, CN1, CAL1", "AqYieldNC", P2, "Rien.", 1, SOLS_PISTES,
     "https://www.gissol.fr/le-gis/programmes/rmqs-34",
     "Publications ; données RMQS sur demande au GIS Sol",
     "Calcaire : Grande-Terre et Marie-Galante surtout."),
    ("Parcellaire", "Géométrie des îlots et des parcelles",
     "ilots.shp, parcelles.shp : ID_ILOT, ID_PARCELL, ID_EXPL, SURFACE, POURCENTAG",
     "obligatoire", P1,
     "RPG 2017 avec pacage, pac_ilot, num_ilot, parcelle, surf_parc (data/gis/01_RPG 2017).",
     3, "RPG (ASP, diffusé par l'IGN). La version publique est anonymisée, sans numéro "
     "d'exploitation ; sa couverture de la Guadeloupe reste à vérifier.",
     "https://geoservices.ign.fr/rpg",
     "Niveau 2 : la version avec numéro PACAGE est réservée aux administrations, sur "
     "demande à la DAAF ; vérifier la convention qui couvre la copie locale",
     "ID_PARCELL = pac_ilot + « _ » + parcelle, à confirmer avec l'équipe MAELIA."),
    ("Parcellaire", "Séquences de cultures", "parcelles.shp : SEQUENCE, CULT_REF, INDEX_DEP, "
     "EXPREST, ID_SDC", "obligatoire", P1,
     "Groupe RPG déclaré de 2012 à 2017 par parcelle (Data_RPG_Gwad_2017) ; ou le plan "
     "optimisé par MOSAICA.", 2,
     "Séquences RPG Explorer (INRAE), construites sur le RPG public depuis 2015, pour la "
     "France hexagonale seulement.",
     "https://entrepot.recherche.data.gouv.fr/dataset.xhtml?persistentId=doi:10.57745/W8SQPZ",
     "RPG Explorer : Licence Etalab 2.0 ; nos séquences, niveau 2", "12 groupes, pas la culture fine ; que devient une plantation de 7 ans "
     "dans une séquence annuelle ?"),
    ("Parcellaire", "Pente", "ilots.shp : PENTE_MOY, PENTE_SWAT", "obligatoire", P1,
     "MNT de 1 à 10 m et pente par parcelle (data/gis/02_Altitude, 03_Pente).", 2,
     "RGE ALTI (IGN) : le MNT à 1 m de Guadeloupe vient des levés Litto3D (IGN-SHOM). "
     "L'origine du MNT local n'est pas documentée dans ses métadonnées.",
     "https://geoservices.ign.fr/rgealti",
     "Local ; RGE ALTI diffusé gratuitement par l'IGN (licence à lire sur la fiche)",
     "Unité de PENTE à confirmer (% ou degrés)."),
    ("Parcellaire", "Irrigabilité", "ilots.shp : CARACT_IRR", "obligatoire", P1,
     "Réseau d'irrigation du Conseil départemental (bornes, canalisations, tampon de 800 m) "
     "et IRRIG_PARC.", 2, "Conseil départemental de la Guadeloupe, propriétaire du réseau ; "
     "exploitation en délégation de service public (Karukér'Ô dans le Nord Grande-Terre, "
     "contrat renouvelé en 2024).", "",
     "Copie locale ; mise à jour à demander au Département", "Date du relevé à vérifier ; MOSAICA le complète par la culture observée "
     "(vigilance G.10)."),
    ("Parcellaire", "Parcelles fauchables et pâturables", "parcelles.shp : IS_FAUCHE, "
     "IS_PATURAG", "pour les prairies", P2,
     "Rien par parcelle ; les deux ITK de prairie (piquet, pâturage tournant) disent le mode.",
     1, "Dire d'expert ; règle simple par ITK.", "", "—",
     "Champs vus dans le jeu de la formation (1.4.31), absents du guide."),
    ("Exploitations", "Liste et type des exploitations", "exploitations.csv : ID_EXPL, "
     "TYPE_EXPL", "obligatoire", P1,
     "4 638 exploitations et leur type (8 types MOSAICA, d'après Chopin et al. 2015).", 2,
     "—", "", "Niveau 2",
     "TYPE_EXPL sert à choisir l'ITK dans MAELIA : la typologie économique de MOSAICA "
     "n'est pas forcément le bon critère."),
    ("Exploitations", "Matériel d'irrigation", "materiel.csv : surface irrigable par jour, "
     "travail par jour ; ilots.shp : MATERIEL", "si irrigation", P1, "Rien.", 1,
     "Dire d'expert : Chambre d'agriculture, Conseil départemental.", CHAMBRE, "—",
     "Aspersion, goutte-à-goutte : quelques types suffisent."),
    ("Exploitations", "Main-d'œuvre disponible", "contrainte de main-d'œuvre "
     "(avecContrainteDeMainOeuvre)", "pour le test de robustesse", P2,
     "Budget d'heures par exploitation (MO_Expl_init, reconstruit à partir des ITK "
     "observés).", 2, "Recensement agricole 2020 (UTA).", AGRESTE,
     "Niveau 2. RA 2020 : public à l'EPCI ; données individuelles sous secret statistique, "
     "par le CASD après avis du Comité du secret",
     "Annuel dans MOSAICA. MAELIA compte par jour : 12 h par unité de main-d'œuvre, 16 h pour "
     "finir une parcelle (paramétrable). Où déclarer le nombre d'unités par exploitation, et "
     "si les chantiers faits par un tiers comptent : à confirmer."),
    ("Exploitations", "Outils et débits de chantier", "<OT>_OUTIL, <OT>_TEMPS de "
     "reglesDeDecisions.csv", "pour le temps de travail et l'économie", P2,
     "Temps de travail par opération (Data_OTK : MO_EXPL × DOSE) ; pas de liste d'outils.", 2,
     "Référentiel d'outils de la grille d'enquête ITK ; Chambre d'agriculture.", CHAMBRE, "—",
     "Le matériel tropical (coupeuse de canne, câble de bananeraie) est à ajouter."),
    ("Exploitations", "Élevage : lots d'animaux et bâtiments", "lotsAnimaux.csv (ID_LOT, "
     "TYPE_ANIMAUX, NB_UGB, CST_ALIM, FECES, RESTITUTION_BATIMENT, ELOIGNEMENT_MIN/MAX), "
     "batiments.shp", "pour le pâturage", P2,
     "Rien : l'élevage n'apparaît dans MOSAICA que par les ITK de prairie.", 0,
     "Recensement agricole 2020, base nationale d'identification bovine (BDNI).", AGRESTE,
     "RA : individuel par le CASD seulement ; BDNI : accès restreint",
     "À cadrer avec le projet CEDRE (élevage)."),
    ("Engrais et PRO", "Engrais minéraux", "engrais.csv : composition, facteurs NH₃, "
     "eqCO2, coût", "AqYieldNC", P2,
     "Data_OTK : teneur en N, prix unitaire ; P et K par la formule du produit.", 2,
     "Engrais.csv des jeux d'exemple MAELIA (types génériques AN, Urea, NPK…).",
     DOC_ENTREES, "Local", "Faire correspondre chaque produit à un type MAELIA."),
    ("Engrais et PRO", "Produits organiques locaux (fumier, compost, écumes, vinasse, "
     "bagasse)", "engrais.csv : C, N, humidité, paramètres de décomposition (K1, C2, kres…)",
     "AqYieldNC", P2, "Data_OTK : HUM, CARB, FHUM des amendements.", 1,
     "Analyses INRAE/CIRAD des produits locaux ; paramètres de décomposition par analogie "
     "avec un produit du fichier MAELIA.", DOC_ENTREES, "Publications",
     "Les paramètres de décomposition demandent des incubations : analogie d'abord."),
    ("Engrais et PRO", "Gisements annuels de PRO", "engrais.csv : QuantiteDispoAnnuelleT",
     "AqYieldNC", P2, "Rien.", 1, "Sucreries et distilleries, ADEME, Chambre d'agriculture.",
     CHAMBRE, "—", "À 0, le produit n'est jamais épandu ; 1000000000 = illimité. Stock "
     "géré au niveau du territoire ou de l'exploitation ; un délai de retour par produit. En "
     "1.4.31 : parametres/engrais_qte_annuelle_dispo.csv."),
    ("Économie", "Prix et redevance de l'eau", "prixEau.csv, redevanceEau.csv", "si irrigation",
     P2, "Un forfait par hectare (EAU_IRRIG, MAT_IRRIG dans Data_OTK), pas un prix au m³.", 1,
     "Tarif du réseau départemental : une part fixe et une part au m³ (0,09 € HT/m³ au "
     "total en 2012, rapport du délégataire) ; Office de l'eau Guadeloupe (redevances).",
     "https://www.cg971.fr/wp-content/uploads/2020/07/CRF-V2-RAPPORT-2012-Guadeloupe-Irrigation-modif-suite-demande-SD-19-11-13.pdf",
     "Public ; tarif en vigueur à demander au Département",
     "MAELIA attend un prix par m³ et par type de ressource (nappe, surface, retenue, canal)."),
    ("Économie", "Prix du carburant", "module économique (grille d'enquête : GNR, €/L)",
     "pour les sorties économiques", P2, "Rien.", 1,
     "Prix maximaux fixés chaque mois par arrêté préfectoral (code de l'énergie, R. 671-1 et "
     "suivants), publiés au recueil des actes administratifs de la préfecture.", "", "Public",
     "Le gazole non routier est-il dans l'arrêté ? À vérifier."),
    ("Économie", "Séries de prix pluriannuelles", "prixVentes<SC>.csv : une colonne par an",
     "pour les scénarios de prix", P2, "2017 ; les années 2018-2022 en sont des copies.", 1,
     "DAAF Guadeloupe (bulletins de conjoncture Agreste), ODEADOM.", AGRESTE, "Public",
     "Les bulletins donnent des prix par filière, pas toujours par culture fine."),
    ("Validation", "Rendements observés par culture et par an",
     "sert à caler RENDEMENT_OPTIMAL et à valider", "indispensable au calage", P1,
     "Rdt_Cult, sans série annuelle.", 1,
     "Agreste Guadeloupe (mémentos, bulletins de conjoncture : surfaces, productions ; "
     "canne : tonnage broyé et rendement moyen), interprofession canne et CTCS pour le "
     "détail par bassin, LPG pour la banane.",
     "https://daaf.guadeloupe.agriculture.gouv.fr/IMG/pdf/agreste_memento_2022_guadeloupe.pdf",
     "Agreste public ; détail par bassin ou par exploitation à demander aux filières",
     "C'est ici que la vigilance C.1 se règle ou se déplace."),
    ("Validation", "Jeux expérimentaux pour calibrer AqYield en tropical",
     "humidité et azote du sol, biomasse, LAI", "pour créer une espèce", P1, "Rien.", 0,
     "Essais INRAE Antilles-Guyane et CIRAD ; LAI par télédétection (Sentinel-2).", "",
     "Essais : à demander aux équipes ; Sentinel-2 : libre", "Commencer par une culture pilote (igname ou melon), puis la canne."),
    ("Référentiels", "Limites administratives", "communes.shp, departement.shp",
     "optionnel (un avertissement s'il manque) ; le département sert aux aides couplées", P2,
     "Code commune par parcelle ; pas la couche.", 1, "ADMIN EXPRESS (IGN).",
     "https://geoservices.ign.fr/adminexpress", "Licence Ouverte 2.0", "Téléchargement direct."),
    ("Référentiels", "Calendrier", "date/joursParMois.csv", "obligatoire", P1,
     "Contenu fixe, donné dans le guide.", 3, "Guide MAELIA.", DOC_ENTREES, "—",
     "À recopier tel quel."),
    ("Référentiels", "Contour du terrain et zone hydrographique minimale", "contourZH.shp, "
     "ZH.shp ; ID_ZH dans ilots.shp et typeDeSolParZH.shp", "obligatoire, à confirmer", P1,
     "Contour des îles (par le RPG ou les communes) ; 230 bassins versants.", 2, "—", "", "Local",
     "Les deux jeux d'exemple gardent ces fichiers alors que le module hydrologique est "
     "coupé (une seule zone dans terrainTest)."),
    ("Hydrologie", "Bassins versants élémentaires et leur chaînage", "ZH.shp : ID_ZH, "
     "ID_ND_EXUT", "module hydrologique", P3,
     "230 bassins de 50 ha et plus avec exutoires (data/gis/10_Bassins versants) et "
     "bassin de chaque parcelle.", 2,
     "Nos bassins, tirés du MNT. La BD TOPAGE Guadeloupe (Sandre) donne cours d'eau, plans "
     "d'eau et tronçons, mais pas encore de bassins versants.",
     "https://www.data.gouv.fr/datasets/bd-topage-r-guadeloupe-2026",
     "Local ; BD TOPAGE : Licence Ouverte 2.0", "La table de chaînage amont-aval reste à écrire."),
    ("Hydrologie", "Relief", "MNT, pente (alti25m, pente_percent)", "module hydrologique", P3,
     "MNT de 1 à 10 m.", 3, "RGE ALTI (IGN).", "https://geoservices.ign.fr/rgealti", "Local",
     "—"),
    ("Hydrologie", "Géomorphologie SWAT et HRU", "donneesMNT_ZH.csv, hru_*.shp",
     "module hydrologique", P3, "Rien.", 1, "À produire avec ArcSWAT ou QSWAT.", DOC_ENTREES,
     "—", "Un projet en soi."),
    ("Hydrologie", "Occupation du sol", "clc/", "module hydrologique", P3, "Rien.", 1,
     "KaruCover (KaruGéo) : occupation du sol à grande échelle, 77 postes, 2004, 2010, 2017 "
     "et 2022, compatible OCS GE. En repli, Corine Land Cover (DOM couverts, unité "
     "minimale 25 ha).",
     "https://www.karugeo.fr/accueil/actualites/92_224/karucover_ocs2d__une_donnee_de_reference",
     "KaruGéo : consultation libre, conditions de téléchargement à vérifier ; CLC libre",
     "KaruCover 2017 est contemporain du RPG utilisé par MOSAICA."),
    ("Hydrologie", "Réseau hydrographique, retenues, canaux", "troncons/, "
     "retenuesCollinaires/, canaux/", "module hydrologique", P3,
     "Ouvrages et canalisations du réseau d'irrigation.", 1,
     "BD TOPO (IGN), BD TOPAGE Guadeloupe, Conseil départemental (ouvrages d'irrigation).",
     "https://geoservices.ign.fr/bdtopo", "Licence Ouverte 2.0", "—"),
    ("Hydrologie", "Prélèvements et rejets", "equipements/ (points de prélèvement)",
     "module hydrologique", P3, "Périmètres de protection des captages (PPE, PPI, PPR).", 1,
     "Banque nationale des prélèvements en eau (BNPE), qui couvre les DOM : volumes annuels "
     "par ouvrage et par usage.", "https://bnpe.eaufrance.fr/", "Libre",
     "Annuel seulement."),
    ("Hydrologie", "Débits observés", "calage du module hydrologique", "module hydrologique",
     P3, "Rien.", 1, "Réseau hydrométrique de la DEAL (HydroPortail, bulletins "
     "hydrologiques) ; Observatoire de l'eau de Guadeloupe.",
     "https://www.hydro.eaufrance.fr/", "Libre",
     "La DEAL signale des courbes de tarage en consolidation et des lacunes en 2024."),
    ("Normatif", "Débits de référence, restrictions, règles des barrages",
     "pointsDeReference.shp, seuilsDeRestriction.csv, barrage.csv", "module normatif", P3,
     "Rien.", 2, "Arrêté cadre sécheresse (DEAL/RN n° 971-2023-07-06-0009) : seuils de "
     "vigilance, d'alerte et de crise à 7 stations ; SDAGE Guadeloupe.",
     "https://www.guadeloupe.developpement-durable.gouv.fr/", "Public",
     "Les règles de gestion des retenues restent à obtenir."),
    ("Indicateurs", "Biodiversité (i-Bio) et érosion", "parcelles.shp : IBIO_LCD, IBIO_HSN, "
     "IBIO_CONN ; texture, matière organique et pente pour l'érosion", "optionnel", P3,
     "ZNIEFF, pente ; pas d'indicateur de paysage.", 1, "À calculer par SIG.", "", "—",
     "Modules présentés à la formation ; champs IBIO vus dans le jeu 1.4.31."),
    ("Indicateurs", "Zonages réglementaires", "plan d'épandage (engrais.csv : plan_epandage), "
     "zones vulnérables, captages", "optionnel", P3,
     "Périmètres de protection des captages, ZNIEFF, risque chlordécone par parcelle.", 2,
     "DEAL Guadeloupe ; KaruGéo diffuse les cartes de chlordécone dans les sols.",
     "https://www.karugeo.fr/", "Local ; KaruGéo en consultation libre",
     "La grille d'enquête ITK demande les réglementations du territoire."),
    ("Filières", "Unités de transformation, recettes, transport", "UT.shp, UP.shp, "
     "recettes.csv, produits.csv, routes.shp", "module filières", P3,
     "Quotas et capacités par filière dans les contraintes de MOSAICA.", 1,
     "Sucreries, distilleries, centrale bagasse-biomasse ; OpenStreetMap (routes).",
     "https://www.openstreetmap.org/", "—", "—"),
)

VERROUS = (
    ("Cultures tropicales", "Hors la jachère (« gel »), aucune culture de MOSAICA n'existe dans "
     "la base d'espèces de MAELIA. Chacune est à créer, avec le référent thématique : une "
     "colonne complète dans le fichier des espèces (la formation le fait avec « mon_espece »)."),
    ("Plantations pluriannuelles", "Canne (3 à 7 ans), banane (8 à 15 ans), agrumes et vergers "
     "(15 ans), ananas (18 mois) : la séquence MAELIA est annuelle et un ITK décrit une année, "
     "semis et récolte compris. Aucun mécanisme documenté ; vergers et vignes ne figurent pas "
     "dans le référentiel d'espèces de la grille d'enquête."),
    ("Plafonds d'un ITK", "{plafonds}"),
    ("Récolte", "La récolte attend la maturité en degrés-jours, puis elle est forcée en fin de "
     "fenêtre. Une campagne fixée par l'usine (canne) ou une récolte continue (banane, "
     "maraîchage) ne se décrivent pas ainsi."),
    ("Prairies", "HerbSim ne connaît que 7 espèces tempérées et 5 types de graminées : les "
     "prairies naturelles tropicales, un quart de la surface observée, n'ont pas de "
     "paramètres. L'azote n'est plus un obstacle : le jeu de la formation fait tourner des "
     "prairies fauchées et pâturées avec AqYieldNC (HerbSimNC)."),
    ("Rendement potentiel", "RENDEMENT_OPTIMAL reste une entrée : le remplir avec Rdt_Cult "
     "reporterait la surestimation des rendements (vigilance C.1) dans MAELIA."),
    ("Opérations sans type MAELIA", "Effeuillage, tuteurage, ensachage, emballage, soins aux "
     "animaux : jusqu'à 85 % des heures de la banane disparaissent à la traduction."),
    ("Choix de l'ITK", "MOSAICA choisit la variante d'ITK, MAELIA la déduit de la situation. "
     "Deux pistes pour imposer une variante par parcelle sans créer une espèce par variante : "
     "la séquence de référence (ID_SDC de la parcelle, IDS_SDCS de l'ITK) et le critère libre "
     "CRIT_SPAT_ADHOC. À vérifier avec l'équipe."),
    ("Calendrier tempéré", "La première année démarre en août ; un frein hivernal, un drapeau "
     "« culture d'hiver » et une fauche de fin d'été au 1er août sont dans le modèle. À passer "
     "en revue pour un climat sans hiver."),
    ("Mécanisation", "D'après la note de 2022, les entrées OUTIL, PASSAGES et AGRIW n'ont pas "
     "d'effet sur la simulation : aucun conflit de matériel n'est simulé. À revérifier en 1.4.31."),
    ("Fichiers", "Les csv et dbf de MAELIA ne se modifient pas dans Excel (séparateurs, "
     "décimales). Ce classeur sert à piloter la collecte, pas à saisir les données."),
)

A_CONFIRMER = (
    ("Format des fichiers", "Le guide (août 2026) place especesCultivees.csv et Engrais.csv "
     "dans culture/ et Engrais/. Le jeu de la formation (MAELIA 1.4.31) lit un dossier "
     "parametres/ : une case vide prend la valeur de la base MAELIA, une espèce nouvelle "
     "demande une colonne complète. Les lignes d'ITK y sont renommées (TRAVAIL_SOL, "
     "DESHERBAGE_MECA, PATURE). Quel format viser ?"),
    ("Variante d'ITK par parcelle", "ID_SDC et CRIT_SPAT_ADHOC permettent-ils d'imposer la "
     "variante choisie par MOSAICA sans créer une espèce par variante ?"),
    ("Plafonds et récoltes multiples", "Nombre maximal d'opérations par ITK dans la version "
     "courante ; comment décrire 34 passages de récolte par an."),
    ("Main-d'œuvre", "Où déclarer le nombre d'unités de main-d'œuvre par exploitation ; les "
     "chantiers faits par un tiers (coupe de la canne) consomment-ils le temps de l'agriculteur ?"),
    ("Module économique", "Quels fichiers la version courante lit-elle : prixVentes, primes, "
     "chargesOp et chargesDePassage du guide, ou les prix unitaires de la grille d'enquête ? "
     "Unité de prixVentes (le guide imprime €/ha)."),
    ("Zone hydrographique", "Faut-il au moins une zone hydrographique et un contour quand le "
     "module hydrologique est coupé ?"),
    ("Géographie", "Système de coordonnées attendu hors métropole ; POSX et POSY de la grille "
     "météo sont décrits en Lambert II étendu."),
    ("Météo", "Unité du rayonnement (MJ/m²/j ou W/m²) ; d'où vient l'humidité de l'air du "
     "déclencheur hygrométrie."),
    ("État initial du sol", "Azote minéral initial par couche et fraction stable de la matière "
     "organique : fichier ou valeurs par défaut ?"),
    ("Climat sans hiver", "FREIN = 1, IS_CULTURE_HIVER, démarrage en août, stress de gel : "
     "quels réglages pour un terrain tropical ?"),
)

# Lignes des fichiers d'espèces et d'ITK que la feuille Cultures ne note pas.
NON_NOTES = (
    ("COULEUR_R, COULEUR_V, COULEUR_B", "Couleur d'affichage : obligatoire, sans enjeu."),
    ("isCouvert", "Vrai pour un couvert intermédiaire : faux pour toutes les cultures de MOSAICA."),
    ("a_Ndemand_ci, b_Ndemand_ci, Dde", "Propres aux couverts intermédiaires."),
    ("RootC_fixed, BESOIN_Ntot", "Variantes de SR_ratio et de BESOIN_N (apport racinaire fixe, "
     "besoin total par hectare comme pour la betterave et la pomme de terre)."),
    ("tgelLev10/90, tgelJuv10/90, tgelVeg10/90, tgelFlo10/90, DEGRES_J_stadeJuvenile, "
     "DEGRES_J_dureeFloraison", "Stress climatique (gel, échaudage), apparus en 1.4.31 ; "
     "inactif par défaut (avecStressClimatique). Le gel est sans objet aux Antilles, "
     "l'échaudage reste à instruire."),
    ("ALPHA*, KC*", "Modèle de culture « simple » seulement."),
    ("date_maj, source_projet, indice_fiabilite", "Traçabilité de l'espèce (1.4.31). MAELIA "
     "tient son propre indice de fiabilité par espèce."),
    ("IS_CULTURE_HIVER", "Culture d'hiver ou de printemps : sert à choisir un ITK de repli "
     "quand le semis échoue. Sens à définir sous les tropiques."),
    ("IS_CORPEN", "Ajuste les doses d'azote minéral aux rendements simulés (option du lanceur)."),
    ("<OT>_OUTIL, _AGRIW, _PASSAGES, _OPERATEUR, _NOM, _OT_PREALABLE", "Outil, opération faite "
     "par l'agriculteur ou par un tiers, passages, nom. Sans effet sur la simulation d'après la "
     "note de 2022 ; l'outil sert au module économique."),
    ("ID_ANTE_PREC, ID_SUIV, CRIT_SPAT_ADHOC", "Antéprécédent, culture suivante, critère "
     "libre : critères de spatialisation apparus en 1.4.31."),
    ("PHYTO_TYPE", "Type de traitement, pour l'IFT."),
    ("IRRIGATION_SIRR1 à 3, _IS_THEORIQUE, _GROUPE", "Mode d'optimisation de l'irrigation "
     "(taux de satisfaction hydrique visé par stade) et tours d'eau par groupe."),
)

LIENS = (
    ("Documentation MAELIA", "https://maelia.pages-forge.inrae.fr/documentation"),
    ("Documentation MAELIA — données d'entrée", DOC_ENTREES),
    ("Application ITK (compte : Renaud Misslin, MAELAB)", APPLI_ITK),
    ("Forum MAELIA", "https://forum-maelia.discourse.group/"),
    ("Site MAELIA", "https://www.maelia-iam.fr/"),
)


# --- lecture des tables MOSAICA ---------------------------------------------------------------


def lire_cultures() -> tuple[list[Culture], list[str], str]:
    from case_studies.guadeloupe.domain.crop_families import base_group_for
    from case_studies.guadeloupe.domain.itk import annual_rate_per_ha
    from case_studies.guadeloupe.pipeline.data_pipeline import (
        DEFAULT_YEAR, INDICE_H_DIR, build_dataset,
    )
    from case_studies.guadeloupe.reporting import maelia_crops
    from core.config import load_config
    from core.data.readers import read_wide_table
    from scripts._common import CONFIG_PATH

    config = load_config(CONFIG_PATH)
    data = config.get("data") or {}
    year = data.get("year", DEFAULT_YEAR)
    p = build_dataset(config).parameters
    crop_data, operation_data = p["crop_data"], p["operation_data"]
    matrix = p["crop_operation_matrix"].fillna(0)
    plantation = read_wide_table(INDICE_H_DIR / "Duree_Plant_Cult.txt")[year]
    cycle = p["crop_cycle_duration"]

    types = maelia_crops.operation_types(matrix, operation_data)
    hours = (operation_data["DOSE"] * operation_data["MO_EXPL"]).reindex(matrix.index).fillna(0)
    amortized = (operation_data["AMORTI"] == 1).reindex(matrix.index, fill_value=False)
    is_pass = (operation_data["NATURE"] == 1).reindex(matrix.index, fill_value=False)
    labour = annual_rate_per_ha(matrix, hours, plantation, cycle, amortized)
    labour_untyped = annual_rate_per_ha(matrix, hours.where(types.isna(), 0), plantation, cycle,
                                        amortized)
    water = crop_data.loc[[f"BESOIN_EAU_{m:02d}" for m in range(1, 13)]].sum()
    surface = p["plot_data"]["SURF_HA"].groupby(p["baseline_fine_crop"]).sum()
    proteins = p["crop_nutrient_content"].loc["Prot"]

    cultures, sans_itk = [], []
    for code in matrix.columns:
        used = matrix.index[matrix[code] != 0]
        if len(used) == 0:  # en-têtes de groupe RPG (CS, BA…) : jamais alloués avec un ITK
            sans_itk.append(code)
            continue
        total = float(labour.get(code, 0))
        # Passages par an : les opérations (NATURE = 1), celles de plantation étalées sur
        # la durée de la plantation. Les lignes d'intrants (NATURE = 0) sont des quantités.
        years = max(float(plantation.get(code, 1)), 1.0)
        per_year = (matrix[code].where(~amortized, matrix[code] / years)
                    * 12 / float(cycle.get(code, 12)))
        cultures.append(Culture(
            code=code, famille=base_group_for(code), plante=plante(code),
            surface_2017_ha=float(surface.get(code, 0)),
            rendement=float(p["crop_yield"].get(code, 0)),
            variance=float(p["crop_variance_per_ha"].get(code, 0)),
            proteines=float(proteins.get(code, 0)),
            long_rac=float(crop_data.at["LONG_RAC", code]),
            biom_aer=float(crop_data.at["BIOM_AER", code]),
            rac=float(crop_data.at["RAC", code]), carb=float(crop_data.at["CARB", code]),
            prof_sillons=float(crop_data.at["PROF_SILLONS", code]),
            types_ot=set(types[used].dropna()), n_ot_types=int(types[used].notna().sum()),
            n_ot=len(used),
            part_heures_hors_types=float(labour_untyped.get(code, 0)) / total if total else 0.0,
            besoin_eau=float(water[code]), prix=float(p["crop_price"].get(code, 0)),
            primes=float(p["crop_subsidy_per_ha_annualized"].get(code, 0)),
            charges=float(p["crop_variable_cost_per_ha"].get(code, 0)),
            duree_plantation=float(plantation.get(code, 1)),
            duree_cycle_mois=float(cycle.get(code, 12)),
            passages_par_an={k: float(per_year[is_pass & (types == k)].sum()) for k in PLAFONDS},
        ))
    ordre = list(FAMILLES)
    cultures.sort(key=lambda c: (ordre.index(c.famille), -c.surface_2017_ha, c.code))
    return cultures, sans_itk, f"année {year}, scénario {data.get('scenario', 'RESTIT')}"


def modele_maelia(c: Culture) -> str:
    return {"prairie": "HerbSim / HerbSimNC", "jachère": "gel (espèce existante, ITK fourni)"}.get(
        c.plante, "AqYield / AqYieldNC")


# Ce qu'un ITK peut contenir, d'après la grille d'enquête ITK de la formation (version 1.4.22) :
# type MAELIA -> (nom affiché, nombre maximal d'opérations). À confirmer avec l'équipe.
PLAFONDS = {"harvest": ("récoltes", 1), "fertilisation": ("apports", 4),
            "crop_protection": ("traitements", 8), "hoeing": ("désherbages", 5),
            "tillage": ("préparations du sol", 4)}


def depassements(c: Culture) -> str:
    return " ; ".join(f"{c.passages_par_an[k]:.3g} {nom} (max {cap})"
                      for k, (nom, cap) in PLAFONDS.items() if c.passages_par_an[k] > cap + 0.01)


def cycle(c: Culture) -> str:
    if c.duree_cycle_mois > 12:
        return f"cycle de {c.duree_cycle_mois:g} mois"
    if c.duree_plantation > 1:
        return f"plantation de {c.duree_plantation:g} ans"
    return "annuelle"


def moyenne(values) -> float | str:
    nums = [v for v in values if not isinstance(v, str)]
    return sum(nums) / len(nums) if nums else SO


# --- écriture ---------------------------------------------------------------------------------

ROUGE, JAUNE, VERT = "#F8696B", "#FFEB84", "#63BE7B"
ENCRE, GRIS, PALE = "#1F2937", "#6B7280", "#F3F4F6"
ECHELLE_COULEUR = {"type": "3_color_scale", "min_type": "num", "min_value": 0,
                   "mid_type": "num", "mid_value": 1.5, "max_type": "num", "max_value": 3,
                   "min_color": ROUGE, "mid_color": JAUNE, "max_color": VERT}
TEINTES_BLOC = {B_EAU: "#DBEAFE", B_NC: "#E0E7FF", B_ITK: "#FEF3C7", B_FERTI: "#FDE68A",
                B_ECO: "#E5E7EB"}


def ecrire(cultures: list[Culture], sans_itk: list[str], origine: str, out: Path) -> None:
    wb = xlsxwriter.Workbook(str(out))
    wb.set_properties({"title": "Inventaire des données pour MAELIA en Guadeloupe",
                       "author": "MOSAICA"})
    base = {"font_name": "Calibri", "font_size": 10, "font_color": ENCRE, "valign": "vcenter"}
    f = lambda **kw: wb.add_format({**base, **kw})  # noqa: E731
    titre = f(bold=True, font_size=14)
    sous_titre = f(italic=True, font_color=GRIS)
    entete = f(bold=True, bg_color=ENCRE, font_color="#FFFFFF", text_wrap=True, border=1,
               border_color="#FFFFFF")
    texte = f(text_wrap=True, valign="top")
    gras = f(bold=True)
    score = f(align="center", border=1, border_color="#FFFFFF")
    score_so = f(align="center", font_color="#9CA3AF", bg_color=PALE, border=1,
                 border_color="#FFFFFF")
    moy = f(align="center", num_format="0.0", border=1, border_color="#FFFFFF")
    moy_gras = f(align="center", num_format="0.0", bold=True, border=1, border_color="#FFFFFF")
    entier = f(num_format="# ##0")
    pourcent = f(num_format="0%", align="center")
    lien = f(font_color="#1D4ED8", underline=1, text_wrap=True, valign="top")

    # Créées dans l'ordre de lecture ; « Cultures » est remplie d'abord car les autres la citent.
    ws_lm = wb.add_worksheet("Lisez-moi")
    ws_sy = wb.add_worksheet("Synthèse")
    ws_cu = wb.add_worksheet("Cultures")
    ws_pa = wb.add_worksheet("Paramètres")
    ws_au = wb.add_worksheet("Autres données")

    # ---- Cultures ----
    INFO = ("Famille", "Code", "Culture", "Surface 2017 (ha)", "Modèle MAELIA", "Cycle",
            "Heures hors types MAELIA", "Dépassements des plafonds d'un ITK (passages par an)")
    n_info, n_par = len(INFO), len(PARAMETRES)
    R_BLOC, R_NOM, R0 = 2, 3, 4
    R1 = R0 + len(cultures) - 1
    col_par = {i: n_info + i for i in range(n_par)}
    c_moy0 = n_info + n_par
    SYNTH = [BLOCS_COURTS[b] for b in BLOCS] + ["Score global", "Paramètres à 0"]

    ws_cu.write(0, 0, "Qualité des données par culture et par paramètre MAELIA", titre)
    ws_cu.write(1, 0, "0 = absente, difficile · 1 = absente, accessible · 2 = disponible, à "
                f"retravailler · 3 = utilisable · {SO} = sans objet. Les notes sont "
                "modifiables : les moyennes et la feuille Synthèse suivent.", sous_titre)
    for j, name in enumerate(INFO):
        ws_cu.merge_range(R_BLOC, j, R_NOM, j, name, entete)
    for bloc in BLOCS:
        cols = [col_par[i] for i, par in enumerate(PARAMETRES) if par.bloc == bloc]
        fmt = f(bold=True, bg_color=TEINTES_BLOC[bloc], align="center", text_wrap=True, border=1,
                border_color="#FFFFFF")
        # Le nom complet (avec le fichier MAELIA) ne tient pas sur un bloc de deux colonnes.
        ws_cu.merge_range(R_BLOC, cols[0], R_BLOC, cols[-1],
                          bloc if len(cols) > 8 else BLOCS_COURTS[bloc], fmt)
    rot = f(bold=True, rotation=90, align="center", valign="bottom", text_wrap=True, border=1,
            border_color="#FFFFFF", bg_color=PALE)
    for i, par in enumerate(PARAMETRES):
        ws_cu.write(R_NOM, col_par[i], par.nom, rot)
        ws_cu.write_comment(R_NOM, col_par[i], f"{par.sens}\n\nNote : {par.regle}",
                            {"x_scale": 2.2, "y_scale": 1.8})
    ws_cu.merge_range(R_BLOC, c_moy0, R_BLOC, c_moy0 + len(SYNTH) - 1, "Moyennes de la ligne",
                      f(bold=True, bg_color=ENCRE, font_color="#FFFFFF", align="center"))
    for k, name in enumerate(SYNTH):
        ws_cu.write(R_NOM, c_moy0 + k, name, rot)

    notes: dict[str, list] = {}
    for r, c in enumerate(cultures, start=R0):
        row = [noter(par, c) for par in PARAMETRES]
        notes[c.code] = row
        ws_cu.write(r, 0, FAMILLES[c.famille], gras)
        ws_cu.write(r, 1, c.code)
        ws_cu.write(r, 2, libelle(c.code))
        ws_cu.write_number(r, 3, round(c.surface_2017_ha, 1), entier)
        ws_cu.write(r, 4, modele_maelia(c))
        ws_cu.write(r, 5, cycle(c))
        ws_cu.write_number(r, 6, round(c.part_heures_hors_types, 2), pourcent)
        ws_cu.write(r, 7, depassements(c))
        for i, v in enumerate(row):
            ws_cu.write(r, col_par[i], v, score_so if v == SO else score)
        for k, bloc in enumerate(BLOCS):
            cols = [col_par[i] for i, par in enumerate(PARAMETRES) if par.bloc == bloc]
            rng = f"{xl_rowcol_to_cell(r, cols[0])}:{xl_rowcol_to_cell(r, cols[-1])}"
            ws_cu.write_formula(r, c_moy0 + k, f'=IFERROR(AVERAGE({rng}),"{SO}")', moy,
                                moyenne(row[cols[0] - n_info:cols[-1] - n_info + 1]))
        rng = f"{xl_rowcol_to_cell(r, n_info)}:{xl_rowcol_to_cell(r, n_info + n_par - 1)}"
        ws_cu.write_formula(r, c_moy0 + len(BLOCS), f'=IFERROR(AVERAGE({rng}),"{SO}")', moy_gras,
                            moyenne(row))
        ws_cu.write_formula(r, c_moy0 + len(BLOCS) + 1, f"=COUNTIF({rng},0)",
                            f(align="center"), sum(1 for v in row if v == 0))

    surf = f"${xl_col_to_name(3)}${R0 + 1}:${xl_col_to_name(3)}${R1 + 1}"
    surfaces = [c.surface_2017_ha for c in cultures]
    pied = f(bold=True, bg_color=PALE)
    for offset, label in ((1, "Moyenne des cultures"),
                          (2, "Moyenne pondérée par la surface 2017")):
        ws_cu.merge_range(R1 + offset, 0, R1 + offset, n_info - 1, label, pied)
    for col in list(col_par.values()) + [c_moy0 + k for k in range(len(BLOCS) + 1)]:
        letter = xl_col_to_name(col)
        rng = f"{letter}{R0 + 1}:{letter}{R1 + 1}"
        if col < c_moy0:
            vals = [notes[c.code][col - n_info] for c in cultures]
        elif col < c_moy0 + len(BLOCS):
            idx = [i for i, par in enumerate(PARAMETRES) if par.bloc == BLOCS[col - c_moy0]]
            vals = [moyenne([notes[c.code][i] for i in idx]) for c in cultures]
        else:
            vals = [moyenne(notes[c.code]) for c in cultures]
        pairs = [(v, s) for v, s in zip(vals, surfaces) if not isinstance(v, str)]
        weight = sum(s for _, s in pairs)
        ws_cu.write_formula(R1 + 1, col, f'=IFERROR(AVERAGE({rng}),"{SO}")', moy_gras,
                            moyenne(vals))
        ws_cu.write_formula(
            R1 + 2, col, f'=IFERROR(SUMPRODUCT({surf},{rng})/SUMIF({rng},">=0",{surf}),"{SO}")',
            moy_gras, sum(v * s for v, s in pairs) / weight if weight else SO)

    zone = (R0, n_info, R1 + 2, c_moy0 + len(BLOCS))
    ws_cu.conditional_format(*zone, ECHELLE_COULEUR)
    ws_cu.data_validation(R0, n_info, R1, n_info + n_par - 1,
                          {"validate": "list", "source": ["0", "1", "2", "3", SO],
                           "error_title": "Note", "error_message": f"0, 1, 2, 3 ou {SO}"})
    ws_cu.freeze_panes(R0, 3)
    ws_cu.autofilter(R_NOM, 0, R1, c_moy0 + len(SYNTH) - 1)
    ws_cu.set_row(R_BLOC, 30)
    ws_cu.set_row(R_NOM, 150)
    for j, width in enumerate((27, 15, 50, 10, 30, 19, 9, 44)):
        ws_cu.set_column(j, j, width)
    ws_cu.set_column(n_info, c_moy0 + len(SYNTH) - 1, 4.3)
    if sans_itk:
        ws_cu.write(R1 + 4, 0, "Codes sans ITK, laissés de côté (en-têtes de groupe RPG) : "
                    + ", ".join(sans_itk), sous_titre)

    # ---- Paramètres ----
    ws_pa.write(0, 0, "Dictionnaire des paramètres de la feuille Cultures", titre)
    ws_pa.write(1, 0, "Une ligne par colonne notée. Les décomptes renvoient à la feuille "
                "Cultures ; les pistes de sources sont à valider.", sous_titre)
    heads = ("Bloc", "Paramètre MAELIA", "Signification", "Unité", "Nécessité",
             "Ce que MOSAICA a", "Règle de notation", "Pistes de sources", "Lien", "Moyenne",
             "Moyenne pondérée surface", "Cultures à 0", "à 1", "à 2", "à 3", "sans objet",
             "Surface à 0 (ha)", "Surface à 0 ou 1 (ha)")
    for j, h in enumerate(heads):
        ws_pa.write(3, j, h, entete)
    for i, par in enumerate(PARAMETRES):
        r = 4 + i
        letter = xl_col_to_name(col_par[i])
        rng = f"Cultures!${letter}${R0 + 1}:${letter}${R1 + 1}"
        surf_cu = f"Cultures!{surf}"
        vals = [notes[c.code][i] for c in cultures]
        pairs = [(v, s) for v, s in zip(vals, surfaces) if not isinstance(v, str)]
        weight = sum(s for _, s in pairs)
        ws_pa.write(r, 0, BLOCS_COURTS[par.bloc], f(bg_color=TEINTES_BLOC[par.bloc],
                                                    text_wrap=True, valign="top"))
        ws_pa.write(r, 1, par.nom, f(bold=True, valign="top", text_wrap=True))
        for j, value in enumerate((par.sens, par.unite, par.necessite, par.mosaica, par.regle,
                                   par.pistes), start=2):
            ws_pa.write(r, j, value, texte)
        if par.lien:
            ws_pa.write_url(r, 8, par.lien, lien, par.lien)
        ws_pa.write_formula(r, 9, f'=IFERROR(AVERAGE({rng}),"{SO}")', moy, moyenne(vals))
        ws_pa.write_formula(
            r, 10, f'=IFERROR(SUMPRODUCT({surf_cu},{rng})/SUMIF({rng},">=0",{surf_cu}),"{SO}")',
            moy, sum(v * s for v, s in pairs) / weight if weight else SO)
        for k, level in enumerate((0, 1, 2, 3)):
            ws_pa.write_formula(r, 11 + k, f"=COUNTIF({rng},{level})", f(align="center"),
                                sum(1 for v in vals if v == level))
        ws_pa.write_formula(r, 15, f'=COUNTIF({rng},"{SO}")', f(align="center"),
                            sum(1 for v in vals if v == SO))
        ws_pa.write_formula(r, 16, f"=SUMIF({rng},0,{surf_cu})", entier,
                            sum(s for v, s in pairs if v == 0))
        ws_pa.write_formula(r, 17, f'=SUMIF({rng},"<=1",{surf_cu})', entier,
                            sum(s for v, s in pairs if v <= 1))
    last = 3 + n_par
    ws_pa.conditional_format(4, 9, last, 10, ECHELLE_COULEUR)
    for col in (16, 17):
        ws_pa.conditional_format(4, col, last, col, {"type": "data_bar", "bar_color": "#F59E0B",
                                                     "bar_solid": True})
    ws_pa.freeze_panes(4, 2)
    ws_pa.autofilter(3, 0, last, len(heads) - 1)
    r = last + 2
    ws_pa.write(r, 0, "Lignes des fichiers MAELIA non notées", gras)
    for name, text in NON_NOTES:
        r += 1
        ws_pa.merge_range(r, 0, r, 1, name, f(bold=True, valign="top", text_wrap=True))
        ws_pa.merge_range(r, 2, r, 7, text, texte)
        ws_pa.set_row(r, 30)
    for j, width in enumerate((16, 26, 42, 14, 18, 40, 44, 44, 30, 9, 11, 8, 6, 6, 6, 8, 12, 12)):
        ws_pa.set_column(j, j, width)
    ws_pa.set_row(3, 32)

    # ---- Autres données ----
    ws_au.write(0, 0, "Données hors cultures : climat, sols, parcellaire, exploitations, "
                "hydrologie", titre)
    ws_au.write(1, 0, "Même échelle 0-3. La priorité dit quel usage la donnée bloque : le "
                "module agricole seul (1), la version azote et le test de robustesse (2), "
                "les modules hydrologique, normatif et filières (3). Laissés de côté, sans "
                "objet sur une île tropicale : bandes d'altitude pour la neige, îlots hors "
                "zone.", sous_titre)
    heads = ("Thème", "Donnée", "Fichier et champs MAELIA", "Nécessité", "Priorité",
             "Ce qu'on a aujourd'hui", "Qualité", "Sources", "Lien", "Accès, licence",
             "À faire, remarques")
    for j, h in enumerate(heads):
        ws_au.write(3, j, h, entete)
    for i, row in enumerate(AUTRES):
        r = 4 + i
        for j, value in enumerate(row):
            if j == 6:
                ws_au.write_number(r, j, value, f(align="center", valign="top", bold=True,
                                                  border=1, border_color="#FFFFFF"))
            elif j == 8 and value:
                ws_au.write_url(r, j, value, lien, value)
            elif j == 0:
                ws_au.write(r, j, value, f(bold=True, valign="top"))
            else:
                ws_au.write(r, j, value, texte)
    last_au = 3 + len(AUTRES)
    ws_au.conditional_format(4, 6, last_au, 6, ECHELLE_COULEUR)
    ws_au.data_validation(4, 6, last_au, 6, {"validate": "list", "source": ["0", "1", "2", "3"]})
    ws_au.freeze_panes(4, 2)
    ws_au.autofilter(3, 0, last_au, len(heads) - 1)
    for j, width in enumerate((14, 30, 34, 20, 18, 46, 8, 46, 34, 22, 44)):
        ws_au.set_column(j, j, width)
    ws_au.set_row(3, 22)

    # ---- Synthèse ----
    ws_sy.write(0, 0, "Synthèse : où en sont les données pour MAELIA en Guadeloupe", titre)
    ws_sy.write(1, 0, "Moyenne des notes (0 à 3) ; les cellules sans objet ne comptent pas. "
                "Tout est recalculé depuis les feuilles Cultures et Autres données.", sous_titre)
    ws_sy.write(3, 0, "Par famille de cultures", gras)
    heads = ["Famille", "Variantes", "Surface 2017 (ha)"] + SYNTH[:-1]
    for j, h in enumerate(heads):
        ws_sy.write(4, j, h, entete)
    fam_rng = f"Cultures!$A${R0 + 1}:$A${R1 + 1}"
    r = 5
    for code, name in FAMILLES.items():
        members = [c for c in cultures if c.famille == code]
        if not members:
            continue
        ws_sy.write(r, 0, name, gras)
        ws_sy.write_formula(r, 1, f"=COUNTIF({fam_rng},$A{r + 1})", f(align="center"),
                            len(members))
        ws_sy.write_formula(r, 2, f"=SUMIF({fam_rng},$A{r + 1},Cultures!{surf})", entier,
                            sum(c.surface_2017_ha for c in members))
        for k in range(len(BLOCS) + 1):
            letter = xl_col_to_name(c_moy0 + k)
            rng = f"Cultures!${letter}${R0 + 1}:${letter}${R1 + 1}"
            if k < len(BLOCS):
                idx = [i for i, par in enumerate(PARAMETRES) if par.bloc == BLOCS[k]]
                vals = [moyenne([notes[c.code][i] for i in idx]) for c in members]
            else:
                vals = [moyenne(notes[c.code]) for c in members]
            ws_sy.write_formula(r, 3 + k, f'=IFERROR(AVERAGEIFS({rng},{fam_rng},$A{r + 1}),"{SO}")',
                                moy_gras if k == len(BLOCS) else moy, moyenne(vals))
        r += 1
    ws_sy.conditional_format(5, 3, r - 1, 3 + len(BLOCS), ECHELLE_COULEUR)
    ws_sy.conditional_format(5, 2, r - 1, 2, {"type": "data_bar", "bar_color": "#93C5FD",
                                              "bar_solid": True})

    r += 2
    ws_sy.write(r, 0, "Par thème, hors cultures", gras)
    for j, h in enumerate(("Thème", "Données", "Qualité moyenne", "Données à 0")):
        ws_sy.write(r + 1, j, h, entete)
    th_rng = f"'Autres données'!$A$5:$A${last_au + 1}"
    q_rng = f"'Autres données'!$G$5:$G${last_au + 1}"
    r += 2
    first_theme = r
    for theme in dict.fromkeys(row[0] for row in AUTRES):
        vals = [row[6] for row in AUTRES if row[0] == theme]
        ws_sy.write(r, 0, theme, gras)
        ws_sy.write_formula(r, 1, f"=COUNTIF({th_rng},$A{r + 1})", f(align="center"), len(vals))
        ws_sy.write_formula(r, 2, f'=IFERROR(AVERAGEIFS({q_rng},{th_rng},$A{r + 1}),"{SO}")', moy,
                            moyenne(vals))
        ws_sy.write_formula(r, 3, f"=COUNTIFS({th_rng},$A{r + 1},{q_rng},0)", f(align="center"),
                            sum(1 for v in vals if v == 0))
        r += 1
    ws_sy.conditional_format(first_theme, 2, r - 1, 2, ECHELLE_COULEUR)

    r += 2
    ws_sy.write(r, 0, "Ce qu'une meilleure donnée ne réglera pas", gras)
    r += 1
    hors_plafond = [c for c in cultures if depassements(c)]
    pire = max(cultures, key=lambda c: c.passages_par_an["harvest"])
    plafonds = (
        "La grille d'enquête ITK prévoit un semis et une récolte par ITK, "
        + ", ".join(f"{cap} {nom}" for k, (nom, cap) in PLAFONDS.items() if k != "harvest")
        + f" (les apports s'entendent par stratégie de fertilisation). {len(hors_plafond)} "
        f"cultures sur {len(cultures)} en sortent, soit "
        f"{round(sum(c.surface_2017_ha for c in hors_plafond)):d} ha observés en 2017, jusqu'à "
        f"{pire.passages_par_an['harvest']:.0f} passages de récolte par an pour {pire.code} : "
        "colonne Dépassements de la feuille Cultures.")
    for titre_bloc, lignes in (("Ce qu'une meilleure donnée ne réglera pas", VERROUS),
                               ("À confirmer avec l'équipe MAELIA", A_CONFIRMER)):
        if lignes is A_CONFIRMER:
            r += 2
            ws_sy.write(r, 0, titre_bloc, gras)
            r += 1
        for name, text in lignes:
            ws_sy.write(r, 0, name, f(bold=True, valign="top", text_wrap=True))
            ws_sy.merge_range(r, 1, r, 8, text.replace("{plafonds}", plafonds), texte)
            ws_sy.set_row(r, 44)
            r += 1
    ws_sy.set_column(0, 0, 30)
    ws_sy.set_column(1, 1, 11)
    ws_sy.set_column(2, 2, 17)
    ws_sy.set_column(3, 8, 14)
    ws_sy.set_row(4, 32)

    # ---- Lisez-moi ----
    ws_lm.set_column(0, 0, 4)
    ws_lm.set_column(1, 1, 34)
    ws_lm.set_column(2, 2, 110)
    ws_lm.write(0, 1, "Inventaire des données pour instancier MAELIA en Guadeloupe", titre)
    ws_lm.write(1, 1, f"Généré le {dt.date.today():%d/%m/%Y} à partir des tables MOSAICA "
                f"({origine}) et de la documentation MAELIA.", sous_titre)
    r = 3
    ws_lm.write(r, 1, "L'échelle", gras)
    for level, name, text in ECHELLE:
        r += 1
        ws_lm.write_number(r, 0, level, f(align="center", bold=True))
        ws_lm.write(r, 1, name, gras)
        ws_lm.write(r, 2, text, texte)
    ws_lm.conditional_format(4, 0, r, 0, ECHELLE_COULEUR)
    r += 1
    ws_lm.write(r, 0, SO, score_so)
    ws_lm.write(r, 1, "Sans objet", gras)
    ws_lm.write(r, 2, "Le paramètre ne concerne pas cette culture (pas d'irrigation, pas de "
                "travail du sol, prairie simulée par HerbSim, jachère sans ITK).", texte)
    r += 2
    ws_lm.write(r, 1, "Les feuilles", gras)
    for name, text in (
        ("Synthèse", "Score moyen par famille de cultures et par thème, et les verrous qui ne "
         "tiennent pas aux données."),
        ("Cultures", f"{len(cultures)} cultures fines de MOSAICA × {n_par} paramètres MAELIA. "
         "Survoler un en-tête de colonne affiche le sens du paramètre et la règle de notation."),
        ("Paramètres", "Le dictionnaire des colonnes : ce que MOSAICA a, comment la note est "
         "donnée, où chercher, et la surface concernée par chaque manque."),
        ("Autres données", f"{len(AUTRES)} jeux de données hors cultures (climat, sols, "
         "parcellaire, exploitations, hydrologie…), avec leurs sources et leurs liens."),
    ):
        r += 1
        ws_lm.write(r, 1, name, gras)
        ws_lm.write(r, 2, text, texte)
    r += 2
    ws_lm.write(r, 1, "Comment les notes sont données", gras)
    for name, text in (
        ("Notes calculées", "Quand la donnée se lit dans les tables de MOSAICA (rendement, "
         "opérations, temps de travail, doses, prix, aides, charges), la note est calculée "
         "culture par culture. Elle est plafonnée à 2 quand la valeur est un proxy ou que son "
         "niveau est discuté."),
        ("Notes appréciées", "Quand la donnée manque (phénologie, Kc, réponse à l'eau, besoins "
         "en azote, calendrier), la note dit seulement si une référence publiée existe pour la "
         "plante : 1 si oui, 0 sinon. C'est une appréciation à faire valider par les "
         "agronomes ; les pistes de sources n'ont pas été vérifiées une à une."),
        ("Variantes d'une même plante", "Les paramètres d'espèce sont communs à toutes les "
         "variantes d'une plante (les 18 cannes à sucre, les 4 bananes) : seuls l'ITK, le "
         "rendement et l'économie les distinguent."),
        ("Surface 2017", "Surface observée, ventilée sur les cultures fines par les règles "
         "GAMS d'attribution des ITK. Elle sert à pondérer : un manque sur la canne pèse plus "
         "qu'un manque sur le melon."),
        ("Corriger une note", "Les notes se modifient dans la feuille Cultures (liste "
         "déroulante) ; couleurs, moyennes et Synthèse suivent. Relancer le script écrase ces "
         "corrections : pour les garder, les reporter dans le script."),
    ):
        r += 1
        ws_lm.write(r, 1, name, f(bold=True, valign="top"))
        ws_lm.write(r, 2, text, texte)
        ws_lm.set_row(r, 44)
    r += 2
    ws_lm.write(r, 1, "Sources MAELIA et versions", gras)
    for name, text in (
        ("Guide de l'utilisateur", "Version d'août 2026 : structure des fichiers, application "
         "ITK. Tables parfois tronquées."),
        ("Note de 2022", "Note d'accompagnement à la préparation des données d'entrée : champs "
         "obligatoires des sols, couples de règles de déclenchement."),
        ("Formation de septembre 2026", "Supports, grille d'enquête ITK (version 1.4.22) et "
         "deux jeux d'exemple : terrainTest et le jeu du TD, simulé avec MAELIA 1.4.31."),
        ("Quand les sources divergent", "Le jeu 1.4.31 fait foi, parce qu'il a tourné : dossier "
         "parametres/, lignes d'ITK renommées, prairies simulées avec l'azote, économie "
         "facultative. Les points douteux sont listés en bas de la feuille Synthèse."),
    ):
        r += 1
        ws_lm.write(r, 1, name, f(bold=True, valign="top"))
        ws_lm.write(r, 2, text, texte)
        ws_lm.set_row(r, 30)
    r += 2
    ws_lm.write(r, 1, "Liens utiles", gras)
    for name, url in LIENS:
        r += 1
        ws_lm.write(r, 1, name)
        ws_lm.write_url(r, 2, url, lien, url)
    r += 2
    ws_lm.write(r, 1, "Régénérer", gras)
    ws_lm.write(r, 2, ".venv/Scripts/python clement/maelia/build_inventaire_donnees_maelia.py",
                f(font_name="Consolas"))
    ws_lm.write(r + 1, 2, "Pour aller plus loin : docs/maelia/README.md, crop-parameters.md et "
                "coupling-todo.md dans le dépôt MOSAICA.", sous_titre)

    for ws in (ws_lm, ws_sy, ws_cu, ws_pa, ws_au):
        ws.hide_gridlines(2)
    ws_cu.set_landscape()
    ws_au.set_landscape()
    ws_sy.activate()
    wb.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    cultures, sans_itk, origine = lire_cultures()
    ecrire(cultures, sans_itk, origine, args.out)
    print(f"{len(cultures)} cultures x {len(PARAMETRES)} paramètres, {len(AUTRES)} autres "
          f"données -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
