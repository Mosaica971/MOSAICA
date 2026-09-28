"""Exporte `slides.html` en PowerPoint (.pptx) éditable.

POURQUOI CE FORMAT. Le .pptx s'ouvre nativement dans LibreOffice Impress, PowerPoint et Google
Slides, et c'est le seul format de présentation que Canva sache importer. Un .odp ne serait lu
que par Impress.

POURQUOI UN PARSEUR PLUTÔT QU'UNE RECOPIE. Le contenu vit dans `slides.html`. Le retaper ici
créerait deux sources de vérité qui divergeraient à la première correction. Ce module lit donc
le HTML — dont il connaît les classes, puisque c'est le même auteur — et en tire une structure
neutre, puis la compose en diapositives.

CE QUI EST ÉDITABLE DANS LA SORTIE. Tout le texte : titres, paragraphes, listes, tableaux,
grands chiffres, bandeau de source. Les visuels (carte, graphiques) sont des images PNG
regénérables par ce même script — les modifier suppose de corriger la source, pas la diapo.

LES POLICES. Le fichier nomme Archivo, Newsreader et IBM Plex Mono, qui sont les polices du
support HTML. Elles sont gratuites (Google Fonts) ; installées sur le poste, la diapo est
identique au HTML. Absentes, LibreOffice substitue sans casser la mise en page.

Usage :
    .venv/Scripts/python memoire/soutenance/build_pptx.py
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR  # noqa: E402
from pptx.util import Emu, Inches, Pt  # noqa: E402

HERE = Path(__file__).resolve().parent
DECK = HERE / "slides.html"
OUT = HERE / "soutenance.pptx"
IMG = HERE / "img"

# Palette claire du support HTML.
INK = RGBColor(0x18, 0x1C, 0x19)
MUTED = RGBColor(0x5C, 0x64, 0x5E)
FAINT = RGBColor(0x8A, 0x92, 0x8B)
LINE = RGBColor(0xD6, 0xDA, 0xD3)
RULE = RGBColor(0xBF, 0xC6, 0xBD)
GROUND = RGBColor(0xF4, 0xF5, 0xF1)
PANEL = RGBColor(0xFB, 0xFC, 0xF9)
GOLD = RGBColor(0xA8, 0x76, 0x1C)
TEAL = RGBColor(0x22, 0x66, 0x5C)
ALERT = RGBColor(0xB0, 0x3A, 0x2E)

F_TITLE = "Archivo"
F_BODY = "Newsreader"
F_MONO = "IBM Plex Mono"

W, H = 13.333, 7.5
MARGIN = 0.62
BODY_TOP = 1.98
BODY_BOTTOM = 6.62

# Les visuels, reconnus par l'attribut aria-label du <svg> — donc par leur sens, pas par leur
# position, qui bougera au prochain remaniement du deck.
CHART_BY_LABEL = [
    ("risque chlordécone", "carte"),
    ("Front marge", "front"),
    ("Répartition de la surface", "assolement"),
    ("Origine des légumes", "imports"),
    ("chambres d'agriculture", "syndicats"),
    ("Frise chronologique", "frise"),
]

# La frise : (année, libellé, piste). La piste décide de la couleur et du côté de l'axe —
# alternance stricte haut/bas, qui n'est lisible que parce que l'ordre est chronologique.
FRISE = [
    ("1946", "Départementalisation", "bas"),
    ("1968", "Quotas sucriers\neuropéens", "haut"),
    ("1981", "Réforme foncière :\n60 % de canne imposés", "bas"),
    ("1989", "POSEIDOM : régime\ndérogatoire outre-mer", "haut"),
    ("1990-93", "Interdit en France,\ntoléré aux Antilles", "cld"),
    ("2006", "Réforme du sucre :\nprix garanti abaissé", "haut"),
    ("2009", "Grève générale,\n44 jours, vie chère", "bas"),
    ("2017", "Fin des quotas\nsucriers européens", "haut"),
    ("2019", "Responsabilité de\nl'État reconnue", "cld"),
    ("2023", "Convention canne,\naide 447 €/ha", "haut"),
    ("2025", "Chambres d'agriculture :\nle MODEF en tête", "bas"),
    ("2027", "Échéances : octroi de\nmer, chlordécone IV", "avenir"),
]


# ──────────────────────────── lecture du HTML ────────────────────────────

def _cls(attrs: dict) -> str:
    return attrs.get("class", "")


# Balises orphelines : html.parser ne leur envoie jamais de handle_endtag, donc les empiler
# décalerait la pile pour tout le reste du document — et avec elle la lecture des classes.
VOID = {"br", "img", "hr", "input", "meta", "link", "source", "col", "area"}


class DeckParser(HTMLParser):
    """Transforme slides.html en une liste de diapositives structurées."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides: list[dict] = []
        self.cur: dict | None = None
        self.zone: str | None = None          # rail | body | src
        self.stack: list[tuple[str, str]] = []
        self.buf: list[str] = []
        self.block: dict | None = None
        self.svg_depth = 0
        self.table: dict | None = None
        self.row: list[str] | None = None
        self.in_head = False

    # -- utilitaires ------------------------------------------------------
    def _text(self) -> str:
        t = "".join(self.buf)
        t = re.sub(r"\s+", " ", t).strip()
        self.buf = []
        return t

    def _push(self, kind: str, **kw) -> None:
        text = self._text()
        if kind in {"figs", "table", "chart"} or text:
            self.cur["blocks"].append({"kind": kind, "text": text, **kw})

    def _has(self, name: str) -> bool:
        return any(name in c for _, c in self.stack)

    # -- balises ----------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        c = _cls(a)

        if self.svg_depth:
            if tag == "svg":
                self.svg_depth += 1
            return

        if tag == "svg":
            label = a.get("aria-label", "")
            kind = next((k for needle, k in CHART_BY_LABEL if needle in label), None)
            if kind and self.cur is not None:
                self.cur["blocks"].append({"kind": "chart", "text": "", "chart": kind})
            self.svg_depth = 1
            return

        if tag == "section" and "slide" in c:
            self.cur = {"sec": a.get("data-sec", ""), "sub": "", "title": "",
                        "blocks": [], "src": "", "divider": "divider" in c}
            self.slides.append(self.cur)
            self.buf = []
        if self.cur is None:
            return

        if tag == "br":
            self.buf.append(" ")
            return
        if tag == "sup":
            self.buf.append("^")
            return
        if tag in VOID:
            return

        self.stack.append((tag, c))

        if tag == "div" and "rail" in c:
            self.zone = "rail"; self.buf = []
        elif tag == "div" and c.strip().startswith("body"):
            self.zone = "body"; self.buf = []
        elif tag == "div" and "src" in c:
            self.zone = "src"; self.buf = []

        if self.zone != "body":
            return

        if tag in {"h1", "h2", "h3", "p", "li"}:
            self.buf = []
        elif tag == "div" and "figs" in c:
            self.block = {"kind": "figs", "items": []}
        elif tag == "div" and "fig" in c and self.block and self.block["kind"] == "figs":
            self.block["items"].append({"v": "", "l": "", "tone": ""})
        elif tag == "span" and self.block and self.block["kind"] == "figs":
            self.buf = []
        elif tag == "ul" and "pts" in c:
            self.block = {"kind": "bullets", "items": []}
        elif tag == "div" and "note" in c:
            self.buf = []
        elif tag == "div" and "thread" in c:
            self.buf = []
        elif tag == "div" and "kicker" in c:
            self.buf = []
        elif tag == "table":
            self.table = {"kind": "table", "head": [], "rows": []}
        elif tag == "tr":
            self.row = []
        elif tag in {"th", "td"}:
            self.buf = []
        elif tag == "thead":
            self.in_head = True
        elif tag == "caption":
            self.buf = []

    def handle_endtag(self, tag):
        if self.svg_depth:
            if tag == "svg":
                self.svg_depth -= 1
            return
        if self.cur is None or tag in VOID or tag == "sup":
            return
        if tag == "caption":
            self.buf = []
            if self.stack:
                self.stack.pop()
            return

        if self.zone == "body":
            if tag in {"h1", "h2"}:
                t = self._text()
                if not self.cur["title"]:
                    self.cur["title"] = t
                elif t:
                    self.cur["blocks"].append({"kind": "h3", "text": t})
            elif tag == "h3":
                self._push("h3")
            elif tag == "p":
                lead = any("lead" in c for t2, c in self.stack if t2 == "p")
                self._push("lead" if lead else "text")
            elif tag == "li":
                if self.block and self.block["kind"] == "bullets":
                    t = self._text()
                    if t:
                        self.block["items"].append(t)
            elif tag == "ul" and self.block and self.block["kind"] == "bullets":
                if self.block["items"]:
                    self.cur["blocks"].append(self.block)
                self.block = None
            elif tag == "span" and self.block and self.block["kind"] == "figs":
                t = self._text()
                cls = next((c for tg, c in reversed(self.stack) if tg == "span"), "")
                if self.block["items"]:
                    it = self.block["items"][-1]
                    if "v" in cls.split():
                        it["v"] = t
                        it["tone"] = ("gold" if "gold" in cls else
                                      "teal" if "teal" in cls else
                                      "red" if "red" in cls else "")
                    elif "l" in cls.split():
                        it["l"] = t
            elif tag == "div":
                cls = next((c for tg, c in reversed(self.stack) if tg == "div"), "")
                if "figs" in cls and self.block and self.block["kind"] == "figs":
                    if self.block["items"]:
                        self.cur["blocks"].append(self.block)
                    self.block = None
                elif "note" in cls:
                    self._push("note", warn="warn" in cls)
                elif "thread" in cls:
                    self._push("thread")
                elif "kicker" in cls:
                    self._push("kicker")
            elif tag in {"th", "td"} and self.row is not None:
                self.row.append(self._text())
            elif tag == "tr" and self.table is not None and self.row is not None:
                (self.table["head"] if self.in_head else self.table["rows"]).append(self.row)
                self.row = None
            elif tag == "thead":
                self.in_head = False
            elif tag == "table" and self.table is not None:
                if self.table["head"] or self.table["rows"]:
                    self.cur["blocks"].append(self.table)
                self.table = None

        elif self.zone == "rail" and tag == "div":
            spans = [s for s in re.split(r"\s{2,}", self._text()) if s]
            if spans:
                self.cur["sub"] = spans[-1] if len(spans) > 1 else ""
            self.zone = None
        elif self.zone == "src" and tag == "div":
            self.cur["src"] = self._text()
            self.zone = None

        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.svg_depth or self.cur is None:
            return
        if self.zone == "rail":
            t = data.strip()
            if t:
                self.buf.append(t + "  ")
            return
        self.buf.append(data)


