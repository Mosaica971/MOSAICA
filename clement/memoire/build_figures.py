"""Genere les figures du memoire en PDF vectoriel, depuis les sorties de runs.

POURQUOI PAS LES PNG DE `reporting/plots.py`. Ceux-la sont faits pour le dashboard : 110 dpi,
titres francais incrustes dans l'image, palette pensee pour un ecran. Dans un document
imprime il faut du vectoriel, pas de titre (la legende LaTeX le porte, sinon le titre apparait
deux fois), une police accordee au corps de texte, et des formes de marqueur distinctes parce
qu'un memoire s'imprime souvent en noir et blanc.

    .venv/Scripts/python memoire/build_figures.py

COULEURS. Deux series, donc les slots categoriels 1 et 2 de la palette de reference : bleu
#2a78d6 et orange #eb6834. Cette paire est couverte par la validation deja calculee de la
palette (les trois premiers slots passent le controle tous-couples en mode clair, CVD dE 9,2 /
vision normale 24,0, cibles >= 8 et >= 15). La surface est ici du papier blanc au lieu de
#fcfcfb, ce qui ne peut qu'augmenter le contraste. La distinction ne repose de toute facon pas
sur la teinte seule : rond pour l'observe, carre pour le simule.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # aucun affichage : on ecrit des fichiers
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
FIGURES = Path(__file__).resolve().parent / "figures"

# --- Palette (slots 1 et 2) et encre, cf. references/palette.md --------------
OBSERVE = "#2a78d6"
SIMULE = "#eb6834"
ENCRE = "#0b0b0b"
ENCRE_SECONDAIRE = "#52514e"
MUET = "#898781"
GRILLE = "#e1e0d9"

# Les 12 groupes RPG, seule resolution a laquelle l'observe existe.
NOMS = {
    "AG": "Agrumes",
    "AN": "Ananas",
    "BA": "Banane export",
    "BC": "Banane plantain",
    "CS": "Canne à sucre",
    "IG": "Igname",
    "JA": "Jachère",
    "MA": "Maraîchage",
    "ME": "Melon",
    "PN": "Prairie",
    "VE": "Vergers",
}


def _style() -> None:
    """Accorde la figure au corps du texte : serif, corps reduit, chrome discret."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9,
        "axes.edgecolor": MUET,
        "axes.labelcolor": ENCRE,
        "text.color": ENCRE,
        "xtick.color": ENCRE_SECONDAIRE,
        "ytick.color": ENCRE,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,      # polices en TrueType : le PDF reste selectionnable
        "figure.autolayout": False,
    })


def _lire(run: str) -> list[dict]:
    chemin = OUTPUTS / run / "csv" / "calibration_pad_by_crop.csv"
    if not chemin.exists():
        raise SystemExit(f"{chemin} est absent -- lancer le run avant de tracer.")
    with chemin.open(encoding="utf8", newline="") as f:
        lignes = [r for r in csv.DictReader(f) if r["crop"] != "TOTAL"]
    return sorted(lignes, key=lambda r: float(r["observed_ha"]))


def calibration_haltere(run: str = "calib_retenu") -> Path:
    """Observe vs simule par culture, en haltere sur axe logarithmique.

    POURQUOI CETTE FORME, ET PAS LES BARRES APPARIEES DE L'ARTICLE. Les surfaces vont de
    \\SI{4}{ha} (melon simule) a \\SI{12813}{ha} (canne observee), soit plus de trois ordres de
    grandeur. Des barres lineaires ecraseraient tout sauf la canne et la prairie -- on verrait
    la dominance des deux filieres, qu'on sait deja, et rien de l'ecart de calibration, qui est
    la question. Et des barres sur axe log sont un contresens : la longueur d'une barre doit
    etre proportionnelle a la valeur depuis zero.
    L'haltere resout les deux : chaque culture est lisible quelle que soit sa taille, et la
    LONGUEUR DU SEGMENT est l'ecart -- en echelle log, un rapport, c'est-a-dire exactement ce
    que le PAD mesure. Les cultures ou le modele tombe juste apparaissent comme des points
    confondus, ce qui est le resultat qu'on veut montrer pour la canne et la prairie.
    """
    lignes = _lire(run)
    codes = [NOMS.get(r["crop"], r["crop"]) for r in lignes]
    obs = [float(r["observed_ha"]) for r in lignes]
    sim = [max(float(r["simulated_ha"]), 0.5) for r in lignes]  # garde-fou : log(0)
    y = range(len(lignes))

    fig, ax = plt.subplots(figsize=(6.0, 3.6))

    for i, (o, s) in enumerate(zip(obs, sim)):
        ax.plot([o, s], [i, i], color=MUET, linewidth=1.2, zorder=1, solid_capstyle="round")
    # Le simule est un carre EVIDE, et il est trace SOUS l'observe. La raison est le cas qui
    # compte le plus : quand le modele tombe juste -- canne, prairie -- les deux points sont
    # confondus, et un marqueur plein masquerait l'autre. On lirait une seule serie la ou le
    # resultat est qu'il y en a deux, superposees. Evide, il laisse voir le point bleu au
    # centre, et la coincidence devient visible au lieu d'etre invisible.
    # Plein / evide double aussi la distinction de teinte : le memoire peut etre imprime en
    # noir et blanc.
    ax.scatter(sim, list(y), s=42, facecolors="none", edgecolors=SIMULE, marker="s",
               linewidths=1.4, zorder=3, label="Simulé")
    ax.scatter(obs, list(y), s=22, color=OBSERVE, marker="o", zorder=4,
               label="Observé 2017")

    ax.set_xscale("log")
    ax.set_yticks(list(y))
    ax.set_yticklabels(codes)
    ax.set_xlabel("Surface (ha, échelle logarithmique)")
    ax.grid(axis="x", color=GRILLE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.spines["left"].set_color(GRILLE)
    ax.spines["bottom"].set_color(GRILLE)

    # Legende : deux series, donc elle est obligatoire. Sans cadre, elle ne concurrence pas
    # les donnees. L'ordre est force : le simule est TRACE en premier (pour passer sous
    # l'observe) mais doit se LIRE en second -- on compare le simule a l'observe, pas
    # l'inverse.
    poignees, etiquettes = ax.get_legend_handles_labels()
    ordre = [etiquettes.index("Observé 2017"), etiquettes.index("Simulé")]
    ax.legend([poignees[i] for i in ordre], [etiquettes[i] for i in ordre],
              loc="lower right", frameon=False, handletextpad=0.4, borderpad=0.2)

    fig.tight_layout(pad=0.4)
    FIGURES.mkdir(exist_ok=True)
    cible = FIGURES / "calibration-observe-simule.pdf"
    fig.savefig(cible, bbox_inches="tight", transparent=True)
    plt.close(fig)
    return cible


def main() -> int:
    _style()
    for cible in (calibration_haltere(),):
        print(f"{cible.relative_to(ROOT)} ecrit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
