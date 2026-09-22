"""Audit du corpus et construction du graphe de justification.

Le corpus (`memoire/corpus/*.yaml`) affirme deux choses que personne ne verifie a la
main sur 481 items :

  1. aucun choix retenu n'est arbitraire      -> tout `retenu` porte un `parce-que`
  2. aucune branche n'a ete coupee au flair   -> tout `ecarte` porte un `mesure-par`

Ce script les verifie, plus six controles de forme (ids, enums, arcs pendants,
symetrie parce-que/justifie, macros inconnues, couverture dans le .tex).

Il n'ECRIT JAMAIS dans les .yaml : ils portent des commentaires que PyYAML detruirait
au dump. La symetrie manquante est completee EN MEMOIRE pour le graphe, et listee dans
le rapport pour correction manuelle.

    python memoire/audit_corpus.py             # rapport -> stdout + corpus/_audit.md
    python memoire/audit_corpus.py --graph     # + corpus/_graphe.dot et _graphe-*.mmd
    python memoire/audit_corpus.py --strict    # code de sortie non nul si une regle casse
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent
CORPUS = RACINE / "corpus"
CHAPITRES = RACINE / "chapitres"
CHIFFRES = RACINE / "chiffres.tex"

# --- vocabulaire ferme, copie de corpus/00-schema.md -------------------------

TYPES = {
    "choix", "resultat", "piege", "erreur", "notion",
    "methode", "organisation", "donnee", "perspective", "reflexivite",
}
STATUTS = {"retenu", "ecarte", "differe", "erreur-a-posteriori", "ouvert"}
SEVERITES = {"critique", "majeur", "mineur", None}
ARCS = ["parce-que", "justifie", "ferme-la-branche", "mesure-par", "contredit"]
DESTINATIONS = (
    {f"ch{i}" for i in range(7)}
    | {f"annexe{c}" for c in "ABCDEF"}
    | {"oral", "note", "article", "aucune"}
)

# prefixe attendu par fichier
PREFIXES = {
    "10-contexte-commande": "CTX",
    "20-portage-gams": "PORT",
    "30-architecture-logicielle": "ARCH",
    "40-solveur-tractabilite": "SOLV",
    "50-donnees": "DON",
    "60-calibration": "CAL",
    "70-prospective": "PROS",
    "80-indicateurs": "IND",
    "90-verification-outillage": "VER",
    "95-methode-organisation": "MET",
    "96-reflexivite": "REF",
    "97-perspectives": "PERSP",
    "98-article": "ART",
}

# ch0..ch6 -> le .tex qui doit porter l'item
CHAPITRE_TEX = {
    "ch0": "00-introduction.tex",
    "ch1": "01-terrain-et-objet.tex",
    "ch2": "02-porter.tex",
    "ch3": "03-calibrer.tex",
    "ch4": "04-explorer.tex",
    "ch5": "05-discussion.tex",
    "ch6": "06-conclusion.tex",
}


@dataclass
class Item:
    id: str
    fichier: str
    titre: str
    type: str | None
    statut: str | None
    severite: str | None = None
    source: list[str] = field(default_factory=list)
    chiffre: list[str] = field(default_factory=list)
    destination: list[str] = field(default_factory=list)
    arcs: dict[str, list[str]] = field(default_factory=dict)
    critique: str | None = None
    reflexif: bool = False
    brut: dict = field(default_factory=dict)

    @property
    def prefixe(self) -> str:
        return self.id.rsplit("-", 1)[0]

    @property
    def est_branche(self) -> bool:
        return bool(re.search(r"-B\d+$", self.id))

    def a(self, arc: str) -> list[str]:
        return self.arcs.get(arc) or []


def _liste(valeur) -> list[str]:
    """Un champ absent, null, scalaire ou liste -> toujours une liste de str."""
    if valeur is None:
        return []
    if isinstance(valeur, str):
        return [valeur]
    return [str(v) for v in valeur]


def charger() -> tuple[list[Item], list[str]]:
    items: list[Item] = []
    erreurs: list[str] = []
    for chemin in sorted(CORPUS.glob("*.yaml")):
        souche = chemin.stem
        attendu = PREFIXES.get(souche)
        try:
            brut = yaml.safe_load(chemin.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            erreurs.append(f"{chemin.name} : YAML illisible -- {exc}")
            continue
        if not isinstance(brut, list):
            erreurs.append(f"{chemin.name} : la racine doit etre une liste d'items")
            continue
        for rang, entree in enumerate(brut, 1):
            if not isinstance(entree, dict) or "id" not in entree:
                erreurs.append(f"{chemin.name} item #{rang} : pas d'`id`")
                continue
            reflexif = "axe" in entree
            item = Item(
                id=str(entree["id"]).strip(),
                fichier=chemin.name,
                titre=str(entree.get("titre") or entree.get("axe") or "").strip(),
                type=entree.get("type"),
                statut=entree.get("statut"),
                severite=entree.get("severite"),
                source=_liste(entree.get("source")),
                chiffre=_liste(entree.get("chiffre")),
                destination=_liste(entree.get("destination")),
                arcs={k: _liste(v) for k, v in (entree.get("arcs") or {}).items()},
                critique=entree.get("critique"),
                reflexif=reflexif,
                brut=entree,
            )
            if attendu and not item.id.startswith(attendu + "-"):
                erreurs.append(f"{item.id} : prefixe attendu {attendu}- dans {chemin.name}")
            items.append(item)
    return items, erreurs


def valider_forme(items: list[Item]) -> list[str]:
    """Les controles qui ne demandent que l'item lui-meme."""
    pbs: list[str] = []
    vus: dict[str, str] = {}
    for it in items:
        if it.id in vus:
            pbs.append(f"{it.id} : id duplique ({vus[it.id]} et {it.fichier})")
        vus[it.id] = it.fichier

        if not it.titre:
            pbs.append(f"{it.id} : titre vide")
        if it.reflexif:
            # forme differente et voulue : ancrage/question/risque au lieu de source/statut
            for champ in ("ancrage", "question", "risque"):
                if not it.brut.get(champ):
                    pbs.append(f"{it.id} : champ reflexif `{champ}` manquant")
            continue
        if it.type not in TYPES:
            pbs.append(f"{it.id} : type `{it.type}` hors vocabulaire")
        if it.statut not in STATUTS:
            pbs.append(f"{it.id} : statut `{it.statut}` hors vocabulaire")
        if it.severite not in SEVERITES:
            pbs.append(f"{it.id} : severite `{it.severite}` hors vocabulaire")
        if not it.source:
            pbs.append(f"{it.id} : aucune source -- l'affirmation n'est pas verifiable")
        if not it.destination:
            pbs.append(f"{it.id} : aucune destination (mettre `aucune` si archive)")
        for dest in it.destination:
            if dest not in DESTINATIONS:
                pbs.append(f"{it.id} : destination `{dest}` inconnue")
        for arc in it.arcs:
            if arc not in ARCS:
                pbs.append(f"{it.id} : arc `{arc}` inconnu")
    return pbs


