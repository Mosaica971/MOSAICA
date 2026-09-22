"""Carte du risque chlordécone : trait de côte réel + parcelles du RPG 2017.

CE QUE LA CARTE MONTRE.
  * Le **trait de côte** de Basse-Terre, Grande-Terre et Marie-Galante, extrait de la couche
    pédologique `Pédologie_GC_MG_simplifiée` — une carte des sols couvre la terre émergée, donc
    sa frontière extérieure EST la côte. Il est obtenu en rastérisant la couche puis en
    extrayant l'isocontour de la limite terre/mer, ce qui dissout au passage les milliers de
    polygones de classes de sol.
  * Les **24 582 parcelles** du modèle que `domain/geometry` sait localiser (99,4 % des 24 734),
    agrégées en cellules de 150 m, coloriées par `RISQUE_CLD` — 1 = risque le plus élevé.

CE QU'ELLE NE MONTRE PAS, et il faut le dire avant de lire une parcelle dessus :
  * **Les Saintes, La Désirade et Petite-Terre n'ont pas de contour** : aucune couche du dépôt
    ne les couvre. Le ZNIEFF départemental n'en donne que des îlots épars (Grand Îlet, La Coche,
    Morne Frégule) — dessiner une île à partir de ça serait inventer sa forme. Elles sont donc
    posées à leurs **coordonnées réelles**, calculées par projection UTM 20N, sous forme de
    repères annotés « hors périmètre ». Le RPG 2017 n'y déclare aucune parcelle agricole.
  * `RISQUE_CLD == 5` recouvre EXACTEMENT les 5 382 parcelles de Marie-Galante (vérifié par
    tabulation croisée avec ILE). C'est un régime d'absence de donnée, pas un constat de
    non-contamination : l'île est annotée comme telle.
  * une cellule porte la classe la PLUS ÉLEVÉE qu'elle contient — convention de précaution,
    assumée, et écrite dans la légende.
  * ~1 557 parcelles sont interchangeables avec une jumelle de même commune et même surface
    (cf. `domain/geometry`). La lecture territoriale tient ; une parcelle isolée n'est pas une
    preuve.

SORTIES
  memoire/soutenance/carte-chlordecone.svg   la carte seule, autonome
  memoire/soutenance/carte-preview.png       un aperçu, pour contrôle de mise en page
et, si `--inject` est passé, le SVG est réinséré dans `slides.html` entre les marqueurs
`<!--CARTE:START-->` et `<!--CARTE:END-->`.

Usage :
    .venv/Scripts/python memoire/soutenance/build_carte_chlordecone.py [--inject] [--preview]
"""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from case_studies.guadeloupe.domain.geometry import RPG_LAYER, build_geometry_join  # noqa: E402
from core.data.readers import read_mapping_set, read_wide_table  # noqa: E402
from core.data.shapefile import read_polygons  # noqa: E402

HERE = Path(__file__).resolve().parent
PEDO_LAYER = Path("data/gis") / "04_Pédologie" / "Pédologie_GC_MG_simplifiée.shp"

CELL_M = 150.0        # côté d'une cellule de parcelles, en mètres
COAST_RES_M = 90.0    # pas de la rastérisation qui produit le trait de côte
SIMPLIFY = 1.1        # distance minimale entre deux points d'un contour, en unités de viewBox

# Rampe ordinale : jaune -> orange -> rouge, plus un gris. Validée en séparation daltonienne
# (ΔE OKLab >= 11 sur toute paire adjacente, dans les deux thèmes). L'identité n'est jamais
# portée par la seule couleur : les trois classes sont spatialement disjointes ET annotées.
RISK_STYLE = {
    1: ("risk1", "#A32018", "risque le plus élevé"),
    2: ("risk2", "#DC7522", "risque intermédiaire"),
    3: ("risk3", "#EFC33F", "risque faible"),
    4: ("base", "#96A08F", "aucun risque classé"),
}
DRAW_ORDER = [4, 3, 2, 1]  # le risque passe toujours par-dessus la trame de fond