def parse_deck() -> list[dict]:
    p = DeckParser()
    p.feed(DECK.read_text(encoding="utf-8"))
    for s in p.slides:
        if not s["sub"]:
            s["sub"] = s["sec"]
    return p.slides


# ──────────────────────────── visuels ────────────────────────────

def render_charts(scale: int = 2) -> dict[str, Path]:
    """Les trois graphiques du support, redessinés en PNG avec la même palette."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    IMG.mkdir(exist_ok=True)
    gold, teal, alert = "#A8761C", "#22665C", "#B03A2E"
    grey, ink, muted = "#BFC6BD", "#181C19", "#5C645E"
    out: dict[str, Path] = {}

    def finish(fig, name):
        path = IMG / f"{name}.png"
        fig.savefig(path, dpi=100 * scale, facecolor="#F4F5F1", bbox_inches="tight")
        plt.close(fig)
        out[name] = path

    # --- front marge x enveloppe publique
    x = [35.9, 43.0, 50.3, 57.4, 64.6, 72.0, 90.0]
    brute = [112.93, 110.62, 107.38, 104.23, 101.15, 98.35, 98.35]
    obj = [74.36, 76.84, 77.96, 79.18, 80.62, 81.04, 81.04]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    fig.patch.set_facecolor("#F4F5F1"); ax.set_facecolor("#F4F5F1")
    ax.plot(x, brute, "-o", color=gold, lw=2.5, ms=6, label="Marge brute du territoire")
    ax.plot(x, obj, "-o", color=teal, lw=2.5, ms=6, label="Objectif — marge ajustée du risque")
    ax.annotate("112,9", (x[0], brute[0]), textcoords="offset points", xytext=(6, 7),
                color=ink, fontsize=10)
    ax.annotate("98,4", (x[-1], brute[-1]), textcoords="offset points", xytext=(-4, 8),
                ha="right", color=ink, fontsize=10)
    ax.annotate("74,4", (x[0], obj[0]), textcoords="offset points", xytext=(9, 4),
                color=ink, fontsize=10)
    ax.annotate("81,0", (x[-1], obj[-1]), textcoords="offset points", xytext=(-4, -14),
                ha="right", color=ink, fontsize=10)
    ax.set_xlabel("Plafond de l'enveloppe publique de subventions (M€)", fontsize=9, color=muted)
    ax.set_ylabel("M€", fontsize=9, color=muted)
    ax.grid(axis="y", color=grey, lw=.6, ls=(0, (2, 4)))
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=muted, labelsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=muted, loc="center right")
    finish(fig, "front")

    # --- assolement
    labels = ["Canne à sucre", "Prairie", "Banane", "Vivrier et autres"]
    vals = [12813, 6109, 1921, 2735]
    cols = [gold, teal, "#C9DDD7", grey]
    fig, ax = plt.subplots(figsize=(8.2, 3.2))
    fig.patch.set_facecolor("#F4F5F1"); ax.set_facecolor("#F4F5F1")
    y = range(len(vals))
    ax.barh(list(y), vals, color=cols, height=.62)
    ax.invert_yaxis()
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=10, color=ink)
    for i, v in enumerate(vals):
        ax.text(v + 220, i, f"{v:,}".replace(",", " "), va="center", fontsize=10, color=ink)
    ax.set_xlim(0, 15200)
    ax.set_xlabel("hectares cultivés, sur 23 578 au total", fontsize=9, color=muted)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    finish(fig, "assolement")

    # --- origine des légumes importés
    fig, ax = plt.subplots(figsize=(8.2, 2.6))
    fig.patch.set_facecolor("#F4F5F1"); ax.set_facecolor("#F4F5F1")
    lab = ["Europe", "Autres origines", "Caraïbe"]
    val = [79, 13, 8]
    ax.barh([0, 1, 2], val, color=[teal, grey, gold], height=.6)
    ax.invert_yaxis()
    ax.set_yticks([0, 1, 2]); ax.set_yticklabels(lab, fontsize=10, color=ink)
    for i, v in enumerate(val):
        ax.text(v + 1.4, i, f"{v} %", va="center", fontsize=11, color=ink)
    ax.set_xlim(0, 95); ax.set_xticks([])
    ax.set_xlabel("origine des légumes importés", fontsize=9, color=muted)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    finish(fig, "imports")

    # --- chambres d'agriculture
    org = ["MODEF", "JA-FNSEA", "Confédération\npaysanne", "Coordination\nrurale", "FDSEA"]
    gp = [30.76, 25.14, 23.88, 11.89, 8.33]
    fr = [1.48, 46.70, 20.49, 29.85, None]
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    fig.patch.set_facecolor("#F4F5F1"); ax.set_facecolor("#F4F5F1")
    import numpy as np
    idx = np.arange(len(org))
    ax.bar(idx - .19, gp, .36, color=gold, label="Guadeloupe")
    ax.bar(idx + .19, [v if v is not None else 0 for v in fr], .36, color=teal,
           label="France entière")
    for i, v in enumerate(gp):
        ax.text(i - .19, v + 1, f"{v:.1f}".replace(".", ","), ha="center", fontsize=9, color=ink)
    for i, v in enumerate(fr):
        if v is None:
            ax.text(i + .19, 1.2, "—", ha="center", fontsize=10, color=muted)
        else:
            ax.text(i + .19, v + 1, f"{v:.1f}".replace(".", ","), ha="center", fontsize=9, color=ink)
    ax.set_xticks(idx); ax.set_xticklabels(org, fontsize=9, color=ink)
    ax.set_ylabel("% des suffrages, premier collège", fontsize=9, color=muted)
    ax.set_ylim(0, 52)
    ax.grid(axis="y", color=grey, lw=.6, ls=(0, (2, 4)))
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=muted, labelsize=9, length=0)
    ax.legend(frameon=False, fontsize=9, labelcolor=muted)
    finish(fig, "syndicats")

    # --- frise chronologique
    fig, ax = plt.subplots(figsize=(13.2, 3.9))
    fig.patch.set_facecolor("#F4F5F1"); ax.set_facecolor("#F4F5F1")
    colors = {"haut": gold, "bas": teal, "cld": alert, "avenir": grey}
    ax.axhline(0, color=grey, lw=1.4, zorder=1)
    for i, (year, label, track) in enumerate(FRISE):
        x = i
        col = colors[track]
        up = track in ("haut", "avenir")
        ax.plot([x, x], [0, 0.22 if up else -0.22], color=col, lw=1.4,
                ls=":" if track == "avenir" else "-", zorder=2)
        ax.scatter([x], [0], s=70, color="none" if track == "avenir" else col,
                   edgecolor=col, linewidths=1.6, zorder=3)
        ax.text(x, 0.30 if up else -0.30, year, ha="center",
                va="bottom" if up else "top", fontsize=13, fontweight="bold", color=col)
        ax.text(x, 0.52 if up else -0.52, label, ha="center",
                va="bottom" if up else "top", fontsize=8.5, color=ink, linespacing=1.5)
    ax.text(7, -0.13, "année des données du modèle", ha="center", va="top",
            fontsize=7.5, color=muted)
    ax.set_xlim(-0.7, len(FRISE) - 0.3)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    for lab, col, xpos in (("Sucre, filières et Europe", gold, 0.0),
                           ("Territoire et société", teal, 3.4),
                           ("Chlordécone", alert, 6.2)):
        ax.plot([xpos, xpos + 0.22], [1.08, 1.08], color=col, lw=3)
        ax.text(xpos + 0.32, 1.08, lab, fontsize=8, color=muted, va="center")
    finish(fig, "frise")

    return out


def render_map(scale: int = 2) -> Path:
    import clement.soutenance.build_carte_chlordecone as carte
    IMG.mkdir(exist_ok=True)
    parc, polygons = carte.load()
    pts, geo = carte.project(polygons)
    coast = carte.coastline(geo)
    carte.preview(parc, pts, geo, coast)
    src = HERE / "carte-preview.png"
    dst = IMG / "carte.png"
    dst.write_bytes(src.read_bytes())
    return dst


# ──────────────────────────── composition ────────────────────────────

def tb(slide, x, y, w, h):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    # La hauteur déclarée d'une zone de texte ne borne pas le rendu, mais elle est ce qu'un
    # contrôle géométrique lit : la caler sur l'avance réelle évite de fausses alertes de
    # chevauchement — et rend le fichier plus propre à retoucher à la main.
    tf._box = box
    return tf


def fit(tf, h):
    """Ajuste la hauteur déclarée de la zone de texte à l'avance réellement consommée."""
    tf._box.height = Inches(max(h, 0.18))