def valider_arcs(items: list[Item]) -> tuple[list[str], list[str]]:
    """Arcs pendants, et symetrie parce-que <-> justifie.

    La symetrie est completee en memoire (le graphe doit etre juste) et signalee
    (les .yaml doivent le devenir aussi, a la main, pour garder les commentaires).
    """
    par_id = {it.id: it for it in items}
    pendants: list[str] = []
    asymetries: list[str] = []

    for it in items:
        for arc, cibles in it.arcs.items():
            for cible in cibles:
                if cible not in par_id:
                    pendants.append(f"{it.id} --{arc}--> {cible} : cible inexistante")

    for it in items:
        for parent in it.a("parce-que"):
            p = par_id.get(parent)
            if p is not None and it.id not in p.a("justifie"):
                asymetries.append(f"{parent} devrait porter `justifie: [{it.id}]`")
                p.arcs.setdefault("justifie", []).append(it.id)
        for enfant in it.a("justifie"):
            e = par_id.get(enfant)
            if e is not None and it.id not in e.a("parce-que"):
                asymetries.append(f"{enfant} devrait porter `parce-que: [{it.id}]`")
                e.arcs.setdefault("parce-que", []).append(it.id)

    return pendants, sorted(set(asymetries))


# Les types qui relevent d'une DECISION, et sont donc justiciables d'un `parce-que`.
# Un `resultat`, une `donnee`, une `notion`, un `piege` ou une `erreur` ne se justifie
# pas : il s'etablit, et c'est `source:` qui en repond. Confondre les deux etait le
# defaut de la premiere version de cette regle -- elle reclamait une justification a
# des faits, ce qui n'a pas de sens et noyait les vrais manques.
TYPES_DECIDES = {"choix", "methode", "organisation", "perspective"}


