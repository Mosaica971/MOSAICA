"""Draw the parcel map: which crop sits on which piece of land, observed and simulated.

Pure and Streamlit-free, like comparison.py and prospective.py. Geometry comes from
domain/geometry.build_geometry_join; colours come from the crop families so that the two maps
of a run are readable side by side -- the same crop must be the same colour on both, or the
comparison is worthless.

Coordinates are the file's own UTM 20N metres, drawn with an equal aspect ratio. No
reprojection: at this extent the projection is already a faithful map.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

from case_studies.guadeloupe.domain.crop_families import base_group_for
from case_studies.guadeloupe.domain.crop_labels import label_for
from core.data.shapefile import Polygon

# One fixed colour per observed RPG group. Fixed rather than generated so a crop keeps its
# colour between the observed and the simulated map, and between runs.
GROUP_COLORS: dict[str, str] = {
    "CS": "#8c6d31",   # canne a sucre
    "BA": "#f4d35e",   # banane export
    "BC": "#e8871a",   # banane plantain
    "MA": "#4daf4a",   # maraichage
    "PN": "#a6d854",   # prairies
    "JA": "#d9d9d9",   # jachere
    "IG": "#984ea3",   # igname
    "AN": "#e41a1c",   # ananas
    "ME": "#66c2a5",   # melon
    "VE": "#377eb8",   # vergers
    "AG": "#1f78b4",   # agrumes
    "NC": "#f0f0f0",   # non cultive
}
_UNKNOWN_COLOR = "#bdbdbd"


def group_color(crop: str) -> str:
    try:
        return GROUP_COLORS.get(base_group_for(crop), _UNKNOWN_COLOR)
    except KeyError:
        return _UNKNOWN_COLOR


def build_map_figure(
    polygons: dict[str, Polygon],
    allocation: dict[str, str],
    *,
    title: str,
    bounds: tuple[float, float, float, float] | None = None,
    show_legend: bool = True,
    edge_width: float = 0.0,
) -> "plt.Figure":
    """One map: every located plot filled with its crop's family colour.

    `bounds` fixes the extent so two maps of the same run can be compared without the eye
    having to correct for a different frame -- pass shared_bounds() for that. Plots present
    in `polygons` but absent from `allocation` are drawn in the "non cultivated" grey rather
    than omitted: a hole in the map would read as missing data when it means unused land.
    """
    fig, ax = plt.subplots(figsize=_figsize(bounds or _bounds_of(polygons)))
    vertices: list[list[tuple[float, float]]] = []
    colors: list[str] = []
    used_groups: set[str] = set()

    for plot, polygon in polygons.items():
        crop = allocation.get(plot)
        color = GROUP_COLORS["NC"] if crop is None else group_color(crop)
        if crop is not None:
            try:
                used_groups.add(base_group_for(crop))
            except KeyError:
                pass
        for ring in polygon.rings:
            if len(ring) >= 3:
                vertices.append(ring)
                colors.append(color)

    if vertices:
        collection = PolyCollection(
            vertices,
            facecolors=colors,
            edgecolors="white" if edge_width else "none",
            linewidths=edge_width,
        )
        ax.add_collection(collection)

    extent = bounds or _bounds_of(polygons)
    if extent:
        x0, y0, x1, y1 = extent
        pad = max((x1 - x0), (y1 - y0)) * 0.02
        ax.set_xlim(x0 - pad, x1 + pad)
        ax.set_ylim(y0 - pad, y1 + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(title, fontsize=11)

    if show_legend and used_groups:
        handles = [
            Line2D([0], [0], marker="s", linestyle="", markersize=8,
                   markerfacecolor=GROUP_COLORS.get(g, _UNKNOWN_COLOR),
                   markeredgecolor="none", label=label_for(g))
            for g in sorted(used_groups)
        ]
        ax.legend(handles=handles, fontsize=7, loc="upper left",
                  bbox_to_anchor=(1.01, 1.0), frameon=False)
    fig.tight_layout()
    return fig


def build_change_figure(
    polygons: dict[str, Polygon],
    before: dict[str, str],
    after: dict[str, str],
    *,
    title: str,
    bounds: tuple[float, float, float, float] | None = None,
) -> "plt.Figure":
    """Where the land use CHANGED, in three colours.

    Two maps side by side show what is where; they do not show what MOVED, because the eye
    cannot difference two mosaics. This one answers that directly: green kept its observed
    group, red changed, grey was never allocated on either side.
    """
    fig, ax = plt.subplots(figsize=_figsize(bounds or _bounds_of(polygons)))
    palette = {"inchange": "#4daf4a", "change": "#e41a1c", "hors": "#e0e0e0"}
    vertices: list[list[tuple[float, float]]] = []
    colors: list[str] = []
    tally = {"inchange": 0, "change": 0, "hors": 0}

    for plot, polygon in polygons.items():
        old, new = before.get(plot), after.get(plot)
        if old is None or new is None:
            kind = "hors"
        else:
            try:
                kind = "inchange" if base_group_for(old) == base_group_for(new) else "change"
            except KeyError:
                kind = "hors"
        tally[kind] += 1
        for ring in polygon.rings:
            if len(ring) >= 3:
                vertices.append(ring)
                colors.append(palette[kind])

    if vertices:
        ax.add_collection(PolyCollection(vertices, facecolors=colors, edgecolors="none"))

    extent = bounds or _bounds_of(polygons)
    if extent:
        x0, y0, x1, y1 = extent
        pad = max((x1 - x0), (y1 - y0)) * 0.02
        ax.set_xlim(x0 - pad, x1 + pad)
        ax.set_ylim(y0 - pad, y1 + pad)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(title, fontsize=11)
    labels = {
        "inchange": f"inchangé ({tally['inchange']:,})",
        "change": f"changé ({tally['change']:,})",
        "hors": f"non alloué ({tally['hors']:,})",
    }
    ax.legend(
        handles=[
            Line2D([0], [0], marker="s", linestyle="", markersize=8,
                   markerfacecolor=palette[k], markeredgecolor="none", label=labels[k])
            for k in ("inchange", "change", "hors")
        ],
        fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False,
    )
    fig.tight_layout()
    return fig


def shared_bounds(polygons: dict[str, Polygon]) -> tuple[float, float, float, float] | None:
    return _bounds_of(polygons)


def _figsize(bounds: "tuple[float, float, float, float] | None") -> tuple[float, float]:
    """Figure shaped like the territory, plus room for the legend.

    A fixed square frame wastes half the canvas on a region that is not square, and the
    equal-aspect axes then float in white space. Height follows the extent's own ratio,
    clamped so a single narrow commune does not produce a sliver.
    """
    width = 9.0
    if not bounds:
        return (width, 7.0)
    x0, y0, x1, y1 = bounds
    span_x, span_y = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    # The map itself gets about two thirds of the width; the legend takes the rest.
    height = (width * 0.66) * (span_y / span_x)
    return (width, min(max(height, 4.0), 11.0))


def _bounds_of(polygons: dict[str, Polygon]) -> tuple[float, float, float, float] | None:
    boxes = [p.bounds for p in polygons.values() if p.rings]
    if not boxes:
        return None
    return (
        min(b[0] for b in boxes), min(b[1] for b in boxes),
        max(b[2] for b in boxes), max(b[3] for b in boxes),
    )


def filter_polygons(
    polygons: dict[str, Polygon], plots: "set[str] | None"
) -> dict[str, Polygon]:
    """Restrict to a subset of plots (an island, a region), keeping insertion order."""
    if plots is None:
        return polygons
    return {plot: poly for plot, poly in polygons.items() if plot in plots}