def para(tf, text, size, color, font=F_BODY, bold=False, italic=False,
         space_before=0, space_after=6, first=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.name = font
    r.font.bold = bold
    r.font.italic = italic
    return p


def hline(slide, x, y, w, color=LINE):
    from pptx.enum.shapes import MSO_SHAPE
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Emu(9525))
    s.fill.solid(); s.fill.fore_color.rgb = color
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def build(slides_data, charts, map_png) -> None:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    main_total = sum(1 for s in slides_data if s["sec"] != "Réserve")
    main_n = res_n = 0

    for sd in slides_data:
        slide = prs.slides.add_slide(blank)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = GROUND

        # — bandeau
        if sd["sec"] == "Réserve":
            res_n += 1
            num = f"RÉSERVE R{res_n}"
        else:
            main_n += 1
            num = f"{main_n:02d} / {main_total}"
        rail = tb(slide, MARGIN, 0.34, W - 2 * MARGIN, 0.3)
        p = rail.paragraphs[0]
        head = sd["sec"].upper()
        if sd["sub"] and sd["sub"].upper() != head:
            head += "   ·   " + sd["sub"].upper()
        r = p.add_run(); r.text = head
        r.font.size = Pt(10.5); r.font.color.rgb = MUTED; r.font.name = F_MONO
        rnum = tb(slide, W - MARGIN - 2.6, 0.34, 2.6, 0.3)
        pn = rnum.paragraphs[0]; pn.alignment = PP_ALIGN.RIGHT
        rr = pn.add_run(); rr.text = num
        rr.font.size = Pt(10.5); rr.font.color.rgb = FAINT; rr.font.name = F_MONO
        hline(slide, MARGIN, 0.68, W - 2 * MARGIN)

        # — titre
        title_size = 38 if sd["divider"] else 30
        ttf = tb(slide, MARGIN, 0.92, W - 2 * MARGIN, 1.0)
        para(ttf, sd["title"], title_size, INK, F_TITLE, bold=True, first=True, space_after=0)

        # — visuels
        blocks = sd["blocks"]
        chart = next((b for b in blocks if b["kind"] == "chart"), None)
        tables = [b for b in blocks if b["kind"] == "table"]
        text_blocks = [b for b in blocks if b["kind"] not in {"chart", "table"}]

        # La carte et la frise sont larges : elles se posent SOUS le texte, pleine page. Les
        # autres graphiques tiennent dans la colonne de droite, et les tableaux sous le texte.
        # Superposer un visuel au texte était le défaut de la première version.
        wide = chart is not None and chart["chart"] in {"carte", "frise"}
        col_w = (5.35 if (chart is not None and not wide) else min(W - 2 * MARGIN, 11.4))
        y = BODY_TOP

        if chart is not None and not wide:
            path = charts.get(chart["chart"])
            if path and Path(path).exists():
                from PIL import Image
                iw, ih = Image.open(path).size
                box_w, box_h = W - MARGIN - (MARGIN + col_w + 0.5), BODY_BOTTOM - BODY_TOP
                sc = min(box_w / iw, box_h / ih)
                pw, ph = iw * sc, ih * sc
                slide.shapes.add_picture(
                    str(path), Inches(W - MARGIN - pw),
                    Inches(BODY_TOP + (box_h - ph) / 2), Inches(pw), Inches(ph))

        # — texte
        for b in text_blocks:
            if y > BODY_BOTTOM - 0.3:
                break
            k = b["kind"]
            if k == "figs":
                items = b["items"][:6]
                n = max(len(items), 1)
                fw = col_w / n
                for i, it in enumerate(items):
                    f = tb(slide, MARGIN + i * fw, y, fw - 0.12, 1.18)
                    tone = {"gold": GOLD, "teal": TEAL, "red": ALERT}.get(it["tone"], INK)
                    para(f, it["v"], 22 if n > 3 else 28, tone, F_TITLE, bold=True,
                         first=True, space_after=2)
                    para(f, it["l"], 9, MUTED, F_MONO, space_after=0)
                y += 1.25
                continue
            # La note a son propre encart, décalé par le filet de couleur : ne pas créer ici la
            # zone générique, sinon elle reste vide et recouvre la note.
            tf = None if k == "note" else tb(slide, MARGIN, y, col_w, 0.4)
            y0 = y
            if k == "kicker":
                para(tf, b["text"].upper(), 10, TEAL, F_MONO, bold=True, first=True)
                y += 0.30
            elif k == "h3":
                para(tf, b["text"], 15, INK, F_TITLE, bold=True, first=True)
                y += 0.36
            elif k == "lead":
                para(tf, b["text"], 17, INK, F_BODY, first=True)
                y += 0.32 + 0.23 * (len(b["text"]) // int(col_w * 12) + 1)
            elif k == "note":
                hline(slide, MARGIN, y + 0.02, 0.032, ALERT if b.get("warn") else TEAL)
                tf = tb(slide, MARGIN + 0.18, y, col_w - 0.18, 0.4)
                para(tf, b["text"], 13, MUTED, F_BODY, first=True)
                y += 0.26 + 0.19 * (len(b["text"]) // int(col_w * 15) + 1)
            elif k == "thread":
                para(tf, b["text"], 11, MUTED, F_MONO, first=True)
                y += 0.24 + 0.18 * (len(b["text"]) // int(col_w * 17) + 1)
            elif k == "bullets":
                first = True
                for it in b["items"]:
                    para(tf, "— " + it, 13.5, MUTED, F_BODY, first=first, space_after=5)
                    first = False
                    y += 0.18 + 0.20 * (len(it) // int(col_w * 15) + 1)
                y += 0.1
            else:
                para(tf, b["text"], 13.5, MUTED, F_BODY, first=True)
                y += 0.26 + 0.20 * (len(b["text"]) // int(col_w * 14) + 1)
            fit(tf, y - y0 - 0.06)

        # — tableaux, posés côte à côte sous le texte
        avail_w = (col_w if (chart is not None and not wide) else W - 2 * MARGIN)
        n_tab = max(len(tables), 1)
        tab_w = (avail_w - 0.4 * (n_tab - 1)) / n_tab
        top = max(y + 0.12, BODY_TOP)
        for ti, table in enumerate(tables):
            head = table["head"][0] if table["head"] else []
            rows = table["rows"]
            ncol = max([len(head)] + [len(r) for r in rows] or [1])
            nrow = len(rows) + (1 if head else 0)
            tx = MARGIN + ti * (tab_w + 0.4)
            tw = tab_w
            th = min(0.38 * nrow, max(BODY_BOTTOM - top, 0.8))
            shape = slide.shapes.add_table(nrow, ncol, Inches(tx), Inches(top),
                                           Inches(tw), Inches(th))
            tbl = shape.table
            tbl.first_row = bool(head)
            data = ([head] if head else []) + rows
            for ri, row in enumerate(data):
                for ci in range(ncol):
                    cell = tbl.cell(ri, ci)
                    cell.text = row[ci] if ci < len(row) else ""
                    cell.margin_left = cell.margin_right = Inches(0.06)
                    cell.margin_top = cell.margin_bottom = Inches(0.02)
                    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = PANEL if (ri and ri % 2) else GROUND
                    for p in cell.text_frame.paragraphs:
                        for r in p.runs:
                            is_head = head and ri == 0
                            r.font.size = Pt(10.5 if is_head else 12.5)
                            r.font.name = F_MONO if is_head else F_BODY
                            r.font.bold = bool(is_head)
                            r.font.color.rgb = MUTED if is_head else INK

        # — carte et frise : pleine largeur, dans la place qui reste sous le texte
        if wide:
            path = map_png if chart["chart"] == "carte" else charts.get(chart["chart"])
            if path and Path(path).exists():
                from PIL import Image
                iw, ih = Image.open(path).size
                top = max(y + 0.15, BODY_TOP)
                box_w, box_h = W - 2 * MARGIN, max(BODY_BOTTOM + 0.5 - top, 1.0)
                sc = min(box_w / iw, box_h / ih)
                pw, ph = iw * sc, ih * sc
                slide.shapes.add_picture(str(path), Inches(MARGIN + (box_w - pw) / 2),
                                         Inches(top + (box_h - ph) / 2), Inches(pw), Inches(ph))

        # — source + notes du présentateur
        if sd["src"]:
            hline(slide, MARGIN, BODY_BOTTOM + 0.22, W - 2 * MARGIN)
            stf = tb(slide, MARGIN, BODY_BOTTOM + 0.32, W - 2 * MARGIN, 0.5)
            para(stf, sd["src"], 7.5, FAINT, F_MONO, first=True)
            slide.notes_slide.notes_text_frame.text = sd["src"]

    prs.save(OUT)


def main() -> None:
    slides_data = parse_deck()
    print(f"{len(slides_data)} diapositives lues dans {DECK.name}")
    n_chart = sum(1 for s in slides_data for b in s["blocks"] if b["kind"] == "chart")
    n_table = sum(1 for s in slides_data for b in s["blocks"] if b["kind"] == "table")
    print(f"  {n_chart} visuels, {n_table} tableaux")
    vides = [i + 1 for i, s in enumerate(slides_data) if not s["title"]]
    if vides:
        print(f"  ⚠ diapositives sans titre : {vides}")

    charts = render_charts()
    print("  graphiques :", ", ".join(sorted(charts)))
    map_png = render_map()
    print("  carte :", map_png.name)

    build(slides_data, charts, map_png)
    size = OUT.stat().st_size / 1024 / 1024
    print(f"\n-> {OUT}  ({size:.1f} Mo)")


if __name__ == "__main__":
    main()