def regle_1_choix_justifies(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """Tout `choix` retenu porte un `parce-que` -- sauf s'il se declare `racine: true`."""
    manquants, racines = [], []
    for it in items:
        if it.reflexif or it.statut != "retenu" or it.type not in TYPES_DECIDES:
            continue
        if it.brut.get("racine") is True:
            racines.append(it)
        elif not it.a("parce-que"):
            manquants.append(it)
    return manquants, racines


def regle_2_ecarts_mesures(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """Tout `ecarte` porte un `mesure-par` -- sauf s'il declare `sans-mesure: <raison>`.

    L'echappatoire existe parce qu'une branche peut etre coupee sur une PREUVE et non
    sur une mesure : qu'une somme ponderee ne puisse pas atteindre la partie non convexe
    d'un front est un theoreme, pas une opinion, et aucun banc d'essai ne l'etablirait
    mieux. Elle est declaree, donc comptee, donc opposable.
    """
    manquants, assumes = [], []
    for it in items:
        if it.reflexif or it.statut != "ecarte":
            continue
        if it.a("mesure-par"):
            continue
        (assumes if it.brut.get("sans-mesure") else manquants).append(it)
    return manquants, assumes


def regle_3_verdicts_renverses(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """Tout `erreur-a-posteriori` dit ce qu'il renverse.

    Soit par un arc `contredit` vers l'item porteur du verdict perime, soit -- cas le
    plus frequent -- par un champ `verdict-anterieur` en clair, parce qu'une croyance
    qu'on tenait sans l'ecrire n'a jamais eu d'id.
    """
    manquants, en_clair = [], []
    for it in items:
        if it.reflexif or it.statut != "erreur-a-posteriori":
            continue
        if it.a("contredit"):
            continue
        (en_clair if it.brut.get("verdict-anterieur") else manquants).append(it)
    return manquants, en_clair


def macros_connues() -> set[str]:
    if not CHIFFRES.exists():
        return set()
    texte = CHIFFRES.read_text(encoding="utf-8")
    return set(re.findall(r"\\newcommand\{\\(\w+)\}", texte))


def valider_chiffres(items: list[Item], connues: set[str]) -> list[str]:
    pbs = []
    for it in items:
        for macro in it.chiffre:
            nom = macro.lstrip("\\")
            if nom not in connues:
                pbs.append(f"{it.id} : macro \\{nom} absente de chiffres.tex")
    return pbs


def audit_couverture(items: list[Item]) -> dict:
    """Un item destine a un chapitre est-il traçable dans le .tex de ce chapitre ?

    Preuve utilisee : au moins une de ses macros de chiffre y est citee. C'est un
    PROXY -- un item sans chiffre est incontrolable automatiquement, il est compte
    a part et pas signale comme manquant.
    """
    textes = {}
    for ch, nom in CHAPITRE_TEX.items():
        chemin = CHAPITRES / nom
        textes[ch] = chemin.read_text(encoding="utf-8") if chemin.exists() else ""

    couvert, manquant, sans_chiffre = [], [], []
    for it in items:
        cibles = [d for d in it.destination if d in CHAPITRE_TEX]
        if not cibles:
            continue
        if not it.chiffre:
            sans_chiffre.append(it)
            continue
        for ch in cibles:
            trouve = any(
                re.search(r"\\" + re.escape(m.lstrip("\\")) + r"\b", textes[ch])
                for m in it.chiffre
            )
            (couvert if trouve else manquant).append((it, ch))
    return {"couvert": couvert, "manquant": manquant, "sans_chiffre": sans_chiffre}


def macros_orphelines(connues: set[str]) -> list[str]:
    """Macros definies dans chiffres.tex et citees nulle part dans le mémoire."""
    corpus_tex = "\n".join(
        p.read_text(encoding="utf-8")
        for p in list(CHAPITRES.glob("*.tex")) + list(RACINE.glob("*.tex"))
        if p.name != "chiffres.tex"
    )
    citees = set(re.findall(r"\\(\w+)", corpus_tex))
    return sorted(connues - citees)


def topologie(items: list[Item]) -> dict:
    par_id = {it.id: it for it in items}
    reels = [it for it in items if not it.reflexif]

    racines = [it for it in reels if not it.a("parce-que")]
    feuilles = [it for it in reels if not it.a("justifie")]
    isoles = [
        it for it in reels
        if not any(it.a(a) for a in ARCS)
        and not any(it.id in autre.a(a) for autre in reels for a in ARCS)
    ]

    # profondeur = plus long chemin descendant depuis l'item, avec garde anti-cycle
    profondeur: dict[str, int] = {}
    en_cours: set[str] = set()
    cycles: list[str] = []

    def prof(ident: str) -> int:
        if ident in profondeur:
            return profondeur[ident]
        if ident in en_cours:
            cycles.append(ident)
            return 0
        en_cours.add(ident)
        it = par_id.get(ident)
        enfants = [c for c in (it.a("justifie") if it else []) if c in par_id]
        val = 1 + max((prof(c) for c in enfants), default=0)
        en_cours.discard(ident)
        profondeur[ident] = val
        return val

    for it in reels:
        prof(it.id)

    return {
        "racines": racines,
        "feuilles": feuilles,
        "isoles": isoles,
        "profondeur": profondeur,
        "cycles": sorted(set(cycles)),
        "plus_profonds": sorted(reels, key=lambda i: -profondeur.get(i.id, 0))[:12],
    }


def branches(items: list[Item]) -> list[dict]:
    """Le tableau de la demonstration : choix retenu / branche coupee / mesure."""
    par_id = {it.id: it for it in items}
    lignes = []
    for it in items:
        for cible in it.a("ferme-la-branche"):
            b = par_id.get(cible)
            mesures = (b.a("mesure-par") if b else []) or it.a("mesure-par")
            lignes.append({
                "retenu": it,
                "branche": b,
                "branche_id": cible,
                "mesure": [par_id.get(m) for m in mesures if m in par_id],
                "mesure_ids": mesures,
            })
    return lignes


# --- rendu -------------------------------------------------------------------

COULEUR_STATUT = {
    "retenu": "#1b5e20",
    "ecarte": "#b71c1c",
    "differe": "#e65100",
    "erreur-a-posteriori": "#4a148c",
    "ouvert": "#01579b",
}
FORME_TYPE = {
    "choix": "box", "resultat": "ellipse", "piege": "octagon",
    "erreur": "doubleoctagon", "notion": "note", "methode": "component",
    "organisation": "folder", "donnee": "cylinder", "perspective": "cds",
    "reflexivite": "oval",
}
STYLE_ARC = {
    "parce-que": ("normal", "#37474f", "solid"),
    "ferme-la-branche": ("tee", "#b71c1c", "bold"),
    "mesure-par": ("empty", "#0277bd", "dashed"),
    "contredit": ("diamond", "#6a1b9a", "dotted"),
}


def ecrire_dot(items: list[Item], sortie: Path) -> None:
    reels = [it for it in items if not it.reflexif]
    par_prefixe: dict[str, list[Item]] = defaultdict(list)
    for it in reels:
        par_prefixe[it.prefixe.split("-")[0]].append(it)

    lignes = [
        "digraph corpus {",
        '  graph [rankdir=LR, splines=spline, overlap=false, fontname="Helvetica"];',
        '  node  [fontname="Helvetica", fontsize=9, style=filled, fillcolor="#fafafa"];',
        '  edge  [fontname="Helvetica", fontsize=7];',
    ]
    for prefixe, groupe in sorted(par_prefixe.items()):
        lignes.append(f'  subgraph cluster_{prefixe} {{')
        lignes.append(f'    label="{prefixe}"; color="#bdbdbd";')
        for it in groupe:
            titre = re.sub(r"\s+", " ", it.titre)[:60].replace('"', "'")
            couleur = COULEUR_STATUT.get(it.statut or "", "#455a64")
            forme = FORME_TYPE.get(it.type or "", "box")
            lignes.append(
                f'    "{it.id}" [label="{it.id}\\n{titre}", '
                f'shape={forme}, color="{couleur}", penwidth=1.6];'
            )
        lignes.append("  }")

    connus = {it.id for it in reels}
    for it in reels:
        # `justifie` n'est pas trace : c'est l'inverse de `parce-que`, deja symetrise
        for arc in ("parce-que", "ferme-la-branche", "mesure-par", "contredit"):
            tete, couleur, style = STYLE_ARC[arc]
            for cible in it.a(arc):
                if cible not in connus:
                    continue
                if arc == "parce-que":
                    lignes.append(f'  "{cible}" -> "{it.id}" [arrowhead={tete}, color="{couleur}", style={style}];')
                else:
                    lignes.append(f'  "{it.id}" -> "{cible}" [arrowhead={tete}, color="{couleur}", style={style}, label="{arc}"];')
    lignes.append("}")
    sortie.write_text("\n".join(lignes), encoding="utf-8")


def ecrire_mermaid(items: list[Item], prefixe: str, sortie: Path) -> int:
    """Un graphe par domaine : 481 noeuds d'un coup ne se lisent pas."""
    groupe = [it for it in items if not it.reflexif and it.prefixe.split("-")[0] == prefixe]
    if not groupe:
        return 0
    connus = {it.id for it in groupe}
    lignes = ["flowchart LR"]
    for it in groupe:
        titre = re.sub(r"\s+", " ", it.titre)[:52].replace('"', "'")
        ident = it.id.replace("-", "_")
        if it.statut == "ecarte":
            lignes.append(f'  {ident}["{it.id} — {titre}"]:::ecarte')
        elif it.statut == "erreur-a-posteriori":
            lignes.append(f'  {ident}["{it.id} — {titre}"]:::renverse')
        elif it.statut == "ouvert":
            lignes.append(f'  {ident}["{it.id} — {titre}"]:::ouvert')
        else:
            lignes.append(f'  {ident}["{it.id} — {titre}"]')
    for it in groupe:
        src = it.id.replace("-", "_")
        for cible in it.a("parce-que"):
            if cible in connus:
                lignes.append(f'  {cible.replace("-", "_")} --> {src}')
        for cible in it.a("ferme-la-branche"):
            if cible in connus:
                lignes.append(f'  {src} -.->|coupe| {cible.replace("-", "_")}')
        for cible in it.a("mesure-par"):
            if cible in connus:
                lignes.append(f'  {cible.replace("-", "_")} ==>|mesure| {src}')
    lignes += [
        "  classDef ecarte fill:#ffebee,stroke:#b71c1c;",
        "  classDef renverse fill:#f3e5f5,stroke:#6a1b9a;",
        "  classDef ouvert fill:#e1f5fe,stroke:#01579b;",
    ]
    sortie.write_text("\n".join(lignes), encoding="utf-8")
    return len(groupe)


def rapport(items: list[Item], resultats: dict) -> str:
    reels = [it for it in items if not it.reflexif]
    par_statut = Counter(it.statut for it in reels)
    par_type = Counter(it.type for it in reels)
    par_dest = Counter(d for it in reels for d in it.destination)
    topo = resultats["topologie"]

    L = []
    a = L.append
    a("# Audit du corpus")
    a("")
    a("Genere par `memoire/audit_corpus.py`. Ne pas editer a la main.")
    a("")
    a("## Inventaire")
    a("")
    a(f"- **{len(items)} items** dont {len(reels)} factuels et "
      f"{len(items) - len(reels)} axes reflexifs")
    a(f"- **{sum(len(it.a(x)) for it in items for x in ARCS)} arcs** poses")
    a(f"- {len(resultats['branches'])} branches coupees documentees")
    a("")
    a("| statut | items |   | type | items |")
    a("|---|---:|---|---|---:|")
    stats = sorted(par_statut.items(), key=lambda kv: -kv[1])
    types = sorted(par_type.items(), key=lambda kv: -kv[1])
    for i in range(max(len(stats), len(types))):
        g = f"`{stats[i][0]}` | {stats[i][1]}" if i < len(stats) else " | "
        d = f"`{types[i][0]}` | {types[i][1]}" if i < len(types) else " | "
        a(f"| {g} |  | {d} |")
    a("")
    a("### Charge par destination")
    a("")
    a("| destination | items |")
    a("|---|---:|")
    for dest, n in sorted(par_dest.items(), key=lambda kv: -kv[1]):
        a(f"| `{dest}` | {n} |")
    a("")

    def bloc(titre: str, entrees: list[str], commentaire: str = "") -> None:
        a(f"## {titre} — {len(entrees)}")
        a("")
        if commentaire:
            a(commentaire)
            a("")
        if not entrees:
            a("Aucun.")
        else:
            for e in entrees:
                a(f"- {e}")
        a("")

    bloc("REGLE 1 — choix retenus sans `parce-que`",
         [f"`{it.id}` ({it.fichier}) — {re.sub(r'  +', ' ', it.titre)[:90]}"
          for it in resultats["regle1"]],
         "Portee : les items DECIDES (`choix`, `methode`, `organisation`, `perspective`). "
         "Un fait ne se justifie pas, il se source. Un choix retenu sans `parce-que` est, "
         "litteralement, un choix non justifie : soit on lui trouve son parent, soit on le "
         "declare `racine: true` en assumant que c'est un axiome.")

    bloc("REGLE 1 bis — axiomes declares",
         [f"`{it.id}` — {re.sub(r'  +', ' ', it.titre)[:100]}"
          for it in resultats["regle1_racines"]],
         "Ce que le stage a pose sans le deduire de rien. La liste doit rester courte : "
         "c'est la surface d'attaque du memoire.")

    bloc("REGLE 2 — branches ecartees sans `mesure-par`",
         [f"`{it.id}` ({it.fichier}) — {re.sub(r'  +', ' ', it.titre)[:90]}"
          for it in resultats["regle2"]],
         "Un ecart sans mesure est une opinion.")

    bloc("REGLE 2 bis — ecarts assumes sur argument, sans mesure",
         [f"`{it.id}` — {re.sub(r'  +', ' ', str(it.brut['sans-mesure']))[:160]}"
          for it in resultats["regle2_assumes"]],
         "Declares via `sans-mesure:`. Ce sont des positions defendables, pas des trous : "
         "chacune doit pouvoir etre soutenue a l'oral telle quelle.")

    bloc("REGLE 3 — verdicts renverses sans antecedent",
         [f"`{it.id}` — {re.sub(r'  +', ' ', it.titre)[:90]}" for it in resultats["regle3"]])

    bloc("REGLE 3 bis — verdict anterieur donne en clair",
         [f"`{it.id}` — {re.sub(r'  +', ' ', str(it.brut['verdict-anterieur']))[:150]}"
          for it in resultats["regle3_clair"]],
         "La croyance renversee n'avait pas d'id parce qu'on ne l'avait jamais ecrite. "
         "C'est le cas normal, et c'est le materiau du chapitre sur la methode.")

    bloc("Forme", resultats["forme"])
    bloc("Arcs pendants", resultats["pendants"],
         "Un arc qui pointe vers un id inexistant. C'est toujours une faute : soit la cible "
         "reste a ecrire, soit la reference est fausse.")

    a(f"## Symetrie parce-que / justifie — {len(resultats['asymetries'])} arcs completes")
    a("")
    a("**Ce n'est pas une liste de defauts.** Le corpus est saisi en ne posant qu'un sens de "
      "l'arc (celui qui vient naturellement a l'ecriture) ; le script pose l'autre. Les .yaml "
      "restent volontairement asymetriques — les tenir a jour dans les deux sens a la main "
      "produirait des incoherences sans rien ajouter, puisque l'information est la meme.")
    a("")

    bloc("Macros de chiffre inconnues", resultats["chiffres_pbs"])

    cov = resultats["couverture"]
    a(f"## Couverture des chapitres — {len(cov['manquant'])} manquants")
    a("")
    a(f"Items destines a un chapitre : {len(cov['couvert']) + len(cov['manquant'])} "
      f"controlables (ils portent un chiffre), {len(cov['sans_chiffre'])} incontrolables "
      f"automatiquement. **{len(cov['couvert'])} couverts.**")
    a("")
    if cov["manquant"]:
        a("| item | chapitre | titre |")
        a("|---|---|---|")
        for it, ch in cov["manquant"]:
            a(f"| `{it.id}` | {ch} | {re.sub(r'\\s+', ' ', it.titre)[:70]} |")
    a("")

    a(f"## Macros definies et jamais citees — {len(resultats['orphelines'])}")
    a("")
    a("Chaque macro non citee est un chiffre calcule pour rien, ou une place qui reste "
      "a ecrire dans le .tex.")
    a("")
    a(", ".join(f"`\\{m}`" for m in resultats["orphelines"]) or "Aucune.")
    a("")

    a("## Topologie")
    a("")
    a(f"- {len(topo['racines'])} racines (aucun `parce-que`)")
    a(f"- {len(topo['feuilles'])} feuilles (aucun `justifie`)")
    a(f"- {len(topo['isoles'])} items isoles (aucun arc, dans aucun sens)")
    a(f"- {len(topo['cycles'])} cycles" + (f" : {', '.join(topo['cycles'])}" if topo["cycles"] else ""))
    a("")
    a("Les douze chaines les plus profondes — ce sont les fils narratifs du memoire :")
    a("")
    a("| item | profondeur | titre |")
    a("|---|---:|---|")
    for it in topo["plus_profonds"]:
        a(f"| `{it.id}` | {topo['profondeur'].get(it.id, 0)} | "
          f"{re.sub(r'\\s+', ' ', it.titre)[:70]} |")
    a("")

    a(f"## Les branches coupees — {len(resultats['branches'])}")
    a("")
    a("C'est le tableau de la demonstration : ce qui a ete retenu, ce que cela a ferme, "
      "et ce qui a tranche.")
    a("")
    a("| retenu | ferme | mesure par |")
    a("|---|---|---|")
    for ligne in resultats["branches"]:
        b = ligne["branche"]
        nom_b = f"`{ligne['branche_id']}` {re.sub(r'\\s+', ' ', b.titre)[:48]}" if b else f"`{ligne['branche_id']}` (introuvable)"
        mes = ", ".join(f"`{m}`" for m in ligne["mesure_ids"]) or "**aucune**"
        a(f"| `{ligne['retenu'].id}` {re.sub(r'\\s+', ' ', ligne['retenu'].titre)[:48]} | {nom_b} | {mes} |")
    a("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", action="store_true", help="ecrit _graphe.dot et _graphe-*.mmd")
    ap.add_argument("--strict", action="store_true", help="sortie non nulle si une regle casse")
    args = ap.parse_args()

    items, erreurs_chargement = charger()
    forme = erreurs_chargement + valider_forme(items)
    pendants, asymetries = valider_arcs(items)
    connues = macros_connues()
    regle1, regle1_racines = regle_1_choix_justifies(items)
    regle2, regle2_assumes = regle_2_ecarts_mesures(items)
    regle3, regle3_clair = regle_3_verdicts_renverses(items)

    resultats = {
        "forme": forme,
        "pendants": pendants,
        "asymetries": asymetries,
        "regle1": regle1,
        "regle1_racines": regle1_racines,
        "regle2": regle2,
        "regle2_assumes": regle2_assumes,
        "regle3": regle3,
        "regle3_clair": regle3_clair,
        "chiffres_pbs": valider_chiffres(items, connues),
        "couverture": audit_couverture(items),
        "orphelines": macros_orphelines(connues),
        "topologie": topologie(items),
        "branches": branches(items),
    }

    texte = rapport(items, resultats)
    (CORPUS / "_audit.md").write_text(texte, encoding="utf-8")

    reels = [it for it in items if not it.reflexif]
    print(f"corpus      : {len(items)} items ({len(reels)} factuels), "
          f"{sum(len(it.a(x)) for it in items for x in ARCS)} arcs")
    print(f"regle 1     : {len(resultats['regle1'])} choix retenus sans parce-que")
    print(f"regle 2     : {len(resultats['regle2'])} ecarts sans mesure "
          f"({len(resultats['regle2_assumes'])} assumes sur argument)")
    print(f"regle 3     : {len(resultats['regle3'])} verdicts sans antecedent "
          f"({len(resultats['regle3_clair'])} donnes en clair)")
    print(f"forme       : {len(forme)} anomalies")
    print(f"arcs        : {len(pendants)} pendants, {len(asymetries)} asymetries")
    print(f"chiffres    : {len(resultats['chiffres_pbs'])} macros inconnues, "
          f"{len(resultats['orphelines'])} definies jamais citees")
    print(f"couverture  : {len(resultats['couverture']['manquant'])} items destines a un "
          f"chapitre et absents du .tex")
    print(f"branches    : {len(resultats['branches'])} coupees")
    print(f"rapport     : {(CORPUS / '_audit.md').relative_to(RACINE.parent)}")

    if args.graph:
        ecrire_dot(items, CORPUS / "_graphe.dot")
        total = 0
        for prefixe in sorted({it.prefixe.split("-")[0] for it in items if not it.reflexif}):
            n = ecrire_mermaid(items, prefixe, CORPUS / f"_graphe-{prefixe}.mmd")
            total += n
        print(f"graphe      : _graphe.dot + {total} noeuds en mermaid par domaine")

    if args.strict:
        dur = (forme + pendants + resultats["chiffres_pbs"]
               + [it.id for it in resultats["regle2"]] + [it.id for it in resultats["regle3"]])
        return 1 if dur else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