# Zones annotées. L'ellipse est CALCULÉE depuis les parcelles que la zone sélectionne — région
# du modèle (REGION) ou île (ILE), jamais une liste de communes saisie à la main. Le texte est
# volontairement court : la carte doit se lire, pas se déchiffrer.
ZONES = [
    {"key": "sebt", "select": ("REGION", {5}), "risk": {1, 2},
     "titre": "Ceinture bananière", "detail": "Sud-Est Basse-Terre",
     "colour": 1, "side": "left", "anchor_y": 0.46},
    {"key": "sobt", "select": ("REGION", {6}), "risk": {1, 2},
     "titre": "Côte sous-le-vent", "detail": "Sud-Ouest Basse-Terre",
     "colour": 1, "side": "left", "anchor_y": 0.84},
    {"key": "ngt", "select": ("REGION", {1, 2, 3}), "risk": {3},
     "titre": "Grande-Terre", "detail": "risque faible et diffus",
     "colour": 3, "side": "right", "anchor_y": 0.12, "diffuse": True},
    {"key": "mg", "select": ("ILE", {3}), "risk": None,
     "titre": "Marie-Galante", "detail": "non classée",
     "colour": 4, "side": "right", "anchor_y": 0.74, "diffuse": True},
]

# Nom d'île posé au-dessus ou au-dessous de sa propre boîte englobante, donc jamais sur la donnée.
ISLANDS = [(1, "BASSE-TERRE", "below"), (2, "GRANDE-TERRE", "above")]

# Les trois dépendances, en degrés décimaux. Aucune couche du dépôt ne porte leur contour ;
# elles sont projetées et posées en repère, explicitement hors périmètre du modèle.
DEPENDANCES = [
    ("Les Saintes", 15.8700, -61.6000),
    ("Petite-Terre", 16.1720, -61.1080),
    ("La Désirade", 16.3250, -61.0750),
]

# Géométrie de la planche, en unités de viewBox.
VB_W, VB_H = 1300.0, 960.0
MAP_X, MAP_Y, MAP_W = 252.0, 40.0, 760.0
LEGEND_Y = 800.0


# ─────────────────────────── projection ───────────────────────────

def utm20n(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 -> UTM 20N (mètres). Transverse de Mercator, série usuelle au 6e ordre.
    Contrôlé contre les emprises ZNIEFF de La Désirade et du Grand Îlet des Saintes."""
    a, f, k0, lon0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(-63.0)
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    phi, lam = math.radians(lat), math.radians(lon)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = ep2 * math.cos(phi) ** 2
    A = (lam - lon0) * math.cos(phi)
    m = a * ((1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
             + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi)
             - (35 * e2**3 / 3072) * math.sin(6 * phi))
    x = k0 * n * (A + (1 - t + c) * A**3 / 6
                  + (5 - 18 * t + t**2 + 72 * c - 58 * ep2) * A**5 / 120) + 500000.0
    y = k0 * (m + n * math.tan(phi) * (A**2 / 2 + (5 - t + 9 * c + 4 * c**2) * A**4 / 24
              + (61 - 58 * t + t**2 + 600 * c - 330 * ep2) * A**6 / 720))
    return x, y


# ─────────────────────────── données ───────────────────────────

def load():
    parc = read_wide_table(_ROOT / "data/tables/Data_Parc_Gwad_2017.txt")
    expl = read_mapping_set(_ROOT / "data/sets/EXPL_PARC_2017.set", "farm", "plot")
    join = build_geometry_join(parc, expl.set_index("plot")["farm"], _ROOT / RPG_LAYER)
    return parc, join.polygons


def coastline(extent: dict) -> list[list[tuple[float, float]]]:
    """Trait de côte, en mètres UTM. La couche pédologique est rastérisée dans un masque
    terre/mer, puis l'isocontour 0,5 est extrait : cela dissout d'un coup les milliers de
    polygones de classes de sol, ce qu'un assemblage topologique en Python pur ne ferait pas."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.collections import PolyCollection
    from matplotlib.figure import Figure

    polys = [ring for poly in read_polygons(_ROOT / PEDO_LAYER) if poly is not None
             for ring in poly.rings if len(ring) >= 3]

    x0, x1 = extent["px0"], extent["px1"]
    y0, y1 = extent["py0"], extent["py1"]
    w = max(int((x1 - x0) / COAST_RES_M), 64)
    h = max(int((y1 - y0) / COAST_RES_M), 64)

    fig = Figure(figsize=(w / 100, h / 100), dpi=100)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_axis_off()
    ax.add_collection(PolyCollection(polys, facecolors="k", edgecolors="k", linewidths=0.6))
    canvas.draw()
    img = np.asarray(canvas.buffer_rgba())[:, :, 0]
    mask = (img < 128).astype(float)[::-1]  # remis en repère y croissant vers le nord

    import matplotlib.pyplot as plt
    tmp = plt.figure()
    cs = tmp.gca().contour(mask, levels=[0.5])
    segs = cs.allsegs[0]
    plt.close(tmp)

    out = []
    for seg in segs:
        if len(seg) < 12:          # îlots d'un ou deux pixels : du bruit de rastérisation
            continue
        out.append([(x0 + px * (x1 - x0) / (w - 1), y0 + py * (y1 - y0) / (h - 1))
                    for px, py in seg])
    return out


# ─────────────────────────── géométrie de planche ───────────────────────────

def project(polygons: dict):
    """Centroïdes UTM -> unités de viewBox, échelle égale sur les deux axes, y inversé.
    L'étendue couvre la couche pédologique ET les trois dépendances, pour que le cadre soit
    celui de l'archipel et pas seulement celui des parcelles."""
    cent = {plot: poly.centroid for plot, poly in polygons.items()}
    xs = [p[0] for p in cent.values()]
    ys = [p[1] for p in cent.values()]
    dep = [utm20n(lat, lon) for _, lat, lon in DEPENDANCES]

    # Emprise de la couche pédologique, lue dans l'en-tête du .shp (100 premiers octets).
    import struct
    with open(_ROOT / PEDO_LAYER, "rb") as fh:
        pxmin, pymin, pxmax, pymax = struct.unpack("<4d", fh.read(100)[36:68])

    pad = 500.0
    x0 = min(min(xs), pxmin, min(p[0] for p in dep)) - pad
    x1 = max(max(xs), pxmax, max(p[0] for p in dep)) + pad
    y0 = min(min(ys), pymin, min(p[1] for p in dep)) - pad
    y1 = max(max(ys), pymax, max(p[1] for p in dep)) + pad

    scale = MAP_W / (x1 - x0)
    map_h = (y1 - y0) * scale
    pts = {plot: (MAP_X + (x - x0) * scale, MAP_Y + (y1 - y) * scale)
           for plot, (x, y) in cent.items()}
    geo = {"scale": scale, "map_h": map_h, "px0": x0, "px1": x1, "py0": y0, "py1": y1}
    geo["to_vb"] = lambda x, y: (MAP_X + (x - x0) * scale, MAP_Y + (y1 - y) * scale)
    return pts, geo


def bin_cells(parc: pd.DataFrame, pts: dict, geo: dict) -> dict[tuple[int, int], int]:
    """(colonne, ligne) -> classe de risque la plus élevée présente dans la cellule."""
    px = CELL_M * geo["scale"]
    worst: dict[tuple[int, int], int] = {}
    risk = parc["RISQUE_CLD"]
    for plot, (sx, sy) in pts.items():
        key = (int((sx - MAP_X) // px), int((sy - MAP_Y) // px))
        r = min(int(risk.get(plot, 4)), 4)
        if key not in worst or r < worst[key]:
            worst[key] = r
    return worst


def zone_ellipse(parc: pd.DataFrame, pts: dict, zone: dict):
    column, values = zone["select"]
    sel = parc.index[parc[column].astype(int).isin(values)]
    if zone["risk"] is not None:
        sel = [p for p in sel if int(parc.at[p, "RISQUE_CLD"]) in zone["risk"]]
    pp = [pts[p] for p in sel if p in pts]
    if not pp:
        return None
    xs = sorted(p[0] for p in pp)
    ys = sorted(p[1] for p in pp)
    # Une zone diffuse est resserrée davantage : son ellipse ne désigne pas un foyer mais une
    # tendance, et tracée au 5e centile elle couvrirait la moitié de la mer.
    q = 0.16 if zone.get("diffuse") else 0.05
    lo, hi = int(q * len(pp)), max(int((1 - q) * len(pp)) - 1, 0)
    x0, x1 = xs[lo], xs[max(hi, lo)]
    y0, y1 = ys[lo], ys[max(hi, lo)]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return cx, cy, max((x1 - x0) / 2 + 10, 20), max((y1 - y0) / 2 + 10, 20), len(pp)


def leader(tx: float, ty: float, cx: float, cy: float, rx: float, ry: float, left: bool):
    """Ligne de rappel : on longe la marge, on coude JUSTE à l'extérieur du cadre, puis on
    rejoint le bord de l'ellipse en visant son centre. Le seul segment qui entre dans la carte
    est court et dirigé — c'est ce qui l'empêche de traverser la zone voisine."""
    x0 = tx + (176 if left else -176)
    elbow = MAP_X - 14 if left else MAP_X + MAP_W + 14
    dx, dy = elbow - cx, (ty - 5) - cy
    norm = (dx * dx / (rx * rx) + dy * dy / (ry * ry)) ** 0.5 or 1.0
    ax, ay = cx + dx / norm, cy + dy / norm
    return f"M {x0:.0f} {ty - 5:.0f} H {elbow:.0f} L {ax:.0f} {ay:.0f}", (ax, ay)


def island_labels(parc: pd.DataFrame, pts: dict):
    out = []
    for code, name, where in ISLANDS:
        pp = [pts[p] for p in parc.index[parc["ILE"].astype(int) == code] if p in pts]
        if not pp:
            continue
        xs = [p[0] for p in pp]
        ys = [p[1] for p in pp]
        cx = (min(xs) + max(xs)) / 2
        cy = max(ys) + 34 if where == "below" else min(ys) - 18
        out.append((name, cx, cy))
    return out


def simplify(path: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    out = [path[0]]
    for p in path[1:]:
        if (p[0] - out[-1][0]) ** 2 + (p[1] - out[-1][1]) ** 2 >= tol * tol:
            out.append(p)
    return out


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nb(n) -> str:
    return f"{n:,}".replace(",", " ")


# ─────────────────────────── rendu ───────────────────────────

def build_svg(parc, pts, geo, coast):
    cells = bin_cells(parc, pts, geo)
    px = CELL_M * geo["scale"]
    by_class: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for key, r in cells.items():
        by_class[r].append(key)

    counts = parc["RISQUE_CLD"].value_counts()
    surf = parc.groupby("RISQUE_CLD")["SURF_HA"].sum()

    o: list[str] = []
    a = o.append
    a(f'<svg viewBox="0 0 {VB_W:.0f} {VB_H:.0f}" role="img" class="carte-cld" '
      'aria-label="Carte du risque chlordécone sur les parcelles agricoles de Guadeloupe. '
      'Le risque de classe 1 se concentre sur le sud-est de Basse-Terre et la côte '
      "sous-le-vent, il est absent de Grande-Terre, et Marie-Galante n'est pas classée.\">")
    a('<style>'
      '.carte-cld text{font-family:var(--f-mono),monospace;fill:var(--muted)}'
      '.carte-cld .ttl{fill:var(--ink);font-weight:600;font-family:var(--f-display),sans-serif}'
      '.carte-cld .isl{fill:var(--faint);letter-spacing:.24em}'
      '.carte-cld .lead{stroke:var(--rule);stroke-width:1.1;fill:none}'
      '.carte-cld .sea{fill:none;stroke:var(--rule);stroke-width:1.3;stroke-linejoin:round}'
      '.carte-cld .land{fill:var(--panel);stroke:none}'
      '.carte-cld .base{fill:#96A08F}'
      '.carte-cld .risk1{fill:#A32018}.carte-cld .risk2{fill:#DC7522}.carte-cld .risk3{fill:#EFC33F}'
      '.carte-cld .ell1{stroke:#A32018}.carte-cld .ell3{stroke:#EFC33F}.carte-cld .ell4{stroke:var(--rule)}'
      '.carte-cld .dep{fill:none;stroke:var(--rule);stroke-width:1.4;stroke-dasharray:3 3}'
      '@media (prefers-color-scheme:dark){'
      ':root:not([data-theme="light"]) .carte-cld .base{fill:#5E6A5D}'
      ':root:not([data-theme="light"]) .carte-cld .risk1{fill:#D33B30}'
      ':root:not([data-theme="light"]) .carte-cld .risk2{fill:#F09340}'
      ':root:not([data-theme="light"]) .carte-cld .risk3{fill:#F5D05A}'
      ':root:not([data-theme="light"]) .carte-cld .ell1{stroke:#D33B30}'
      ':root:not([data-theme="light"]) .carte-cld .ell3{stroke:#F5D05A}}'
      ':root[data-theme="dark"] .carte-cld .base{fill:#5E6A5D}'
      ':root[data-theme="dark"] .carte-cld .risk1{fill:#D33B30}'
      ':root[data-theme="dark"] .carte-cld .risk2{fill:#F09340}'
      ':root[data-theme="dark"] .carte-cld .risk3{fill:#F5D05A}'
      ':root[data-theme="dark"] .carte-cld .ell1{stroke:#D33B30}'
      ':root[data-theme="dark"] .carte-cld .ell3{stroke:#F5D05A}'
      '</style>')

    # 1. la terre, puis son trait de côte
    paths = []
    for seg in coast:
        vb = simplify([geo["to_vb"](x, y) for x, y in seg], SIMPLIFY)
        if len(vb) < 8:
            continue
        paths.append("M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in vb) + " Z")
    d = " ".join(paths)
    a(f'<path class="land" d="{d}"/>')
    a(f'<path class="sea" d="{d}"/>')

    # 2. les parcelles
    side = px + 0.6
    for r in DRAW_ORDER:
        keys = by_class.get(r)
        if not keys:
            continue
        a(f'<g class="{RISK_STYLE[r][0]}">')
        for cx, cy in keys:
            a(f'<rect x="{MAP_X + cx * px:.1f}" y="{MAP_Y + cy * px:.1f}" '
              f'width="{side:.1f}" height="{side:.1f}"/>')
        a('</g>')

    # 3. dépendances — repérées, jamais dessinées
    for name, lat, lon in DEPENDANCES:
        dx, dy = geo["to_vb"](*utm20n(lat, lon))
        a(f'<circle class="dep" cx="{dx:.0f}" cy="{dy:.0f}" r="13"/>')
        a(f'<text x="{dx:.0f}" y="{dy + 30:.0f}" text-anchor="middle" font-size="12">'
          f'{esc(name)}</text>')

    for name, lx, ly in island_labels(parc, pts):
        a(f'<text class="isl" x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" '
          f'font-size="15">{esc(name)}</text>')

    # 4. zones annotées
    placed = []
    for zone in ZONES:
        ell = zone_ellipse(parc, pts, zone)
        if ell is None:
            continue
        cx, cy, rx, ry, n = ell
        a(f'<ellipse class="ell{zone["colour"]}" cx="{cx:.0f}" cy="{cy:.0f}" '
          f'rx="{rx:.0f}" ry="{ry:.0f}" fill="none" stroke-width="2.2"'
          + (' stroke-dasharray="5 5"' if zone.get("diffuse") else "") + "/>")
        left = zone["side"] == "left"
        tx = 24.0 if left else VB_W - 24.0
        ty = MAP_Y + geo["map_h"] * zone["anchor_y"]
        path, _ = leader(tx, ty, cx, cy, rx, ry, left)
        a(f'<path class="lead" d="{path}"/>')
        anchor = "start" if left else "end"
        a(f'<text class="ttl" x="{tx:.0f}" y="{ty:.0f}" text-anchor="{anchor}" '
          f'font-size="17">{esc(zone["titre"])}</text>')
        a(f'<text x="{tx:.0f}" y="{ty + 20:.0f}" text-anchor="{anchor}" '
          f'font-size="13">{esc(zone["detail"])}</text>')
        placed.append((zone["key"], tx, ty, cx, cy, n))

    # 5. échelle et nord
    bar = 10_000 * geo["scale"]
    by = MAP_Y + geo["map_h"] - 4
    a(f'<g stroke="var(--rule)" stroke-width="2.5">'
      f'<line x1="{MAP_X:.0f}" y1="{by:.0f}" x2="{MAP_X + bar:.0f}" y2="{by:.0f}"/>'
      f'<line x1="{MAP_X:.0f}" y1="{by - 4:.0f}" x2="{MAP_X:.0f}" y2="{by + 4:.0f}"/>'
      f'<line x1="{MAP_X + bar:.0f}" y1="{by - 4:.0f}" x2="{MAP_X + bar:.0f}" y2="{by + 4:.0f}"/>'
      f'</g><text x="{MAP_X + bar / 2:.0f}" y="{by - 10:.0f}" text-anchor="middle" '
      'font-size="12">10 km</text>')
    nx, ny = MAP_X + MAP_W - 14, MAP_Y + 16
    a(f'<path d="M {nx:.0f} {ny:.0f} l -6 17 l 6 -5 l 6 5 Z" fill="var(--muted)"/>'
      f'<text x="{nx:.0f}" y="{ny + 32:.0f}" text-anchor="middle" font-size="12">N</text>')

    # 6. légende
    a(f'<line x1="24" y1="{LEGEND_Y - 30:.0f}" x2="{VB_W - 24:.0f}" y2="{LEGEND_Y - 30:.0f}" '
      'stroke="var(--line)" stroke-width="1"/>')
    a(f'<text class="ttl" x="24" y="{LEGEND_Y - 8:.0f}" font-size="14">'
      'RISQUE CHLORDÉCONE PAR PARCELLE</text>')
    a(f'<text x="{VB_W - 24:.0f}" y="{LEGEND_Y - 8:.0f}" text-anchor="end" font-size="12">'
      'colonne RISQUE_CLD du jeu de données · cellules de 150 m</text>')

    col_w = (VB_W - 48) / 4
    for i, r in enumerate((1, 2, 3, 4)):
        cls, _, label = RISK_STYLE[r]
        n = int(counts.get(r, 0)) + (int(counts.get(5, 0)) if r == 4 else 0)
        s = float(surf.get(r, 0.0)) + (float(surf.get(5, 0.0)) if r == 4 else 0.0)
        lx = 24 + i * col_w
        a(f'<rect class="{cls}" x="{lx:.0f}" y="{LEGEND_Y + 8:.0f}" width="17" height="17"/>')
        a(f'<text class="ttl" x="{lx + 25:.0f}" y="{LEGEND_Y + 21:.0f}" font-size="14">'
          f'{"classe " + str(r) if r < 4 else "classes 4 et 5"}</text>')
        a(f'<text x="{lx + 25:.0f}" y="{LEGEND_Y + 39:.0f}" font-size="12.5">'
          f'{esc(label)}</text>')
        a(f'<text x="{lx + 25:.0f}" y="{LEGEND_Y + 56:.0f}" font-size="12.5">'
          f'{nb(n)} parcelles · {nb(round(s))} ha</text>')

    ly2 = LEGEND_Y + 86
    a(f'<line x1="24" y1="{ly2 + 8:.0f}" x2="52" y2="{ly2 + 8:.0f}" stroke="var(--rule)" '
      'stroke-width="1.3"/>')
    a(f'<text x="60" y="{ly2 + 12:.0f}" font-size="12.5">trait de côte, extrait de la couche '
      'pédologique</text>')
    a(f'<ellipse cx="{24 + col_w:.0f}" cy="{ly2 + 8:.0f}" rx="13" ry="8" fill="none" '
      'stroke="#A32018" stroke-width="2"/>')
    a(f'<text x="{24 + col_w + 22:.0f}" y="{ly2 + 12:.0f}" font-size="12.5">foyer de '
      'contamination</text>')
    a(f'<ellipse cx="{24 + 2 * col_w:.0f}" cy="{ly2 + 8:.0f}" rx="13" ry="8" fill="none" '
      'stroke="var(--rule)" stroke-width="2" stroke-dasharray="4 4"/>')
    a(f'<text x="{24 + 2 * col_w + 22:.0f}" y="{ly2 + 12:.0f}" font-size="12.5">zone diffuse, '
      'ou non classée</text>')
    a(f'<circle class="dep" cx="{24 + 3 * col_w:.0f}" cy="{ly2 + 8:.0f}" r="9"/>')
    a(f'<text x="{24 + 3 * col_w + 20:.0f}" y="{ly2 + 12:.0f}" font-size="12.5">dépendance, '
      'hors périmètre du modèle</text>')

    a(f'<text x="24" y="{ly2 + 38:.0f}" font-size="12">Une cellule porte la classe la plus '
      'élevée qu’elle contient. Seules les parcelles agricoles déclarées sont coloriées : '
      'forêt, massif de la Soufrière et zones urbaines restent vides.</text>')
    a("</svg>")

    return "\n".join(o), {
        "cells": len(cells),
        "coast_paths": len(paths),
        "coast_points": sum(p.count("L") for p in paths),
        "placed": placed,
        "map_h": geo["map_h"],
    }


def preview(parc, pts, geo, coast) -> None:
    """Aperçu raster de la MÊME géométrie, pour contrôler la mise en page une fois."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Ellipse

    cells = bin_cells(parc, pts, geo)
    px = CELL_M * geo["scale"]
    colours = {1: "#A32018", 2: "#DC7522", 3: "#EFC33F", 4: "#96A08F"}

    fig, ax = plt.subplots(figsize=(VB_W / 100, VB_H / 100), dpi=100)
    ax.set_xlim(0, VB_W); ax.set_ylim(VB_H, 0); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), VB_W, VB_H, color="#F4F5F1", zorder=0))
    for seg in coast:
        vb = simplify([geo["to_vb"](x, y) for x, y in seg], SIMPLIFY)
        if len(vb) < 8:
            continue
        ax.fill([p[0] for p in vb], [p[1] for p in vb], color="#FBFCF9", zorder=1)
        ax.plot([p[0] for p in vb] + [vb[0][0]], [p[1] for p in vb] + [vb[0][1]],
                color="#BFC6BD", linewidth=1.3, zorder=2)
    for r in DRAW_ORDER:
        pr = [(MAP_X + c * px, MAP_Y + w * px) for (c, w), rr in cells.items() if rr == r]
        if pr:
            ax.scatter([p[0] for p in pr], [p[1] for p in pr], s=(px * 1.25) ** 2, marker="s",
                       c=colours[r], linewidths=0, zorder=3 + (4 - r))
    for name, lat, lon in DEPENDANCES:
        dx, dy = geo["to_vb"](*utm20n(lat, lon))
        ax.add_patch(plt.Circle((dx, dy), 13, fill=False, edgecolor="#BFC6BD", linewidth=1.4,
                                linestyle="--", zorder=9))
        ax.text(dx, dy + 30, name, ha="center", fontsize=8, color="#5C645E", zorder=9)
    for name, lx, ly in island_labels(parc, pts):
        ax.text(lx, ly, name, ha="center", fontsize=9, color="#8A928B", zorder=9)
    for zone in ZONES:
        ell = zone_ellipse(parc, pts, zone)
        if ell is None:
            continue
        cx, cy, rx, ry, _ = ell
        ax.add_patch(Ellipse((cx, cy), 2 * rx, 2 * ry, fill=False, zorder=10,
                             edgecolor=colours[zone["colour"]], linewidth=2.2,
                             linestyle="--" if zone.get("diffuse") else "-"))
        left = zone["side"] == "left"
        tx = 24 if left else VB_W - 24
        ty = MAP_Y + geo["map_h"] * zone["anchor_y"]
        ha = "left" if left else "right"
        ax.text(tx, ty, zone["titre"], ha=ha, fontsize=10, weight="bold", color="#181C19", zorder=11)
        ax.text(tx, ty + 20, zone["detail"], ha=ha, fontsize=8, color="#5C645E", zorder=11)
        _, (ax_, ay_) = leader(tx, ty, cx, cy, rx, ry, left)
        elbow = MAP_X - 14 if left else MAP_X + MAP_W + 14
        ax.plot([tx + (176 if left else -176), elbow, ax_], [ty - 5, ty - 5, ay_],
                color="#BFC6BD", linewidth=1.1, zorder=10)
    ax.plot([24, VB_W - 24], [LEGEND_Y - 30] * 2, color="#D6DAD3", linewidth=1, zorder=9)
    col_w = (VB_W - 48) / 4
    for i, r in enumerate((1, 2, 3, 4)):
        lx = 24 + i * col_w
        ax.add_patch(plt.Rectangle((lx, LEGEND_Y + 8), 17, 17, color=colours[r], zorder=9))
        ax.text(lx + 25, LEGEND_Y + 21, f"classe {r}" if r < 4 else "classes 4 et 5",
                fontsize=9, weight="bold", color="#181C19", zorder=9)
        ax.text(lx + 25, LEGEND_Y + 39, RISK_STYLE[r][2], fontsize=8, color="#5C645E", zorder=9)
    out = HERE / "carte-preview.png"
    fig.savefig(out, dpi=100, facecolor="#F4F5F1")
    plt.close(fig)
    print(f"aperçu -> {out}")


def main() -> None:
    parc, polygons = load()
    pts, geo = project(polygons)
    print("projection contrôlée — La Désirade :", tuple(round(v) for v in utm20n(16.3283, -61.0417)),
          "(ZNIEFF observé x 703 223-709 179, y 1 802 997-1 806 215)")
    coast = coastline(geo)
    svg, stats = build_svg(parc, pts, geo, coast)

    (HERE / "carte-chlordecone.svg").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + svg.replace("var(--muted)", "#5C645E").replace("var(--ink)", "#181C19")
             .replace("var(--faint)", "#8A928B").replace("var(--rule)", "#BFC6BD")
             .replace("var(--line)", "#D6DAD3").replace("var(--panel)", "#FBFCF9")
             .replace("var(--f-mono),monospace", "monospace")
             .replace("var(--f-display),sans-serif", "sans-serif"),
        encoding="utf-8")

    print(f"parcelles localisées : {nb(len(pts))}")
    print(f"cellules de {CELL_M:.0f} m : {nb(stats['cells'])}")
    print(f"trait de côte : {stats['coast_paths']} contours, {nb(stats['coast_points'])} points")
    print(f"hauteur de carte : {stats['map_h']:.0f} (viewBox {VB_W:.0f}x{VB_H:.0f}), "
          f"légende à {LEGEND_Y:.0f}")
    for key, tx, ty, cx, cy, n in stats["placed"]:
        print(f"  {key:<6} texte=({tx:6.0f},{ty:6.0f})  ellipse=({cx:6.0f},{cy:6.0f})  n={n}")

    if "--preview" in sys.argv:
        preview(parc, pts, geo, coast)

    if "--inject" in sys.argv:
        deck = HERE / "slides.html"
        html = deck.read_text(encoding="utf-8")
        # La carte paraît deux fois : à l'ouverture, puis au retour en deuxième partie. Chaque
        # emplacement a sa paire de marqueurs, et chacun est réécrit en entier.
        done = 0
        for tag in ("CARTE", "CARTE2"):
            start, end = f"<!--{tag}:START-->", f"<!--{tag}:END-->"
            i, j = html.find(start), html.find(end)
            if i < 0 or j < 0:
                continue
            html = html[: i + len(start)] + "\n" + svg + "\n" + html[j:]
            done += 1
        if not done:
            raise SystemExit("aucun marqueur CARTE:START / CARTE:END dans slides.html")
        deck.write_text(html, encoding="utf-8")
        print(f"carte injectée {done}× dans {deck.name} ({nb(len(svg))} octets pièce)")


if __name__ == "__main__":
    main()
